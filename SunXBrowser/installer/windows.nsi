Unicode true
!include "MUI2.nsh"
!include "LogicLib.nsh"
!ifndef PAYLOAD
  !error "PAYLOAD is required"
!endif
!ifndef OUTPUT
  !error "OUTPUT is required"
!endif
!ifndef VERSION
  !error "VERSION is required"
!endif
!ifndef PAYLOAD_DELETE
  !error "PAYLOAD_DELETE is required"
!endif
Name "SunXBrowser"
VIProductVersion "${VERSION}"
VIAddVersionKey /LANG=1033 "ProductName" "SunXBrowser"
VIAddVersionKey /LANG=1033 "FileDescription" "SunXBrowser per-user installer"
VIAddVersionKey /LANG=1033 "FileVersion" "${VERSION}"
OutFile "${OUTPUT}"
Icon "..\assets\app.ico"
UninstallIcon "..\assets\app.ico"
InstallDir "$LOCALAPPDATA\Programs\SunXBrowser"
RequestExecutionLevel user
SetCompressor /SOLID lzma
!define MUI_ABORTWARNING
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"

Section "SunXBrowser"
  SetShellVarContext current
  SetOutPath "$INSTDIR"
  File /r "${PAYLOAD}\*.*"
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  CreateDirectory "$SMPROGRAMS\SunXBrowser"
  CreateShortcut "$SMPROGRAMS\SunXBrowser\SunXBrowser.lnk" "$INSTDIR\chrome.exe"
  CreateShortcut "$SMPROGRAMS\SunXBrowser\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
  CreateShortcut "$DESKTOP\SunXBrowser.lnk" "$INSTDIR\chrome.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\SunXBrowser" "DisplayName" "SunXBrowser"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\SunXBrowser" "DisplayVersion" "${VERSION}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\SunXBrowser" "UninstallString" '$\"$INSTDIR\Uninstall.exe$\"'
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\SunXBrowser" "InstallLocation" "$INSTDIR"
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\SunXBrowser" "NoModify" 1
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\SunXBrowser" "NoRepair" 1
SectionEnd

Section "Uninstall"
  SetShellVarContext current
  Delete "$DESKTOP\SunXBrowser.lnk"
  Delete "$SMPROGRAMS\SunXBrowser\SunXBrowser.lnk"
  Delete "$SMPROGRAMS\SunXBrowser\Uninstall.lnk"
  RMDir "$SMPROGRAMS\SunXBrowser"
  ; PAYLOAD_DELETE is generated from the exact payload; never delete profiles.
  !include "${PAYLOAD_DELETE}"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\SunXBrowser"
SectionEnd
