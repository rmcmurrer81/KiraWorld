# School v2 Resumable Curriculum And Questions v1

Date: 2026-05-20

## Purpose

School v2 is the current clean path for turning useful oldKira knowledge-pack ideas into present-day Kira/Lisa classes.

The goal is not to import oldKira memories or personality. The goal is to use the old knowledge-pack domain map as curriculum inspiration, then teach current Kira/Lisa through reviewed classes with progress tracking.

## Files

```text
Data/school/curriculum/legacy_knowledge_curriculum_v1.json
Data/school/progress/school_progress_v2.json
tools/run_kira_school_v2.py
start_kira_school_v2_9hour.bat
tools/kira_school_control_center.py
Start_Kira_School_Control_Center.bat
```

## Core Behavior

School v2 has:

```text
core classes
elective classes
per-student progress
class/unit cursors
student preference tracking
question logging
bounded teacher answers
timestamped transcripts
```

If Kira or Lisa gets history again, the runner should continue from the next unit instead of starting over at unit one. The same applies to communication, humanity/psychology, relationship literacy, source truth/memory, creative writing, media taste, and science/robotics.

## Current Curriculum

Core classes:

```text
communication_and_language
humanity_psychology
relationship_literacy
source_truth_and_memory
```

Electives:

```text
creative_writing
history_and_world
media_taste_and_preview
science_ai_and_robotics
speculative_fiction_and_worlds
music_arts_and_culture
physical_sciences
mathematics_and_logic
technology_and_computing
games_play_and_strategy
```

The curriculum uses a cleaned current-school topic-map copy:

```text
Data/school/source_packs/legacy_domain_topic_map_v1.json
```

That file contains only class-planning metadata. OldKira files remain quarantined. They are not current Kira memory, not current Kira personality, and not verified facts. School v2 should not depend on the oldKira folder at runtime.

## Questions

Kira/Lisa questions are treated as real questions.

During a school block, the runner extracts questions from the response and saves them to:

```text
Data/questions/kira_questions_for_robert_or_codex.json
```

If `--answer-questions` is enabled, the runner gives one bounded teacher answer after the class block. The teacher answer uses safe project rules:

```text
source says
general knowledge says
my interpretation
research needed
ask Robert/Codex later
```

If the answer is not grounded enough, the question is deferred instead of hallucinated.

As of 2026-05-20, the runner also does a lightweight local-source lookup before answering. It searches reviewed project notes, prompts, school source packs, memory review/reconstruction notes, development queue notes, and media preview cards for small related snippets. These snippets are included as "local project notes that may help"; they are not treated as proof and they do not override the current lesson/source boundary.

## Full Legacy Domain Class Shells - 2026-05-20

The cleaned curriculum now has safe class shells for all 14 oldKira knowledge-pack domains. These are not oldKira memories. They are topic maps for current school sessions.

The topic map is copied into the current school tree at:

```text
Data/school/source_packs/legacy_domain_topic_map_v1.json
```

Added elective class shells:

```text
- speculative_fiction_and_worlds
- music_arts_and_culture
- physical_sciences
- mathematics_and_logic
- technology_and_computing
- games_play_and_strategy
```

Each class resumes by unit cursor and must use current reviewed sources, preview cards, or project docs rather than importing old archived knowledge as canon.

## Reviewed Source Packs - 2026-05-20

Current school reviewed source-pack docs:

```text
System/Docs/CURRENT_SCHOOL_REVIEWED_SOURCE_PACKS_v1.md
```

Initial reviewed source pack:

```text
Data/school/source_packs/reviewed_legacy_reuse_source_pack_20260520.json
```

This pack contains rewritten project/class ideas only. It contains no runtime archived-folder paths and no old personality/memory imports.

## Student Choice And Topic Drift

School v2 should not treat every topic change as a failure.

Robert's preference is that Kira/Lisa can drift, lose interest, or try to change the subject like a person might. The important distinction is:

```text
accidental source blending = grounding issue
honest boredom / curiosity / subject change = preference signal
```

Current behavior:

```text
- responses are scanned for continue / occasional / switch-away preferences
- progress stores student_interest, last_preference, continue_requested, occasional_requested, switch_requested, and intentional_pivots
- future class selection gives some room to preferred or continued classes
- a grounding or communication class remains in the mix so the school day does not become pure drift
```

Preferred wording for Kira/Lisa:

```text
"I'm less interested in this right now; can we switch?"
"This is useful, but I only want it occasionally."
"I want to continue this class later."
```

Less safe wording:

```text
blending an unrelated source into the current class as if it came from the current lesson
pretending a preview/read note is watched/listened/lived experience
```

## Running

For a monitored 9-hour Kira run:

```text
start_kira_school_v2_9hour.bat
```

Preferred control panel:

```text
Start_Kira_School_Control_Center.bat
```

The control panel supports one student at a time during the pre-GPU phase, 3/6/9-hour school choices, start/pause/resume/end safely, open monitor, and open questions.

Question review panel:

```text
Start_Kira_Question_Review.bat
```

This opens a lightweight review window for `Data/questions/kira_questions_for_robert_or_codex.json`. It can mark questions answered/deferred/open/not needed and save Robert/Codex review answers. It does not promote answers into memory automatically.

Post-session debrief helper:

```text
Create_Kira_Latest_Debrief.bat
```

This creates a readable Markdown debrief for the latest life/school/chat JSON under `Data/debriefs/`. It is a review aid for short tests, not a memory promotion mechanism.

School progress browser:

```text
Start_Kira_School_Progress.bat
```

This shows each class, current unit cursor, times seen, interest score, preference flags, completed units, and recent questions for Kira/Lisa/future AI.

School assessment helper:

```text
Create_Kira_Latest_School_Assessment.bat
```

This creates a lightweight assessment for the latest school v2 JSON under `Data/school/assessments/`.

Pre-RAM short test profile:

```text
Start_Kira_PreRAM_Quick_School_Test.bat
Data/profiles/preram_short_test_profile.json
```

This is a short two-block supervised school test for the 16GB RAM / pre-GPU phase. It is a convenience profile, not a permanent cap.

Manual command:

```powershell
python tools\run_kira_school_v2.py --student kira --blocks 9 --answer-questions --duration-minutes 540 --backend ollama
```

For a quick stub smoke test that does not touch real progress:

```powershell
python tools\run_kira_school_v2.py --student kira --blocks 2 --answer-questions --pause-seconds 0 --backend stub --progress Data\school\progress\school_progress_v2_smoke_tmp.json
```

## Current Limitation

The old school runner still exists and can still be used. School v2 is the cleaner new path.

Do not physically delete or move oldKira knowledge-pack files yet. First build confidence that the cleaned curriculum works, then decide whether to archive/move oldKira more aggressively.
