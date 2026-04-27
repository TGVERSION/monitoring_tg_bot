import logging
from datetime import date

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import REPORT_DAY, REPORT_TIME
from db import (
    deactivate_user,
    get_active_filters,
    get_active_users,
    get_last_processed_date,
    get_max_insert_date,
    get_price_data_for_org,
    update_last_processed_date,
)
from report import build_report

logger = logging.getLogger(__name__)


async def send_weekly_report(bot) -> None:
    last_date = await get_last_processed_date()
    max_date = await get_max_insert_date()

    if max_date is None:
        logger.info("price_monitoring is empty, skipping")
        return

    if last_date is not None and max_date <= last_date:
        logger.info("No new rows since %s, skipping", last_date)
        return

    users = await get_active_users()
    filters = await get_active_filters()
    today = date.today()

    for user in users:
        try:
            rows = await get_price_data_for_org(
                user["organization_name"], filters, last_date
            )
            message = build_report(user["organization_name"], rows, today)
            if message is None:
                logger.info("Empty report for %s, skipping", user["organization_name"])
                continue
            await bot.send_message(user["telegram_id"], message)
        except Exception as exc:
            logger.error("Failed to send to %s: %s", user["telegram_id"], exc)
            if "bot was blocked" in str(exc).lower():
                await deactivate_user(user["telegram_id"])

    await update_last_processed_date(max_date)


def create_scheduler(bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    hour, minute = REPORT_TIME.split(":")
    scheduler.add_job(
        send_weekly_report,
        CronTrigger(day_of_week=REPORT_DAY, hour=int(hour), minute=int(minute)),
        args=[bot],
    )
    return scheduler
