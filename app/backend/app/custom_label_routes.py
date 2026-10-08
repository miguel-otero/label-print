from fastapi import APIRouter, File, Form, Header, UploadFile
from fastapi.responses import FileResponse, Response

from app.custom_labels import MAX_UPLOAD_BYTES, CustomLabelService, png_bytes
from app.schemas import CustomLabelPrintRequest, LabelImage, PrintResponse


def create_custom_label_router(service: CustomLabelService) -> APIRouter:
    router = APIRouter(prefix="/etiqueta-personalizada", tags=["Etiqueta personalizada"])

    @router.get("/imagenes", response_model=list[LabelImage])
    def list_images() -> list[LabelImage]:
        return service.list_images()

    @router.post("/imagenes", response_model=LabelImage, status_code=201)
    def upload_image(file: UploadFile = File(...), name: str = Form(...)) -> LabelImage:
        data = file.file.read(MAX_UPLOAD_BYTES + 1)
        return service.upload(data, file.filename or "", name)

    @router.get("/imagenes/{image_id}/contenido")
    def image_content(image_id: int) -> FileResponse:
        _, path = service.get_image(image_id)
        return FileResponse(path, media_type="image/png")

    @router.get("/imagenes/{image_id}/preview")
    def image_preview(image_id: int) -> Response:
        _, bitmap = service.bitmap(image_id)
        return Response(content=png_bytes(bitmap), media_type="image/png")

    @router.post("/imprimir", response_model=PrintResponse)
    def print_image(
        payload: CustomLabelPrintRequest,
        user: str = Header(default="operador1", alias="X-User"),
    ) -> PrintResponse:
        return service.print_image(payload.imagen_id, payload.cantidad, user)

    return router
