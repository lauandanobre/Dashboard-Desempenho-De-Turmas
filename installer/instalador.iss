; Instalador do Metricas das Turmas (Inno Setup 6, gratuito: https://jrsoftware.org/isinfo.php)
; Antes de compilar, gere o executavel:  pyinstaller --noconfirm MetricasTurmas.spec
; Compilar:  ISCC.exe installer\instalador.iss      (ou abrir no Inno Setup e apertar F9)
; Resultado: dist_instalador\Instalador_Metricas_das_Turmas.exe

#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif

[Setup]
AppId={{6F3B8C52-2D0A-4E55-9A41-7C1D5E9B0A11}
AppName=Metricas das Turmas
AppVersion={#AppVersion}
AppPublisher=Cursinho UFABC
DefaultDirName={autopf}\Metricas das Turmas
DefaultGroupName=Metricas das Turmas
OutputDir=..\dist_instalador
OutputBaseFilename=Instalador_Metricas_das_Turmas
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\MetricasDasTurmas.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; Instala so para o usuario atual: nao pede senha de administrador.
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na area de trabalho"; GroupDescription: "Atalhos:"

[Files]
Source: "..\dist\MetricasDasTurmas\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
; Modelo de planilha e exemplo ficticio em Documentos (facil de achar; nao sao apagados ao desinstalar)
Source: "..\assets\modelo_planilha_turmas.xlsx"; DestDir: "{userdocs}\Metricas das Turmas"; Flags: ignoreversion uninsneveruninstall
Source: "..\assets\exemplo_ficticio.xlsx"; DestDir: "{userdocs}\Metricas das Turmas"; Flags: ignoreversion uninsneveruninstall

[Icons]
Name: "{group}\Metricas das Turmas"; Filename: "{app}\MetricasDasTurmas.exe"
Name: "{autodesktop}\Metricas das Turmas"; Filename: "{app}\MetricasDasTurmas.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\MetricasDasTurmas.exe"; Description: "Abrir o Metricas das Turmas agora"; Flags: nowait postinstall skipifsilent
