import { Loader2 } from "lucide-react";
import { Button } from "@/shared/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";

export function InventoryLimitCard({ value, onChange, saving, onSave }) {
  return (
    <Card className="lg:col-span-2">
      <CardHeader>
        <CardTitle className="text-base">Impresión desde inventario</CardTitle>
        <CardDescription>
          Límite máximo permitido para la suma de etiquetas de un lote.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3 sm:flex-row sm:items-end">
        <div className="w-full max-w-xs space-y-2">
          <Label htmlFor="inventory-print-limit">Etiquetas por lote</Label>
          <Input
            id="inventory-print-limit"
            type="number"
            min={1}
            value={value}
            onChange={(event) =>
              onChange(Math.max(1, Number.parseInt(event.target.value || "1", 10)))
            }
          />
        </div>
        <Button onClick={onSave} disabled={saving}>
          {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          Guardar límite
        </Button>
      </CardContent>
    </Card>
  );
}
