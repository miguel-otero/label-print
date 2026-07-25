import asyncio
import logging
from calendar import monthrange
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from threading import Lock
from typing import Any

import psycopg
from psycopg import sql
from psycopg.rows import dict_row
import pytds
from sshtunnel import SSHTunnelForwarder

from app.schemas import InventorySyncResult
from app.settings import Settings


logger = logging.getLogger(__name__)


PRODUCT_COLUMNS = (
    "referencia",
    "descripcion",
    "um_siesa",
    "codigo_barra",
    "cantidadxum",
    "unidad_de_medida_barras",
    "linea",
    "codigo_propio",
)


def subtract_calendar_months(value: date, months: int) -> date:
    month_index = value.year * 12 + value.month - 1 - months
    year, zero_based_month = divmod(month_index, 12)
    month = zero_based_month + 1
    day = min(value.day, monthrange(year, month)[1])
    return date(year, month, day)


class InventorySyncError(RuntimeError):
    pass


class InventorySyncService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._sync_lock = Lock()
        self._status_lock = Lock()
        self._status = InventorySyncResult(status="idle")

    def get_status(self) -> InventorySyncResult:
        with self._status_lock:
            return self._status.model_copy()

    def sync_all(self) -> InventorySyncResult:
        with self._sync_lock:
            started_at = datetime.now(timezone.utc)
            retention_cutoff = self._retention_cutoff()

            if not self.settings.external_sync_enabled:
                result = InventorySyncResult(
                    status="disabled",
                    started_at=started_at,
                    finished_at=datetime.now(timezone.utc),
                    retention_cutoff=retention_cutoff,
                    message="Sincronizacion externa deshabilitada.",
                )
                self._set_status(result)
                return result

            self._set_status(InventorySyncResult(status="running", started_at=started_at))

            try:
                if self.settings.use_postgres:
                    self._ensure_inventory_entries_schema()
                    self._purge_expired_inventory_entries(retention_cutoff)

                if not self.settings.external_database_configured:
                    result = InventorySyncResult(
                        status="not_configured",
                        started_at=started_at,
                        finished_at=datetime.now(timezone.utc),
                        retention_cutoff=retention_cutoff,
                        message="Configure la conexion SQL Server en conn/.env.",
                    )
                    self._set_status(result)
                    return result

                product_rows = self._fetch_warehouse_app_products()
                self._replace_products(product_rows)
                entries_since = self._get_entries_since_date(retention_cutoff)
                entry_rows = self._fetch_external_rows(
                    "consulta_entradas.sql",
                    {"since_date": entries_since},
                )
                inventory_rows = self._fetch_external_rows("consulta_inventario.sql")
                self._replace_inventory(inventory_rows)
                self._replace_inventory_entries_since(
                    entry_rows,
                    entries_since,
                    retention_cutoff,
                )
            except Exception as exc:
                logger.exception("Inventory synchronization failed")
                result = InventorySyncResult(
                    status="error",
                    started_at=started_at,
                    finished_at=datetime.now(timezone.utc),
                    message=str(exc),
                )
                self._set_status(result)
                return result

            result = InventorySyncResult(
                status="success",
                started_at=started_at,
                finished_at=datetime.now(timezone.utc),
                product_rows=len(product_rows),
                inventory_rows=len(inventory_rows),
                inventory_entry_rows=len(entry_rows),
                entries_since=entries_since,
                retention_cutoff=retention_cutoff,
            )
            self._set_status(result)
            return result

    def _set_status(self, status: InventorySyncResult) -> None:
        with self._status_lock:
            self._status = status

    def _postgres_connect(self) -> psycopg.Connection:
        return psycopg.connect(
            host=self.settings.database_host,
            port=self.settings.database_port,
            dbname=self.settings.database_name,
            user=self.settings.database_user,
            password=self.settings.database_password,
        )

    def _external_connect(self) -> Any:
        return pytds.connect(
            server=self.settings.external_database_host,
            port=self.settings.external_database_port,
            database=self.settings.external_database_name,
            user=self.settings.external_database_user,
            password=self.settings.external_database_password,
            timeout=self.settings.external_database_timeout_seconds,
            login_timeout=min(self.settings.external_database_timeout_seconds, 30),
            as_dict=True,
            readonly=True,
        )

    def _fetch_warehouse_app_products(self) -> list[dict[str, Any]]:
        if self.settings.warehouse_app_database_engine.lower() != "postgres":
            raise InventorySyncError("La base APP de Almacen solo soporta engine postgres.")
        if not self.settings.warehouse_app_database_configured:
            raise InventorySyncError("Configure la conexion APP de Almacen en conn/.env.")

        with SSHTunnelForwarder(
            (self.settings.warehouse_app_ssh_host, self.settings.warehouse_app_ssh_port),
            ssh_username=self.settings.warehouse_app_ssh_user,
            ssh_password=self.settings.warehouse_app_ssh_password,
            remote_bind_address=(
                self.settings.warehouse_app_database_host,
                self.settings.warehouse_app_database_port,
            ),
            local_bind_address=("127.0.0.1", 0),
        ) as tunnel:
            with psycopg.connect(
                host=tunnel.local_bind_host,
                port=tunnel.local_bind_port,
                dbname=self.settings.warehouse_app_database_name,
                user=self.settings.warehouse_app_database_user,
                password=self.settings.warehouse_app_database_password,
                options="-c default_transaction_read_only=on",
                row_factory=dict_row,
            ) as conn:
                cursor = conn.execute(
                    sql.SQL("select {} from v_label_print_items").format(
                        sql.SQL(", ").join(sql.Identifier(column) for column in PRODUCT_COLUMNS)
                    )
                )
                returned_columns = {column.name for column in cursor.description}
                missing_columns = [
                    column for column in PRODUCT_COLUMNS if column not in returned_columns
                ]
                if missing_columns:
                    raise InventorySyncError(
                        "La vista v_label_print_items no devuelve columnas requeridas: "
                        + ", ".join(missing_columns)
                    )
                rows = cursor.fetchall()

        return [dict(row) for row in rows]

    def _read_query(self, filename: str) -> str:
        path = Path(self.settings.sync_query_dir) / filename
        if not path.is_file():
            raise InventorySyncError(f"No existe la consulta SQL Server: {path.resolve()}")
        return path.read_text(encoding="utf-8")

    def _fetch_external_rows(
        self,
        filename: str,
        params: dict[str, object] | None = None,
    ) -> list[dict[str, Any]]:
        query = self._read_query(filename)
        with closing(self._external_connect()) as conn:
            with closing(conn.cursor()) as cursor:
                cursor.execute(query, params or {})
                return list(cursor.fetchall())

    def _retention_cutoff(self) -> date:
        return subtract_calendar_months(
            date.today(),
            self.settings.inventory_entries_retention_months,
        )

    def _purge_expired_inventory_entries(self, retention_cutoff: date) -> None:
        table = sql.Identifier(self.settings.inventory_entries_table)
        with self._postgres_connect() as conn:
            conn.execute(
                sql.SQL("delete from {} where fecha < %s").format(table),
                (retention_cutoff,),
            )

    def _ensure_inventory_entries_schema(self) -> None:
        table = sql.Identifier(self.settings.inventory_entries_table)
        with self._postgres_connect() as conn:
            conn.execute(
                sql.SQL(
                    "alter table {} add column if not exists proveedor_nit text not null default ''"
                ).format(table)
            )
            conn.execute(
                sql.SQL(
                    "alter table {} add column if not exists proveedor_razon_social text not null default ''"
                ).format(table)
            )

    def _get_entries_since_date(self, retention_cutoff: date) -> date:
        table = sql.Identifier(self.settings.inventory_entries_table)
        with self._postgres_connect() as conn:
            latest = conn.execute(
                sql.SQL("select max(fecha) from {}").format(table)
            ).fetchone()[0]

        if latest is None:
            return retention_cutoff

        return max(
            retention_cutoff,
            latest - timedelta(days=self.settings.external_sync_lookback_days),
        )

    def _replace_inventory(self, rows: list[dict[str, Any]]) -> None:
        table = sql.Identifier(self.settings.inventory_table)
        values = [
            (row["referencia"], row["inventario"], row["bodega"])
            for row in rows
        ]

        with self._postgres_connect() as conn:
            with conn.transaction():
                conn.execute(sql.SQL("truncate table {} restart identity").format(table))
                if values:
                    with conn.cursor() as cursor:
                        cursor.executemany(
                            sql.SQL(
                                "insert into {} (referencia, inventario, bodega) values (%s, %s, %s)"
                            ).format(table),
                            values,
                        )

    def _replace_inventory_entries_since(
        self,
        rows: list[dict[str, Any]],
        since_date: date,
        retention_cutoff: date,
    ) -> None:
        table = sql.Identifier(self.settings.inventory_entries_table)
        values = self._aggregate_inventory_entry_rows(rows, since_date, retention_cutoff)

        with self._postgres_connect() as conn:
            with conn.transaction():
                conn.execute(
                    sql.SQL(
                        "delete from {} where fecha < %s or fecha >= %s"
                    ).format(table),
                    (retention_cutoff, since_date),
                )
                if values:
                    with conn.cursor() as cursor:
                        cursor.executemany(
                            sql.SQL(
                                """
                                insert into {}
                                    (referencia, entradas_inv, documento, fecha, bodega,
                                     proveedor_nit, proveedor_razon_social)
                                values (%s, %s, %s, %s, %s, %s, %s)
                                """
                            ).format(table),
                            values,
                        )

    def _replace_products(self, rows: list[dict[str, Any]]) -> None:
        table = sql.Identifier(self.settings.products_table)
        self._validate_product_rows(rows)
        values = [
            (
                self._row_text(row["referencia"]),
                self._row_text(row["descripcion"]),
                self._row_text(row["um_siesa"]),
                self._row_text(row["codigo_barra"]),
                self._row_text(row["cantidadxum"]),
                self._row_text(row["unidad_de_medida_barras"]),
                self._row_text(row["linea"]),
                self._row_bool(row["codigo_propio"]),
            )
            for row in rows
        ]

        with self._postgres_connect() as conn:
            with conn.transaction():
                conn.execute(sql.SQL("truncate table {} restart identity").format(table))
                if values:
                    with conn.cursor() as cursor:
                        cursor.executemany(
                            sql.SQL(
                                """
                                insert into {}
                                    (referencia, descripcion, um_siesa, codigo_barra,
                                     cantidadxum, unidad_de_medida_barras, linea, codigo_propio)
                                values (%s, %s, %s, %s, %s, %s, %s, %s)
                                """
                            ).format(table),
                            values,
                        )

    def _validate_product_rows(self, rows: list[dict[str, Any]]) -> None:
        for index, row in enumerate(rows, start=1):
            missing_columns = [column for column in PRODUCT_COLUMNS if column not in row]
            if missing_columns:
                raise InventorySyncError(
                    "La vista v_label_print_items no devuelve columnas requeridas: "
                    + ", ".join(missing_columns)
                )
            for column in PRODUCT_COLUMNS[:-1]:
                if row[column] is None:
                    raise InventorySyncError(
                        f"La fila {index} de v_label_print_items tiene {column} nulo."
                    )

    @staticmethod
    def _row_date(value: date | datetime) -> date:
        return value.date() if isinstance(value, datetime) else value

    @staticmethod
    def _row_text(value: object) -> str:
        return "" if value is None else str(value).strip()

    @staticmethod
    def _row_bool(value: object) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value != 0
        normalized = str(value).strip().lower()
        return normalized in {"1", "true", "t", "yes", "y", "si", "s"}

    def _aggregate_inventory_entry_rows(
        self,
        rows: list[dict[str, Any]],
        since_date: date,
        retention_cutoff: date,
    ) -> list[tuple[object, ...]]:
        grouped: dict[tuple[str, str, date, str], dict[str, object]] = {}
        for row in rows:
            row_date = self._row_date(row["fecha"])
            if row_date < retention_cutoff or row_date < since_date:
                continue

            reference = self._row_text(row["referencia"])
            document = self._row_text(row["documento"])
            warehouse = self._row_text(row["bodega"])
            key = (reference, document, row_date, warehouse)
            existing = grouped.get(key)
            quantity = Decimal(str(row["entradas_inv"] or 0))
            provider_nit = self._row_text(row.get("proveedor_nit"))
            provider_name = self._row_text(row.get("proveedor_razon_social"))

            if existing is None:
                grouped[key] = {
                    "quantity": quantity,
                    "provider_nit": provider_nit,
                    "provider_name": provider_name,
                }
                continue

            existing["quantity"] = existing["quantity"] + quantity
            existing["provider_nit"] = max(str(existing["provider_nit"]), provider_nit)
            existing["provider_name"] = max(str(existing["provider_name"]), provider_name)

        return [
            (
                reference,
                data["quantity"],
                document,
                row_date,
                warehouse,
                data["provider_nit"],
                data["provider_name"],
            )
            for (reference, document, row_date, warehouse), data in grouped.items()
        ]


class InventorySyncRunner:
    def __init__(self, service: InventorySyncService, settings: Settings) -> None:
        self.service = service
        self.settings = settings
        self._stop = asyncio.Event()

    async def run(self) -> None:
        while not self._stop.is_set():
            result = await asyncio.to_thread(self.service.sync_all)
            if result.status == "error":
                logger.error("Inventory synchronization error: %s", result.message)
            elif result.status == "not_configured":
                logger.info(result.message)

            try:
                await asyncio.wait_for(
                    self._stop.wait(),
                    timeout=self.settings.external_sync_interval_minutes * 60,
                )
            except TimeoutError:
                continue

    def stop(self) -> None:
        self._stop.set()
