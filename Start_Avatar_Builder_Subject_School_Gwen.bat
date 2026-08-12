@echo off
cd /d "%~dp0"
py tools\intake_avatar_reference_models_20260713.py --source-root "%USERPROFILE%\Desktop\45"
py tools\intake_avatar_reference_models_20260713.py --source-root "%USERPROFILE%\Desktop\40"
py tools\run_avatar_builder_subject_school_20260712.py --candidate-id spider_gwen_spider_gwen_20260606_013325 --duration-hours 4 --cycle-minutes 15 --stop-generic-school --source-root "%USERPROFILE%\Desktop\1model" --source-root "%USERPROFILE%\Desktop\21" --source-root "%USERPROFILE%\Desktop\40" --source-root "%USERPROFILE%\Desktop\45"
py tools\run_avatar_builder_subject_school_real_model_pass_20260713.py --candidate-id spider_gwen_spider_gwen_20260606_013325
pause
