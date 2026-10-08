# Comandos del proyecto

## Etiquetas personalizadas

```powershell
docker compose --env-file .\conn\.env up -d --build --no-deps clinic_backend
```

Reconstruye el backend con soporte PNG/JPG, migra el historial y monta
`storage/label-images/` para conservar las imágenes cargadas desde la aplicación.

```powershell
docker compose --env-file .\conn\.env run --rm --no-deps -e CUSTOM_LABEL_DATABASE_TESTS=1 clinic_backend sh -c "pip install -r requirements-test.txt && python -m unittest discover -s tests -v"
```

Ejecuta las pruebas de conversión y cola en un esquema de prueba aislado, sin
enviar trabajos al agente Windows ni a la impresora.

Ejecutar desde `G:\projects\label-print` en PowerShell. Los comandos que administran el agente deben abrirse **como administrador**. Para habilitar scripts únicamente en la terminal actual:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

## Aplicación Docker

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\powershell\start.ps1
```

Levanta frontend, backend y PostgreSQL en segundo plano usando `conn/.env`.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\powershell\start.ps1 -Build
```

Reconstruye las imágenes y levanta todos los contenedores.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\powershell\start.ps1 -Logs
```

Levanta la aplicación y mantiene visibles los logs de Compose.

```powershell
docker compose --env-file .\conn\.env ps
docker compose --env-file .\conn\.env logs -f
docker compose --env-file .\conn\.env down
```

Muestra el estado, sigue los logs o detiene los contenedores sin eliminar el volumen PostgreSQL.

```powershell
docker compose --env-file .\conn\.env up -d --force-recreate clinic_backend
```

Recrea solamente el backend para cargar cambios en `conn/.env`.

## Agente de impresión Windows

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\powershell\build-print-agent-installer.ps1
```

Compila el agente autocontenido y genera el instalador en
`artifacts\windows-agent`. Requiere Python 3.12 e Inno Setup unicamente en el
equipo de desarrollo.

```powershell
.\artifacts\windows-agent\ClinicLabelPrintAgent-Setup-0.2.0-x64.exe `
  /VERYSILENT /SUPPRESSMSGBOXES /NORESTART `
  /CONFIG="C:\ruta-segura\agent.env"
```

Instala o actualiza el agente para todos los usuarios sin utilizar el
repositorio. Al omitir los modificadores abre el asistente grafico.

El script heredado sigue disponible para diagnostico:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\powershell\install-print-agent.ps1 `
  -ServerUrl "http://localhost:8080/api" `
  -Token "TOKEN_DE_CONN_ENV" `
  -PrinterName "ZDesigner ZD230-203dpi ZPL"
```

Instala o actualiza el agente como servicio automático `ClinicLabelPrintAgent`. El token debe coincidir con `CLINIC_PRINT_AGENT_TOKEN` de `conn/.env`.

```powershell
Get-Service ClinicLabelPrintAgent
Restart-Service ClinicLabelPrintAgent
```

Consulta o reinicia el servicio instalado.

```powershell
Get-Content "$env:ProgramData\ClinicLabelPrint\logs\ClinicLabelPrintAgent.wrapper.log" -Tail 100 -Wait
Get-Content "$env:ProgramData\ClinicLabelPrint\logs\ClinicLabelPrintAgent.err.log" -Tail 100 -Wait
```

Sigue los logs del wrapper y los errores del proceso del agente.

```powershell
Stop-Service ClinicLabelPrintAgent
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\powershell\run-print-agent.ps1
```

Detiene temporalmente el servicio y ejecuta el agente en primer plano para diagnóstico.
Detecta el ejecutable nuevo y el entorno heredado. Tambien puede usar
`run-print-agent.ps1 -StopService` como administrador; sin ese modificador rechaza
el arranque si el servicio esta activo. Al terminar: `Start-Service ClinicLabelPrintAgent`.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\powershell\uninstall-print-agent.ps1
```

En instalaciones `.exe`, ejecuta el desinstalador y retira el programa y el
servicio. En instalaciones heredadas elimina solo el servicio. Conserva
configuracion y logs en `C:\ProgramData\ClinicLabelPrint`.

## Preparacion Ubuntu y distribucion ZIP

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\powershell\startup.ps1 -Tools docker
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\powershell\update_zip.ps1 -NoUpload
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\powershell\update_zip.ps1
```

El primero prepara **Ubuntu/Debian en WSL**, no Windows/Docker Desktop. Los
siguientes generan `artifacts/deploy/deploy.zip`; con `-NoUpload` solo empaquetan,
sin el modificador suben a GCS mediante `gsutil` autenticado. `conn/` se incluye
deliberadamente, junto con logos y archivos de empaquetado del agente.

## Equivalentes Bash en Ubuntu/Debian

```bash
bash scripts/linux/startup.sh -t docker -t zip -t jq
bash scripts/linux/start.sh --build
bash scripts/linux/start.sh --logs
bash scripts/linux/update_zip.sh --no-upload
bash scripts/linux/update_zip.sh
```

Preparan herramientas (solicitan `sudo`), levantan Docker, siguen logs, generan el
ZIP o lo suben. Para subirlo, instale tambien Google Cloud CLI con
`bash scripts/linux/startup.sh -t gcloud` y autentiquese con la cuenta autorizada.
En PowerShell 7 sobre Ubuntu los equivalentes generales pueden ejecutarse con
`pwsh -NoProfile -File ./scripts/powershell/start.ps1 -Build` o
`pwsh -NoProfile -File ./scripts/powershell/update_zip.ps1 -NoUpload`.

Las tareas del agente Windows requieren **WSL con interoperabilidad Windows**,
no Ubuntu nativo. Las contrapartes aceptan los mismos parametros PowerShell:

```bash
bash scripts/linux/build-print-agent-installer.sh -Version 0.2.0
bash scripts/linux/install-print-agent.sh -ServerUrl 'http://localhost:8080/api' -Token 'TOKEN' -PrinterName 'ZDesigner ZD230-203dpi ZPL'
bash scripts/linux/run-print-agent.sh -StopService
bash scripts/linux/uninstall-print-agent.sh
```

Abra la terminal como administrador para instalar, desinstalar o detener el
servicio. Compilar requiere Python 3.12 e Inno Setup **en Windows**. El agente
no se instala en la VM Ubuntu; ahi solo se ejecutan los contenedores.

## Estado y conectividad

```powershell
Invoke-RestMethod http://localhost:8080/api/health
Invoke-RestMethod http://localhost:8080/api/impresora/status
Invoke-WebRequest http://localhost:8083 -UseBasicParsing
```

Comprueba la salud del backend, el heartbeat del agente y la disponibilidad del frontend.

```powershell
Get-Printer -Name "ZDesigner ZD230-203dpi ZPL"
Test-NetConnection localhost -Port 8080
```

Verifica que exista la cola Zebra y que el puerto del backend sea accesible.

## Frontend

Ejecutar desde `app\frontend` cuando Node.js esté instalado localmente:

```powershell
npm install
npm run dev
npm run build
npm run lint
npm run format
```

Instala dependencias, inicia Vite, genera el build, ejecuta ESLint o aplica Prettier, respectivamente.

Si Node.js solo está disponible en Docker:

```powershell
docker exec clinic_frontend npm run build
docker exec clinic_frontend npm run lint
```

## Validaciones

```powershell
docker compose --env-file .\conn\.env config --quiet
python -m compileall app\backend\app app\windows_agent\agent
git diff --check
```

Valida Compose, la sintaxis Python y problemas de espacios o marcadores en el diff.

## Git

```powershell
git status
git diff
git add .
git commit -m "Se ajusta descripcion del cambio"
git push -u origin dev
```

Revisa cambios, prepara archivos, crea un commit y publica la rama `dev`.

```powershell
git switch main
git pull origin main
git merge dev
git push origin main
```

Integra los cambios de `dev` en `main` después de validar y resolver cualquier conflicto.
