import logging
from datetime import date

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from db import (
    deactivate_user,
    get_active_filters,
    get_active_users,
    get_top_service_per_org,
    get_top_specializations,
)
from report import build_report

logger = logging.getLogger(__name__)
router = Router()


class BroadcastState(StatesGroup):
    confirming = State()


def _spec_button_label(spec_row) -> str:
    net_change = float(spec_row["net_change"] or 0)
    sum_old_price = float(spec_row["sum_old_price"] or 0)
    pct = round(net_change / sum_old_price * 100, 1) if sum_old_price else 0.0
    sign = "+" if pct > 0 else ""
    emoji = "⬆️" if net_change > 0 else "⬇️"
    return f"{emoji} {spec_row['specialization']} {sign}{pct}%"


async def send_broadcast(bot, specialization_name: str, filters: list) -> int:
    specs = await get_top_specializations(None, filters)
    spec_row = next((s for s in specs if s["specialization"] == specialization_name), None)
    if spec_row is None:
        return 0

    services = await get_top_service_per_org(specialization_name, None, filters)
    message = build_report(spec_row, services, date.today())
    if message is None:
        return 0

    users = await get_active_users()
    sent = 0
    for user in users:
        try:
            await bot.send_message(user["telegram_id"], message, parse_mode="HTML")
            sent += 1
        except Exception as exc:
            logger.error("Failed to send to %s: %s", user["telegram_id"], exc)
            if "bot was blocked" in str(exc).lower():
                await deactivate_user(user["telegram_id"])
    return sent
