from datetime import date
from report import build_report


def row(group, price, diff):
    return {"GroupName": group, "Price": price, "PriceDifference": diff}


def test_returns_none_for_empty_rows():
    assert build_report("Клиника", [], date(2026, 4, 27)) is None


def test_header_contains_org_name_and_date():
    result = build_report("Клиника Альфа", [row("Анализы", 1000.0, 0)], date(2026, 4, 27))
    assert "Клиника Альфа" in result
    assert "27.04.2026" in result


def test_groups_services_by_group_name():
    rows = [row("Анализы", 1000.0, 0), row("Анализы", 800.0, 0), row("Консультации", 2000.0, 0)]
    result = build_report("Клиника", rows, date(2026, 4, 27))
    assert "Анализы" in result
    assert "Консультации" in result


def test_shows_service_count():
    rows = [row("Анализы", 1000.0, 0), row("Анализы", 800.0, 0)]
    result = build_report("Клиника", rows, date(2026, 4, 27))
    assert "2 усл." in result


def test_no_change_shows_label():
    result = build_report("Клиника", [row("Анализы", 1000.0, 0)], date(2026, 4, 27))
    assert "без изм." in result


def test_positive_percent():
    # old = 1000, new = 1100, diff = +100 → +10%
    result = build_report("Клиника", [row("Анализы", 1100.0, 100)], date(2026, 4, 27))
    assert "+10.0%" in result


def test_negative_percent():
    # old = 1000, new = 900, diff = -100 → -10%
    result = build_report("Клиника", [row("Анализы", 900.0, -100)], date(2026, 4, 27))
    assert "-10.0%" in result


def test_none_group_name_falls_back_to_prochee():
    result = build_report("Клиника", [row(None, 500.0, 0)], date(2026, 4, 27))
    assert "Прочее" in result


def test_none_price_difference_treated_as_zero():
    result = build_report("Клиника", [row("Анализы", 1000.0, None)], date(2026, 4, 27))
    assert "без изм." in result
