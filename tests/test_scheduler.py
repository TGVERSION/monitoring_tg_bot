import pytest
from unittest.mock import AsyncMock, patch
from datetime import date


def _spec_row():
    return {
        "specialization": "Хирургия",
        "net_change": 500.0,
        "sum_old_price": 5000.0,
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


@pytest.mark.asyncio
async def test_skip_when_no_data_in_db():
    with patch("scheduler.get_last_processed_date", new_callable=AsyncMock) as m_last, \
         patch("scheduler.get_max_insert_date", new_callable=AsyncMock) as m_max:
        m_last.return_value = date(2026, 4, 20)
        m_max.return_value = None
        bot = AsyncMock()
        from scheduler import send_weekly_report
        await send_weekly_report(bot)
        bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_skip_when_no_new_rows():
    with patch("scheduler.get_last_processed_date", new_callable=AsyncMock) as m_last, \
         patch("scheduler.get_max_insert_date", new_callable=AsyncMock) as m_max:
        m_last.return_value = date(2026, 4, 27)
        m_max.return_value = date(2026, 4, 27)
        bot = AsyncMock()
        from scheduler import send_weekly_report
        await send_weekly_report(bot)
        bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_skip_when_no_specialization_data():
    with patch("scheduler.get_last_processed_date", new_callable=AsyncMock) as m_last, \
         patch("scheduler.get_max_insert_date", new_callable=AsyncMock) as m_max, \
         patch("scheduler.get_top_specialization", new_callable=AsyncMock) as m_spec:
        m_last.return_value = date(2026, 4, 20)
        m_max.return_value = date(2026, 4, 27)
        m_spec.return_value = None
        bot = AsyncMock()
        from scheduler import send_weekly_report
        await send_weekly_report(bot)
        bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_sends_report_to_all_active_users():
    with patch("scheduler.get_last_processed_date", new_callable=AsyncMock) as m_last, \
         patch("scheduler.get_max_insert_date", new_callable=AsyncMock) as m_max, \
         patch("scheduler.get_top_specialization", new_callable=AsyncMock) as m_spec, \
         patch("scheduler.get_top_service_per_org", new_callable=AsyncMock) as m_svc, \
         patch("scheduler.get_active_users", new_callable=AsyncMock) as m_users, \
         patch("scheduler.update_last_processed_date", new_callable=AsyncMock) as m_update:
        m_last.return_value = date(2026, 4, 20)
        m_max.return_value = date(2026, 4, 27)
        m_spec.return_value = _spec_row()
        m_svc.return_value = _services()
        m_users.return_value = [
            {"telegram_id": 111},
            {"telegram_id": 222},
        ]
        bot = AsyncMock()
        from scheduler import send_weekly_report
        await send_weekly_report(bot)
        assert bot.send_message.call_count == 2
        assert bot.send_message.call_args_list[0][0][0] == 111
        assert bot.send_message.call_args_list[1][0][0] == 222
        m_update.assert_called_once_with(date(2026, 4, 27))


@pytest.mark.asyncio
async def test_all_users_get_same_message():
    with patch("scheduler.get_last_processed_date", new_callable=AsyncMock) as m_last, \
         patch("scheduler.get_max_insert_date", new_callable=AsyncMock) as m_max, \
         patch("scheduler.get_top_specialization", new_callable=AsyncMock) as m_spec, \
         patch("scheduler.get_top_service_per_org", new_callable=AsyncMock) as m_svc, \
         patch("scheduler.get_active_users", new_callable=AsyncMock) as m_users, \
         patch("scheduler.update_last_processed_date", new_callable=AsyncMock):
        m_last.return_value = date(2026, 4, 20)
        m_max.return_value = date(2026, 4, 27)
        m_spec.return_value = _spec_row()
        m_svc.return_value = _services()
        m_users.return_value = [{"telegram_id": 111}, {"telegram_id": 222}]
        bot = AsyncMock()
        from scheduler import send_weekly_report
        await send_weekly_report(bot)
        msg1 = bot.send_message.call_args_list[0][0][1]
        msg2 = bot.send_message.call_args_list[1][0][1]
        assert msg1 == msg2


@pytest.mark.asyncio
async def test_continues_after_single_user_error():
    with patch("scheduler.get_last_processed_date", new_callable=AsyncMock) as m_last, \
         patch("scheduler.get_max_insert_date", new_callable=AsyncMock) as m_max, \
         patch("scheduler.get_top_specialization", new_callable=AsyncMock) as m_spec, \
         patch("scheduler.get_top_service_per_org", new_callable=AsyncMock) as m_svc, \
         patch("scheduler.get_active_users", new_callable=AsyncMock) as m_users, \
         patch("scheduler.update_last_processed_date", new_callable=AsyncMock):
        m_last.return_value = date(2026, 4, 20)
        m_max.return_value = date(2026, 4, 27)
        m_spec.return_value = _spec_row()
        m_svc.return_value = _services()
        m_users.return_value = [{"telegram_id": 111}, {"telegram_id": 222}]
        bot = AsyncMock()
        bot.send_message.side_effect = [Exception("Telegram error"), None]
        from scheduler import send_weekly_report
        await send_weekly_report(bot)
        assert bot.send_message.call_count == 2


@pytest.mark.asyncio
async def test_deactivates_user_when_bot_blocked():
    with patch("scheduler.get_last_processed_date", new_callable=AsyncMock) as m_last, \
         patch("scheduler.get_max_insert_date", new_callable=AsyncMock) as m_max, \
         patch("scheduler.get_top_specialization", new_callable=AsyncMock) as m_spec, \
         patch("scheduler.get_top_service_per_org", new_callable=AsyncMock) as m_svc, \
         patch("scheduler.get_active_users", new_callable=AsyncMock) as m_users, \
         patch("scheduler.update_last_processed_date", new_callable=AsyncMock), \
         patch("scheduler.deactivate_user", new_callable=AsyncMock) as m_deactivate:
        m_last.return_value = date(2026, 4, 20)
        m_max.return_value = date(2026, 4, 27)
        m_spec.return_value = _spec_row()
        m_svc.return_value = _services()
        m_users.return_value = [{"telegram_id": 111}]
        bot = AsyncMock()
        bot.send_message.side_effect = Exception("Forbidden: bot was blocked by the user")
        from scheduler import send_weekly_report
        await send_weekly_report(bot)
        m_deactivate.assert_called_once_with(111)
