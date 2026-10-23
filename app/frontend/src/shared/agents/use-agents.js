import { useSyncExternalStore } from "react";
import { getAgentSnapshot, subscribeAgents } from "./selection";

export function useAgents() {
  const state = useSyncExternalStore(subscribeAgents, getAgentSnapshot);
  return {
    ...state,
    selectedAgent: state.agents.find(
      (agent) => agent.agent_id === state.selectedId && agent.enabled,
    ),
  };
}
