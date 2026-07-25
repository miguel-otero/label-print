# Clinic Label Print Backend

FastAPI backend para buscar productos, generar ZPL y enviar etiquetas a una cola de impresion Zebra.

## Docker

El backend puede correr en Docker junto con PostgreSQL:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1 -Mode Docker -Build
```

En Docker, `CLINIC_DATABASE_HOST` apunta a `clinic_db` y la impresion queda en modo `simulated`.

## Ejecucion USB en Windows

Para imprimir por USB, el backend debe correr localmente en Windows porque Docker no ve la cola USB del host.

Desde la raiz del repo:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1
```

Ese comando usa `-Mode Usb` por defecto. Levanta PostgreSQL y el frontend en Docker, y ejecuta el backend local en:

```text
http://localhost:8080/api
```

El backend local se conecta a PostgreSQL usando el host y puerto configurados en `conn/backend.env`. Las credenciales se leen de `conn/.env`.

```env
CLINIC_DATABASE_HOST=localhost
CLINIC_DATABASE_PORT=5432
```

## Configuracion

La configuracion base vive en `conn/backend.env`.

Datos PostgreSQL:

```env
CLINIC_DATA_SOURCE=postgres
CLINIC_DATABASE_HOST=localhost
CLINIC_DATABASE_PORT=5432
```

Los valores `CLINIC_DATABASE_NAME`, `CLINIC_DATABASE_USER` y `CLINIC_DATABASE_PASSWORD` viven exclusivamente en `conn/.env`, ignorado por Git. El archivo `conn/.env.example` documenta las variables requeridas.

## Sincronizacion SQL Server

Completa en `conn/.env`:

```env
CLINIC_EXTERNAL_DATABASE_HOST=...
CLINIC_EXTERNAL_DATABASE_NAME=...
CLINIC_EXTERNAL_DATABASE_USER=...
CLINIC_EXTERNAL_DATABASE_PASSWORD=...
```

El puerto, intervalo, retencion maxima y ventana de relectura se configuran en `conn/backend.env`. `inventory` se reemplaza completamente y `inventory_entries` se actualiza de forma incremental, conservando solo los ultimos dos meses calendario.

Variables operativas:

```env
CLINIC_EXTERNAL_DATABASE_PORT=1433
CLINIC_EXTERNAL_DATABASE_TIMEOUT_SECONDS=60
CLINIC_EXTERNAL_SYNC_ENABLED=true
CLINIC_EXTERNAL_SYNC_INTERVAL_MINUTES=60
CLINIC_EXTERNAL_SYNC_LOOKBACK_DAYS=1
CLINIC_INVENTORY_ENTRIES_RETENTION_MONTHS=2
```

Flujo de `inventory_entries`:

1. Calcula el corte restando meses calendario a la fecha actual.
2. Elimina en PostgreSQL cualquier fila anterior al corte, aunque SQL Server no este disponible.
3. Si la tabla esta vacia, consulta SQL Server desde el corte.
4. Si ya contiene datos, consulta desde la ultima fecha menos la ventana de relectura, siempre limitada por el corte.
5. Reemplaza transaccionalmente solo esa ventana reciente.

`CLINIC_INVENTORY_ENTRIES_RETENTION_MONTHS` admite `1` o `2`; nunca permite conservar mas de dos meses.

Flujo de `inventory`:

1. Ejecuta `scripts/consulta_inventario.sql`.
2. Abre una transaccion PostgreSQL.
3. Vacia `inventory` y carga el resultado completo.
4. Si la escritura falla, la transaccion conserva la version anterior.

Los fallos de SQL Server no detienen FastAPI ni eliminan la ultima carga valida de `inventory`.

Endpoints:

- `GET /api/sincronizacion/inventario`: ultimo estado.
- `POST /api/sincronizacion/inventario`: ejecutar ahora.

## Impresion desde inventario

Tablas auxiliares creadas de forma idempotente al iniciar FastAPI:

- `app_settings`: contiene `inventory_print_limit`.
- `print_batches`: resumen de cada lote.
- `print_batch_items`: resultado por articulo y presentacion.

Reglas:

- Solo se imprime una bodega por lote.
- El limite configurado nunca puede superar 400 etiquetas.
- El producto seleccionado debe pertenecer a la misma referencia de `inventory`.
- La cantidad enviada puede reemplazar el calculo automatico del frontend.
- Los trabajos ZPL agrupan hasta tres etiquetas y pueden mezclar productos.
- Un fallo de una fila ZPL no detiene las filas restantes.
- El estado del lote puede ser `success`, `partial` o `error`.

Endpoints:

- `GET /api/inventario/bodegas`
- `GET /api/inventario?warehouse=1018&availability=all&page=1&page_size=100`
- `POST /api/inventario/seleccion`
- `GET /api/configuracion/impresion-inventario`
- `PUT /api/configuracion/impresion-inventario`
- `POST /api/imprimir-inventario`
- `GET /api/historial/lotes`

`POST /api/inventario/seleccion` reconcilia referencias despues de una recarga completa, porque los IDs de `inventory` pueden cambiar. La impresion final vuelve a validar IDs, referencias, bodega, presentacion, formato y limite.

Estados devueltos:

- `idle`: aun no se ha ejecutado.
- `running`: sincronizacion en curso.
- `success`: ambas tablas se actualizaron.
- `error`: fallo de conexion, consulta o escritura.
- `not_configured`: faltan datos de SQL Server; la depuracion PostgreSQL si se intenta.

Fechas devueltas:

- `entries_since`: inicio efectivo de la ventana incremental consultada.
- `retention_cutoff`: primera fecha que puede permanecer en `inventory_entries`.

Contrato de las consultas:

- `consulta_inventario.sql` debe devolver `bodega`, `referencia` e `inventario`.
- `consulta_entradas.sql` recibe `since_date` y debe devolver `referencia`, `entradas_inv`, `documento`, `fecha` y `bodega`.
- La consulta de entradas incluye adicionalmente `DATEADD(MONTH, -2, GETDATE())` para impedir lecturas externas fuera del horizonte maximo.

Impresora USB Windows:

```env
CLINIC_PRINTER_NAME=ZDesigner ZD230-203dpi ZPL
CLINIC_PRINTER_CONNECTION=windows_spooler
```

Datos mock de respaldo:

```env
CLINIC_DATA_SOURCE=mock
```

## Endpoints

- `GET /api/health`
- `GET /api/productos?search=`
- `GET /api/formatos`
- `GET /api/formatos/{code}/preview`
- `POST /api/imprimir`
- `POST /api/impresora/test`
- `POST /api/impresora/test/etiqueta`
- `GET /api/historial`

## Plantillas ZPL

Las plantillas viven en `app/backend/label_templates`.

- `etiquetas3.zpl`
- `etiquetas3_bold.zpl`
