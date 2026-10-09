"""Egasining hozirgi holati (uxlayapti, avtobusda...) uchun tayyor shablonlar."""
import re

from .db import Database

DEFAULT_PRESETS: dict[str, str] = {
    "sleep": "Uxlayapti. Uyg'onganidan keyin javob beradi.",
    "bus": "Avtobusda, jamoat transportida ketyapti. Gavjum bo'lishi mumkin, hozir yozishga qulay emas.",
    "football": "Futbol o'ynayapti, telefoni yonida emas.",
    "meeting": "Uchrashuvda (yig'ilishda), telefonga qaray olmaydi.",
    "drive": "Mashina haydayapti, yo'lda telefonga qaray olmaydi.",
    "gym": "Sport zalida, mashg'ulotda.",
    "lunch": "Ovqatlanyapti, tez orada qaytadi.",
    "work": "Ishga sho'ng'igan, diqqatini jamlab ishlayapti. Bo'shaganda javob beradi.",
    "study": "Darsda yoki o'qish bilan band, telefonga qaramayapti.",
    "interview": "Intervyuda (muhim suhbatda), telefoni o'chirilgan.",
    "majlis": "Majlisda o'tiribdi, telefonga qaray olmaydi.",
    "taxi": "Taksida yo'lda ketyapti, tez orada manziliga yetadi.",
    "metro": "Metroda ketyapti, aloqa yomon bo'lishi mumkin.",
    "trip": "Safarda, kamdan-kam onlayn bo'ladi.",
    "run": "Yugurishga chiqqan, telefonga qaramayapti.",
    "walk": "Sayrda yuribdi, telefonga qaramayapti.",
    "family": "Oilasi bilan vaqt o'tkazyapti, telefonga qaramayapti.",
    "guest": "Mehmondorchilikda yoki to'y-marosimda.",
    "sick": "Tobi yo'q, dam olyapti. Shoshilinch bo'lmasa keyinroq javob beradi.",
    "rest": "Dam olyapti, telefondan uzoqda.",
    "vacation": "Ta'tilda. Ish masalalariga qaytgach javob beradi.",
    "shop": "Bozorda (do'konda) xarid qilyapti, qo'li band.",
}

NAME_RE = re.compile(r"[a-z0-9_]{1,32}")
_DURATION_RE = re.compile(r"(\d+)(m|h)?", re.IGNORECASE)


def all_presets(db: Database) -> dict[str, str]:
    return {**DEFAULT_PRESETS, **db.list_presets()}


def preset_name(command: str) -> str:
    """'/bus-set@mybot' → 'bus'. '-set' / '_set' qo'shimchasi ixtiyoriy."""
    name = command.lstrip("/").partition("@")[0].lower()
    for suffix in ("-set", "_set"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
    return name


def split_duration(args: str) -> tuple[int | None, str]:
    """'40 izoh' → (2400, 'izoh'); '2h' → (7200, ''); muddat bo'lmasa (None, args)."""
    args = args.strip()
    head, _, rest = args.partition(" ")
    m = _DURATION_RE.fullmatch(head)
    if not m or int(m[1]) == 0:
        return None, args
    unit = 3600 if (m[2] or "m").lower() == "h" else 60
    return int(m[1]) * unit, rest.strip()
