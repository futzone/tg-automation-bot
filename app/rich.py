"""Telegram'ning rich message formatidagi xabarlar (jadval, ro'yxat, sarlavha...) matnsiz keladi:
mazmuni `rich_message.blocks` ichida. Ularni oddiy matnga aylantiramiz, shunda buyruqlar va AI ishlaydi."""
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message


def rich_text(t: Any) -> str:
    if t is None:
        return ""
    if isinstance(t, str):
        return t
    if isinstance(t, list):
        return "".join(rich_text(x) for x in t)
    if getattr(t, "text", None) is not None:
        return rich_text(t.text)
    return getattr(t, "alternative_text", None) or getattr(t, "expression", None) or ""


def _kind(block: Any) -> str:
    return str(getattr(block.type, "value", block.type))


def rich_blocks(blocks: list) -> list[str]:
    lines: list[str] = []
    for b in blocks or []:
        kind = _kind(b)
        if kind == "table":
            if getattr(b, "caption", None):
                lines.append(rich_text(b.caption))
            for row in b.cells:
                lines.append("| " + " | ".join(rich_text(c.text).strip() for c in row) + " |")
        elif kind == "list":
            for item in b.items:
                sub = rich_blocks(item.blocks)
                lines.append(f"{item.label or '-'} " + (sub[0] if sub else ""))
                lines += ["   " + s for s in sub[1:]]
        elif kind == "divider":
            lines.append("---")
        elif getattr(b, "blocks", None) is not None:  # details, iqtibos
            if getattr(b, "summary", None) is not None:
                lines.append(rich_text(b.summary))
            lines += rich_blocks(b.blocks)
        elif getattr(b, "text", None) is not None:
            lines.append(rich_text(b.text))
        elif getattr(b, "caption", None) is not None:
            lines.append(rich_text(b.caption))
    return [line for line in lines if line.strip()]


def rich_to_text(message: Message) -> str:
    return "\n".join(rich_blocks(message.rich_message.blocks)).strip()


class RichMessageMiddleware(BaseMiddleware):
    """Matni yo'q rich xabarning text maydonini to'ldiradi."""

    async def __call__(self, handler, event, data):
        if isinstance(event, Message) and event.rich_message and not event.text and not event.caption:
            text = rich_to_text(event)
            if text:
                event = event.model_copy(update={"text": text})
        return await handler(event, data)
