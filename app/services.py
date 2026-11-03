"""Suhbatdoshlar uchun qo'shimcha xizmatlar: valyuta kursi, ob-havo, namoz vaqti, Vikipediya,
tarixda bugun, hikmatli so'zlar va qiziq faktlar. Claude ularni tool sifatida chaqiradi."""
import json
import logging
import re
from datetime import datetime
from urllib.parse import quote
from zoneinfo import ZoneInfo

import aiohttp

log = logging.getLogger(__name__)

TIMEOUT = aiohttp.ClientTimeout(total=10)
HEADERS = {"User-Agent": "tg-automation-bot/1.0 (Telegram assistant bot)"}
DEFAULT_PRAYER_REGION = "toshkent-shahri"
CURRENCIES = ("USD", "EUR", "RUB")
CITIES = {  # ob-havo uchun tayyor koordinatalar; boshqa shaharlar geokodlash orqali topiladi
    "toshkent": ("Toshkent", 41.2995, 69.2401),
    "buxoro": ("Buxoro", 39.7747, 64.4286),
    "samarqand": ("Samarqand", 39.6542, 66.9597),
    "namangan": ("Namangan", 40.9983, 71.6726),
    "andijon": ("Andijon", 40.7821, 72.3442),
    "fargona": ("Farg'ona", 40.3842, 71.7843),
    "nukus": ("Nukus", 42.4600, 59.6000),
    "qarshi": ("Qarshi", 38.8606, 65.7891),
    "navoiy": ("Navoiy", 40.1039, 65.3688),
    "jizzax": ("Jizzax", 40.1158, 67.8422),
    "termiz": ("Termiz", 37.2242, 67.2783),
    "guliston": ("Guliston", 40.4897, 68.7842),
    "urganch": ("Urganch", 41.5500, 60.6333),
}
DEFAULT_WEATHER_CITIES = ("toshkent", "buxoro")
WMO = {
    0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast", 45: "fog", 48: "rime fog",
    51: "light drizzle", 53: "drizzle", 55: "dense drizzle", 61: "light rain", 63: "rain", 65: "heavy rain",
    66: "freezing rain", 67: "heavy freezing rain", 71: "light snow", 73: "snow", 75: "heavy snow",
    77: "snow grains", 80: "rain showers", 81: "rain showers", 82: "violent rain showers",
    85: "snow showers", 86: "heavy snow showers", 95: "thunderstorm", 96: "thunderstorm with hail",
    99: "thunderstorm with heavy hail",
}
PRAYER_NAMES = {
    "bomdod": "Bomdod", "quyosh": "Quyosh", "peshin": "Peshin", "asr": "Asr", "shom": "Shom", "xufton": "Xufton",
}


async def _get_json(url: str, timeout: aiohttp.ClientTimeout = TIMEOUT, **params):
    async with aiohttp.ClientSession(timeout=timeout, headers=HEADERS) as session:
        async with session.get(url, params=params or None) as resp:
            if resp.status == 404:
                return None
            resp.raise_for_status()
            return await resp.json(content_type=None)


async def currency_rates() -> dict:
    try:
        data = await _get_json("https://cbu.uz/ru/arkhiv-kursov-valyut/json/", aiohttp.ClientTimeout(total=4))
        rates = {
            r["Ccy"]: {"rate_uzs": float(r["Rate"]), "change": float(r["Diff"]), "nominal": int(r["Nominal"])}
            for r in data if r["Ccy"] in CURRENCIES
        }
        date = next((r["Date"] for r in data if r["Ccy"] == "USD"), "")
        return {"source": "O'zbekiston Respublikasi Markaziy banki", "date": date, "rates": rates}
    except Exception as e:  # noqa: BLE001  cbu.uz chet el serverlaridan ochilmaydi
        log.info("cbu.uz ishlamadi (%s), zaxira manba ishlatiladi", type(e).__name__)
    data = await _get_json("https://open.er-api.com/v6/latest/USD")
    r = data["rates"]
    rates = {c: {"rate_uzs": round(r["UZS"] / r[c], 2)} for c in CURRENCIES}
    return {
        "source": "open.er-api.com (taxminiy, Markaziy bank rasmiy kursidan biroz farq qilishi mumkin)",
        "date": data.get("time_last_update_utc", ""),
        "rates": rates,
    }


async def _geocode(city: str) -> tuple[str, float, float] | None:
    key = re.sub(r"[^a-z]", "", city.lower())
    for alias, value in CITIES.items():
        if len(key) >= 4 and (alias.startswith(key[:5]) or key.startswith(alias[:5])):
            return value
    for extra in ({"countryCode": "UZ"}, {}):  # avval O'zbekistondan qidiramiz
        data = await _get_json(
            "https://geocoding-api.open-meteo.com/v1/search", name=city, count=1, language="en", **extra
        )
        if data and data.get("results"):
            r = data["results"][0]
            return r["name"], r["latitude"], r["longitude"]
    return None


async def weather(city: str | None = None) -> dict:
    places = [await _geocode(city)] if city else [CITIES[c] for c in DEFAULT_WEATHER_CITIES]
    if places == [None]:
        return {"error": f"'{city}' shahri topilmadi"}
    out = []
    for name, lat, lon in places:
        data = await _get_json(
            "https://api.open-meteo.com/v1/forecast",
            latitude=lat, longitude=lon, timezone="auto", forecast_days=1,
            current="temperature_2m,apparent_temperature,weather_code,wind_speed_10m,relative_humidity_2m",
            daily="temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        )
        cur, day = data["current"], data["daily"]
        out.append({
            "city": name,
            "now": {
                "temperature_c": cur["temperature_2m"],
                "feels_like_c": cur["apparent_temperature"],
                "condition": WMO.get(cur["weather_code"], f"code {cur['weather_code']}"),
                "wind_kmh": cur["wind_speed_10m"],
                "humidity_pct": cur["relative_humidity_2m"],
            },
            "today": {
                "min_c": day["temperature_2m_min"][0],
                "max_c": day["temperature_2m_max"][0],
                "precipitation_chance_pct": day["precipitation_probability_max"][0],
            },
        })
    return {"source": "Open-Meteo", "weather": out}


async def prayer_times(region: str | None = None) -> dict | None:
    """namoz-vaqti.uz. region — slug yoki alias (toshkent, buxoro, samarqand-shahri...). Topilmasa None."""
    slug = quote((region or DEFAULT_PRAYER_REGION).strip().lower().replace(" ", "-"))
    data = await _get_json(f"https://namoz-vaqti.uz/lotin/namoz-vaqtlari/{slug}", format="json")
    if not data or "today" not in data:
        return None
    today = data["today"]
    return {
        "region": data["meta"]["region"]["name"],
        "slug": data["meta"]["region"]["slug"],
        "date": data["meta"]["date"],
        "times": today["times"],
        "current": today.get("current", {}).get("label") or None,
        "next": today.get("next") or None,
    }


def format_prayer_times(data: dict) -> str:
    lines = [f"🕌 {data['region']}, {data['date']}", ""]
    for key, name in PRAYER_NAMES.items():
        if key in data["times"]:
            lines.append(f"{name}: {data['times'][key]}")
    nxt = data.get("next")
    if nxt and nxt.get("time"):
        lines += ["", f"Keyingisi: {nxt.get('label')} — {nxt['time']}"]
    return "\n".join(lines)


async def wiki_summary(topic: str, lang: str = "uz") -> dict:
    lang = lang if lang in ("uz", "ru", "en") else "uz"
    langs = [lang] + [x for x in ("uz", "ru", "en") if x != lang]
    for code in langs:
        title = quote(topic.strip().replace(" ", "_"), safe="")
        data = await _get_json(f"https://{code}.wikipedia.org/api/rest_v1/page/summary/{title}")
        if data and data.get("extract") and data.get("type") != "disambiguation":
            return {
                "title": data.get("title"), "lang": code, "summary": data["extract"],
                "url": data.get("content_urls", {}).get("desktop", {}).get("page"),
            }
    return {"error": f"Vikipediyada «{topic}» topilmadi"}


async def on_this_day(tz: str) -> dict:
    now = datetime.now(ZoneInfo(tz))
    data = await _get_json(f"https://en.wikipedia.org/api/rest_v1/feed/onthisday/selected/{now:%m}/{now:%d}")
    events = (data or {}).get("selected") or []
    return {
        "date": f"{now:%m-%d}",
        "events": [{"year": e.get("year"), "text": e.get("text")} for e in events[:6]],
    }


async def random_quote() -> dict:
    try:
        data = await _get_json("https://api.quotable.io/random")
        return {"quote": data["content"], "author": data["author"]}
    except Exception:  # noqa: BLE001  quotable.io ko'pincha ishlamaydi, zaxira manba
        data = await _get_json("https://zenquotes.io/api/random")
        return {"quote": data[0]["q"], "author": data[0]["a"]}


async def random_fact() -> dict:
    data = await _get_json("https://uselessfacts.jsph.pl/api/v2/facts/random", language="en")
    return {"fact": data["text"]}


TOOLS = [
    {
        "name": "currency_rates",
        "description": "Bugungi valyuta kurslari: USD, EUR, RUB so'mda (Markaziy bank yoki zaxira manba). Manbani javobda ayt.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "weather",
        "description": "Hozirgi ob-havo va bugungi prognoz. Shahar ko'rsatilmasa, Toshkent va Buxoro uchun qaytaradi.",
        "input_schema": {
            "type": "object",
            "properties": {"city": {"type": "string", "description": "Shahar nomi (ixtiyoriy)"}},
        },
    },
    {
        "name": "prayer_times",
        "description": "Bugungi namoz vaqtlari (namoz-vaqti.uz). Hudud ko'rsatilmasa, egasining joylashuvi olinadi.",
        "input_schema": {
            "type": "object",
            "properties": {
                "region": {
                    "type": "string",
                    "description": "O'zbekistondagi hudud lotincha, masalan: toshkent, buxoro, samarqand-shahri, olmazor",
                },
            },
        },
    },
    {
        "name": "wiki_summary",
        "description": "Vikipediyadan atama, joy yoki shaxs haqida qisqacha ma'lumot.",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Maqola nomi, masalan: Amir Temur"},
                "lang": {"type": "string", "enum": ["uz", "ru", "en"], "description": "Vikipediya tili"},
            },
            "required": ["topic"],
        },
    },
    {
        "name": "on_this_day",
        "description": "«Tarixda bugun»: bugungi sanada tarixda bo'lgan voqealar (inglizcha).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "random_quote",
        "description": "Jahon mutafakkirlarining tasodifiy hikmatli so'zi (inglizcha).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "random_fact",
        "description": "Tasodifiy qiziqarli fakt (inglizcha).",
        "input_schema": {"type": "object", "properties": {}},
    },
]


class ToolRunner:
    def __init__(self, tz: str, prayer_region: str | None):
        self.tz = tz
        self.prayer_region = prayer_region

    async def __call__(self, name: str, args: dict) -> str:
        try:
            if name == "currency_rates":
                result = await currency_rates()
            elif name == "weather":
                result = await weather(args.get("city"))
            elif name == "prayer_times":
                result = await prayer_times(args.get("region") or self.prayer_region)
                if result is None:
                    result = {"error": "Bu hudud topilmadi"}
            elif name == "wiki_summary":
                result = await wiki_summary(args.get("topic", ""), args.get("lang", "uz"))
            elif name == "on_this_day":
                result = await on_this_day(self.tz)
            elif name == "random_quote":
                result = await random_quote()
            elif name == "random_fact":
                result = await random_fact()
            else:
                result = {"error": f"noma'lum tool: {name}"}
        except Exception as e:  # noqa: BLE001
            log.warning("Tool %s xatosi: %s", name, e)
            result = {"error": f"Xizmat hozir ishlamayapti ({type(e).__name__})"}
        log.info("Tool %s(%s)", name, args)
        return json.dumps(result, ensure_ascii=False)
