import { Trash2 } from "lucide-react";
import { Button } from "@/shared/ui/button";
import { TableRender } from "@/shared/layouts/table-render";
import { cn, formatPresentationQuantity } from "@/shared/utils/utils";

export function BatchSelectionTable({ items, onRemove, centered = false }) {
  const columns = [
    {
      key: "reference",
      header: "Referencia",
      headClassName: centered ? "text-center" : undefined,
      cellClassName: cn("font-mono text-xs", centered && "text-center"),
      render: (item) => item.inventory.reference,
    },
    {
      key: "presentation",
      header: "Presentación",
      headClassName: centered ? "text-center" : undefined,
      cellClassName: cn("text-sm", centered && "text-center"),
      render: (item) =>
        item.product
          ? formatPresentationQuantity(item.product.presentation_quantity)
          : "Pendiente de selección",
    },
    {
      key: "labels",
      header: "Etiquetas",
      headClassName: cn("w-28", centered ? "text-center" : "text-right"),
      cellClassName: cn("font-mono", centered ? "text-center" : "text-right"),
      render: (item) => item.quantity,
    },
    {
      key: "actions",
      headClassName: cn("w-14", centered && "text-center"),
      cellClassName: centered ? "text-center" : undefined,
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
