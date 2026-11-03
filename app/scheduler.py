"""Rejalashtirilgan xabarlar: bir martalik yoki takroriy (har kuni, hafta, oy, yil).

Egasi oddiy tilda yozadi ("har oyning 10-sanasida CEO ga ... deb yubor"), Claude uni jadvalga
aylantiradi. Xabar aynan berilgan matn bo'lishi yoki AI topshiriq bo'yicha har safar yangidan yozishi mumkin."""
import asyncio
import calendar
import json
import logging
import re
import time
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot

from .config import Config
from .db import Database
from .llm import LLM
from .prompt import build_system_prompt, parse_reply
from .sender import notify, send_text
from .services import TOOLS, ToolRunner

log = logging.getLogger(__name__)

KINDS = ("once", "daily", "weekly", "monthly", "yearly")
WEEKDAYS = ["dushanba", "seshanba", "chorshanba", "payshanba", "juma", "shanba", "yakshanba"]
MONTHS = [
    "", "yanvar", "fevral", "mart", "aprel", "may", "iyun",
    "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr",
]
TIME_RE = re.compile(r"([01]?\d|2[0-3]):([0-5]\d)")
TICK_SECONDS = 20
GRACE_SECONDS = 3600  # bot o'chiq bo'lib, vaqti shundan ko'p o'tib ketgan xabar yuborilmaydi
CONTACTS_FOR_PARSE = 60
HISTORY_FOR_COMPOSE = 12

PARSE_SYSTEM = """Sen {owner}ning rejalashtirilgan xabar haqidagi so'rovini jadvalga aylantirasan.
Hozirgi vaqt: {now} ({tz}).

{target}

Faqat bitta JSON obyekt qaytar, boshqa hech narsa yozma:
{{"chat_id": <son yoki null>, "error": null, "items": [
  {{"kind": "once|daily|weekly|monthly|yearly", "date": "YYYY-MM-DD" yoki null, "time": "HH:MM",
   "weekday": <0=dushanba ... 6=yakshanba> yoki null, "day": <1-31> yoki null, "month": <1-12> yoki null,
   "mode": "text|ai", "content": "..."}}
]}}

Qoidalar:
- Odatda items da bitta element bo'ladi. So'rovda bir nechta sana bo'lsa (masalan jadval: har qatorda xizmat,
  summa va to'lov kuni), har bir sana uchun alohida element yoz. Bir kunga to'g'ri keladigan qatorlarni
  bitta xabarga birlashtir. Har bir xabar o'zi tushunarli bo'lsin: nima, qancha, qachon (jadvaldagi
  ma'lumotlarni to'liq ko'chir). So'rovdagi umumiy izohlarni (masalan "narxlar o'zgarishi mumkin")
  kerakli joyda saqla.
- once — bir martalik, date to'ldiriladi ("bugun", "ertaga", "15-noyabr" ni hozirgi sanaga nisbatan hisobla).
- daily — har kuni. weekly — har hafta, weekday. monthly — har oy, day. yearly — har yili, month va day.
- Vaqt aytilmagan bo'lsa "09:00". "Kechqurun 9" — 21:00, "tushdan keyin 3" — 15:00.
- mode "text": {owner} yuboriladigan aniq matnni bergan (odatda qo'shtirnoqda yoki "... deb yubor").
  content — aynan o'sha matn, bir harfini ham o'zgartirma.
- mode "ai": {owner} nima yozish kerakligini tasvirlagan (tabrikla, eslat, chiroyli qilib yoz, so'ra).
  content — AI uchun to'liq topshiriq: nima haqida, qanday ohangda; so'rovdagi barcha tafsilotlarni saqla.
- So'rov tushunarsiz bo'lsa yoki qabul qiluvchini aniq topa olmasang, error ga qisqa sabab yoz (o'zbekcha)."""

TARGET_FIXED = "Qabul qiluvchi ma'lum: {label}, chat_id = {chat_id}. chat_id ga shuni yoz."
TARGET_PICK = """Qabul qiluvchini quyidagi suhbatdoshlar ro'yxatidan top (ism, laqab, username yoki shaxsiy
qoidalardagi ta'rif bo'yicha, masalan "CEO", "onam"). Bir nechta odam mos kelsa yoki hech kim topilmasa,
chat_id null bo'lsin va error ga sababini yoz.
{contacts}"""

COMPOSE_TASK = """## Hozirgi vazifa
Hozir sen suhbatdoshning xabariga javob bermayapsan. {owner} oldindan rejalashtirib qo'ygan xabarni yozasan:
u {owner}ning akkauntidan, {owner}ning o'zi yozgandek birinchi shaxsda («men») yuboriladi. Topshiriqqa amal qil,
shaxsiy qoidalardagi murojaat va ohangni saqla, suhbat tarixidan kontekst ol. Kerak bo'lsa toollardan foydalan.
Faqat yuboriladigan xabar matnini yoz: izoh, qo'shtirnoq, [SKIP] yoki [NOTIFY] yozma."""


def next_run(kind: str, spec: dict, tz: str, after: float) -> int | None:
    """Jadval bo'yicha `after` dan keyingi birinchi yuborish vaqti (unix). Bir martalik o'tib ketgan bo'lsa None."""
    zone = ZoneInfo(tz)
    hour, minute = map(int, spec["time"].split(":"))
    now = datetime.fromtimestamp(after, zone)

    def at(d: date) -> int:
        return int(datetime(d.year, d.month, d.day, hour, minute, tzinfo=zone).timestamp())

    candidates: list[int] = []
    if kind == "once":
        candidates = [at(date.fromisoformat(spec["date"]))]
    elif kind == "daily":
        candidates = [at(now.date() + timedelta(days=i)) for i in range(2)]
    elif kind == "weekly":
        d = now.date() + timedelta(days=(spec["weekday"] - now.weekday()) % 7)
        candidates = [at(d), at(d + timedelta(days=7))]
    elif kind == "monthly":
        y, m = now.year, now.month
        for _ in range(13):
            candidates.append(at(date(y, m, min(spec["day"], calendar.monthrange(y, m)[1]))))
            y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    elif kind == "yearly":
        for y in (now.year, now.year + 1):
            candidates.append(at(date(y, spec["month"], min(spec["day"], calendar.monthrange(y, spec["month"])[1]))))
    return next((ts for ts in candidates if ts > after), None)


def describe(kind: str, spec: dict) -> str:
    t = spec["time"]
    if kind == "once":
        d = date.fromisoformat(spec["date"])
        return f"{d.day}-{MONTHS[d.month]} {d.year}, {t} (bir martalik)"
    if kind == "daily":
        return f"har kuni {t}"
    if kind == "weekly":
        return f"har {WEEKDAYS[spec['weekday']]} {t}"
    if kind == "monthly":
        return f"har oyning {spec['day']}-kuni {t}"
    return f"har yili {spec['day']}-{MONTHS[spec['month']]} {t}"


def target_label(db: Database, chat_id: int) -> str:
    c = db.get_contact(chat_id)
    if not c:
        return f"ID {chat_id}"
    return f"{c['name']} (@{c['username']})" if c["username"] else c["name"]


def format_schedule(row, tz: str) -> str:
    spec = json.loads(row["spec"])
    what = f"💬 «{row['content']}»" if row["mode"] == "text" else f"🤖 AI: {row['content']}"
    if len(what) > 160:
        what = what[:157] + "…"
    nxt = datetime.fromtimestamp(row["next_ts"], ZoneInfo(tz))
    who = f"{row['name']} (@{row['username']})" if row["name"] and row["username"] else (row["name"] or f"ID {row['chat_id']}")
    return f"#{row['id']}. {who} — {describe(row['kind'], spec)}\n{what}\nKeyingisi: {nxt:%d.%m.%Y %H:%M}"


def _validate(data: dict) -> tuple[str, dict] | str:
    """(kind, spec) yoki xato matni."""
    kind = data.get("kind")
    if kind not in KINDS:
        return "jadval turini aniqlab bo'lmadi"
    m = TIME_RE.fullmatch(str(data.get("time") or "").strip())
    if not m:
        return "vaqtni aniqlab bo'lmadi"
    spec: dict = {"time": f"{int(m[1]):02d}:{m[2]}"}
    try:
        if kind == "once":
            spec["date"] = date.fromisoformat(str(data.get("date"))).isoformat()
        if kind == "weekly":
            spec["weekday"] = int(data["weekday"])
            assert 0 <= spec["weekday"] <= 6
        if kind in ("monthly", "yearly"):
            spec["day"] = int(data["day"])
            assert 1 <= spec["day"] <= 31
        if kind == "yearly":
            spec["month"] = int(data["month"])
            assert 1 <= spec["month"] <= 12
    except (KeyError, TypeError, ValueError, AssertionError):
        return "sana yoki kunni aniqlab bo'lmadi"
    return kind, spec


async def create_schedule(llm: LLM, db: Database, cfg: Config, request: str, chat_id: int | None = None) -> str:
    """Egasining so'rovini jadvalga aylantirib saqlaydi. Egasiga ko'rsatiladigan javob matnini qaytaradi."""
    now = datetime.now(ZoneInfo(cfg.timezone))
    if chat_id is not None:
        target = TARGET_FIXED.format(label=target_label(db, chat_id), chat_id=chat_id)
        known = {chat_id}
    else:
        contacts = db.list_contacts(CONTACTS_FOR_PARSE)
        if not contacts:
            return "Hali hech kim yozmagan, qabul qiluvchini topib bo'lmaydi. O'sha odam bilan chatda %schedule yozing."
        rules: dict[int, list[str]] = {}
        for r in db.list_person_rules():
            for c in contacts:
                if r["chat_id"] == c["chat_id"] or (r["username"] and r["username"] == c["username"]):
                    rules.setdefault(c["chat_id"], []).append(r["text"])
        lines = []
        for c in contacts:
            line = f"- chat_id {c['chat_id']}: {c['name']}" + (f" (@{c['username']})" if c["username"] else "")
            if c["chat_id"] in rules:
                line += " — qoidalar: " + "; ".join(rules[c["chat_id"]])
            lines.append(line)
        target = TARGET_PICK.format(contacts="\n".join(lines))
        known = {c["chat_id"] for c in contacts}
    system = PARSE_SYSTEM.format(owner=cfg.owner_name, now=f"{now:%Y-%m-%d %H:%M (%A)}", tz=cfg.timezone, target=target)
    raw = await llm.complete(system, request)
    found = re.search(r"\{.*\}", raw, re.DOTALL)
    try:
        data = json.loads(found[0]) if found else {}
    except json.JSONDecodeError:
        data = {}
    if data.get("error") and not data.get("items"):
        return f"⚠️ Tushunmadim: {data['error']}"
    try:
        target_id = int(data.get("chat_id"))
    except (TypeError, ValueError):
        target_id = None
    if target_id not in known:
        return (
            "⚠️ Kimga yuborishni aniqlay olmadim. /schedule @username <so'rov> yoki /schedule <ID> <so'rov> deb yozing, "
            "yoki o'sha odam bilan chatning o'zida %schedule <so'rov> yozing."
        )
    items = data.get("items")
    if not isinstance(items, list):
        items = [data]  # eski format: bitta jadval
    created, problems = [], []
    for item in items:
        if not isinstance(item, dict):
            continue
        checked = _validate(item)
        content = str(item.get("content") or "").strip()
        if isinstance(checked, str) or not content:
            reason = checked if isinstance(checked, str) else "matn yo'q"
            problems.append(f"«{content[:60] or '?'}»: {reason}")
            continue
        kind, spec = checked
        nxt = next_run(kind, spec, cfg.timezone, time.time())
        if nxt is None:
            problems.append(f"{describe(kind, spec)} — vaqti o'tib ketgan")
            continue
        mode = "text" if item.get("mode") == "text" else "ai"
        created.append(db.add_schedule(target_id, kind, json.dumps(spec), mode, content, nxt))
    if not created:
        detail = "; ".join(problems) or "jadvalni aniqlab bo'lmadi"
        return f"⚠️ Tushunmadim: {detail}. Masalan: «har juma 08:00 da 'Juma muborak' deb yubor»."
    rows = {r["id"]: r for r in db.list_schedules(target_id)}
    title = "✅ Rejalashtirildi" if len(created) == 1 else f"✅ {len(created)} ta xabar rejalashtirildi"
    body = "\n\n".join(format_schedule(rows[sid], cfg.timezone) for sid in created)
    text = f"{title}\n\n{body}"
    if problems:
        text += "\n\n⚠️ Qo'shilmadi: " + "; ".join(problems)
    ids = " ".join(f"/sdel {sid}" for sid in created)
    return text + f"\n\nRo'yxat: /schedules, bekor qilish: {ids}"


class Scheduler:
    def __init__(self, bot: Bot, db: Database, llm: LLM, cfg: Config):
        self.bot, self.db, self.llm, self.cfg = bot, db, llm, cfg

    async def run(self) -> None:
        while True:
            try:
                await self.tick()
            except Exception:  # noqa: BLE001
                log.exception("Scheduler xatosi")
            await asyncio.sleep(TICK_SECONDS)

    async def tick(self) -> None:
        now = int(time.time())
        for row in self.db.due_schedules(now):
            # Avval keyingi vaqtga o'tkazamiz: yuborishda xato bo'lsa ham xabar qayta-qayta ketmaydi
            nxt = next_run(row["kind"], json.loads(row["spec"]), self.cfg.timezone, now)
            if nxt:
                self.db.set_schedule_next(row["id"], nxt)
            else:
                self.db.delete_schedule(row["id"])
            label = target_label(self.db, row["chat_id"])
            if now - row["next_ts"] > GRACE_SECONDS:
                await notify(self.bot, self.cfg.owner_id, f"⏰ #{row['id']} ({label}) vaqtida yuborilmadi: bot o'chiq edi.")
                continue
            await self.fire(row, label)

    async def compose(self, chat_id: int, task: str) -> str:
        system = build_system_prompt(self.db, self.cfg.owner_name, self.cfg.timezone, chat_id)
        system += "\n\n" + COMPOSE_TASK.format(owner=self.cfg.owner_name)
        history = self.db.get_history(chat_id, HISTORY_FOR_COMPOSE)
        names = {"user": "Suhbatdosh", "assistant": self.cfg.owner_name}
        transcript = "\n".join(f"{names[role]}: {text}" for role, text in history) or "(yozishma yo'q)"
        prompt = f"Oxirgi yozishmalar (eng yangisi pastda):\n{transcript}\n\nTopshiriq: {task}"
        runner = ToolRunner(self.cfg.timezone, self.db.get_setting("location_slug") or None)
        return parse_reply(await self.llm.complete(system, prompt, TOOLS, runner)).text

    async def fire(self, row, label: str) -> None:
        chat_id = row["chat_id"]
        text = ""
        try:
            conn_id = self.db.owner_connection(self.cfg.owner_id)
            if not conn_id:
                raise RuntimeError("akkaunt botga ulanmagan")
            text = row["content"] if row["mode"] == "text" else await self.compose(chat_id, row["content"])
            if not text:
                raise RuntimeError("AI bo'sh javob qaytardi")
            await send_text(self.bot, self.db, chat_id, conn_id, text)
            self.db.add_history(chat_id, "assistant", text)
            log.info("Rejalashtirilgan xabar #%s chat %s ga yuborildi", row["id"], chat_id)
            await notify(self.bot, self.cfg.owner_id, f"📤 Rejalashtirilgan xabar #{row['id']} {label} ga yuborildi:\n\n{text}")
        except Exception as e:  # noqa: BLE001
            log.exception("Rejalashtirilgan xabar #%s yuborilmadi", row["id"])
            body = f"\n\nMatn (o'zingiz yuborishingiz mumkin):\n{text}" if text else ""
            await notify(
                self.bot, self.cfg.owner_id,
                f"⚠️ Rejalashtirilgan xabar #{row['id']} {label} ga yuborilmadi: {type(e).__name__}: {e}\n"
                "Telegram botga faqat oxirgi 24 soatda faol bo'lgan chatlarga yozishga ruxsat beradi." + body,
            )
