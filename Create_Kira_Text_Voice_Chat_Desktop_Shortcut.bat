@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$shell = New-Object -ComObject WScript.Shell; " ^
  "$desktop = [Environment]::GetFolderPath('Desktop'); " ^
  "$shortcut = $shell.CreateShortcut((Join-Path $desktop 'Kira Text + Voice Chat.lnk')); " ^
  "$shortcut.TargetPath = (Join-Path (Get-Location) 'Start_Kira_Text_Voice_Chat.bat'); " ^
  "$shortcut.WorkingDirectory = (Get-Location).Path; " ^
  "$icon = Join-Path (Get-Location) 'Assets\icons\kira_world_shell_icon.ico'; " ^
  "if (Test-Path $icon) { $shortcut.IconLocation = $icon }; " ^
  "$shortcut.Description = 'Kira text and full-voice chat without loading the 3D world'; " ^
  "$shortcut.Save(); " ^
  "Write-Host 'Created desktop shortcut: Kira Text + Voice Chat.lnk'"
if %ERRORLEVEL% NEQ 0 pause
