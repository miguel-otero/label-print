import { useEffect, useMemo, useState } from "react";
import { Search } from "lucide-react";
import { toast } from "sonner";
import { AppLayout } from "@/shared/layouts/app-layout";
import { Button } from "@/shared/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";
import { Input } from "@/shared/ui/input";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/shared/ui/sheet";
import { BatchTable } from "@/features/history/components/batch-table";
import { IndividualTable } from "@/features/history/components/individual-table";
import { StatusBadge } from "@/features/history/components/status-badge";
import { DetailRow } from "@/features/history/components/detail-row";
import { getBatchHistory, getHistory, retryPrintJob } from "@/shared/api/api";

export function HistoryPage() {
  const [individual, setIndividual] = useState([]);
  const [batches, setBatches] = useState([]);
  const [view, setView] = useState("batches");
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [date, setDate] = useState("");
  const [selectedBatch, setSelectedBatch] = useState(null);
  const [selectedIndividual, setSelectedIndividual] = useState(null);
  const [retryingJobId, setRetryingJobId] = useState(null);

  async function handleRetry(item) {
    if (!item.job_id || !window.confirm("¿Desea volver a enviar este trabajo a la cola de impresión?")) return;
    setRetryingJobId(item.job_id);
    try {
      const result = await retryPrintJob(item.job_id);
      toast.success(`Trabajo #${result.job_id} agregado nuevamente a la cola.`);
      setSelectedBatch(null);
      setSelectedIndividual(null);
    } catch (error) {
      toast.error(error.message || "No fue posible reintentar el trabajo.");
    } finally {
      setRetryingJobId(null);
    }
  }

  useEffect(() => {
    let active = true;
    async function refreshHistory() {
      const [nextIndividual, nextBatches] = await Promise.all([getHistory(), getBatchHistory()]);
      if (!active) return;
      setIndividual(nextIndividual);
      setBatches(nextBatches);
      setLoading(false);
    }
    refreshHistory();
    const interval = window.setInterval(refreshHistory, 3000);
    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, []);

  const filteredBatches = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return batches.filter((batch) => {
      const matchesQuery =
        !normalized ||
        batch.format.toLowerCase().includes(normalized) ||
        batch.warehouse.toLowerCase().includes(normalized) ||
        (batch.source_document ?? "").toLowerCase().includes(normalized) ||
        batch.items.some(
          (item) =>
            item.reference.toLowerCase().includes(normalized) ||
            item.description.toLowerCase().includes(normalized),
        );
      return matchesQuery && (!date || batch.timestamp.startsWith(date));
    });
  }, [batches, query, date]);

  const filteredIndividual = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return individual.filter((item) => {
      const matchesQuery =
        !normalized ||
        item.product_code.toLowerCase().includes(normalized) ||
        item.product_description.toLowerCase().includes(normalized) ||
        item.format.toLowerCase().includes(normalized);
      return matchesQuery && (!date || item.timestamp.startsWith(date));
    });
  }, [individual, query, date]);

  return (
    <AppLayout title="Historial de impresión" subtitle="Impresiones individuales y por inventario">
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Filtros</CardTitle>
          <CardDescription>Buscar por producto, formato, bodega o fecha.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex gap-2">
            <Button
              size="sm"
              variant={view === "batches" ? "default" : "outline"}
              onClick={() => setView("batches")}
            >
              Lotes de inventario
            </Button>
            <Button
              size="sm"
              variant={view === "individual" ? "default" : "outline"}
              onClick={() => setView("individual")}
            >
              Etiquetas individuales
            </Button>
          </div>
          <div className="grid gap-3 sm:grid-cols-[1fr_220px]">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Buscar por referencia o descripción"
                className="pl-9"
              />
            </div>
            <Input type="date" value={date} onChange={(event) => setDate(event.target.value)} />
          </div>
        </CardContent>
      </Card>

      <Card className="mt-6">
        <CardHeader className="pb-3">
          <CardTitle className="text-base">
            {view === "batches" ? "Lotes de inventario" : "Impresiones individuales"}
          </CardTitle>
          <CardDescription>
            {view === "batches" ? filteredBatches.length : filteredIndividual.length} resultado(s)
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {view === "batches" ? (
            <BatchTable items={filteredBatches} loading={loading} onSelect={setSelectedBatch} />
          ) : (
            <IndividualTable
              items={filteredIndividual}
              loading={loading}
              onSelect={setSelectedIndividual}
            />
          )}
        </CardContent>
      </Card>

      <Sheet open={!!selectedBatch} onOpenChange={(open) => !open && setSelectedBatch(null)}>
        <SheetContent className="overflow-y-auto sm:max-w-xl">
          {selectedBatch && (
            <>
              <SheetHeader>
                <SheetTitle>Lote de inventario #{selectedBatch.id}</SheetTitle>
                <SheetDescription>
                  {new Date(selectedBatch.timestamp).toLocaleString()}
                </SheetDescription>
              </SheetHeader>
              <div className="mt-6 space-y-3 text-sm">
                <DetailRow label="Usuario" value={selectedBatch.user} />
                <DetailRow label="Bodega" value={selectedBatch.warehouse} />
                <DetailRow
                  label="Origen"
                  value={
                    selectedBatch.source === "inventory_entry"
                      ? "Entrada de inventario"
                      : "Inventario"
                  }
                />
                {selectedBatch.source_document && (
                  <DetailRow label="Documento" value={selectedBatch.source_document} />
                )}
                {selectedBatch.source_date && (
                  <DetailRow label="Fecha documento" value={selectedBatch.source_date} />
                )}
                <DetailRow label="Formato" value={selectedBatch.format} />
                <DetailRow
                  label="Resultado"
                  value={`${selectedBatch.printed_labels} impresas · ${selectedBatch.failed_labels} con error`}
                />
                <DetailRow label="Estado" value={<StatusBadge status={selectedBatch.status} />} />
                {selectedBatch.message && (
                  <DetailRow label="Mensaje" value={selectedBatch.message} />
                )}
                {["error", "unknown"].includes(selectedBatch.status) && selectedBatch.job_id && (
                  <Button type="button" variant="destructive" disabled={retryingJobId === selectedBatch.job_id} onClick={() => handleRetry(selectedBatch)}>
                    {retryingJobId === selectedBatch.job_id ? "Reintentando..." : "Reintentar impresión"}
                  </Button>
                )}
                <div className="pt-2">
                  <h3 className="mb-2 text-sm font-semibold">Artículos</h3>
                  <div className="divide-y rounded-md border">
                    {selectedBatch.items.map((item, index) => (
                      <div key={`${item.product_id}-${index}`} className="space-y-1 p-3">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <div className="font-mono text-xs">{item.reference}</div>
                            <div className="text-xs text-muted-foreground">{item.description}</div>
                          </div>
                          <StatusBadge status={item.status} />
                        </div>
                        <div className="text-xs">
                          {item.presentation} · {item.printed_labels}/{item.requested_labels}{" "}
                          impresas
                        </div>
                        {item.message && (
                          <div className="text-xs text-destructive">{item.message}</div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>

      <Sheet
        open={!!selectedIndividual}
        onOpenChange={(open) => !open && setSelectedIndividual(null)}
      >
        <SheetContent>
          {selectedIndividual && (
            <>
              <SheetHeader>
                <SheetTitle>Detalle de impresión #{selectedIndividual.id}</SheetTitle>
                <SheetDescription>
                  {new Date(selectedIndividual.timestamp).toLocaleString()}
                </SheetDescription>
              </SheetHeader>
              <div className="mt-6 space-y-3 text-sm">
                <DetailRow label="Usuario" value={selectedIndividual.user} />
                <DetailRow
                  label="Producto"
                  value={`${selectedIndividual.product_code} - ${selectedIndividual.product_description}`}
                />
                <DetailRow label="Formato" value={selectedIndividual.format} />
                <DetailRow label="Cantidad" value={String(selectedIndividual.quantity)} />
                <DetailRow
                  label="Estado"
                  value={<StatusBadge status={selectedIndividual.status} />}
                />
                {selectedIndividual.message && (
                  <DetailRow label="Mensaje" value={selectedIndividual.message} />
                )}
                {["error", "unknown"].includes(selectedIndividual.status) && selectedIndividual.job_id && (
                  <Button type="button" variant="destructive" disabled={retryingJobId === selectedIndividual.job_id} onClick={() => handleRetry(selectedIndividual)}>
                    {retryingJobId === selectedIndividual.job_id ? "Reintentando..." : "Reintentar impresión"}
                  </Button>
                )}
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>
    </AppLayout>
  );
}
