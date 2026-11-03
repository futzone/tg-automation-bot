"""Botning o'z chatidagi boshqaruv paneli (faqat egasi uchun)."""
import html
import io
import logging
import re
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import (
    BotCommand,
    BotCommandScopeChat,
    KeyboardButton,
    KeyboardButtonRequestUsers,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from .business import STRIKE_LIMIT, Responder
from .config import Config
from .db import Database
from .llm import LLM
from .prompt import DEFAULT_PERSONA, MEDIA_NAMES, build_system_prompt, parse_reply
from .scheduler import create_schedule, format_schedule
from .sender import send_media
from .services import DEFAULT_PRAYER_REGION, TOOLS, ToolRunner, format_prayer_times, prayer_times
from .status import DEFAULT_PRESETS, NAME_RE, all_presets, preset_name, split_duration
from .utils import split_text

log = logging.getLogger(__name__)
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

Alohida odamlar uchun qoidalar:
/pick — chatlaringizdan odamni tanlash: ID si chiqadi va keyingi xabaringiz unga qoida bo'ladi
/for @username <qoida> — faqat shu odamga, masalan: /for @ali Uni «Aliboy» deb chaqir
/for <ID> <qoida> — username'i yo'q odam uchun (ID: /contacts)
/for @username — shu odamning qoidalari
/people — barcha shaxsiy qoidalar
/pdel <raqam> — o'chirish
/contacts — botga yozgan suhbatdoshlar va ularning ID si
Yoki o'sha odam bilan chatning o'zida yozing (buyruq chatdan o'chiriladi, javob shu yerga keladi):
%id — uning ID si, %add <qoida> — qoida qo'shish, %rules — ro'yxat, %del <raqam> — o'chirish

GIF va stikerlar (bot matn o'rniga yuboradi):
Menga GIF yoki stiker yuboring, keyin u qachon yuborilishini yozing
(GIF'ni izoh bilan yuborsangiz, izoh shart sifatida olinadi)
/media — ro'yxat, /media <raqam> — ko'rish
/mdel <raqam> — o'chirish
/cancel — yuborilgan GIF/stikerni saqlamaslik

Rejalashtirilgan xabarlar (oddiy tilda yozing):
/schedule @username <so'rov> — masalan: /schedule @ali har juma 08:00 da «Juma muborak» deb yubor
/schedule <so'rov> — odamni bot o'zi topadi: /schedule bugun 21:00 da Oybekni tug'ilgan kuni bilan chiroyli tabrikla
Yoki o'sha odam bilan chatda: %schedule <so'rov>
/schedules — ro'yxat, /sdel <raqam> — o'chirish
Aniq matn qo'shtirnoqda bo'lsa, aynan o'zi ketadi; aks holda AI har safar yangidan yozadi.

Bitta chatni boshqarish (o'sha chatda yozing, % yoki # bilan, buyruq chatdan o'chiriladi):
%clear — bot shu chatda yozgan barcha xabarlarni o'chirish
%pause — bot shu chatda javob bermaydi (%pause 2h — 2 soatga); rejalashtirilgan xabarlar ketaveradi
%resume — qayta yoqish
/paused — pauzadagi chatlar, /unpause <ID> — shu yerdan yoqish

Namoz vaqti:
/namoz — bugungi namoz vaqtlari
/location <hudud> — hududni o'rnatish, masalan: /location buxoro

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
/test @username <xabar> — shu odamga qanday javob berishini sinash
/pause — botni butunlay to'xtatish
/resume — qayta yoqish (chat pauzalari, AI limiti va so'kinish cheklovlari ham tozalanadi)
/status — holat
/prompt — to'liq system promptni ko'rish (/prompt @username — shu odam uchun)
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
    ("pick", "Odamni tanlab, unga qoida yozish"),
    ("for", "Bitta odam uchun qoida"),
    ("people", "Shaxsiy qoidalar"),
    ("contacts", "Suhbatdoshlar"),
    ("knowledge", "Bilim bazasi"),
    ("media", "GIF va stikerlar"),
    ("schedule", "Xabarni rejalashtirish"),
    ("schedules", "Rejalashtirilgan xabarlar"),
    ("namoz", "Namoz vaqtlari"),
    ("location", "Namoz vaqti uchun hudud"),
    ("paused", "Pauzadagi chatlar"),
    ("test", "Javobni sinash"),
    ("status", "Holat"),
    ("pause", "To'xtatish"),
    ("resume", "Yoqish"),
]


# Holat nomi sifatida ishlatib bo'lmaydigan buyruqlar
RESERVED = {c for c, _ in COMMANDS} | {
    "start", "kdel", "forget", "prompt", "newstatus", "delstatus", "mdel", "cancel", "pdel", "id",
    "sdel", "unpause",
}
# Yuborilgan GIF/stiker sharti yoki tanlangan odam uchun qoida shuncha soniya kutiladi,
# keyin oddiy matn yana umumiy qoida bo'lib saqlanadi
PENDING_MEDIA_SECONDS = 600
PICK_REQUEST_ID = 1
PICK_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(
        text="👤 Odamni tanlash",
        request_users=KeyboardButtonRequestUsers(
            request_id=PICK_REQUEST_ID, user_is_bot=False, max_quantity=1, request_name=True, request_username=True
        ),
    )]],
    resize_keyboard=True,
    one_time_keyboard=True,
)
USERNAME_RE = re.compile(r"@([A-Za-z0-9_]{4,32})")
CONTACTS_SHOWN = 30


def contact_label(contact) -> str:
    name = contact["name"]
    return f"{name} (@{contact['username']})" if contact["username"] else name


def resolve_person(db: Database, word: str, known_only: bool = False) -> tuple[int | None, str | None, str] | None:
    """@username yoki ID ni (chat_id, username, ko'rinadigan nom) ga aylantiradi.
    known_only=True bo'lsa, ID faqat botga yozgan odamniki bo'lsagina qabul qilinadi."""
    if m := USERNAME_RE.fullmatch(word):
        username = m[1].lower()
        contact = db.find_contact(username)
        if contact:
            return contact["chat_id"], username, contact_label(contact)
        return None, username, f"@{username}"
    if word.isdigit():
        contact = db.get_contact(int(word))
        if contact:
            return contact["chat_id"], contact["username"], contact_label(contact)
        if not known_only:
            return int(word), None, f"ID {word}"
    return None


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

    @router.message(Command("for"))
    async def cmd_for(message: Message, command: CommandObject, db: Database):
        target, _, text = (command.args or "").strip().partition(" ")
        person = resolve_person(db, target)
        if not person:
            return await message.answer(
                "Odamni ro'yxatdan tanlash uchun pastdagi tugmani bosing (yoki /pick).\n\n"
                "Foydalanish: /for @username <qoida>\n"
                "Masalan: /for @ali Uni «Aliboy» deb chaqir, sensirab gaplash\n"
                "Username'i yo'q bo'lsa, ID bilan: /for 123456789 <qoida> (ID: /contacts)",
                reply_markup=PICK_KEYBOARD,
            )
        chat_id, username, label = person
        if not text.strip():
            rules = db.person_rules(chat_id, username)
            if not rules:
                return await message.answer(f"{label} uchun qoida yo'q.")
            lines = "\n".join(f"#{r['id']}. {r['text']}" for r in rules)
            return await message.answer(f"👤 {label} uchun qoidalar:\n\n{lines}\n\nO'chirish: /pdel <raqam>")
        rid = db.add_person_rule(chat_id, username, text.strip())
        note = ""
        if chat_id is None:
            note = "\n\nBu odam hali yozmagan, shuning uchun username bo'yicha topiladi."
        await message.answer(
            f"✅ {label} uchun qoida #{rid} saqlandi.\nSinash: /test {target} <xabar>{note}"
        )

    @router.message(Command("people"))
    async def cmd_people(message: Message, db: Database):
        rules = db.list_person_rules()
        if not rules:
            return await message.answer("Shaxsiy qoidalar yo'q. Qo'shish: /for @username <qoida>")
        lines = []
        for r in rules:
            who = r["name"] or "?"
            if r["username"]:
                who += f" (@{r['username']})"
            elif r["chat_id"]:
                who += f" (ID {r['chat_id']})"
            lines.append(f"#{r['id']}. {who}: {r['text']}")
        for chunk in split_text("👥 Shaxsiy qoidalar:\n\n" + "\n".join(lines) + "\n\nO'chirish: /pdel <raqam>"):
            await message.answer(chunk)

    @router.message(Command("pdel"))
    async def cmd_pdel(message: Message, command: CommandObject, db: Database):
        if not command.args or not command.args.strip().lstrip("#").isdigit():
            return await message.answer("Foydalanish: /pdel <raqam> (raqamlar: /people)")
        ok = db.delete_person_rule(int(command.args.strip().lstrip("#")))
        await message.answer("🗑 O'chirildi" if ok else "Topilmadi")

    @router.message(Command("contacts"))
    async def cmd_contacts(message: Message, db: Database):
        contacts = db.list_contacts(CONTACTS_SHOWN)
        if not contacts:
            return await message.answer("Hali hech kim yozmagan.")
        lines = [f"{contact_label(c)} — ID {c['chat_id']}" for c in contacts]
        await message.answer(
            "👥 Oxirgi suhbatdoshlar:\n\n" + "\n".join(lines)
            + "\n\nQoida qo'shish: /for @username <qoida> yoki /for <ID> <qoida>"
        )

    @router.message(Command("pick", "id"))
    async def cmd_pick(message: Message):
        await message.answer(
            "Pastdagi tugmani bosing va chatlaringizdan odamni tanlang. Username'i yo'q yoki yopiq akkaunt "
            "bo'lsa ham ishlaydi.",
            reply_markup=PICK_KEYBOARD,
        )

    def pending_person(db: Database) -> int | None:
        chat_id, _, ts = (db.get_setting("pending_person") or "|").partition("|")
        if not chat_id or int(ts) + PENDING_MEDIA_SECONDS < time.time():
            return None
        return int(chat_id)

    @router.message(F.users_shared.request_id == PICK_REQUEST_ID)
    async def on_user_picked(message: Message, db: Database):
        user = message.users_shared.users[0]
        name = " ".join(filter(None, [user.first_name, user.last_name]))
        if name:
            db.save_contact(user.user_id, name, user.username)
        contact = db.get_contact(user.user_id)
        label = html.escape(contact_label(contact) if contact else f"ID {user.user_id}")
        rules = db.person_rules(user.user_id, contact["username"] if contact else None)
        existing = ""
        if rules:
            existing = "\n\nHozirgi qoidalar:\n" + "\n".join(f"#{r['id']}. {html.escape(r['text'])}" for r in rules)
        db.set_setting("pending_media", "")
        db.set_setting("pending_person", f"{user.user_id}|{int(time.time())}")
        await message.answer(
            f"👤 {label}\nID: <code>{user.user_id}</code>{existing}\n\n"
            "Endi shu odam uchun qoidani bitta xabar bilan yozing, masalan: «Uni Aliboy deb chaqir, sensirab gaplash».\n"
            "Bekor qilish: /cancel",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove(),
        )

    def pending_media(db: Database) -> tuple[str, str] | None:
        kind, file_id, ts = (db.get_setting("pending_media") or "||").split("|")
        if not file_id or int(ts) + PENDING_MEDIA_SECONDS < time.time():
            return None
        return kind, file_id

    async def save_media(message: Message, db: Database, kind: str, file_id: str, condition: str):
        db.set_setting("pending_media", "")
        mid = db.add_media(kind, file_id, condition)
        await message.answer(
            f"✅ {MEDIA_NAMES[kind]} #{mid} saqlandi. Qachon yuboriladi: {condition}\n"
            f"Ro'yxat: /media, sinash: /test <xabar>"
        )

    @router.message(F.sticker | F.animation)
    async def on_media(message: Message, db: Database):
        if message.sticker:
            kind, file_id = "sticker", message.sticker.file_id
        else:
            kind, file_id = "animation", message.animation.file_id
        db.set_setting("pending_person", "")
        if message.caption:
            return await save_media(message, db, kind, file_id, message.caption.strip())
        db.set_setting("pending_media", f"{kind}|{file_id}|{int(time.time())}")
        await message.answer(
            f"🎞 Qabul qildim ({MEDIA_NAMES[kind]}). Endi u qachon yuborilishini bitta xabar bilan yozing, "
            "masalan: «Rahmat deyishsa» yoki «Tug'ilgan kunim bilan tabriklashsa».\nBekor qilish: /cancel"
        )

    @router.message(Command("cancel"))
    async def cmd_cancel(message: Message, db: Database):
        had = pending_media(db) is not None or pending_person(db) is not None
        db.set_setting("pending_media", "")
        db.set_setting("pending_person", "")
        await message.answer(
            "Bekor qilindi." if had else "Bekor qiladigan narsa yo'q.", reply_markup=ReplyKeyboardRemove()
        )

    @router.message(Command("media"))
    async def cmd_media(message: Message, command: CommandObject, db: Database, bot: Bot):
        if command.args and command.args.strip().lstrip("#").isdigit():
            media = db.get_media(int(command.args.strip().lstrip("#")))
            if not media:
                return await message.answer("Topilmadi. Ro'yxat: /media")
            await message.answer(f"#{media['id']} — {media['condition']}")
            return await send_media(bot, message.chat.id, media)
        items = db.list_media()
        if not items:
            return await message.answer("Hali GIF yoki stiker yo'q. Menga GIF yoki stiker yuboring.")
        lines = [f"#{m['id']}. {MEDIA_NAMES[m['kind']]} — {m['condition']}" for m in items]
        await message.answer(
            "🎞 GIF va stikerlar:\n\n" + "\n".join(lines) + "\n\nKo'rish: /media <raqam>, o'chirish: /mdel <raqam>"
        )

    @router.message(Command("mdel"))
    async def cmd_mdel(message: Message, command: CommandObject, db: Database):
        if not command.args or not command.args.strip().lstrip("#").isdigit():
            return await message.answer("Foydalanish: /mdel <raqam>")
        ok = db.delete_media(int(command.args.strip().lstrip("#")))
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
    async def cmd_test(message: Message, command: CommandObject, db: Database, llm: LLM, cfg: Config, bot: Bot):
        if not command.args:
            return await message.answer("Foydalanish: /test <suhbatdosh xabari>")
        first, _, rest = command.args.strip().partition(" ")
        person = resolve_person(db, first, known_only=True) if rest.strip() else None
        text = rest.strip() if person else command.args
        chat_id, username = person[:2] if person else (None, None)
        await message.bot.send_chat_action(message.chat.id, "typing")
        system = build_system_prompt(db, cfg.owner_name, cfg.timezone, chat_id, username)
        runner = ToolRunner(cfg.timezone, db.get_setting("location_slug") or None)
        try:
            raw = await llm.reply(system, [("user", text)], TOOLS, runner)
        except Exception as e:  # noqa: BLE001
            return await message.answer(f"⚠️ Xato: {type(e).__name__}: {e}")
        parsed = parse_reply(raw)
        media = db.get_media(parsed.media_id) if parsed.media_id else None
        if media:
            await message.answer(
                f"🧪 Bot matn o'rniga shu {MEDIA_NAMES[media['kind']]}ni yuboradi (#{media['id']}: {media['condition']}):"
            )
            await send_media(bot, message.chat.id, media)
            if parsed.notify:
                await message.answer(f"🔔 Sizga bildirishnoma: {parsed.notify}")
            return
        whom = f" ({person[2]} uchun)" if person else ""
        out = f"🧪 Bot javobi{whom}:\n\n" + (parsed.text or "(javob bermaydi — [SKIP])")
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

    @router.message(Command("schedule"))
    async def cmd_schedule(message: Message, command: CommandObject, db: Database, llm: LLM, cfg: Config):
        args = (command.args or "").strip()
        if not args:
            return await message.answer(
                "Foydalanish: /schedule [@username yoki ID] <so'rov>\n\n"
                "Misollar:\n"
                "/schedule bugun 21:00 da Oybekni tug'ilgan kuni bilan batafsil va chiroyli tabrikla\n"
                "/schedule @ceo har oyning 10-sanasida 09:00 da «Bugun $120 serverlar uchun to'lov qilishimiz kerak» deb yubor\n"
                "/schedule @ali har juma 08:00 da «Juma muborak» deb yubor\n\n"
                "Odamni ko'rsatmasangiz, bot uni /contacts ro'yxatidan ism bo'yicha topadi. "
                "Yoki o'sha odam bilan chatda %schedule <so'rov> yozing."
            )
        first, _, rest = args.partition(" ")
        person = resolve_person(db, first, known_only=True) if rest.strip() else None
        if USERNAME_RE.fullmatch(first) and not person:
            return await message.answer(
                f"{first} hali sizga yozmagan, shuning uchun bot uning chatini bilmaydi. "
                "O'sha odam bilan chatda %schedule <so'rov> yozing."
            )
        await message.bot.send_chat_action(message.chat.id, "typing")
        try:
            if person and person[0] is not None:
                reply = await create_schedule(llm, db, cfg, rest.strip(), person[0])
            else:
                reply = await create_schedule(llm, db, cfg, args)
        except Exception as e:  # noqa: BLE001
            reply = f"⚠️ Xato: {type(e).__name__}: {e}"
        await message.answer(reply)

    @router.message(Command("schedules"))
    async def cmd_schedules(message: Message, db: Database, cfg: Config):
        rows = db.list_schedules()
        if not rows:
            return await message.answer("Rejalashtirilgan xabar yo'q. Qo'shish: /schedule")
        text = "🗓 Rejalashtirilgan xabarlar:\n\n" + "\n\n".join(format_schedule(r, cfg.timezone) for r in rows)
        for chunk in split_text(text + "\n\nO'chirish: /sdel <raqam>"):
            await message.answer(chunk)

    @router.message(Command("sdel"))
    async def cmd_sdel(message: Message, command: CommandObject, db: Database):
        if not command.args or not command.args.strip().lstrip("#").isdigit():
            return await message.answer("Foydalanish: /sdel <raqam> (raqamlar: /schedules)")
        ok = db.delete_schedule(int(command.args.strip().lstrip("#")))
        await message.answer("🗑 O'chirildi" if ok else "Topilmadi")

    @router.message(Command("paused"))
    async def cmd_paused(message: Message, db: Database, cfg: Config):
        rows = db.list_muted()
        if not rows:
            return await message.answer("Pauzadagi chat yo'q. Chatda %pause yozsangiz, bot o'sha chatda javob bermaydi.")
        lines = []
        for r in rows:
            who = r["name"] or "?"
            if r["username"]:
                who += f" (@{r['username']})"
            until = "muddatsiz"
            if r["until_ts"]:
                until = f"{datetime.fromtimestamp(r['until_ts'], ZoneInfo(cfg.timezone)):%d.%m %H:%M} gacha"
            lines.append(f"{who} — ID {r['chat_id']}, {until}")
        await message.answer("⏸ Pauzadagi chatlar:\n\n" + "\n".join(lines) + "\n\nYoqish: /unpause <ID>")

    @router.message(Command("unpause"))
    async def cmd_unpause(message: Message, command: CommandObject, db: Database):
        person = resolve_person(db, (command.args or "").strip())
        if not person or person[0] is None:
            return await message.answer("Foydalanish: /unpause <ID yoki @username> (ro'yxat: /paused)")
        ok = db.unmute_chat(person[0])
        await message.answer(f"▶️ {person[2]}: bot yana javob beradi" if ok else f"{person[2]} pauzada emas")

    @router.message(Command("location"))
    async def cmd_location(message: Message, command: CommandObject, db: Database):
        region = (command.args or "").strip()
        if not region:
            current = db.get_setting("location_name") or "Toshkent shahri (standart)"
            return await message.answer(
                f"📍 Hozirgi hudud: {current}\n\n"
                "O'zgartirish: /location <hudud>, masalan: /location buxoro, /location samarqand-shahri, "
                "/location olmazor"
            )
        try:
            data = await prayer_times(region)
        except Exception as e:  # noqa: BLE001
            return await message.answer(f"⚠️ namoz-vaqti.uz bilan bog'lanib bo'lmadi: {type(e).__name__}")
        if not data:
            return await message.answer("Bunday hudud topilmadi. Lotin harflarida yozing, masalan: /location buxoro")
        db.set_setting("location_slug", data["slug"])
        db.set_setting("location_name", data["region"])
        await message.answer(f"✅ Hudud: {data['region']}\n\n{format_prayer_times(data)}")

    @router.message(Command("namoz"))
    async def cmd_namoz(message: Message, db: Database):
        try:
            data = await prayer_times(db.get_setting("location_slug") or DEFAULT_PRAYER_REGION)
        except Exception as e:  # noqa: BLE001
            return await message.answer(f"⚠️ namoz-vaqti.uz bilan bog'lanib bo'lmadi: {type(e).__name__}")
        if not data:
            return await message.answer("Hudud topilmadi. /location bilan qayta o'rnating.")
        await message.answer(format_prayer_times(data))

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
    async def cmd_prompt(message: Message, command: CommandObject, db: Database, cfg: Config):
        person = resolve_person(db, command.args.strip()) if command.args else None
        chat_id, username = person[:2] if person else (None, None)
        for chunk in split_text(build_system_prompt(db, cfg.owner_name, cfg.timezone, chat_id, username)):
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
            f"Shaxsiy qoidalar: {len(db.list_person_rules())}\n"
            f"GIF va stikerlar: {len(db.list_media())}\n"
            f"Rejalashtirilgan xabarlar: {len(db.list_schedules())}\n"
            f"Pauzadagi chatlar: {len(db.list_muted())}\n"
            f"Namoz vaqti hududi: {db.get_setting('location_name') or 'Toshkent shahri'}\n"
            f"AI limiti: har chatga {cfg.rate_limit_minutes} daqiqada {cfg.rate_limit_count} ta javob\n"
            f"So'kingani uchun cheklangan chatlar: {db.count_blocked(STRIKE_LIMIT)}\n"
            f"Qo'lda yozganda pauza: {cfg.pause_minutes} daqiqa"
        )

    @router.message(F.text & ~F.text.startswith("/"))
    async def free_text_rule(message: Message, db: Database):
        if pending := pending_media(db):
            return await save_media(message, db, *pending, message.text.strip())
        if (chat_id := pending_person(db)) is not None:
            db.set_setting("pending_person", "")
            contact = db.get_contact(chat_id)
            rid = db.add_person_rule(chat_id, contact["username"] if contact else None, message.text.strip())
            label = contact_label(contact) if contact else f"ID {chat_id}"
            return await message.answer(
                f"✅ {label} uchun qoida #{rid} saqlandi.\nSinash: /test {chat_id} <xabar>, ro'yxat: /people"
            )
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
        log.info("Tushunilmagan xabar turi: %s", message.content_type)
        await message.answer(f"Bu turdagi xabarni ({message.content_type}) tushunmadim. Yordam: /help")

    return router


def create_stranger_router() -> Router:
    """Botga boshqa odamlar to'g'ridan-to'g'ri yozsa."""
    router = Router(name="stranger")

    @router.message(F.chat.type == "private")
    async def stranger(message: Message):
        await message.answer("Bu shaxsiy yordamchi bot.")

    return router
