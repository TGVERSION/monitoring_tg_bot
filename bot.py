import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, REPORT_DAY, REPORT_TIME
from handlers import admin, registration
from scheduler import create_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


async def main() -> None:
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(registration.router)
    dp.include_router(admin.router)

    scheduler = create_scheduler(bot)
    scheduler.start()
    logging.info("Scheduler started. Report day: %s, time: %s", REPORT_DAY, REPORT_TIME)

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        scheduler.shutdown()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
