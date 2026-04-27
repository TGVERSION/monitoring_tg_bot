import asyncio

import asyncpg
from datetime import date as date_type

from config import DATABASE_URL

ALLOWED_FILTER_FIELDS = {
    "GroupName", "SubGroupName", "ServiceName",
    "type_reception", "specialization", "type_filial", "type_group",
}

_pool = None
_pool_lock = asyncio.Lock()


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        async with _pool_lock:
            if _pool is None:
                _pool = await asyncpg.create_pool(DATABASE_URL)
    return _pool


async def get_organization_by_inn(inn: str):
    pool = await get_pool()
    return await pool.fetchrow(
        "SELECT * FROM organizations WHERE inn = $1", inn
    )


async def get_user_by_telegram_id(telegram_id: int):
    pool = await get_pool()
    return await pool.fetchrow(
        "SELECT * FROM bot_users WHERE telegram_id = $1", telegram_id
    )


async def register_user(telegram_id: int, inn: str):
    pool = await get_pool()
    await pool.execute(
        """
        INSERT INTO bot_users (telegram_id, inn)
        VALUES ($1, $2)
        ON CONFLICT (telegram_id) DO UPDATE SET inn = $2, is_active = true
        """,
        telegram_id, inn,
    )


async def deactivate_user(telegram_id: int):
    pool = await get_pool()
    await pool.execute(
        "UPDATE bot_users SET is_active = false WHERE telegram_id = $1",
        telegram_id,
    )


async def get_active_users() -> list:
    pool = await get_pool()
    return await pool.fetch(
        """
        SELECT bu.telegram_id, o.organization_name
        FROM bot_users bu
        JOIN organizations o ON bu.inn = o.inn
        WHERE bu.is_active = true
        """
    )


async def get_all_bot_users() -> list:
    pool = await get_pool()
    return await pool.fetch(
        """
        SELECT bu.telegram_id, bu.registered_at, bu.is_active,
               o.organization_name, o.inn
        FROM bot_users bu
        JOIN organizations o ON bu.inn = o.inn
        ORDER BY bu.registered_at DESC
        """
    )


async def get_last_processed_date():
    pool = await get_pool()
    row = await pool.fetchrow("SELECT last_processed_date FROM report_state LIMIT 1")
    return row["last_processed_date"] if row else None


async def get_max_insert_date():
    pool = await get_pool()
    row = await pool.fetchrow(
        'SELECT MAX("InsertDate") AS max_date FROM price_monitoring'
    )
    return row["max_date"] if row else None


async def update_last_processed_date(new_date) -> None:
    pool = await get_pool()
    updated = await pool.execute(
        "UPDATE report_state SET last_processed_date = $1",
        new_date,
    )
    if updated == "UPDATE 0":
        await pool.execute(
            "INSERT INTO report_state (last_processed_date) VALUES ($1)",
            new_date,
        )


async def get_active_filters() -> list:
    pool = await get_pool()
    return await pool.fetch(
        "SELECT field_name, field_value FROM admin_filters WHERE is_active = true"
    )


async def get_all_filters() -> list:
    pool = await get_pool()
    return await pool.fetch(
        "SELECT id, field_name, field_value, is_active FROM admin_filters ORDER BY id"
    )


async def add_filter(field_name: str, field_value: str) -> None:
    pool = await get_pool()
    await pool.execute(
        "INSERT INTO admin_filters (field_name, field_value) VALUES ($1, $2)",
        field_name, field_value,
    )


async def delete_filter(filter_id: int) -> None:
    pool = await get_pool()
    await pool.execute("DELETE FROM admin_filters WHERE id = $1", filter_id)


async def get_all_organizations() -> list:
    pool = await get_pool()
    return await pool.fetch(
        "SELECT inn, organization_name FROM organizations ORDER BY organization_name"
    )


async def add_organization(inn: str, organization_name: str) -> None:
    pool = await get_pool()
    await pool.execute(
        "INSERT INTO organizations (inn, organization_name) VALUES ($1, $2)",
        inn, organization_name,
    )


async def get_price_data_for_org(
    organization_name: str, filters: list, last_date
) -> list:
    pool = await get_pool()

    fallback = date_type(1900, 1, 1)
    since = last_date if last_date is not None else fallback

    if not filters:
        return await pool.fetch(
            """
            SELECT "GroupName", "Price", "PriceDifference"
            FROM price_monitoring
            WHERE "OrganizationName" = $1 AND "InsertDate" > $2
            """,
            organization_name, since,
        )

    or_clauses = []
    params = [organization_name, since]
    for i, f in enumerate(filters, start=3):
        if f["field_name"] not in ALLOWED_FILTER_FIELDS:
            raise ValueError(f"Disallowed filter field: {f['field_name']!r}")
        or_clauses.append(f'"{f["field_name"]}" = ${i}')
        params.append(f["field_value"])

    query = f"""
        SELECT "GroupName", "Price", "PriceDifference"
        FROM price_monitoring
        WHERE "OrganizationName" = $1
          AND "InsertDate" > $2
          AND ({" OR ".join(or_clauses)})
    """
    return await pool.fetch(query, *params)
