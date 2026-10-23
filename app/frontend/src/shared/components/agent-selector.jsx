import { Printer } from "lucide-react";
import { useAgents } from "@/shared/agents/use-agents";
import { selectAgent } from "@/shared/agents/selection";

export function AgentSelector() {
  const { agents, selectedAgent, loaded, error } = useAgents();
  return (
    <div className="flex flex-wrap items-center gap-3 border-b bg-card px-4 py-3">
      <label htmlFor="print-destination" className="flex items-center gap-2 text-sm font-medium">
        <Printer className="h-4 w-4" /> Destino de impresión
      </label>
      <select
        id="print-destination"
        className="h-9 min-w-0 max-w-full rounded-md border bg-background px-3 text-sm"
        value={selectedAgent?.agent_id || ""}
        onChange={(event) => selectAgent(event.target.value)}
        disabled={!loaded}
      >
        <option value="">{loaded ? "Seleccione equipo e impresora" : "Cargando equipos…"}</option>
        {agents
          .filter((agent) => agent.enabled)
          .map((agent) => (
            <option key={agent.agent_id} value={agent.agent_id}>
              {agent.display_name} · {agent.printer_name} ·{" "}
              {agent.online ? "Conectado" : "Desconectado"}
            </option>
          ))}
      </select>
      {error ? (
        <span role="alert" className="text-sm text-destructive">
          {error}
        </span>
      ) : selectedAgent && !selectedAgent.online ? (
        <span className="text-sm text-muted-foreground">
          Los trabajos esperarán a que este equipo se conecte.
        </span>
      ) : null}
    </div>
  );
}
