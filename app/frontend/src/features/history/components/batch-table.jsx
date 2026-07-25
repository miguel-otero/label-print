import { Eye } from "lucide-react";
import { Button } from "@/shared/ui/button";
import { TableRender } from "@/shared/layouts/table-render";
import { StatusBadge } from "./status-badge";

export function BatchTable({ items, loading, onSelect }) {
  const columns = [
    {
      key: "date",
      header: "Fecha",
      headClassName: "w-44 text-center",
      cellClassName: "text-center text-xs text-muted-foreground",
      render: (item) => new Date(item.timestamp).toLocaleString(),
    },
    {
      key: "warehouse",
      header: "Bodega",
      headClassName: "w-24 text-center",
      cellClassName: "text-center font-mono text-xs",
      render: (item) => item.warehouse,
    },
    {
      key: "source",
      header: "Origen",
      headClassName: "w-40 text-center",
      cellClassName: "text-center text-xs",
      render: (item) =>
        item.source === "inventory_entry"
          ? `Entrada ${item.source_document ?? ""}`
          : "Inventario",
    },
    {
      key: "items",
      header: "Artículos",
      headClassName: "text-center",
      cellClassName: "text-center",
      render: (item) => item.items.length,
    },
    {
      key: "format",
      header: "Formato",
      headClassName: "w-24 text-center",
      cellClassName: "text-center font-mono text-xs",
      render: (item) => item.format,
    },
    {
      key: "labels",
      header: "Etiquetas",
      headClassName: "w-28 text-center",
      cellClassName: "text-center",
      render: (item) => `${item.printed_labels}/${item.requested_labels}`,
    },
    {
      key: "status",
      header: "Estado",
      headClassName: "w-28 text-center",
      cellClassName: "text-center",
      render: (item) => <StatusBadge status={item.status} />,
    },
    {
      key: "actions",
      headClassName: "w-14",
      render: (item) => (
        <Button variant="ghost" size="icon" onClick={() => onSelect(item)}>
          <Eye className="h-4 w-4" />
        </Button>
      ),
    },
  ];

  return (
    <TableRender
      columns={columns}
      items={items}
      loading={loading}
      emptyMessage="Sin registros para los filtros aplicados."
      rowKey={(item) => item.id}
    />
  );
}
