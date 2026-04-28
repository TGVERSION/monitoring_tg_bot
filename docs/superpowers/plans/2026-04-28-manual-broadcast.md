# Ручная рассылка с выбором специализации — План реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Добавить в `/admin` сценарий ручной рассылки: топ-5 специализаций → выбор → превью → подтверждение → рассылка всем пользователям.

**Architecture:** Новый `handlers/broadcast.py` содержит FSM-сценарий и тестируемую функцию `send_broadcast()`. Новая `get_top_specializations()` в `db.py` возвращает список вместо одной строки. `admin.py` меняет одну кнопку и удаляет старый обработчик `test_broadcast`. `scheduler.py` не трогается.

**Tech Stack:** Python 3.11+, aiogram 3.x, asyncpg, pytest, pytest-asyncio

---

## Структура файлов

| Файл | Действие | Ответственность |
|------|----------|----------------|
| `db.py` | Изменить | Добавить `get_top_specializations()` |
| `handlers/broadcast.py` | Создать | `_spec_button_label`, `send_broadcast`, 4 обработчика |
| `tests/test_broadcast.py` | Создать | 11 тестов: 3 на метку кнопки + 8 на `send_broadcast` |
| `handlers/admin.py` | Изменить | Переименовать кнопку, удалить `test_broadcast` handler |
| `bot.py` | Изменить | Подключить `broadcast.router` |

---

## Task 1: `get_top_specializations` в `db.py`

**Files:**
- Modify: `db.py` — добавить функцию после `get_top_specialization`

- [ ] **Step 1: Добавить функцию в `db.py`**

Вставить после блока `get_top_specialization` (после строки с `since, *filter_params,`):

```python
async def get_top_specializations(last_date, filters: list = None, limit: int = 5) -> list:
    pool = await get_pool()
    fallback = date_type(1900, 1, 1)
    since = last_date if last_date is not None else fallback
    filter_clause, filter_params = _build_filter_clause(filters or [], next_param=3)
    return await pool.fetch(
        f"""
        SELECT
            specialization,
            SUM(ABS("PriceDifference")) AS total_abs_change,
            SUM("PriceDifference")      AS net_change,
            SUM("Price" - "PriceDifference") AS sum_old_price
        FROM price_monitoring
        WHERE "InsertDate" > $1
          AND specialization IS NOT NULL
          AND specialization <> ''
          AND "PriceDifference" IS NOT NULL
          AND "Price" IS NOT NULL
          AND "OrganizationName" IN (SELECT organization_name FROM organizations)
          {filter_clause}
        GROUP BY specialization
        ORDER BY total_abs_change DESC
        LIMIT $2
        """,
        since, limit, *filter_params,
    )
```

- [ ] **Step 2: Проверить синтаксис**

```bash
python -c "import db; print('OK')"
```

Ожидаемый вывод: `OK`

- [ ] **Step 3: Commit**

```bash
git add db.py
git commit -m "feat: add get_top_specializations returning top-N list"
```

---

## Task 2: `_spec_button_label` — заготовка файла (TDD)

**Files:**
- Create: `tests/test_broadcast.py`
- Create: `handlers/broadcast.py` (только `_spec_button_label`)

- [ ] **Step 1: Создать `tests/test_broadcast.py`**

```python
import pytest
from unittest.mock import AsyncMock, patch
from datetime import date


def _spec_row(name="Хирургия", net=500.0, old=5000.0, total_abs=600.0):
    return {
        "specialization": name,
        "net_change": net,
        "sum_old_price": old,
        "total_abs_change": total_abs,
    }


def _services():
    return [
        {
            "OrganizationName": "Клиника А",
            "ServiceName": "УЗИ",
            "Price": 1100.0,
            "PriceDifference": 100.0,
        }
    ]


def test_button_label_up():
    from handlers.broadcast import _spec_button_label
    label = _spec_button_label(_spec_row("Хирургия", net=500.0, old=5000.0))
    assert "⬆️" in label
    assert "Хирургия" in label
    assert "+10.0%" in label


def test_button_label_down():
    from handlers.broadcast import _spec_button_label
    label = _spec_button_label(_spec_row("Педиатрия", net=-300.0, old=5000.0))
    assert "⬇️" in label
    assert "Педиатрия" in label
    assert "-6.0%" in label


def test_button_label_zero_old_price():
    from handlers.broadcast import _spec_button_label
    label = _spec_button_label(_spec_row("Терапия", net=0.0, old=0.0))
    assert "⬇️" in label
    assert "Терапия" in label
    assert "0.0%" in label
```

- [ ] **Step 2: Убедиться что тесты падают**

```bash
pytest tests/test_broadcast.py -v --tb=short
```

Ожидаемый вывод: `ERROR ... ModuleNotFoundError: No module named 'handlers.broadcast'`

- [ ] **Step 3: Создать `handlers/broadcast.py`**

```python
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
```

- [ ] **Step 4: Запустить тесты — 3 passed**

```bash
pytest tests/test_broadcast.py -v --tb=short
```

Ожидаемый вывод: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add handlers/broadcast.py tests/test_broadcast.py
git commit -m "feat: broadcast handler stub with _spec_button_label (TDD)"
```

---

## Task 3: `send_broadcast` (TDD)

**Files:**
- Modify: `tests/test_broadcast.py` — добавить 8 тестов
- Modify: `handlers/broadcast.py` — добавить `send_broadcast`

- [ ] **Step 1: Добавить 8 тестов в `tests/test_broadcast.py`** (после `test_button_label_zero_old_price`)

```python
@pytest.mark.asyncio
async def test_send_broadcast_sends_to_all_users():
    with patch("handlers.broadcast.get_top_specializations", new_callable=AsyncMock) as m_specs, \
         patch("handlers.broadcast.get_top_service_per_org", new_callable=AsyncMock) as m_svc, \
         patch("handlers.broadcast.get_active_users", new_callable=AsyncMock) as m_users, \
         patch("handlers.broadcast.deactivate_user", new_callable=AsyncMock):
        m_specs.return_value = [_spec_row("Хирургия")]
        m_svc.return_value = _services()
        m_users.return_value = [{"telegram_id": 111}, {"telegram_id": 222}]
        bot = AsyncMock()
        from handlers.broadcast import send_broadcast
        sent = await send_broadcast(bot, "Хирургия", [])
        assert sent == 2
        assert bot.send_message.call_count == 2


@pytest.mark.asyncio
async def test_send_broadcast_no_spec_data_returns_zero():
    with patch("handlers.broadcast.get_top_specializations", new_callable=AsyncMock) as m_specs:
        m_specs.return_value = []
        bot = AsyncMock()
        from handlers.broadcast import send_broadcast
        sent = await send_broadcast(bot, "Хирургия", [])
        assert sent == 0
        bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_send_broadcast_empty_report_returns_zero():
    with patch("handlers.broadcast.get_top_specializations", new_callable=AsyncMock) as m_specs, \
         patch("handlers.broadcast.get_top_service_per_org", new_callable=AsyncMock) as m_svc:
        m_specs.return_value = [_spec_row("Хирургия")]
        m_svc.return_value = []
        bot = AsyncMock()
        from handlers.broadcast import send_broadcast
        sent = await send_broadcast(bot, "Хирургия", [])
        assert sent == 0
        bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_send_broadcast_no_users_returns_zero():
    with patch("handlers.broadcast.get_top_specializations", new_callable=AsyncMock) as m_specs, \
         patch("handlers.broadcast.get_top_service_per_org", new_callable=AsyncMock) as m_svc, \
         patch("handlers.broadcast.get_active_users", new_callable=AsyncMock) as m_users:
        m_specs.return_value = [_spec_row("Хирургия")]
        m_svc.return_value = _services()
        m_users.return_value = []
        bot = AsyncMock()
        from handlers.broadcast import send_broadcast
        sent = await send_broadcast(bot, "Хирургия", [])
        assert sent == 0
        bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_send_broadcast_continues_after_error():
    with patch("handlers.broadcast.get_top_specializations", new_callable=AsyncMock) as m_specs, \
         patch("handlers.broadcast.get_top_service_per_org", new_callable=AsyncMock) as m_svc, \
         patch("handlers.broadcast.get_active_users", new_callable=AsyncMock) as m_users, \
         patch("handlers.broadcast.deactivate_user", new_callable=AsyncMock):
        m_specs.return_value = [_spec_row("Хирургия")]
        m_svc.return_value = _services()
        m_users.return_value = [{"telegram_id": 111}, {"telegram_id": 222}]
        bot = AsyncMock()
        bot.send_message.side_effect = [Exception("Telegram error"), None]
        from handlers.broadcast import send_broadcast
        sent = await send_broadcast(bot, "Хирургия", [])
        assert bot.send_message.call_count == 2
        assert sent == 1


@pytest.mark.asyncio
async def test_send_broadcast_deactivates_blocked_user():
    with patch("handlers.broadcast.get_top_specializations", new_callable=AsyncMock) as m_specs, \
         patch("handlers.broadcast.get_top_service_per_org", new_callable=AsyncMock) as m_svc, \
         patch("handlers.broadcast.get_active_users", new_callable=AsyncMock) as m_users, \
         patch("handlers.broadcast.deactivate_user", new_callable=AsyncMock) as m_deactivate:
        m_specs.return_value = [_spec_row("Хирургия")]
        m_svc.return_value = _services()
        m_users.return_value = [{"telegram_id": 111}]
        bot = AsyncMock()
        bot.send_message.side_effect = Exception("Forbidden: bot was blocked by the user")
        from handlers.broadcast import send_broadcast
        await send_broadcast(bot, "Хирургия", [])
        m_deactivate.assert_called_once_with(111)


@pytest.mark.asyncio
async def test_send_broadcast_filters_passed_to_db():
    filters = [{"field_name": "type_group", "field_value": "Прием"}]
    with patch("handlers.broadcast.get_top_specializations", new_callable=AsyncMock) as m_specs, \
         patch("handlers.broadcast.get_top_service_per_org", new_callable=AsyncMock) as m_svc, \
         patch("handlers.broadcast.get_active_users", new_callable=AsyncMock) as m_users, \
         patch("handlers.broadcast.deactivate_user", new_callable=AsyncMock):
        m_specs.return_value = [_spec_row("Хирургия")]
        m_svc.return_value = _services()
        m_users.return_value = [{"telegram_id": 111}]
        bot = AsyncMock()
        from handlers.broadcast import send_broadcast
        await send_broadcast(bot, "Хирургия", filters)
        m_specs.assert_called_once_with(None, filters)
        m_svc.assert_called_once_with("Хирургия", None, filters)


def test_send_broadcast_does_not_import_update_last_processed_date():
    import handlers.broadcast as bmod
    assert not hasattr(bmod, "update_last_processed_date"), \
        "broadcast не должен импортировать update_last_processed_date"
```

- [ ] **Step 2: Запустить — 8 новых тестов должны упасть**

```bash
pytest tests/test_broadcast.py -v --tb=short -k "send_broadcast"
```

Ожидаемый вывод: `ImportError: cannot import name 'send_broadcast'`

- [ ] **Step 3: Добавить `send_broadcast` в `handlers/broadcast.py`** — после `_spec_button_label`

```python
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
```

- [ ] **Step 4: Запустить — 11 passed**

```bash
pytest tests/test_broadcast.py -v --tb=short
```

Ожидаемый вывод: `11 passed`

- [ ] **Step 5: Commit**

```bash
git add handlers/broadcast.py tests/test_broadcast.py
git commit -m "feat: add send_broadcast with TDD (11 tests)"
```

---

## Task 4: Обработчики в `handlers/broadcast.py`

**Files:**
- Modify: `handlers/broadcast.py` — добавить IsAdmin фильтр и 4 обработчика

- [ ] **Step 1: Добавить IsAdmin фильтр**

В начало `handlers/broadcast.py` добавить импорт после остальных импортов:

```python
from handlers.admin import IsAdmin
```

После строки `router = Router()` добавить:

```python
router.callback_query.filter(IsAdmin())
```

- [ ] **Step 2: Добавить обработчик показа списка специализаций** — в конец файла

```python
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
```

- [ ] **Step 3: Добавить обработчик выбора специализации и показа превью**

```python
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
```

- [ ] **Step 4: Добавить обработчики подтверждения и отмены**

```python
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
```

- [ ] **Step 5: Запустить все тесты**

```bash
pytest -v --tb=short
```

Ожидаемый вывод: `40 passed`

- [ ] **Step 6: Commit**

```bash
git add handlers/broadcast.py
git commit -m "feat: add broadcast handler functions (list, preview, confirm, cancel)"
```

---

## Task 5: Подключить роутер, обновить `admin.py` и `bot.py`

**Files:**
- Modify: `handlers/admin.py` — переименовать кнопку, удалить `test_broadcast`
- Modify: `bot.py` — подключить `broadcast.router`

- [ ] **Step 1: Обновить кнопку в `_main_menu` в `handlers/admin.py`**

Найти:
```python
[InlineKeyboardButton(text="📨 Тест-рассылка", callback_data="admin_test_broadcast")],
```

Заменить на:
```python
[InlineKeyboardButton(text="📨 Рассылка", callback_data="admin_broadcast")],
```

- [ ] **Step 2: Удалить обработчик `test_broadcast` из `handlers/admin.py`**

Найти и удалить весь блок (строки 255–266):
```python
@router.callback_query(F.data == "admin_test_broadcast")
async def test_broadcast(callback: CallbackQuery) -> None:
    from scheduler import send_weekly_report

    await callback.message.answer("Запускаю тест-рассылку...")
    try:
        await send_weekly_report(callback.bot, force=True)
        await callback.message.answer("✅ Тест-рассылка завершена.")
    except Exception as exc:
        logger.error("Test broadcast failed: %s", exc)
        await callback.message.answer(f"❌ Ошибка: {exc}")
    await callback.answer()
```

- [ ] **Step 3: Обновить `bot.py`**

Найти:
```python
from handlers import admin, registration
```

Заменить на:
```python
from handlers import admin, broadcast, registration
```

Найти:
```python
    dp.include_router(registration.router)
    dp.include_router(admin.router)
```

Заменить на:
```python
    dp.include_router(registration.router)
    dp.include_router(admin.router)
    dp.include_router(broadcast.router)
```

- [ ] **Step 4: Запустить все тесты**

```bash
pytest -v --tb=short
```

Ожидаемый вывод: `40 passed`

- [ ] **Step 5: Commit**

```bash
git add handlers/admin.py bot.py
git commit -m "feat: wire broadcast router into bot, replace test_broadcast button"
```

---

## Checklist готовности

- [ ] `pytest` — 40 тестов без ошибок
- [ ] `python bot.py` запускается без ошибок
- [ ] `/admin` → «📨 Рассылка» открывает список топ-5 специализаций с процентами
- [ ] Кнопка специализации → превью + кнопки «✅ Отправить всем» / «❌ Отмена»
- [ ] «✅ Отправить всем» → рассылает и показывает «✅ Отправлено N пользователям»
- [ ] «❌ Отмена» → «Рассылка отменена»
- [ ] Автоматическая рассылка в понедельник 9:30 не изменилась
