import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs) {
  return twMerge(clsx(inputs));
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
