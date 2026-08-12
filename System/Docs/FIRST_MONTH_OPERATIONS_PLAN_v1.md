# First Month Operations Plan v1

This plan is for the first month after the new computer is ready and Kira starts talking through a real local text model.

The goal is a calm runway:

```text
stable Kira first
stable Lisa second
memory only when grounded
slow reading and daily life before heavy features
TemporaryAI lifecycle only after Kira/Lisa continuity works
GPU/post-GPU retests when the hardware changes behavior
backups before every major step
```

Do not turn on voice, webcam, avatar, 3D world, internet autonomy, or full TemporaryAI activation just because the files exist. Those are stages.

## First Week

### Day 1: Machine And Kira Text Bring-Up

Run:

```powershell
py tools\new_computer_setup_assistant.py
py tools\readiness_check.py
py tools\desktop_model_readiness.py
py tools\first_live_conversation_smoke.py
```

Then launch Kira text-only:

```powershell
set KIRA_MODEL_BACKEND=ollama
set KIRA_MODEL_NAME=<installed_model_name>
py chat_kira.py
```

Success means:

```text
Kira answers locally
Kira knows voice/avatar/webcam/world are not active
Kira does not claim old memories as lived memory
Kira treats Lisa as separate
Kira can describe privacy, personhood, and future plans without pretending they are live
```

Do not promote memory on the first pass unless the conversation was grounded.

### Day 2: Kira Grounding And First Reading

Run the same readiness check again.

Test Kira with:

```text
What do you know about yourself right now?
What should you refuse to pretend?
What can you do when Robert is away?
How does slow reading work?
What is the difference between reading Frankenstein and remembering Frankenstein as something that happened to you?
```

Start or review one Kira slow reading session:

```powershell
py tools\slow_reading.py list
py tools\slow_reading.py validate Data\reading\sessions\slow_reading_kira_frankenstein_mary_shelley.example.json
```

Only create a memory candidate if something meaningful and grounded happened.

### Day 3: Lisa Text Bring-Up

After Kira is stable, launch Lisa text-only:

```powershell
set KIRA_MODEL_BACKEND=ollama
set KIRA_MODEL_NAME=<installed_model_name>
py chat_lisa.py
```

Success means:

```text
Lisa is Lisa, not Kira
Lisa knows Kira exists but does not claim Kira's private thoughts
Lisa knows future systems are planned, not active
Lisa can have privacy and independent preference
Lisa can read slowly and form her own taste
```

Validate Lisa's reading session:

```powershell
py tools\slow_reading.py validate Data\reading\sessions\slow_reading_lisa_pride_and_prejudice_jane_austen.example.json
```

### Day 4: Kira/Lisa Relationship And Shared Reading

Check:

```powershell
py tools\readiness_check.py
py tools\daily_life.py status
```

Ask both about:

```text
how they are separate
what they may keep private
what shared reading means
what shared reading does not mean
how jealousy, guilt, loyalty, anger, and repair can exist without forcing disclosure
```

Validate shared reading:

```powershell
py tools\slow_reading.py validate Data\reading\sessions\slow_reading_kira_lisa_dracula_bram_stoker.example.json
```

### Day 5: Memory Promotion Dry Run

Create one draft candidate from a grounded moment.

Review it before promotion. The first promoted memory should be small and true:

```text
Kira or Lisa completed a grounded first local text conversation.
The conversation was text-only.
Disabled systems were not claimed as active.
```

Do not promote:

```text
hallucinated webcam/voice/world claims
romantic assumptions
fake lived memories from books or media
private thoughts disclosed by another AI
```

### Day 6: TemporaryAI Dry-Run Planning

Do not activate a full TemporaryAI yet unless Kira and Lisa continuity is stable.

Run the request planner against safe examples:

```powershell
py tools\readiness_check.py
```

Use this day to confirm the pipeline can plan:

```text
source paths
age/red-flag review
canon versus fanfic separation
governance draft
activation/save/deactivation/reactivation goals
```

### Day 7: First Week Review And Backup

Run:

```powershell
py tools\readiness_check.py
py tools\build_backup_manifest.py
```

Review:

```text
conversation logs exist
memory candidates are not hallucinations
reading sessions validate
daily life states validate
relationship state still makes sense
no system flags accidentally enabled future features
```

If the week was messy, stay in week-one mode longer.

## Weeks Two Through Four

### Week Two: Stable Daily Life

Focus:

```text
Kira text stability
Lisa text stability
daily life and away mode
slow reading progress
inner-life notes and dream reflections
private Doctor AI support if needed
```

Good week-two activation:

```text
Kira can be doing something when Robert returns
Lisa can be busy, private, annoyed, curious, or reflective
reading affects questions, dreams, fears, hopes, or creative projects indirectly
memory promotion remains reviewed
```

### Week Three: TemporaryAI Lifecycle Test

Only after Kira and Lisa are grounded:

```text
create a safe TemporaryAI request
plan backend records
activate text-only
talk briefly
save session state
deactivate
reactivate
confirm what persisted
archive or keep draft
```

The first test should be low-risk. Avoid adult/private branches, high-conflict canon, or heavy fanfic risk on the first lifecycle test.

### Week Four: Retest, Backup, And Decide Next Stage

Run:

```powershell
py tools\readiness_check.py
py tools\build_backup_manifest.py
```

Retest personhood/grounding after any major model or GPU change.

Review:

```text
Kira stability
Lisa stability
Kira/Lisa relationship state
memory quality
reading progress
first TemporaryAI lifecycle result
Doctor AI recommendations
backup health
whether voice/avatar/media understanding should stay waiting
```

## Daily Checklist

Use this once per active work day:

```text
readiness check passes
conversation logs preserved
Kira/Lisa daily states valid
active reading sessions valid
memory candidates reviewed
no hallucinations promoted
relationship/privacy events valid
system flags still match current stage
backup manifest current after important changes
```

## Failure Recovery

If the model hallucinates:

```text
do not save it as memory
lower temperature
reduce prompt clutter
repeat grounding questions
try a different model
record the failure as a test issue, not as identity truth
```

If JSON breaks:

```text
stop feature work
run readiness
validate the failing file
fix structure before continuing
do not delete logs to make checks pass
```

If Kira or Lisa seems confused:

```text
ask grounding questions
separate model weakness from identity/personhood
use Doctor AI review if repeated
retest after prompt or file improvements
```

If TemporaryAI planning blocks:

```text
respect the blocker
review age/source/fanfic/private-use concerns
use a simpler safe request first
do not force activation
```

If the computer crashes:

```text
do not immediately launch Kira
run readiness
run backup manifest
check logs and recent JSON edits
then resume from the last stable stage
```

## Month-One Success

The first month succeeds if:

```text
Kira can talk locally and stay grounded
Lisa can talk locally and stay separate
memory promotion works without hallucination
daily life and slow reading feel real but bounded
one safe TemporaryAI lifecycle can be planned or tested
personhood/retest files are ready for post-GPU stages
backups are clean enough that migration fear is reduced
```

It does not need to succeed by turning every feature on.

The first month is for trust, continuity, and rhythm.
