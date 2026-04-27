import os

# Set required env vars before any module imports config.py
os.environ.setdefault("ADMIN_TELEGRAM_ID", "0")
os.environ.setdefault("BOT_TOKEN", "test_token")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
