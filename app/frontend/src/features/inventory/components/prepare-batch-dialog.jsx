import { PackageCheck, RefreshCw } from "lucide-react";
import { Button } from "@/shared/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/shared/ui/dialog";
import { Input } from "@/shared/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select";
import { TableRender } from "@/shared/layouts/table-render";

export function PrepareBatchDialog({
  open,
  onOpenChange,
  items,
  maxLabels,
  totalLabels,
  overLimit,
  unresolved,
  canSubmit,
  printing,
  quantityLabel = "Existencia",
  onChoosePresentation,
  onQuantityChange,
  onPrint,
}) {
  const columns = [
    {
      key: "article",
      header: "Artículo",
      render: (item) => (
        <>
          <div className="font-mono text-xs">{item.inventory.reference}</div>
          <div className="line-clamp-2 text-xs text-muted-foreground">
            {item.product?.description ??
              item.inventory.presentations[0]?.description ??
              "Producto no registrado"}
          </div>
          <div className="text-xs text-muted-foreground">
            {quantityLabel}: {Number(item.inventory.inventory_quantity).toLocaleString()}
          </div>
        </>
      ),
    },
    {
      key: "presentation",
      header: "Presentación",
      headClassName: "min-w-56",
      render: (item) => (
        <Select
          value={item.product ? String(item.product.id) : ""}
          onValueChange={(value) => onChoosePresentation(item.inventory.id, value)}
        >
          <SelectTrigger>
            <SelectValue placeholder="Seleccionar presentación" />
          </SelectTrigger>
          <SelectContent>
            {item.inventory.presentations.map((product) => (
              <SelectItem key={product.id} value={String(product.id)}>
                {product.presentation_quantity} · {product.barcode}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      ),
    },
    {
      key: "automatic",
      header: "Automática",
      headClassName: "w-28",
      cellClassName: "text-center font-mono",
      render: (item) => (item.product ? item.automaticQuantity : "—"),
    },
    {
      key: "toPrint",
      header: "A imprimir",
      headClassName: "w-28",
      render: (item) => (
        <Input
          type="number"
          min={0}
          value={item.quantity}
          disabled={!item.product}
          onChange={(event) =>
            onQuantityChange(
              item.inventory.id,
              Math.max(0, Number.parseInt(event.target.value || "0", 10)),
            )
          }
          className="text-right"
        />
      ),
    },
  ];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Preparar lote de inventario</DialogTitle>
          <DialogDescription>
            Confirma la presentación y la cantidad de etiquetas de cada artículo.
          </DialogDescription>
        </DialogHeader>

        <div className="max-h-[58vh] overflow-auto rounded-md border">
          <TableRender columns={columns} items={items} rowKey={(item) => item.inventory.id} />
        </div>

        <div className="flex items-center justify-between rounded-md border bg-muted/20 px-3 py-2">
          <span className="flex items-center gap-2 text-sm">
            <PackageCheck className="h-4 w-4" />
            Total del lote
          </span>
          <span className={overLimit ? "font-semibold text-destructive" : "font-semibold"}>
            {totalLabels} / {maxLabels}
          </span>
        </div>
        {unresolved && (
          <p className="text-sm text-destructive">
            Los articulos con etiquetas a imprimir deben tener presentacion.
          </p>
        )}
        {overLimit && (
          <p className="text-sm text-destructive">
            Reduce las cantidades para respetar el límite configurado.
          </p>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancelar
          </Button>
          <Button onClick={onPrint} disabled={!canSubmit}>
            {printing && <RefreshCw className="mr-2 h-4 w-4 animate-spin" />}
            Imprimir {totalLabels} etiquetas
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
