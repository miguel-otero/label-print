import { formatPresentationQuantity } from "./utils.js";

export function buildLabelRegions(layout) {
  const anchors = layout.elements
    .filter((element) => element.kind === "barcode")
    .map((element) => element.x)
    .sort((a, b) => a - b);
  if (anchors.length < 2) {
    return [{ start: 0, end: layout.width, width: layout.width }];
  }
  const firstBarcodeInset = anchors[0];
  const boundaries = [
    ...anchors.map((anchor) => Math.max(0, anchor - firstBarcodeInset)),
    layout.width,
  ];
  return boundaries.slice(0, -1).map((start, index) => {
    const end = boundaries[index + 1];
    return { start, end, width: end - start };
  });
}

export function getElementRegionIndex(element, regions) {
  const fieldPosition = readFieldPosition(element.field);
  if (fieldPosition !== null && fieldPosition >= 1 && fieldPosition <= regions.length) {
    return fieldPosition - 1;
  }
  const anchorX = element.width !== null ? element.x + element.width / 2 : element.x;
  const index = regions.findIndex((region) => anchorX >= region.start && anchorX < region.end);
  return index === -1 ? regions.length - 1 : index;
}

export function resolvePreviewValue(element, products, regions) {
  const product = products[getElementRegionIndex(element, regions)];
  if (!product) return "";
  if (product.own_code === false && /Codigobarras\d*/.test(element.field)) return "";
  if (element.kind === "graphic") return element.label ?? "";
  return element.field
    .replace(/Descripcion\d*/g, product.description)
    .replace(/Codigo(?!barras)\d*/g, product.product_code)
    .replace(/Presentacion\d*/g, formatPresentationQuantity(product.presentation_quantity))
    .replace(/Codigobarras\d*/g, product.barcode);
}

function readFieldPosition(field) {
  const match = field.match(
    /(?:Descripcion|CodigoLabel|Codigo|PresentacionLabel|Presentacion|Codigobarras)(\d+)/,
  );
  return match ? Number(match[1]) : null;
}
