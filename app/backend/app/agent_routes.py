from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from app.agent_registry import AgentRegistry
from app.retention import RetentionService
from app.schemas import AgentRegistration, AgentUpdate, PrinterAgentStatus


def create_agent_router(registry: AgentRegistry, retention: RetentionService) -> APIRouter:
    router = APIRouter()

    def require_admin(x_admin_key: str = Header(default="")) -> None:
        registry.check_admin(x_admin_key)

    @router.get("/agentes", response_model=list[PrinterAgentStatus])
    def agents() -> list[PrinterAgentStatus]:
        return registry.list()

    @router.get("/agentes/paquete/estado")
    def release_status() -> dict:
        try:
            _, manifest = registry.release()
            return {"available": True, "version": manifest["version"]}
        except HTTPException as exc:
            return {"available": False, "message": exc.detail}

    @router.post("/admin/agentes", dependencies=[Depends(require_admin)], response_model=PrinterAgentStatus)
    def register(payload: AgentRegistration) -> PrinterAgentStatus:
        return registry.save(payload)

    @router.patch("/admin/agentes/{agent_id}", dependencies=[Depends(require_admin)], response_model=PrinterAgentStatus)
    def update(agent_id: str, payload: AgentUpdate) -> PrinterAgentStatus:
        if any(value is None for value in payload.model_dump(exclude_unset=True).values()):
            raise HTTPException(422, "Los campos enviados no pueden ser nulos.")
        return registry.save(payload, agent_id)

    @router.post("/admin/agentes/{agent_id}/restablecer", dependencies=[Depends(require_admin)])
    def reset(agent_id: str) -> PrinterAgentStatus:
        return registry.reset(agent_id)

    @router.post("/admin/agentes/{agent_id}/paquete", dependencies=[Depends(require_admin)])
    def package(agent_id: str) -> FileResponse:
        path = registry.package(agent_id)
        return FileResponse(
            path, media_type="application/zip", filename=f"agente-{agent_id}.zip",
            headers={"Cache-Control": "no-store"},
            background=BackgroundTask(path.unlink, missing_ok=True),
        )

    @router.get("/mantenimiento/estado")
    def maintenance() -> dict:
        return retention.status()

    @router.get("/admin/mantenimiento/simulacion", dependencies=[Depends(require_admin)])
    def diagnose() -> dict:
        return retention.run_once(dry_run=True)

    return router
