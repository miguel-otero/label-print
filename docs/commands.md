Scripts de ejecucion:

powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1

powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1 -Mode Docker

powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1 -InstallDeps


----------------------------

Reconstruye los contenedores:
powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1 -Mode Docker -Build

--------------------------------

Instala el agente desde PowerShell como administrador en el equipo conectado a la Zebra:

powershell.exe -NoProfile -ExecutionPolicy Bypass `
    -File .\scripts\install-print-agent.ps1 `
    -ServerUrl "http://localhost:8080/api" `
    -Token "" `
    -PrinterName "ZDesigner ZD230-203dpi ZPL"

  Luego verifica:

  Get-Service ClinicLabelPrintAgent

  Y consulta el log:

  Get-Content "$env:ProgramData\ClinicLabelPrint\logs\agent.log" -Tail 100


Para desinstalarlo:

  powershell.exe -NoProfile -ExecutionPolicy Bypass `
    -File .\scripts\uninstall-print-agent.ps1
---------------------------------

