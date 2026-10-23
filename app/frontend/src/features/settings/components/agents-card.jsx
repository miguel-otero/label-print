import { useEffect, useState } from "react";
import { Download, Plus, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/shared/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/shared/ui/dialog";
import { useAgents } from "@/shared/agents/use-agents";
import {
  downloadAgent,
  manageAgent,
  refreshAgents,
  getAgentRelease,
  getMaintenanceStatus,
  diagnoseRetention,
} from "@/shared/api/api";

const titles = {
  create: "Registrar equipo Windows",
  edit: "Editar estación",
  toggle: "Cambiar disponibilidad",
  reset: "Restablecer instalación y credencial",
  download: "Descargar instalador y configuración",
  diagnose: "Simular limpieza del histórico",
};

export function AgentsCard() {
  const { agents } = useAgents();
  const [release, setRelease] = useState(null);
  const [maintenance, setMaintenance] = useState(null);
  const [operation, setOperation] = useState(null);
  const [key, setKey] = useState("");
  const [name, setName] = useState("");
  const [printer, setPrinter] = useState("");
  const [busy, setBusy] = useState(false);
  const [diagnosis, setDiagnosis] = useState(null);
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    Promise.all([getAgentRelease(), getMaintenanceStatus()])
      .then(([artifact, status]) => {
        setRelease(artifact);
        setMaintenance(status);
      })
      .catch((error) => setLoadError(error.message));
  }, []);

  function open(action, agent) {
    setKey("");
    setName(agent?.display_name || "");
    setPrinter(agent?.printer_name || agents[0]?.printer_name || "");
    setOperation({ action, agent });
  }

  function close() {
    if (busy) return;
    setKey("");
    setOperation(null);
  }

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    const { action, agent } = operation;
    try {
      if (action === "download") {
        const blob = await downloadAgent(agent.agent_id, key);
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = `agente-${agent.agent_id}.zip`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.setTimeout(() => URL.revokeObjectURL(url), 1000);
        toast.success("Paquete descargado", {
          description: "Extraiga el ZIP e instale en el equipo registrado.",
        });
      } else if (action === "diagnose") {
        setDiagnosis(await diagnoseRetention(key));
      } else {
        const payload =
          action === "create" || action === "edit"
            ? {
                display_name: name.trim(),
                printer_name: printer.trim(),
                ...(action === "create" ? { enabled: true } : {}),
              }
            : action === "toggle"
              ? { enabled: !agent.enabled }
              : undefined;
        await manageAgent(
          action === "create" ? "create" : action === "reset" ? "reset" : "update",
          agent?.agent_id,
          payload,
          key,
        );
        await refreshAgents();
        toast.success(
          action === "reset"
            ? "Descargue un nuevo ZIP para reconectar el equipo"
            : "Estación actualizada",
        );
      }
      setOperation(null);
    } catch (error) {
      toast.error("No se pudo completar la operación", { description: error.message });
    } finally {
      setKey("");
      setBusy(false);
    }
  }

  return (
    <Card className="min-w-0 lg:col-span-2">
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="space-y-1">
            <CardTitle className="flex items-center gap-2 text-base">
              <ShieldCheck className="h-4 w-4" /> Equipos de impresión
            </CardTitle>
            <CardDescription>
              Un agente y una impresora por equipo Windows. La administración requiere clave.
            </CardDescription>
          </div>
          <Button onClick={() => open("create")}>
            <Plus className="mr-2 h-4 w-4" /> Registrar equipo
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-5">
        {loadError && (
          <p role="alert" className="text-sm text-destructive">
            {loadError}
          </p>
        )}
        <div className="grid gap-3 xl:grid-cols-2">
          {agents.map((agent) => (
            <div key={agent.agent_id} className="min-w-0 space-y-3 rounded-lg border p-4">
              <div className="flex flex-wrap justify-between gap-2">
                <div className="min-w-0">
                  <p className="break-words font-medium">{agent.display_name}</p>
                  <p className="break-words text-sm text-muted-foreground">{agent.printer_name}</p>
                </div>
                <span className="text-xs text-muted-foreground">
                  {!agent.enabled ? "Deshabilitado" : agent.online ? "Conectado" : "Desconectado"}
                </span>
              </div>
              <p className="text-xs text-muted-foreground">
                Versión: {agent.version || "Sin informar"} · Última conexión:{" "}
                {agent.last_seen_at ? new Date(agent.last_seen_at).toLocaleString() : "Nunca"}
              </p>
              {agent.legacy_auth && (
                <p className="text-sm text-muted-foreground">
                  Actualice este equipo con su nuevo ZIP antes de habilitar otros agentes.
                </p>
              )}
              <div className="flex flex-wrap gap-2">
                <Button
                  size="sm"
                  disabled={!release?.available}
                  onClick={() => open("download", agent)}
                >
                  <Download className="mr-2 h-4 w-4" /> Descargar ZIP
                </Button>
                <Button size="sm" variant="outline" onClick={() => open("edit", agent)}>
                  Editar
                </Button>
                <Button size="sm" variant="outline" onClick={() => open("toggle", agent)}>
                  {agent.enabled ? "Deshabilitar" : "Habilitar"}
                </Button>
                <Button size="sm" variant="ghost" onClick={() => open("reset", agent)}>
                  Restablecer
                </Button>
              </div>
            </div>
          ))}
          {!agents.length && (
            <p className="text-sm text-muted-foreground">No hay estaciones disponibles.</p>
          )}
        </div>
        <p className="text-sm text-muted-foreground">
          {release?.available
            ? `Instalador ${release.version}. El ZIP incluye la configuración actual de esta estación.`
            : release?.message || "Comprobando instalador…"}
        </p>
        <div className="space-y-2 border-t pt-4">
          <p className="font-medium">Retención del histórico</p>
          <p className="text-sm text-muted-foreground">
            {maintenance
              ? `${maintenance.months} meses calendario · Limpieza ${maintenance.enabled ? "activa" : "pendiente de activación"} · Cada ${maintenance.interval_minutes} minutos`
              : "Cargando política…"}
          </p>
          <p className="text-sm text-muted-foreground">
            {maintenance?.last_run
              ? `Última ejecución: ${new Date(maintenance.last_run.finished_at).toLocaleString()} · ${maintenance.last_run.status === "success" ? "Correcta" : "Error"}`
              : "Sin ejecuciones registradas."}
          </p>
          <Button variant="outline" size="sm" onClick={() => open("diagnose")}>
            Simular limpieza
          </Button>
          {diagnosis && (
            <div className="overflow-auto rounded-md border p-3 text-sm">
              <p>
                Simulación sin borrados · Corte: {new Date(diagnosis.cutoff).toLocaleDateString()}
              </p>
              <p>Impresiones activas protegidas: {diagnosis.protected_roots}</p>
              <table className="mt-2 w-full text-left">
                <thead>
                  <tr>
                    <th>Datos</th>
                    <th>Total</th>
                    <th>Antiguos</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(diagnosis.tables).map(([table, counts]) => (
                    <tr key={table}>
                      <td>
                        {{
                          print_history: "Historial",
                          print_batches: "Lotes",
                          print_jobs: "Trabajos",
                          inventory_entries: "Entradas",
                        }[table] || table}
                      </td>
                      <td>{counts.total}</td>
                      <td>{counts.expired}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="mt-2 text-muted-foreground">
                Los registros antiguos asociados a impresiones activas se conservarán hasta que
                finalicen.
              </p>
            </div>
          )}
        </div>
      </CardContent>
      <Dialog open={Boolean(operation)} onOpenChange={(isOpen) => !isOpen && close()}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{titles[operation?.action]}</DialogTitle>
            <DialogDescription>
              {operation?.action === "reset"
                ? "La credencial actual dejará de funcionar. Descargue un nuevo ZIP e impórtelo en el equipo que utilizará esta estación."
                : operation?.action === "toggle"
                  ? "Deshabilitar detiene nuevas reclamaciones. El trabajo activo podrá terminar; los pendientes conservarán su destino."
                  : operation?.action === "diagnose"
                    ? "Consulta los registros antiguos sin eliminarlos."
                    : `Autorice esta operación${operation?.agent ? ` para ${operation.agent.display_name}` : ""} con la clave de administrador.`}
            </DialogDescription>
          </DialogHeader>
          <form className="space-y-4" onSubmit={submit}>
            {["create", "edit"].includes(operation?.action) && (
              <>
                <div className="space-y-2">
                  <Label htmlFor="agent-name">Nombre del equipo</Label>
                  <Input
                    id="agent-name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                    maxLength={160}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="agent-printer">Nombre exacto de la impresora en Windows</Label>
                  <Input
                    id="agent-printer"
                    value={printer}
                    onChange={(e) => setPrinter(e.target.value)}
                    required
                    maxLength={160}
                  />
                </div>
              </>
            )}
            <div className="space-y-2">
              <Label htmlFor="agent-admin-key">Clave de administrador</Label>
              <Input
                id="agent-admin-key"
                type="password"
                autoComplete="off"
                value={key}
                onChange={(e) => setKey(e.target.value)}
                required
                disabled={busy}
              />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" disabled={busy} onClick={close}>
                Cancelar
              </Button>
              <Button type="submit" disabled={busy || !key}>
                {busy
                  ? "Procesando…"
                  : operation?.action === "download"
                    ? "Descargar ZIP"
                    : "Continuar"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </Card>
  );
}
