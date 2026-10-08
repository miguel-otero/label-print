import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ImagePlus, LoaderCircle, Printer } from "lucide-react";
import { toast } from "sonner";
import { AppLayout } from "@/shared/layouts/app-layout";
import { Button } from "@/shared/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/shared/ui/dialog";
import {
  getLabelImages,
  getLabelImagePreview,
  labelImageUrl,
  printCustomLabel,
  uploadLabelImage,
} from "@/shared/api/api";
import { cn } from "@/shared/utils/utils";

function LabelRow({ url, count }) {
  return (
    <svg
      viewBox="0 0 799 200"
      role="img"
      aria-label={`Fila de ${count} etiquetas con imagen`}
      className="w-full rounded border bg-white"
    >
      {[32, 302, 575].map((x, index) => (
        <g key={x}>
          <rect
            x={x - 8}
            y="6"
            width="218"
            height="188"
            rx="4"
            fill="white"
            stroke="#d1d5db"
            strokeDasharray="5 4"
          />
          {index < count && <image href={url} x={x} y="14" width="202" height="172" />}
        </g>
      ))}
    </svg>
  );
}

export function CustomLabelPage() {
  const [images, setImages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [libraryError, setLibraryError] = useState("");
  const [selected, setSelected] = useState(null);
  const [file, setFile] = useState(null);
  const [name, setName] = useState("");
  const [uploading, setUploading] = useState(false);
  const [quantity, setQuantity] = useState("");
  const [preview, setPreview] = useState(null);
  const [previewError, setPreviewError] = useState("");
  const [printing, setPrinting] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [lastJob, setLastJob] = useState(null);
  const fileInput = useRef(null);

  useEffect(() => {
    let active = true;
    getLabelImages()
      .then((items) => {
        if (active) setImages(items);
      })
      .catch((error) => {
        if (active) setLibraryError(error.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!selected) return;
    const controller = new AbortController();
    let objectUrl;
    getLabelImagePreview(selected.id, controller.signal)
      .then((blob) => {
        if (controller.signal.aborted) return;
        objectUrl = URL.createObjectURL(blob);
        setPreview({ imageId: selected.id, url: objectUrl });
      })
      .catch((error) => {
        if (!controller.signal.aborted) setPreviewError(error.message);
      });
    return () => {
      controller.abort();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [selected]);

  function selectImage(image) {
    if (image.id === selected?.id) return;
    setPreview(null);
    setPreviewError("");
    setSelected(image);
  }

  async function handleUpload(event) {
    event.preventDefault();
    if (!file || uploading) return;
    if (!/\.(png|jpe?g)$/i.test(file.name) || file.size > 5 * 1024 * 1024) {
      toast.error("Seleccione un archivo PNG o JPG de hasta 5 MB.");
      return;
    }
    setUploading(true);
    try {
      const image = await uploadLabelImage(file, name.trim());
      setImages((current) => [image, ...current]);
      setLibraryError("");
      selectImage(image);
      setFile(null);
      setName("");
      if (fileInput.current) fileInput.current.value = "";
      toast.success("Imagen guardada en la biblioteca.");
    } catch (error) {
      toast.error(error.message);
    } finally {
      setUploading(false);
    }
  }

  const count = Number(quantity);
  const canPrint =
    selected &&
    preview?.imageId === selected.id &&
    quantity !== "" &&
    Number.isInteger(count) &&
    count >= 1 &&
    count <= 400 &&
    !uploading &&
    !printing;
  const rows = canPrint ? Math.ceil(count / 3) : 0;
  const remainder = canPrint ? count % 3 : 0;

  async function handlePrint() {
    if (!canPrint) return;
    setPrinting(true);
    try {
      const result = await printCustomLabel(selected.id, count);
      setLastJob(result.job_id);
      setQuantity("");
      toast.success(`Trabajo #${result.job_id} agregado a la cola.`);
    } catch (error) {
      toast.error(error.message);
    } finally {
      setPrinting(false);
      setConfirming(false);
    }
  }

  return (
    <AppLayout
      title="Etiqueta personalizada"
      subtitle="Imprima un logo o imagen en etiquetas de tres columnas"
    >
      <div className="grid min-w-0 gap-6 lg:grid-cols-2">
        <div className="min-w-0 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Cargar imagen</CardTitle>
              <CardDescription>PNG o JPG, hasta 5 MB y 4096 × 4096 píxeles.</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleUpload} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="image-name">Nombre de la imagen</Label>
                  <Input
                    id="image-name"
                    value={name}
                    maxLength={120}
                    required
                    disabled={uploading}
                    onChange={(event) => setName(event.target.value)}
                    placeholder="Logo clinica"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="image-file-trigger">Archivo</Label>
                  <Input
                    id="image-file"
                    ref={fileInput}
                    type="file"
                    accept=".png,.jpg,.jpeg"
                    className="hidden"
                    tabIndex={-1}
                    disabled={uploading}
                    onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                  />
                  <div className="flex min-w-0 flex-wrap items-center gap-3">
                    <Button
                      id="image-file-trigger"
                      type="button"
                      variant="outline"
                      className="shrink-0"
                      disabled={uploading}
                      aria-describedby="image-file-name"
                      onClick={() => fileInput.current?.click()}
                    >
                      Elige el archivo
                    </Button>
                    <span
                      id="image-file-name"
                      className="min-w-0 break-all text-sm text-muted-foreground"
                      aria-live="polite"
                    >
                      {file?.name || "Ningún archivo seleccionado"}
                    </span>
                  </div>
                </div>
                <Button type="submit" disabled={uploading || !file || !name.trim()}>
                  {uploading ? (
                    <LoaderCircle className="mr-2 size-4 animate-spin" />
                  ) : (
                    <ImagePlus className="mr-2 size-4" />
                  )}
                  {uploading ? "Guardando..." : "Guardar imagen"}
                </Button>
              </form>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Biblioteca de imágenes</CardTitle>
            </CardHeader>
            <CardContent>
              {loading && <p className="text-sm text-muted-foreground">Cargando imágenes...</p>}
              {libraryError && (
                <p role="alert" className="text-sm text-destructive">
                  {libraryError}
                </p>
              )}
              {!loading && !libraryError && images.length === 0 && (
                <p className="text-sm text-muted-foreground">Cargue una imagen para comenzar.</p>
              )}
              <div className="grid max-h-[28rem] grid-cols-2 gap-3 overflow-y-auto sm:grid-cols-3">
                {images.map((image) => (
                  <button
                    key={image.id}
                    type="button"
                    onClick={() => selectImage(image)}
                    disabled={printing || confirming}
                    aria-pressed={selected?.id === image.id}
                    className={cn(
                      "min-w-0 space-y-2 rounded-md border p-3 text-left hover:border-primary",
                      selected?.id === image.id && "border-primary ring-1 ring-primary",
                    )}
                  >
                    <img
                      src={labelImageUrl(image.id)}
                      alt={image.name}
                      loading="lazy"
                      className="h-20 w-full rounded bg-white object-contain"
                    />
                    <span className="block break-words text-sm font-medium">{image.name}</span>
                    <span className="block text-xs text-muted-foreground">
                      {image.width} × {image.height} px
                    </span>
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
        <Card className="h-fit min-w-0">
          <CardHeader>
            <CardTitle className="text-base">Vista previa e impresión</CardTitle>
            <CardDescription>
              La imagen se imprime centrada en blanco y negro, sin recortes ni texto adicional.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            {!selected ? (
              <p className="text-sm text-muted-foreground">
                Seleccione una imagen de la biblioteca.
              </p>
            ) : (
              <>
                <p className="break-words text-sm font-medium">{selected.name}</p>
                {previewError ? (
                  <p role="alert" className="text-sm text-destructive">
                    {previewError}
                  </p>
                ) : preview?.imageId === selected.id ? (
                  <LabelRow url={preview.url} count={canPrint ? Math.min(count, 3) : 3} />
                ) : (
                  <p className="text-sm text-muted-foreground">Preparando vista previa...</p>
                )}
                <div className="space-y-2">
                  <Label htmlFor="custom-quantity">Cantidad de etiquetas</Label>
                  <Input
                    id="custom-quantity"
                    type="number"
                    min="1"
                    max="400"
                    step="1"
                    value={quantity}
                    disabled={printing || confirming}
                    placeholder="Digite la cantidad"
                    onChange={(event) => setQuantity(event.target.value)}
                  />
                  <p className="text-xs text-muted-foreground">
                    Entre 1 y 400 etiquetas. Se repite la misma imagen en todas.
                  </p>
                </div>
                {canPrint && (
                  <p className="text-sm">
                    {count} etiqueta(s) en {rows} fila(s).
                  </p>
                )}
                {canPrint && remainder > 0 && (
                  <div className="space-y-2">
                    <p className="text-xs text-muted-foreground">
                      Última fila: {remainder} etiqueta(s); las demás posiciones quedan vacías.
                    </p>
                    <LabelRow url={preview.url} count={remainder} />
                  </div>
                )}
                <Button disabled={!canPrint} onClick={() => setConfirming(true)}>
                  {printing ? (
                    <LoaderCircle className="mr-2 size-4 animate-spin" />
                  ) : (
                    <Printer className="mr-2 size-4" />
                  )}
                  {printing ? "Enviando..." : "Imprimir etiquetas"}
                </Button>
              </>
            )}
            {lastJob && (
              <p role="status" className="text-sm">
                Trabajo #{lastJob} agregado a la cola.{" "}
                <Link to="/history?view=individual" className="text-primary underline">
                  Ver historial
                </Link>
              </p>
            )}
          </CardContent>
        </Card>
      </div>
      <Dialog
        open={confirming}
        onOpenChange={(open) => {
          if (!printing) setConfirming(open);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Confirmar impresión</DialogTitle>
            <DialogDescription>
              Se enviarán {count} etiquetas con la imagen «{selected?.name}» a la cola de impresión.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" disabled={printing} onClick={() => setConfirming(false)}>
              Cancelar
            </Button>
            <Button
              disabled={printing}
              onClick={(event) => {
                event.preventDefault();
                handlePrint();
              }}
            >
              {printing ? "Enviando..." : "Confirmar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AppLayout>
  );
}
