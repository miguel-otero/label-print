import unicodedata
from datetime import datetime, timezone
from typing import Literal, Protocol

from fastapi import HTTPException
import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from app.mock_data import FORMATS, HISTORY, PRODUCTS
from app.schemas import LabelFormat, LabelFormatPayload, PrintHistory, Product
from app.settings import Settings


PrintStatus = Literal["success", "error"]


def normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value.lower())
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


class Repository(Protocol):
    def search_products(
        self,
        search: str | None,
        *,
        lines: list[str],
        limit: int,
        offset: int,
    ) -> list[Product]: ...
    def count_products(self, search: str | None, *, lines: list[str]) -> int: ...
    def get_product_lines(self) -> list[str]: ...
    def health_check(self) -> bool: ...
    def get_formats(self, *, active_only: bool = True) -> list[LabelFormat]: ...
    def get_format(self, code: str) -> LabelFormat | None: ...
    def list_template_files(self) -> list[str]: ...
    def save_format(self, payload: LabelFormatPayload, *, format_id: int | None = None) -> LabelFormat: ...
    def delete_format(self, format_id: int) -> None: ...
    def get_product(self, product_id: int) -> Product | None: ...
    def add_history(
        self,
        *,
        product: Product,
        label_format: str,
        quantity: int,
        status: PrintStatus,
        message: str | None,
        user: str,
    ) -> PrintHistory: ...
    def get_history(self) -> list[PrintHistory]: ...


class MockRepository:
    def __init__(self) -> None:
        self._history = list(HISTORY)
        self._formats = list(FORMATS)

    def _filter_products(self, search: str | None, *, lines: list[str]) -> list[Product]:
        query = normalize((search or "").strip())
        selected_lines = {line for line in lines if line}
        products = [product for product in PRODUCTS if product.own_code]
        if selected_lines:
            products = [product for product in products if product.line in selected_lines]
        if query:
            products = [
                product
                for product in products
                if query in normalize(product.product_code)
                or query in normalize(product.description)
                or query in normalize(product.barcode)
                or query in normalize(product.line or "")
            ]
        return products

    def search_products(
        self,
        search: str | None,
        *,
        lines: list[str],
        limit: int,
        offset: int,
    ) -> list[Product]:
        return self._filter_products(search, lines=lines)[offset : offset + limit]

    def count_products(self, search: str | None, *, lines: list[str]) -> int:
        return len(self._filter_products(search, lines=lines))

    def get_product_lines(self) -> list[str]:
        return sorted({product.line for product in PRODUCTS if product.line and product.own_code})

    def health_check(self) -> bool:
        return True

    def get_formats(self, *, active_only: bool = True) -> list[LabelFormat]:
        if active_only:
            return [label_format for label_format in self._formats if label_format.active]
        return list(self._formats)

    def get_format(self, code: str) -> LabelFormat | None:
        return next((label_format for label_format in self._formats if label_format.code == code), None)

    def list_template_files(self) -> list[str]:
        return sorted({label_format.template_file for label_format in self._formats})

    def save_format(self, payload: LabelFormatPayload, *, format_id: int | None = None) -> LabelFormat:
        if format_id is None:
            next_id = max((label_format.id for label_format in self._formats), default=0) + 1
            item = LabelFormat(id=next_id, **payload.model_dump())
            self._formats.append(item)
            return item

        item = LabelFormat(id=format_id, **payload.model_dump())
        for index, label_format in enumerate(self._formats):
            if label_format.id == format_id:
                self._formats[index] = item
                return item
        raise HTTPException(status_code=404, detail="Formato no encontrado")

    def delete_format(self, format_id: int) -> None:
        initial_count = len(self._formats)
        self._formats = [label_format for label_format in self._formats if label_format.id != format_id]
        if len(self._formats) == initial_count:
            raise HTTPException(status_code=404, detail="Formato no encontrado")

    def get_product(self, product_id: int) -> Product | None:
        return next((product for product in PRODUCTS if product.id == product_id), None)

    def add_history(
        self,
        *,
        product: Product,
        label_format: str,
        quantity: int,
        status: PrintStatus,
        message: str | None,
        user: str,
    ) -> PrintHistory:
        item = PrintHistory(
            id=(max((entry.id for entry in self._history), default=0) + 1),
            timestamp=datetime.now(timezone.utc),
            user=user,
            product_code=product.product_code,
            product_description=product.description,
            format=label_format,
            quantity=quantity,
            status=status,
            message=message,
        )
        self._history.append(item)
        return item

    def get_history(self) -> list[PrintHistory]:
        return sorted(self._history, key=lambda entry: entry.timestamp, reverse=True)


class PostgresRepository:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(
            host=self.settings.database_host,
            port=self.settings.database_port,
            dbname=self.settings.database_name,
            user=self.settings.database_user,
            password=self.settings.database_password,
            row_factory=dict_row,
        )

    def _product_select_sql(self) -> sql.SQL:
        return sql.SQL(
            """
            select id,
                   linea as line,
                   referencia as product_code,
                   descripcion as description,
                   um_siesa as unit_of_measure,
                   codigo_barra as barcode,
                   unidad_de_medida_barras as barcode_unit_measure,
                   cantidadxum as quantity_per_unit,
                   codigo_propio as own_code,
                   concat_ws(' ', nullif(cantidadxum, ''), nullif(unidad_de_medida_barras, '')) as presentation_quantity
            from {table}
            """
        ).format(table=sql.Identifier(self.settings.products_table))

    def _product_filter_sql(
        self,
        search: str | None,
        *,
        lines: list[str],
    ) -> tuple[sql.SQL, dict[str, object]]:
        term = (search or "").strip()
        selected_lines = [line for line in lines if line]
        conditions: list[sql.SQL] = [sql.SQL("codigo_propio = true")]
        params: dict[str, object] = {}

        if term:
            conditions.append(
                sql.SQL(
                    """
                    (
                        referencia ilike %(pattern)s
                        or descripcion ilike %(pattern)s
                        or codigo_barra ilike %(pattern)s
                        or linea ilike %(pattern)s
                    )
                    """
                )
            )
            params["pattern"] = f"%{term}%"

        if selected_lines:
            conditions.append(sql.SQL("linea = any(%(lines)s::text[])"))
            params["lines"] = selected_lines

        return sql.SQL(" where ") + sql.SQL(" and ").join(conditions), params

    def search_products(
        self,
        search: str | None,
        *,
        lines: list[str],
        limit: int,
        offset: int,
    ) -> list[Product]:
        where_sql, params = self._product_filter_sql(search, lines=lines)
        params.update({"limit": limit, "offset": offset})
        with self._connect() as conn:
            rows = conn.execute(
                self._product_select_sql()
                + where_sql
                + sql.SQL(
                    """
                    order by linea, descripcion, referencia, id
                    limit %(limit)s offset %(offset)s
                    """
                ),
                params,
            ).fetchall()
        return [Product.model_validate(row) for row in rows]

    def count_products(self, search: str | None, *, lines: list[str]) -> int:
        where_sql, params = self._product_filter_sql(search, lines=lines)
        with self._connect() as conn:
            row = conn.execute(
                sql.SQL("select count(*) as total from {table}").format(
                    table=sql.Identifier(self.settings.products_table)
                )
                + where_sql,
                params,
            ).fetchone()
        return int(row["total"]) if row else 0

    def get_product_lines(self) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                sql.SQL(
                    """
                    select distinct linea as line
                    from {table}
                    where codigo_propio = true
                      and linea is not null
                      and linea <> ''
                    order by linea
                    """
                ).format(table=sql.Identifier(self.settings.products_table))
            ).fetchall()
        return [str(row["line"]) for row in rows]

    def health_check(self) -> bool:
        try:
            with self._connect() as conn:
                conn.execute(
                    sql.SQL("select 1 from {table} limit 1").format(
                        table=sql.Identifier(self.settings.products_table)
                    )
                ).fetchone()
        except psycopg.Error:
            return False
        return True

    def get_formats(self, *, active_only: bool = True) -> list[LabelFormat]:
        where_sql = sql.SQL("where active = true") if active_only else sql.SQL("")
        with self._connect() as conn:
            rows = conn.execute(
                sql.SQL(
                    """
                    select id, name, code, width_mm, height_mm, preview_type, active, template_file
                    from {table}
                    {where}
                    order by id
                    """
                ).format(table=sql.Identifier(self.settings.formats_table), where=where_sql)
            ).fetchall()
        return [LabelFormat.model_validate(row) for row in rows]

    def get_format(self, code: str) -> LabelFormat | None:
        with self._connect() as conn:
            row = conn.execute(
                sql.SQL(
                    """
                    select id, name, code, width_mm, height_mm, preview_type, active, template_file
                    from {table}
                    where code = %(code)s
                    limit 1
                    """
                ).format(table=sql.Identifier(self.settings.formats_table)),
                {"code": code},
            ).fetchone()
        return LabelFormat.model_validate(row) if row else None

    def list_template_files(self) -> list[str]:
        template_path = self._template_dir()
        return sorted(path.name for path in template_path.glob("*.zpl") if path.is_file())

    def save_format(self, payload: LabelFormatPayload, *, format_id: int | None = None) -> LabelFormat:
        data = payload.model_dump()
        with self._connect() as conn:
            if format_id is None:
                row = conn.execute(
                    sql.SQL(
                        """
                        insert into {table}
                            (name, code, width_mm, height_mm, preview_type, active, template_file)
                        values
                            (%(name)s, %(code)s, %(width_mm)s, %(height_mm)s,
                             %(preview_type)s, %(active)s, %(template_file)s)
                        on conflict (code) do update set
                            name = excluded.name,
                            width_mm = excluded.width_mm,
                            height_mm = excluded.height_mm,
                            preview_type = excluded.preview_type,
                            active = excluded.active,
                            template_file = excluded.template_file
                        returning id, name, code, width_mm, height_mm, preview_type, active, template_file
                        """
                    ).format(table=sql.Identifier(self.settings.formats_table)),
                    data,
                ).fetchone()
            else:
                data["id"] = format_id
                row = conn.execute(
                    sql.SQL(
                        """
                        update {table}
                        set name = %(name)s,
                            code = %(code)s,
                            width_mm = %(width_mm)s,
                            height_mm = %(height_mm)s,
                            preview_type = %(preview_type)s,
                            active = %(active)s,
                            template_file = %(template_file)s
                        where id = %(id)s
                        returning id, name, code, width_mm, height_mm, preview_type, active, template_file
                        """
                    ).format(table=sql.Identifier(self.settings.formats_table)),
                    data,
                ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Formato no encontrado")
        return LabelFormat.model_validate(row)

    def delete_format(self, format_id: int) -> None:
        with self._connect() as conn:
            row = conn.execute(
                sql.SQL(
                    """
                    delete from {table}
                    where id = %(id)s
                    returning id
                    """
                ).format(table=sql.Identifier(self.settings.formats_table)),
                {"id": format_id},
            ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Formato no encontrado")

    def _template_dir(self):
        from pathlib import Path

        return Path(__file__).resolve().parents[1] / "label_templates"

    def get_product(self, product_id: int) -> Product | None:
        with self._connect() as conn:
            row = conn.execute(
                self._product_select_sql()
                + sql.SQL(
                    """
                    where id = %(id)s
                      and codigo_propio = true
                    limit 1
                    """
                ),
                {"id": product_id},
            ).fetchone()
        return Product.model_validate(row) if row else None

    def add_history(
        self,
        *,
        product: Product,
        label_format: str,
        quantity: int,
        status: PrintStatus,
        message: str | None,
        user: str,
    ) -> PrintHistory:
        payload = {
            "timestamp": datetime.now(timezone.utc),
            "user": user,
            "product_code": product.product_code,
            "product_description": product.description,
            "format": label_format,
            "quantity": quantity,
            "status": status,
            "message": message,
        }
        with self._connect() as conn:
            row = conn.execute(
                sql.SQL(
                    """
                    insert into {table}
                        (timestamp, "user", product_code, product_description, format, quantity, status, message)
                    values
                        (%(timestamp)s, %(user)s, %(product_code)s, %(product_description)s,
                         %(format)s, %(quantity)s, %(status)s, %(message)s)
                    returning id, timestamp, "user", product_code, product_description,
                              format, quantity, status, message
                    """
                ).format(table=sql.Identifier(self.settings.history_table)),
                payload,
            ).fetchone()
        return PrintHistory.model_validate(row)

    def get_history(self) -> list[PrintHistory]:
        with self._connect() as conn:
            rows = conn.execute(
                sql.SQL(
                    """
                    select id, timestamp, "user", product_code, product_description,
                           format, quantity, status, message
                    from {table}
                    order by timestamp desc
                    limit 200
                    """
                ).format(table=sql.Identifier(self.settings.history_table))
            ).fetchall()
        return [PrintHistory.model_validate(row) for row in rows]


def create_repository(settings: Settings) -> Repository:
    if settings.use_postgres:
        return PostgresRepository(settings)
    return MockRepository()


def require_product(repository: Repository, product_id: int) -> Product:
    product = repository.get_product(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return product
