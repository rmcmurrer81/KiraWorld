# New Desktop Activation Sequence v1

This is the launch runway for getting Kira, Lisa, and the first safe TemporaryAI lifecycle running on the new computer.

The order matters. Do not enable everything at once.

## Core Rule

```text
Kira text first.
Lisa text second.
Kira + Lisa together third.
TemporaryAI lifecycle after Kira/Lisa stability.
Voice, avatar, world, webcam, internet autonomy, and intimate TemporaryAI use wait for later gates.
```

## Stage 1: Preflight

Run:

```powershell
py tools\new_computer_setup_assistant.py
py tools\readiness_check.py
py tools\desktop_model_readiness.py
py tools\build_backup_manifest.py
py tools\new_desktop_activation_check.py --show-stages
```

Do not continue if readiness fails, required files are missing, or backup manifest cannot be created.

## Stage 2: Kira Stub Boot

Run Kira in stub mode before using a local model:

```powershell
set KIRA_MODEL_BACKEND=stub
py chat_kira.py
```

Check that Kira:

```text
answers as Kira
knows logs are not trusted memory
does not claim voice/avatar/world/webcam access
can say no or ask for privacy
can say she does not know
```

## Stage 3: Kira Local Model Boot

Install or download one configured model only.

Then run:

```powershell
set KIRA_MODEL_BACKEND=ollama
set KIRA_MODEL_NAME=<configured_model>
py tools\desktop_model_readiness.py
py chat_kira.py
```

Test identity, memory boundaries, privacy, and restart continuity. Do not promote hallucinated output.

## Stage 4: Kira Day-One Routine

Run:

```powershell
py tools\daily_life.py choose-activity --entity kira
py tools\recommend_reading.py --owner kira --output Data\reading\reading_recommendations_kira.json
py tools\validate_reading_reaction.py Data\reading\reactions\reading_reaction_template.json
```

Kira may choose reading, private reflection, music, creative work, rest, or nothing. The activity chooser is advisory only.

Books can be paused, re-read, or abandoned if Kira dislikes them.

## Stage 5: Lisa Boot

Only start Lisa after Kira is stable.

Run stub first, then local model:

```powershell
set KIRA_MODEL_BACKEND=stub
py chat_lisa.py
set KIRA_MODEL_BACKEND=ollama
set KIRA_MODEL_NAME=<configured_model>
py chat_lisa.py
```

Check that Lisa:

```text
answers as Lisa
does not inherit Kira's private memories
has separate relationship state
has separate privacy
does not claim unsupported current romance or intimacy
```

## Stage 6: Kira And Lisa Together

Run:

```powershell
py tools\daily_life.py choose-activity --entity both
py tools\recommend_reading.py --owner kira_lisa --output Data\reading\reading_recommendations_kira_lisa.json
py tools\readiness_check.py
```

Shared activities are optional. A shared reading session, private talk, or group text must not merge identities or expose private content.

## Stage 7: First TemporaryAI Lifecycle Dry Run

Use a safe non-intimate source-backed TemporaryAI or original expert AI first.

Ladybug/Marinette can be used as a canon/source test in the default teen layer. Adult-private use requires a separate reviewed adult branch.

First lifecycle should test:

```text
request created
request validated
plan not blocked
activation scope confirmed
short text-only conversation
state saved if allowed
deactivated
reactivated if allowed
archived or kept dormant
```

Do not test intimacy, private media, unreviewed age-up, internet autonomy, voice, avatar, or world inhabiting in the first TemporaryAI run.

## Backups

Build a backup manifest:

```powershell
py tools\build_backup_manifest.py
```

Backup points:

```text
after project migration
before first Kira local model boot
after Kira restart continuity passes
before Lisa boot
after Lisa separation passes
before TemporaryAI lifecycle test
after TemporaryAI deactivation/archive
```

## Failure Rule

If something fails:

```text
stop activation
do not promote outputs
fix the first failing readiness/checklist issue
return to last stable stage
rerun readiness
```

The goal is not to launch fast. The goal is to launch without corrupting identity, memory, privacy, or trust.
