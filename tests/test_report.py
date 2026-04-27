from datetime import date
from report import build_report


def spec(specialization, net_change, sum_old_price):
    return {
        "specialization": specialization,
        "net_change": net_change,
        "sum_old_price": sum_old_price,
    }


def svc(org, service, price, diff):
    return {
        "OrganizationName": org,
        "ServiceName": service,
        "Price": price,
        "PriceDifference": diff,
    }


def test_returns_none_when_spec_row_is_none():
    assert build_report(None, [svc("Клиника А", "УЗИ", 1000.0, 100.0)], date(2026, 4, 27)) is None


def test_returns_none_when_no_services():
    assert build_report(spec("Хирургия", 500.0, 5000.0), [], date(2026, 4, 27)) is None


def test_trend_up_when_net_change_positive():
    result = build_report(spec("Хирургия", 500.0, 5000.0), [svc("Клиника А", "УЗИ", 1000.0, 100.0)], date(2026, 4, 27))
    assert "⬆️" in result
    assert "повышают" in result


def test_trend_down_when_net_change_negative():
    result = build_report(spec("Хирургия", -500.0, 5000.0), [svc("Клиника А", "УЗИ", 900.0, -100.0)], date(2026, 4, 27))
    assert "⬇️" in result
    assert "снижают" in result


def test_specialization_name_in_output():
    result = build_report(spec("Кардиология", 200.0, 2000.0), [svc("Клиника А", "ЭКГ", 500.0, 50.0)], date(2026, 4, 27))
    assert "Кардиология" in result


def test_avg_pct_positive():
    # net=500, sum_old=5000 → +10.0%
    result = build_report(spec("Хирургия", 500.0, 5000.0), [svc("Клиника А", "УЗИ", 1100.0, 100.0)], date(2026, 4, 27))
    assert "+10.0%" in result


def test_avg_pct_negative():
    # net=-500, sum_old=5000 → -10.0%
    result = build_report(spec("Хирургия", -500.0, 5000.0), [svc("Клиника А", "УЗИ", 900.0, -100.0)], date(2026, 4, 27))
    assert "-10.0%" in result


def test_service_line_contains_org_and_service():
    result = build_report(
        spec("Хирургия", 100.0, 1000.0),
        [svc("Клиника Альфа", "Аппендэктомия", 15000.0, 500.0)],
        date(2026, 4, 27),
    )
    assert "Клиника Альфа" in result
    assert "Аппендэктомия" in result
    assert "15000₽" in result


def test_service_pct_up():
    # price=1100, diff=100 → old=1000 → +10.0%
    result = build_report(
        spec("Хирургия", 100.0, 1000.0),
        [svc("Клиника А", "УЗИ", 1100.0, 100.0)],
        date(2026, 4, 27),
    )
    assert "+10.0%" in result


def test_service_pct_down():
    # price=900, diff=-100 → old=1000 → -10.0%
    result = build_report(
        spec("Хирургия", -100.0, 1000.0),
        [svc("Клиника А", "УЗИ", 900.0, -100.0)],
        date(2026, 4, 27),
    )
    assert "-10.0%" in result


def test_multiple_orgs_all_shown():
    services = [
        svc("Клиника А", "УЗИ", 1100.0, 100.0),
        svc("Клиника Б", "МРТ", 5500.0, 500.0),
        svc("Клиника В", "Анализ крови", 330.0, 30.0),
    ]
    result = build_report(spec("Хирургия", 630.0, 6000.0), services, date(2026, 4, 27))
    assert "Клиника А" in result
    assert "Клиника Б" in result
    assert "Клиника В" in result


def test_section_header_present():
    result = build_report(spec("Хирургия", 100.0, 1000.0), [svc("Клиника А", "УЗИ", 1100.0, 100.0)], date(2026, 4, 27))
    assert "Услуги с наибольшими изменениями" in result


def test_zero_sum_old_price_does_not_crash():
    result = build_report(spec("Хирургия", 0.0, 0.0), [svc("Клиника А", "УЗИ", 1000.0, 0.0)], date(2026, 4, 27))
    assert result is not None
    assert "0.0%" in result
