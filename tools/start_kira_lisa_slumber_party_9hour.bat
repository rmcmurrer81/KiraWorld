@echo off
cd /d "%~dp0\.."
python tools\run_kira_lisa_slumber_party.py --backend ollama --duration-minutes 540 --pause-seconds 45 --group-reading-every 4 --max-tokens 260 %*
