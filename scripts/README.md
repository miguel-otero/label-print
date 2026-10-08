# Scripts por plataforma

Ejecute desde la raiz del repositorio. Todos resuelven sus rutas a partir del
propio script. Los SQL permanecen en `scripts/`: Docker y el backend los consumen
directamente. No los vuelva a ejecutar como migraciones: el esquema recrea
`products` y el seed reemplaza inventario y entradas.

| Tarea | PowerShell (`scripts/powershell/`) | Bash (`scripts/linux/`) |
| --- | --- | --- |
| Iniciar Docker | `start.ps1 [-Build] [-Logs]` | `start.sh [--build] [--logs]` |
| Preparar Ubuntu/Debian | `startup.ps1 -Tools docker` | `startup.sh -t docker` |
| Empaquetar y subir a GCS | `update_zip.ps1 [-NoUpload] [-Bucket gs://…]` | `update_zip.sh [--no-upload] [--bucket gs://…]` |
| Instalar agente heredado | `install-print-agent.ps1` | `install-print-agent.sh` (WSL) |
| Diagnostico agente | `run-print-agent.ps1 [-StopService]` | `run-print-agent.sh [-StopService]` (WSL) |
| Desinstalar agente | `uninstall-print-agent.ps1` | `uninstall-print-agent.sh` (WSL) |
| Compilar instalador | `build-print-agent-installer.ps1` | `build-print-agent-installer.sh` (WSL) |

En Windows use `powershell.exe -NoProfile -ExecutionPolicy Bypass -File RUTA`.
`start.ps1` y `update_zip.ps1` tambien funcionan con PowerShell 7 (`pwsh`) en Linux.
`startup.ps1` llama al preparador Bash nativamente en Linux o mediante WSL en
Windows; **no instala Docker Desktop**. Herramientas admitidas: `docker`, `jq`,
`unzip`, `zip`, `gcloud`. Se solicitan permisos `sudo` cuando hacen falta.

## Limite de plataforma del agente

El agente utiliza APIs nativas del spooler Windows. Las cuatro contrapartes Bash
invocan PowerShell de Windows desde WSL y aceptan sus mismos parametros; no crean
un servicio Linux. Se requiere interoperabilidad Windows y, para instalar,
desinstalar o detener servicios, abrir la terminal Windows/WSL como administrador.
Las rutas de `-InnoCompilerPath` se convierten con `wslpath` cuando son rutas WSL.
En Ubuntu nativo estas tareas fallan con una explicacion; compile el instalador
en Windows o con `.github/workflows/windows-agent.yml`.

`windows-agent-common.ps1` y `windows-agent-common.sh` son bibliotecas internas,
no comandos independientes. El instalador `.exe` sigue siendo la distribucion
recomendada; el script de instalacion Python se mantiene solo para compatibilidad.

## ZIP de distribucion

Ambas versiones usan `scripts/deploy-files.txt`. Incluyen `conn/` deliberadamente,
`docker-compose.yml`, `storage/` (logos), `packaging/`, codigo, SQL y documentacion.
Excluyen dependencias, caches, entornos Python, builds y logs. No siguen enlaces
simbolicos/junctions. Conservan el resultado en `artifacts/deploy/deploy.zip`;
una nueva ejecucion lo reemplaza para no retener archivos eliminados del proyecto.
Sin `-NoUpload`/`--no-upload` requieren `gsutil` autenticado y suben al destino
predeterminado `gs://label-print-cv/deploy.zip`. No reinician servidores ni
respaldan PostgreSQL. Trate el ZIP como confidencial por contener `conn/`.

## Validacion sin efectos operativos

```text
python -m unittest discover -s scripts/tests -v
```

Las pruebas usan proyectos temporales y comandos simulados. No instalan paquetes,
no administran el servicio real, no suben archivos ni imprimen etiquetas.
