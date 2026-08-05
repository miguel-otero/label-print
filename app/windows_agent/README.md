# Agente de impresión Windows

El agente reclama trabajos ZPL desde el backend Docker y los envía como RAW a la cola Zebra local. Producción se ejecuta como el servicio `ClinicLabelPrintAgent`; el backend nunca accede directamente al spooler.

## Requisitos

- Windows con Python 3.11 o superior.
- Cola Zebra instalada y visible para una cuenta dedicada.
- La cuenta debe tener el derecho **Log on as a service**.
- Acceso HTTP/HTTPS desde la estación a la API del servidor.
- El mismo `CLINIC_PRINT_AGENT_TOKEN` configurado en servidor y agente.

## Instalación

Desde PowerShell como administrador:

```powershell
.\scripts\install-print-agent.ps1 `
  -ServerUrl "http://servidor:8080/api" `
  -Token "secreto-compartido" `
  -PrinterName "ZDesigner ZD230-203dpi ZPL"
```

El script solicita la cuenta dedicada, instala el entorno en `%ProgramData%\ClinicLabelPrint`, protege `agent.env` e inicia el servicio.

Comandos útiles:

```powershell
Get-Service ClinicLabelPrintAgent
Get-Content "$env:ProgramData\ClinicLabelPrint\logs\agent.log" -Tail 100
.\scripts\run-print-agent.ps1
.\scripts\uninstall-print-agent.ps1
```

Detenga el servicio antes de usar el modo consola para evitar dos consumidores simultáneos.
