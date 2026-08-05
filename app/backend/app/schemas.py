from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class Product(BaseModel):
    id: int
    line: str | None = None
    product_code: str
    description: str
    unit_of_measure: str
    barcode: str
    barcode_unit_measure: str | None = None
    quantity_per_unit: str | None = None
    own_code: bool = True
    presentation_quantity: str


class LabelFormat(BaseModel):
    id: int
    name: str
    code: str
    width_mm: int
    height_mm: int
    preview_type: Literal["format1", "format2"]
    active: bool
    template_file: str


class LabelFormatPayload(BaseModel):
    name: str
    code: str
    width_mm: int = Field(gt=0)
    height_mm: int = Field(gt=0)
    preview_type: Literal["format1", "format2"] = "format2"
    active: bool = True
    template_file: str


class PrintRequest(BaseModel):
    formato: str
    producto_id: int
    cantidad: int = Field(ge=1)


class PrintResponse(BaseModel):
    ok: bool
    job_id: int
    history_id: int
    status: Literal["queued"] = "queued"
    message: str


class PrinterTestResponse(BaseModel):
    ok: bool
    printer: str
    connection: str = "windows_agent"
    job_id: int | None = None
    status: str | None = None
    message: str | None = None


class PrintHistory(BaseModel):
    id: int
    job_id: int | None = None
    timestamp: datetime
    user: str
    product_code: str
    product_description: str
    format: str
    quantity: int
    status: Literal["queued", "processing", "success", "partial", "error", "unknown"]
    message: str | None = None


class InventorySyncResult(BaseModel):
    status: Literal["idle", "running", "success", "error", "not_configured", "disabled"]
    started_at: datetime | None = None
    finished_at: datetime | None = None
    product_rows: int = 0
    inventory_rows: int = 0
    inventory_entry_rows: int = 0
    entries_since: date | None = None
    retention_cutoff: date | None = None
    message: str | None = None


class InventoryItem(BaseModel):
    id: int
    warehouse: str
    reference: str
    inventory_quantity: Decimal
    presentations: list[Product]
    printable: bool
    unavailable_reason: str | None = None


class InventoryPrintSettings(BaseModel):
    max_labels_per_batch: int = Field(default=400, ge=1)


class InventorySelectionRefreshRequest(BaseModel):
    warehouse: str
    references: list[str] = Field(min_length=1, max_length=400)


class InventoryEntryDocument(BaseModel):
    provider_name: str | None = None
    document: str
    warehouse: str
    date: date
    reference_count: int
    total_entry_quantity: Decimal


class InventoryEntryItem(BaseModel):
    id: int
    warehouse: str
    document: str
    date: date
    reference: str
    line: str | None = None
    description: str | None = None
    entry_quantity: Decimal
    presentations: list[Product]
    printable: bool
    unavailable_reason: str | None = None


class InventoryBatchItemRequest(BaseModel):
    inventory_id: int
    product_id: int
    quantity: int = Field(ge=0)


class InventoryBatchPrintRequest(BaseModel):
    format: str
    warehouse: str
    items: list[InventoryBatchItemRequest] = Field(min_length=1)


class InventoryEntryBatchItemRequest(BaseModel):
    entry_id: int
    product_id: int
    quantity: int = Field(ge=0)


class InventoryEntryBatchPrintRequest(BaseModel):
    format: str
    warehouse: str
    document: str
    items: list[InventoryEntryBatchItemRequest] = Field(min_length=1)


class InventoryBatchItemResult(BaseModel):
    product_id: int
    reference: str
    description: str
    barcode: str
    presentation: str
    inventory_quantity: Decimal
    requested_labels: int
    printed_labels: int
    failed_labels: int
    status: Literal["queued", "processing", "success", "partial", "error", "unknown"]
    message: str | None = None


class InventoryBatchPrintResponse(BaseModel):
    job_id: int
    batch_id: int
    status: Literal["queued", "processing", "success", "partial", "error", "unknown"]
    requested_labels: int
    printed_labels: int
    failed_labels: int
    message: str | None = None
    items: list[InventoryBatchItemResult]


class PrintBatchHistory(BaseModel):
    id: int
    job_id: int | None = None
    timestamp: datetime
    user: str
    format: str
    warehouse: str
    source: Literal["inventory", "inventory_entry"] = "inventory"
    source_document: str | None = None
    source_date: date | None = None
    requested_labels: int
    printed_labels: int
    failed_labels: int
    status: Literal["queued", "processing", "success", "partial", "error", "unknown"]
    message: str | None = None
    items: list[InventoryBatchItemResult]


class AgentHeartbeatRequest(BaseModel):
    agent_id: str
    printer_name: str
    printer_ok: bool
    message: str | None = None


class PrinterAgentStatus(BaseModel):
    agent_id: str
    printer_name: str
    online: bool
    printer_ok: bool
    last_seen_at: datetime | None = None
    message: str | None = None


class AgentPrintDocument(BaseModel):
    id: int
    sequence: int
    zpl: str


class AgentPrintJob(BaseModel):
    id: int
    kind: str
    printer_name: str
    documents: list[AgentPrintDocument]


class AgentDocumentResult(BaseModel):
    document_id: int
    ok: bool
    message: str | None = None


class AgentJobResultRequest(BaseModel):
    agent_id: str
    documents: list[AgentDocumentResult] = Field(min_length=1)
