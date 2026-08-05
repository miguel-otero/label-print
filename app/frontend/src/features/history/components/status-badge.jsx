import { Badge } from "@/shared/ui/badge";

export function StatusBadge({ status }) {
  if (status === "queued") return <Badge variant="outline">En cola</Badge>;
  if (status === "processing") return <Badge variant="secondary">Procesando</Badge>;
  if (status === "unknown") {
    return <Badge className="bg-warning text-warning-foreground">Incierto</Badge>;
  }
  if (status === "success") {
    return <Badge className="bg-success text-success-foreground hover:bg-success">Éxito</Badge>;
  }
  if (status === "partial") return <Badge variant="secondary">Parcial</Badge>;
  return <Badge variant="destructive">Error</Badge>;
}
