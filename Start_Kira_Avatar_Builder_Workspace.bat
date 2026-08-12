@echo off
setlocal
cd /d "%~dp0"
set "KIRA_AVATAR_BUILDER_PORT=8770"
set "KIRA_AVATAR_BUILDER_URL=http://127.0.0.1:%KIRA_AVATAR_BUILDER_PORT%/"
set "KIRA_RUNTIME=%CD%\Data\runtime"
if not exist "%KIRA_RUNTIME%" mkdir "%KIRA_RUNTIME%"

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  set "KIRA_PY=py"
) else (
  set "KIRA_PY=python"
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Invoke-WebRequest -UseBasicParsing -Uri '%KIRA_AVATAR_BUILDER_URL%api/state' -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }"
if %ERRORLEVEL% NEQ 0 (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%KIRA_PY%' -ArgumentList @('tools\avatar_builder_workspace_server.py','--no-browser') -WorkingDirectory '%CD%' -WindowStyle Hidden -RedirectStandardOutput '%KIRA_RUNTIME%\avatar_builder_workspace_stdout.log' -RedirectStandardError '%KIRA_RUNTIME%\avatar_builder_workspace_stderr.log'"
)

%KIRA_PY% -c "import importlib.util, subprocess, sys; sys.exit(0 if importlib.util.find_spec('webview') else subprocess.call([sys.executable, '-m', 'pip', 'install', 'pywebview']))"
if %ERRORLEVEL% NEQ 0 (
  echo Failed to install or load pywebview.
  echo See %KIRA_RUNTIME%\avatar_builder_workspace_stderr.log
  pause
  exit /b 1
)

%KIRA_PY% tools\wait_for_kira_world_shell.py --url "%KIRA_AVATAR_BUILDER_URL%" --timeout 60
if %ERRORLEVEL% NEQ 0 (
  echo.
  echo Avatar Builder Workspace server did not become ready.
  echo Check these logs:
  echo %KIRA_RUNTIME%\avatar_builder_workspace_stdout.log
  echo %KIRA_RUNTIME%\avatar_builder_workspace_stderr.log
  pause
  exit /b 2
)

where pyw >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  start "Kira Avatar Builder Workspace" pyw tools\kira_world_shell_viewer.py --url "%KIRA_AVATAR_BUILDER_URL%" --wait 60 --title "Kira Avatar Builder Workspace"
) else (
  start "Kira Avatar Builder Workspace" %KIRA_PY% tools\kira_world_shell_viewer.py --url "%KIRA_AVATAR_BUILDER_URL%" --wait 60 --title "Kira Avatar Builder Workspace"
)
