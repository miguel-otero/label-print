import { useEffect, useState } from "react";
import { FileText } from "lucide-react";
import { toast } from "sonner";
import { AppLayout } from "@/shared/layouts/app-layout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";
import { PrinterCard } from "@/features/settings/components/printer-card";
import { SystemStatusCard } from "@/features/settings/components/system-status-card";
import { InventoryLimitCard } from "@/features/settings/components/inventory-limit-card";
import { FormatForm } from "@/features/settings/components/format-form";
import { FormatsTable } from "@/features/settings/components/formats-table";
import { DeleteFormatDialog } from "@/features/settings/components/delete-format-dialog";
import {
  deleteFormat,
  getFormats,
  getFormatTemplates,
  getInventoryPrintSettings,
  pingBackend,
  printTestLabel,
  saveFormat,
  saveInventoryPrintSettings,
  testPrinter,
} from "@/shared/api/api";

const emptyFormatForm = {
  name: "",
  code: "",
  width_mm: 102,
  height_mm: 25,
  preview_type: "format2",
  active: true,
  template_file: "",
};

export function SettingsPage() {
  const [printerName, setPrinterName] = useState("ZDesigner ZD230-203dpi ZPL");
  const [backendOk, setBackendOk] = useState(null);
  const [testing, setTesting] = useState(false);
  const [printingTest, setPrintingTest] = useState(false);
  const [lastResult, setLastResult] = useState(null);
  const [templates, setTemplates] = useState([]);
  const [formats, setFormats] = useState([]);
  const [loadingFormats, setLoadingFormats] = useState(true);
  const [savingFormat, setSavingFormat] = useState(false);
  const [deletingFormatId, setDeletingFormatId] = useState(null);
  const [formatToDelete, setFormatToDelete] = useState(null);
  const [formatForm, setFormatForm] = useState(emptyFormatForm);
  const [editingFormatId, setEditingFormatId] = useState(null);
  const [inventoryPrintLimit, setInventoryPrintLimit] = useState(400);
  const [savingInventoryLimit, setSavingInventoryLimit] = useState(false);

  useEffect(() => {
    pingBackend()
      .then(setBackendOk)
      .catch(() => setBackendOk(false));
    loadFormatSettings();
    getInventoryPrintSettings()
      .then((settings) => setInventoryPrintLimit(settings.max_labels_per_batch))
      .catch((error) =>
        toast.error("No se pudo cargar el límite de impresión", {
          description: error instanceof Error ? error.message : "Error desconocido",
        }),
      );
  }, []);

  async function handleSaveInventoryLimit() {
    if (inventoryPrintLimit < 1) {
      toast.error("El limite debe ser mayor o igual a 1 etiqueta.");
      return;
    }
    setSavingInventoryLimit(true);
    try {
      const saved = await saveInventoryPrintSettings({
        max_labels_per_batch: inventoryPrintLimit,
      });
      setInventoryPrintLimit(saved.max_labels_per_batch);
      toast.success("Límite de impresión actualizado");
    } catch (error) {
      toast.error("No se pudo guardar el límite", {
        description: error instanceof Error ? error.message : "Error desconocido",
      });
    } finally {
      setSavingInventoryLimit(false);
    }
  }

  async function loadFormatSettings() {
    setLoadingFormats(true);
    try {
      const [templateFiles, existingFormats] = await Promise.all([
        getFormatTemplates(),
        getFormats(true),
      ]);
      setTemplates(templateFiles);
      setFormats(existingFormats);
      setFormatForm((current) => ({
        ...current,
        template_file: current.template_file || templateFiles[0] || "",
      }));
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Error desconocido";
      toast.error("No se pudieron cargar los formatos ZPL", { description: msg });
    } finally {
      setLoadingFormats(false);
    }
  }

  async function handleTest() {
    setTesting(true);
    try {
      const res = await testPrinter();
      setPrinterName(res.printer);
      setLastResult({
        ok: true,
        message: res.message ?? `Impresora ${res.printer} OK`,
        at: new Date().toISOString(),
      });
      toast.success("Impresora respondió correctamente");
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Error desconocido";
      setLastResult({ ok: false, message: msg, at: new Date().toISOString() });
      toast.error("Falló al probar impresora", { description: msg });
    } finally {
      setTesting(false);
    }
  }

  async function handleTestLabel() {
    setPrintingTest(true);
    try {
      const res = await printTestLabel();
      setPrinterName(res.printer);
      setLastResult({
        ok: true,
        message: res.message ?? "Etiqueta de prueba enviada",
        at: new Date().toISOString(),
      });
      toast.success("Etiqueta de prueba enviada");
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Error";
      setLastResult({ ok: false, message: msg, at: new Date().toISOString() });
      toast.error("No se pudo imprimir prueba", { description: msg });
    } finally {
      setPrintingTest(false);
    }
  }

  async function handleSaveFormat(event) {
    event.preventDefault();
    const payload = {
      ...formatForm,
      name: formatForm.name.trim(),
      code: formatForm.code.trim(),
      template_file: formatForm.template_file.trim(),
      width_mm: Number(formatForm.width_mm),
      height_mm: Number(formatForm.height_mm),
    };
    if (!payload.name || !payload.code || !payload.template_file) {
      toast.error("Completa nombre, código y plantilla ZPL.");
      return;
    }
    const formatWithTemplate = formats.find(
      (format) => format.template_file === payload.template_file && format.id !== editingFormatId,
    );
    if (formatWithTemplate) {
      toast.error("Ese archivo ZPL ya está asociado a otro formato.", {
        description: `Actualmente lo usa: ${formatWithTemplate.name}`,
      });
      return;
    }
    setSavingFormat(true);
    try {
      await saveFormat(payload, editingFormatId ?? undefined);
      toast.success(editingFormatId ? "Formato ZPL actualizado" : "Formato ZPL registrado");
      await loadFormatSettings();
      resetFormatForm(payload.template_file);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Error desconocido";
      toast.error(
        editingFormatId ? "No se pudo actualizar el formato" : "No se pudo registrar el formato",
        { description: msg },
      );
    } finally {
      setSavingFormat(false);
    }
  }

  function handleEditFormat(format) {
    setEditingFormatId(format.id);
    setFormatForm({
      name: format.name,
      code: format.code,
      width_mm: format.width_mm,
      height_mm: format.height_mm,
      preview_type: format.preview_type,
      active: format.active,
      template_file: format.template_file,
    });
  }

  function resetFormatForm(fallbackTemplate = templates[0] || "") {
    setEditingFormatId(null);
    setFormatForm({
      ...emptyFormatForm,
      template_file: fallbackTemplate,
    });
  }

  async function handleDeleteFormat(format) {
    setDeletingFormatId(format.id);
    try {
      await deleteFormat(format.id);
      toast.success("Formato eliminado", {
        description: `El archivo ${format.template_file} se conserva en el backend.`,
      });
      if (editingFormatId === format.id) {
        resetFormatForm();
      }
      setFormatToDelete(null);
      await loadFormatSettings();
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Error desconocido";
      toast.error("No se pudo eliminar el formato", { description: msg });
    } finally {
      setDeletingFormatId(null);
    }
  }

  return (
    <AppLayout title="Configuraciones" subtitle="Estado, impresora y formatos de etiquetas.">
      <div className="grid gap-6 lg:grid-cols-2">
        <PrinterCard
          printerName={printerName}
          onPrinterNameChange={setPrinterName}
          testing={testing}
          printingTest={printingTest}
          onTest={handleTest}
          onTestLabel={handleTestLabel}
        />

        <SystemStatusCard backendOk={backendOk} printerName={printerName} lastResult={lastResult} />

        <InventoryLimitCard
          value={inventoryPrintLimit}
          onChange={setInventoryPrintLimit}
          saving={savingInventoryLimit}
          onSave={handleSaveInventoryLimit}
        />

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <FileText className="h-4 w-4" />
              Formatos ZPL
            </CardTitle>
            <CardDescription>
              Registra formatos usando archivos .zpl que ya existan en el almacenamiento del
              backend.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-6 xl:grid-cols-[minmax(0,420px)_1fr]">
            <FormatForm
              form={formatForm}
              onChange={setFormatForm}
              onSubmit={handleSaveFormat}
              editing={editingFormatId !== null}
              onCancel={() => resetFormatForm()}
              templates={templates}
              saving={savingFormat}
              loadingFormats={loadingFormats}
            />

            <FormatsTable
              formats={formats}
              loading={loadingFormats}
              editingFormatId={editingFormatId}
              deletingFormatId={deletingFormatId}
              savingFormat={savingFormat}
              onEdit={handleEditFormat}
              onDelete={setFormatToDelete}
            />
          </CardContent>
        </Card>
      </div>

      <DeleteFormatDialog
        format={formatToDelete}
        deleting={deletingFormatId !== null}
        onOpenChange={(open) => {
          if (!open && deletingFormatId === null) {
            setFormatToDelete(null);
          }
        }}
        onConfirm={() => formatToDelete && handleDeleteFormat(formatToDelete)}
        onCancel={() => setFormatToDelete(null)}
      />
    </AppLayout>
  );
}
