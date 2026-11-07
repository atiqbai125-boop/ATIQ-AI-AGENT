import sqlite3, os, hashlib
from cryptography.fernet import Fernet
from core.config import DB_PATH

def _fernet():
    secret = os.getenv("BOT_SECRET_KEY")
    if not secret or len(secret) < 24:
        raise RuntimeError("BOT_SECRET_KEY must be a random secret of at least 24 characters")
    key = hashlib.sha256(secret.encode()).digest()
    import base64
    return Fernet(base64.urlsafe_b64encode(key))

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as db:
        db.execute("CREATE TABLE IF NOT EXISTS settings (name TEXT PRIMARY KEY, value BLOB NOT NULL)")

def save_api_key(value: str):
    encrypted = _fernet().encrypt(value.encode())
    with sqlite3.connect(DB_PATH) as db:
        db.execute("INSERT OR REPLACE INTO settings(name,value) VALUES('gemini_api_key',?)", (encrypted,))

def get_api_key():
    if DB_PATH.exists():
        with sqlite3.connect(DB_PATH) as db:
            row = db.execute("SELECT value FROM settings WHERE name='gemini_api_key'").fetchone()
        if row:
            return _fernet().decrypt(row[0]).decode()
    return os.getenv("GEMINI_API_KEY")
