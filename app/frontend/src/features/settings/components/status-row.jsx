import { Badge } from "@/shared/ui/badge";

export function StatusRow({ label, ok, pending, okText, failText, icon }) {
  return (
    <div className="flex min-w-0 items-start justify-between gap-3 rounded-md border bg-card p-3">
      <div className="flex shrink-0 items-center gap-2 text-sm font-medium">
        {icon}
        {label}
      </div>
      {pending ? (
        <Badge variant="outline">Verificando...</Badge>
      ) : ok ? (
        <Badge className="max-w-[65%] whitespace-normal break-words text-right leading-snug bg-success text-success-foreground hover:bg-success">
          {okText}
        </Badge>
      ) : (
        <Badge
          variant="destructive"
          className="max-w-[65%] whitespace-normal break-words text-right leading-snug [overflow-wrap:anywhere]"
        >
          {failText}
        </Badge>
      )}
    </div>
  );
}
