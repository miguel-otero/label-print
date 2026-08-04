import { cn } from "@/shared/utils/utils";
import { TableRender } from "@/shared/layouts/table-render";

const headClassName =
  "sticky top-0 z-10 bg-card px-1.5 text-center text-xs text-foreground shadow-sm 2xl:text-sm";
const centerCell = "px-1.5 text-center text-xs text-foreground 2xl:text-sm";

function formatQuantityPerUnit(value) {
  if (value === null || value === undefined || value === "") return "";
  const quantity = Number(value);
  return Number.isFinite(quantity) ? String(Math.round(quantity)) : value;
}

export function ProductsTable({ products, loading, selected, onSelect }) {
  const columns = [
    {
      key: "line",
      header: "Línea",
      headClassName: cn(headClassName, "w-[15%]"),
      cellClassName: centerCell,
      render: (product) => <span className="line-clamp-2">{product.line ?? "Sin línea"}</span>,
    },
    {
      key: "code",
      header: "Código",
      headClassName: cn(headClassName, "w-[12%]"),
      cellClassName: "break-words px-1.5 text-center text-xs text-foreground 2xl:text-sm",
      render: (product) => product.product_code,
    },
    {
      key: "description",
      header: "Descripción",
      headClassName: cn(headClassName, "w-[30%]"),
      cellClassName: "px-1.5 text-xs text-foreground 2xl:text-sm",
      render: (product) => <span className="line-clamp-2">{product.description}</span>,
    },
    {
      key: "barcode",
      header: "Código de barras",
      headClassName: cn(headClassName, "w-[16%]"),
      cellClassName: "break-words px-1.5 text-center font-mono text-xs text-foreground",
      render: (product) => product.barcode,
    },
    {
      key: "barcode_unit",
      header: "UM. Código de barras",
      headClassName: cn(headClassName, "w-[18%]"),
      cellClassName: "break-words px-1.5 text-center text-xs text-foreground 2xl:text-sm",
      render: (product) => product.barcode_unit_measure ?? "",
    },
    {
      key: "quantity_per_unit",
      header: "Cant. por UM",
      headClassName: cn(headClassName, "w-[9%]"),
      cellClassName: centerCell,
      render: (product) => formatQuantityPerUnit(product.quantity_per_unit),
    },
  ];

  return (
    <TableRender
      columns={columns}
      items={products}
      loading={loading && products.length === 0}
      skeletonRows={5}
      emptyMessage="Sin resultados, prueba con otra descripción."
      tableClassName="min-w-[900px] table-fixed"
      containerClassName="max-h-[520px]"
      rowKey={(product) => product.id}
      rowProps={(product) => ({
        onClick: () => onSelect(product),
        className: cn(
          "cursor-pointer",
          selected?.id === product.id && "bg-accent/60 hover:bg-accent",
        ),
      })}
    />
  );
}
