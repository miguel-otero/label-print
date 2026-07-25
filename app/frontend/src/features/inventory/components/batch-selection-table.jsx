import { Trash2 } from "lucide-react";
import { Button } from "@/shared/ui/button";
import { TableRender } from "@/shared/layouts/table-render";

export function BatchSelectionTable({ items, onRemove }) {
  const columns = [
    {
      key: "reference",
      header: "Referencia",
      cellClassName: "font-mono text-xs",
      render: (item) => item.inventory.reference,
    },
    {
      key: "presentation",
      header: "Presentación",
      cellClassName: "text-sm",
      render: (item) => item.product?.presentation_quantity ?? "Pendiente de selección",
    },
    {
      key: "labels",
      header: "Etiquetas",
      headClassName: "w-28 text-right",
      cellClassName: "text-right font-mono",
      render: (item) => item.quantity,
    },
    {
      key: "actions",
      headClassName: "w-14",
      render: (item) => (
        <Button
          variant="ghost"
          size="icon"
          onClick={() => onRemove(item.inventory.id)}
          aria-label={`Quitar ${item.inventory.reference}`}
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      ),
    },
  ];

  return <TableRender columns={columns} items={items} rowKey={(item) => item.inventory.id} />;
}
