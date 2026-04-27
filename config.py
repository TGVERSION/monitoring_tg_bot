import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
ADMIN_TELEGRAM_ID = int(os.getenv("ADMIN_TELEGRAM_ID"))
REPORT_DAY = os.getenv("REPORT_DAY", "monday")
REPORT_TIME = os.getenv("REPORT_TIME", "09:30")
