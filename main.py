import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
import uvicorn
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from bot.handlers import (
    start, help_command, status, setkey, text_message, photo_message,
    document_message, voice_message, error_handler
)
from core.config import validate_config
from core.storage import init_db

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("atiq-agent")
telegram_app = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global telegram_app
    validate_config()
    init_db()
    telegram_app = Application.builder().token(os.environ["TELEGRAM_BOT_TOKEN"]).build()
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("help", help_command))
    telegram_app.add_handler(CommandHandler("status", status))
    telegram_app.add_handler(CommandHandler("setkey", setkey))
    telegram_app.add_handler(MessageHandler(filters.PHOTO, photo_message))
    telegram_app.add_handler(MessageHandler(filters.Document.ALL, document_message))
    telegram_app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, voice_message))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message))
    telegram_app.add_error_handler(error_handler)
    await telegram_app.initialize()
    await telegram_app.start()
    await telegram_app.updater.start_polling(drop_pending_updates=True)
    log.info("ATIQ AI AGENT started")
    yield
    if telegram_app:
        await telegram_app.updater.stop()
        await telegram_app.stop()
        await telegram_app.shutdown()

app = FastAPI(title="ATIQ AI AGENT", version="1.0.0", lifespan=lifespan)

@app.get("/")
async def home():
    return {"name": "ATIQ AI AGENT", "status": "online"}

@app.get("/health")
async def health():
    return {"status": "ok", "service": "telegram-agent"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "10000")))
