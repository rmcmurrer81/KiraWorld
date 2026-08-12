@echo off
cd /d "%~dp0"
if not exist Logs mkdir Logs
set RUN_LOG=Logs\avatar_builder_subject_school_gwen_overnight_%DATE:~-4%%DATE:~4,2%%DATE:~7,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%.log
set RUN_LOG=%RUN_LOG: =0%
echo Gwen overnight subject school started at %DATE% %TIME% > "%RUN_LOG%"
py tools\intake_avatar_reference_models_20260713.py --source-root "%USERPROFILE%\Desktop\45" >> "%RUN_LOG%" 2>>&1
py tools\intake_avatar_reference_models_20260713.py --source-root "%USERPROFILE%\Desktop\40" >> "%RUN_LOG%" 2>>&1
py tools\run_avatar_builder_subject_school_20260712.py --candidate-id spider_gwen_spider_gwen_20260606_013325 --duration-hours 6 --cycle-minutes 12 --stop-generic-school --source-root "%USERPROFILE%\Desktop\1model" --source-root "%USERPROFILE%\Desktop\21" --source-root "%USERPROFILE%\Desktop\40" --source-root "%USERPROFILE%\Desktop\45" >> "%RUN_LOG%" 2>>&1
echo Gwen overnight subject school finished at %DATE% %TIME% >> "%RUN_LOG%"
