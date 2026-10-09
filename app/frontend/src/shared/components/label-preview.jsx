import { useEffect, useState } from "react";
import { getFormatPreview } from "@/shared/api/api";
import { Package } from "lucide-react";
import { formatPresentationQuantity } from "@/shared/utils/utils";
import {
  buildLabelRegions,
  getElementRegionIndex,
  resolvePreviewValue,
} from "@/shared/utils/label-preview";

function Barcode({ value, compact = false }) {
  // Stylized visual barcode placeholder (not real ZPL).
  const safeValue = value || "0";
  const bars = Array.from({ length: 42 }, (_, i) => {
    const seed = (safeValue.charCodeAt(i % safeValue.length) + i * 7) % 5;
    const w = seed === 0 ? 3 : seed === 1 ? 1 : 2;
    return w;
  });
  return (
    <div className="flex min-w-0 flex-col items-center gap-1">
      <div className={compact ? "flex h-7 items-end gap-[1px]" : "flex h-10 items-end gap-[1px]"}>
        {bars.map((w, i) => (
          <div key={i} style={{ width: w }} className="h-full bg-foreground" />
        ))}
      </div>
      <span
        className={
          compact
            ? "font-mono text-[8px] text-foreground"
            : "font-mono text-[10px] tracking-widest text-foreground"
        }
      >
        {value}
      </span>
    </div>
  );
}

function BarcodeSvg({ value, x, y, width, height }) {
  const safeValue = value || "0";
  const bars = Array.from({ length: 42 }, (_, i) => {
    const seed = (safeValue.charCodeAt(i % safeValue.length) + i * 7) % 5;
    return seed === 0 ? 3 : seed === 1 ? 1 : 2;
  });
  const total = bars.reduce((sum, bar) => sum + bar, 0) + bars.length - 1;
  const scale = width / total;
  let cursor = x;
  return (
    <g>
      {bars.map((bar, index) => {
        const barWidth = Math.max(0.7, bar * scale);
        const rect = (
          <rect key={index} x={cursor} y={y} width={barWidth} height={height} fill="black" />
        );
        cursor += barWidth + scale;
        return rect;
      })}
      <text
        x={x + width / 2}
        y={y + height + 18}
        textAnchor="middle"
        fontFamily="monospace"
        fontSize="14"
        fill="black"
      >
        {value}
      </text>
    </g>
  );
}

function ZplTemplatePreview({ product, products, format, quantity }) {
  const [layout, setLayout] = useState(null);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setLayout(null);
    getFormatPreview(format.code)
      .then((nextLayout) => {
        if (!cancelled) setLayout(nextLayout);
      })
      .catch(() => {
        if (!cancelled) setLayout(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [format.code]);
  if (loading && !layout) {
    return (
      <div className="flex h-32 w-full items-center justify-center rounded-md border border-dashed text-xs text-muted-foreground">
        Cargando plantilla ZPL...
      </div>
    );
  }
  if (!layout) {
    return null;
  }
  const slotProducts = products ?? Array(Math.min(3, Math.max(1, quantity))).fill(product);
  // Infer all three columns from the original layout before hiding any bars.
  const regions = buildLabelRegions(layout);
  return (
    <div className="flex w-full flex-col items-center gap-3">
      <div
        className="grid w-full max-w-[620px] gap-1.5"
        style={{
          gridTemplateColumns: regions.map((region) => `${region.width}fr`).join(" "),
        }}
      >
        {regions.map((region, regionIndex) => (
          <div
            key={`${region.start}-${region.end}`}
            className="overflow-hidden rounded-sm border-2 border-foreground/80 bg-white text-black shadow-sm"
          >
            <svg
              className="block w-full"
              viewBox={`0 0 ${region.width} ${layout.height}`}
              style={{ aspectRatio: `${region.width} / ${layout.height}` }}
              role="img"
              aria-label={`Vista previa etiqueta ${regionIndex + 1}`}
            >
              {layout.elements.map((element, index) => {
                if (getElementRegionIndex(element, regions) !== regionIndex) return null;
                const value = resolvePreviewValue(element, slotProducts, regions);
                if (!value) return null;
                return (
                  <PreviewElement
                    key={`${element.kind}-${element.field}-${element.x}-${element.y}-${index}`}
                    element={element}
                    region={region}
                    value={value}
                  />
                );
              })}
            </svg>
          </div>
        ))}
      </div>
      <div className="text-center text-xs text-muted-foreground">
        {format.name} - layout ZPL {layout.width}x{layout.height} dots
      </div>
      {quantity > 3 && (
        <p className="text-center text-xs text-muted-foreground">
          Vista del primer trabajo: 3 de {quantity} etiquetas. El backend imprime filas adicionales.
        </p>
      )}
    </div>
  );
}

function PreviewElement({ element, region, value }) {
  const localX = element.x - region.start;
  if (element.kind === "barcode") {
    const barcodeWidth = element.width ?? estimateBarcodeWidth(element, region, value);
    return (
      <BarcodeSvg
        value={value}
        x={localX}
        y={element.y}
        width={barcodeWidth}
        height={element.height ?? 52}
      />
    );
  }
  if (element.kind === "graphic") {
    return (
      <text
        x={localX}
        y={element.y + (element.height ?? 15)}
        fontFamily="monospace"
        fontSize={element.height ?? 15}
        fontWeight="700"
        fill="black"
      >
        {value}
      </text>
    );
  }
  const fontSize = element.font_height ?? 16;
  const boxWidth = element.width ?? region.width - localX;
  const textAnchor = element.align === "C" ? "middle" : element.align === "R" ? "end" : "start";
  const lines = wrapSvgText(value, element);
  const lineStep = fontSize + (element.line_spacing ?? 0);
  const x =
    element.align === "C"
      ? localX + boxWidth / 2
      : element.align === "R"
        ? localX + boxWidth
        : localX;
  return (
    <text
      x={x}
      y={element.y + fontSize}
      textAnchor={textAnchor}
      fontFamily="Arial, sans-serif"
      fontSize={fontSize}
      fontWeight="600"
      fill="black"
    >
      {lines.map((line, index) => (
        <tspan key={`${line}-${index}`} x={x} dy={index === 0 ? 0 : lineStep}>
          {line}
        </tspan>
      ))}
    </text>
  );
}

function wrapSvgText(value, element) {
  const maxLines = Math.max(1, element.lines ?? 1);
  const boxWidth = element.width;
  const fontWidth = element.font_width ?? element.font_height ?? 16;
  if (boxWidth === null || maxLines === 1) {
    return [truncateTextToWidth(value, boxWidth, fontWidth)];
  }
  const maxChars = Math.max(1, Math.floor(boxWidth / Math.max(1, fontWidth * 0.58)));
  const words = value.trim().split(/\s+/);
  const lines = [];
  let current = "";
  for (const word of words) {
    const candidate = current ? `${current} ${word}` : word;
    if (candidate.length <= maxChars) {
      current = candidate;
      continue;
    }
    if (current) lines.push(current);
    current = word;
    if (lines.length === maxLines) break;
  }
  if (current && lines.length < maxLines) {
    lines.push(current);
  }
  if (lines.length === 0) return [""];
  const lastIndex = lines.length - 1;
  lines[lastIndex] = truncateTextToWidth(lines[lastIndex], boxWidth, fontWidth);
  return lines;
}

function truncateTextToWidth(value, boxWidth, fontWidth) {
  if (boxWidth === null) return value;
  const maxChars = Math.max(1, Math.floor(boxWidth / Math.max(1, fontWidth * 0.58)));
  if (value.length <= maxChars) return value;
  if (maxChars <= 1) return value.slice(0, 1);
  return `${value.slice(0, maxChars - 1)}…`;
}

function estimateBarcodeWidth(element, region, value) {
  void value;
  const localX = element.x - region.start;
  const rightMargin = Math.max(18, localX);
  return Math.max(120, region.width - localX - rightMargin);
}

export function LabelPreview({ product, products, format, quantity = 1 }) {
  if (!product || !format) {
    return (
      <div className="flex h-64 flex-col items-center justify-center rounded-md border border-dashed text-center text-sm text-muted-foreground">
        <Package className="mb-2 h-8 w-8 opacity-60" />
        Selecciona un producto y un formato para ver la vista previa.
      </div>
    );
  }
  // Scale physical mm to px keeping proportions (4 px / mm).
  const scale = 4;
  const width = format.width_mm * scale;
  const height = format.height_mm * scale;
  const missing =
    !product.product_code ||
    (product.own_code !== false && !product.barcode) ||
    (format.preview_type === "format1" && (!product.description || !product.unit_of_measure)) ||
    (format.preview_type === "format2" && !product.presentation_quantity);
  const isTemplateBackedFormat = Boolean(format.template_file);
  return (
    <div className="flex flex-col items-center gap-3">
      {isTemplateBackedFormat ? (
        <ZplTemplatePreview
          product={product}
          products={products}
          format={format}
          quantity={quantity}
        />
      ) : (
        <div
          className="flex flex-col items-center justify-center rounded-sm border-2 border-foreground/80 bg-white p-2 text-black shadow-sm"
          style={{ width, height }}
        >
          {format.preview_type === "format1" ? (
            <div className="flex h-full w-full flex-col justify-between">
              <div>
                <div className="font-mono text-[11px] font-bold leading-tight">
                  {product.product_code}
                </div>
                <div className="line-clamp-2 text-[10px] leading-tight">{product.description}</div>
                <div className="text-[9px] uppercase opacity-70">UM: {product.unit_of_measure}</div>
              </div>
              <div className="min-h-14">
                {product.own_code !== false && <Barcode value={product.barcode} />}
              </div>
            </div>
          ) : (
            <div className="flex h-full w-full flex-col items-center justify-between">
              <div className="text-center">
                <div className="font-mono text-[12px] font-bold leading-tight">
                  {product.product_code}
                </div>
                <div className="text-[10px] leading-tight">
                  Presentacion: {formatPresentationQuantity(product.presentation_quantity)}
                </div>
              </div>
              <div className="min-h-14">
                {product.own_code !== false && <Barcode value={product.barcode} />}
              </div>
            </div>
          )}
        </div>
      )}
      {!isTemplateBackedFormat && (
        <div className="text-xs text-muted-foreground">
          {format.name} - {format.width_mm}x{format.height_mm} mm
        </div>
      )}
      {missing && (
        <p className="text-xs text-warning">No todos los campos estan disponibles en los datos.</p>
      )}
    </div>
  );
}
