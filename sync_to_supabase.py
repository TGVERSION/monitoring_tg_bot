"""
Sync price_monitoring from local PostgreSQL to Supabase.

Strategy: delete rows from Supabase for the last SYNC_DAYS days,
then re-insert fresh data from local DB. Handles both INSERT and UPDATE.
"""
import logging
import os
import sys
import time as _time
from dataclasses import dataclass, field
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

SYNC_COLUMNS = [
    "ExternalId", "OrganizationName", "GroupName", "SubGroupName", "ServiceName",
    "Price", "InsertDate", "NonNormalizedPrice", "reference_serv", "PriceDifference",
    "PriceHandlerSkip", "type_reception", "specialization", "type_reception_skip",
    "specialization_skip", "type_filial", "type_filial_skip", "type_group", "type_group_skip",
]


@dataclass
class SyncProgress:
    sync_days: int = 0
    since: date | None = None
    total: int = 0
    inserted: int = 0
    deleted: int = 0
    # phase: "init" | "deleting" | "inserting" | "done" | "error"
    phase: str = "init"
    error: str | None = None
    started_at: float = field(default_factory=_time.time)


def _local_conn():
    return psycopg2.connect(
        host=os.environ["LOCAL_DB_HOST"],
        port=int(os.getenv("LOCAL_DB_PORT", "5432")),
        dbname=os.environ["LOCAL_DB_NAME"],
        user=os.environ["LOCAL_DB_USER"],
        password=os.environ["LOCAL_DB_PASSWORD"],
    )


def sync(progress: SyncProgress | None = None) -> int:
    if progress is None:
        progress = SyncProgress()

    since = date.today() - timedelta(days=SYNC_DAYS)
    progress.sync_days = SYNC_DAYS
    progress.since = since
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
        progress.total = local_count
        logger.info("Local rows in window: %d", local_count)

        progress.phase = "deleting"
        supa_cur.execute(
            'DELETE FROM price_monitoring WHERE "InsertDate" >= %s', (since,)
        )
        deleted = supa_cur.rowcount
        supa_conn.commit()
        progress.deleted = deleted
        logger.info("Deleted %d rows from Supabase", deleted)

        progress.phase = "inserting"
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
            progress.inserted = inserted
            logger.info("Progress: %d / %d rows inserted", inserted, local_count)

    progress.phase = "done"
    logger.info("Sync complete. Inserted %d rows total.", inserted)
    return inserted


if __name__ == "__main__":
    try:
        sync()
    except Exception:
        logger.exception("Sync failed")
        sys.exit(1)
