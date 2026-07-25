import { CheckCircle2, Printer, Wifi, WifiOff, XCircle } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";
import { StatusRow } from "./status-row";

export function SystemStatusCard({ backendOk, printerName, lastResult }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Estado del sistema</CardTitle>
        <CardDescription>Información del backend y de la última prueba.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <StatusRow
          label="API local"
          ok={backendOk === true}
          pending={backendOk === null}
          okText="Alcanzable"
          failText="No responde"
          icon={backendOk ? <Wifi className="h-4 w-4" /> : <WifiOff className="h-4 w-4" />}
        />
        <StatusRow
          label="Impresora"
          ok={!!printerName}
          okText="Configurada"
          failText="No configurada"
          icon={<Printer className="h-4 w-4" />}
        />
        <div className="rounded-md border bg-muted/40 p-3 text-sm">
          <div className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Último test
          </div>
          {lastResult ? (
            <div className="flex items-start gap-2">
              {lastResult.ok ? (
                <CheckCircle2 className="mt-0.5 h-4 w-4 text-success" />
              ) : (
                <XCircle className="mt-0.5 h-4 w-4 text-destructive" />
              )}
              <div>
                <div className="font-medium">{lastResult.message}</div>
                <div className="text-xs text-muted-foreground">
                  {new Date(lastResult.at).toLocaleString()}
                </div>
              </div>
            </div>
          ) : (
            <div className="text-muted-foreground">Sin pruebas todavía.</div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
