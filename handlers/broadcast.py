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
