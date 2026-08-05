import asyncio
import secrets
from contextlib import asynccontextmanager, suppress
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware

from app.inventory_print import InventoryPrintError, InventoryPrintService
from app.inventory_sync import InventorySyncRunner, InventorySyncService
from app.print_queue import PrintQueueError, PrintQueueService
from app.printer import (
    PrinterError,
    QueuedZplDocument,
    build_individual_queue_documents,
)
from app.repository import Repository, create_repository, require_product
from app.schemas import (
    LabelFormat,
    LabelFormatPayload,
    InventoryBatchPrintRequest,
    InventoryBatchPrintResponse,
    InventoryEntryBatchPrintRequest,
    InventoryEntryDocument,
    InventoryEntryItem,
    InventoryItem,
    InventoryPrintSettings,
    InventorySelectionRefreshRequest,
    InventorySyncResult,
    PrintBatchHistory,
    PrintHistory,
    PrintRequest,
    PrintResponse,
    PrinterTestResponse,
    AgentHeartbeatRequest,
    AgentJobResultRequest,
    AgentPrintJob,
    PrinterAgentStatus,
    Product,
)
from app.settings import get_settings
from app.zpl_preview import ZplPreviewLayout, build_zpl_preview_layout

settings = get_settings()
repository = create_repository(settings)
print_queue = PrintQueueService(settings)
inventory_print_service = InventoryPrintService(settings, print_queue)
inventory_sync = InventorySyncService(settings)
inventory_sync_runner = InventorySyncRunner(inventory_sync, settings)


@asynccontextmanager
async def lifespan(_: FastAPI):
    print_queue.ensure_schema()
    inventory_print_service.ensure_schema()
    sync_task: asyncio.Task[None] | None = None
    if settings.use_postgres and settings.external_sync_enabled:
        sync_task = asyncio.create_task(inventory_sync_runner.run())

    yield

    if sync_task is not None:
        inventory_sync_runner.stop()
        sync_task.cancel()
        with suppress(asyncio.CancelledError):
            await sync_task


app = FastAPI(title="Clinic Label Print API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count"],
)


def get_repository() -> Repository:
    return repository


def require_agent_token(authorization: str | None = Header(default=None)) -> None:
    if not settings.print_agent_token:
        raise HTTPException(status_code=503, detail="CLINIC_PRINT_AGENT_TOKEN no esta configurado.")
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not secrets.compare_digest(token, settings.print_agent_token):
        raise HTTPException(status_code=401, detail="Token de agente invalido.")


@app.get(f"{settings.api_prefix}/health")
def health(response: Response, repo: Repository = Depends(get_repository)) -> dict[str, str]:
    if not repo.health_check():
        response.status_code = 503
        return {"status": "error", "data_source": settings.data_source}
    return {"status": "ok", "data_source": settings.data_source}


@app.get(f"{settings.api_prefix}/sincronizacion/inventario", response_model=InventorySyncResult)
def get_inventory_sync_status() -> InventorySyncResult:
    return inventory_sync.get_status()


@app.post(f"{settings.api_prefix}/sincronizacion/inventario", response_model=InventorySyncResult)
def sync_inventory(response: Response) -> InventorySyncResult:
    result = inventory_sync.sync_all()
    if result.status == "disabled":
        response.status_code = 202
    elif result.status == "not_configured":
        response.status_code = 503
    elif result.status == "error":
        response.status_code = 502
    return result


@app.get(f"{settings.api_prefix}/inventario/bodegas", response_model=list[str])
def get_inventory_warehouses() -> list[str]:
    try:
        return inventory_print_service.get_warehouses()
    except InventoryPrintError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get(f"{settings.api_prefix}/inventario", response_model=list[InventoryItem])
def get_inventory(
    response: Response,
    warehouse: str,
    search: str | None = None,
    line: list[str] = Query(default_factory=list),
    availability: Literal["all", "printable", "unprintable"] = "all",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=10000),
) -> list[InventoryItem]:
    try:
        items, total = inventory_print_service.search_inventory(
            warehouse=warehouse,
            search=search,
            lines=line,
            availability=availability,
            limit=page_size,
            offset=(page - 1) * page_size,
        )
    except InventoryPrintError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    response.headers["X-Total-Count"] = str(total)
    return items


@app.get(
    f"{settings.api_prefix}/inventario/entradas/documentos",
    response_model=list[InventoryEntryDocument],
)
def get_inventory_entry_documents(
    response: Response,
    warehouse: str,
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=100),
) -> list[InventoryEntryDocument]:
    try:
        documents, total = inventory_print_service.search_entry_documents(
            warehouse=warehouse,
            search=search,
            limit=page_size,
            offset=(page - 1) * page_size,
        )
    except InventoryPrintError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    response.headers["X-Total-Count"] = str(total)
    return documents


@app.get(
    f"{settings.api_prefix}/inventario/entradas/documentos/{{document}}",
    response_model=list[InventoryEntryItem],
)
def get_inventory_entry_document_items(
    document: str,
    warehouse: str,
) -> list[InventoryEntryItem]:
    try:
        return inventory_print_service.get_entry_document_items(
            warehouse=warehouse,
            document=document,
        )
    except InventoryPrintError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post(
    f"{settings.api_prefix}/inventario/seleccion",
    response_model=list[InventoryItem],
)
def get_inventory_selection(
    payload: InventorySelectionRefreshRequest,
) -> list[InventoryItem]:
    try:
        return inventory_print_service.get_inventory_selection(
            warehouse=payload.warehouse,
            references=payload.references,
        )
    except InventoryPrintError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get(
    f"{settings.api_prefix}/configuracion/impresion-inventario",
    response_model=InventoryPrintSettings,
)
def get_inventory_print_settings() -> InventoryPrintSettings:
    try:
        return inventory_print_service.get_settings()
    except InventoryPrintError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.put(
    f"{settings.api_prefix}/configuracion/impresion-inventario",
    response_model=InventoryPrintSettings,
)
def update_inventory_print_settings(
    payload: InventoryPrintSettings,
) -> InventoryPrintSettings:
    try:
        return inventory_print_service.update_settings(payload)
    except InventoryPrintError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post(
    f"{settings.api_prefix}/imprimir-inventario",
    response_model=InventoryBatchPrintResponse,
)
def print_inventory_batch(
    payload: InventoryBatchPrintRequest,
    user: str = Header(default="operador1", alias="X-User"),
) -> InventoryBatchPrintResponse:
    try:
        return inventory_print_service.print_batch(payload, user=user)
    except InventoryPrintError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post(
    f"{settings.api_prefix}/imprimir-inventario/entrada",
    response_model=InventoryBatchPrintResponse,
)
def print_inventory_entry_batch(
    payload: InventoryEntryBatchPrintRequest,
    user: str = Header(default="operador1", alias="X-User"),
) -> InventoryBatchPrintResponse:
    try:
        return inventory_print_service.print_entry_batch(payload, user=user)
    except InventoryPrintError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get(
    f"{settings.api_prefix}/historial/lotes",
    response_model=list[PrintBatchHistory],
)
def get_batch_history() -> list[PrintBatchHistory]:
    try:
        return inventory_print_service.get_batch_history()
    except InventoryPrintError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get(f"{settings.api_prefix}/productos", response_model=list[Product])
def search_products(
    response: Response,
    search: str | None = None,
    line: list[str] = Query(default_factory=list),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=100),
    repo: Repository = Depends(get_repository),
) -> list[Product]:
    total = repo.count_products(search, lines=line)
    response.headers["X-Total-Count"] = str(total)
    return repo.search_products(search, lines=line, limit=page_size, offset=(page - 1) * page_size)


@app.get(f"{settings.api_prefix}/productos/lineas", response_model=list[str])
def get_product_lines(repo: Repository = Depends(get_repository)) -> list[str]:
    return repo.get_product_lines()


@app.get(f"{settings.api_prefix}/formatos", response_model=list[LabelFormat])
def get_formats(
    include_inactive: bool = False,
    repo: Repository = Depends(get_repository),
) -> list[LabelFormat]:
    return repo.get_formats(active_only=not include_inactive)


@app.get(f"{settings.api_prefix}/formatos/plantillas", response_model=list[str])
def get_format_templates(repo: Repository = Depends(get_repository)) -> list[str]:
    return repo.list_template_files()


@app.post(f"{settings.api_prefix}/formatos", response_model=LabelFormat)
def create_format(
    payload: LabelFormatPayload,
    repo: Repository = Depends(get_repository),
) -> LabelFormat:
    validate_template_file(payload.template_file, repo)
    validate_unique_template_file(payload.template_file, repo)
    return repo.save_format(payload)


@app.put(f"{settings.api_prefix}/formatos/{{format_id}}", response_model=LabelFormat)
def update_format(
    format_id: int,
    payload: LabelFormatPayload,
    repo: Repository = Depends(get_repository),
) -> LabelFormat:
    validate_template_file(payload.template_file, repo)
    validate_unique_template_file(payload.template_file, repo, current_format_id=format_id)
    return repo.save_format(payload, format_id=format_id)


@app.delete(f"{settings.api_prefix}/formatos/{{format_id}}", status_code=204)
def delete_format(
    format_id: int,
    repo: Repository = Depends(get_repository),
) -> None:
    repo.delete_format(format_id)


@app.get(f"{settings.api_prefix}/formatos/{{code}}/preview", response_model=ZplPreviewLayout)
def get_format_preview(code: str, repo: Repository = Depends(get_repository)) -> ZplPreviewLayout:
    label_format = repo.get_format(code)
    if label_format is None:
        raise HTTPException(status_code=404, detail="Formato no encontrado")

    preview = build_zpl_preview_layout(label_format)
    if preview is None:
        raise HTTPException(status_code=404, detail="Vista previa ZPL no disponible")
    return preview


def validate_template_file(template_file: str, repository: Repository) -> None:
    if "/" in template_file or "\\" in template_file or not template_file.endswith(".zpl"):
        raise HTTPException(status_code=400, detail="Plantilla ZPL invalida")
    if template_file not in repository.list_template_files():
        raise HTTPException(status_code=400, detail="La plantilla ZPL no existe")


def validate_unique_template_file(
    template_file: str,
    repository: Repository,
    *,
    current_format_id: int | None = None,
) -> None:
    for label_format in repository.get_formats(active_only=False):
        if label_format.template_file == template_file and label_format.id != current_format_id:
            raise HTTPException(
                status_code=409,
                detail="La plantilla ZPL ya esta asociada a otro formato",
            )


def require_label_format(repository: Repository, code: str) -> LabelFormat:
    label_format = repository.get_format(code)
    if label_format is None:
        raise HTTPException(status_code=404, detail="Formato no encontrado")
    return label_format


@app.post(f"{settings.api_prefix}/imprimir", response_model=PrintResponse)
def print_label(
    payload: PrintRequest,
    repo: Repository = Depends(get_repository),
    user: str = Header(default="operador1", alias="X-User"),
) -> PrintResponse:
    product = require_product(repo, payload.producto_id)
    label_format = require_label_format(repo, payload.formato)

    try:
        documents = build_individual_queue_documents(
            label_format=label_format,
            product=product,
            quantity=payload.cantidad,
        )
    except PrinterError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    history = repo.add_history(
        product=product, label_format=payload.formato, quantity=payload.cantidad,
        status="queued", message=None, user=user,
    )
    job_id = print_queue.enqueue(
        kind="individual", documents=documents, requested_labels=payload.cantidad,
        history_id=history.id,
    )
    return PrintResponse(
        ok=True,
        job_id=job_id,
        history_id=history.id,
        message="Trabajo agregado a la cola de impresion",
    )


@app.post(f"{settings.api_prefix}/impresora/test", response_model=PrinterTestResponse)
def test_printer() -> PrinterTestResponse:
    job_id = print_queue.enqueue(
        kind="printer_test",
        documents=[QueuedZplDocument(zpl="", item_counts={})],
        requested_labels=0,
    )
    return PrinterTestResponse(
        ok=True, printer=settings.printer_name, job_id=job_id, status="queued",
        message="Prueba de conexion agregada a la cola.",
    )


@app.post(f"{settings.api_prefix}/impresora/test/etiqueta", response_model=PrinterTestResponse)
def print_test_label() -> PrinterTestResponse:
    test_format = LabelFormat(
        id=0,
        name="Prueba 3 columnas",
        code="3_etiquetas_v3",
        width_mm=100,
        height_mm=25,
        preview_type="format2",
        active=True,
        template_file="3_etiquetas_v3.zpl",
    )
    test_product = Product(
        id=0,
        product_code="TEST-USB",
        description="Prueba de impresion USB",
        unit_of_measure="UN",
        barcode="123456789012",
        presentation_quantity="1 u",
    )

    documents = build_individual_queue_documents(
        label_format=test_format, product=test_product, quantity=1,
    )
    job_id = print_queue.enqueue(
        kind="test_label", documents=documents, requested_labels=1,
    )
    return PrinterTestResponse(
        ok=True, printer=settings.printer_name, job_id=job_id, status="queued",
        message="Etiqueta de prueba agregada a la cola.",
    )


@app.get(f"{settings.api_prefix}/impresora/status", response_model=PrinterAgentStatus)
def get_printer_status() -> PrinterAgentStatus:
    print_queue.mark_stale_jobs()
    return print_queue.get_agent_status()


@app.post(
    f"{settings.api_prefix}/agente/heartbeat",
    response_model=PrinterAgentStatus,
    dependencies=[Depends(require_agent_token)],
)
def agent_heartbeat(payload: AgentHeartbeatRequest) -> PrinterAgentStatus:
    try:
        return print_queue.heartbeat(payload)
    except PrintQueueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post(
    f"{settings.api_prefix}/agente/trabajos/reclamar",
    response_model=None,
    dependencies=[Depends(require_agent_token)],
)
def claim_agent_job(payload: dict[str, str]) -> AgentPrintJob | Response:
    try:
        job = print_queue.claim(payload.get("agent_id", ""))
    except PrintQueueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return job if job is not None else Response(status_code=204)


@app.post(
    f"{settings.api_prefix}/agente/trabajos/{{job_id}}/resultado",
    dependencies=[Depends(require_agent_token)],
)
def complete_agent_job(job_id: int, payload: AgentJobResultRequest) -> dict[str, object]:
    try:
        return print_queue.complete(job_id, payload)
    except PrintQueueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post(f"{settings.api_prefix}/trabajos/{{job_id}}/reintentar")
def retry_print_job(job_id: int) -> dict[str, object]:
    try:
        new_job_id = print_queue.retry(job_id)
    except PrintQueueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"job_id": new_job_id, "status": "queued"}


@app.get(f"{settings.api_prefix}/historial", response_model=list[PrintHistory])
def get_history(repo: Repository = Depends(get_repository)) -> list[PrintHistory]:
    return repo.get_history()
