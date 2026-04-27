import pytest
from unittest.mock import AsyncMock, patch
from datetime import date


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
async def test_sends_report_when_new_rows_exist():
    with patch("scheduler.get_last_processed_date", new_callable=AsyncMock) as m_last, \
         patch("scheduler.get_max_insert_date", new_callable=AsyncMock) as m_max, \
         patch("scheduler.get_active_users", new_callable=AsyncMock) as m_users, \
         patch("scheduler.get_active_filters", new_callable=AsyncMock) as m_filters, \
         patch("scheduler.get_price_data_for_org", new_callable=AsyncMock) as m_data, \
         patch("scheduler.update_last_processed_date", new_callable=AsyncMock) as m_update:
        m_last.return_value = date(2026, 4, 20)
        m_max.return_value = date(2026, 4, 27)
        m_users.return_value = [
            {"telegram_id": 111, "organization_name": "Клиника Альфа"}
        ]
        m_filters.return_value = []
        m_data.return_value = [
            {"GroupName": "Анализы", "Price": 1000.0, "PriceDifference": 0}
        ]
        bot = AsyncMock()
        from scheduler import send_weekly_report
        await send_weekly_report(bot)
        bot.send_message.assert_called_once()
        assert bot.send_message.call_args[0][0] == 111
        m_update.assert_called_once_with(date(2026, 4, 27))


@pytest.mark.asyncio
async def test_continues_after_single_user_error():
    with patch("scheduler.get_last_processed_date", new_callable=AsyncMock) as m_last, \
         patch("scheduler.get_max_insert_date", new_callable=AsyncMock) as m_max, \
         patch("scheduler.get_active_users", new_callable=AsyncMock) as m_users, \
         patch("scheduler.get_active_filters", new_callable=AsyncMock) as m_filters, \
         patch("scheduler.get_price_data_for_org", new_callable=AsyncMock) as m_data, \
         patch("scheduler.update_last_processed_date", new_callable=AsyncMock):
        m_last.return_value = date(2026, 4, 20)
        m_max.return_value = date(2026, 4, 27)
        m_users.return_value = [
            {"telegram_id": 111, "organization_name": "Клиника Альфа"},
            {"telegram_id": 222, "organization_name": "Клиника Бета"},
        ]
        m_filters.return_value = []
        m_data.return_value = [
            {"GroupName": "Анализы", "Price": 1000.0, "PriceDifference": 0}
        ]
        bot = AsyncMock()
        bot.send_message.side_effect = [Exception("Telegram error"), None]
        from scheduler import send_weekly_report
        await send_weekly_report(bot)
        assert bot.send_message.call_count == 2


@pytest.mark.asyncio
async def test_skips_user_with_empty_report():
    with patch("scheduler.get_last_processed_date", new_callable=AsyncMock) as m_last, \
         patch("scheduler.get_max_insert_date", new_callable=AsyncMock) as m_max, \
         patch("scheduler.get_active_users", new_callable=AsyncMock) as m_users, \
         patch("scheduler.get_active_filters", new_callable=AsyncMock) as m_filters, \
         patch("scheduler.get_price_data_for_org", new_callable=AsyncMock) as m_data, \
         patch("scheduler.update_last_processed_date", new_callable=AsyncMock):
        m_last.return_value = date(2026, 4, 20)
        m_max.return_value = date(2026, 4, 27)
        m_users.return_value = [{"telegram_id": 111, "organization_name": "Клиника Альфа"}]
        m_filters.return_value = []
        m_data.return_value = []
        bot = AsyncMock()
        from scheduler import send_weekly_report
        await send_weekly_report(bot)
        bot.send_message.assert_not_called()
