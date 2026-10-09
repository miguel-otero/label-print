import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

export function barcodeModeLabel(printsBarcode) {
  if (printsBarcode === null || printsBarcode === undefined) return "Modalidad no registrada";
  return printsBarcode ? "Con código de barras" : "Sin código de barras";
}

export function presentationOptionLabel(product) {
  return `${formatPresentationQuantity(product.presentation_quantity)} · ${barcodeModeLabel(product.own_code !== false)}${product.own_code !== false ? ` · ${product.barcode}` : ""}`;
}

export function batchPreviewProducts(items) {
  const products = [];
  for (const item of items) {
    if (!item.product || item.quantity <= 0) continue;
    const count = Math.min(3 - products.length, item.quantity);
    products.push(...Array(count).fill(item.product));
    if (products.length === 3) break;
  }
  return products;
}

export function formatPresentationQuantity(value) {
  if (value === null || value === undefined || value === "") return "";
  const text = String(value);
  const match = text.match(/^\s*([+-]?\d+(?:[.,]\d+)?)(.*)$/);
  if (!match) return text;
  const quantity = Number(match[1].replace(",", "."));
  if (!Number.isFinite(quantity)) return text;
  return `${Math.round(quantity)}${match[2]}`;
}
