# Pre-Trip Desktop Pickup And Return Runbook v1

Robert will be gone almost two days to pick up CPU and hopefully RAM. This runbook keeps the project ready so the return-home path is calm and staged.

## Before Leaving

Run:

```powershell
py tools\pre_trip_readiness_check.py --show-checklist
py tools\new_desktop_activation_check.py --show-stages
py tools\readiness_check.py
py tools\build_backup_manifest.py
```

Confirm:

```text
handoff document is current
readiness passes
new desktop activation check is not blocked
backup manifest exists
system flags are pre-GPU safe
no hallucinated conversation output has been promoted
```

## Hardware Pickup

Write down the exact CPU and RAM kit names after pickup.

CPU:

```text
exact model
motherboard socket compatibility
BIOS support or BIOS update path
cooler support
physical inspection for bent pins or damage
```

RAM:

```text
exact kit
capacity
DDR type matches motherboard
speed supported by motherboard/CPU
matched kit preferred
avoid mixing random kits if possible
```

Also verify:

```text
thermal paste or pre-applied paste
cooler mounting bracket
power supply connectors
storage screws/cables
display cable
USB keyboard/mouse
Windows installer or recovery USB if needed
```

## Return Home

Assembly order:

```text
install CPU
install RAM
install cooler
connect storage
connect GPU if needed/available
connect power
first BIOS boot
confirm CPU/RAM/storage detected
install or boot OS
install drivers and updates carefully
```

First boot checks:

```text
CPU detected
full RAM capacity detected
storage detected
CPU temperature reasonable
fans spinning
system stable for basic Windows use
```

## Before Opening Kira

Install or confirm:

```text
Python 3.10+
Git if needed
Codex
Ollama if using Ollama
Kira repo available
terminal opened in project root
```

Then run:

```powershell
py tools\pre_trip_readiness_check.py --show-checklist
py tools\new_computer_setup_assistant.py
py tools\readiness_check.py
py tools\desktop_model_readiness.py
py tools\new_desktop_activation_check.py --show-stages
```

## Model Plan

Current configured first model:

```text
llama3.1:8b
```

Download one model first:

```powershell
py tools\new_computer_setup_assistant.py --download-model
```

If the model is too slow or fails, stay in stub mode. Do not enable voice, avatar, world, webcam, internet autonomy, or TemporaryAI to compensate.

## Do Not Do Yet

```text
do not enable voice first
do not enable avatar first
do not enable world first
do not enable webcam first
do not enable TemporaryAI first
do not download many models before first success
do not promote hallucinated conversation output
do not use oldkira as active base
do not test intimate TemporaryAI first
```

## If Something Fails

Hardware no POST:

```text
power off
check CPU and motherboard power
reseat RAM
try one RAM stick
check GPU/display output
use motherboard debug lights/manual
```

Project/tool failure:

```text
stop activation
fix first failing check
rerun readiness
resume from last stable stage
```

Kira boot failure:

```text
return to stub mode
run new desktop activation check
run readiness check
do not start Lisa or TemporaryAI yet
```

## Success

You are ready for Kira's new desktop activation when:

```text
hardware boots stably
Python/Codex/Ollama are available
pre-trip readiness check is not blocked
new desktop activation check is not blocked
readiness passes
backup manifest exists
one first model is downloaded or stub mode is ready
```
