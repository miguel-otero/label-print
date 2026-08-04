# clinic-label-print

Sistema interno para buscar productos e imprimir etiquetas en una impresora Zebra ZD230 usando ZPL.

La ruta actual del proyecto usa tres contenedores para desarrollo general:

- Frontend: React + TanStack Router/Start + Vite.
- Backend: FastAPI.
- Base de datos: PostgreSQL.

El arranque se hace desde un solo script: `scripts/start.ps1`.

- Modo USB, por defecto: frontend y PostgreSQL en Docker, backend local en Windows para acceder a la cola USB.
- Modo Docker: frontend, backend y PostgreSQL en Docker, con impresion simulada.

## Arquitectura objetivo

Servicios Docker:

- `clinic_frontend`: `http://localhost:8083`
- `clinic_backend`: `http://localhost:8080/api`
- `clinic_db`: PostgreSQL `localhost:5432`

Flujo principal:

1. El operador abre el frontend.
2. El frontend consume la API FastAPI.
3. El backend consulta productos, formatos e historial en PostgreSQL.
4. El backend genera ZPL desde plantillas o desde formatos simples.
5. En Docker, la impresion queda simulada por defecto.
6. En Windows local con `start.ps1 -Mode Usb`, el backend puede enviar RAW/ZPL a la cola Windows.

## Impresion desde inventario

La opcion lateral `Imprimir de inventario` abre `/inventory-print`.

Flujo:

1. Selecciona una bodega; `1018` es la predeterminada cuando existe.
2. Filtra por referencia, descripcion, codigo de barras o disponibilidad.
3. Selecciona uno o mas articulos imprimibles.
4. Elige un unico formato para todo el lote.
5. En el modal previo, resuelve las referencias con varias presentaciones y ajusta cantidades.
6. Confirma el lote. Al terminar, la seleccion se limpia.

La cantidad automatica se calcula por presentacion:

```txt
floor(ceil(inventario) / cantidad_por_um)
```

Ejemplo: 7 unidades con una presentacion `PAQ x 5` producen 1 etiqueta. Si el resultado es 0, el articulo puede seleccionarse y ajustarse manualmente a 1. Los ajustes manuales pueden superar el calculo automatico, pero la suma del lote no puede superar el limite persistido en PostgreSQL.

El limite se configura desde `Configuraciones > Impresion desde inventario`, admite valores entre 1 y 400 y el backend vuelve a validarlo al recibir el lote.

El boton `Actualizar inventario` dispara la sincronizacion externa y vuelve a consultar PostgreSQL sin recargar la pagina. Si SQL Server no esta configurado, conserva y recarga los datos locales. Las cantidades automaticas se recalculan; los ajustes manuales se conservan.

Las plantillas de tres posiciones pueden mezclar productos distintos en una misma fila. Si una fila falla, el backend continua con las siguientes y devuelve el detalle legible por articulo.

El historial guarda un registro principal por lote y detalles por articulo. La pantalla `Historial de impresion` separa lotes de inventario e impresiones individuales.

## Arranque recomendado

Desde la raiz del repositorio:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1
```

Ese comando usa `-Mode Usb` por defecto:

- Detiene `clinic_backend` en Docker.
- Levanta `clinic_db` y `clinic_frontend` en Docker.
- Usa PostgreSQL en `localhost:5432`.
- Corre FastAPI local en Windows con `--reload`.
- Permite acceder a la cola Windows de la Zebra USB.

Si faltan dependencias del backend:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1 -InstallDeps
```

Con rebuild del frontend:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1 -Build
```

## Arranque completo en Docker

Para levantar los 3 servicios en contenedores:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1 -Mode Docker
```

Con rebuild:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1 -Mode Docker -Build
```

Ver logs:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1 -Mode Docker -Logs
```

El modo Docker usa `CLINIC_PRINTER_CONNECTION=simulated`.

El servicio `clinic_db` inicializa tablas y datos base desde:

```txt
scripts/postgres_schema.sql
scripts/postgres_seed.sql
```

El seed incluye datos locales de respaldo obtenidos de:

```txt
dev/data/inv-30-06-2026.csv
dev/data/movimientos_entradas.csv
```

`inventory` carga las 1.689 filas del snapshot del 30 de junio de 2026. `inventory_entries` carga 1.107 movimientos y aplica en PostgreSQL el mismo horizonte dinamico de dos meses, por lo que una inicializacion futura omitira automaticamente movimientos vencidos.

Los archivos de `/docker-entrypoint-initdb.d/` solo se ejecutan automaticamente al crear un volumen PostgreSQL vacio. Un volumen existente no vuelve a ejecutar el seed al reiniciar el contenedor.

## Configuracion

Frontend:

```env
VITE_API_URL=http://localhost:8080/api
```

Backend:

```env
CLINIC_API_PREFIX=/api
CLINIC_DATA_SOURCE=postgres
CLINIC_DATABASE_HOST=localhost
CLINIC_DATABASE_PORT=5432
CLINIC_PRODUCTS_TABLE=products
CLINIC_FORMATS_TABLE=label_formats
CLINIC_HISTORY_TABLE=print_history
CLINIC_PRINTER_NAME=ZDesigner ZD230-203dpi ZPL
CLINIC_PRINTER_CONNECTION=windows_spooler
```

La configuracion local y las credenciales se guardan en `conn/.env`, que esta excluido de Git. Usa `conn/.env.example` como referencia:

```env
CLINIC_DATA_SOURCE=postgres
CLINIC_DATABASE_HOST=localhost
CLINIC_DATABASE_PORT=5432
CLINIC_DATABASE_NAME=...
CLINIC_DATABASE_USER=...
CLINIC_DATABASE_PASSWORD=...

CLINIC_EXTERNAL_DATABASE_HOST=...
CLINIC_EXTERNAL_DATABASE_NAME=...
CLINIC_EXTERNAL_DATABASE_USER=...
CLINIC_EXTERNAL_DATABASE_PASSWORD=...
```

Para ejecutar Compose directamente, indica el archivo porque no se encuentra en la raiz:

```powershell
docker compose --env-file .\conn\.env up -d
```

En Docker Compose, el backend reemplaza internamente el host local por `clinic_db` y `CLINIC_PRINTER_CONNECTION` por `simulated`, porque un contenedor Linux no puede acceder a la cola USB de Windows.

## Sincronizacion de inventario

El backend consulta Microsoft SQL Server usando:

- `scripts/consulta_inventario.sql`: reemplazo transaccional completo de `inventory`.
- `scripts/consulta_entradas.sql`: sincronizacion incremental de `inventory_entries`.

`inventory_entries` conserva como maximo los dos meses calendario definidos por `CLINIC_INVENTORY_ENTRIES_RETENTION_MONTHS`. Se permite reducir el valor a un mes, pero la configuracion rechaza valores superiores a dos. Cada ejecucion elimina registros anteriores al corte, incluso si SQL Server no esta disponible, y la consulta externa nunca solicita fechas mas antiguas.

En la primera carga se consulta desde el corte de retencion. En las siguientes, se parte de la fecha mas reciente guardada menos `CLINIC_EXTERNAL_SYNC_LOOKBACK_DAYS`, sin sobrepasar el corte. Esa ventana se reemplaza transaccionalmente para reflejar movimientos nuevos, corregidos o anulados sin truncar toda la tabla.

La sincronizacion se ejecuta al iniciar el backend y luego cada `CLINIC_EXTERNAL_SYNC_INTERVAL_MINUTES`. Si las credenciales externas no estan configuradas, la API sigue funcionando con los datos existentes.

Ejecucion y estado manual:

```txt
POST /api/sincronizacion/inventario
GET  /api/sincronizacion/inventario
```

## Endpoints principales

Base URL:

```txt
http://localhost:8080/api
```

Endpoints:

- `GET /health`
- `GET|POST /sincronizacion/inventario`
- `GET /inventario/bodegas`
- `GET /inventario`
- `POST /inventario/seleccion`
- `GET|PUT /configuracion/impresion-inventario`
- `POST /imprimir-inventario`
- `GET /historial/lotes`
- `GET /productos?search=`
- `GET /formatos`
- `GET /formatos/{code}/preview`
- `POST /imprimir`
- `POST /impresora/test`
- `POST /impresora/test/etiqueta`
- `GET /historial`

## Base de datos

Tablas actuales:

- `products`
- `label_formats`
- `print_history`

Formatos iniciales:

- `50x25`
- `60x40`
- `100x50`
- `etiquetas3`
- `etiquetas3_bold`

El volumen persistente de PostgreSQL se llama `clinic_db_data`.

## Plantillas ZPL

Las plantillas viven en:

```txt
app/backend/label_templates
```

Plantillas actuales:

- `etiquetas3.zpl`
- `etiquetas3_bold.zpl`

Para formatos de 3 columnas:

- 1 a 3 etiquetas generan un trabajo.
- 4 o mas etiquetas generan varios trabajos por grupos de 3.
- Las posiciones sobrantes se imprimen vacias.

## Vista previa ZPL

El frontend consulta:

```txt
GET /api/formatos/{code}/preview
```

El backend parsea la plantilla ZPL y expone:

- Tamano del lienzo (`^PW`, `^LL`).
- Textos variables (`^FT`, `^A0N`, `^FB`, `^FD`).
- Codigos de barras (`^BY`, `^BC`, `^FD`).
- Graficos estaticos (`^GFA`).

La vista previa renderiza esos elementos en SVG para mantener proporciones cercanas al resultado impreso.

## Verificaciones utiles

Compilar backend:

```powershell
python -m compileall app\backend\app
```

Validar configuracion Docker:

```powershell
docker compose --env-file .\conn\.env config
```

Build frontend:

```powershell
docker compose --env-file .\conn\.env run --rm --no-deps clinic_frontend npm run build
```

## Estructura relevante

```txt
app/
  backend/
    app/
      main.py
      printer.py
      repository.py
      schemas.py
      settings.py
      zpl_preview.py
    label_templates/
  frontend/
    src/
      components/
      lib/
      routes/
conn/
docker/
scripts/
```
