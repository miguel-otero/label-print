#ifndef AppVersion
  #define AppVersion "0.0.0-dev"
#endif
#ifndef PayloadDir
  #error PayloadDir must be defined
#endif
#ifndef OutputDir
  #define OutputDir "."
#endif

#define AppName "Clinic Label Print Agent"

[Setup]
AppId={{C5B71EA9-B977-4BD8-B458-A7A73333AE42}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Clinic Label Print
DefaultDirName={autopf}\ClinicLabelPrintAgent
DisableProgramGroupPage=yes
OutputDir={#OutputDir}
OutputBaseFilename=ClinicLabelPrintAgent-Setup-{#AppVersion}-x64
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
UninstallDisplayName={#AppName}
WizardStyle=modern
CloseApplications=no
RestartApplications=no
SetupLogging=yes

[Files]
Source: "{#PayloadDir}\agent\*"; DestDir: "{app}\agent"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#PayloadDir}\ClinicLabelPrintAgent.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#PayloadDir}\ClinicLabelPrintAgent.xml"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
Name: "{commonappdata}\ClinicLabelPrint"
Name: "{commonappdata}\ClinicLabelPrint\logs"; Permissions: system-full admins-full

[UninstallRun]
Filename: "{app}\ClinicLabelPrintAgent.exe"; Parameters: "stop"; Flags: runhidden waituntilterminated skipifdoesntexist; RunOnceId: "StopAgentService"
Filename: "{app}\ClinicLabelPrintAgent.exe"; Parameters: "uninstall"; Flags: runhidden waituntilterminated skipifdoesntexist; RunOnceId: "RemoveAgentService"

[Code]
var
  ConfigPage: TInputFileWizardPage;
  SelectedConfigPath: string;
  LegacyWrapperPath: string;

function InstalledConfigPath(): string;
begin
  Result := ExpandConstant('{commonappdata}\ClinicLabelPrint\agent.env');
end;

function FindConfigPath(): string;
begin
  Result := ExpandConstant('{param:CONFIG|}');
  if (Result = '') and Assigned(ConfigPage) then
    Result := ConfigPage.Values[0];
  if (Result = '') and FileExists(ExpandConstant('{src}\agent.env')) then
    Result := ExpandConstant('{src}\agent.env');
end;

function HasConfigKey(Lines: TStrings; const Key: string): Boolean;
var
  I, Separator: Integer;
  Line, Name, Value: string;
begin
  Result := False;
  for I := 0 to Lines.Count - 1 do
  begin
    Line := Trim(Lines[I]);
    if (Line = '') or (Line[1] = '#') then
      Continue;
    Separator := Pos('=', Line);
    if Separator = 0 then
      Continue;
    Name := Trim(Copy(Line, 1, Separator - 1));
    Value := Trim(Copy(Line, Separator + 1, MaxInt));
    if (CompareText(Name, Key) = 0) and (Value <> '') then
    begin
      Result := True;
      Exit;
    end;
  end;
end;

function ConfigValue(Lines: TStrings; const Key: string): string;
var
  I, Separator: Integer;
  Line, Name: string;
begin
  Result := '';
  for I := 0 to Lines.Count - 1 do
  begin
    Line := Trim(Lines[I]);
    Separator := Pos('=', Line);
    if Separator = 0 then
      Continue;
    Name := Trim(Copy(Line, 1, Separator - 1));
    if CompareText(Name, Key) = 0 then
    begin
      Result := Trim(Copy(Line, Separator + 1, MaxInt));
      Exit;
    end;
  end;
end;

function ValidateConfigFile(const Path: string; ShowMessage: Boolean): Boolean;
var
  Lines: TStringList;
  ServerUrl: string;
begin
  Result := False;
  if not FileExists(Path) then
  begin
    if ShowMessage then
      MsgBox('No se encontro el archivo de configuracion: ' + Path, mbError, MB_OK);
    Exit;
  end;

  Lines := TStringList.Create;
  try
    Lines.LoadFromFile(Path);
    if not HasConfigKey(Lines, 'CLINIC_AGENT_SERVER_URL') or
       not HasConfigKey(Lines, 'CLINIC_PRINT_AGENT_TOKEN') or
       not HasConfigKey(Lines, 'CLINIC_PRINTER_NAME') then
    begin
      if ShowMessage then
        MsgBox('agent.env debe contener URL, token e impresora.', mbError, MB_OK);
      Exit;
    end;
    ServerUrl := Lowercase(ConfigValue(Lines, 'CLINIC_AGENT_SERVER_URL'));
    if (Pos('http://', ServerUrl) <> 1) and (Pos('https://', ServerUrl) <> 1) then
    begin
      if ShowMessage then
        MsgBox('CLINIC_AGENT_SERVER_URL debe comenzar por http:// o https://.', mbError, MB_OK);
      Exit;
    end;
    Result := True;
  finally
    Lines.Free;
  end;
end;

procedure InitializeWizard();
var
  DefaultConfig: string;
begin
  ConfigPage := CreateInputFilePage(
    wpSelectDir,
    'Configuracion del agente',
    'Seleccione el archivo agent.env preparado para este equipo.',
    'En una actualizacion puede dejar el campo vacio para conservar la configuracion instalada.'
  );
  ConfigPage.Add('Archivo agent.env:', 'Archivos de entorno|*.env|Todos los archivos|*.*', '.env');

  DefaultConfig := ExpandConstant('{param:CONFIG|}');
  if (DefaultConfig = '') and FileExists(ExpandConstant('{src}\agent.env')) then
    DefaultConfig := ExpandConstant('{src}\agent.env');
  ConfigPage.Values[0] := DefaultConfig;
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := WizardSilent and Assigned(ConfigPage) and (PageID = ConfigPage.ID);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  ConfigPath: string;
begin
  Result := True;
  if Assigned(ConfigPage) and (CurPageID = ConfigPage.ID) then
  begin
    ConfigPath := FindConfigPath();
    if ConfigPath = '' then
    begin
      if FileExists(InstalledConfigPath()) then
        Exit;
      MsgBox('Debe seleccionar un agent.env para una instalacion nueva.', mbError, MB_OK);
      Result := False;
      Exit;
    end;
    Result := ValidateConfigFile(ConfigPath, True);
  end;
end;

procedure StopAndRemoveService(const WrapperPath: string);
var
  ResultCode: Integer;
begin
  if not FileExists(WrapperPath) then
    Exit;
  Exec(WrapperPath, 'stop', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec(WrapperPath, 'uninstall', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;

function PrepareToInstall(var NeedsRestart: Boolean): string;
var
  CurrentWrapperPath: string;
begin
  Result := '';
  SelectedConfigPath := FindConfigPath();
  if (SelectedConfigPath = '') and not FileExists(InstalledConfigPath()) then
  begin
    Result := 'No existe una configuracion instalada y no se proporciono agent.env.';
    Exit;
  end;
  if (SelectedConfigPath <> '') and
     not ValidateConfigFile(SelectedConfigPath, not WizardSilent) then
  begin
    Result := 'El archivo agent.env no es valido.';
    Exit;
  end;

  CurrentWrapperPath := ExpandConstant('{app}\ClinicLabelPrintAgent.exe');
  LegacyWrapperPath := ExpandConstant('{commonappdata}\ClinicLabelPrint\ClinicLabelPrintAgent.exe');
  StopAndRemoveService(CurrentWrapperPath);
  if CompareText(CurrentWrapperPath, LegacyWrapperPath) <> 0 then
    StopAndRemoveService(LegacyWrapperPath);
end;

procedure InstallAndStartService();
var
  ResultCode: Integer;
  ConfigPath, BackupPath, AgentPath, WrapperPath: string;
begin
  ConfigPath := InstalledConfigPath();
  BackupPath := ConfigPath + '.previous';
  ForceDirectories(ExtractFileDir(ConfigPath));
  ForceDirectories(ExpandConstant('{commonappdata}\ClinicLabelPrint\logs'));

  if SelectedConfigPath <> '' then
  begin
    if FileExists(ConfigPath) then
      CopyFile(ConfigPath, BackupPath, False);
    if CompareText(SelectedConfigPath, ConfigPath) <> 0 then
      if not CopyFile(SelectedConfigPath, ConfigPath, False) then
        RaiseException('No se pudo copiar agent.env a ProgramData.');
  end;

  if not Exec(
    ExpandConstant('{sys}\icacls.exe'),
    '"' + ConfigPath + '" /inheritance:r /grant:r "*S-1-5-18:F" "*S-1-5-32-544:F"',
    '',
    SW_HIDE,
    ewWaitUntilTerminated,
    ResultCode
  ) or (ResultCode <> 0) then
    RaiseException('No se pudieron proteger los permisos de agent.env.');

  AgentPath := ExpandConstant('{app}\agent\ClinicLabelPrintAgent.exe');
  if not Exec(
    AgentPath,
    '--check-config "' + ConfigPath + '"',
    ExpandConstant('{app}\agent'),
    SW_HIDE,
    ewWaitUntilTerminated,
    ResultCode
  ) or (ResultCode <> 0) then
    RaiseException('La configuracion o la impresora indicada no son validas. Revise el log del instalador.');

  WrapperPath := ExpandConstant('{app}\ClinicLabelPrintAgent.exe');
  if not Exec(WrapperPath, 'install', ExpandConstant('{app}'), SW_HIDE, ewWaitUntilTerminated, ResultCode) or
     (ResultCode <> 0) then
    RaiseException('No se pudo registrar el servicio ClinicLabelPrintAgent.');
  if not Exec(WrapperPath, 'start', ExpandConstant('{app}'), SW_HIDE, ewWaitUntilTerminated, ResultCode) or
     (ResultCode <> 0) then
    RaiseException('El servicio fue instalado, pero no se pudo iniciar.');
  Sleep(2000);
  if not Exec(WrapperPath, 'status', ExpandConstant('{app}'), SW_HIDE, ewWaitUntilTerminated, ResultCode) or
     (ResultCode <> 0) then
    RaiseException('El servicio no permanece en ejecucion. Revise los logs en ProgramData.');

  if (LegacyWrapperPath <> '') and FileExists(LegacyWrapperPath) then
    DeleteFile(LegacyWrapperPath);
  DeleteFile(ExpandConstant('{commonappdata}\ClinicLabelPrint\ClinicLabelPrintAgent.xml'));
  DelTree(ExpandConstant('{commonappdata}\ClinicLabelPrint\venv'), True, True, True);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    InstallAndStartService();
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
    MsgBox(
      'La configuracion y los logs se conservaron en ' +
      ExpandConstant('{commonappdata}\ClinicLabelPrint') + '.',
      mbInformation,
      MB_OK
    );
end;
