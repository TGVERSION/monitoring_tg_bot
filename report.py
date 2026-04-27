from datetime import date


def build_report(spec_row, services: list, report_date: date) -> str | None:
    if spec_row is None or not services:
        return None

    net_change = float(spec_row["net_change"] or 0)
    sum_old_price = float(spec_row["sum_old_price"] or 0)
    avg_pct = round(net_change / sum_old_price * 100, 1) if sum_old_price else 0.0

    trend_emoji = "⬆️" if net_change > 0 else "⬇️"
    trend_word = "повышают" if net_change > 0 else "снижают"
    pct_sign = "+" if avg_pct > 0 else ""

    lines = [
        f"Конкуренты {trend_emoji} {trend_word} цены",
        "",
        f"Специализация: {spec_row['specialization']} ({pct_sign}{avg_pct:.1f}% к прошлому периоду)",
        "",
        "Услуги с наибольшими изменениями у этой специализации:",
    ]

    for svc in services:
        diff = float(svc["PriceDifference"] or 0)
        price = float(svc["Price"])
        old_price = price - diff
        svc_pct = round(diff / old_price * 100, 1) if old_price else 0.0
        svc_emoji = "⬆️" if diff > 0 else "⬇️"
        svc_sign = "+" if svc_pct > 0 else ""
        lines.append(
            f"{svc_emoji} {svc['OrganizationName']} - {svc['ServiceName']}"
            f" — {price:.0f}₽ ({svc_sign}{svc_pct:.1f}%)"
        )

    return "\n".join(lines)
