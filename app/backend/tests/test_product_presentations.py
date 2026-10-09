"""Presentation and queue regressions; integration cases never use the real queue."""

import itertools
import os
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from app.inventory_print import InventoryPrintError, InventoryPrintService
from app.print_queue import PrintQueueService
from app.printer import (
    PrinterError, build_individual_queue_documents, empty_template_values,
    load_template, populate_template, remove_empty_template_slot,
    replace_template_values, template_values,
)
from app.repository import MockRepository, PostgresRepository
from app.schemas import (
    AgentDocumentResult, AgentJobResultRequest, InventoryBatchPrintRequest,
    InventoryEntryBatchPrintRequest, LabelFormat, Product,
)
from app.settings import Settings
from app.zpl_preview import parse_zpl_preview_layout


TEMPLATES = Path(__file__).resolve().parents[1] / "label_templates"


def product(own_code: bool, **overrides) -> Product:
    values = dict(
        id=1, product_code="REF-INTERNA", description="Producto de prueba",
        unit_of_measure="UN", barcode="123456789012" if own_code else "",
        own_code=own_code, barcode_unit_measure="UN", quantity_per_unit="1.0000",
        presentation_quantity="1.0000 UN", line="Prueba",
    )
    return Product(**(values | overrides))


def label_format(filename: str) -> LabelFormat:
    return LabelFormat(id=1, name="Prueba", code="TEST", width_mm=100,
                       height_mm=25, preview_type="format2", active=True,
                       template_file=filename)


class PresentationZplTests(unittest.TestCase):
    def test_all_barcode_combinations_and_empty_slots(self):
        for path in TEMPLATES.glob("*.zpl"):
            template = load_template(path.name)
            original = parse_zpl_preview_layout(code="TEST", zpl=template)
            self.assertEqual(sum(item.kind == "barcode" for item in original.elements), 3)
            for count in (1, 2, 3):
                for modes in itertools.product((False, True), repeat=count):
                    with self.subTest(template=path.name, modes=modes):
                        products = [product(mode, id=index + 1, product_code=f"REF-{index + 1}")
                                    for index, mode in enumerate(modes)]
                        zpl = populate_template(template=template, products=products)
                        layout = parse_zpl_preview_layout(code="TEST", zpl=zpl)
                        self.assertEqual(zpl.count("^BC"), sum(modes))
                        self.assertEqual(zpl.count("^BY"), sum(modes))
                        self.assertEqual(sum(item.kind == "text" for item in layout.elements), count * 5)
                        self.assertNotIn("Codigobarras", zpl)
                        for index in range(1, 4):
                            self.assertEqual(f"REF-{index}" in zpl, index <= count)
                        for item in layout.elements:
                            if item.kind == "barcode":
                                self.assertEqual(item.field, "123456789012")

    def test_existing_barcode_zpl_is_unchanged(self):
        selected = product(True)
        for path in TEMPLATES.glob("*.zpl"):
            template = load_template(path.name)
            for count in (1, 2, 3):
                # Original population algorithm, including dynamic region discovery.
                expected = template
                replacements = {}
                for position in range(1, 4):
                    if position <= count:
                        replacements.update(template_values(product=selected, position=position))
                    else:
                        expected = remove_empty_template_slot(expected, position)
                        replacements.update(empty_template_values(position=position))
                expected = replace_template_values(expected, replacements)
                self.assertEqual(populate_template(template=template, products=[selected] * count), expected)

    def test_individual_quantities_and_missing_manufacturer_barcode(self):
        for path in TEMPLATES.glob("*.zpl"):
            for quantity in (1, 2, 3, 4, 7):
                documents = build_individual_queue_documents(
                    label_format=label_format(path.name), product=product(False), quantity=quantity,
                )
                self.assertEqual(len(documents), (quantity + 2) // 3)
                self.assertEqual(sum(document.item_counts[0] for document in documents), quantity)
                for document in documents:
                    self.assertNotIn("^BC", document.zpl)
                    self.assertNotIn("^BY", document.zpl)
                    self.assertEqual(document.zpl.count("REF-INTERNA"), document.item_counts[0])
                    self.assertIn("^FD1 UN^FS", document.zpl)

    def test_invalid_presentations_are_rejected_without_inventing_values(self):
        template = load_template(next(TEMPLATES.glob("*.zpl")).name)
        for changes in (
            {"quantity_per_unit": ""}, {"quantity_per_unit": "0"},
            {"quantity_per_unit": "NaN"}, {"quantity_per_unit": "-1"},
            {"barcode_unit_measure": " "}, {"presentation_quantity": ""},
        ):
            with self.subTest(changes=changes), self.assertRaises(PrinterError):
                populate_template(template=template, products=[product(False, **changes)])
        InventoryPrintService._validate_presentation(product(False))
        with self.assertRaises(InventoryPrintError):
            InventoryPrintService._validate_presentation(product(True, barcode=""))

    def test_mock_catalog_groups_before_pagination_and_matches_aliases(self):
        rows = [product(False, id=2, barcode="MFR-A"),
                product(False, id=3, barcode="MFR-B", quantity_per_unit="01", barcode_unit_measure=" un "),
                product(True, id=4)]
        with patch("app.repository.PRODUCTS", rows):
            repository = MockRepository()
            self.assertEqual(repository.count_products(None, lines=[]), 2)
            result = repository.search_products("MFR-B", lines=[], limit=1, offset=0)
            self.assertEqual([item.id for item in result], [2])


@unittest.skipUnless(os.environ.get("PRESENTATION_DATABASE_TESTS") == "1", "Enable isolated PostgreSQL tests explicitly")
class PresentationIntegrationTests(unittest.TestCase):
    def setUp(self):
        settings = Settings(data_source="postgres", print_agent_id="test-presentation-agent")
        self.schema = f"test_presentations_{uuid4().hex}"
        options = dict(host=settings.database_host, port=settings.database_port,
                       dbname=settings.database_name, user=settings.database_user,
                       password=settings.database_password, row_factory=dict_row)
        self.options = options
        with psycopg.connect(**options) as conn:
            conn.execute(sql.SQL("create schema {}").format(sql.Identifier(self.schema)))
        self.addCleanup(self.drop_schema)

        def connect(_):
            # No public fallback: every service, including claim/retry, stays isolated.
            return psycopg.connect(**options, options=f"-c search_path={self.schema}")

        self.queue = type("IsolatedQueue", (PrintQueueService,), {"_connect": connect})(settings)
        self.repository = type("IsolatedRepository", (PostgresRepository,), {"_connect": connect})(settings)
        self.service = type("IsolatedInventory", (InventoryPrintService,), {"_connect": connect})(settings, self.queue)
        with self.queue._connect() as conn:
            # Only the temporary schema is visible to this bootstrap script.
            schema_path = Path("/scripts/postgres_schema.sql")
            if not schema_path.exists():
                schema_path = Path(__file__).resolve().parents[3] / "scripts/postgres_schema.sql"
            conn.execute(schema_path.read_text(encoding="utf-8-sig"))
            conn.execute("alter table print_history drop column prints_barcode")
            conn.execute("alter table print_batch_items drop column prints_barcode")
            conn.execute('''insert into print_history
                ("user", product_code, product_description, format, quantity, status)
                values ('test', 'OLD', 'Anterior', 'TEST', 1, 'success')''')
        self.queue.ensure_schema()
        self.service.ensure_schema()
        self.queue.ensure_schema()
        self.service.ensure_schema()
        with self.queue._connect() as conn:
            rows = [
                (1, "BOTH", "Propio", "UN", "OWN-1", "1", "UN", "Mixta", True),
                (2, "BOTH", "Fabricante", "UN", "MFR-1", "1.0", "UN", "Mixta", False),
                (3, "BOTH", "Fabricante", "UN", "MFR-2", "01,00", " un ", "Mixta", False),
                (4, "FOREIGN", "Sin propio", "UN", "", "2", "UN", "Solo fabricante", False),
                (5, "BOTH", "Propio", "UN", "OWN-2", "1", "UN", "Mixta", True),
                (6, "INVALID", "Sin UM", "UN", "", "0", "", "Invalida", False),
            ]
            with conn.cursor() as cursor:
                cursor.executemany('''insert into products
                    (id, referencia, descripcion, um_siesa, codigo_barra, cantidadxum,
                     unidad_de_medida_barras, linea, codigo_propio)
                    values (%s, %s, %s, %s, %s, %s, %s, %s, %s)''', rows)
            conn.execute("insert into inventory (referencia, inventario, bodega) values ('BOTH', 12, 'TEST'), ('FOREIGN', 10, 'TEST'), ('INVALID', 1, 'TEST')")
            conn.execute("insert into inventory_entries (referencia, entradas_inv, documento, fecha, bodega) values ('BOTH', 12, 'DOC', current_date, 'TEST'), ('FOREIGN', 10, 'DOC', current_date, 'TEST'), ('INVALID', 1, 'DOC', current_date, 'TEST')")
            conn.execute("insert into label_formats (name, code, width_mm, height_mm, preview_type, active, template_file) values ('Prueba', 'TEST', 100, 25, 'format2', true, %s)", (next(TEMPLATES.glob("*.zpl")).name,))

    def drop_schema(self):
        if not self.schema.startswith("test_presentations_"):
            raise RuntimeError("Refusing to drop non-test schema")
        with psycopg.connect(**self.options) as conn:
            conn.execute(sql.SQL("drop schema {} cascade").format(sql.Identifier(self.schema)))

    def inventory(self, **overrides):
        return self.service.search_inventory(**(dict(warehouse="TEST", search=None, lines=[],
                                                    availability="all", limit=50, offset=0) | overrides))

    def finish(self, job, ok=True):
        return self.queue.complete(job.id, AgentJobResultRequest(
            agent_id="test-presentation-agent", documents=[
                AgentDocumentResult(document_id=doc.id, ok=ok) for doc in job.documents
            ],
        ))

    def test_catalog_search_totals_pagination_lines_and_alias_identity(self):
        self.assertEqual(self.repository.count_products(None, lines=[]), 5)
        rows = self.repository.search_products("MFR-2", lines=[], limit=1, offset=0)
        self.assertEqual([row.id for row in rows], [2])
        self.assertEqual(self.repository.count_products("MFR-2", lines=[]), 1)
        self.assertEqual(self.repository.count_products(None, lines=["Solo fabricante"]), 1)
        self.assertIn("Solo fabricante", self.repository.get_product_lines())
        self.assertFalse(self.repository.get_product(3).own_code)
        self.assertIsNone(self.repository.get_product(99))
        ids = [self.repository.search_products(None, lines=[], limit=1, offset=i)[0].id for i in range(5)]
        self.assertEqual(len(set(ids)), 5)
        with self.queue._connect() as conn:
            self.assertEqual(conn.execute("select count(*) as n from products").fetchone()["n"], 6)

    def test_inventory_and_entries_include_grouped_presentations_and_refresh(self):
        rows, total = self.inventory()
        self.assertEqual(total, 3)
        both = next(row for row in rows if row.reference == "BOTH")
        self.assertEqual({item.id for item in both.presentations}, {1, 2, 5})
        self.assertTrue(next(row for row in rows if row.reference == "FOREIGN").printable)
        self.assertFalse(next(row for row in rows if row.reference == "INVALID").printable)
        self.assertEqual(self.inventory(availability="printable")[1], 2)
        self.assertEqual(self.inventory(search="MFR-2")[1], 1)
        self.assertEqual(self.inventory(lines=["Solo fabricante"])[1], 1)
        refreshed = self.service.get_inventory_selection(warehouse="TEST", references=["FOREIGN", "BOTH"])
        self.assertEqual(len(refreshed), 2)
        entries = self.service.get_entry_document_items(warehouse="TEST", document="DOC")
        self.assertEqual({item.id for item in next(row for row in entries if row.reference == "BOTH").presentations}, {1, 2, 5})
        self.assertTrue(next(row for row in entries if row.reference == "FOREIGN").printable)

    def test_individual_history_and_retry_preserve_original_zpl(self):
        old = self.repository.get_history()[0]
        self.assertIsNone(old.prints_barcode)
        for product_id, expected in ((1, True), (2, False)):
            selected = self.repository.get_product(product_id)
            documents = build_individual_queue_documents(label_format=self.repository.get_format("TEST"), product=selected, quantity=4)
            history = self.repository.add_history(product=selected, label_format="TEST", quantity=4,
                                                   status="queued", message=None, user="test")
            self.assertEqual(history.prints_barcode, expected)
            job_id = self.queue.enqueue(kind="individual", documents=documents, requested_labels=4, history_id=history.id)
            job = self.queue.claim("test-presentation-agent")
            self.assertEqual(job.id, job_id)
            self.assertEqual(self.finish(job, ok=False)["status"], "error")
            with self.queue._connect() as conn:
                conn.execute("update products set codigo_propio = not codigo_propio, codigo_barra = 'CHANGED' where id = %s", (product_id,))
            self.queue.retry(job_id)
            retried = self.queue.claim("test-presentation-agent")
            self.assertEqual([doc.zpl for doc in retried.documents], [doc.zpl for doc in job.documents])
            self.assertEqual(self.finish(retried)["status"], "success")
            self.assertEqual(next(item for item in self.repository.get_history() if item.id == history.id).prints_barcode, expected)

    def test_mixed_inventory_and_entry_batches_history_and_validation(self):
        inventory, _ = self.inventory()
        entries = self.service.get_entry_document_items(warehouse="TEST", document="DOC")
        for source in ("inventory", "entry"):
            with self.subTest(source=source):
                rows = inventory if source == "inventory" else entries
                ids = {row.reference: row.id for row in rows}
                key = "inventory_id" if source == "inventory" else "entry_id"
                request_type = InventoryBatchPrintRequest if source == "inventory" else InventoryEntryBatchPrintRequest
                send = self.service.print_batch if source == "inventory" else self.service.print_entry_batch
                base = dict(format="TEST", warehouse="TEST")
                if source == "entry":
                    base["document"] = "DOC"
                # First row: own + foreign + foreign; second row: foreign only.
                payload = request_type(**base, items=[
                    {key: ids["BOTH"], "product_id": 1, "quantity": 1},
                    {key: ids["FOREIGN"], "product_id": 4, "quantity": 3},
                ])
                result = send(payload, user="test")
                self.assertEqual([item.prints_barcode for item in result.items], [True, False])
                job = self.queue.claim("test-presentation-agent")
                self.assertEqual([doc.zpl.count("^BC") for doc in job.documents], [1, 0])
                self.assertEqual(self.finish(job)["status"], "success")
                history = next(item for item in self.service.get_batch_history() if item.id == result.batch_id)
                self.assertEqual(history.printed_labels, 4)
                self.assertEqual([item.prints_barcode for item in history.items], [True, False])
                for item in (
                    {key: ids["INVALID"], "product_id": 6, "quantity": 1},
                    {key: ids["FOREIGN"], "product_id": 1, "quantity": 1},
                    {key: ids["FOREIGN"], "product_id": 4, "quantity": 401},
                ):
                    with self.assertRaises(InventoryPrintError):
                        send(request_type(**base, items=[item]), user="test")


if __name__ == "__main__":
    unittest.main()
