# Agente de impresion Windows

El agente reclama trabajos ZPL desde el backend Docker y los envia como RAW a la
cola Zebra local. En produccion se ejecuta como el servicio
`ClinicLabelPrintAgent`; el backend nunca accede directamente al spooler.

El heartbeat consulta el estado nativo de la cola. Reporta
`printer_ok=false` cuando Windows informa desconexion, falta de papel, atasco,
puerta abierta u otra condicion que requiere intervencion.

## Instalacion recomendada

El equipo destino no necesita el repositorio, Python ni PowerShell. Distribuya
juntos:

```text
ClinicLabelPrintAgent-Setup-0.2.0-x64.exe
agent.env
ClinicLabelPrintAgent-Setup-0.2.0-x64.exe.sha256
```

Prepare `agent.env` a partir de `agent.env.example`. Al abrir el instalador
como administrador, este detecta el archivo ubicado a su lado o permite
seleccionarlo. El programa se instala para todos los usuarios en
`C:\Program Files\ClinicLabelPrintAgent`; la configuracion y los logs quedan
en `C:\ProgramData\ClinicLabelPrint`.

Instalacion automatizada:

```powershell
ClinicLabelPrintAgent-Setup-0.2.0-x64.exe `
  /VERYSILENT /SUPPRESSMSGBOXES /NORESTART `
  /CONFIG="C:\Distribucion\agent.env"
```

Despues de instalar, elimine o proteja la copia de distribucion de
`agent.env`. Las actualizaciones conservan la configuracion existente si no
reciben otro archivo. La desinstalacion conserva configuracion y logs.

## Requisitos operativos

- Windows 10 u 11 x64.
- Cola Zebra local instalada para todo el equipo y visible para `LocalSystem`.
- Acceso HTTP/HTTPS desde la estacion a la API.
- El mismo `CLINIC_PRINT_AGENT_TOKEN` configurado en servidor y agente.

## Compilacion y publicacion

La version se define en `pyproject.toml`. En un equipo de desarrollo con
Python 3.12 e Inno Setup 6:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\build-print-agent-installer.ps1
```

El resultado queda en `artifacts\windows-agent`. Los pull requests que
modifican el agente validan el instalador. Un tag que coincida con la version,
por ejemplo `agent-v0.2.0`, crea una GitHub Release con el instalador y su
SHA-256. Mientras no exista certificado de firma de codigo, Windows mostrara el
editor como desconocido.

## Diagnostico y migracion

Los scripts anteriores se conservan temporalmente para diagnostico y migracion:

```powershell
Get-Service ClinicLabelPrintAgent
Get-Content "$env:ProgramData\ClinicLabelPrint\logs\ClinicLabelPrintAgent.err.log" -Tail 100
.\scripts\run-print-agent.ps1
.\scripts\uninstall-print-agent.ps1
```

Detenga el servicio antes de usar el modo consola para evitar dos consumidores
simultaneos. El instalador detecta la instalacion heredada en `ProgramData`,
conserva `agent.env` y los logs, reemplaza el servicio y elimina el entorno
virtual despues de iniciar correctamente la nueva version.
