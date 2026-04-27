from collections import defaultdict
from datetime import date


def build_report(organization_name: str, rows: list, report_date: date) -> str | None:
    if not rows:
        return None

    groups = defaultdict(list)
    for row in rows:
        key = row["GroupName"] or "Прочее"
        groups[key].append(row)

    lines = [f"📊 Обновление цен — {organization_name} ({report_date.strftime('%d.%m.%Y')})\n"]

    for group_name, services in sorted(groups.items()):
        count = len(services)
        prices = [s["Price"] for s in services if s["Price"] is not None]
        avg_price = sum(prices) / len(prices) if prices else 0

        total_diff = sum(s["PriceDifference"] or 0 for s in services)
        total_old = sum(
            (s["Price"] - (s["PriceDifference"] or 0))
            for s in services
            if s["Price"] is not None
        )

        if total_old > 0 and total_diff != 0:
            pct = round(total_diff / total_old * 100, 1)
            change = f"(+{pct}%)" if pct > 0 else f"({pct}%)"
        else:
            change = "(без изм.)"

        lines.append(f"▪️ {group_name} ({count} усл.): ср. цена {avg_price:.0f}₽ {change}")

    return "\n".join(lines)
