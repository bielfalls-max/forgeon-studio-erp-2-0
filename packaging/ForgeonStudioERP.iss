; Compilar a partir da raiz usando ISCC packaging\ForgeonStudioERP.iss
; Instalador local por usuário. Não inclui banco e não toca instalações anteriores.
#define AppVersion "2.0.5"
#define ProjectRoot ".."

[Setup]
AppId={{E679C95C-12A2-4E06-AE2A-023D634B8AF2}
AppName=FORGEON STUDIO ERP 2.0
AppVersion={#AppVersion}
AppPublisher=Forgeon Studio
AppPublisherURL=https://github.com/bielfalls-max/forgeon-studio-erp-2-0
DefaultDirName={localappdata}\Programs\ForgeonStudioERP2
DefaultGroupName=FORGEON STUDIO ERP 2.0
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
MinVersion=10.0.10240
OutputDir={#ProjectRoot}\dist\installer
OutputBaseFilename=ForgeonStudioERP-{#AppVersion}-Windows-x64-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\ForgeonStudioERP.exe
SetupLogging=yes
CloseApplications=yes
RestartApplications=no
VersionInfoVersion=2.0.5.0
SetupIconFile={#ProjectRoot}\forgeon\assets\forgeon.ico

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; GroupDescription: "Atalhos:"; Flags: unchecked

[Files]
Source: "{#ProjectRoot}\dist\ForgeonStudioERP\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#ProjectRoot}\modelos\*.xlsx"; DestDir: "{app}\modelos"; Flags: ignoreversion
Source: "{#ProjectRoot}\docs\*.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "{#ProjectRoot}\requirements*.txt"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "{#ProjectRoot}\README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\FORGEON STUDIO ERP 2.0"; Filename: "{app}\ForgeonStudioERP.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\FORGEON STUDIO ERP 2.0"; Filename: "{app}\ForgeonStudioERP.exe"; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{group}\Desinstalar FORGEON STUDIO ERP 2.0"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\ForgeonStudioERP.exe"; Description: "Abrir FORGEON STUDIO ERP 2.0"; Flags: nowait postinstall skipifsilent

; Sem UninstallDelete: banco/backups em LOCALAPPDATA\ForgeonStudioERP2 são preservados.
