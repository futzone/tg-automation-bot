"""Shaxsiy chatlardagi (Telegram Business) xabarlarga avtomatik javob berish."""
import asyncio
import html
import logging
import re
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Bot, Router
from aiogram.types import BusinessConnection, Message

from .config import Config
from .db import Database
from .llm import LLM
from .moderation import BadWords
from .prompt import MEDIA_NAMES, OFFER_TEXTS, build_system_prompt, parse_reply
from .scheduler import create_schedule, format_schedule
from .sender import notify, send_media, send_text
from .services import TOOLS, ToolRunner
from .status import split_duration
from .utils import chat_label, describe_message, split_text

log = logging.getLogger(__name__)
router = Router(name="business")

# Shuncha marta so'kingan suhbatdoshga bot boshqa javob bermaydi (birinchisida ogohlantiradi)
STRIKE_LIMIT = 2
WARN_TEXT = "Iltimos, hurmatni saqlaylik. Haqoratli so'zlarsiz yozsangiz, bajonidil javob beraman."
BLOCK_TEXT = (
    "Hurmatsizlik qilganingiz uchun endi men sizga javob bera olmayman. "
    "{owner}ning o'zi bilan gaplashing 🙏"
)
LIMIT_TEXT = "{owner} hozir band. Xabaringizni qoldiring, bo'shaganda o'zi javob beradi."
NO_EMOJI_REPLY = "🙂"  # emojisi yo'q stikerga javob
# Egasi shaxsiy chatning o'zida yozadigan buyruqlar (% yoki # bilan): %id, %add <qoida>, %rules,
# %del <raqam>, %clear, %pause [muddat], %resume, %schedule <so'rov>, %schedules
CHAT_COMMAND_RE = re.compile(
    r"[%#]\s*(id|add|rules|del|clear|pause|resume|schedules|schedule)\b\s*(.*)", re.IGNORECASE | re.DOTALL
)
# Shuncha AI javobdan keyin suhbatdoshga qo'shimcha xizmatlar (kurs, ob-havo...) taklif qilinadi
OFFER_AFTER_REPLIES = 3
OFFER_EVERY_SECONDS = 7 * 86400
DELETE_BATCH = 100  # deleteBusinessMessages bir chaqiruvda shuncha xabarni o'chiradi


class Responder:
    """Har bir chat uchun javobni biroz kechiktiradi (debounce): suhbatdosh bir nechta
    xabarni ketma-ket yozsa, bot hammasini o'qib, bitta javob beradi."""

    def __init__(self, bot: Bot, db: Database, llm: LLM, cfg: Config):
        self.bot, self.db, self.llm, self.cfg = bot, db, llm, cfg
        self.tasks: dict[int, asyncio.Task] = {}
        self.limited: set[int] = set()  # limitga yetgani haqida egasiga xabar berilgan chatlar
        self.awaiting_ai: set[int] = set()  # AI javobi kutilayotgan chatlar

    def cancel(self, chat_id: int) -> None:
        self.awaiting_ai.discard(chat_id)
        task = self.tasks.pop(chat_id, None)
        if task and not task.done():
            task.cancel()

    def schedule(self, chat_id: int, conn_id: str, label: str, sticker: str | None = None) -> None:
        """sticker — stiker emojisi: AI siz, mos emoji bilan javob beriladi.
        Chatda matnli xabarga AI javobi kutilayotgan bo'lsa, stiker e'tiborga olinmaydi:
        AI hamma xabarga bitta javob beradi."""
        if chat_id in self.awaiting_ai:
            sticker = None
        self.cancel(chat_id)
        if sticker is None:
            self.awaiting_ai.add(chat_id)
        self.tasks[chat_id] = asyncio.create_task(self._run(chat_id, conn_id, label, sticker))

    async def _sticker_reply(self, chat_id: int, conn_id: str, label: str, emoji: str) -> None:
        reply = await self.llm.pick_emoji(emoji) if emoji else NO_EMOJI_REPLY
        await send_text(self.bot, self.db, chat_id, conn_id, reply)
        self.db.add_history(chat_id, "assistant", reply)
        about = f"Stikerga mos emoji {emoji} edi" if emoji else "Stikerning emojisi yo'q edi"
        await self._notify(f"🎭 {label} stiker yubordi. {about} va bunga javoban {reply} yubordim.")

    def _blocked(self, chat_id: int) -> bool:
        return (
            self.db.get_setting("paused") == "1"
            or self.db.is_chat_paused(chat_id)
            or self.db.is_chat_muted(chat_id)
        )

    def _should_offer(self, chat_id: int) -> bool:
        """AI javoblar soni (24 soatlik oyna) — limitdan alohida hisoblanadi, egasi yozganda tozalanmaydi."""
        key, now = f"ai_replies:{chat_id}", int(time.time())
        count, _, since = (self.db.get_setting(key) or "0|0").partition("|")
        if now - int(since) > 86400:
            count, since = "0", str(now)
        count = int(count) + 1
        self.db.set_setting(key, f"{count}|{since}")
        if count < OFFER_AFTER_REPLIES:
            return False
        last = self.db.get_setting(f"offered:{chat_id}")
        return not last or int(last) + OFFER_EVERY_SECONDS < now

    def reset_limits(self) -> None:
        self.db.clear_llm_calls()
        self.limited.clear()

    async def _send_limit_message(self, chat_id: int, conn_id: str, label: str) -> None:
        """Limit tugaganda AI chaqirilmaydi, tayyor matn yuboriladi."""
        text = self.cfg.rate_limit_message or LIMIT_TEXT.format(owner=self.cfg.owner_name)
        await send_text(self.bot, self.db, chat_id, conn_id, text)
        if chat_id not in self.limited:
            self.limited.add(chat_id)
            await self._notify(
                f"🚦 {label} juda ko'p yozyapti: {self.cfg.rate_limit_minutes} daqiqada "
                f"{self.cfg.rate_limit_count} ta AI javob limiti tugadi, endi tayyor matn yuborilyapti."
            )

    async def rebuke(self, chat_id: int, conn_id: str, label: str) -> None:
        """So'kingan suhbatdoshni ogohlantiradi, takrorlansa javob berishni to'xtatadi."""
        self.cancel(chat_id)
        if self._blocked(chat_id):
            return
        final = self.db.add_strike(chat_id) >= STRIKE_LIMIT
        text = BLOCK_TEXT.format(owner=self.cfg.owner_name) if final else WARN_TEXT
        await send_text(self.bot, self.db, chat_id, conn_id, text)
        self.db.add_history(chat_id, "assistant", text)
        if final:
            await self._notify(
                f"🚫 {label} so'kingani uchun bot unga javob berishni to'xtatdi. "
                "Shu chatda o'zingiz yozsangiz yoki /resume bossangiz, cheklov olinadi."
            )

    async def _run(self, chat_id: int, conn_id: str, label: str, sticker: str | None) -> None:
        try:
            await asyncio.sleep(self.cfg.debounce_seconds)
            if self._blocked(chat_id):
                return
            if sticker is not None:
                await asyncio.shield(self._sticker_reply(chat_id, conn_id, label, sticker))
                return
            window = self.cfg.rate_limit_minutes * 60
            if self.db.count_llm_calls(chat_id, window) >= self.cfg.rate_limit_count:
                await asyncio.shield(self._send_limit_message(chat_id, conn_id, label))
                return
            self.limited.discard(chat_id)
            self.db.add_llm_call(chat_id)
            await self.bot.send_chat_action(chat_id, "typing", business_connection_id=conn_id)
            offer = self._should_offer(chat_id)
            system = build_system_prompt(self.db, self.cfg.owner_name, self.cfg.timezone, chat_id)
            history = self.db.get_history(chat_id, self.cfg.history_limit)
            runner = ToolRunner(self.cfg.timezone, self.db.get_setting("location_slug") or None)
            raw = await self.llm.reply(system, history, TOOLS, runner)
            if self._blocked(chat_id):  # siz javob kutilayotgan paytda o'zingiz yozib qo'ygan bo'lsangiz
                return
            # Yuborish jarayonini yangi xabar to'xtatib qo'ymasligi uchun shield
            await asyncio.shield(self._deliver(chat_id, conn_id, label, raw, offer))
        except asyncio.CancelledError:
            pass
        except Exception as e:  # noqa: BLE001
            log.exception("Javob berishda xato (chat %s)", chat_id)
            await self._notify(f"⚠️ {label} chatiga javob berishda xato: {type(e).__name__}: {e}")
        finally:
            if self.tasks.get(chat_id) is asyncio.current_task():
                self.tasks.pop(chat_id, None)
                self.awaiting_ai.discard(chat_id)

    async def _deliver(self, chat_id: int, conn_id: str, label: str, raw: str, offered: bool = False) -> None:
        parsed = parse_reply(raw)
        media = self.db.get_media(parsed.media_id) if parsed.media_id else None
        if media:
            name = MEDIA_NAMES[media["kind"]]
            await send_media(self.bot, chat_id, media, conn_id, self.db)
            self.db.add_history(chat_id, "assistant", f"[tayyor {name} yuborildi]")
            if self.cfg.report_every_reply:
                await self._notify(f"🤖 {label} ga {name} #{media['id']} yuborildi ({media['condition']})")
        elif parsed.text:
            await send_text(self.bot, self.db, chat_id, conn_id, parsed.text)
            self.db.add_history(chat_id, "assistant", parsed.text)
            if offered:
                await self._send_offer(chat_id, conn_id)
            if self.cfg.report_every_reply:
                await self._notify(f"🤖 {label} ga javob berildi:\n\n{parsed.text}")
        if parsed.notify:
            await self._notify(f"🔔 {label}: {parsed.notify}")

    async def _send_offer(self, chat_id: int, conn_id: str) -> None:
        """Qo'shimcha xizmatlar taklifi — javobdan keyin alohida xabar, suhbatdosh tilida."""
        self.db.set_setting(f"offered:{chat_id}", str(int(time.time())))
        user_messages = [text for role, text in self.db.get_history(chat_id, 10) if role == "user"]
        lang = await self.llm.detect_language(user_messages)
        text = OFFER_TEXTS[lang].format(owner=self.cfg.owner_name)
        await send_text(self.bot, self.db, chat_id, conn_id, text)
        self.db.add_history(chat_id, "assistant", text)

    async def _notify(self, text: str) -> None:
        await notify(self.bot, self.cfg.owner_id, text)


async def clear_bot_messages(bot: Bot, db: Database, chat_id: int, conn_id: str) -> tuple[int, int]:
    """Bot shu chatga yuborgan barcha xabarlarni o'chiradi. (o'chirildi, o'chirib bo'lmadi)."""
    ids = [r["message_id"] for r in db.sent_messages(chat_id)]
    deleted = failed = 0
    for i in range(0, len(ids), DELETE_BATCH):
        batch = ids[i:i + DELETE_BATCH]
        try:
            await bot.delete_business_messages(conn_id, batch)
            deleted += len(batch)
        except Exception as e:  # noqa: BLE001
            log.warning("Chat %s: bot xabarlarini o'chirib bo'lmadi: %s", chat_id, e)
            failed += len(batch)
    db.forget_sent(chat_id, ids)  # o'chmaganlari ham: ular odatda juda eski yoki allaqachon o'chirilgan
    return deleted, failed


async def chat_command(
    message: Message, command: str, args: str, db: Database, cfg: Config, bot: Bot, llm: LLM, responder: Responder
) -> None:
    """Egasi suhbatdosh bilan chatda %buyruq yozdi: xabar chatdan o'chiriladi, javob botning o'z chatiga keladi."""
    chat_id, username = message.chat.id, message.chat.username
    label = html.escape(chat_label(message))
    log.info("Egasi chat %s da %%%s buyrug'ini yozdi", chat_id, command)
    if command == "clear":
        deleted, failed = await clear_bot_messages(bot, db, chat_id, message.business_connection_id)
        text = f"🧹 {label}: botning {deleted} ta xabari o'chirildi."
        if failed:
            text += f"\n⚠️ {failed} tasini o'chirib bo'lmadi (juda eski bo'lishi yoki o'chirish ruxsati yo'qligi mumkin)."
        elif not deleted:
            text = f"{label}: bot bu chatda hali hech narsa yozmagan (yoki allaqachon tozalangan)."
    elif command == "pause":
        seconds, _ = split_duration(args)
        db.mute_chat(chat_id, seconds)
        responder.cancel(chat_id)
        until = "%resume yozguningizcha"
        if seconds:
            ends = datetime.fromtimestamp(time.time() + seconds, ZoneInfo(cfg.timezone))
            until = f"{ends:%d.%m %H:%M} gacha"
        text = (
            f"⏸ {label}: bot bu chatda javob bermaydi ({until}).\n"
            "Rejalashtirilgan xabarlar yuborilaveradi. Qayta yoqish: shu chatda %resume"
        )
    elif command == "resume":
        was = db.unmute_chat(chat_id)
        db.unpause_chat(chat_id)
        db.clear_strikes(chat_id)
        text = f"▶️ {label}: bot bu chatda yana javob beradi." if was else f"▶️ {label}: chat pauzada emas edi, cheklovlar tozalandi."
    elif command == "schedule":
        if not args:
            text = (
                "Foydalanish: shu chatda <code>%schedule </code><i>so'rov</i>, masalan:\n"
                "%schedule har juma 08:00 da «Juma muborak» deb yubor\n"
                "%schedule bugun 21:00 da tug'ilgan kuni bilan chiroyli qilib tabrikla"
            )
        else:
            await bot.send_chat_action(cfg.owner_id, "typing")
            text = html.escape(await create_schedule(llm, db, cfg, args, chat_id))
    elif command == "schedules":
        rows = db.list_schedules(chat_id)
        text = (
            f"🗓 {label} uchun rejalashtirilgan xabarlar:\n\n"
            + "\n\n".join(html.escape(format_schedule(r, cfg.timezone)) for r in rows)
            + "\n\nO'chirish: /sdel <raqam>"
            if rows else f"{label} uchun rejalashtirilgan xabar yo'q."
        )
    elif command == "id":
        text = (
            f"🆔 {label}\nID: <code>{chat_id}</code>\n\n"
            f"Shu chatda qoida qo'shish: <code>%add </code><i>qoida</i>\n"
            f"Yoki shu yerda: <code>/for {chat_id} </code><i>qoida</i>"
        )
    elif command == "add":
        if args:
            rid = db.add_person_rule(chat_id, username, args)
            text = f"✅ {label} uchun qoida #{rid} saqlandi:\n{html.escape(args)}"
        else:
            text = "Foydalanish: shu chatda <code>%add </code><i>qoida</i>, masalan: %add Uni «Aliboy» deb chaqir"
    elif command == "rules":
        rules = db.person_rules(chat_id, username)
        lines = "\n".join(f"#{r['id']}. {html.escape(r['text'])}" for r in rules)
        text = f"👤 {label} uchun qoidalar:\n\n{lines}\n\nO'chirish: %del <raqam>" if rules else f"{label} uchun qoida yo'q."
    else:
        rule_ids = {r["id"] for r in db.person_rules(chat_id, username)}
        rid = int(args.lstrip("#")) if args.lstrip("#").isdigit() else None
        if rid in rule_ids and db.delete_person_rule(rid):
            text = f"🗑 {label} uchun qoida #{rid} o'chirildi"
        else:
            text = f"{label} uchun bunday qoida yo'q. Ro'yxat: shu chatda %rules"
    try:
        await bot.delete_business_messages(message.business_connection_id, [message.message_id])
    except Exception as e:  # noqa: BLE001
        log.warning("%%buyruqni chatdan o'chirib bo'lmadi: %s", e)
        text += (
            "\n\n⚠️ Buyruqni chatdan o'chira olmadim, suhbatdosh uni ko'radi. Chat Automation sozlamalarida "
            "botga xabarlarni o'chirish ruxsatini bering yoki uni o'zingiz o'chiring."
        )
    for chunk in split_text(text):
        await bot.send_message(cfg.owner_id, chunk, parse_mode="HTML")


@router.business_connection()
async def on_connection(conn: BusinessConnection, db: Database, cfg: Config, bot: Bot):
    can_reply = bool(conn.rights.can_reply) if conn.rights else bool(conn.can_reply)
    db.save_connection(conn.id, conn.user.id, conn.is_enabled, can_reply)
    if conn.user.id != cfg.owner_id:
        log.warning("Begona akkaunt ulandi: %s (%s), e'tiborsiz qoldiriladi", conn.user.id, conn.user.full_name)
        return
    if not conn.is_enabled:
        text = "🔌 Bot akkauntingizdan uzildi."
    elif can_reply:
        text = "✅ Bot akkauntingizga ulandi va javob bera oladi."
    else:
        text = "⚠️ Bot ulandi, lekin 'Reply to messages' ruxsati o'chiq. Chat Automation sozlamalarida yoqing."
    try:
        await bot.send_message(cfg.owner_id, text)
    except Exception:  # noqa: BLE001
        pass


@router.business_message()
async def on_business_message(
    message: Message, db: Database, cfg: Config, bot: Bot, llm: LLM, responder: Responder, badwords: BadWords
):
    conn_id = message.business_connection_id
    conn = db.get_connection(conn_id)
    if conn is None or not conn["can_reply"]:
        # Ulanish bot ishga tushishidan oldin bo'lgan yoki ruxsat keyin yoqilgan bo'lsa, Telegram'dan so'raymiz
        info = await bot.get_business_connection(conn_id)
        can_reply = bool(info.rights.can_reply) if info.rights else bool(info.can_reply)
        db.save_connection(info.id, info.user.id, info.is_enabled, can_reply)
        conn = db.get_connection(conn_id)

    if conn["user_id"] != cfg.owner_id or not conn["enabled"]:
        return  # faqat egasining akkaunti

    chat_id = message.chat.id
    db.save_contact(chat_id, message.chat.full_name or "Noma'lum", message.chat.username)
    from_owner = message.from_user and message.from_user.id == cfg.owner_id

    if from_owner:
        if message.sender_business_bot:
            # botning o'zi yuborgan xabar, tarixga allaqachon yozilgan; %clear uchun ID si saqlanadi
            db.add_sent(chat_id, message.message_id, conn_id)
            return
        if message.text and (m := CHAT_COMMAND_RE.fullmatch(message.text.strip())):
            return await chat_command(message, m[1].lower(), m[2].strip(), db, cfg, bot, llm, responder)
        # Siz o'zingiz qo'lda yozdingiz: shu chatda bot vaqtincha jim turadi
        db.add_history(chat_id, "assistant", describe_message(message))
        db.pause_chat(chat_id, cfg.pause_minutes * 60)
        responder.cancel(chat_id)
        # Siz faolsiz: AI limiti hamma chatlarda, so'kinish cheklovi shu chatda tozalanadi
        responder.reset_limits()
        db.clear_strikes(chat_id)
        log.info("Egasi chat %s ga yozdi, %s daqiqa pauza", chat_id, cfg.pause_minutes)
        return

    db.add_history(chat_id, "user", describe_message(message))
    if not conn["can_reply"]:
        log.warning("Chat %s: 'Reply to messages' ruxsati yo'q, javob berilmaydi", chat_id)
        return
    if db.get_strikes(chat_id) >= STRIKE_LIMIT:
        responder.cancel(chat_id)
        return  # so'kingani uchun javob berish to'xtatilgan
    if not (message.text or message.sticker):
        return  # GIF, video, audio, ovozli xabar, rasm va fayllarga javob berilmaydi (tarixda qoladi)
    if badwords.contains(message.text or ""):
        return await responder.rebuke(chat_id, conn_id, chat_label(message))
    sticker = (message.sticker.emoji or "") if message.sticker else None
    responder.schedule(chat_id, conn_id, chat_label(message), sticker)
