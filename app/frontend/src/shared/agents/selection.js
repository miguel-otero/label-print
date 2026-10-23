const STORAGE_KEY = "clinic-print-agent";
let savedId = null;
try {
  savedId = globalThis.localStorage?.getItem(STORAGE_KEY) || null;
} catch {
  // Selection still works when browser storage is unavailable.
}
let snapshot = { agents: [], selectedId: savedId, loaded: false, error: null };
let hadSelection = Boolean(savedId);
const listeners = new Set();

function publish(next) {
  snapshot = next;
  listeners.forEach((notify) => notify());
}

export const subscribeAgents = (notify) => {
  listeners.add(notify);
  return () => listeners.delete(notify);
};
export const getAgentSnapshot = () => snapshot;

export function selectAgent(id) {
  hadSelection = true;
  try {
    globalThis.localStorage?.setItem(STORAGE_KEY, id || "");
  } catch {
    // Keep the in-memory preference.
  }
  publish({ ...snapshot, selectedId: id || null });
}

export function updateAgents(agents) {
  const enabled = agents.filter((agent) => agent.enabled);
  let selectedId = snapshot.selectedId;
  if (!selectedId && !hadSelection && enabled.length === 1) {
    selectedId = enabled[0].agent_id;
    selectAgent(selectedId);
  }
  publish({ agents, selectedId, loaded: true, error: null });
}

export function agentLoadFailed(error) {
  publish({ ...snapshot, error: error.message, loaded: true });
}

export function requireSelectedAgent() {
  if (snapshot.error) throw new Error("No se pudo verificar el destino de impresión.");
  const selected = snapshot.agents.find(
    (agent) => agent.agent_id === snapshot.selectedId && agent.enabled,
  );
  if (!selected) throw new Error("Seleccione el equipo y la impresora de destino.");
  return selected.agent_id;
}
