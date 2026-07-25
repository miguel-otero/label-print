import { useEffect, useRef } from "react";
import { CircleAlert } from "lucide-react";
import { Badge } from "@/shared/ui/badge";
import { TableRender } from "@/shared/layouts/table-render";

const headBase =
  "sticky top-0 z-10 bg-card px-1.5 text-center align-middle text-xs text-foreground shadow-sm 2xl:text-sm";

function HeaderSelectCheckbox({ checked, disabled, indeterminate, onToggle }) {
  const ref = useRef(null);

  useEffect(() => {
    if (ref.current) ref.current.indeterminate = indeterminate;
  }, [indeterminate]);

  return (
    <input
      ref={ref}
      type="checkbox"
      checked={checked}
      disabled={disabled}
      onChange={onToggle}
      onClick={(event) => event.stopPropagation()}
      className="h-4 w-4"
      aria-label="Seleccionar todos los productos filtrados"
      title="Seleccionar todos los productos filtrados"
    />
  );
}

export function InventoryTable({
  items,
  loading,
  isSelected,
  onToggle,
  allFilteredSelected = false,
  someFilteredSelected = false,
  onToggleAllFiltered,
  selectAllDisabled = false,
}) {
  const columns = [
    {
      key: "select",
      header: onToggleAllFiltered ? (
        <HeaderSelectCheckbox
          checked={allFilteredSelected}
          disabled={selectAllDisabled}
          indeterminate={someFilteredSelected && !allFilteredSelected}
          onToggle={onToggleAllFiltered}
        />
      ) : null,
      headClassName: `${headBase} w-12`,
      cellClassName: "text-center align-middle",
      render: (item) => (
        <input
          type="checkbox"
          checked={isSelected(item)}
          disabled={!item.printable}
          onChange={() => onToggle(item)}
          onClick={(event) => event.stopPropagation()}
          className="h-4 w-4"
          aria-label={`Seleccionar ${item.reference}`}
        />
      ),
    },
    {
      key: "line",
      header: "Linea",
      headClassName: `${headBase} w-32`,
      cellClassName: "text-center align-middle text-xs",
      render: (item) => (
        <span className="line-clamp-2">{item.presentations[0]?.line ?? "Sin linea"}</span>
      ),
    },
    {
      key: "reference",
      header: "Referencia",
      headClassName: `${headBase} w-28`,
      cellClassName: "text-center align-middle font-mono text-xs",
      render: (item) => item.reference,
    },
    {
      key: "description",
      header: "Descripción",
      headClassName: headBase,
      cellClassName: "align-middle",
      render: (item) => (
        <span className="line-clamp-2 text-sm">
          {item.presentations[0]?.description ?? "Producto no registrado"}
        </span>
      ),
    },
    {
      key: "quantity",
      header: "Existencia",
      headClassName: `${headBase} w-28`,
      cellClassName: "text-center align-middle font-mono",
      render: (item) => Number(item.inventory_quantity).toLocaleString(),
    },
    {
      key: "presentations",
      header: "Presentaciones",
      headClassName: `${headBase} w-36 text-center`,
      cellClassName: "text-center align-middle",
      render: (item) => item.presentations.length || "—",
    },
    {
      key: "status",
      header: "Estado",
      headClassName: `${headBase} w-40`,
      cellClassName: "text-center align-middle",
      render: (item) =>
        item.printable ? (
          <Badge variant="secondary">Imprimible</Badge>
        ) : (
          <span className="flex items-center gap-1.5 text-xs text-destructive">
            <CircleAlert className="h-3.5 w-3.5 shrink-0" />
            {item.unavailable_reason}
          </span>
        ),
    },
  ];

  return (
    <TableRender
      columns={columns}
      items={items}
      loading={loading}
      skeletonRows={6}
      skeletonCellClassName="h-6 w-full"
      emptyMessage="No hay inventario para los filtros seleccionados."
      tableClassName="min-w-[880px]"
      containerClassName="max-h-[520px]"
      rowKey={(item) => item.id}
      rowProps={(item) => ({
        onClick: () => onToggle(item),
        className: item.printable
          ? `cursor-pointer ${isSelected(item) ? "bg-accent/60" : ""}`
          : "opacity-60",
      })}
    />
  );
}
