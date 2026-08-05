import ctypes
import os
import re
import subprocess
import tempfile
import textwrap
import unicodedata
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path

from app.schemas import LabelFormat, Product
from app.settings import Settings


class PrinterError(Exception):
    pass


@dataclass(frozen=True)
class BatchLabel:
    item_key: int
    product: Product


@dataclass
class BatchItemPrintOutcome:
    printed_labels: int = 0
    failed_labels: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class QueuedZplDocument:
    zpl: str
    item_counts: dict[int, int]


class Printer(ABC):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @abstractmethod
    def test(self) -> dict[str, str | bool]:
        raise NotImplementedError

    @abstractmethod
    def print_label(
        self,
        *,
        label_format: LabelFormat,
        product: Product,
        quantity: int,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def print_batch(
        self,
        *,
        label_format: LabelFormat,
        labels: list[BatchLabel],
    ) -> dict[int, BatchItemPrintOutcome]:
        raise NotImplementedError


class SimulatedPrinter(Printer):
    def test(self) -> dict[str, str | bool]:
        return {
            "ok": True,
            "printer": self.settings.printer_name,
            "connection": self.settings.printer_connection,
        }

    def print_label(
        self,
        *,
        label_format: LabelFormat,
        product: Product,
        quantity: int,
    ) -> None:
        _ = (label_format, product, quantity)

    def print_batch(
        self,
        *,
        label_format: LabelFormat,
        labels: list[BatchLabel],
    ) -> dict[int, BatchItemPrintOutcome]:
        _ = label_format
        outcomes: dict[int, BatchItemPrintOutcome] = {}
        for label in labels:
            outcome = outcomes.setdefault(label.item_key, BatchItemPrintOutcome())
            outcome.printed_labels += 1
        return outcomes


class QueuePrinter(Printer):
    def test(self) -> dict[str, str | bool]:
        self._test_connection()
        return {
            "ok": True,
            "printer": self.settings.printer_name,
            "connection": self.settings.printer_connection,
        }

    def print_label(
        self,
        *,
        label_format: LabelFormat,
        product: Product,
        quantity: int,
    ) -> None:
        for zpl in build_zpl_jobs(
            label_format=label_format,
            product=product,
            quantity=quantity,
        ):
            self._send_raw(encode_zpl_payload(zpl))

    def print_batch(
        self,
        *,
        label_format: LabelFormat,
        labels: list[BatchLabel],
    ) -> dict[int, BatchItemPrintOutcome]:
        outcomes = {
            label.item_key: BatchItemPrintOutcome()
            for label in labels
        }

        for offset in range(0, len(labels), 3):
            job_labels = labels[offset : offset + 3]
            try:
                zpl = build_mixed_zpl_job(
                    label_format=label_format,
                    products=[label.product for label in job_labels],
                )
                self._send_raw(encode_zpl_payload(zpl))
            except PrinterError as exc:
                message = str(exc)
                for label in job_labels:
                    outcome = outcomes[label.item_key]
                    outcome.failed_labels += 1
                    if message not in outcome.errors:
                        outcome.errors.append(message)
                continue

            for label in job_labels:
                outcomes[label.item_key].printed_labels += 1

        return outcomes

    @abstractmethod
    def _test_connection(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def _send_raw(self, payload: bytes) -> None:
        raise NotImplementedError


class WindowsSpoolerPrinter(QueuePrinter):
    def _test_connection(self) -> None:
        handle = self._open_printer()
        winspool.ClosePrinter(handle)

    def _send_raw(self, payload: bytes) -> None:
        handle = self._open_printer()
        job_started = False
        page_started = False
        try:
            doc_info = DOCINFO(
                "Clinic Label Print",
                None,
                "RAW",
            )
            if not winspool.StartDocPrinterW(handle, 1, ctypes.byref(doc_info)):
                raise_spooler_error("No se pudo iniciar el trabajo de impresion")
            job_started = True

            if not winspool.StartPagePrinter(handle):
                raise_spooler_error("No se pudo iniciar la pagina de impresion")
            page_started = True

            written = ctypes.c_ulong(0)
            buffer = ctypes.create_string_buffer(payload)
            if not winspool.WritePrinter(
                handle,
                buffer,
                len(payload),
                ctypes.byref(written),
            ):
                raise_spooler_error("No se pudo escribir en la cola de impresion")
            if written.value != len(payload):
                raise PrinterError("La cola de impresion recibio datos incompletos")
        finally:
            if page_started:
                winspool.EndPagePrinter(handle)
            if job_started:
                winspool.EndDocPrinter(handle)
            winspool.ClosePrinter(handle)

    def _open_printer(self) -> ctypes.c_void_p:
        if os.name != "nt":
            raise PrinterError("windows_spooler solo funciona si el backend corre en Windows")

        handle = ctypes.c_void_p()
        if not winspool.OpenPrinterW(
            self.settings.printer_name,
            ctypes.byref(handle),
            None,
        ):
            raise_spooler_error(
                f"No se pudo abrir la impresora '{self.settings.printer_name}'"
            )
        return handle


class CupsPrinter(QueuePrinter):
    def _test_connection(self) -> None:
        result = subprocess.run(
            ["lpstat", "-p", self.settings.printer_name],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            message = (result.stderr or result.stdout or "").strip()
            raise PrinterError(message or f"No se encontro la cola '{self.settings.printer_name}'")

    def _send_raw(self, payload: bytes) -> None:
        with tempfile.NamedTemporaryFile(suffix=".zpl", delete=False) as file:
            file.write(payload)
            file_path = file.name

        try:
            result = subprocess.run(
                ["lp", "-d", self.settings.printer_name, "-o", "raw", file_path],
                check=False,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                message = (result.stderr or result.stdout or "").strip()
                raise PrinterError(message or "No se pudo enviar a la cola CUPS")
        finally:
            os.unlink(file_path)


class DOCINFO(ctypes.Structure):
    _fields_ = [
        ("lpszDocName", ctypes.c_wchar_p),
        ("lpszOutput", ctypes.c_wchar_p),
        ("lpszDatatype", ctypes.c_wchar_p),
    ]


winspool = ctypes.WinDLL("winspool.drv", use_last_error=True) if os.name == "nt" else None

if winspool is not None:
    winspool.OpenPrinterW.argtypes = [
        ctypes.c_wchar_p,
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.c_void_p,
    ]
    winspool.OpenPrinterW.restype = ctypes.c_bool
    winspool.ClosePrinter.argtypes = [ctypes.c_void_p]
    winspool.ClosePrinter.restype = ctypes.c_bool
    winspool.StartDocPrinterW.argtypes = [
        ctypes.c_void_p,
        ctypes.c_ulong,
        ctypes.POINTER(DOCINFO),
    ]
    winspool.StartDocPrinterW.restype = ctypes.c_ulong
    winspool.EndDocPrinter.argtypes = [ctypes.c_void_p]
    winspool.EndDocPrinter.restype = ctypes.c_bool
    winspool.StartPagePrinter.argtypes = [ctypes.c_void_p]
    winspool.StartPagePrinter.restype = ctypes.c_bool
    winspool.EndPagePrinter.argtypes = [ctypes.c_void_p]
    winspool.EndPagePrinter.restype = ctypes.c_bool
    winspool.WritePrinter.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_ulong,
        ctypes.POINTER(ctypes.c_ulong),
    ]
    winspool.WritePrinter.restype = ctypes.c_bool


def raise_spooler_error(message: str) -> None:
    error_code = ctypes.get_last_error()
    if error_code:
        error_message = ctypes.FormatError(error_code).strip()
        raise PrinterError(f"{message}: {error_message} ({error_code})")
    raise PrinterError(message)


def encode_zpl_payload(zpl: str) -> bytes:
    try:
        return zpl.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise PrinterError("El ZPL contiene caracteres que no se pudieron codificar") from exc


def create_printer(settings: Settings) -> Printer:
    connection = settings.printer_connection.lower()
    if connection == "simulated":
        return SimulatedPrinter(settings)
    if connection in {"windows_spooler", "usb", "spooler"}:
        return WindowsSpoolerPrinter(settings)
    if connection == "cups":
        return CupsPrinter(settings)
    raise ValueError(f"Unsupported printer connection: {settings.printer_connection}")


def build_zpl_jobs(
    *,
    label_format: LabelFormat,
    product: Product,
    quantity: int,
) -> list[str]:
    if label_format.template_file:
        return build_template_jobs(
            product=product,
            quantity=quantity,
            template_name=label_format.template_file,
        )

    raise PrinterError(f"El formato '{label_format.code}' no tiene plantilla ZPL configurada")


def build_individual_queue_documents(
    *,
    label_format: LabelFormat,
    product: Product,
    quantity: int,
) -> list[QueuedZplDocument]:
    jobs = build_zpl_jobs(label_format=label_format, product=product, quantity=quantity)
    documents: list[QueuedZplDocument] = []
    remaining = quantity
    for zpl in jobs:
        label_count = min(3, remaining)
        documents.append(QueuedZplDocument(zpl=zpl, item_counts={0: label_count}))
        remaining -= label_count
    return documents


def build_batch_queue_documents(
    *,
    label_format: LabelFormat,
    labels: list[BatchLabel],
) -> list[QueuedZplDocument]:
    documents: list[QueuedZplDocument] = []
    for offset in range(0, len(labels), 3):
        document_labels = labels[offset : offset + 3]
        zpl = build_mixed_zpl_job(
            label_format=label_format,
            products=[label.product for label in document_labels],
        )
        documents.append(
            QueuedZplDocument(
                zpl=zpl,
                item_counts=dict(Counter(label.item_key for label in document_labels)),
            )
        )
    return documents


def build_legacy_zpl_jobs(
    *,
    label_format: LabelFormat,
    product: Product,
    quantity: int,
) -> list[str]:
    zpl = build_zpl(label_format=label_format, product=product)
    return [zpl for _ in range(quantity)]


def build_zpl(*, label_format: LabelFormat, product: Product) -> str:
    width = dots(label_format.width_mm)
    height = dots(label_format.height_mm)

    description = sanitize_zpl_text(product.description)
    code = sanitize_zpl_text(product.product_code)
    unit = sanitize_zpl_text(product.unit_of_measure)
    presentation = sanitize_zpl_text(product.presentation_quantity)
    barcode = sanitize_barcode(product.barcode)

    if label_format.preview_type == "format2":
        return small_label_zpl(
            width=width,
            height=height,
            code=code,
            description=description,
            barcode=barcode,
        )

    return standard_label_zpl(
        width=width,
        height=height,
        code=code,
        description=description,
        barcode=barcode,
        unit=unit,
        presentation=presentation,
    )


def build_template_jobs(
    *,
    product: Product,
    quantity: int,
    template_name: str,
) -> list[str]:
    template = load_template(template_name)
    jobs: list[str] = []
    remaining = quantity

    while remaining > 0:
        labels_in_job = min(3, remaining)
        jobs.append(
            populate_template(
                template=template,
                products=[product] * labels_in_job,
            )
        )
        remaining -= labels_in_job

    return jobs


def build_mixed_zpl_job(
    *,
    label_format: LabelFormat,
    products: list[Product],
) -> str:
    if not 1 <= len(products) <= 3:
        raise PrinterError("Cada trabajo ZPL debe contener entre una y tres etiquetas")
    if not label_format.template_file:
        raise PrinterError(f"El formato '{label_format.code}' no tiene plantilla ZPL configurada")
    return populate_template(
        template=load_template(label_format.template_file),
        products=products,
    )


def populate_template(*, template: str, products: list[Product]) -> str:
    replacements: dict[str, str] = {}
    output = template

    for position in range(1, 4):
        if position <= len(products):
            replacements.update(
                template_values(product=products[position - 1], position=position)
            )
        else:
            output = remove_empty_template_slot(output, position)
            replacements.update(empty_template_values(position=position))

    return replace_template_values(output, replacements)


def load_template(filename: str) -> str:
    if "/" in filename or "\\" in filename or not filename.endswith(".zpl"):
        raise PrinterError(f"Plantilla ZPL invalida: {filename}")

    template_path = Path(__file__).resolve().parents[1] / "label_templates" / filename
    try:
        template = template_path.read_text(encoding="utf-8-sig")
    except FileNotFoundError as exc:
        raise PrinterError(f"No se encontro la plantilla ZPL: {filename}") from exc
    except UnicodeDecodeError as exc:
        raise PrinterError(
            f"La plantilla ZPL '{filename}' no es un archivo de texto valido. "
            "Exporte la etiqueta como ZPL plano desde ZebraDesigner."
        ) from exc

    validate_zpl_template(template, filename)
    return template


def validate_zpl_template(template: str, filename: str) -> None:
    if "^XA" not in template or "^XZ" not in template:
        raise PrinterError(
            f"La plantilla ZPL '{filename}' no contiene una estructura ZPL valida (^XA/^XZ). "
            "Verifique que no sea un proyecto o paquete de ZebraDesigner."
        )

    missing_placeholders = [
        placeholder
        for position in range(1, 4)
        for placeholder in (
            f"Codigo{position}",
            f"Descripcion{position}",
            f"Presentacion{position}",
            f"Codigobarras{position}",
        )
        if placeholder not in template
    ]
    if missing_placeholders:
        missing = ", ".join(missing_placeholders)
        raise PrinterError(
            f"La plantilla ZPL '{filename}' no contiene los placeholders requeridos: {missing}"
        )


def template_values(*, product: Product, position: int) -> dict[str, str]:
    presentation = format_presentation_quantity(product.presentation_quantity or "1 unidad")
    return {
        f"Codigo{position}": sanitize_zpl_text(product.product_code),
        f"Descripcion{position}": sanitize_zpl_text(product.description),
        f"Presentacion{position}": sanitize_zpl_text(presentation),
        f"Codigobarras{position}": sanitize_barcode(product.barcode),
    }


def empty_template_values(*, position: int) -> dict[str, str]:
    return {
        f"Codigo{position}": "",
        f"Descripcion{position}": "",
        f"Presentacion{position}": "",
        f"Codigobarras{position}": "",
    }


def format_presentation_quantity(value: str) -> str:
    match = re.match(r"^\s*(?P<quantity>[+-]?\d+(?:[.,]\d+)?)(?P<suffix>.*)$", value)
    if match is None:
        return value

    raw_quantity = match.group("quantity")
    try:
        quantity = Decimal(raw_quantity.replace(",", "."))
    except InvalidOperation:
        return value

    if quantity != quantity.to_integral_value():
        return value

    return f"{int(quantity)}{match.group('suffix')}"


def remove_empty_template_slot(template: str, position: int) -> str:
    output = remove_static_label_fields(template, position)
    return remove_placeholder_fields(output, position)


def remove_placeholder_fields(template: str, position: int) -> str:
    placeholders = (
        f"Descripcion{position}",
        f"Codigo{position}",
        f"Presentacion{position}",
        f"Codigobarras{position}",
    )
    lines = template.splitlines(keepends=True)
    remove_indexes: set[int] = set()

    for index, line in enumerate(lines):
        if not any(f"^FD{placeholder}^FS" in line for placeholder in placeholders):
            continue

        remove_indexes.add(index)
        if index > 0 and "^BY" in lines[index - 1] and "^BC" in lines[index - 1]:
            remove_indexes.add(index - 1)

    return "".join(line for index, line in enumerate(lines) if index not in remove_indexes)


def remove_static_label_fields(template: str, position: int) -> str:
    regions = template_slot_regions(template)
    if position not in regions:
        return template

    region_start, region_end = regions[position]
    lines = template.splitlines(keepends=True)
    remove_indexes: set[int] = set()

    for index, line in enumerate(lines):
        match = re.search(
            r"\^(?:FT|FO)(?P<x>-?\d+),(?P<y>-?\d+)(?P<body>.*?\^FD(?P<field>[^^]+)\^FS)",
            line,
        )
        if match is None:
            continue

        field = sanitize_zpl_text(clean_zpl_field(match.group("field"))).upper()
        if "CODIGO" not in field and "PRESENTACION" not in field:
            continue

        field_width = read_field_block_width(match.group("body"))
        x = int(match.group("x"))
        center = x + (field_width / 2 if field_width is not None else 0)
        if region_start <= center < region_end:
            remove_indexes.add(index)

    return "".join(line for index, line in enumerate(lines) if index not in remove_indexes)


def template_slot_regions(template: str) -> dict[int, tuple[float, float]]:
    width = read_zpl_int_command(template, "PW")
    barcode_anchors: list[tuple[int, int]] = []
    for match in re.finditer(
        r"\^BY[^^]*\^FT(?P<x>-?\d+),(?P<y>-?\d+)\^BC[^^]*\^FD(?:Codigobarras)(?P<position>\d+)\^FS",
        template,
        flags=re.S,
    ):
        barcode_anchors.append((int(match.group("position")), int(match.group("x"))))

    barcode_anchors.sort(key=lambda item: item[0])
    if len(barcode_anchors) < 2 or width is None:
        return {}

    first_inset = barcode_anchors[0][1]
    starts = [(position, max(0, x - first_inset)) for position, x in barcode_anchors]
    regions: dict[int, tuple[float, float]] = {}
    for index, (position, start) in enumerate(starts):
        end = starts[index + 1][1] if index + 1 < len(starts) else width
        regions[position] = (start, end)
    return regions


def read_field_block_width(block: str) -> int | None:
    match = re.search(r"\^FB(?P<width>\d+),", block)
    return int(match.group("width")) if match else None


def read_zpl_int_command(zpl: str, command: str) -> int | None:
    match = re.search(rf"\^{command}(?P<value>\d+)", zpl)
    return int(match.group("value")) if match else None


def clean_zpl_field(value: str) -> str:
    decoded = re.sub(
        r"\\([0-9A-Fa-f]{2})",
        lambda match: chr(int(match.group(1), 16)),
        value,
    )
    return decoded.replace("\\&", "").strip()


def replace_template_values(template: str, replacements: dict[str, str]) -> str:
    output = template
    for placeholder, value in replacements.items():
        output = output.replace(placeholder, value)
    return output


def standard_label_zpl(
    *,
    width: int,
    height: int,
    code: str,
    description: str,
    barcode: str,
    unit: str,
    presentation: str,
) -> str:
    desc_lines = wrap_zpl(description, 28, 2)
    return "\n".join(
        [
            "^XA",
            "^PW" + str(width),
            "^LL" + str(height),
            "^LH0,0",
            f"^FO24,20^A0N,28,28^FD{code}^FS",
            f"^FO24,56^A0N,24,24^FD{desc_lines[0]}^FS",
            f"^FO24,86^A0N,24,24^FD{desc_lines[1]}^FS",
            f"^FO24,122^A0N,22,22^FDUM: {unit}  Pres: {presentation}^FS",
            f"^FO24,{max(152, height - 126)}^BY2,2,62^BCN,62,Y,N,N^FD{barcode}^FS",
            "^XZ",
        ]
    )


def small_label_zpl(
    *,
    width: int,
    height: int,
    code: str,
    description: str,
    barcode: str,
) -> str:
    desc_lines = wrap_zpl(description, 24, 1)
    return "\n".join(
        [
            "^XA",
            "^PW" + str(width),
            "^LL" + str(height),
            "^LH0,0",
            f"^FO18,14^A0N,26,26^FD{code}^FS",
            f"^FO18,46^A0N,20,20^FD{desc_lines[0]}^FS",
            f"^FO18,{max(72, height - 92)}^BY2,2,48^BCN,48,Y,N,N^FD{barcode}^FS",
            "^XZ",
        ]
    )


def dots(mm: int) -> int:
    return round(mm * 8)


def wrap_zpl(value: str, width: int, lines: int) -> list[str]:
    wrapped = textwrap.wrap(value, width=width, break_long_words=False)
    wrapped = wrapped[:lines]
    while len(wrapped) < lines:
        wrapped.append("")
    return wrapped


def sanitize_zpl_text(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value)
    ascii_value = "".join(
        ch for ch in normalized if unicodedata.category(ch) != "Mn"
    ).encode("ascii", "ignore")
    return ascii_value.decode("ascii").replace("^", " ").replace("~", " ")


def sanitize_barcode(value: str) -> str:
    sanitized = "".join(ch for ch in value if ch.isalnum() or ch in "-_.")
    if not sanitized:
        raise PrinterError("El producto no tiene codigo de barras valido")
    return sanitized
