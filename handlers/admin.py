import logging

from aiogram import F, Router
from aiogram.filters import BaseFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    TelegramObject,
)

from config import ADMIN_TELEGRAM_ID
from db import (
    add_filter,
    add_organization,
    delete_filter,
    get_all_bot_users,
    get_all_filters,
    get_all_organizations,
    set_user_active,
)

logger = logging.getLogger(__name__)
router = Router()


class IsAdmin(BaseFilter):
    async def __call__(self, event: TelegramObject) -> bool:
        user = getattr(event, "from_user", None)
        return user is not None and user.id == ADMIN_TELEGRAM_ID


router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

FILTER_FIELDS = [
    "GroupName",
    "SubGroupName",
    "ServiceName",
    "type_reception",
    "specialization",
    "type_filial",
    "type_group",
]


class AdminState(StatesGroup):
    waiting_filter_field = State()
    waiting_filter_value = State()
    waiting_org_inn = State()
    waiting_org_name = State()


def _main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔧 Фильтры", callback_data="admin_filters")],
            [InlineKeyboardButton(text="🏥 Организации", callback_data="admin_orgs")],
            [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")],
            [InlineKeyboardButton(text="📨 Рассылка", callback_data="admin_broadcast")],
        ]
    )


@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    await message.answer("Панель администратора:", reply_markup=_main_menu())


@router.callback_query(F.data == "admin_filters")
async def show_filters(callback: CallbackQuery) -> None:
    filters = await get_all_filters()
    if filters:
        lines = "\n".join(
            f"{f['id']}. {f['field_name']} = {f['field_value']} "
            f"{'✅' if f['is_active'] else '❌'}"
            for f in filters
        )
        text = f"Текущие фильтры:\n{lines}"
    else:
        text = "Фильтры не настроены."

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить", callback_data="filter_add")],
            [InlineKeyboardButton(text="🗑 Удалить", callback_data="filter_delete")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")],
        ]
    )
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "filter_add")
async def filter_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    fields_text = "\n".join(f"• {f}" for f in FILTER_FIELDS)
    await callback.message.answer(
        f"Введите название поля для фильтра:\n{fields_text}"
    )
    await state.set_state(AdminState.waiting_filter_field)
    await callback.answer()


@router.message(AdminState.waiting_filter_field)
async def filter_field_received(message: Message, state: FSMContext) -> None:
    if message.text not in FILTER_FIELDS:
        await message.answer(
            f"Неверное поле. Допустимые значения:\n"
            + "\n".join(f"• {f}" for f in FILTER_FIELDS)
        )
        return
    await state.update_data(field_name=message.text)
    await message.answer(f"Введите значение для поля {message.text}:")
    await state.set_state(AdminState.waiting_filter_value)


@router.message(AdminState.waiting_filter_value)
async def filter_value_received(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    value = message.text.strip()
    await add_filter(data["field_name"], value)
    await state.clear()
    await message.answer(f"✅ Фильтр {data['field_name']} = {value} добавлен.")


@router.callback_query(F.data == "filter_delete")
async def filter_delete_list(callback: CallbackQuery) -> None:
    filters = await get_all_filters()
    if not filters:
        await callback.message.answer("Нет фильтров для удаления.")
        await callback.answer()
        return
    buttons = [
        [InlineKeyboardButton(
            text=f"#{f['id']} {f['field_name']} = {f['field_value']}",
            callback_data=f"del_filter_{f['id']}",
        )]
        for f in filters
    ]
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_filters")])
    await callback.message.edit_text(
        "Выберите фильтр для удаления:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("del_filter_"))
async def filter_delete_confirm(callback: CallbackQuery) -> None:
    filter_id = int(callback.data.split("_")[-1])
    await delete_filter(filter_id)

    # Обновляем список фильтров в том же сообщении
    filters = await get_all_filters()
    if filters:
        buttons = [
            [InlineKeyboardButton(
                text=f"#{f['id']} {f['field_name']} = {f['field_value']}",
                callback_data=f"del_filter_{f['id']}",
            )]
            for f in filters
        ]
        buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_filters")])
        await callback.message.edit_text(
            f"✅ Фильтр #{filter_id} удалён.\n\nВыберите фильтр для удаления:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        )
    else:
        await callback.message.edit_text(
            f"✅ Фильтр #{filter_id} удалён. Фильтров больше нет.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="admin_filters")]]
            ),
        )
    await callback.answer()


@router.callback_query(F.data == "admin_orgs")
async def show_orgs(callback: CallbackQuery) -> None:
    orgs = await get_all_organizations()
    if orgs:
        lines = "\n".join(f"• {o['inn']} — {o['organization_name']}" for o in orgs)
        text = f"Организации:\n{lines}"
    else:
        text = "Организации не добавлены."

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить", callback_data="org_add")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")],
        ]
    )
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "org_add")
async def org_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.answer("Введите ИНН организации:")
    await state.set_state(AdminState.waiting_org_inn)
    await callback.answer()


@router.message(AdminState.waiting_org_inn)
async def org_inn_received(message: Message, state: FSMContext) -> None:
    await state.update_data(inn=message.text.strip())
    await message.answer(
        "Введите название организации (точно как в поле OrganizationName в price_monitoring):"
    )
    await state.set_state(AdminState.waiting_org_name)


@router.message(AdminState.waiting_org_name)
async def org_name_received(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    name = message.text.strip()
    try:
        await add_organization(data["inn"], name)
    except Exception as exc:
        await state.clear()
        if "unique" in str(exc).lower() or "duplicate" in str(exc).lower():
            await message.answer(f"❌ Организация с ИНН {data['inn']} уже существует.")
        else:
            logger.error("Failed to add organization: %s", exc)
            await message.answer("❌ Ошибка при добавлении организации. Попробуйте ещё раз.")
        return
    await state.clear()
    await message.answer(f"✅ Организация «{name}» (ИНН: {data['inn']}) добавлена.")


def _users_text(users) -> str:
    if not users:
        return "Нет зарегистрированных пользователей."
    lines = []
    for u in users:
        status = "✅" if u["is_active"] else "❌"
        date = u["registered_at"].strftime("%d.%m.%Y") if u["registered_at"] else "—"
        lines.append(f"{status} {u['organization_name']} — {date}")
    return f"Пользователи ({len(users)}):\n\n" + "\n".join(lines)


def _users_keyboard(users) -> InlineKeyboardMarkup:
    buttons = []
    for u in users:
        action = "🚫 Откл." if u["is_active"] else "✅ Вкл."
        buttons.append([InlineKeyboardButton(
            text=f"{action} {u['organization_name']}",
            callback_data=f"toggle_user_{u['telegram_id']}",
        )])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(F.data == "admin_users")
async def show_users(callback: CallbackQuery) -> None:
    users = await get_all_bot_users()
    await callback.message.edit_text(
        _users_text(users),
        reply_markup=_users_keyboard(users),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("toggle_user_"))
async def toggle_user(callback: CallbackQuery) -> None:
    telegram_id = int(callback.data.removeprefix("toggle_user_"))
    users = await get_all_bot_users()
    user = next((u for u in users if u["telegram_id"] == telegram_id), None)
    if user is None:
        await callback.answer("Пользователь не найден.")
        return
    new_status = not user["is_active"]
    await set_user_active(telegram_id, new_status)
    users = await get_all_bot_users()
    status_label = "✅ Активирован" if new_status else "🚫 Отключён"
    await callback.message.edit_text(
        _users_text(users),
        reply_markup=_users_keyboard(users),
    )
    await callback.answer(f"{status_label}: {user['organization_name']}")


@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery) -> None:
    await callback.message.edit_text("Панель администратора:", reply_markup=_main_menu())
    await callback.answer()
