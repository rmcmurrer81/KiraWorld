@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$shell = New-Object -ComObject WScript.Shell; " ^
  "$desktop = [Environment]::GetFolderPath('Desktop'); " ^
  "$shortcut = $shell.CreateShortcut((Join-Path $desktop 'Kira World Builder Workspace.lnk')); " ^
  "$shortcut.TargetPath = (Join-Path (Get-Location) 'Start_Kira_World_Builder_Workspace.bat'); " ^
  "$shortcut.WorkingDirectory = (Get-Location).Path; " ^
  "$icon = Join-Path (Get-Location) 'Assets\icons\kira_world_shell_icon.ico'; " ^
  "if (Test-Path $icon) { $shortcut.IconLocation = $icon }; " ^
  "$shortcut.Description = 'World Builder workspace for source-labeled notebook-world requests without loading Home World'; " ^
  "$shortcut.Save(); " ^
  "Write-Host 'Created desktop shortcut: Kira World Builder Workspace.lnk'"
if %ERRORLEVEL% NEQ 0 pause
