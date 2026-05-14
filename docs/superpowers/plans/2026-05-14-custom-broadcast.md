# Custom Broadcast Text Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Добавить в ручную рассылку кнопку «✏️ Свой текст», позволяющую администратору ввести произвольное сообщение, посмотреть превью и разослать его всем пользователям.

**Architecture:** Все изменения — в `handlers/broadcast.py`. Добавляются два новых FSM-состояния (`typing_custom`, `confirming_custom`), четыре новых handler и функция `send_broadcast_text`. Существующие `send_broadcast`, `confirm_broadcast`, `cancel_broadcast` не трогаются.

**Tech Stack:** Python 3.12, aiogram 3, asyncio, pytest-asyncio, unittest.mock

---

## Файловая карта

| Файл | Действие |
|------|---------|
| `handlers/broadcast.py` | Изменить: новые состояния, импорты, 4 handler, 1 функция, обновить клавиатуру в `select_specialization` |
| `tests/test_broadcast.py` | Изменить: добавить 7 тестов |

---

## Task 1: `send_broadcast_text` — TDD

**Files:**
- Modify: `handlers/broadcast.py`
- Modify: `tests/test_broadcast.py`

- [ ] **Step 1: Добавить 5 падающих тестов в конец `tests/test_broadcast.py`**

```python
@pytest.mark.asyncio
async def test_send_broadcast_text_sends_to_all_users():
    with patch("handlers.broadcast.get_active_users", new_callable=AsyncMock) as m_users, \
         patch("handlers.broadcast.deactivate_user", new_callable=AsyncMock):
        m_users.return_value = [{"telegram_id": 111}, {"telegram_id": 222}]
        bot = AsyncMock()
        from handlers.broadcast import send_broadcast_text
        sent = await send_broadcast_text(bot, "Привет!")
        assert sent == 2
        bot.send_message.assert_any_call(111, "Привет!")
        bot.send_message.assert_any_call(222, "Привет!")


@pytest.mark.asyncio
async def test_send_broadcast_text_no_users():
    with patch("handlers.broadcast.get_active_users", new_callable=AsyncMock) as m_users:
        m_users.return_value = []
        bot = AsyncMock()
        from handlers.broadcast import send_broadcast_text
        sent = await send_broadcast_text(bot, "Привет!")
        assert sent == 0
        bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_send_broadcast_text_continues_after_error():
    with patch("handlers.broadcast.get_active_users", new_callable=AsyncMock) as m_users, \
         patch("handlers.broadcast.deactivate_user", new_callable=AsyncMock):
        m_users.return_value = [{"telegram_id": 111}, {"telegram_id": 222}]
        bot = AsyncMock()
        bot.send_message.side_effect = [Exception("network error"), None]
        from handlers.broadcast import send_broadcast_text
        sent = await send_broadcast_text(bot, "Привет!")
        assert sent == 1
        assert bot.send_message.call_count == 2


@pytest.mark.asyncio
async def test_send_broadcast_text_deactivates_blocked_user():
    with patch("handlers.broadcast.get_active_users", new_callable=AsyncMock) as m_users, \
         patch("handlers.broadcast.deactivate_user", new_callable=AsyncMock) as m_deactivate:
        m_users.return_value = [{"telegram_id": 111}]
        bot = AsyncMock()
        bot.send_message.side_effect = Exception("Forbidden: bot was blocked by the user")
        from handlers.broadcast import send_broadcast_text
        await send_broadcast_text(bot, "Привет!")
        m_deactivate.assert_called_once_with(111)


@pytest.mark.asyncio
async def test_send_broadcast_text_no_parse_mode():
    with patch("handlers.broadcast.get_active_users", new_callable=AsyncMock) as m_users, \
         patch("handlers.broadcast.deactivate_user", new_callable=AsyncMock):
        m_users.return_value = [{"telegram_id": 111}]
        bot = AsyncMock()
        from handlers.broadcast import send_broadcast_text
        await send_broadcast_text(bot, "Привет!")
        _, kwargs = bot.send_message.call_args
        assert "parse_mode" not in kwargs
```

- [ ] **Step 2: Убедиться, что тесты падают**

```
python -m pytest tests/test_broadcast.py -k "send_broadcast_text" -v
```
Ожидаемый результат: `ImportError: cannot import name 'send_broadcast_text'` или `5 failed`

- [ ] **Step 3: Добавить `send_broadcast_text` в `handlers/broadcast.py`**

Добавить сразу после функции `send_broadcast` (после строки 58):

```python
async def send_broadcast_text(bot, text: str) -> int:
    users = await get_active_users()
    sent = 0
    for user in users:
        try:
            await bot.send_message(user["telegram_id"], text)
            sent += 1
        except Exception as exc:
            logger.error("Failed to send to %s: %s", user["telegram_id"], exc)
            if "bot was blocked" in str(exc).lower():
                await deactivate_user(user["telegram_id"])
    return sent
```

- [ ] **Step 4: Прогнать тесты — убедиться, что 5 новых проходят**

```
python -m pytest tests/test_broadcast.py -k "send_broadcast_text" -v
```
Ожидаемый результат: `5 passed`

- [ ] **Step 5: Прогнать весь suite — убедиться, что ничего не сломалось**

```
python -m pytest --tb=short
```
Ожидаемый результат: `49 passed`

- [ ] **Step 6: Коммит**

```bash
git add handlers/broadcast.py tests/test_broadcast.py
git commit -m "feat: add send_broadcast_text for plain-text custom broadcast (TDD)"
```

---

## Task 2: FSM-состояния, входная точка и валидация ввода — TDD

**Files:**
- Modify: `handlers/broadcast.py`
- Modify: `tests/test_broadcast.py`

- [ ] **Step 1: Добавить 2 падающих теста в конец `tests/test_broadcast.py`**

```python
@pytest.mark.asyncio
async def test_custom_text_empty_rejected():
    message = AsyncMock()
    message.text = "   "
    state = AsyncMock()
    from handlers.broadcast import custom_text_received
    await custom_text_received(message, state)
    message.answer.assert_called_once()
    assert "пустым" in message.answer.call_args[0][0]
    state.update_data.assert_not_called()


@pytest.mark.asyncio
async def test_custom_text_too_long_rejected():
    message = AsyncMock()
    message.text = "а" * 4097
    state = AsyncMock()
    from handlers.broadcast import custom_text_received
    await custom_text_received(message, state)
    message.answer.assert_called_once()
    assert "4096" in message.answer.call_args[0][0]
    state.update_data.assert_not_called()
```

- [ ] **Step 2: Убедиться, что тесты падают**

```
python -m pytest tests/test_broadcast.py -k "custom_text" -v
```
Ожидаемый результат: `ImportError` или `2 failed`

- [ ] **Step 3: Добавить новые FSM-состояния в `BroadcastState`**

Заменить существующий класс `BroadcastState`:

```python
class BroadcastState(StatesGroup):
    confirming        = State()
    typing_custom     = State()
    confirming_custom = State()
```

- [ ] **Step 4: Добавить импорт `html.escape` и `Message` в `handlers/broadcast.py`**

Изменить строку импорта из aiogram:

```python
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
```

Добавить в начало файла (после `from datetime import date`):

```python
from html import escape as html_escape
```

- [ ] **Step 5: Добавить handler `custom_broadcast_start` в `handlers/broadcast.py`**

Добавить после обработчика `show_broadcast_menu`:

```python
@router.callback_query(F.data == "bcast_custom_start", BroadcastState.confirming)
async def custom_broadcast_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(BroadcastState.typing_custom)
    await callback.message.answer("Введите текст для рассылки:")
    await callback.answer()
```

- [ ] **Step 6: Добавить handler `custom_text_received` в `handlers/broadcast.py`**

Добавить после `custom_broadcast_start`:

```python
@router.message(BroadcastState.typing_custom, IsAdmin())
async def custom_text_received(message: Message, state: FSMContext) -> None:
    text = message.text.strip() if message.text else ""
    if not text:
        await message.answer("Текст не может быть пустым. Введите сообщение:")
        return
    if len(text) > 4096:
        await message.answer("Слишком длинный текст (максимум 4096 символов). Введите короче:")
        return
    await state.update_data(custom_text=text)
    await state.set_state(BroadcastState.confirming_custom)
    await message.answer(
        f"<b>Ваш текст:</b>\n\n{html_escape(text)}",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✅ Отправить всем", callback_data="bcast_confirm_custom")],
                [InlineKeyboardButton(text="✏️ Изменить", callback_data="bcast_edit_custom")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="bcast_cancel")],
            ]
        ),
    )
```

- [ ] **Step 7: Прогнать тесты — убедиться, что 2 новых проходят**

```
python -m pytest tests/test_broadcast.py -k "custom_text" -v
```
Ожидаемый результат: `2 passed`

- [ ] **Step 8: Прогнать весь suite**

```
python -m pytest --tb=short
```
Ожидаемый результат: `51 passed`

- [ ] **Step 9: Коммит**

```bash
git add handlers/broadcast.py tests/test_broadcast.py
git commit -m "feat: add typing_custom state and validation for custom broadcast text"
```

---

## Task 3: Confirm/Edit handlers и кнопка «✏️ Свой текст»

**Files:**
- Modify: `handlers/broadcast.py`

- [ ] **Step 1: Добавить handler `confirm_custom_broadcast`**

Добавить после `custom_text_received`:

```python
@router.callback_query(F.data == "bcast_confirm_custom", BroadcastState.confirming_custom)
async def confirm_custom_broadcast(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    text = data.get("custom_text", "")
    await state.clear()
    sent = await send_broadcast_text(callback.bot, text)
    if sent == 0:
        await callback.message.answer("Нет активных подписчиков.")
    else:
        await callback.message.answer(f"✅ Отправлено {sent} пользователям.")
    await callback.answer()
```

- [ ] **Step 2: Добавить handler `edit_custom_broadcast`**

Добавить после `confirm_custom_broadcast`:

```python
@router.callback_query(F.data == "bcast_edit_custom", BroadcastState.confirming_custom)
async def edit_custom_broadcast(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(BroadcastState.typing_custom)
    await callback.message.answer("Введите новый текст для рассылки:")
    await callback.answer()
```

- [ ] **Step 3: Добавить кнопку «✏️ Свой текст» в `select_specialization`**

В функции `select_specialization` найти блок с клавиатурой (около строки 116) и заменить:

```python
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✅ Отправить всем", callback_data="bcast_confirm")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="bcast_cancel")],
            ]
        ),
```

на:

```python
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✅ Отправить всем", callback_data="bcast_confirm")],
                [InlineKeyboardButton(text="✏️ Свой текст", callback_data="bcast_custom_start")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="bcast_cancel")],
            ]
        ),
```

- [ ] **Step 4: Прогнать весь suite — убедиться, что все 51 тест проходят**

```
python -m pytest --tb=short
```
Ожидаемый результат: `51 passed`

- [ ] **Step 5: Коммит**

```bash
git add handlers/broadcast.py
git commit -m "feat: add confirm/edit handlers and 'custom text' button to broadcast preview"
```

---

## Итоговая проверка

После всех задач:

```
python -m pytest -v
```

Ожидаемый результат: **51 passed** (44 существующих + 7 новых)

Финальная структура `BroadcastState`:
```
confirming        — авто-превью (существующее)
typing_custom     — ожидание ввода текста от админа (новое)
confirming_custom — превью кастомного текста (новое)
```

Полный UX-поток для кастомного текста:
```
select_specialization → [✏️ Свой текст]
    → bcast_custom_start → "Введите текст для рассылки:"
    → custom_text_received (валидация) → превью с кнопками
    → bcast_confirm_custom → send_broadcast_text → "✅ Отправлено N пользователям."
       bcast_edit_custom   → "Введите новый текст для рассылки:"
       bcast_cancel        → "Рассылка отменена."
```
