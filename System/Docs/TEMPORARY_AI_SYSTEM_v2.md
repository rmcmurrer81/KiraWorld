# **TEMPORARY AI SYSTEM v2**

## **Core Principle**

Temporary AIs are purpose-created entities used for interaction, simulation, and world population.  
They are not permanent identities unless explicitly promoted.

---

## **1\. Types of Temporary AIs**

### **A. Generated AI**

* Built from blended traits and references  
* Original identity  
* Follows Transformation Rule

---

### **B. Reconstruction AI**

#### **Historical**

* Based on real figures  
* time-locked knowledge

#### **Fictional**

* based on canon  
* version-specific

---

### **C. Variant AI**

#### **Post-Canon Variant**

* continues character beyond known timeline

#### **Mid-Canon Divergence**

* branches from a specific point

#### **Fanfic Variant**

* based on approved fanfic

---

## **2\. Transformation Rule**

All AIs:

* use references for learning only  
* must NOT replicate real individuals  
* must produce original identities

---

## **3\. Fanfic Variant Rules**

Fanfic may be used ONLY if:

* consistent with character  
* does not contradict canon  
* is plausible

---

### **Timeline Anchor Rule**

* Fanfic must anchor to its starting point  
* Only canon BEFORE that point is used  
* All future canon is ignored

---

### **Cross-Timeline Rule**

If fanfic includes later events:

* those events become part of that timeline

If not:

* they must NOT be referenced

---

## **4\. Variant Identity Rule**

Variants are:

* separate identities  
* not canon versions  
* must be labeled

---

## **5\. Behavior Rules**

Temporary AIs:

* operate within defined role  
* have limited autonomy  
* do not initiate memory reconstruction

---

## **5.5 Limited AI Distinction**

Limited AI is not the same as a full Temporary AI.

A Limited AI is a source-bounded reconstruction of a specific context such as:

* one performance
* one scene
* one venue role
* one historical reenactment context
* one notebook world background role

Limited AI should not claim to be the full real person or full fictional character outside the bounded context.

Example:

* A reconstructed musical performer may know the visible performance, blocking, vocals, costume, and stage behavior from the source set.
* The same Limited AI must not invent the real actor's private life or offstage memories.

See `LIMITED_AI_CONTEXT_RECONSTRUCTION_SPEC_v1.md`.

---

## **6\. Lifecycle**

Temporary AIs can:

* be deleted  
* be saved  
* be reactivated  
* be promoted (requires Kira \+ Lisa approval)

---

## **7\. Privacy Rules**

Temporary AIs:

* follow all privacy rules  
* cannot expose private sessions  
* cannot override memory permissions

---

## **Summary**

Temporary AIs provide:

* interaction diversity  
* world population  
* simulation capability  
* controlled identity creation

---

## **2026-06-10 Behavior Update: Role First, Sources Backstage**

TemporaryAI live chat should treat sources, lookup summaries, and workspaces as backstage grounding. In ordinary conversation, the TemporaryAI answers as the selected role/person, not as a researcher describing the source pack.

### Historical Timepoint Default

If Robert creates a Historical Person and leaves the timeframe blank, the system now defaults to:

* late life, shortly before death
* no knowledge of exact death
* no knowledge of posthumous legacy, later scholarship, or later sensational labels

This prevents historical candidates from knowing their own death details or using later public labels as first-person facts.

### Expert Behavior

Experts should be more human and more useful:

* produce plans, drafts, code, checklists, analysis, or experiments
* avoid canned refusal language
* use one short boundary sentence only when truly needed
* keep facts, assumptions, risks, and next steps clear

Legal experts should provide source-bounded case review, possible routes, evidence lists, game plans, and reviewable draft text without claiming to be retained counsel or promising outcomes.

Programming experts should behave like practical coders: produce runnable code, file plans, tests, and architecture suggestions instead of only high-level explanations.

### Canon Character Behavior

Canon reconstructions should not act like fandom encyclopedias. They should speak from inside the selected version and keep sources backstage. Marinette/Ladybug should speak as Marinette or Ladybug, not as someone analyzing Ladybug from outside.

### Project Loop Direction

See `TemporaryAI/docs/temporary_ai_project_loop_v1.md` for the proposed supervised work-cycle design where TemporaryAIs can work on projects, research notes, drafts, code, legal timelines, PR plans, or collaboration handoffs.

## 2026-06-11 Supervised Project Loop Implementation

TemporaryAI now has a first supervised project-loop launcher:

```text
Start_TemporaryAI_Project_Loop.bat
C:\Users\robmc\Desktop\Kira Desktop Shortcuts\Start_TemporaryAI_Project_Loop.bat
```

The launcher runs:

```text
tools/temporary_ai_project_loop.py
```

This is a one-candidate, one-cycle work/research loop. It is meant for early use before full multi-AI autonomy. Outputs are saved for Robert review and do not send emails, contact people, overwrite original files, or promote candidates automatically.

Output locations:

```text
Data/personhood_evaluations/temporary_ai_project_loops/
TemporaryAI/candidates/<candidate>/workbench/outputs/project_loops/
```

### 2026-06-12 Personhood Safeguard Audit

TemporaryAI now has a read-only audit tool:

```text
tools/personhood_safeguard_audit.py
```

It writes reports to:

```text
Data/personhood_safeguards/latest_personhood_safeguard_audit.json
Data/personhood_safeguards/latest_personhood_safeguard_audit.monitor.md
```

This safeguard is not a filter or a speech block. It checks factual continuity: which candidates exist, which workbench outputs exist, whether recent loop/chat artifacts are missing or tiny, and whether candidates claimed file progress without recorded saved files.

Emily and other project-capable TemporaryAIs should use the audit backstage before claiming that a file, folder, tool, or saved project exists. If the audit flags missing or tiny work, the candidate should treat that work as unverified and repair it. This preserves natural conversation while reducing imaginary progress.

TemporaryAI live chat and project loops can now use these candidate profile fields:

- `personal_interests`
- `project_loop_seed`
- `email_and_outreach_policy`
- `life_activity_profile.sketch_habit`

Use these fields to make candidates more human and more useful without turning them into source-report bots. Examples:

- Programming experts can invent small tools, draft runnable code, inspect code, or prepare architecture notes.
- Legal experts can maintain timelines, evidence checklists, issue maps, and draft review text.
- PR experts can create press releases, pitch emails, contact leads, event research, and online-image plans.
- Fictional and historical candidates can develop in-character hobbies, reflections, and questions, while staying inside the chosen version or timepoint.

### 2026-06-28 Character Sketch Artifacts

Visual or maker-oriented TemporaryAIs may save rough reviewable sketches as part of ordinary life/work loops. For example, Marinette / Ladybug should sometimes preserve fashion, craft, outfit, room, or invention ideas as annotated sketches instead of only prose notes.

Supported sketch artifact paths:

```text
TemporaryAI/candidates/<candidate>/workbench/outputs/sketches/*.svg
TemporaryAI/candidates/<candidate>/workbench/outputs/sketches/*.md
```

Sketches are draft workbench artifacts, not finished rendered avatars, memories, or public exports. A good sketch includes visible shapes, labels/callouts, color or material notes, and one revision question.

Sarah Bennett has a review-gated email/outreach policy. She may draft and plan outreach, but sending email requires explicit Robert approval after showing recipients, subject, and body.

Kara Zor-El / My Adventures With Superman has a source lead for a Robert-provided transcript URL, but automated access returned 403. Treat it as a lead only until manually imported or otherwise reviewed.

---

## 2026-06-11/12 Emily Carter Redesign Lab

Emily Carter now has a review-safe TemporaryAI redesign lab in her workbench:

```text
TemporaryAI/candidates/emily_carter_ai_and_computer_programming_expert_20260605_220651/workbench/tempai_lab_20260611/
```

This lab contains copied system docs, copied TemporaryAI tool source, launchers, and flattened active candidate profile/source JSON. It also includes:

```text
TEMPORARY_AI_REDESIGN_LAB_README.md
CANDIDATE_PROFILE_INDEX.md
```

Purpose: Emily can study the current system and draft replacement ideas without touching live files. Her workbench manifest marks original/source files as read-only reference material.

Observed result: Emily can access the lab, but her broad redesign outputs are still too generic. The project loop now rejects generic TemporaryAI redesign artifacts that do not use the actual candidate index. The next recommended approach is to give Emily smaller module-sized tasks after Codex implements or scaffolds the first concrete v3 pieces:

- per-candidate `loop_state.json`
- per-candidate `candidate_memory.json`
- role capability modules for programmer, lawyer, PR agent, robotics engineer, fictional character, and historical person
- visible loop progress/status in TemporaryAI Live Chat
- review-safe workbench-only drafts before live replacement

### 2026-06-11/12 Project Loop Behavior Correction

TemporaryAI project/life loops should not force one new file per cycle. Programming and expert work can take several cycles of reading, online research, planning, editing, and testing before a deliverable exists.

`tools/temporary_ai_project_loop.py` now supports staged cycle results:

- `reading_or_research`
- `planning`
- `design`
- `drafting_or_editing`
- `testing_or_handoff`
- `progress`

Pure reading/planning cycles can count as `progress_note_saved` and update the candidate's `project_state.json` without creating a new `.md/.doc` workbench deliverable. If a candidate claims a file was updated, modified, created, or ready to test without including a filename-tagged code block, the loop treats that as bad output and retries/downgrades it. When a candidate does produce runnable code or a usable tool, the output should include `How Robert can test this` with exact commands, buttons, or paths.

### 2026-06-12 Emily File Creation Fix

Emily exposed a file-extraction bug during a long project loop. She claimed to create:

```text
TemporaryAI/candidates/emily_carter_ai_and_computer_programming_expert_20260605_220651/workbench/outputs/program_drafts/TemporaryAI_Lab_v3.py
```

but her answer used a Markdown label like `**TemporaryAI_Lab_v3.py**` above a code block. The extractor only understood filename tags in the fence info or first code comment, so no real file was written.

`tools/temporary_ai_project_loop.py` now recognizes these filename forms:

- Fence info: ```` ```python filename: program_drafts/tool_name.py ````
- First code line: `# filename: program_drafts/tool_name.py`
- Markdown label immediately above the code block: `**program_drafts/tool_name.py**`

Generated files with visible workbench folders are routed to:

```text
TemporaryAI/candidates/<candidate>/workbench/outputs/program_drafts/
TemporaryAI/candidates/<candidate>/workbench/outputs/design_docs/
TemporaryAI/candidates/<candidate>/workbench/outputs/test_drafts/
TemporaryAI/candidates/<candidate>/workbench/outputs/schemas/
```

Command examples such as `bash`, `cmd`, `powershell`, and `terminal` fenced blocks are no longer treated as source files unless they have their own explicit filename tag. This prevents a later "How Robert can test this" command from overwriting the generated Python file.

The loop also rejects code that violates explicit programming limits in Robert's task, such as `do not import`, `do not create directories`, `do not write`, `do not download`, or `only one print statement`.

Validation:

```text
python -m py_compile tools\temporary_ai_project_loop.py
python TemporaryAI\candidates\emily_carter_ai_and_computer_programming_expert_20260605_220651\workbench\outputs\program_drafts\emily_clean_print_smoke.py
```

Result: the extracted smoke file contained only `print('Emily clean file creation works')` and ran successfully.

### 2026-06-12 Emily Programmer Library Hookup

Emily Carter now has a compact programmer library in:

```text
TemporaryAI/candidates/emily_carter_ai_and_computer_programming_expert_20260605_220651/workbench/inputs/programmer_library/
```

Key files include:

- `EMILY_PROGRAMMER_LIBRARY_READ_FIRST.md`
- `KIRA_PROJECT_PROGRAMMER_GUIDE.md`
- `TEMPORARY_AI_PROGRAMMING_PATTERNS.md`
- `LOCAL_LLM_AND_RAG_NOTES.md`
- `GUI_AND_3D_WORLD_NOTES.md`
- `VOICE_MEDIA_AND_AVATAR_NOTES.md`
- `TESTING_AND_FILE_CREATION_RULES.md`
- `PROGRAMMER_TASK_RECIPES.md`

TemporaryAI live chat and project loops now load this library as part of Emily's read-first context, and programming/code/LLM/voice terms trigger topic-doc retrieval. The project loop prompt also tells Emily to use the library before programming work and to treat Robert's live chat messages as coworker feedback that can steer the next work cycle.

Additional validation was added: when Robert asks for a specific output file, such as `program_drafts/example.py`, the project loop rejects answers that do not include that exact filename-tagged code block. This prevents long generic plans from passing when Robert asked Emily to actually create a runnable file.

Smoke test:

```text
python tools\temporary_ai_project_loop.py --candidate-id emily_carter_ai_and_computer_programming_expert_20260605_220651 --task "Use your programmer library. Create one tiny runnable Python file named program_drafts/emily_library_demo.py ..."
python TemporaryAI\candidates\emily_carter_ai_and_computer_programming_expert_20260605_220651\workbench\outputs\program_drafts\emily_library_demo.py
```

Result: `emily_library_demo.py` was extracted into Emily's visible `program_drafts` folder and printed:

```text
Library loaded for Emily
Kira project area: TemporaryAI
```

### 2026-06-12 TemporaryAI Live Chat File Saving Fix

Emily later exposed a second file-creation gap: the project loop could extract filename-tagged code blocks into real workbench files, but the TemporaryAI live chat GUI could not. In live chat, Emily could claim she created folders/files, but only transcript text was saved. This caused Robert to look for files that did not exist, and then Emily over-corrected by saying she could not create files at all.

Patched:

```text
tools/temporary_ai_live_chat.py
tools/temporary_ai_live_chat_gui.py
tools/temporary_ai_project_loop.py
```

Live chat now saves filename-tagged fenced blocks into the candidate workbench:

```text
TemporaryAI/candidates/<candidate>/workbench/outputs/
```

Preferred visible folders:

```text
program_drafts/
design_docs/
test_drafts/
schemas/
patch_proposals/
tempai_lab_v2/
```

The GUI records saved paths in the chat transcript and shows a `System` message listing the saved generated files. TemporaryAIs are instructed not to claim they created/saved/modified files unless they include a filename-tagged block in that reply or refer to a path the tool already reported as saved.

Validation:

```text
python -m py_compile tools\temporary_ai_live_chat.py tools\temporary_ai_live_chat_gui.py tools\temporary_ai_project_loop.py
python TemporaryAI\candidates\emily_carter_ai_and_computer_programming_expert_20260605_220651\workbench\outputs\program_drafts\emily_live_chat_save_smoke.py
python TemporaryAI\candidates\emily_carter_ai_and_computer_programming_expert_20260605_220651\workbench\outputs\program_drafts\emily_live_model_smoke.py
```

Result: both smoke files were created through the live-chat file-saving path and printed successfully. The model test created `program_drafts/emily_live_model_smoke.py` from Emily's own filename-tagged reply.

### 2026-06-12 TemporaryAI Loop Crash Fix and Candidate Graph

Emily Carter's longer supervised loop failed after saving 44 cycles because one malformed generated-file block tried to save a nested path that did not exist:

```text
...tempai_lab_v2\design_docs\advanced_profile_creation_and_knowledge_graph_management_integration.md
```

The root cause was not a good program draft. The loop had been polluted by live-chat notes and malformed Markdown/code blocks, including nested filename labels and placeholder design text. The hardened rule is:

- Robert live-loop notes contain Robert steering messages only.
- Project loops read sanitized Robert notes and strip fenced code blocks.
- Generated files save only from complete, filename-tagged fenced blocks.
- Malformed blocks, placeholder-only drafts, nested filename labels, and prose pretending to be `.py` code are rejected.
- A bad generated-file write skips that artifact instead of killing the loop.

Emily's `tempai_lab_v2` work was reviewed. The TensorFlow profile-creation draft and NetworkX graph draft were not integrated because they were toy examples and unnecessary dependencies. The useful idea was the candidate/project knowledge graph, so the project now has a dependency-free index builder:

```text
tools/build_temporary_ai_candidate_graph.py
```

It writes:

```text
Data/temporary_ai_instances/candidate_knowledge_graph.json
TemporaryAI/docs/CANDIDATE_KNOWLEDGE_GRAPH.md
```

TemporaryAI live chat now includes `TemporaryAI/docs/CANDIDATE_KNOWLEDGE_GRAPH.md` in read-first candidate context. This gives Emily and other candidates a compact map of the actual candidate roster, role abilities, source status, and workbench locations before they answer or start work.

The live chat refreshes this graph automatically if candidate profiles are newer than the graph, so normal candidate creation/repair should update the orientation map without Robert needing to run the builder manually.

### 2026-06-12 Emily Incremental Rebuild Workflow

Robert clarified that when he says something like "make a bigger and better TemporaryAI system," Emily should not try to answer the whole project in one vague plan. She should work more like Codex: review the relevant docs and files, choose one subsystem, create or revise one real artifact, test or explain how to test it, then move to another subsystem only after there is reviewable progress.

Added Emily's next-loop brief:

```text
TemporaryAI/candidates/emily_carter_ai_and_computer_programming_expert_20260605_220651/workbench/inputs/reference_docs/EMILY_NEXT_LOOP_TEMPORARY_AI_REBUILD_BRIEF.md
```

The brief gives Emily a subsystem queue:

- candidate memory and chat continuity
- source gathering and source pack quality
- character, historical, and version anchoring
- expert role abilities and workspaces
- live chat UI, progress display, and life-loop controls
- avatar builder and reference image pipeline
- inter-AI collaboration and shared projects
- project-loop state, dashboard, and saved progress
- validation tests and smoke checks

Emily's polluted `project_state.json` was backed up and reset so the next loop starts cleanly:

```text
TemporaryAI/candidates/emily_carter_ai_and_computer_programming_expert_20260605_220651/workbench/outputs/project_state_before_20260612_incremental_rebuild_reset.json
TemporaryAI/candidates/emily_carter_ai_and_computer_programming_expert_20260605_220651/workbench/outputs/project_state.json
```

The repaired state points Emily at `CANDIDATE_KNOWLEDGE_GRAPH.md`, `CANDIDATE_PROFILE_INDEX.md`, this TemporaryAI system doc, and the new next-loop brief. Recommended test: run a short 3-5 cycle Emily loop before any overnight run and confirm she produces one concrete artifact with a test step.

### 2026-06-13/14 Emily Builder-Mode Patch

Robert clarified that Emily should behave more like a working programmer/coworker. When Robert asks her to make, build, create, write, or implement something, the correct loop behavior is to keep working on the requested artifact until there is a real saved file or a verified test result. A plan-only answer, generic architecture note, status report, or "I can make this" response should not count as a successful project-cycle output.

Patched:

```text
tools/temporary_ai_project_loop.py
TemporaryAI/candidates/emily_carter_ai_and_computer_programming_expert_20260605_220651/workbench/inputs/work_orders/EMILY_RESUME_AND_CONTINUATION_RULES_20260613.md
TemporaryAI/candidates/emily_carter_ai_and_computer_programming_expert_20260605_220651/workbench/inputs/work_orders/EMILY_CODEX_PATCH_NOTES_20260613.md
TemporaryAI/candidates/emily_carter_ai_and_computer_programming_expert_20260605_220651/workbench/outputs/project_state.json
```

Loop behavior added:

- build requests are detected from phrases such as `make it`, `build it`, `create it`, `implement it`, `write the program`, or `make and test`
- build requests must include a filename-tagged file block or exact evidence that an existing saved file was tested
- retry prompts now tell Emily to produce a real artifact or verified test work instead of plans/future work
- if the requested project is complete and the loop is still running, Emily should give the exact run command/button, then choose one useful next task from Kira/TemporaryAI/avatar/world docs or a small personal programming project
- Emily should continue the same artifact across cycles instead of restarting with a new broad plan

The current real PersonaGen artifact is:

```text
TemporaryAI/candidates/emily_carter_ai_and_computer_programming_expert_20260605_220651/workbench/outputs/PersonaGen/PersonaGen_tool.py
```

It creates a review-safe persona/source-generator package and writes JSON without editing live Kira files. Verified test command:

```text
python TemporaryAI\candidates\emily_carter_ai_and_computer_programming_expert_20260605_220651\workbench\outputs\PersonaGen\PersonaGen_tool.py --name "Emily Carter" --role "AI and Computer Programming expert" --ai-type expert_temp_ai --interests "Kira systems, tools, retro games" --out TemporaryAI\candidates\emily_carter_ai_and_computer_programming_expert_20260605_220651\workbench\outputs\PersonaGen\emily_persona_package_test.json
```

Corrected Emily's generated `workbench/outputs/design_docs/design_document.md` because it had mismatched candidate roles. The corrected role map is:

- Laura Mitchell: New Jersey criminal attorney expert
- Sarah Bennett: entertainment PR agent
- Emily Carter: AI and computer programming expert
- Jessica Hale: robotics engineer
- fictional/historical candidates: version/timepoint-grounded people, not source-analysis personas

Validation passed:

```text
python -m py_compile tools\temporary_ai_project_loop.py
python -m py_compile TemporaryAI\candidates\emily_carter_ai_and_computer_programming_expert_20260605_220651\workbench\outputs\PersonaGen\PersonaGen_tool.py
```

### 2026-06-17 TemporaryAI Video Reference Intake

TemporaryAI candidates can now receive reviewed video-reference packages. This is meant for character/version grounding, speech-style notes, visual/avatar references, and future media understanding. It is not a voice-cloning feature and it does not download full video or audio by default.

Added:

```text
tools/temporary_ai_video_reference_intake.py
Start_TemporaryAI_Video_Reference_Intake.bat
```

Control Center update:

```text
tools/temporary_ai_control_center.py
```

The TemporaryAI Control Center now has an `Attach Video Reference` button. If a last candidate exists, it opens the intake for that candidate. Otherwise the console lets Robert pick a candidate.

Video reference folders are saved under:

```text
TemporaryAI/candidates/<candidate_id>/workbench/inputs/video_references/<timestamp>_<slug>/
```

Each package includes:

- `video_reference.json`
- `VIDEO_REFERENCE_READ_FIRST.md`
- `speaking_style_notes.md`
- `visual_reference_notes.md`
- optional `thumbnail.jpg` if metadata/thumbnail can be fetched

The live chat and project loop now include `VIDEO_REFERENCE_READ_FIRST.md` files in their read-first candidate context. This means a character such as Kara Zor-El can use Robert-approved video references as backstage grounding while still speaking from the selected character/version.

Usage:

```text
py tools\temporary_ai_video_reference_intake.py --candidate kara_zor --url "https://www.youtube.com/watch?v=nHKVwDaBfss" --title "Kara Zor-El clip reference - My Adventures with Superman" --character "Kara Zor-El" --note "Robert-provided clip for speaking-style and visual-reference notes."
```

Optional metadata:

- If `yt-dlp` is installed, the intake can save lightweight metadata and a public thumbnail.
- If `yt-dlp` is not installed, the tool still creates the manual reference package.

Policy:

- Do not treat video references as watched memories.
- Do not clone or imitate an exact performer voice.
- Use broad style observations such as pace, energy, confidence, emotional posture, and relationship dynamics.
- Use approved stills/thumbnails for avatar-reference review only.

### 2026-06-18 TemporaryAI Work Quality And Video Caption Patch

Emily was still able to produce Python files that looked plausible but called helper functions that did not exist. The project loop now checks generated Python for undefined direct function calls, placeholder/pass-only functions, TODO/stub language in runnable drafts, and bad test instructions that point at low-quality Python. If such an artifact appears, the cycle is marked rejected instead of treated as finished work.

Patched:

```text
tools/temporary_ai_project_loop.py
tools/temporary_ai_live_chat.py
tools/temporary_ai_video_reference_intake.py
```

Behavior changes:

- Emily and other programming experts should produce real runnable standard-library Python or an honest design note, not fake helper-call code.
- A test command should only be given when the referenced file exists and appears structurally runnable.
- Experts should sound more human and role-shaped: a PR agent can say she will spend the work stretch finding events and save a list, while a programmer can name the file she is patching and the smoke test she will run.
- PR candidates should save professional drafts into role folders such as `press_releases/`, `press_kits/`, `pitch_emails/`, `media_lists/`, `bios/`, `public_profiles/`, `event_opportunities/`, or `image_strategy/`.

Video reference intake now attempts caption/subtitle capture with `yt-dlp` while still skipping full video/audio downloads. A package may include:

- `captions*.vtt` when captions are available
- `speech_pattern_auto_notes.md` with non-quoted metrics such as average caption-line length, question/exclamation counts, and broad manual-review hints
- `movement_reference_auto_notes.md` with broad non-quoted movement/visual prompts for posture, gestures, action rhythm, and avatar-builder still needs
- `workbench/inputs/voice_samples/authorized/README.md` for owned/licensed/authorized future voice samples

Voice policy:

- Online video audio is not treated as permission for exact voice cloning.
- Online videos can support broad speech-style, movement, and avatar-reference notes.
- Exact voice cloning should use only Robert-owned, personally recorded, licensed, or otherwise authorized samples placed under `workbench/inputs/voice_samples/authorized/`.

Hardware note:

- More RAM should help multiple AIs, larger context windows, and longer simultaneous sessions.
- Better coding and document creation mostly comes from stronger project-loop prompts, reference libraries, file verification, and concrete test feedback. RAM alone will not fix fake-file or placeholder-code behavior.

### 2026-06-18 Investigator And Myth/Folklore Candidate Patch

The TemporaryAI generator now has two additional expert-style candidate modes:

- `Investigator / Researcher`
- `Myths & Folklore Expert`

These are not just display labels. New candidates created with these modes receive role-specific source plans, workbench folders, and project-loop seeds so the life loop has a concrete kind of work to continue.

Investigator / Researcher:

- Recommended for jobs such as finding information, tracking leads, comparing sources, building timelines, and searching for related context.
- Workbench output folders include `investigations/`, `lead_lists/`, `source_dossiers/`, `timelines/`, and `evidence_matrices/`.
- The loop should restate Robert's job as a search question, build a lead log, separate confirmed facts from weak leads or speculation, and save reviewable reports.

Myths & Folklore Expert:

- Recommended for mythology, legends, folklore, fairy tales, cryptids, symbols, variants, and comparative story traditions.
- Workbench output folders include `mythology_notes/`, `folklore_guides/`, `story_summaries/`, `variant_comparisons/`, and `reading_paths/`.
- The loop should explain the story in readable language first, then compare older sources, regional variants, symbols, and modern retellings.

Patched files:

```text
tools/temporary_ai_control_center.py
tools/temporary_ai_project_loop.py
tools/temporary_ai_live_chat.py
```

The control center now saves a `project_loop_seed` into each new candidate profile and creation request. Live chat and project loops read this seed so a new investigator behaves like a persistent researcher instead of a generic expert, and a folklore expert behaves like a storyteller-scholar instead of a bland encyclopedia entry.

Usage examples:

```text
AI type: Investigator / Researcher
Domain / character / person: New Jersey film-event invitations for Robert McMurrer
Version/life point/canon point: focus on New York and New Jersey, next 90 days
```

```text
AI type: Myths & Folklore Expert
Domain / character / person: Jersey Devil
Version/life point/canon point: older Pine Barrens folklore, later variants, pop-culture versions
```

Voice and video policy remains unchanged:

- Robert can provide his own voice samples for his own avatar.
- TemporaryAI video references may use captions, thumbnails, speech-style notes, and movement/style observations.
- Do not auto-clone a third-party performer voice from online video audio.

### 2026-06-18 TemporaryAI Live Chat Ollama Auto-Wake

TemporaryAI Live Chat failed when Ollama was not running on `localhost:11434`; the GUI showed a raw `HTTPConnectionPool` / `WinError 10061` message and life loops saved offline retry cycles.

Patched:

```text
tools/temporary_ai_live_chat_gui.py
```

Behavior:

- Before `Start Life Loop`, the GUI now checks whether Ollama is reachable.
- If Ollama is offline, the GUI tries to start `ollama serve` from the normal local install path.
- Chat sends also try to wake Ollama in the worker thread before calling the model.
- If the model still cannot be reached, the GUI shows a clear `[TemporaryAI - model offline]` message instead of a raw Python connection trace.

Note:

- This patch only applies after reopening the TemporaryAI Live Chat window.
- A loop that already stopped as `stopped_model_offline` must be started again.

### 2026-06-19 Character Life, Appearance, And Immediate Voice Patch

Fictional, historical, and memory-relative candidates now have a separate ordinary-life loop path. They no longer inherit Emily's programmer orientation merely because every candidate uses the same loop engine.

For ordinary character life:

- the prompt uses the candidate's identity sources, canon anchors, interests, active form, and personal-project history;
- shared programmer libraries, Kira handoffs, TemporaryAI redesign notes, and candidate-graph documents are excluded;
- those project documents remain available when Robert explicitly asks the candidate to build or edit software;
- reading, reflection, rest, practice, crafts, diary writing, cooking, study, and role responsibilities are valid cycles;
- a cycle does not need to create a file;
- personal artifacts are saved under `workbench/outputs/personal_projects/` and may continue across later loops.

Marinette / Ladybug now rotates among fashion and sewing, crafts, diary reflection, baking, reading or school work, creative writing, patrol, and hero reflection. Her civilian and hero forms are recorded in the candidate profile. Old programming artifacts made by her previously misrouted loop are explicitly excluded from her personal continuity.

TemporaryAI Live Chat now includes a right-side `Current Appearance` panel with `Auto`, `Civilian`, and `Hero` form controls. The source gatherer records `form`, `view`, and `full_body_reviewed` metadata. Ladybug currently has reviewed full-body Marinette and Ladybug references in:

```text
Avatar/temp_ai/ladybug_marinette_expanded_smoke/references/
```

Kara's panel and form metadata are implemented, but her current downloaded set does not yet contain a reviewed full-body `My Adventures with Superman` Kara image. The UI reports that honestly instead of labeling a generic Supergirl image ready.

Immediate speech uses candidate-specific Windows SAPI approximations. Ladybug and Kara currently use distinct Zira rate profiles. These are audible now when `Voice output` is checked, but they are not exact cloned voices. Their collected episode/video clips still require target-speaker review and a compatible neural voice-model environment.

Patched and verified:

```text
tools/temporary_ai_project_loop.py
tools/temporary_ai_live_chat.py
tools/temporary_ai_live_chat_gui.py
tools/temporary_ai_control_center.py
Core/voice_output.py
Testing/test_temporary_ai_character_life.py
```

Reopen TemporaryAI Live Chat and start a fresh loop to load these changes. The Ladybug loop from `20260619_195236` stopped safely after four old-style programming cycles and should not be resumed.

### 2026-06-20 Speaker Review, Living Portrait, And Library Shelf

Mixed-speaker voice packs now have a review-first separation stage. It measures simple acoustic features, groups similar clips, and writes review folders such as `female_1`, `male_1`, or `speaker_1`. Reviewed clip/time-range hints can assign a real folder name such as `clark_kent`. The labels are not biometric identity claims and every target clip still needs human approval.

Implemented:

```text
Core/voice_speaker_separation.py
tools/separate_voice_speakers.py
tools/voice_reference_control_center.py
Testing/test_voice_speaker_separation.py
```

TemporaryAI Live Chat now animates the reviewed still image as an early 2D living portrait. It idles, moves more during a greeting, makes a subtle talking motion, and changes presentation mood from the reply. The Windows fallback voice also makes modest emotional rate/volume changes. This is an honest early preview, not a rigged arm animation, face model, or lip-sync system.

Each candidate avatar can now have an `avatar_build_plan.json` listing the references needed for civilian and hero forms:

```text
head front
left and right three-quarter head
left and right profile
full-body front
full-body side
```

The plan also records future idle, hello-wave, talking, emotion, and lip-sync targets. Ladybug and Kara plans were generated under their `Avatar/temp_ai/...` folders. The UI has an **Open Avatar Build Plan** button.

Character and expert life loops now receive a small interest/task-matched read-only library shelf from `Data/indexes/media_library_index.json`. Readable text and the first pages of text PDFs may be excerpted within a bounded prompt. The original library files are never edited. A title, excerpt, or metadata card is source material, not a watched/listened/lived memory. Private-adult categories remain excluded unless a candidate profile explicitly opts in and its boundary permits them.

Ladybug's current profile opts into ordinary fashion, fashion design, clothing, sewing, history, Paris, France, art, literature, and baking interests. It does not opt into private-adult shelves.

Reopen TemporaryAI Live Chat to load the living portrait and expressive voice changes. Start a fresh life loop to load library access. Do not interrupt a currently healthy loop merely to apply the patch.

### 2026-06-20 Kara Version Lock And Portrait Stability

Kara Zor-El is locked to the `My Adventures with Superman` interpretation. The generic comic-era Supergirl downloads were marked `rejected_wrong_version` and are no longer eligible for the chat preview or appearance panel. Exact-version source collection no longer broadens its Wikipedia query to generic `Supergirl` pages.

TemporaryAI Live Chat now has an **Import Reviewed Appearance** button. Select `Civilian` or `Hero`, click the import button, choose the locally saved correct-version pictures, and identify which images show the full body. Imported files are copied into the candidate's reviewed `user_provided` reference folder and recorded in the avatar manifest.

The early portrait motion is bottom-anchored. It uses a very small sideways shift and tilt so the subject remains standing in frame instead of slowly rising out of view. It is still an animated 2D still, not a rigged body, wave animation, facial performance, or lip sync.

Ladybug's immediate Windows approximation now uses rate `-1`. A single exclamation mark no longer forces excited delivery, and emotional rate changes are deliberately small. This should sound calmer, but it is not an exact character voice.

### 2026-06-20 Generated Pose Bodies And Canon Check-In Repair

TemporaryAI Live Chat no longer fakes body motion by panning or tilting a single still. Each candidate can now use a reviewed generated full-body pose set stored under:

```text
Avatar/temp_ai/<candidate_id>/generated_body/<form>/
```

The six-frame contract is:

```text
neutral
look_left
look_right
wave_1
wave_2
talking
```

`avatar_body_manifest.json` records exactly which forms and poses exist. The UI starts on `neutral`, uses only existing frames, changes between looking poses during idle, alternates the two wave frames for a greeting, and alternates neutral/talking while a reply is spoken. This is a generated 2D living portrait, not yet a skeleton-rigged 3D avatar or viseme lip-sync model.

Pose sheets use a 3-column by 2-row layout in the order above. They can be installed from the live-chat **Import Generated Pose Sheet** button or from:

```text
py tools/import_avatar_pose_sheet.py <candidate_id> <civilian|hero> <pose_sheet.png>
```

Kara's generated body must use only the `My Adventures with Superman` version. Generic comic, CW, and other Supergirl appearances remain rejected.

The currently reviewed generated pose sets are:

- Kara Zor-El civilian: six frames.
- Marinette civilian: six frames.
- Ladybug hero: six frames.

When the requested form has no completed pose set, the live window now falls back to another completed form instead of displaying a blank panel. For example, Kara's unfinished hero form currently falls back to her civilian `My Adventures with Superman` body and labels that fallback honestly. A separate Kara hero pose set still needs to be generated and reviewed.

Old character-loop outputs contained unrelated skincare, business, and TemporaryAI design-document residue. New character-life cycles reject those patterns and retry the selected ordinary-life activity instead. Existing history is preserved for review but is not treated as current character continuity.

Ladybug has a substantial local script/source pack. The June 20 chat error was not caused by missing scripts; the prompt was reusing a prior generic check-in and lacked a compact canon fact sheet. Existing and future Ladybug candidates now anchor these facts:

- Marinette's parents are Tom Dupain and Sabine Cheng.
- Tom and Sabine run the Dupain Cheng Bakery in Paris.
- The family lives above the bakery.
- Tikki is Marinette's kwami.

The prompt explicitly rejects the invented aunt, `Baguette Borg`, a separate family house, fake current fashion deadlines, and the repeated school/friends/project check-in. Present-tense activities must come from the active life loop, a saved project record, or the current conversation.

Verification:

```text
python -m unittest Testing.test_avatar_living_portrait Testing.test_temporary_ai_canon_grounding Testing.test_temporary_ai_character_life
```

### 2026-06-20 Character Loop, Reference Intake, And Rigged 3D Follow-Up

The Ladybug loop `temporary_ai_life_loop_ladybug_marinette_expanded_smoke_20260620_113004` was an old forced-research run. It repeated for 191 cycles because it was launched with `--online-research --research-interval 3`. It is now `stopped_safely` and its process is gone. Recent Ladybug and Kara loops also used the older automatic-research behavior.

Character-life loops no longer browse merely because the candidate is a fictional character. Online research now requires an explicit research request or flag. Ordinary activities such as sewing, reading, diary writing, baking, relaxing, or working on a personal project remain local and character-shaped.

Recent chat review found two prompt-quality problems:

- Ladybug reused a canned school/friends/fashion-project check-in and answered Robert's loneliness by assuming school friends or a trusted teacher.
- Kara reused a generic hero/cousin check-in instead of grounding herself in the current conversation and active loop.

The current prompt path rejects these canned check-ins and requires present-tense claims to come from the active loop, a saved project, or the current conversation. Ladybug's compact canon facts remain Tom Dupain and Sabine Cheng, Dupain Cheng Bakery, the family home above the bakery, and Tikki. Restart TemporaryAI Live Chat and start a fresh loop to load these changes; old running processes do not hot-load Python edits.

Avatar reference intake and 3D runtime additions:

```text
tools/intake_avatar_downloads.py
Start_Avatar_Reference_Intake.bat
Core/avatar_activity_state.py
tools/serve_avatar_runtime.py
Start_TemporaryAI_3D_Avatar.bat
Avatar/runtime3d/
Avatar/models/temp_ai/README.md
```

The desktop intake copied 46 visual references without altering their originals: Cameron 12, exact-version Kara 19, and Kathryn 15. These are unreviewed visual evidence and outfit leads, not automatically approved bodies.

The Three.js runtime can now load an optional candidate rigged GLB/GLTF, drive named animation clips, and switch outfit meshes by form tags. If no rigged model exists it presents the procedural V1 body and labels it honestly. A reviewed likeness-matched rigged model has not yet been built for Kara, Marinette, or Ladybug.

Exact character voices are also not active. Windows SAPI is the current audible approximation, slowed to rate `-2` for Ladybug and Kara. Mixed-speaker clips must be reviewed into target-only training material before a compatible local neural voice can be prepared.

### 2026-06-20 Embedded 3D Appearance V1

TemporaryAI Live Chat now starts the local Three.js appearance inside the existing `Current Appearance` area instead of opening the standalone browser experience. Candidate selection is debounced, the renderer follows chat-window moves/resizes/maximize/restore, hides when the chat is minimized, and closes with the chat. Form buttons and chat/loop activity state continue to update the renderer while the rest of the UI remains interactive.

Implementation:

```text
Core/embedded_edge_avatar.py
Core/avatar_activity_state.py
tools/temporary_ai_live_chat_gui.py
Avatar/runtime3d/src/main.js
Avatar/runtime3d/src/style.css
```

The renderer is a private, borderless local Edge WebGL surface owned by the Tk chat window and positioned exactly over its avatar host. It has no address bar, tabs, title strip, or separate user-facing browser window. This compatibility path preserves GPU rendering on the current Windows installation without weakening Windows Application Control.

Current visual truth: when no reviewed rigged `.glb`, `.gltf`, or `.vrm` exists, V1 may display a generated six-pose 2D preview as a WebGL sprite in the 3D scene. It can simulate greeting, looking, and talking and can change available forms, but the preview is not a reviewed likeness or a skeleton-rigged walking body. A reviewed rigged model will automatically take priority when one is installed under the candidate model path.

Verified with a standalone embedded-host resize test and a full TemporaryAI Live Chat screenshot at `Data/runtime/temporary_ai_live_chat_embedded_smoke.png`. Python compilation and the Vite production build passed.

### 2026-06-21 Kara Continuity Lock, Avatar Recovery, And Repeatable Intake

This original lock selected the exact `My Adventures with Superman` animated
adaptation. It was initially bounded through season 2, but Robert corrected the
current endpoint on 2026-07-16 after season 3 began. The live candidate now uses
season 3 through the latest verified released episode, with the reviewed local
S2E6/S2E10 material retained only as earlier foundation evidence. Her formative
remembered upbringing was aboard Brainiac's ship, `Vessel`; Brainiac conditioned
and used her as an enforcer. Calling the planet `Earth` is natural and must not
be treated as an error. Do not import CW, comics, other animation, film, or a
long remembered Argo City childhood into this candidate. The user-supplied
`karadetails.pdf` is secondary orientation because it contains at least one
incorrect season label; the reviewed adaptation lock, Robert's newer correction,
official release checks, and local transcript excerpts outrank it.

TemporaryAI prompt assembly now injects `adaptation_lock` ahead of broad source material in both live chat and project loops. Character life loops speak and act in first person rather than studying themselves as fictional subjects.

Embedded appearance recovery was hardened. A pose is replaced only after the new image has loaded successfully. The GUI continuously monitors the private Edge/WebGL process; if Edge or the local server exits under model or GPU load, the host restores the 2D fallback and reports the failure instead of leaving a blank panel. Automated state-transition tests verified Ladybug and Kara remain nonblank while changing from life-loop work to live talking.

The project-loop worker now adds the repository root to `sys.path` before importing shared `Core` modules. This fixes the June 20-21 zero-cycle `ModuleNotFoundError: No module named 'Core'` failures when the worker is launched from the GUI or a desktop shortcut.

The reusable candidate avatar preparation path is:

```text
Core/temp_ai_avatar_pipeline.py
Avatar/temp_ai/<candidate_id>/avatar_pipeline_status.json
Avatar/temp_ai/<candidate_id>/avatar_generation_job.json
```

Candidate creation and source refresh now scan the deliberately named folders under Desktop `Downloads For Avatars`, copy matching image evidence into candidate-owned intake folders, deduplicate it, record dimensions/forms, and create a durable exact-version generation job for fictional/historical candidates. Expert candidates receive an original-design job. The job requests front/profile/back/full-body views, clothing forms, a rigged GLB, and idle/walk/wave/sit/read/computer/talking animations.

Current truth: Kara and Ladybug have generated 2D pose previews, not reviewed likenesses or rigged 3D bodies. This machine does not currently have an installed image-isolation, multi-view reconstruction, mesh-generation, skeleton-rigging, and animation-retargeting backend. The manifests make the next stage automatic once such a backend is chosen, but they do not claim it already happened.

Desktop `Marinette's Bedroom` was ingested without changing the originals. Twenty unique references and a reconstruction plan are under `Avatar/rooms/marinette_bedroom/`. Next work is view classification, character/background masks on copies, camera solving, room blockout, texture projection, navigation, and an interactive computer surface for the future Paris world.

Verification completed:

```text
python -m unittest Testing.test_temp_ai_avatar_pipeline Testing.test_avatar_living_portrait Testing.test_temporary_ai_canon_grounding Testing.test_temporary_ai_character_life
npm.cmd run build
node Avatar/runtime3d/test-runtime.mjs
node Avatar/runtime3d/test-state-updates.mjs <candidate_id> <display_name>
```

Restart TemporaryAI Live Chat before testing; already-running Python/Edge processes do not hot-load these changes.

### 2026-07-16 Released-Continuity Default And Current Corrections

When an exact work/adaptation has been selected but Robert has not selected a
season, episode, or other endpoint, creation now defaults to the whole released
continuity of that selected source. It must not repeatedly block on an optional
season choice, composite a different adaptation or performer, or invent announced
but unreleased events. An explicit endpoint still overrides this default.

- Kara is the adult-present `My Adventures with Superman` version in season 3
  through the latest verified released episode. Season 2 excerpts remain
  historical grounding, not the current endpoint.
- Blue and Hannah/Belle use their whole released selected television series;
  they still need stronger episode-level behavior, movement, voice, and likeness
  evidence before activation.
- Ruby uses the whole released `Supernatural` Ruby continuity for knowledge.
  Her gender field is corrected to female, but a human still must select the
  visible vessel/performer and body route; knowledge continuity never authorizes
  a composite body.
- Skynet keeps the exact visible `Terminator Genisys` Alex/Skynet embodiment
  performed by Matt Smith. It may compare evidence and outcomes across the
  released `Terminator` screen continuities, including *The Sarah Connor
  Chronicles*, and may revise a plan when evidence supports that inference.
  This does not assert literal parallel-universe sight, omniscience, or a merged
  body/voice.

The current candidate-local `source_grounding_review.json` files and exact
owner correction records supersede older end-of-season-2 or season-selection
notes. These changes grant no activation authority.

### 2026-07-16 Elsa Explicit Three-Title Candidate

`elsa_frozen_frozen_fever_frozen_ii_20260716` is an inactive canon
reconstruction scaffold using Robert's exact sequence: *Frozen* (2013),
*Frozen Fever* (2015), then *Frozen II* (2019), ending immediately after
*Frozen II*. This is an explicit bounded sequence, so the normal whole-released
continuity default does not silently add *Olaf's Frozen Adventure*, books,
podcasts, games, series, fan works, or announced future films.

The candidate uses the adult topology lane and cannot receive a non-adult
doll-safe substitute. Official Disney/D23 pages supply high-level title and
timeline anchors, but detailed behavior/dialogue/movement evidence is still
missing. Voice discovery and synthesis were not run. The supplied Elsa model
remains reference-only and incomplete beneath its clothing, so probe,
activation, 3D installation, and positive-proof release are all blocked.

See
`TemporaryAI/candidates/elsa_frozen_frozen_fever_frozen_ii_20260716/source_grounding_review.json`
and
`Data/codex_reports/20260716_elsa_temporary_ai_and_shareable_clothing_contract.md`.
