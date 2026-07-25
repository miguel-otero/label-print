import { ChevronDown, Filter } from "lucide-react";
import { Badge } from "@/shared/ui/badge";
import { cn } from "@/shared/utils/utils";

export function LineFilter({
  productLines,
  selectedLines,
  open,
  onToggleOpen,
  onToggleLine,
  onSelectAll,
  label,
}) {
  return (
    <div className="rounded-md border bg-muted/20">
      <button
        type="button"
        onClick={onToggleOpen}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-sm text-foreground"
      >
        <span className="flex items-center gap-2 font-medium">
          <Filter className="h-4 w-4" />
          Filtro por línea
        </span>
        <span className="flex items-center gap-2">
          <Badge variant={selectedLines.length === 0 ? "secondary" : "default"}>{label}</Badge>
          <ChevronDown className={cn("h-4 w-4 transition-transform", open && "rotate-180")} />
        </span>
      </button>

      {open && (
        <div className="border-t bg-card px-3 py-2">
          <div className="max-h-36 overflow-auto pr-1">
            <label className="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-sm text-foreground hover:bg-muted">
              <input
                type="checkbox"
                checked={selectedLines.length === 0}
                onChange={onSelectAll}
                className="h-4 w-4"
              />
              Todas las líneas
            </label>
            {productLines.map((line) => (
              <label
                key={line}
                className="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-sm text-foreground hover:bg-muted"
              >
                <input
                  type="checkbox"
                  checked={selectedLines.includes(line)}
                  onChange={() => onToggleLine(line)}
                  className="h-4 w-4"
                />
                <span>{line}</span>
              </label>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
