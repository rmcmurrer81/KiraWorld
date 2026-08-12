@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$shell = New-Object -ComObject WScript.Shell; $shortcut = $shell.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\Kira World Shell.lnk'); $shortcut.TargetPath = '%CD%\Start_Kira_World_Shell.bat'; $shortcut.WorkingDirectory = '%CD%'; $shortcut.IconLocation = '%CD%\Assets\icons\kira_world_shell_icon.ico,0'; $shortcut.Save()"
echo Created desktop shortcut: Kira World Shell
pause
