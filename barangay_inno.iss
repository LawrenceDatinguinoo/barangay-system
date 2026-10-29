[Setup]
AppName=Barangay System
AppVersion=1.0
DefaultDirName={pf}\BarangaySystem
DefaultGroupName=Barangay System
OutputDir=C:\MyAppInstaller
OutputBaseFilename=BarangaySystemSetup
SetupIconFile=C:\Users\IF\barangay\LOGOS.ico
Compression=lzma
SolidCompression=yes

[Files]
; Your EXE created by PyInstaller:
Source: "C:\Users\IF\barangay\dist\main.exe"; DestDir: "{app}"

; Your ICON
Source: "C:\Users\IF\barangay\LOGOS.ico"; DestDir: "{app}"

; Photo folder if needed
Source: "C:\Users\IF\barangay\photos\*"; DestDir: "{app}\photos"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Barangay System"; Filename: "{app}\main.exe"; IconFilename: "{app}\LOGOS.ico"
Name: "{commondesktop}\Barangay System"; Filename: "{app}\main.exe"; IconFilename: "{app}\LOGOS.ico"

[Run]
Filename: "{app}\main.exe"; Description: "Launch Barangay System"; Flags: nowait postinstall skipifsilent
