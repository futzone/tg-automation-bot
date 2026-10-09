"""Botning o'z chatidagi boshqaruv paneli (faqat egasi uchun)."""
import io
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import BotCommand, BotCommandScopeChat, Message

from .business import STRIKE_LIMIT, Responder
from .config import Config
from .db import Database
from .llm import LLM
from .prompt import DEFAULT_PERSONA, build_system_prompt, parse_reply
from .status import DEFAULT_PRESETS, NAME_RE, all_presets, preset_name, split_duration
from .utils import split_text

MAX_FILE_BYTES = 200_000

HELP = """🤖 Boshqaruv paneli

Qoidalar:
/add <matn> — qoida qo'shish
(buyruqsiz oddiy matn yozsangiz ham qoida sifatida saqlanadi)
/rules — qoidalar ro'yxati
/del <raqam> — qoidani o'chirish

Siz haqingizda:
/persona — joriy tavsifni ko'rish
/persona <matn> — o'zingiz haqingizda yozish (kim ekansiz, nima bilan shug'ullanasiz)

Bilim bazasi:
.txt yoki .md fayl yuboring — bilim sifatida saqlanadi (FAQ, narxlar, xizmatlar...)
/knowledge — ro'yxat
/kdel <raqam> — o'chirish

Hozirgi holatingiz (suhbatdoshlarga shuni aytadi):
/bus, /sleep, /work, /taxi, /family... — tayyor holatlar (to'liq ro'yxat: /statuses)
/bus 40 — 40 daqiqaga (2h = 2 soat), keyin o'zi o'chadi
/bus 40 Chilonzorga ketyapman — qo'shimcha izoh bilan
/set <matn> — erkin holat, masalan: /set 2h Tug'ilgan kundaman
/free — holatni o'chirish
/statuses — holatlar ro'yxati
/newstatus <nom> <tavsif> — o'z holatingizni qo'shish, keyin /<nom>
/delstatus <nom> — o'zingiz qo'shgan holatni o'chirish

Boshqaruv:
/test <xabar> — bot qanday javob berishini sinash (hech kimga yuborilmaydi)
/pause — botni butunlay to'xtatish
/resume — qayta yoqish (chat pauzalari, AI limiti va so'kinish cheklovlari ham tozalanadi)
/status — holat
/prompt — to'liq system promptni ko'rish
/forget — barcha chatlar tarixini o'chirish

💡 Shaxsiy chatda o'zingiz yozsangiz, bot o'sha chatda vaqtincha jim turadi."""

COMMANDS = [
    ("free", "Holatni o'chirish"),
    ("set", "Erkin holat o'rnatish"),
    ("statuses", "Holatlar ro'yxati"),
    ("help", "Yordam"),
    ("add", "Qoida qo'shish"),
    ("rules", "Qoidalar ro'yxati"),
    ("del", "Qoidani o'chirish"),
    ("persona", "O'zingiz haqingizda"),
    ("knowledge", "Bilim bazasi"),
    ("test", "Javobni sinash"),
    ("status", "Holat"),
    ("pause", "To'xtatish"),
    ("resume", "Yoqish"),
]


# Holat nomi sifatida ishlatib bo'lmaydigan buyruqlar
RESERVED = {c for c, _ in COMMANDS} | {"start", "kdel", "forget", "prompt", "newstatus", "delstatus"}


async def setup_commands(bot: Bot, owner_id: int, db: Database) -> None:
    presets = [(name, text[:60]) for name, text in all_presets(db).items()]
    await bot.set_my_commands(
        [BotCommand(command=c, description=d) for c, d in presets + COMMANDS],
        scope=BotCommandScopeChat(chat_id=owner_id),
    )


def create_owner_router(owner_id: int) -> Router:
    router = Router(name="owner")
    router.message.filter(F.chat.type == "private", F.from_user.id == owner_id)

    async def apply_status(message: Message, db: Database, cfg: Config, text: str, seconds: int | None):
        until = int(time.time()) + seconds if seconds else None
        db.set_status(text, until)
        if until:
            ends = f"{datetime.fromtimestamp(until, ZoneInfo(cfg.timezone)):%H:%M} da o'zi o'chadi"
        else:
            ends = "o'chirish: /free"
        await message.answer(f"✅ Holat o'rnatildi ({ends}):\n\n{text}")

    @router.message(CommandStart())
    @router.message(Command("help"))
    async def cmd_help(message: Message):
        await message.answer(HELP)

    @router.message(Command("add"))
    async def cmd_add(message: Message, command: CommandObject, db: Database):
        if not command.args:
            return await message.answer("Foydalanish: /add <qoida matni>")
        rid = db.add_rule(command.args.strip())
        await message.answer(f"✅ Qoida #{rid} saqlandi")

    @router.message(Command("rules"))
    async def cmd_rules(message: Message, db: Database):
        rules = db.list_rules()
        if not rules:
            return await message.answer("Hali qoida yo'q. /add bilan qo'shing.")
        text = "📋 Qoidalar:\n\n" + "\n".join(f"#{r['id']}. {r['text']}" for r in rules)
        for chunk in split_text(text):
            await message.answer(chunk)

    @router.message(Command("del"))
    async def cmd_del(message: Message, command: CommandObject, db: Database):
        if not command.args or not command.args.strip().lstrip("#").isdigit():
            return await message.answer("Foydalanish: /del <raqam>")
        ok = db.delete_rule(int(command.args.strip().lstrip("#")))
        await message.answer("🗑 O'chirildi" if ok else "Bunday qoida topilmadi")

    @router.message(Command("persona"))
    async def cmd_persona(message: Message, command: CommandObject, db: Database):
        if command.args:
            db.set_setting("persona", command.args.strip())
            return await message.answer("✅ Tavsif yangilandi")
        await message.answer("👤 Joriy tavsif:\n\n" + db.get_setting("persona", DEFAULT_PERSONA))

    @router.message(Command("knowledge"))
    async def cmd_knowledge(message: Message, db: Database):
        items = db.list_knowledge()
        if not items:
            return await message.answer("Bilim bazasi bo'sh. .txt yoki .md fayl yuboring.")
        text = "📚 Bilim bazasi:\n\n" + "\n".join(
            f"#{k['id']}. {k['name']} ({len(k['content'])} belgi)" for k in items
        )
        await message.answer(text)

    @router.message(Command("kdel"))
    async def cmd_kdel(message: Message, command: CommandObject, db: Database):
        if not command.args or not command.args.strip().lstrip("#").isdigit():
            return await message.answer("Foydalanish: /kdel <raqam>")
        ok = db.delete_knowledge(int(command.args.strip().lstrip("#")))
        await message.answer("🗑 O'chirildi" if ok else "Topilmadi")

    @router.message(F.document)
    async def on_document(message: Message, bot: Bot, db: Database):
        doc = message.document
        name = doc.file_name or "fayl"
        if not name.lower().endswith((".txt", ".md")):
            return await message.answer("Faqat .txt yoki .md fayllar qabul qilinadi.")
        if doc.file_size and doc.file_size > MAX_FILE_BYTES:
            return await message.answer("Fayl juda katta (maksimum 200 KB).")
        buf = io.BytesIO()
        await bot.download(doc, destination=buf)
        try:
            content = buf.getvalue().decode("utf-8").strip()
        except UnicodeDecodeError:
            return await message.answer("Fayl UTF-8 formatida bo'lishi kerak.")
        if not content:
            return await message.answer("Fayl bo'sh.")
        kid = db.add_knowledge(name, content)
        await message.answer(f"✅ «{name}» bilim bazasiga qo'shildi (#{kid})")

    @router.message(Command("test"))
    async def cmd_test(message: Message, command: CommandObject, db: Database, llm: LLM, cfg: Config):
        if not command.args:
            return await message.answer("Foydalanish: /test <suhbatdosh xabari>")
        await message.bot.send_chat_action(message.chat.id, "typing")
        system = build_system_prompt(db, cfg.owner_name, cfg.timezone)
        try:
            raw = await llm.reply(system, [("user", command.args)])
        except Exception as e:  # noqa: BLE001
            return await message.answer(f"⚠️ Xato: {type(e).__name__}: {e}")
        parsed = parse_reply(raw)
        out = "🧪 Bot javobi:\n\n" + (parsed.text or "(javob bermaydi — [SKIP])")
        if parsed.notify:
            out += f"\n\n🔔 Sizga bildirishnoma: {parsed.notify}"
        for chunk in split_text(out):
            await message.answer(chunk)

    @router.message(Command("pause"))
    async def cmd_pause(message: Message, db: Database):
        db.set_setting("paused", "1")
        await message.answer("⏸ Bot to'xtatildi. Qayta yoqish: /resume")

    @router.message(Command("resume"))
    async def cmd_resume(message: Message, db: Database, responder: Responder):
        db.set_setting("paused", "0")
        db.clear_pauses()
        db.clear_strikes()
        responder.reset_limits()
        await message.answer("▶️ Bot yoqildi")

    @router.message(Command("free"))
    async def cmd_free(message: Message, db: Database):
        db.clear_status()
        await message.answer("🟢 Holat o'chirildi")

    @router.message(Command("set"))
    async def cmd_set(message: Message, command: CommandObject, db: Database, cfg: Config):
        seconds, text = split_duration(command.args or "")
        if not text:
            return await message.answer("Foydalanish: /set [muddat] <holat matni>\nMasalan: /set 2h Tug'ilgan kundaman")
        await apply_status(message, db, cfg, text, seconds)

    @router.message(Command("statuses"))
    async def cmd_statuses(message: Message, db: Database):
        lines = [f"/{name} — {text}" for name, text in all_presets(db).items()]
        await message.answer("🗂 Holatlar:\n\n" + "\n".join(lines) + "\n\nO'chirish: /free")

    @router.message(Command("newstatus"))
    async def cmd_newstatus(message: Message, command: CommandObject, db: Database, bot: Bot):
        name, _, text = (command.args or "").strip().partition(" ")
        name, text = name.lstrip("/").lower(), text.strip()
        if not text or not NAME_RE.fullmatch(name):
            return await message.answer(
                "Foydalanish: /newstatus <nom> <tavsif>\n"
                "Nom: faqat lotin harflari, raqam va _ (masalan: /newstatus dars Dars o'tyapti, telefonga qaray olmaydi)"
            )
        if name in RESERVED:
            return await message.answer(f"/{name} boshqaruv buyrug'i, boshqa nom tanlang.")
        db.save_preset(name, text)
        await setup_commands(bot, message.chat.id, db)
        await message.answer(f"✅ Saqlandi. Yoqish: /{name}")

    @router.message(Command("delstatus"))
    async def cmd_delstatus(message: Message, command: CommandObject, db: Database, bot: Bot):
        name = (command.args or "").strip().lstrip("/").lower()
        if not db.delete_preset(name):
            hint = " (tayyor holatni o'chirib bo'lmaydi)" if name in DEFAULT_PRESETS else ""
            return await message.answer(f"Bunday holat topilmadi{hint}. Ro'yxat: /statuses")
        await setup_commands(bot, message.chat.id, db)
        await message.answer("🗑 O'chirildi")

    @router.message(Command("forget"))
    async def cmd_forget(message: Message, db: Database):
        db.clear_history()
        await message.answer("🧹 Barcha chatlar tarixi o'chirildi")

    @router.message(Command("prompt"))
    async def cmd_prompt(message: Message, db: Database, cfg: Config):
        for chunk in split_text(build_system_prompt(db, cfg.owner_name, cfg.timezone)):
            await message.answer(chunk)

    @router.message(Command("status"))
    async def cmd_status(message: Message, db: Database, cfg: Config):
        paused = db.get_setting("paused") == "1"
        conns = db.conn.execute(
            "SELECT enabled, can_reply FROM connections WHERE user_id = ?", (cfg.owner_id,)
        ).fetchall()
        if not conns:
            conn_text = "ulanmagan (Settings → Business → Chat Automation)"
        elif any(c["enabled"] and c["can_reply"] for c in conns):
            conn_text = "ulangan ✅"
        else:
            conn_text = "ulangan, lekin javob berish ruxsati yo'q ⚠️"
        status = db.get_status()
        if not status:
            status_text = "o'rnatilmagan"
        elif status[1]:
            status_text = f"{status[0]} ({datetime.fromtimestamp(status[1], ZoneInfo(cfg.timezone)):%H:%M} gacha)"
        else:
            status_text = status[0]
        await message.answer(
            f"📊 Holat\n\n"
            f"Bot: {'⏸ to‘xtatilgan' if paused else '▶️ ishlayapti'}\n"
            f"Hozirgi holatingiz: {status_text}\n"
            f"Akkaunt: {conn_text}\n"
            f"Model: {cfg.model}\n"
            f"Qoidalar: {len(db.list_rules())}\n"
            f"Bilimlar: {len(db.list_knowledge())}\n"
            f"AI limiti: har chatga {cfg.rate_limit_minutes} daqiqada {cfg.rate_limit_count} ta javob\n"
            f"So'kingani uchun cheklangan chatlar: {db.count_blocked(STRIKE_LIMIT)}\n"
            f"Qo'lda yozganda pauza: {cfg.pause_minutes} daqiqa"
        )

    @router.message(F.text & ~F.text.startswith("/"))
    async def free_text_rule(message: Message, db: Database):
        rid = db.add_rule(message.text.strip())
        await message.answer(f"✅ Qoida #{rid} sifatida saqlandi. Ko'rish: /rules")

    @router.message(F.text.startswith("/"))
    async def preset_or_unknown(message: Message, db: Database, cfg: Config):
        command, _, args = message.text.partition(" ")
        text = all_presets(db).get(preset_name(command))
        if text is None:
            return await message.answer("Noma'lum buyruq. Yordam: /help, holatlar: /statuses")
        seconds, note = split_duration(args)
        await apply_status(message, db, cfg, f"{text} {note}".strip(), seconds)

    @router.message()
    async def unknown(message: Message):
        await message.answer("Noma'lum buyruq. Yordam: /help")

    return router


def create_stranger_router() -> Router:
    """Botga boshqa odamlar to'g'ridan-to'g'ri yozsa."""
    router = Router(name="stranger")

    @router.message(F.chat.type == "private")
    async def stranger(message: Message):
        await message.answer("Bu shaxsiy yordamchi bot.")

    return router
