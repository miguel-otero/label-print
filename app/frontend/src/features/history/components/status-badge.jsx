import { Badge } from "@/shared/ui/badge";

export function StatusBadge({ status }) {
  if (status === "success") {
    return <Badge className="bg-success text-success-foreground hover:bg-success">Éxito</Badge>;
  }
  if (status === "partial") return <Badge variant="secondary">Parcial</Badge>;
  return <Badge variant="destructive">Error</Badge>;
}
