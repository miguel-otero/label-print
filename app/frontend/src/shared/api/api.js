export const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8080/api";

async function apiRequest(path, init) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });
  let body;
  try {
    body = await res.json();
  } catch {
    body = null;
  }
  if (!res.ok) {
    let message = `Error HTTP ${res.status}`;
    if (isApiObject(body)) {
      message = String(body.detail ?? body.message ?? message);
    }
    throw new Error(message);
  }
  if (isApiObject(body) && body.ok === false) {
    throw new Error(String(body.message ?? "La operacion no fue exitosa"));
  }
  return body;
}

function isApiObject(value) {
  return typeof value === "object" && value !== null;
}
// GET /productos?search=&page=&page_size=
export async function searchProducts(query, page = 1, pageSize = 100, lines = []) {
  const params = new URLSearchParams();
  if (query.trim()) params.set("search", query.trim());
  lines.forEach((line) => params.append("line", line));
  params.set("page", String(page));
  params.set("page_size", String(pageSize));
  const qs = params.toString();
  const res = await fetch(`${API_BASE}/productos?${qs}`, {
    headers: {
      "Content-Type": "application/json",
    },
  });
  let body;
  try {
    body = await res.json();
  } catch {
    body = null;
  }
  if (!res.ok) {
    let message = `Error HTTP ${res.status}`;
    if (isApiObject(body)) {
      message = String(body.detail ?? body.message ?? message);
    }
    throw new Error(message);
  }
  return {
    items: body,
    total: Number(res.headers.get("X-Total-Count") ?? 0),
  };
}

export async function getProductLines() {
  return apiRequest("/productos/lineas");
}
// GET /formatos
export async function getFormats(includeInactive = false) {
  const suffix = includeInactive ? "?include_inactive=true" : "";
  return apiRequest(`/formatos${suffix}`);
}

export async function getFormatTemplates() {
  return apiRequest("/formatos/plantillas");
}

export async function saveFormat(payload, formatId) {
  return apiRequest(formatId ? `/formatos/${formatId}` : "/formatos", {
    method: formatId ? "PUT" : "POST",
    body: JSON.stringify(payload),
  });
}

export async function deleteFormat(formatId) {
  return apiRequest(`/formatos/${formatId}`, {
    method: "DELETE",
  });
}
// GET /formatos/{code}/preview
export async function getFormatPreview(code) {
  return apiRequest(`/formatos/${encodeURIComponent(code)}/preview`);
}
// POST /imprimir  { formato, producto_id, cantidad }
export async function printLabel(payload) {
  return apiRequest("/imprimir", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getInventoryWarehouses() {
  return apiRequest("/inventario/bodegas");
}

export async function searchInventory(
  warehouse,
  query,
  availability,
  page = 1,
  pageSize = 100,
  lines = [],
) {
  const params = new URLSearchParams({
    warehouse,
    availability,
    page: String(page),
    page_size: String(pageSize),
  });
  if (query.trim()) params.set("search", query.trim());
  lines.forEach((line) => params.append("line", line));
  const res = await fetch(`${API_BASE}/inventario?${params.toString()}`, {
    headers: { "Content-Type": "application/json" },
  });
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const message = isApiObject(body)
      ? String(body.detail ?? body.message ?? `Error HTTP ${res.status}`)
      : `Error HTTP ${res.status}`;
    throw new Error(message);
  }
  return {
    items: body,
    total: Number(res.headers.get("X-Total-Count") ?? 0),
  };
}

export async function getInventoryEntryDocuments(warehouse, query, page = 1, pageSize = 100) {
  const params = new URLSearchParams({
    warehouse,
    page: String(page),
    page_size: String(pageSize),
  });
  if (query.trim()) params.set("search", query.trim());
  const res = await fetch(`${API_BASE}/inventario/entradas/documentos?${params.toString()}`, {
    headers: { "Content-Type": "application/json" },
  });
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const message = isApiObject(body)
      ? String(body.detail ?? body.message ?? `Error HTTP ${res.status}`)
      : `Error HTTP ${res.status}`;
    throw new Error(message);
  }
  return {
    items: body,
    total: Number(res.headers.get("X-Total-Count") ?? 0),
  };
}

export async function getInventoryEntryDocumentItems(warehouse, document) {
  const params = new URLSearchParams({ warehouse });
  return apiRequest(
    `/inventario/entradas/documentos/${encodeURIComponent(document)}?${params.toString()}`,
  );
}

export async function getInventoryPrintSettings() {
  return apiRequest("/configuracion/impresion-inventario");
}

export async function refreshInventorySelection(warehouse, references) {
  return apiRequest("/inventario/seleccion", {
    method: "POST",
    body: JSON.stringify({ warehouse, references }),
  });
}

export async function saveInventoryPrintSettings(payload) {
  return apiRequest("/configuracion/impresion-inventario", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function printInventoryBatch(payload) {
  return apiRequest("/imprimir-inventario", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function printInventoryEntryBatch(payload) {
  return apiRequest("/imprimir-inventario/entrada", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function syncInventory() {
  await apiRequest("/sincronizacion/inventario", { method: "POST" });
}
// POST /impresora/test
export async function testPrinter() {
  return apiRequest("/impresora/test", {
    method: "POST",
  });
}
// POST /impresora/test/etiqueta
export async function printTestLabel() {
  return apiRequest("/impresora/test/etiqueta", {
    method: "POST",
  });
}
// GET /historial
export async function getHistory() {
  return apiRequest("/historial");
}

export async function getBatchHistory() {
  return apiRequest("/historial/lotes");
}

export async function pingBackend() {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 2500);
  try {
    const res = await fetch(`${API_BASE}/health`, {
      cache: "no-store",
      signal: controller.signal,
    });
    if (!res.ok) return false;
    const body = await res.json();
    return body.status === "ok";
  } catch {
    return false;
  } finally {
    window.clearTimeout(timeout);
  }
}
