"""Shaxsiy chatlardagi (Telegram Business) xabarlarga avtomatik javob berish."""
import asyncio
import logging

from aiogram import Bot, Router
from aiogram.types import BusinessConnection, Message

from .config import Config
from .db import Database
from .llm import LLM
from .moderation import BadWords
from .prompt import build_system_prompt, parse_reply
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


class Responder:
    """Har bir chat uchun javobni biroz kechiktiradi (debounce): suhbatdosh bir nechta
    xabarni ketma-ket yozsa, bot hammasini o'qib, bitta javob beradi."""

    def __init__(self, bot: Bot, db: Database, llm: LLM, cfg: Config):
        self.bot, self.db, self.llm, self.cfg = bot, db, llm, cfg
        self.tasks: dict[int, asyncio.Task] = {}
        self.limited: set[int] = set()  # limitga yetgani haqida egasiga xabar berilgan chatlar

    def cancel(self, chat_id: int) -> None:
        task = self.tasks.pop(chat_id, None)
        if task and not task.done():
            task.cancel()

    def schedule(self, chat_id: int, conn_id: str, label: str) -> None:
        self.cancel(chat_id)
        self.tasks[chat_id] = asyncio.create_task(self._run(chat_id, conn_id, label))

    def _blocked(self, chat_id: int) -> bool:
        return self.db.get_setting("paused") == "1" or self.db.is_chat_paused(chat_id)

    def reset_limits(self) -> None:
        self.db.clear_llm_calls()
        self.limited.clear()

    async def _send_limit_message(self, chat_id: int, conn_id: str, label: str) -> None:
        """Limit tugaganda AI chaqirilmaydi, tayyor matn yuboriladi."""
        text = self.cfg.rate_limit_message or LIMIT_TEXT.format(owner=self.cfg.owner_name)
        await self.bot.send_message(chat_id, text, business_connection_id=conn_id)
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
        await self.bot.send_message(chat_id, text, business_connection_id=conn_id)
        self.db.add_history(chat_id, "assistant", text)
        if final:
            await self._notify(
                f"🚫 {label} so'kingani uchun bot unga javob berishni to'xtatdi. "
                "Shu chatda o'zingiz yozsangiz yoki /resume bossangiz, cheklov olinadi."
            )

    async def _run(self, chat_id: int, conn_id: str, label: str) -> None:
        try:
            await asyncio.sleep(self.cfg.debounce_seconds)
            if self._blocked(chat_id):
                return
            window = self.cfg.rate_limit_minutes * 60
            if self.db.count_llm_calls(chat_id, window) >= self.cfg.rate_limit_count:
                await asyncio.shield(self._send_limit_message(chat_id, conn_id, label))
                return
            self.limited.discard(chat_id)
            self.db.add_llm_call(chat_id)
            await self.bot.send_chat_action(chat_id, "typing", business_connection_id=conn_id)
            system = build_system_prompt(self.db, self.cfg.owner_name, self.cfg.timezone)
            history = self.db.get_history(chat_id, self.cfg.history_limit)
            raw = await self.llm.reply(system, history)
            if self._blocked(chat_id):  # siz javob kutilayotgan paytda o'zingiz yozib qo'ygan bo'lsangiz
                return
            # Yuborish jarayonini yangi xabar to'xtatib qo'ymasligi uchun shield
            await asyncio.shield(self._deliver(chat_id, conn_id, label, raw))
        except asyncio.CancelledError:
            pass
        except Exception as e:  # noqa: BLE001
            log.exception("Javob berishda xato (chat %s)", chat_id)
            await self._notify(f"⚠️ {label} chatiga javob berishda xato: {type(e).__name__}: {e}")
        finally:
            if self.tasks.get(chat_id) is asyncio.current_task():
                self.tasks.pop(chat_id, None)

    async def _deliver(self, chat_id: int, conn_id: str, label: str, raw: str) -> None:
        parsed = parse_reply(raw)
        if parsed.text:
            for chunk in split_text(parsed.text):
                await self.bot.send_message(chat_id, chunk, business_connection_id=conn_id)
            self.db.add_history(chat_id, "assistant", parsed.text)
            if self.cfg.report_every_reply:
                await self._notify(f"🤖 {label} ga javob berildi:\n\n{parsed.text}")
        if parsed.notify:
            await self._notify(f"🔔 {label}: {parsed.notify}")

    async def _notify(self, text: str) -> None:
        try:
            for chunk in split_text(text):
                await self.bot.send_message(self.cfg.owner_id, chunk)
        except Exception:  # noqa: BLE001
            log.warning("Egasiga xabar yuborib bo'lmadi (botga /start bosilganmi?)")


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
    message: Message, db: Database, cfg: Config, bot: Bot, responder: Responder, badwords: BadWords
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
    from_owner = message.from_user and message.from_user.id == cfg.owner_id

    if from_owner:
        if message.sender_business_bot:
            return  # botning o'zi yuborgan xabar, tarixga allaqachon yozilgan
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
    if badwords.contains(message.text or message.caption or ""):
        return await responder.rebuke(chat_id, conn_id, chat_label(message))
    responder.schedule(chat_id, conn_id, chat_label(message))
