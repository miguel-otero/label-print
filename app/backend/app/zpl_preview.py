import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from app.schemas import LabelFormat


class ZplPreviewElement(BaseModel):
    kind: Literal["text", "barcode", "graphic"]
    x: int
    y: int
    width: int | None = None
    height: int | None = None
    font_width: int | None = None
    font_height: int | None = None
    lines: int | None = None
    line_spacing: int | None = None
    align: Literal["L", "C", "R"] | None = None
    field: str
    label: str | None = None


class ZplPreviewLayout(BaseModel):
    code: str
    width: int
    height: int
    elements: list[ZplPreviewElement]


def build_zpl_preview_layout(label_format: LabelFormat) -> ZplPreviewLayout | None:
    if not label_format.template_file:
        return None

    template_path = Path(__file__).resolve().parents[1] / "label_templates" / label_format.template_file
    if not template_path.is_file():
        return None
    zpl = template_path.read_text(encoding="utf-8-sig")
    return parse_zpl_preview_layout(code=label_format.code, zpl=zpl)


def parse_zpl_preview_layout(*, code: str, zpl: str) -> ZplPreviewLayout:
    command_zpl = _strip_field_data(zpl)
    width = _read_int_command(command_zpl, "PW") or 1
    height = _read_int_command(command_zpl, "LL") or 1
    elements: list[ZplPreviewElement] = []

    barcode_matcher = re.compile(
        r"\^BY(?P<module>\d+),(?P<ratio>\d+),(?P<height>\d+)"
        r"\^FT(?P<x>-?\d+),(?P<y>-?\d+)\^BC[^^]*\^FD(?P<field>[^\\^]+)\^FS"
    )
    for match in barcode_matcher.finditer(zpl):
        elements.append(
            ZplPreviewElement(
                kind="barcode",
                x=int(match.group("x")),
                y=int(match.group("y")) - int(match.group("height")),
                width=None,
                height=int(match.group("height")),
                field=match.group("field"),
            )
        )

    text_matcher = re.compile(
        r"\^(?P<origin>FT|FO)(?P<x>-?\d+),(?P<y>-?\d+)"
        r"\^A0N,(?P<font_height>\d+),(?P<font_width>\d+)"
        r"(?:\^FB(?P<width>\d+),(?P<lines>\d+),(?P<spacing>-?\d+),(?P<align>[LCRJ]))?"
        r".*?\^FD(?P<field>[^^]+)\^FS"
    )
    seen_text: set[tuple[str, int, int, int | None]] = set()
    text_elements: list[ZplPreviewElement] = []
    for match in text_matcher.finditer(zpl):
        field = _clean_field_value(match.group("field"))
        x = int(match.group("x"))
        y = int(match.group("y"))
        font_height = int(match.group("font_height"))
        text_width = int(match.group("width")) if match.group("width") else None
        dedupe_key = (field, x, y, text_width)
        if dedupe_key in seen_text:
            continue
        seen_text.add(dedupe_key)
        element = ZplPreviewElement(
            kind="text",
            x=x,
            y=y - font_height if match.group("origin") == "FT" else y,
            width=text_width,
            height=font_height,
            font_width=int(match.group("font_width")),
            font_height=font_height,
            lines=int(match.group("lines")) if match.group("lines") else None,
            line_spacing=int(match.group("spacing")) if match.group("spacing") else None,
            align=_normalize_align(match.group("align")),
            field=field,
        )
        elements.append(element)
        text_elements.append(element)

    graphic_matcher = re.compile(
        r"\^FO(?P<x>-?\d+),(?P<y>-?\d+)"
        r"\^GFA,(?P<total>\d+),(?P<bytes>\d+),(?P<row_bytes>\d+),"
    )
    for match in graphic_matcher.finditer(zpl):
        x = int(match.group("x"))
        y = int(match.group("y"))
        row_bytes = int(match.group("row_bytes"))
        graphic_bytes = int(match.group("bytes"))
        field, label = _infer_graphic_label(x=x, y=y, text_elements=text_elements)
        elements.append(
            ZplPreviewElement(
                kind="graphic",
                x=x,
                y=y,
                width=row_bytes * 8,
                height=max(1, round(graphic_bytes / row_bytes)),
                field=field,
                label=label,
            )
        )

    elements.sort(key=lambda item: (item.y, item.x, item.kind))
    return ZplPreviewLayout(code=code, width=width, height=height, elements=elements)


def _read_int_command(zpl: str, command: str) -> int | None:
    match = re.search(rf"\^{command}(\d+)", zpl)
    return int(match.group(1)) if match else None


def _strip_field_data(zpl: str) -> str:
    return re.sub(r"\^FD.*?\^FS", "^FD^FS", zpl, flags=re.S)


def _normalize_align(value: str | None) -> Literal["L", "C", "R"] | None:
    if value in {"L", "C", "R"}:
        return value
    return None


def _clean_field_value(value: str) -> str:
    decoded = re.sub(
        r"\\([0-9A-Fa-f]{2})",
        lambda match: chr(int(match.group(1), 16)),
        value,
    )
    return decoded.replace("\\&", "").strip()


def _infer_graphic_label(
    *,
    x: int,
    y: int,
    text_elements: list[ZplPreviewElement],
) -> tuple[str, str]:
    candidates = [
        item
        for item in text_elements
        if item.field.startswith(("Codigo", "Presentacion")) and abs(item.y - y) <= 8
    ]
    if not candidates:
        return "Grafico", "GRAFICO"

    nearest = min(candidates, key=lambda item: abs(item.x - x))
    position_match = re.search(r"(\d+)$", nearest.field)
    position = position_match.group(1) if position_match else ""

    if nearest.field.startswith("Codigo"):
        return f"CodigoLabel{position}", "CODIGO:"
    if nearest.field.startswith("Presentacion"):
        return f"PresentacionLabel{position}", "PRESENTACION:"
    return f"Grafico{position}", "GRAFICO"
