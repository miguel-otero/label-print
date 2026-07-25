import { Badge } from "@/shared/ui/badge";

export function StatusRow({ label, ok, pending, okText, failText, icon }) {
  return (
    <div className="flex items-center justify-between rounded-md border bg-card p-3">
      <div className="flex items-center gap-2 text-sm font-medium">
        {icon}
        {label}
      </div>
      {pending ? (
        <Badge variant="outline">Verificando...</Badge>
      ) : ok ? (
        <Badge className="bg-success text-success-foreground hover:bg-success">{okText}</Badge>
      ) : (
        <Badge variant="destructive">{failText}</Badge>
      )}
    </div>
  );
}
