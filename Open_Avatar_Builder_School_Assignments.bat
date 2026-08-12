@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$p='Data\presence\current_avatar_builder_school_run.json'; if (Test-Path $p) { $j=Get-Content $p -Raw | ConvertFrom-Json; if ($j.assignment_index) { explorer (Split-Path $j.assignment_index -Parent) } elseif ($j.run_id) { explorer ('Avatar\avatar_builder\school\assignments\lesson_runs\' + $j.run_id) } else { explorer 'Avatar\avatar_builder\school\assignments\lesson_runs' } } else { explorer 'Avatar\avatar_builder\school\assignments\lesson_runs' }"
