import { useEffect, useMemo, useState } from "react";
import { FileText, RefreshCw, Search, Warehouse } from "lucide-react";
import { toast } from "sonner";
import { AppLayout } from "@/shared/layouts/app-layout";
import { PrintConfigurationPanel } from "@/shared/components/print-configuration-panel";
import { Button } from "@/shared/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select";
import { TableRender } from "@/shared/layouts/table-render";
import { Badge } from "@/shared/ui/badge";
import { InventoryPagination } from "@/features/inventory/components/inventory-pagination";
import { BatchSelectionTable } from "@/features/inventory/components/batch-selection-table";
import { PrepareBatchDialog } from "@/features/inventory/components/prepare-batch-dialog";
import {
  getFormats,
  getInventoryEntryDocumentItems,
  getInventoryEntryDocuments,
  getInventoryPrintSettings,
  getInventoryWarehouses,
  printInventoryEntryBatch,
  syncInventory,
} from "@/shared/api/api";

const PAGE_SIZE = 50;
const headClassName =
  "sticky top-0 z-10 bg-card px-1.5 text-center align-middle text-xs text-foreground shadow-sm 2xl:text-sm";
const centerCellClassName = "text-center align-middle text-xs text-foreground 2xl:text-sm";
const centerMonoCellClassName =
  "text-center align-middle font-mono text-xs text-foreground 2xl:text-sm";

function automaticQuantity(entryQuantity, product) {
  const quantityPerUnit = Number(product.quantity_per_unit);
  if (!Number.isFinite(quantityPerUnit) || quantityPerUnit <= 0) return 0;
  return Math.floor(Math.ceil(Number(entryQuantity)) / quantityPerUnit);
}

function toBatchInventory(entry) {
  return {
    id: entry.id,
    warehouse: entry.warehouse,
    reference: entry.reference,
    inventory_quantity: entry.entry_quantity,
    presentations: entry.presentations,
    printable: entry.printable,
    unavailable_reason: entry.unavailable_reason,
  };
}

export function InventoryEntryPrintPage() {
  const [warehouses, setWarehouses] = useState([]);
  const [warehouse, setWarehouse] = useState("");
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [documents, setDocuments] = useState([]);
  const [totalDocuments, setTotalDocuments] = useState(0);
  const [page, setPage] = useState(1);
  const [loadingDocuments, setLoadingDocuments] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [entryItems, setEntryItems] = useState([]);
  const [loadingItems, setLoadingItems] = useState(false);
  const [formats, setFormats] = useState([]);
  const [formatId, setFormatId] = useState("");
  const [maxLabels, setMaxLabels] = useState(400);
  const [selected, setSelected] = useState(new Map());
  const [prepareOpen, setPrepareOpen] = useState(false);
  const [printing, setPrinting] = useState(false);

  useEffect(() => {
    Promise.all([getInventoryWarehouses(), getFormats(), getInventoryPrintSettings()])
      .then(([nextWarehouses, nextFormats, nextSettings]) => {
        setWarehouses(nextWarehouses);
        setWarehouse(nextWarehouses.includes("1018") ? "1018" : (nextWarehouses[0] ?? ""));
        setFormats(nextFormats);
        setFormatId(nextFormats[0] ? String(nextFormats[0].id) : "");
        setMaxLabels(nextSettings.max_labels_per_batch);
      })
      .catch((error) => {
        toast.error("No se pudo preparar la impresion por entrada", {
          description: error instanceof Error ? error.message : "Error desconocido",
        });
      });
  }, []);

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      setPage(1);
      setDebouncedQuery(query);
    }, 250);
    return () => window.clearTimeout(timeout);
  }, [query]);

  useEffect(() => {
    if (!warehouse) return;
    let active = true;
    setLoadingDocuments(true);
    getInventoryEntryDocuments(warehouse, debouncedQuery, page, PAGE_SIZE)
      .then((result) => {
        if (!active) return;
        setDocuments(result.items);
        setTotalDocuments(result.total);
      })
      .catch((error) => {
        if (!active) return;
        toast.error("No se pudieron consultar documentos", {
          description: error instanceof Error ? error.message : "Error desconocido",
        });
      })
      .finally(() => {
        if (active) setLoadingDocuments(false);
      });
    return () => {
      active = false;
    };
  }, [warehouse, debouncedQuery, page, refreshKey]);

  const selectedItems = useMemo(() => Array.from(selected.values()), [selected]);
  const totalLabels = selectedItems.reduce((sum, item) => sum + item.quantity, 0);
  const selectedFormat = formats.find((format) => String(format.id) === formatId) ?? null;
  const previewItem = selectedItems[0] ?? null;
  const previewProduct = previewItem?.product ?? previewItem?.inventory.presentations[0] ?? null;
  const printableItems = selectedItems.filter((item) => item.product && item.quantity > 0);
  const unresolved = selectedItems.some((item) => item.quantity > 0 && !item.product);
  const overLimit = totalLabels > maxLabels;
  const canOpenPreparation =
    selectedItems.length > 0 && !!selectedDocument && !!selectedFormat && !printing;
  const canSubmit = canOpenPreparation && !unresolved && totalLabels > 0 && !overLimit;
  const totalPages = Math.max(1, Math.ceil(totalDocuments / PAGE_SIZE));

  function changeWarehouse(value) {
    setWarehouse(value);
    setPage(1);
    setSelectedDocument(null);
    setEntryItems([]);
    setSelected(new Map());
  }

  async function selectDocument(document) {
    setSelectedDocument(document);
    setEntryItems([]);
    setSelected(new Map());
    setLoadingItems(true);
    try {
      const items = await getInventoryEntryDocumentItems(document.warehouse, document.document);
      setEntryItems(items);
      const nextSelection = new Map();
      for (const item of items) {
        if (!item.printable) continue;
        const inventory = toBatchInventory(item);
        const product = item.presentations.length === 1 ? item.presentations[0] : null;
        const calculated = product ? automaticQuantity(item.entry_quantity, product) : 0;
        nextSelection.set(item.id, {
          inventory,
          product,
          quantity: calculated,
          automaticQuantity: calculated,
          manuallyAdjusted: false,
        });
      }
      setSelected(nextSelection);
    } catch (error) {
      toast.error("No se pudo cargar el documento", {
        description: error instanceof Error ? error.message : "Error desconocido",
      });
    } finally {
      setLoadingItems(false);
    }
  }

  function updateSelected(entryId, updater) {
    setSelected((current) => {
      const existing = current.get(entryId);
      if (!existing) return current;
      const next = new Map(current);
      next.set(entryId, updater(existing));
      return next;
    });
  }

  function choosePresentation(entryId, productId) {
    updateSelected(entryId, (item) => {
      const product =
        item.inventory.presentations.find((candidate) => candidate.id === Number(productId)) ??
        null;
      const calculated = product
        ? automaticQuantity(item.inventory.inventory_quantity, product)
        : 0;
      return {
        ...item,
        product,
        quantity: calculated,
        automaticQuantity: calculated,
        manuallyAdjusted: false,
      };
    });
  }

  function setItemQuantity(entryId, quantity) {
    updateSelected(entryId, (item) => ({ ...item, quantity, manuallyAdjusted: true }));
  }

  function removeSelected(entryId) {
    setSelected((current) => {
      const next = new Map(current);
      next.delete(entryId);
      return next;
    });
  }

  async function synchronizeWithSiesa() {
    setRefreshing(true);
    let synchronized = true;
    try {
      await syncInventory();
    } catch (error) {
      synchronized = false;
      toast.warning("No hubo sincronizacion externa", {
        description:
          error instanceof Error
            ? `${error.message} Se recargaran los datos actuales de PostgreSQL.`
            : "Se recargaran los datos actuales de PostgreSQL.",
      });
    } finally {
      setPage(1);
      setSelectedDocument(null);
      setEntryItems([]);
      setSelected(new Map());
      setRefreshKey((value) => value + 1);
      setRefreshing(false);
    }
    if (synchronized) toast.success("Sincronizacion con Siesa completada");
  }

  async function handlePrint() {
    if (!selectedFormat || !selectedDocument || !canSubmit) return;
    setPrinting(true);
    try {
      const result = await printInventoryEntryBatch({
        format: selectedFormat.code,
        warehouse: selectedDocument.warehouse,
        document: selectedDocument.document,
        items: printableItems.map((item) => ({
          entry_id: item.inventory.id,
          product_id: item.product.id,
          quantity: item.quantity,
        })),
      });
      if (result.status === "success") {
        toast.success(`Lote #${result.batch_id} enviado`, {
          description: `${result.printed_labels} etiquetas impresas.`,
        });
      } else {
        toast.warning(`Lote #${result.batch_id} finalizado con errores`, {
          description: result.message || "Revisa el historial del lote.",
          duration: 10000,
        });
      }
      setPrepareOpen(false);
      setSelected(new Map());
    } catch (error) {
      toast.error("No se pudo imprimir el lote", {
        description: error instanceof Error ? error.message : "Error desconocido",
      });
    } finally {
      setPrinting(false);
    }
  }

  const documentColumns = [
    {
      key: "provider",
      header: "Proveedor",
      headClassName: `${headClassName} w-56`,
      cellClassName: centerCellClassName,
      render: (item) => (
        <span className="line-clamp-2">{item.provider_name || "Sin proveedor"}</span>
      ),
    },
    {
      key: "document",
      header: "Documento",
      headClassName,
      cellClassName: centerMonoCellClassName,
      render: (item) => item.document,
    },
    {
      key: "date",
      header: "Fecha",
      headClassName: `${headClassName} w-32`,
      cellClassName: centerCellClassName,
      render: (item) => item.date,
    },
    {
      key: "warehouse",
      header: "Bodega",
      headClassName: `${headClassName} w-24`,
      cellClassName: centerMonoCellClassName,
      render: (item) => item.warehouse,
    },
    {
      key: "references",
      header: "Refs.",
      headClassName: `${headClassName} w-20`,
      cellClassName: centerMonoCellClassName,
      render: (item) => item.reference_count,
    },
    {
      key: "quantity",
      header: "Entrada",
      headClassName: `${headClassName} w-28`,
      cellClassName: centerMonoCellClassName,
      render: (item) => Number(item.total_entry_quantity).toLocaleString(),
    },
  ];

  const itemColumns = [
    {
      key: "line",
      header: "Linea",
      headClassName: `${headClassName} w-32`,
      cellClassName: centerCellClassName,
      render: (item) => item.presentations[0]?.line ?? "Sin linea",
    },
    {
      key: "reference",
      header: "Referencia",
      headClassName: `${headClassName} w-28`,
      cellClassName: centerMonoCellClassName,
      render: (item) => item.reference,
    },
    {
      key: "description",
      header: "Descripcion",
      headClassName,
      cellClassName: "text-center align-middle text-sm text-foreground",
      render: (item) => item.presentations[0]?.description ?? "Producto no registrado",
    },
    {
      key: "quantity",
      header: "Entrada",
      headClassName: `${headClassName} w-28`,
      cellClassName: centerMonoCellClassName,
      render: (item) => Number(item.entry_quantity).toLocaleString(),
    },
    {
      key: "presentations",
      header: "Presentaciones",
      headClassName: `${headClassName} w-32`,
      cellClassName: centerCellClassName,
      render: (item) => item.presentations.length || "-",
    },
    {
      key: "status",
      header: "Estado",
      headClassName: `${headClassName} w-36`,
      cellClassName: centerCellClassName,
      render: (item) =>
        item.printable ? (
          <Badge variant="secondary">Imprimible</Badge>
        ) : (
          <span className="text-xs text-destructive">{item.unavailable_reason}</span>
        ),
    },
  ];

  return (
    <AppLayout
      title="Imprimir por entrada"
      subtitle="Selecciona un documento de entrada y prepara etiquetas desde sus articulos."
      actions={
        <Button variant="outline" size="sm" onClick={synchronizeWithSiesa} disabled={refreshing}>
          <RefreshCw className={`h-4 w-4 sm:mr-2 ${refreshing ? "animate-spin" : ""}`} />
          <span className="hidden sm:inline">Sincronizar con Siesa</span>
        </Button>
      }
    >
      <div className="grid w-full min-w-0 max-w-full gap-6 xl:grid-cols-3">
        <div className="w-full min-w-0 max-w-full space-y-6 xl:col-span-2">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Documentos de entrada</CardTitle>
              <CardDescription>Filtra por bodega y selecciona el documento a imprimir.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Button
                variant="outline"
                className="w-full sm:hidden"
                onClick={synchronizeWithSiesa}
                disabled={refreshing}
              >
                <RefreshCw className={`mr-2 h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
                Sincronizar con Siesa
              </Button>
              <div className="grid gap-3 md:grid-cols-[180px_1fr]">
                <div className="space-y-1.5">
                  <Label>Bodega</Label>
                  <Select value={warehouse} onValueChange={changeWarehouse}>
                    <SelectTrigger>
                      <Warehouse className="mr-2 h-4 w-4" />
                      <SelectValue placeholder="Bodega" />
                    </SelectTrigger>
                    <SelectContent>
                      {warehouses.map((value) => (
                        <SelectItem key={value} value={value}>
                          {value}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label>Buscar documento</Label>
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input
                      value={query}
                      onChange={(event) => setQuery(event.target.value)}
                      placeholder="Documento o referencia"
                      className="pl-9"
                    />
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="overflow-hidden">
            <CardContent className="p-0">
              <TableRender
                columns={documentColumns}
                items={documents}
                loading={loadingDocuments}
                emptyMessage="No hay documentos para los filtros seleccionados."
                tableClassName="min-w-[900px]"
                containerClassName="max-h-[360px]"
                rowKey={(item) => `${item.warehouse}-${item.document}`}
                rowProps={(item) => ({
                  onClick: () => selectDocument(item),
                  className: `cursor-pointer ${
                    selectedDocument?.document === item.document &&
                    selectedDocument?.warehouse === item.warehouse
                      ? "bg-accent/60"
                      : ""
                  }`,
                })}
              />
            </CardContent>
            <InventoryPagination
              page={page}
              totalPages={totalPages}
              totalItems={totalDocuments}
              loading={loadingDocuments}
              onPageChange={setPage}
            />
          </Card>

          <Card className="overflow-hidden">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-base">
                <FileText className="h-4 w-4" />
                {selectedDocument ? selectedDocument.document : "Articulos del documento"}
              </CardTitle>
              <CardDescription>
                {selectedDocument
                  ? `${entryItems.length} articulo(s) en bodega ${selectedDocument.warehouse}`
                  : "Selecciona un documento para ver sus entradas."}
              </CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              <TableRender
                columns={itemColumns}
                items={entryItems}
                loading={loadingItems}
                emptyMessage="Selecciona un documento de entrada."
                tableClassName="min-w-[860px]"
                containerClassName="max-h-[420px]"
                rowKey={(item) => item.id}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Seleccion del lote</CardTitle>
              <CardDescription>
                {selectedItems.length} articulo(s), {totalLabels} de {maxLabels} etiquetas.
              </CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              {selectedItems.length === 0 ? (
                <div className="py-10 text-center text-sm text-muted-foreground">
                  Selecciona un documento con articulos imprimibles.
                </div>
              ) : (
                <BatchSelectionTable items={selectedItems} onRemove={removeSelected} />
              )}
            </CardContent>
          </Card>
        </div>

        <div className="xl:sticky xl:top-20 xl:self-start">
          <PrintConfigurationPanel
            formats={formats}
            formatId={formatId}
            onFormatChange={setFormatId}
            product={previewProduct}
            quantity={totalLabels}
            previewQuantity={Math.max(1, previewItem?.quantity ?? 1)}
            quantityLabel="Etiquetas del lote"
            quantityHelp={`Limite configurado: ${maxLabels}. Las cantidades se ajustan antes de imprimir.`}
            description={
              selectedDocument
                ? `Documento ${selectedDocument.document} en bodega ${selectedDocument.warehouse}`
                : "Selecciona un documento de entrada"
            }
            printing={printing}
            canPrint={canOpenPreparation}
            onPrint={() => setPrepareOpen(true)}
            printButtonLabel="Preparar lote"
          />
        </div>
      </div>

      <PrepareBatchDialog
        open={prepareOpen}
        onOpenChange={setPrepareOpen}
        items={selectedItems}
        maxLabels={maxLabels}
        totalLabels={totalLabels}
        overLimit={overLimit}
        unresolved={unresolved}
        canSubmit={canSubmit}
        printing={printing}
        quantityLabel="Entrada"
        onChoosePresentation={choosePresentation}
        onQuantityChange={setItemQuantity}
        onPrint={handlePrint}
      />
    </AppLayout>
  );
}
