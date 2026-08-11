import { Loader2, Printer } from "lucide-react";
import { Button } from "@/shared/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";

export function PrinterCard({
  printerName,
  onPrinterNameChange,
  testing,
  printingTest,
  onTest,
  onTestLabel,
}) {
  return (
    <Card className="min-w-0">
      <CardHeader>
        <CardTitle className="text-base">Impresora configurada</CardTitle>
        <CardDescription>Cola configurada en el agente Windows.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="printer">Nombre de impresora</Label>
          <Input
            id="printer"
            value={printerName}
            onChange={(e) => onPrinterNameChange(e.target.value)}
            readOnly
          />
        </div>
        <div className="flex flex-wrap gap-2">
          <Button onClick={onTest} disabled={testing}>
            {testing ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Printer className="mr-2 h-4 w-4" />
            )}
            Probar impresora
          </Button>
          <Button variant="outline" onClick={onTestLabel} disabled={printingTest}>
            {printingTest ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Printer className="mr-2 h-4 w-4" />
            )}
            Imprimir etiqueta de prueba
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
