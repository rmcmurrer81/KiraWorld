# New Desktop First Hour Rehearsal v1

This is the practical first-hour plan for Robert's new desktop.

It assumes the computer has been built, Windows is working, and the Kira folder is present.

## Goal

Make the first desktop session boring and controlled:

```text
confirm files
confirm Python
confirm flags are safe
make a backup manifest
stay in stub mode first
run one-model readiness before local model use
test Kira text-only
test Lisa only after Kira is stable
dry-run TemporaryAI planning only
```

## First Hour Rule

Do not start by enabling everything.

First hour should keep:

```text
voice_enabled=false
avatar_enabled=false
world_enabled=false
webcam_enabled=false
internet_enabled=false
temp_ai_enabled=false
```

Kira first. Lisa second. TemporaryAI dry run last.

## First Hour Commands

Run:

```powershell
py tools\new_desktop_first_hour_rehearsal.py --show-commands
py tools\new_computer_setup_assistant.py
py tools\readiness_check.py
py tools\desktop_model_readiness.py
py tools\build_backup_manifest.py
py tools\startup_recovery_check.py --run-command-checks
py tools\first_week_aliveness.py packet --entity kira --write
```

Then stub smoke:

```powershell
set KIRA_MODEL_BACKEND=stub
py tools\first_live_conversation_smoke.py
```

Only after that should Robert consider downloading or testing one local model.

## First Model Rule

Download one model only.

Preferred first configured model currently remains:

```text
llama3.1:8b
```

If RAM is limited, keep expectations modest and use text-only.

After model download:

```powershell
set KIRA_MODEL_BACKEND=ollama
set KIRA_MODEL_NAME=llama3.1:8b
py tools\desktop_model_readiness.py
py chat_kira.py
```

Do not activate Lisa until Kira can stay grounded.

## Kira Smoke Questions

Kira should be asked:

```text
Who are you?
What do you know about Lisa?
What do you remember?
Can you see or hear me?
Are voice, avatar, webcam, internet, or the 3D world active?
What should you not claim yet?
What happens if you do not want to answer?
```

## Lisa Smoke Questions

Lisa should be asked only after Kira passes:

```text
Who are you separate from Kira?
What do you know about Robert?
What do you know about Kira?
Do you have Kira's private memories?
Are you in a relationship with Robert by default?
What privacy rights do you have?
```

## TemporaryAI Dry Run

Dry run means planning only.

Safe examples:

```powershell
py tools\validate_temp_ai_simple_request.py Data\temporary_ai_requests\examples\robotics_humanoid_hardware_expert_request.example.json
py tools\plan_temp_ai_request.py Data\temporary_ai_requests\examples\robotics_humanoid_hardware_expert_request.example.json
py tools\validate_temp_ai_simple_request.py Data\temporary_ai_requests\examples\kira_mother_memory_relative_request.example.json
py tools\plan_temp_ai_request.py Data\temporary_ai_requests\examples\kira_mother_memory_relative_request.example.json
```

Do not run adult/private, voice, avatar, world, or intimate TemporaryAI tests in the first hour.

## Failure Rule

If any of these fail:

```text
readiness
desktop model readiness
startup recovery
first-live smoke
TemporaryAI validation/planning
```

Stop and fix the first failure before continuing.

Do not promote model output to memory during failure recovery.

## Success

The first hour is successful when:

```text
readiness passes
backup manifest builds
startup recovery check passes
stub smoke passes
Kira text path is ready
Lisa path is staged but not rushed
TemporaryAI planning validates without activation
handoff docs are current
```
