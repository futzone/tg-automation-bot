"""Telegram Chat Automation uchun AI javobchi bot.

Ishga tushirish:  python bot.py
"""
import asyncio
import logging

from aiogram import Bot, Dispatcher

from app.business import Responder
from app.business import router as business_router
from app.config import BASE_DIR, load_config
from app.db import Database
from app.llm import LLM
from app.moderation import BadWords
from app.owner import create_owner_router, create_stranger_router, setup_commands


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    cfg = load_config()
    db = Database(cfg.db_path)
    llm = LLM(cfg.anthropic_api_key, cfg.model, cfg.max_tokens)
    bot = Bot(cfg.bot_token)
    responder = Responder(bot, db, llm, cfg)
    badwords = BadWords(BASE_DIR / "badwords.txt")

    dp = Dispatcher(db=db, llm=llm, cfg=cfg, responder=responder, badwords=badwords)
    dp.include_routers(create_owner_router(cfg.owner_id), business_router, create_stranger_router())

    me = await bot.get_me()
    logging.info("Bot @%s ishga tushdi (model: %s, so'kinish filtri: %s ta)", me.username, cfg.model, len(badwords))
    if not me.can_connect_to_business:
        logging.warning("⚠️ BotFather'da Business Mode yoqilmagan! /mybots → Bot Settings → Business Mode")
    await setup_commands(bot, cfg.owner_id, db)
    await bot.delete_webhook(drop_pending_updates=False)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
