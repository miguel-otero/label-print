"""Shared connection and transaction coordination for queue maintenance."""
import psycopg
from psycopg.rows import dict_row

from app.settings import Settings

# Queue mutations take a shared transaction lock; each purge batch takes exclusive.
# Separate from the session lock that elects a single maintenance runner.
QUEUE_LOCK = 749812001
RETENTION_LOCK = 749812002


def connect(settings: Settings) -> psycopg.Connection:
    return psycopg.connect(
        host=settings.database_host, port=settings.database_port,
        dbname=settings.database_name, user=settings.database_user,
        password=settings.database_password, row_factory=dict_row,
    )


def queue_transaction(conn: psycopg.Connection) -> None:
    conn.execute("select pg_advisory_xact_lock_shared(%s)", (QUEUE_LOCK,))
