import os
from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise EnvironmentError(f"Required environment variable '{name}' is not set")
    return value


BOT_TOKEN = _require("BOT_TOKEN")
DATABASE_URL = _require("DATABASE_URL")
ADMIN_TELEGRAM_ID = int(_require("ADMIN_TELEGRAM_ID"))
REPORT_DAY = os.getenv("REPORT_DAY", "monday")
REPORT_TIME = os.getenv("REPORT_TIME", "09:30")
