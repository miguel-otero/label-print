import { Loader2, Plus, X } from "lucide-react";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select";

export function FormatForm({
  form,
  onChange,
  onSubmit,
  editing,
  onCancel,
  templates,
  saving,
  loadingFormats,
}) {
  return (
    <form className="space-y-4 rounded-md border bg-muted/20 p-4" onSubmit={onSubmit}>
      <div className="flex items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold">{editing ? "Editar formato" : "Nuevo formato"}</h3>
          <p className="text-sm text-muted-foreground">
            {editing
              ? "Modifica la información del formato seleccionado."
              : "Asocia un archivo .zpl existente con un formato disponible para impresión."}
          </p>
        </div>
        {editing ? (
          <Button type="button" variant="outline" size="sm" onClick={onCancel} disabled={saving}>
            <X className="mr-2 h-4 w-4" />
            Cancelar
          </Button>
        ) : null}
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2 sm:col-span-2">
          <Label htmlFor="format-name">Nombre visible</Label>
          <Input
            id="format-name"
            value={form.name}
            onChange={(e) => onChange((current) => ({ ...current, name: e.target.value }))}
            placeholder="3 columnas nuevo"
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="format-code">Código interno</Label>
          <Input
            id="format-code"
            value={form.code}
            onChange={(e) => onChange((current) => ({ ...current, code: e.target.value }))}
            placeholder="etiquetas3_nuevo"
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="format-template">Archivo ZPL</Label>
          <Select
            value={form.template_file}
            onValueChange={(value) => onChange((current) => ({ ...current, template_file: value }))}
            disabled={templates.length === 0 || loadingFormats}
          >
            <SelectTrigger id="format-template">
              <SelectValue placeholder="Selecciona plantilla" />
            </SelectTrigger>
            <SelectContent>
              {templates.map((template) => (
                <SelectItem key={template} value={template}>
                  {template}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="format-width">Ancho (mm)</Label>
          <Input
            id="format-width"
            type="number"
            min={1}
            value={form.width_mm}
            onChange={(e) =>
              onChange((current) => ({ ...current, width_mm: Number(e.target.value) }))
            }
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="format-height">Alto (mm)</Label>
          <Input
            id="format-height"
            type="number"
            min={1}
            value={form.height_mm}
            onChange={(e) =>
              onChange((current) => ({ ...current, height_mm: Number(e.target.value) }))
            }
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="format-preview">Vista previa</Label>
          <Select
            value={form.preview_type}
            onValueChange={(value) => onChange((current) => ({ ...current, preview_type: value }))}
          >
            <SelectTrigger id="format-preview">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="format2">Formato ZPL</SelectItem>
              <SelectItem value="format1">Formato simple</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <label className="flex items-center gap-2 pt-7 text-sm font-medium">
          <input
            type="checkbox"
            className="h-4 w-4 rounded border-input"
            checked={form.active}
            onChange={(e) => onChange((current) => ({ ...current, active: e.target.checked }))}
          />
          Activo
        </label>
      </div>
      {templates.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No hay archivos .zpl disponibles en el backend para registrar.
        </p>
      ) : null}
      <Button type="submit" disabled={saving || loadingFormats || templates.length === 0}>
        {saving ? (
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        ) : (
          <Plus className="mr-2 h-4 w-4" />
        )}
        {editing ? "Guardar cambios" : "Registrar formato"}
      </Button>
    </form>
  );
}
