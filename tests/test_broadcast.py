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
