import os
from pathlib import Path

DATA_DIR = Path(os.getenv("DATA_DIR", "/var/data"))
WORK_DIR = DATA_DIR / "workspaces"
DB_PATH = DATA_DIR / "agent.sqlite3"
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "18"))
MAX_FILES = int(os.getenv("MAX_PROJECT_FILES", "250"))
MAX_UNPACKED_MB = int(os.getenv("MAX_UNPACKED_MB", "80"))
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
OWNER_ID = int(os.getenv("OWNER_TELEGRAM_ID", "0"))

def validate_config():
    if not os.getenv("TELEGRAM_BOT_TOKEN"):
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN environment variable")
    if OWNER_ID <= 0:
        raise RuntimeError("Set OWNER_TELEGRAM_ID to your numeric Telegram user ID")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    WORK_DIR.mkdir(parents=True, exist_ok=True)
