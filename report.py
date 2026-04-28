from datetime import date

SEP = "━━━━━━━━━━━━━━━"
_ANALYTICS_URL = (
    "https://analytic.vismuth.ru/superset/dashboard/1/"
    "?native_filters_key=5jlp9immVU61iAY-zTzq05vtIM60Sv-Z_DuCP9JHBjc37fuwCgu4oRNp5Btxl270"
)
FOOTER = (
    f"\n{SEP}\n"
    f'🟣 Хотите узнать больше? <a href="{_ANALYTICS_URL}">Полный отчёт на сайте аналитики</a>'
)


def _fmt_price(price: float) -> str:
    return f"{int(price):,}".replace(",", " ")


def build_report(spec_row, services: list, report_date: date) -> str | None:
    if spec_row is None or not services:
        return None

    net_change = float(spec_row["net_change"] or 0)
    sum_old_price = float(spec_row["sum_old_price"] or 0)
    avg_pct = round(net_change / sum_old_price * 100, 1) if sum_old_price else 0.0
    pct_sign = "+" if avg_pct > 0 else ""

    up_items = []   # (abs_pct, line)
    down_items = []
    for svc in services:
        diff = float(svc["PriceDifference"] or 0)
        if diff == 0:
            continue
        price = float(svc["Price"])
        old_price = price - diff
        svc_pct = round(diff / old_price * 100, 1) if old_price else 0.0
        svc_sign = "+" if svc_pct > 0 else ""
        line = (
            f"{'🔺' if diff > 0 else '🔻'} <b>{svc['OrganizationName']}</b>:"
            f" {svc['ServiceName']} 💰 {_fmt_price(price)} ₽ ({svc_sign}{svc_pct:.1f}%)"
        )
        if diff > 0:
            up_items.append((abs(svc_pct), line))
        else:
            down_items.append((abs(svc_pct), line))

    up_items.sort(key=lambda x: x[0], reverse=True)
    down_items.sort(key=lambda x: x[0], reverse=True)
    up_lines = [line for _, line in up_items]
    down_lines = [line for _, line in down_items]

    if not up_lines and not down_lines:
        return None

    parts = [
        "📊 <b>Еженедельный отчёт по ценам конкурентов</b>",
        SEP,
        f"🏥 <b>Специализация: {spec_row['specialization']} | {pct_sign}{avg_pct:.1f}%</b>",
        "",
    ]

    if up_lines:
        parts += [SEP, "📈 Повысили цены", SEP] + up_lines

    if down_lines:
        if up_lines:
            parts.append("")
        parts += [SEP, "📉 Снизили цены", SEP] + down_lines

    return "\n".join(parts) + FOOTER
