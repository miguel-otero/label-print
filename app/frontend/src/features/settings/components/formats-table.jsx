import { Loader2, Pencil, Trash2 } from "lucide-react";
import { Badge } from "@/shared/ui/badge";
import { Button } from "@/shared/ui/button";
import { TableRender } from "@/shared/layouts/table-render";

export function FormatsTable({
  formats,
  loading,
  editingFormatId,
  deletingFormatId,
  savingFormat,
  onEdit,
  onDelete,
}) {
  const columns = [
    {
      key: "name",
      header: "Nombre",
      headClassName: "text-center",
      cellClassName: "text-center font-medium",
      render: (format) => format.name,
    },
    {
      key: "code",
      header: "Código",
      headClassName: "text-center",
      cellClassName: "text-center font-mono text-xs",
      render: (format) => format.code,
    },
    {
      key: "template",
      header: "Archivo ZPL",
      headClassName: "text-center",
      cellClassName: "text-center font-mono text-xs",
      render: (format) => format.template_file,
    },
    {
      key: "size",
      header: "Medidas",
      headClassName: "text-center",
      cellClassName: "text-center",
      render: (format) => `${format.width_mm} x ${format.height_mm} mm`,
    },
    {
      key: "status",
      header: "Estado",
      headClassName: "text-center",
      cellClassName: "text-center",
      render: (format) =>
        format.active ? (
          <Badge className="bg-success text-success-foreground hover:bg-success">Activo</Badge>
        ) : (
          <Badge variant="outline">Inactivo</Badge>
        ),
    },
    {
      key: "actions",
      header: "Acciones",
      headClassName: "text-center",
      cellClassName: "text-center",
      render: (format) => (
        <div className="flex justify-center gap-2">
          <Button
            type="button"
            variant={editingFormatId === format.id ? "secondary" : "outline"}
            size="sm"
            onClick={() => onEdit(format)}
            disabled={savingFormat || deletingFormatId === format.id}
          >
            <Pencil className="mr-2 h-4 w-4" />
            Editar
          </Button>
          <Button
            type="button"
            variant="destructive"
            size="sm"
            onClick={() => onDelete(format)}
            disabled={savingFormat || deletingFormatId === format.id}
          >
            {deletingFormatId === format.id ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Trash2 className="mr-2 h-4 w-4" />
            )}
            Eliminar
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div className="min-w-0 rounded-md border bg-card p-3">
      <TableRender
        columns={columns}
        items={formats}
        loading={loading}
        skeletonRows={3}
        emptyMessage="No hay formatos registrados."
        containerClassName="rounded-md border"
        rowKey={(format) => format.id}
      />
    </div>
  );
}
