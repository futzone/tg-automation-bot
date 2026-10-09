"""Sozlamalar .env faylidan o'qiladi."""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"❌ .env faylida {name} ko'rsatilmagan")
    return value


@dataclass(frozen=True)
class Config:
    bot_token: str
    owner_id: int
    owner_name: str
    anthropic_api_key: str
    model: str
    max_tokens: int
    history_limit: int
    pause_minutes: int
    debounce_seconds: float
    rate_limit_count: int
    rate_limit_minutes: int
    rate_limit_message: str
    timezone: str
    report_every_reply: bool
    db_path: Path


def load_config() -> Config:
    return Config(
        bot_token=_required("BOT_TOKEN"),
        owner_id=int(_required("OWNER_ID")),
        owner_name=_required("OWNER_NAME"),
        anthropic_api_key=_required("ANTHROPIC_API_KEY"),
        model=os.getenv("ANTHROPIC_MODEL", "claude-haiku-5-5").strip(),
        max_tokens=int(os.getenv("MAX_TOKENS", "2000")),
        history_limit=int(os.getenv("HISTORY_LIMIT", "20")),
        pause_minutes=int(os.getenv("PAUSE_MINUTES", "30")),
        debounce_seconds=float(os.getenv("DEBOUNCE_SECONDS", "4")),
        rate_limit_count=int(os.getenv("RATE_LIMIT_COUNT", "5")),
        rate_limit_minutes=int(os.getenv("RATE_LIMIT_MINUTES", "10")),
        rate_limit_message=os.getenv("RATE_LIMIT_MESSAGE", "").strip(),
        timezone=os.getenv("TIMEZONE", "Asia/Tashkent").strip(),
        report_every_reply=os.getenv("REPORT_EVERY_REPLY", "false").lower() in ("1", "true", "yes"),
        db_path=BASE_DIR / os.getenv("DB_PATH", "data/bot.db"),
    )
