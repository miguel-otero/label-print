"""Query-time presentation grouping; imported rows are never changed."""

from decimal import Decimal, InvalidOperation

from psycopg import sql

from app.schemas import Product


def catalog_source(table: str) -> sql.Composed:
    # Own codes keep their identity. Manufacturer codes share a representative
    # only when reference, numeric quantity and normalized barcode UM match.
    return sql.SQL(
        """
        (
            select * from (
                select source.*,
                       min(id) over equivalents as representative_id,
                       array_agg(codigo_barra) over equivalents as barcode_aliases
                from {table} source
                window equivalents as (
                    partition by referencia, codigo_propio,
                        case when codigo_propio then id end,
                        case when trim(cantidadxum) ~ '^[+-]?[0-9]+([.,][0-9]+)?$'
                             then replace(trim(cantidadxum), ',', '.')::numeric end,
                        case when trim(cantidadxum) !~ '^[+-]?[0-9]+([.,][0-9]+)?$'
                             then cantidadxum end,
                        upper(regexp_replace(trim(unidad_de_medida_barras), '\\s+', ' ', 'g'))
                )
            ) grouped
            where id = representative_id
        )
        """
    ).format(table=sql.Identifier(table))


def presentation_key(product: Product) -> tuple:
    if product.own_code:
        return (product.id,)
    raw_quantity = product.quantity_per_unit or ""
    try:
        quantity = Decimal(raw_quantity.strip().replace(",", "."))
        if not quantity.is_finite():
            quantity = raw_quantity
    except InvalidOperation:
        quantity = raw_quantity
    return (
        product.product_code,
        quantity,
        " ".join((product.barcode_unit_measure or "").upper().split()),
    )


def group_presentations(products: list[Product]) -> list[Product]:
    representatives: dict[tuple, Product] = {}
    for product in sorted(products, key=lambda item: item.id):
        representatives.setdefault(presentation_key(product), product)
    ids = {product.id for product in representatives.values()}
    return [product for product in products if product.id in ids]
