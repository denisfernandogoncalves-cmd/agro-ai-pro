[Setup]
AppId={{BF427D76-432A-4AC9-8DA3-336125986F0E}
AppName=AGRO-AI-PRO Testes
AppVersion=0.1.0
DefaultDirName={autopf}\AGRO-AI-PRO-Testes
DefaultGroupName=AGRO-AI-PRO Testes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\..\dist-windows
OutputBaseFilename=AGRO-AI-PRO-Testes-Setup
Compression=lzma2/fast
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
CloseApplications=yes
SetupLogging=yes
UninstallDisplayIcon={app}\AGRO-AI-PRO.exe

[Languages]
Name: "portuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Files]
Source: "..\..\dist-windows\AGRO-AI-PRO-Standalone\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\.packaging\postgres\pgsql\doc\src\sgml\html\legalnotice.html"; DestDir: "{app}\licenses"; DestName: "PostgreSQL.html"; Flags: ignoreversion
Source: "..\..\.worktrees\runtime-origin-main\frontend\node_modules\react\LICENSE"; DestDir: "{app}\licenses"; DestName: "React.txt"; Flags: ignoreversion
Source: "..\..\.worktrees\runtime-origin-main\frontend\node_modules\react-dom\LICENSE"; DestDir: "{app}\licenses"; DestName: "React-DOM.txt"; Flags: ignoreversion
Source: "..\..\.packaging\downloads\webview2-offline.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall
Source: "..\..\.packaging\downloads\vc_redist.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Icons]
Name: "{autodesktop}\AGRO-AI-PRO Testes"; Filename: "{app}\AGRO-AI-PRO.exe"
Name: "{group}\AGRO-AI-PRO Testes"; Filename: "{app}\AGRO-AI-PRO.exe"

[Run]
Filename: "{tmp}\vc_redist.exe"; Parameters: "/install /quiet /norestart"; StatusMsg: "Configurando componentes do Windows..."; Flags: waituntilterminated
Filename: "{tmp}\webview2-offline.exe"; Parameters: "/silent /install"; StatusMsg: "Configurando a janela do AGRO..."; Flags: waituntilterminated
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall add rule name=""AGRO-AI-PRO Testes"" dir=in action=allow program=""{app}\runtime\python.exe"" protocol=TCP localport=18765 remoteip=localsubnet profile=private"; StatusMsg: "Configurando acesso pela rede local privada..."; Flags: runhidden waituntilterminated
Filename: "{app}\AGRO-AI-PRO.exe"; Description: "Abrir AGRO-AI-PRO Testes"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""AGRO-AI-PRO Testes"" program=""{app}\runtime\python.exe"""; Flags: runhidden
