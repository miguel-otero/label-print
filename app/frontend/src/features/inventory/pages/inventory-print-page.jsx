import { useEffect, useMemo, useState } from "react";
import { RefreshCw, Search, Warehouse } from "lucide-react";
import { toast } from "sonner";
import { AppLayout } from "@/shared/layouts/app-layout";
import { PrintConfigurationPanel } from "@/shared/components/print-configuration-panel";
import { Button } from "@/shared/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select";
import { InventoryTable } from "@/features/inventory/components/inventory-table";
import { InventoryPagination } from "@/features/inventory/components/inventory-pagination";
import { BatchSelectionTable } from "@/features/inventory/components/batch-selection-table";
import { PrepareBatchDialog } from "@/features/inventory/components/prepare-batch-dialog";
import { LineFilter } from "@/features/print/components/line-filter";
import {
  getFormats,
  getInventoryPrintSettings,
  getInventoryWarehouses,
  getProductLines,
  printInventoryBatch,
  refreshInventorySelection,
  searchInventory,
  syncInventory,
} from "@/shared/api/api";

const PAGE_SIZE = 100;
const BULK_SELECTION_PAGE_SIZE = 10000;

function automaticQuantity(inventory, product) {
  const quantityPerUnit = Number(product.quantity_per_unit);
  if (!Number.isFinite(quantityPerUnit) || quantityPerUnit <= 0) return 0;
  return Math.floor(Math.ceil(Number(inventory)) / quantityPerUnit);
}

function createSelectedInventoryItem(item) {
  const product = item.presentations.length === 1 ? item.presentations[0] : null;
  const calculated = product ? automaticQuantity(item.inventory_quantity, product) : 0;
  return {
    inventory: item,
    product,
    quantity: calculated,
    automaticQuantity: calculated,
    manuallyAdjusted: false,
  };
}

export function InventoryPrintPage() {
  const [warehouses, setWarehouses] = useState([]);
  const [warehouse, setWarehouse] = useState("");
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [productLines, setProductLines] = useState([]);
  const [selectedLines, setSelectedLines] = useState([]);
  const [lineFilterOpen, setLineFilterOpen] = useState(false);
  const [availability, setAvailability] = useState("all");
  const [items, setItems] = useState([]);
  const [totalItems, setTotalItems] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [formats, setFormats] = useState([]);
  const [formatId, setFormatId] = useState("");
  const [maxLabels, setMaxLabels] = useState(400);
  const [selected, setSelected] = useState(new Map());
  const [prepareOpen, setPrepareOpen] = useState(false);
  const [printing, setPrinting] = useState(false);
  const [bulkSelecting, setBulkSelecting] = useState(false);

  useEffect(() => {
    Promise.all([
      getInventoryWarehouses(),
      getFormats(),
      getInventoryPrintSettings(),
      getProductLines(),
    ])
      .then(([nextWarehouses, nextFormats, nextSettings, nextProductLines]) => {
        setWarehouses(nextWarehouses);
        setWarehouse(nextWarehouses.includes("1018") ? "1018" : (nextWarehouses[0] ?? ""));
        setFormats(nextFormats);
        setFormatId(nextFormats[0] ? String(nextFormats[0].id) : "");
        setMaxLabels(nextSettings.max_labels_per_batch);
        setProductLines(nextProductLines);
      })
      .catch((error) => {
        toast.error("No se pudo preparar la impresión de inventario", {
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
    setLoading(true);
    searchInventory(warehouse, debouncedQuery, availability, page, PAGE_SIZE, selectedLines)
      .then((result) => {
        if (!active) return;
        setItems(result.items);
        setTotalItems(result.total);
      })
      .catch((error) => {
        if (!active) return;
        toast.error("No se pudo consultar el inventario", {
          description: error instanceof Error ? error.message : "Error desconocido",
        });
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [warehouse, debouncedQuery, availability, page, refreshKey, selectedLines]);

  const selectedItems = useMemo(() => Array.from(selected.values()), [selected]);
  const totalLabels = selectedItems.reduce((sum, item) => sum + item.quantity, 0);
  const selectedFormat = formats.find((format) => String(format.id) === formatId) ?? null;
  const previewItem = selectedItems[0] ?? null;
  const previewProduct = previewItem?.product ?? previewItem?.inventory.presentations[0] ?? null;
  const printableItems = selectedItems.filter((item) => item.product && item.quantity > 0);
  const unresolved = selectedItems.some((item) => item.quantity > 0 && !item.product);
  const overLimit = totalLabels > maxLabels;
  const canOpenPreparation = selectedItems.length > 0 && !!selectedFormat && !printing;
  const canSubmit = canOpenPreparation && !unresolved && totalLabels > 0 && !overLimit;
  const totalPages = Math.max(1, Math.ceil(totalItems / PAGE_SIZE));
  const visiblePrintableItems = items.filter((item) => item.printable);
  const allFilteredSelected =
    visiblePrintableItems.length > 0 && visiblePrintableItems.every((item) => selected.has(item.id));
  const someFilteredSelected = visiblePrintableItems.some((item) => selected.has(item.id));
  const selectedLineCount = selectedLines.length;
  const lineFilterLabel =
    selectedLineCount === 0
      ? "Todas"
      : `${selectedLineCount} linea${selectedLineCount === 1 ? "" : "s"}`;

  function changeWarehouse(value) {
    setWarehouse(value);
    setPage(1);
    setSelected(new Map());
  }

  function toggleLine(line) {
    setPage(1);
    setSelectedLines((current) =>
      current.includes(line) ? current.filter((item) => item !== line) : [...current, line],
    );
  }

  function selectAllLines() {
    setPage(1);
    setSelectedLines([]);
  }

  function toggleItem(item) {
    if (!item.printable) return;
    setSelected((current) => {
      const next = new Map(current);
      if (next.has(item.id)) {
        next.delete(item.id);
        return next;
      }
      next.set(item.id, createSelectedInventoryItem(item));
      return next;
    });
  }

  async function toggleAllFilteredItems() {
    if (!warehouse || bulkSelecting || totalItems === 0) return;
    setBulkSelecting(true);
    try {
      const filteredItems = [];
      let nextPage = 1;
      let expectedTotal = totalItems;
      while (filteredItems.length < expectedTotal) {
        const result = await searchInventory(
          warehouse,
          debouncedQuery,
          availability,
          nextPage,
          BULK_SELECTION_PAGE_SIZE,
          selectedLines,
        );
        if (result.items.length === 0) break;
        filteredItems.push(...result.items);
        expectedTotal = result.total;
        nextPage += 1;
      }
      const printableItems = filteredItems.filter((item) => item.printable);
      if (printableItems.length === 0) {
        toast.info("No hay productos imprimibles en el filtro actual.");
        return;
      }
      let added = 0;
      let removed = 0;
      setSelected((current) => {
        const next = new Map(current);
        const allAlreadySelected = printableItems.every((item) => next.has(item.id));
        if (allAlreadySelected) {
          for (const item of printableItems) {
            if (next.delete(item.id)) removed += 1;
          }
          return next;
        }
        for (const item of printableItems) {
          if (next.has(item.id)) continue;
          next.set(item.id, createSelectedInventoryItem(item));
          added += 1;
        }
        return next;
      });
      if (removed > 0) {
        toast.success(`${removed} producto(s) filtrado(s) removidos de la seleccion.`);
      } else {
        toast.success(`${added} producto(s) filtrado(s) agregados a la seleccion.`);
      }
    } catch (error) {
      toast.error("No se pudo seleccionar el inventario filtrado", {
        description: error instanceof Error ? error.message : "Error desconocido",
      });
    } finally {
      setBulkSelecting(false);
    }
  }

  function updateSelected(inventoryId, updater) {
    setSelected((current) => {
      const existing = current.get(inventoryId);
      if (!existing) return current;
      const next = new Map(current);
      next.set(inventoryId, updater(existing));
      return next;
    });
  }

  function choosePresentation(inventoryId, productId) {
    updateSelected(inventoryId, (item) => {
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

  function setItemQuantity(inventoryId, quantity) {
    updateSelected(inventoryId, (item) => ({ ...item, quantity, manuallyAdjusted: true }));
  }

  function removeSelected(inventoryId) {
    setSelected((current) => {
      const next = new Map(current);
      next.delete(inventoryId);
      return next;
    });
  }

  async function refreshInventory() {
    setRefreshing(true);
    let synchronized = true;
    try {
      await syncInventory();
    } catch (error) {
      synchronized = false;
      toast.warning("No hubo sincronización externa", {
        description:
          error instanceof Error
            ? `${error.message} Se recargarán los datos actuales de PostgreSQL.`
            : "Se recargarán los datos actuales de PostgreSQL.",
      });
    } finally {
      if (selectedItems.length > 0) {
        try {
          const refreshedItems = await refreshInventorySelection(
            warehouse,
            selectedItems.map((item) => item.inventory.reference),
          );
          const refreshedByReference = new Map(
            refreshedItems.map((item) => [item.reference, item]),
          );
          const nextSelection = new Map();
          for (const previous of selectedItems) {
            const refreshed = refreshedByReference.get(previous.inventory.reference);
            if (!refreshed?.printable) continue;
            const product =
              refreshed.presentations.find((candidate) => candidate.id === previous.product?.id) ??
              (refreshed.presentations.length === 1 ? refreshed.presentations[0] : null);
            const calculated = product
              ? automaticQuantity(refreshed.inventory_quantity, product)
              : 0;
            nextSelection.set(refreshed.id, {
              inventory: refreshed,
              product,
              automaticQuantity: calculated,
              quantity: previous.manuallyAdjusted ? previous.quantity : calculated,
              manuallyAdjusted: previous.manuallyAdjusted,
            });
          }
          setSelected(nextSelection);
        } catch {
          setSelected(new Map());
        }
      }
      setPage(1);
      setRefreshKey((value) => value + 1);
      setRefreshing(false);
    }
    if (synchronized) toast.success("Sincronizacion con Siesa completada");
  }

  async function handlePrint() {
    if (!selectedFormat || !canSubmit) return;
    setPrinting(true);
    try {
      const result = await printInventoryBatch({
        format: selectedFormat.code,
        warehouse,
        items: printableItems.map((item) => ({
          inventory_id: item.inventory.id,
          product_id: item.product.id,
          quantity: item.quantity,
        })),
      });
      if (result.status === "success") {
        toast.success(`Lote #${result.batch_id} enviado`, {
          description: `${result.printed_labels} etiquetas impresas.`,
        });
      } else {
        const failedItems = result.items
          .filter((item) => item.status !== "success")
          .map((item) => `${item.reference}: ${item.message ?? "Error de impresión"}`)
          .join(" · ");
        toast.warning(`Lote #${result.batch_id} finalizado con errores`, {
          description: failedItems || result.message || "Revisa el historial del lote.",
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

  return (
    <AppLayout
      title="Imprimir de inventario"
      subtitle="Selecciona existencias de una bodega y prepara un lote de etiquetas."
      actions={
        <Button variant="outline" size="sm" onClick={refreshInventory} disabled={refreshing}>
          <RefreshCw className={`h-4 w-4 sm:mr-2 ${refreshing ? "animate-spin" : ""}`} />
          <span className="hidden sm:inline">Sincronizar con Siesa</span>
        </Button>
      }
    >
      <div className="grid w-full min-w-0 max-w-full gap-6 xl:grid-cols-3">
        <div className="w-full min-w-0 max-w-full space-y-6 xl:col-span-2">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Inventario disponible</CardTitle>
              <CardDescription>
                La cantidad automática depende de la presentación seleccionada.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Button
                variant="outline"
                className="w-full sm:hidden"
                onClick={refreshInventory}
                disabled={refreshing}
              >
                <RefreshCw className={`mr-2 h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
                Sincronizar con Siesa
              </Button>
              <div className="grid gap-3 md:grid-cols-[180px_1fr_180px]">
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
                  <Label>Buscar</Label>
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input
                      value={query}
                      onChange={(event) => setQuery(event.target.value)}
                      placeholder="Referencia, descripción o código de barras"
                      className="pl-9"
                    />
                  </div>
                </div>
                <div className="space-y-1.5">
                  <Label>Disponibilidad</Label>
                  <Select
                    value={availability}
                    onValueChange={(value) => {
                      setAvailability(value);
                      setPage(1);
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Todos</SelectItem>
                      <SelectItem value="printable">Imprimibles</SelectItem>
                      <SelectItem value="unprintable">No imprimibles</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <LineFilter
                productLines={productLines}
                selectedLines={selectedLines}
                open={lineFilterOpen}
                onToggleOpen={() => setLineFilterOpen((open) => !open)}
                onToggleLine={toggleLine}
                onSelectAll={selectAllLines}
                label={lineFilterLabel}
              />
            </CardContent>
          </Card>

          <Card className="overflow-hidden">
            <CardContent className="p-0">
              <InventoryTable
                items={items}
                loading={loading || bulkSelecting}
                isSelected={(item) => selected.has(item.id)}
                onToggle={toggleItem}
                allFilteredSelected={allFilteredSelected}
                someFilteredSelected={someFilteredSelected}
                onToggleAllFiltered={toggleAllFilteredItems}
                selectAllDisabled={loading || bulkSelecting || totalItems === 0}
              />
            </CardContent>
            <InventoryPagination
              page={page}
              totalPages={totalPages}
              totalItems={totalItems}
              loading={loading}
              onPageChange={setPage}
            />
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Selección del lote</CardTitle>
              <CardDescription>
                {selectedItems.length} artículo(s), {totalLabels} de {maxLabels} etiquetas.
              </CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              {selectedItems.length === 0 ? (
                <div className="py-10 text-center text-sm text-muted-foreground">
                  Selecciona uno o más artículos del inventario.
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
            quantityHelp={`Límite configurado: ${maxLabels}. Las cantidades se ajustan antes de imprimir.`}
            description={
              selectedItems.length
                ? `${selectedItems.length} artículo(s) seleccionados en bodega ${warehouse}`
                : "Selecciona artículos de la tabla"
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
        onChoosePresentation={choosePresentation}
        onQuantityChange={setItemQuantity}
        onPrint={handlePrint}
      />
    </AppLayout>
  );
}
