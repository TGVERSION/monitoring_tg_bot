from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from db import get_organization_by_inn, get_user_by_telegram_id, register_user

router = Router()


class Registration(StatesGroup):
    waiting_for_inn = State()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    user = await get_user_by_telegram_id(message.from_user.id)
    if user and user["is_active"]:
        org = await get_organization_by_inn(user["inn"])
        if not org:
            await message.answer("Данные вашей клиники не найдены. Введите ИНН заново:")
            await state.set_state(Registration.waiting_for_inn)
            return
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(text="Изменить клинику", callback_data="change_clinic")
            ]]
        )
        await message.answer(
            f"Вы зарегистрированы как представитель клиники «{org['organization_name']}».",
            reply_markup=keyboard,
        )
    else:
        await message.answer(
            "👋 <b>Добро пожаловать в бот мониторинга цен конкурентов!</b>\n"
            "\n"
            "📊 <b>Что умеет этот бот:</b>\n"
            "• Каждый понедельник в 9:30 присылает отчёт об изменении цен в конкурирующих клиниках\n"
            "• Показывает специализации с наибольшими изменениями цен\n"
            "• Выделяет конкретные услуги, которые подорожали или подешевели, с указанием клиники и процента изменения\n"
            "• Содержит ссылку на полный дашборд аналитики\n"
            "\n"
            "Чтобы начать, введите ИНН вашей клиники:",
            parse_mode="HTML",
        )
        await state.set_state(Registration.waiting_for_inn)


@router.callback_query(F.data == "change_clinic")
async def change_clinic(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.answer("Введите новый ИНН клиники:")
    await state.set_state(Registration.waiting_for_inn)
    await callback.answer()


@router.message(Registration.waiting_for_inn)
async def process_inn(message: Message, state: FSMContext) -> None:
    inn = message.text.strip()
    org = await get_organization_by_inn(inn)
    if not org:
        await message.answer(
            "ИНН не найден. Обратитесь к администратору."
        )
        return
    await register_user(message.from_user.id, inn)
    await state.clear()
    await message.answer(
        f"✅ Вы успешно зарегистрированы как представитель клиники «{org['organization_name']}»."
    )
