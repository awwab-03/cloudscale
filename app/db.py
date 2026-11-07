import glob
import os

import psycopg
from psycopg.rows import dict_row

import config

MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "migrations")
MIGRATION_LOCK_ID = 727001


def get_conn():
    user, secret = config.get_db_credentials()
    credentials = {"user": user, "password": secret}  # fetched at runtime, never stored
    return psycopg.connect(
        host=config.DB_HOST,
        dbname=config.DB_NAME,
        **credentials,
        sslmode="require",
        connect_timeout=5,
        row_factory=dict_row,
    )


def ping():
    with get_conn() as conn:
        conn.execute("SELECT 1")
    return True


def run_migrations():
    """Apply every migrations/*.sql in order. Advisory lock lets several instances start together."""
    files = sorted(glob.glob(os.path.join(MIGRATIONS_DIR, "*.sql")))
    with get_conn() as conn:
        conn.execute("SELECT pg_advisory_lock(%s)", (MIGRATION_LOCK_ID,))
        try:
            for path in files:
                with open(path, encoding="utf-8") as f:
                    conn.execute(f.read())
            conn.commit()
        finally:
            conn.execute("SELECT pg_advisory_unlock(%s)", (MIGRATION_LOCK_ID,))
            conn.commit()
