"""
Sync price_monitoring from local PostgreSQL to Supabase.

Strategy: delete rows from Supabase for the last SYNC_DAYS days,
then re-insert fresh data from local DB. Handles both INSERT and UPDATE.
"""
import logging
import os
import sys
from datetime import date, timedelta

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

_log_dir = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(_log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(_log_dir, "sync_supabase.log"), encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

SUPABASE_DSN = os.environ["DATABASE_URL"]
SYNC_DAYS = int(os.getenv("SYNC_DAYS", "60"))
BATCH_SIZE = int(os.getenv("SYNC_BATCH_SIZE", "500"))

# Columns to sync (excludes local Id — Supabase generates its own)
SYNC_COLUMNS = [
    "ExternalId", "OrganizationName", "GroupName", "SubGroupName", "ServiceName",
    "Price", "InsertDate", "NonNormalizedPrice", "reference_serv", "PriceDifference",
    "PriceHandlerSkip", "type_reception", "specialization", "type_reception_skip",
    "specialization_skip", "type_filial", "type_filial_skip", "type_group", "type_group_skip",
]


def _local_conn():
    return psycopg2.connect(
        host=os.environ["LOCAL_DB_HOST"],
        port=int(os.getenv("LOCAL_DB_PORT", "5432")),
        dbname=os.environ["LOCAL_DB_NAME"],
        user=os.environ["LOCAL_DB_USER"],
        password=os.environ["LOCAL_DB_PASSWORD"],
    )


def sync():
    since = date.today() - timedelta(days=SYNC_DAYS)
    logger.info("Starting sync: last %d days (from %s)", SYNC_DAYS, since)

    col_list = ", ".join(f'"{c}"' for c in SYNC_COLUMNS)
    placeholders = ", ".join("%s" for _ in SYNC_COLUMNS)

    with _local_conn() as local_conn, psycopg2.connect(SUPABASE_DSN) as supa_conn:
        local_cur = local_conn.cursor()
        supa_cur = supa_conn.cursor()

        local_cur.execute(
            'SELECT COUNT(*) FROM price_monitoring WHERE "InsertDate" >= %s', (since,)
        )
        local_count = local_cur.fetchone()[0]
        logger.info("Local rows in window: %d", local_count)

        supa_cur.execute(
            'DELETE FROM price_monitoring WHERE "InsertDate" >= %s', (since,)
        )
        deleted = supa_cur.rowcount
        supa_conn.commit()
        logger.info("Deleted %d rows from Supabase", deleted)

        local_cur.execute(
            f'SELECT {col_list} FROM price_monitoring WHERE "InsertDate" >= %s ORDER BY "InsertDate"',
            (since,),
        )

        inserted = 0
        while True:
            rows = local_cur.fetchmany(BATCH_SIZE)
            if not rows:
                break
            psycopg2.extras.execute_batch(
                supa_cur,
                f'INSERT INTO price_monitoring ({col_list}) VALUES ({placeholders})',
                rows,
                page_size=BATCH_SIZE,
            )
            supa_conn.commit()
            inserted += len(rows)
            logger.info("Progress: %d / %d rows inserted", inserted, local_count)

    logger.info("Sync complete. Inserted %d rows total.", inserted)


if __name__ == "__main__":
    try:
        sync()
    except Exception:
        logger.exception("Sync failed")
        sys.exit(1)
