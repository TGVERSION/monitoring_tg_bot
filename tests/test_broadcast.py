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
