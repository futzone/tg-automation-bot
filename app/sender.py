"""Suhbatdoshga xabar yuborish. Bot yuborgan har bir xabar ID si saqlanadi, %clear ularni o'chiradi."""
import logging
import sqlite3

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

from .db import Database
from .markup import md_to_html
from .utils import split_text

log = logging.getLogger(__name__)


async def send_text(
    bot: Bot, db: Database, chat_id: int, conn_id: str, text: str, markdown: bool = True
) -> None:
    """markdown=True: model yozgan **qalin**, `kod` va h.k. Telegram formatiga o'giriladi."""
    for chunk in split_text(text):
        msg = None
        if markdown:
            try:
                msg = await bot.send_message(
                    chat_id, md_to_html(chunk), parse_mode="HTML", business_connection_id=conn_id
                )
            except TelegramBadRequest as e:
                log.warning("HTML formatda yuborib bo'lmadi (%s), oddiy matn yuboriladi", e)
        if msg is None:
            msg = await bot.send_message(chat_id, chunk, parse_mode=None, business_connection_id=conn_id)
        db.add_sent(chat_id, msg.message_id, conn_id)


async def send_media(
    bot: Bot, chat_id: int, media: sqlite3.Row, conn_id: str | None = None, db: Database | None = None
) -> None:
    """Saqlangan GIF yoki stikerni yuboradi."""
    send = bot.send_sticker if media["kind"] == "sticker" else bot.send_animation
    msg = await send(chat_id, media["file_id"], business_connection_id=conn_id)
    if conn_id and db:
        db.add_sent(chat_id, msg.message_id, conn_id)


async def notify(bot: Bot, owner_id: int, text: str) -> None:
    """Botning o'z chatida egasiga xabar."""
    try:
        for chunk in split_text(text):
            await bot.send_message(owner_id, chunk)
    except Exception:  # noqa: BLE001
        log.warning("Egasiga xabar yuborib bo'lmadi (botga /start bosilganmi?)")
