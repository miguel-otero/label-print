import assert from "node:assert/strict";
import { test } from "node:test";
import { buildLabelRegions, resolvePreviewValue } from "../src/shared/utils/label-preview.js";
import {
  barcodeModeLabel,
  batchPreviewProducts,
  presentationOptionLabel,
} from "../src/shared/utils/utils.js";

const own = {
  own_code: true,
  barcode: "12345",
  product_code: "REF-A",
  description: "Propio",
  presentation_quantity: "1.0000 UN",
};
const foreign = {
  own_code: false,
  barcode: "",
  product_code: "REF-B",
  description: "Fabricante",
  presentation_quantity: "2.0000 UN",
};
const barcodes = [32, 302, 575].map((x, index) => ({
  kind: "barcode",
  field: `Codigobarras${index + 1}`,
  x,
  width: null,
}));
const layout = { width: 799, elements: barcodes };

test("mixed batches preview actual first-row products, skipping zero quantities", () => {
  const products = batchPreviewProducts([
    { product: own, quantity: 0 },
    { product: null, quantity: 1 },
    { product: foreign, quantity: 1 },
    { product: own, quantity: 3 },
  ]);
  assert.deepEqual(products, [foreign, own, own]);
  const regions = buildLabelRegions(layout);
  assert.deepEqual(
    barcodes.map((element) => resolvePreviewValue(element, products, regions)),
    ["", "12345", "12345"],
  );
  assert.equal(
    resolvePreviewValue({ kind: "text", field: "Codigo1", x: 140, width: 94 }, products, regions),
    "REF-B",
  );
});

test("all foreign labels keep three columns and hide bars plus their digits", () => {
  const products = [foreign, foreign, foreign];
  const regions = buildLabelRegions(layout);
  assert.deepEqual(
    regions.map((region) => region.width),
    [270, 273, 256],
  );
  assert.deepEqual(
    barcodes.map((element) => resolvePreviewValue(element, products, regions)),
    ["", "", ""],
  );
  assert.equal(
    resolvePreviewValue(
      { kind: "text", field: "Presentacion3", x: 702, width: 75 },
      products,
      regions,
    ),
    "2 UN",
  );
});

test("empty slots also hide unnumbered static captions", () => {
  const regions = buildLabelRegions(layout);
  const products = [foreign];
  assert.equal(
    resolvePreviewValue({ kind: "text", field: "CODIGO:", x: 0, width: 668 }, products, regions),
    "",
  );
  assert.equal(
    resolvePreviewValue(
      { kind: "text", field: "PRESENTACION:", x: 473, width: 326 },
      products,
      regions,
    ),
    "",
  );
  assert.equal(resolvePreviewValue(barcodes[1], products, regions), "");
  assert.equal(
    resolvePreviewValue(
      { kind: "text", field: "Descripcion1", x: 32, width: 202 },
      products,
      regions,
    ),
    "Fabricante",
  );
});

test("selectors distinguish modes, keep integer presentation and unknown history", () => {
  assert.equal(presentationOptionLabel(own), "1 UN · Con código de barras · 12345");
  assert.equal(presentationOptionLabel(foreign), "2 UN · Sin código de barras");
  assert.equal(barcodeModeLabel(null), "Modalidad no registrada");
});
