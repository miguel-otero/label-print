import { useEffect, useMemo, useState } from "react";
import { RefreshCw, Search } from "lucide-react";
import { toast } from "sonner";
import { AppLayout } from "@/shared/layouts/app-layout";
import { PrintConfigurationPanel } from "@/shared/components/print-configuration-panel";
import { Button } from "@/shared/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";
import { Input } from "@/shared/ui/input";
import { LineFilter } from "@/features/print/components/line-filter";
import { ProductsTable } from "@/features/print/components/products-table";
import { ProductsPagination } from "@/features/print/components/products-pagination";
import {
  getFormats,
  getProductLines,
  printLabel,
  searchProducts,
  syncInventory,
} from "@/shared/api/api";

const PRODUCTS_PAGE_SIZE = 100;

export function PrintPage() {
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [products, setProducts] = useState([]);
  const [productLines, setProductLines] = useState([]);
  const [selectedLines, setSelectedLines] = useState([]);
  const [lineFilterOpen, setLineFilterOpen] = useState(false);
  const [totalProducts, setTotalProducts] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [formats, setFormats] = useState([]);
  const [selected, setSelected] = useState(null);
  const [formatId, setFormatId] = useState("");
  const [quantity, setQuantity] = useState(1);
  const [printing, setPrinting] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    getFormats().then((f) => {
      setFormats(f);
      if (f.length > 0) setFormatId(String(f[0].id));
    });
    getProductLines()
      .then(setProductLines)
      .catch(() => toast.error("Error al cargar líneas"));
  }, []);

  useEffect(() => {
    const t = setTimeout(() => {
      setPage(1);
      setDebouncedQuery(query);
    }, 250);
    return () => clearTimeout(t);
  }, [query]);

  useEffect(() => {
    runSearch(debouncedQuery, page);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedQuery, page, selectedLines]);

  async function runSearch(q, nextPage) {
    setLoading(true);
    try {
      const data = await searchProducts(q, nextPage, PRODUCTS_PAGE_SIZE, selectedLines);
      setProducts(data.items);
      setTotalProducts(data.total);
    } catch {
      toast.error("Error al buscar productos");
    } finally {
      setLoading(false);
    }
  }

  const selectedFormat = useMemo(
    () => formats.find((f) => String(f.id) === formatId) ?? null,
    [formats, formatId],
  );

  const totalPages = Math.max(1, Math.ceil(totalProducts / PRODUCTS_PAGE_SIZE));
  const pageStart = totalProducts === 0 ? 0 : (page - 1) * PRODUCTS_PAGE_SIZE + 1;
  const pageEnd = Math.min(page * PRODUCTS_PAGE_SIZE, totalProducts);
  const selectedLineCount = selectedLines.length;
  const lineFilterLabel =
    selectedLineCount === 0
      ? "Todas"
      : `${selectedLineCount} línea${selectedLineCount === 1 ? "" : "s"}`;
  const canPrint = !!selected && !!selectedFormat && quantity > 0 && !printing;

  async function handlePrint() {
    if (!selected || !selectedFormat) return;
    setPrinting(true);
    try {
      await printLabel({
        formato: selectedFormat.code,
        producto_id: selected.id,
        cantidad: quantity,
      });
      toast.success("Etiqueta enviada a impresora", {
        description: `${quantity} x ${selected.product_code} (${selectedFormat.code})`,
      });
    } catch (e) {
      toast.error("No se pudo imprimir", {
        description: e instanceof Error ? e.message : "Error desconocido",
      });
    } finally {
      setPrinting(false);
    }
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

  async function synchronizeExternal() {
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
      setPage(1);
      await runSearch(debouncedQuery, 1);
      setRefreshing(false);
    }
    if (synchronized) toast.success("Sincronización externa completada");
  }

  return (
    <AppLayout
      title="Imprimir etiquetas"
      subtitle="Buscar producto y enviar a impresora de etiquetas."
      actions={
        <Button variant="outline" size="sm" onClick={synchronizeExternal} disabled={refreshing}>
          <RefreshCw className={`h-4 w-4 sm:mr-2 ${refreshing ? "animate-spin" : ""}`} />
          <span className="hidden sm:inline">Sincronización Externa</span>
        </Button>
      }
    >
      <div className="grid min-w-0 gap-6 xl:min-h-[calc(100vh-6.5rem)] xl:grid-cols-3">
        <div className="flex min-w-0 flex-col gap-6 xl:col-span-2 xl:min-h-0">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Buscar producto</CardTitle>
              <CardDescription>
                Búsqueda flexible - sin distinción de mayúsculas ni acentos.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <Button
                  variant="outline"
                  className="w-full sm:hidden"
                  onClick={synchronizeExternal}
                  disabled={refreshing}
                >
                  <RefreshCw className={`mr-2 h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
                  Sincronización Externa
                </Button>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Buscar por código de producto o descripción..."
                    className="pl-9"
                  />
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
              </div>
            </CardContent>
          </Card>

          <Card className="overflow-hidden">
            <CardContent className="p-0">
              <ProductsTable
                products={products}
                loading={loading}
                selected={selected}
                onSelect={setSelected}
              />
            </CardContent>
            <ProductsPagination
              page={page}
              totalPages={totalPages}
              pageStart={pageStart}
              pageEnd={pageEnd}
              totalProducts={totalProducts}
              loading={loading}
              onPageChange={setPage}
            />
          </Card>
        </div>

        <div className="xl:sticky xl:top-20 xl:self-start">
          <PrintConfigurationPanel
            formats={formats}
            formatId={formatId}
            onFormatChange={setFormatId}
            product={selected}
            quantity={quantity}
            onQuantityChange={setQuantity}
            printing={printing}
            canPrint={canPrint}
            onPrint={handlePrint}
          />
        </div>
      </div>
    </AppLayout>
  );
}
