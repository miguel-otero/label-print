import { useState } from "react";
import { Eye, Loader2, Minus, Plus, Printer } from "lucide-react";
import { LabelPreview } from "@/shared/components/label-preview";
import { Button } from "@/shared/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select";

const QUICK_QUANTITIES = [9, 18, 30, 60, 120];

export function PrintConfigurationPanel({
  formats,
  formatId,
  onFormatChange,
  product,
  quantity,
  previewQuantity,
  onQuantityChange,
  quantityLabel = "Cantidad",
  quantityHelp,
  description,
  printing,
  canPrint,
  onPrint,
  printButtonLabel = "Imprimir etiqueta",
}) {
  const [showPreview, setShowPreview] = useState(true);
  const selectedFormat = formats.find((format) => String(format.id) === formatId) ?? null;
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Configuración de impresión</CardTitle>
          <CardDescription>
            {description ?? product?.description ?? "Selecciona un producto de la tabla"}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="space-y-2">
            <Label>Formato de etiqueta</Label>
            <Select value={formatId} onValueChange={onFormatChange}>
              <SelectTrigger>
                <SelectValue placeholder="Elegir formato" />
              </SelectTrigger>
              <SelectContent>
                {formats.map((format) => (
                  <SelectItem key={format.id} value={String(format.id)}>
                    {format.name} ({format.code})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>{quantityLabel}</Label>
            {onQuantityChange ? (
              <>
                <div className="grid grid-cols-[auto_auto_1fr_auto_auto] items-center gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    onClick={() => onQuantityChange(Math.max(1, quantity - 3))}
                    aria-label="Restar 3 etiquetas"
                  >
                    -3
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    onClick={() => onQuantityChange(Math.max(1, quantity - 1))}
                    aria-label="Restar 1 etiqueta"
                  >
                    <Minus className="h-4 w-4" />
                  </Button>
                  <Input
                    type="number"
                    min={1}
                    value={quantity}
                    onChange={(event) =>
                      onQuantityChange(Math.max(1, Number.parseInt(event.target.value || "1", 10)))
                    }
                    className="text-center"
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    onClick={() => onQuantityChange(quantity + 1)}
                    aria-label="Sumar 1 etiqueta"
                  >
                    <Plus className="h-4 w-4" />
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    onClick={() => onQuantityChange(quantity + 3)}
                    aria-label="Sumar 3 etiquetas"
                  >
                    +3
                  </Button>
                </div>
                <div className="space-y-1.5">
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] font-medium uppercase text-muted-foreground">
                      Cantidades fijas
                    </span>
                    <span className="h-px flex-1 bg-border" />
                  </div>
                  <div className="grid grid-cols-5 gap-1.5">
                    {QUICK_QUANTITIES.map((nextQuantity) => (
                      <Button
                        key={nextQuantity}
                        type="button"
                        variant={quantity === nextQuantity ? "default" : "outline"}
                        size="sm"
                        onClick={() => onQuantityChange(nextQuantity)}
                        className="px-2"
                      >
                        {nextQuantity}
                      </Button>
                    ))}
                  </div>
                </div>
              </>
            ) : (
              <div className="flex h-10 items-center justify-between rounded-md border bg-muted/20 px-3">
                <span className="text-sm text-muted-foreground">Total del lote</span>
                <span className="font-mono text-lg font-semibold">{quantity}</span>
              </div>
            )}
            {quantityHelp && <p className="text-xs text-muted-foreground">{quantityHelp}</p>}
          </div>

          <div className="flex flex-col gap-2 pt-1">
            <Button
              variant="outline"
              onClick={() => setShowPreview((current) => !current)}
              disabled={!product || !selectedFormat}
            >
              <Eye className="mr-2 h-4 w-4" />
              {showPreview ? "Ocultar vista previa" : "Mostrar vista previa"}
            </Button>
            <Button size="lg" onClick={onPrint} disabled={!canPrint} className="font-semibold">
              {printing ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Printer className="mr-2 h-4 w-4" />
              )}
              {printButtonLabel}
            </Button>
          </div>
        </CardContent>
      </Card>

      {showPreview && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Vista previa</CardTitle>
            <CardDescription>Maqueta visual aproximada - no es el resultado real.</CardDescription>
          </CardHeader>
          <CardContent>
            <LabelPreview
              product={product}
              format={selectedFormat}
              quantity={previewQuantity ?? quantity}
            />
          </CardContent>
        </Card>
      )}
    </div>
  );
}
