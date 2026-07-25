import { Button } from "@/shared/ui/button";

export function ProductsPagination({
  page,
  totalPages,
  pageStart,
  pageEnd,
  totalProducts,
  loading,
  onPageChange,
}) {
  return (
    <div className="flex flex-col gap-3 border-t px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="text-sm text-foreground">
        Página {page} de {totalPages} · {pageStart}-{pageEnd} de {totalProducts}
      </div>
      <div className="flex flex-wrap items-center gap-1.5">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => onPageChange(1)}
          disabled={loading || page <= 1}
        >
          Primera
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => onPageChange(Math.max(1, page - 1))}
          disabled={loading || page <= 1}
          aria-label="Página anterior"
          className="min-w-9"
        >
          {"<"}
        </Button>
        <Button
          type="button"
          variant="default"
          size="sm"
          disabled
          aria-current="page"
          className="min-w-9 disabled:opacity-100"
        >
          {page}
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => onPageChange(Math.min(totalPages, page + 1))}
          disabled={loading || page >= totalPages}
          aria-label="Página siguiente"
          className="min-w-9"
        >
          {">"}
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => onPageChange(totalPages)}
          disabled={loading || page >= totalPages}
        >
          Última
        </Button>
      </div>
    </div>
  );
}
