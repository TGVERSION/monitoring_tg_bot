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
from handlers.admin import IsAdmin
from report import build_report

logger = logging.getLogger(__name__)
router = Router()
router.callback_query.filter(IsAdmin())


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


@router.callback_query(F.data == "admin_broadcast")
async def show_broadcast_menu(callback: CallbackQuery) -> None:
    filters = await get_active_filters()
    specs = await get_top_specializations(None, filters)
    if not specs:
        await callback.message.edit_text(
            "Нет данных для рассылки.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]]
            ),
        )
        await callback.answer()
        return

    buttons = [
        [InlineKeyboardButton(text=_spec_button_label(s), callback_data=f"bcast_spec_{i}")]
        for i, s in enumerate(specs)
    ]
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")])
    await callback.message.edit_text(
        "Выберите специализацию для рассылки:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("bcast_spec_"))
async def select_specialization(callback: CallbackQuery, state: FSMContext) -> None:
    index = int(callback.data.split("_")[-1])
    filters = await get_active_filters()
    specs = await get_top_specializations(None, filters)
    if index >= len(specs):
        await callback.answer("Данные устарели, откройте меню заново.")
        return

    spec_row = specs[index]
    spec_name = spec_row["specialization"]
    services = await get_top_service_per_org(spec_name, None, filters)
    preview = build_report(spec_row, services, date.today())

    if preview is None:
        await callback.message.answer(
            "Нет изменений цен по выбранной специализации.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]]
            ),
        )
        await callback.answer()
        return

    await state.set_state(BroadcastState.confirming)
    await state.update_data(specialization=spec_name)
    await callback.message.answer(
        f"<b>Превью сообщения:</b>\n\n{preview}",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✅ Отправить всем", callback_data="bcast_confirm")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="bcast_cancel")],
            ]
        ),
    )
    await callback.answer()


@router.callback_query(F.data == "bcast_confirm", BroadcastState.confirming)
async def confirm_broadcast(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    spec_name = data.get("specialization")
    await state.clear()

    filters = await get_active_filters()
    sent = await send_broadcast(callback.bot, spec_name, filters)

    if sent == 0:
        await callback.message.answer("Нет активных подписчиков.")
    else:
        await callback.message.answer(f"✅ Отправлено {sent} пользователям.")
    await callback.answer()


@router.callback_query(F.data == "bcast_cancel")
async def cancel_broadcast(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.answer("Рассылка отменена.")
    await callback.answer()
