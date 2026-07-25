import { Button } from "@/shared/ui/button";

export function InventoryPagination({ page, totalPages, totalItems, loading, onPageChange }) {
  return (
    <div className="flex items-center justify-between border-t px-4 py-3 text-sm">
      <span>{totalItems} resultado(s)</span>
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          disabled={page <= 1 || loading}
          onClick={() => onPageChange(page - 1)}
        >
          Anterior
        </Button>
        <span className="min-w-20 text-center">
          {page} / {totalPages}
        </span>
        <Button
          variant="outline"
          size="sm"
          disabled={page >= totalPages || loading}
          onClick={() => onPageChange(page + 1)}
        >
          Siguiente
        </Button>
      </div>
    </div>
  );
}
