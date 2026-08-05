# Backend FastAPI

El backend corre exclusivamente en `clinic_backend`. Gestiona productos, inventario, plantillas ZPL, historial y una cola de impresión persistente en PostgreSQL. No accede al spooler de Windows.

## Ejecución

Desde la raíz:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1 -Mode Docker -Build
```

La API queda en `http://localhost:8080/api` y su salud se consulta en `/api/health`. Compose carga `conn/.env` y fuerza `CLINIC_DATABASE_HOST=clinic_db` dentro del contenedor.

## Cola de impresión

Las solicitudes crean registros `print_jobs` y `print_job_documents`. El agente Windows usa endpoints protegidos con `Authorization: Bearer <CLINIC_PRINT_AGENT_TOKEN>` para:

- registrar su heartbeat;
- reclamar un trabajo pendiente;
- reportar el resultado de cada documento.

Un trabajo que queda procesando sin respuesta pasa a `unknown`; no se reencola automáticamente para evitar etiquetas duplicadas. El operador puede reintentarlo explícitamente desde el historial.

## Validación

```powershell
python -m compileall app\backend\app
docker compose --env-file .\conn\.env config --quiet
```

La estructura inicial vive en `scripts/postgres_schema.sql`. `PrintQueueService.ensure_schema()` aplica de forma idempotente las tablas y restricciones nuevas sobre volúmenes existentes.
