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
    assert "🔺" in result
    assert "Повысили цены" in result


def test_trend_down_when_net_change_negative():
    result = build_report(spec("Хирургия", -500.0, 5000.0), [svc("Клиника А", "УЗИ", 900.0, -100.0)], date(2026, 4, 27))
    assert "🔻" in result
    assert "Снизили цены" in result


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
    assert "15 000 ₽" in result
    assert "💰" in result


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
    assert "Повысили цены" in result


def test_zero_diff_service_is_skipped():
    result = build_report(spec("Хирургия", 100.0, 1000.0), [svc("Клиника А", "УЗИ", 1000.0, 0.0)], date(2026, 4, 27))
    assert result is None


def test_returns_none_when_all_services_have_zero_diff():
    services = [svc("Клиника А", "УЗИ", 1000.0, 0.0), svc("Клиника Б", "МРТ", 2000.0, 0.0)]
    assert build_report(spec("Хирургия", 0.0, 0.0), services, date(2026, 4, 27)) is None


def test_blank_line_in_output():
    services = [
        svc("Клиника А", "УЗИ", 1100.0, 100.0),
        svc("Клиника Б", "МРТ", 5500.0, 500.0),
    ]
    result = build_report(spec("Хирургия", 600.0, 6000.0), services, date(2026, 4, 27))
    assert "\n\n" in result


def test_up_and_down_sections_both_present():
    services = [
        svc("Клиника А", "УЗИ", 1100.0, 100.0),
        svc("Клиника Б", "МРТ", 900.0, -100.0),
    ]
    result = build_report(spec("Хирургия", 0.0, 2000.0), services, date(2026, 4, 27))
    assert "Повысили цены" in result
    assert "Снизили цены" in result


def test_org_name_is_bold():
    result = build_report(
        spec("Хирургия", 100.0, 1000.0),
        [svc("Клиника Альфа", "УЗИ", 1100.0, 100.0)],
        date(2026, 4, 27),
    )
    assert "<b>Клиника Альфа</b>" in result


def test_report_header_present():
    result = build_report(spec("Хирургия", 100.0, 1000.0), [svc("Клиника А", "УЗИ", 1100.0, 100.0)], date(2026, 4, 27))
    assert "Еженедельный отчёт по ценам конкурентов" in result


def test_up_services_sorted_by_abs_pct_descending():
    # Клиника Б: old=2000, diff=+600 → +30%
    # Клиника А: old=1000, diff=+100 → +10%
    # Клиника В: old=1000, diff=+50  → +5%
    # Переданы в обратном порядке — в отчёте должны идти Б → А → В
    services = [
        svc("Клиника А", "УЗИ", 1100.0, 100.0),
        svc("Клиника В", "Анализ", 1050.0, 50.0),
        svc("Клиника Б", "МРТ", 2600.0, 600.0),
    ]
    result = build_report(spec("Хирургия", 750.0, 4000.0), services, date(2026, 4, 27))
    assert result.index("Клиника Б") < result.index("Клиника А") < result.index("Клиника В")


def test_down_services_sorted_by_abs_pct_descending():
    # Клиника Б: old=2000, diff=-600 → -30%
    # Клиника А: old=1000, diff=-100 → -10%
    # Клиника В: old=1000, diff=-50  → -5%
    services = [
        svc("Клиника А", "УЗИ", 900.0, -100.0),
        svc("Клиника В", "Анализ", 950.0, -50.0),
        svc("Клиника Б", "МРТ", 1400.0, -600.0),
    ]
    result = build_report(spec("Хирургия", -750.0, 4000.0), services, date(2026, 4, 27))
    assert result.index("Клиника Б") < result.index("Клиника А") < result.index("Клиника В")


def test_footer_analytics_link_present():
    result = build_report(spec("Хирургия", 100.0, 1000.0), [svc("Клиника А", "УЗИ", 1100.0, 100.0)], date(2026, 4, 27))
    assert "analytic.vismuth.ru" in result
    assert "🟣" in result
    assert "Хотите узнать больше" in result


def test_mixed_up_down_each_section_sorted_by_abs_pct_descending():
    # Up: Клиника Б +30%, Клиника А +10%
    # Down: Клиника Г -30%, Клиника В -10%
    services = [
        svc("Клиника А", "УЗИ", 1100.0, 100.0),
        svc("Клиника Б", "МРТ", 2600.0, 600.0),
        svc("Клиника В", "Рентген", 900.0, -100.0),
        svc("Клиника Г", "КТ", 1400.0, -600.0),
    ]
    result = build_report(spec("Хирургия", 0.0, 6000.0), services, date(2026, 4, 27))
    assert result.index("Клиника Б") < result.index("Клиника А")
    assert result.index("Клиника Г") < result.index("Клиника В")
