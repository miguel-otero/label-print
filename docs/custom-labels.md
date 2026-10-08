# Etiqueta personalizada

La pantalla **Etiqueta personalizada** (`/custom-label`) permite cargar y reutilizar
logos PNG o JPG e imprimir exclusivamente la imagen en el rollo actual de tres
columnas. No requiere actualizar el agente Windows.

## Uso

1. Asigne un nombre y cargue un PNG/JPG de hasta 5 MB y 4096 × 4096 píxeles.
2. Seleccione una imagen de la biblioteca compartida.
3. Revise la vista previa monocromática y digite entre 1 y 400 etiquetas.
4. Confirme la impresión y consulte su estado en el historial individual.

El backend corrige la orientación EXIF, coloca las transparencias sobre blanco y
guarda un PNG sin metadatos. Para imprimir, conserva las proporciones, centra la
imagen y aplica un umbral de blanco y negro de 128. Los colores claros pueden
desaparecer: revise siempre la vista previa. No hay texto, recorte ni edición.

Cada documento ZPL contiene una fila de hasta tres imágenes. Si solicita cuatro
etiquetas, se enviarán dos filas: tres imágenes y una imagen. Las posiciones sin
imagen quedan en blanco y el rollo avanza la fila completa.

## API

| Método y ruta | Entrada / respuesta |
| --- | --- |
| `POST /api/etiqueta-personalizada/imagenes` | Multipart: `file`, `name`; devuelve la imagen registrada (201) |
| `GET /api/etiqueta-personalizada/imagenes` | Biblioteca: ID, nombre, dimensiones y fecha |
| `GET /api/etiqueta-personalizada/imagenes/{id}/contenido` | PNG normalizado |
| `GET /api/etiqueta-personalizada/imagenes/{id}/preview` | PNG de 202 × 172 píxeles, idéntico al bitmap de impresión |
| `POST /api/etiqueta-personalizada/imprimir` | JSON: `{"imagen_id": 1, "cantidad": 4}`; devuelve `job_id`, `history_id` y estado `queued` |

Los errores de archivo inválido responden 400, tamaño excesivo 413, formato no
admitido 415, imagen ausente 404 y cantidad inválida 422. Esta función requiere
PostgreSQL (503 en modo mock).

## Persistencia y despliegue

Los archivos se guardan en `storage/label-images/`, excluidos de Git. Compose monta
esa carpeta en `/data/label-images` y establece `CLINIC_LABEL_IMAGES_DIR`. Al ejecutar
el backend fuera de Docker, la ruta predeterminada apunta al directorio del
proyecto; sólo configure la variable para cambiarla.

Reconstruya y recree únicamente el backend para instalar Pillow/python-multipart
y agregar el montaje. El frontend de desarrollo carga el cambio automáticamente:

```powershell
docker compose --env-file .\conn\.env up -d --build --no-deps clinic_backend
```

El arranque crea `label_images` y agrega `kind`, `image_id` e `image_name` al
historial existente sin borrar registros. El esquema inicial también contiene
estas adiciones. Historial y trabajo se insertan en una transacción; el ZPL queda
guardado para que el reintento no dependa del archivo de imagen.

Respalde **PostgreSQL y `storage/label-images/` juntos**. Para revertir el código,
conserve las columnas, tabla y archivos: son adiciones compatibles; no hace falta
borrar datos. La biblioteca de esta versión no incluye eliminación de imágenes.

## Validación sin impresora

Las pruebas de integración crean y eliminan un esquema PostgreSQL con nombre
aleatorio `test_custom_labels_*`; ningún agente operativo puede reclamar esos
trabajos. Ejecute desde la raíz:

```powershell
docker compose --env-file .\conn\.env run --rm --no-deps -e CUSTOM_LABEL_DATABASE_TESTS=1 clinic_backend sh -c "pip install -r requirements-test.txt && python -m unittest discover -s tests -v"
```

Se comprueban procesamiento de imágenes, carga, vista previa, persistencia,
resultados exitosos/parciales/fallidos/inciertos, reintentos y rollback. La
alineación física final debe verificarse en la Zebra con el rollo instalado.
