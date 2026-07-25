import * as DialogPrimitive from "@radix-ui/react-dialog";
import { Loader2, Trash2 } from "lucide-react";
import { Button } from "@/shared/ui/button";

export function DeleteFormatDialog({ format, deleting, onOpenChange, onConfirm, onCancel }) {
  return (
    <DialogPrimitive.Root open={!!format} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm data-[state=closed]:animate-out data-[state=open]:animate-in data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
        <DialogPrimitive.Content className="fixed left-1/2 top-1/2 z-50 w-[calc(100%-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-lg border bg-card p-6 text-card-foreground shadow-lg data-[state=closed]:animate-out data-[state=open]:animate-in data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95">
          <div className="flex gap-4">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-destructive/10 text-destructive">
              <Trash2 className="h-5 w-5" />
            </div>
            <div className="min-w-0 space-y-2">
              <DialogPrimitive.Title className="text-base font-semibold">
                Eliminar formato ZPL
              </DialogPrimitive.Title>
              <DialogPrimitive.Description className="text-sm text-muted-foreground">
                Esta acción elimina el formato de la lista de impresión, pero conserva el archivo
                .zpl guardado en el backend.
              </DialogPrimitive.Description>
            </div>
          </div>

          {format ? (
            <div className="mt-5 rounded-md border bg-muted/30 p-3 text-sm">
              <div className="font-medium">{format.name}</div>
              <div className="mt-1 grid gap-1 text-muted-foreground">
                <span>Código: {format.code}</span>
                <span>Archivo ZPL: {format.template_file}</span>
              </div>
            </div>
          ) : null}

          <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <Button type="button" variant="outline" onClick={onCancel} disabled={deleting}>
              Cancelar
            </Button>
            <Button
              type="button"
              variant="destructive"
              onClick={onConfirm}
              disabled={!format || deleting}
            >
              {deleting ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Trash2 className="mr-2 h-4 w-4" />
              )}
              Eliminar formato
            </Button>
          </div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
