"""Run with unittest; database cases use an isolated, temporary PostgreSQL schema."""

import io
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import psycopg
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from PIL import Image, ImageOps
from psycopg import sql
from psycopg.rows import dict_row

from app.custom_label_routes import create_custom_label_router
from app.custom_labels import (
    MAX_UPLOAD_BYTES,
    SLOT_SIZE,
    CustomLabelError,
    CustomLabelService,
    build_custom_label_documents,
    label_bitmap,
    normalize_image,
    png_bytes,
)
from app.print_queue import PrintQueueService
from app.repository import PostgresRepository
from app.schemas import AgentDocumentResult, AgentJobResultRequest
from app.settings import Settings


def image_bytes(mode: str = "RGB", size: tuple[int, int] = (96, 48), color="black", format="PNG") -> bytes:
    output = io.BytesIO()
    Image.new(mode, size, color).save(output, format=format)
    return output.getvalue()


class ImageProcessingTests(unittest.TestCase):
    def test_transparency_is_white_and_metadata_removed(self):
        image = normalize_image(image_bytes("RGBA", color=(0, 0, 0, 0)), "logo.png")
        self.assertEqual(image.mode, "RGB")
        self.assertEqual(image.getpixel((0, 0)), (255, 255, 255))
        self.assertEqual(image.info, {})

    def test_jpeg_exif_orientation(self):
        source = Image.new("RGB", (20, 40), "black")
        exif = Image.Exif()
        exif[274] = 6
        output = io.BytesIO()
        source.save(output, format="JPEG", exif=exif)
        normalized = normalize_image(output.getvalue(), "logo.JPG")
        self.assertEqual(normalized.size, (40, 20))
        self.assertEqual(normalized.getexif(), {})

    def test_rejects_invalid_and_unsupported_uploads(self):
        cases = [
            (b"not an image", "logo.png", 400),
            (image_bytes(format="GIF"), "logo.png", 415),
            (image_bytes(), "logo.svg", 415),
            (b"x" * (MAX_UPLOAD_BYTES + 1), "logo.jpg", 413),
            (image_bytes(size=(4097, 1)), "logo.png", 400),
        ]
        for data, filename, expected_status in cases:
            with self.subTest(filename=filename, status=expected_status):
                with self.assertRaises(CustomLabelError) as error:
                    normalize_image(data, filename)
                self.assertEqual(error.exception.status_code, expected_status)

    def test_fit_preserves_aspect_and_centers(self):
        for size in [(100, 50), (50, 100), (100, 100)]:
            with self.subTest(size=size):
                bitmap = label_bitmap(Image.new("RGB", size, "black"))
                self.assertEqual(bitmap.size, SLOT_SIZE)
                bbox = ImageOps.invert(bitmap.convert("L")).getbbox()
                left, top, right, bottom = bbox
                self.assertLessEqual(abs(left - (SLOT_SIZE[0] - right)), 1)
                self.assertLessEqual(abs(top - (SLOT_SIZE[1] - bottom)), 1)
                self.assertAlmostEqual((right - left) / (bottom - top), size[0] / size[1], delta=0.02)

    def test_preview_and_zpl_are_identical_including_padding(self):
        bitmap = label_bitmap(Image.new("RGB", (100, 70), "black"))
        document = build_custom_label_documents(bitmap, 1)[0]
        match = re.search(r"\^GFA,(\d+),(\d+),(\d+),([0-9A-F]+)\^FS", document.zpl)
        count, total, row_bytes = map(int, match.groups()[:3])
        payload = bytes.fromhex(match.group(4))
        self.assertEqual(count, total)
        self.assertEqual(count, len(payload))
        self.assertEqual(row_bytes, 26)
        reconstructed = Image.frombytes("1", (row_bytes * 8, SLOT_SIZE[1]), payload)
        preview = Image.open(io.BytesIO(png_bytes(bitmap)))
        self.assertEqual(
            ImageOps.invert(reconstructed.convert("L")).crop((0, 0, *SLOT_SIZE)).tobytes(),
            preview.convert("L").tobytes(),
        )
        self.assertIsNone(reconstructed.crop((202, 0, 208, 172)).getbbox())

    def test_quantities_and_empty_slots(self):
        bitmap = label_bitmap(Image.new("RGB", (50, 50), "black"))
        for quantity in (1, 2, 3, 4, 400):
            with self.subTest(quantity=quantity):
                documents = build_custom_label_documents(bitmap, quantity)
                self.assertEqual(len(documents), (quantity + 2) // 3)
                self.assertEqual(sum(doc.item_counts[0] for doc in documents), quantity)
                for doc in documents:
                    self.assertEqual(doc.zpl.count("^GFA"), doc.item_counts[0])
                    self.assertNotIn("^FD", doc.zpl)
                if quantity % 3 == 1:
                    self.assertNotIn("^FO302", documents[-1].zpl)
                    self.assertNotIn("^FO575", documents[-1].zpl)


@unittest.skipUnless(os.environ.get("CUSTOM_LABEL_DATABASE_TESTS") == "1", "Enable isolated PostgreSQL integration tests explicitly")
class CustomLabelIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="label-images-test-")
        self.addCleanup(self.directory.cleanup)
        settings = Settings(label_images_dir=self.directory.name, history_table="print_history", print_agent_id="test-custom-agent")
        self.schema = f"test_custom_labels_{uuid4().hex}"
        self.connection_options = dict(
            host=settings.database_host, port=settings.database_port,
            dbname=settings.database_name, user=settings.database_user,
            password=settings.database_password, row_factory=dict_row,
        )
        with psycopg.connect(**self.connection_options) as conn:
            conn.execute(sql.SQL("create schema {}").format(sql.Identifier(self.schema)))
        self.addCleanup(self.drop_schema)

        class IsolatedQueue(PrintQueueService):
            def _connect(queue):
                return psycopg.connect(**self.connection_options, options=f"-c search_path={self.schema}")

        self.queue = IsolatedQueue(settings)
        with self.queue._connect() as conn:
            conn.execute('''create table print_history (
                id bigint generated by default as identity primary key,
                timestamp timestamptz not null default now(), "user" text not null,
                product_code text not null, product_description text not null,
                format text not null, quantity integer not null, status text not null, message text
            )''')
            conn.execute("create table print_batches (id bigint primary key, status text, message text, printed_labels integer, failed_labels integer)")
            conn.execute("create table print_batch_items (id bigint primary key, status text)")
        self.queue.ensure_schema()
        self.service = CustomLabelService(settings, self.queue)
        self.service.ensure_schema()
        app = FastAPI()

        @app.exception_handler(CustomLabelError)
        async def error_handler(_, exc):
            return JSONResponse(status_code=exc.status_code, content={"detail": str(exc)})

        app.include_router(create_custom_label_router(self.service), prefix="/api")
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def drop_schema(self):
        if not self.schema.startswith("test_custom_labels_"):
            raise RuntimeError("Refusing to drop non-test schema")
        with psycopg.connect(**self.connection_options) as conn:
            conn.execute(sql.SQL("drop schema {} cascade").format(sql.Identifier(self.schema)))

    def upload(self):
        response = self.client.post("/api/etiqueta-personalizada/imagenes", data={"name": "Logo de prueba"}, files={"file": ("logo.png", image_bytes(), "image/png")})
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def enqueue(self, image_id, quantity=4):
        response = self.client.post("/api/etiqueta-personalizada/imprimir", json={"imagen_id": image_id, "cantidad": quantity})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def complete(self, job, failed=False):
        return self.queue.complete(job.id, AgentJobResultRequest(agent_id="test-custom-agent", documents=[
            AgentDocumentResult(document_id=doc.id, ok=not failed, message="Error simulado" if failed else None)
            for doc in job.documents
        ]))

    def test_upload_preview_persistence_and_successful_queue(self):
        image = self.upload()
        self.service.ensure_schema()  # A second startup must preserve the library.
        self.assertEqual(len(self.service.list_images()), 1)
        root = f"/api/etiqueta-personalizada/imagenes/{image['id']}"
        self.assertEqual(self.client.get(root + "/contenido").status_code, 200)
        preview = self.client.get(root + "/preview")
        self.assertEqual(Image.open(io.BytesIO(preview.content)).size, SLOT_SIZE)
        result = self.enqueue(image["id"])
        job = self.queue.claim("test-custom-agent")
        self.assertEqual(job.kind, "custom_label")
        self.assertEqual([doc.zpl.count("^GFA") for doc in job.documents], [3, 1])
        self.assertEqual(self.complete(job)["status"], "success")
        with self.queue._connect() as conn:
            counts = conn.execute("select printed_labels, failed_labels from print_jobs where id = %s", (result["job_id"],)).fetchone()
            history = conn.execute("select kind, image_name, status from print_history where id = %s", (result["history_id"],)).fetchone()
        self.assertEqual(counts, {"printed_labels": 4, "failed_labels": 0})
        self.assertEqual(history, {"kind": "custom_label", "image_name": "Logo de prueba", "status": "success"})

    def test_error_retry_uses_frozen_zpl_even_without_image(self):
        image = self.upload()
        result = self.enqueue(image["id"], 2)
        job = self.queue.claim("test-custom-agent")
        self.assertEqual(self.complete(job, failed=True)["status"], "error")
        _, path = self.service.get_image(image["id"])
        path.unlink()
        retried_id = self.queue.retry(result["job_id"])
        retried = self.queue.claim("test-custom-agent")
        self.assertEqual(retried.id, retried_id)
        self.assertEqual([doc.zpl for doc in retried.documents], [doc.zpl for doc in job.documents])
        self.assertEqual(self.complete(retried)["status"], "success")

    def test_partial_and_stale_jobs(self):
        image = self.upload()
        self.enqueue(image["id"], 4)
        job = self.queue.claim("test-custom-agent")
        result = self.queue.complete(job.id, AgentJobResultRequest(agent_id="test-custom-agent", documents=[
            AgentDocumentResult(document_id=job.documents[0].id, ok=True),
            AgentDocumentResult(document_id=job.documents[1].id, ok=False),
        ]))
        self.assertEqual(result["status"], "partial")
        stale = self.enqueue(image["id"], 1)
        self.queue.claim("test-custom-agent")
        with self.queue._connect() as conn:
            conn.execute("update print_jobs set claimed_at = now() - interval '10 minutes' where id = %s", (stale["job_id"],))
        self.queue.mark_stale_jobs()
        with self.queue._connect() as conn:
            history = conn.execute("select status from print_history where id = %s", (stale["history_id"],)).fetchone()
        self.assertEqual(history["status"], "unknown")
        self.queue.retry(stale["job_id"])

    def test_enqueue_failure_rolls_back_history(self):
        image = self.upload()
        with patch.object(self.queue, "enqueue", side_effect=RuntimeError("Simulated database error")):
            with self.assertRaises(RuntimeError):
                self.service.print_image(image["id"], 1, "test")
        with self.queue._connect() as conn:
            self.assertEqual(conn.execute("select count(*) as count from print_history").fetchone()["count"], 0)

    def test_upload_database_failure_cleans_files(self):
        with patch.object(self.queue, "_connect", side_effect=RuntimeError("Simulated database error")):
            with self.assertRaises(RuntimeError):
                self.service.upload(image_bytes(), "logo.png", "test")
        self.assertEqual(list(Path(self.directory.name).iterdir()), [])

    def test_api_validation_and_missing_files(self):
        image = self.upload()
        for quantity in (0, -1, 401, 1.5, True, "2"):
            response = self.client.post("/api/etiqueta-personalizada/imprimir", json={"imagen_id": image["id"], "cantidad": quantity})
            self.assertEqual(response.status_code, 422)
        self.assertEqual(self.client.get("/api/etiqueta-personalizada/imagenes/999/preview").status_code, 404)
        _, path = self.service.get_image(image["id"])
        path.unlink()
        self.assertEqual(self.client.get(f"/api/etiqueta-personalizada/imagenes/{image['id']}/preview").status_code, 404)
        self.assertEqual(self.client.post("/api/etiqueta-personalizada/imagenes", data={"name": "   "}, files={"file": ("logo.png", image_bytes())}).status_code, 400)

    def test_http_upload_validation_and_jpeg(self):
        for filename, data, expected_status in (
            ("logo.svg", image_bytes(), 415),
            ("logo.png", b"invalid image", 400),
            ("logo.png", b"x" * (MAX_UPLOAD_BYTES + 1), 413),
            ("logo.jpg", image_bytes(format="JPEG"), 201),
        ):
            with self.subTest(filename=filename, status=expected_status):
                response = self.client.post("/api/etiqueta-personalizada/imagenes", data={"name": "test"}, files={"file": (filename, data)})
                self.assertEqual(response.status_code, expected_status, response.text)

    def test_product_history_and_existing_enqueue_remain_compatible(self):
        with self.queue._connect() as conn:
            history_id = conn.execute('''insert into print_history
                ("user", product_code, product_description, format, quantity, status)
                values ('test', 'SKU1', 'Producto', '3_etiquetas_v3', 1, 'queued') returning id''').fetchone()["id"]
        documents = build_custom_label_documents(label_bitmap(Image.new("RGB", (30, 30), "black")), 1)
        self.queue.enqueue(kind="individual", documents=documents, requested_labels=1, history_id=history_id)
        self.complete(self.queue.claim("test-custom-agent"))
        repo = PostgresRepository(self.queue.settings)
        with patch.object(repo, "_connect", side_effect=self.queue._connect):
            entry = repo.get_history()[0]
        self.assertEqual(entry.kind, "individual")
        self.assertEqual(entry.product_code, "SKU1")
        self.assertIsNone(entry.image_id)
        self.assertEqual(entry.status, "success")


if __name__ == "__main__":
    unittest.main()
