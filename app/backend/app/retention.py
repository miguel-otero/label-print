"""Calendar retention, bounded deletion and an independent background runner."""
import asyncio
import calendar
import logging
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb

from app.database import QUEUE_LOCK, RETENTION_LOCK, connect
from app.settings import Settings

logger = logging.getLogger(__name__)


def subtract_calendar_months(value: date, months: int) -> date:
    month = value.year * 12 + value.month - 1 - months
    year, month = divmod(month, 12)
    month += 1
    return date(year, month, min(value.day, calendar.monthrange(year, month)[1]))


def retention_cutoff(settings: Settings, now: datetime | None = None) -> datetime:
    zone = ZoneInfo(settings.retention_timezone)
    today = (now or datetime.now(timezone.utc)).astimezone(zone).date()
    return datetime.combine(
        subtract_calendar_months(today, settings.data_retention_months), time.min, zone,
    )


class RetentionService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _connect(self) -> psycopg.Connection:
        return connect(self.settings)

    def ensure_schema(self) -> None:
        if not self.settings.use_postgres:
            return
        with self._connect() as conn:
            conn.execute("""create table if not exists maintenance_state (
                name text primary key, value jsonb not null)""")
            conn.execute("create index if not exists print_jobs_retention_idx on print_jobs(retention_at)")

    def status(self) -> dict:
        result = {"enabled": self.settings.retention_enabled,
                  "months": self.settings.data_retention_months,
                  "interval_minutes": self.settings.retention_interval_minutes,
                  "cutoff": retention_cutoff(self.settings).isoformat(), "last_run": None}
        if self.settings.use_postgres:
            with self._connect() as conn:
                row = conn.execute("select value from maintenance_state where name = 'retention'").fetchone()
                result["last_run"] = row["value"] if row else None
        return result

    def diagnose(self) -> dict:
        cutoff = retention_cutoff(self.settings)
        result = {"cutoff": cutoff.isoformat(), "tables": {}, "protected_roots": 0}
        with self._connect() as conn:
            for table, column in ((self.settings.history_table, "timestamp"),
                                  ("print_batches", "timestamp"),
                                  ("print_jobs", "retention_at"),
                                  (self.settings.inventory_entries_table, "fecha")):
                row = conn.execute(sql.SQL("""
                    select count(*) as total, count(*) filter (where {} < %s) as expired,
                           min({}) as oldest, pg_total_relation_size(%s::regclass) as bytes
                    from {}
                """).format(sql.Identifier(column), sql.Identifier(column), sql.Identifier(table)),
                    (cutoff.date() if column == "fecha" else cutoff, table)).fetchone()
                row["oldest"] = row["oldest"].isoformat() if row["oldest"] else None
                result["tables"][table] = row
            result["protected_roots"] = conn.execute("""
                select count(distinct coalesce('h' || history_id, 'b' || batch_id, 'j' || id))
                       as total from print_jobs where retention_at < %s and status = 'processing'
            """, (cutoff,)).fetchone()["total"]
            result["autovacuum"] = conn.execute("show autovacuum").fetchone()["autovacuum"]
        return result

    def run_once(self, *, dry_run: bool = False) -> dict:
        if dry_run:
            return self.diagnose()
        if not self.settings.retention_enabled or not self.settings.use_postgres:
            return {"status": "disabled"}
        result = {"status": "running", "started_at": datetime.now(timezone.utc).isoformat(),
                  "cutoff": retention_cutoff(self.settings).isoformat(), "deleted": {}}
        cutoff = retention_cutoff(self.settings)
        with self._connect() as leader:
            leader.autocommit = True
            if not leader.execute("select pg_try_advisory_lock(%s) as acquired",
                                  (RETENTION_LOCK,)).fetchone()["acquired"]:
                return {"status": "busy"}
            try:
                # Import here to keep policy helpers usable by the queue.
                from app.print_queue import PrintQueueService
                queue = PrintQueueService(self.settings)
                queue._connect = self._connect
                queue.mark_stale_jobs()
                for table, relation in ((self.settings.history_table, "history_id"),
                                        ("print_batches", "batch_id"), ("print_jobs", None),
                                        (self.settings.inventory_entries_table, "entries")):
                    while True:
                        with self._connect() as conn:
                            conn.execute("select pg_advisory_xact_lock(%s)", (QUEUE_LOCK,))
                            count = self._delete_batch(conn, table, relation, cutoff, result["deleted"])
                        if count == 0:
                            break
                result["status"] = "success"
            except Exception as exc:
                # Do not persist exception strings that may include connection credentials.
                result.update(status="error", error=type(exc).__name__)
                logger.error("Retention failed: %s", type(exc).__name__)
            finally:
                result["finished_at"] = datetime.now(timezone.utc).isoformat()
                try:
                    leader.execute("""insert into maintenance_state(name, value) values ('retention', %s)
                        on conflict(name) do update set value = excluded.value""", (Jsonb(result),))
                finally:
                    leader.execute("select pg_advisory_unlock(%s)", (RETENTION_LOCK,))
        return result

    def _delete_batch(
        self, conn: psycopg.Connection, table: str, relation: str | None,
        cutoff: datetime, totals: dict[str, int],
    ) -> int:
        identifier = sql.Identifier(table)
        if relation == "entries":
            key, condition, value = "id_inventory_entries", sql.SQL("fecha < %s"), cutoff.date()
        elif relation is None:
            key, value = "id", cutoff
            condition = sql.SQL("""retention_at < %s and status <> 'processing'
                and not exists (select 1 from {} h where h.id = root.history_id)
                and not exists (select 1 from print_batches b where b.id = root.batch_id)
            """).format(sql.Identifier(self.settings.history_table))
        else:
            key, value = "id", cutoff
            condition = sql.SQL("""timestamp < %s and not exists (
                select 1 from print_jobs j where j.{} = root.id and j.status = 'processing'
            )""").format(sql.Identifier(relation))
        rows = conn.execute(sql.SQL("""
            select {} as id from {} root where {} order by {} limit %s for update
        """).format(sql.Identifier(key), identifier, condition, sql.Identifier(key)),
            (value, self.settings.retention_batch_size)).fetchall()
        ids = [row["id"] for row in rows]
        if not ids:
            return 0
        if relation not in (None, "entries"):
            jobs = conn.execute(sql.SQL("select id from print_jobs where {} = any(%s)").format(
                sql.Identifier(relation)), (ids,)).fetchall()
            job_ids = [row["id"] for row in jobs]
        else:
            job_ids = ids if relation is None else []
        if job_ids:
            docs = conn.execute("delete from print_job_documents where job_id = any(%s)", (job_ids,)).rowcount
            jobs = conn.execute("delete from print_jobs where id = any(%s)", (job_ids,)).rowcount
            totals["print_job_documents"] = totals.get("print_job_documents", 0) + docs
            totals["print_jobs"] = totals.get("print_jobs", 0) + jobs
        if relation == "batch_id":
            count = conn.execute("delete from print_batch_items where batch_id = any(%s)", (ids,)).rowcount
            totals["print_batch_items"] = totals.get("print_batch_items", 0) + count
        if relation is not None:
            conn.execute(sql.SQL("delete from {} where {} = any(%s)").format(identifier, sql.Identifier(key)), (ids,))
            totals[table] = totals.get(table, 0) + len(ids)
        return len(ids)


class RetentionRunner:
    def __init__(self, service: RetentionService) -> None:
        self.service = service
        self._stop = asyncio.Event()

    def stop(self) -> None:
        self._stop.set()

    async def run(self) -> None:
        while not self._stop.is_set():
            try:
                await asyncio.to_thread(self.service.run_once)
            except Exception as exc:
                logger.error("Maintenance unavailable: %s", type(exc).__name__)
            try:
                await asyncio.wait_for(self._stop.wait(), self.service.settings.retention_interval_minutes * 60)
            except asyncio.TimeoutError:
                pass
