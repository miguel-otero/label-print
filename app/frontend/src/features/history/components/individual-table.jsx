import { Eye } from "lucide-react";
import { Button } from "@/shared/ui/button";
import { TableRender } from "@/shared/layouts/table-render";
import { StatusBadge } from "./status-badge";

export function IndividualTable({ items, loading, onSelect }) {
  const columns = [
    {
      key: "date",
      header: "Fecha",
      headClassName: "w-44 text-center",
      cellClassName: "text-center text-xs text-muted-foreground",
      render: (item) => new Date(item.timestamp).toLocaleString(),
    },
    {
      key: "product",
      header: "Producto",
      headClassName: "text-center",
      render: (item) => (
        <>
          <div className="font-mono text-xs">{item.product_code}</div>
          <div className="text-xs text-muted-foreground">{item.product_description}</div>
        </>
      ),
    },
    {
      key: "format",
      header: "Formato",
      headClassName: "w-24 text-center",
      cellClassName: "text-center font-mono text-xs",
      render: (item) => item.format,
    },
    {
      key: "quantity",
      header: "Cant.",
      headClassName: "w-20 text-center",
      cellClassName: "text-center",
      render: (item) => item.quantity,
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
