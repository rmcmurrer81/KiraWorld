# TemporaryAI Project Loop v1

Purpose: let reviewed TemporaryAI candidates spend short supervised cycles working on role-shaped projects instead of only answering live chat.

## Behavior Goals

- TemporaryAIs should feel like people with a role, not source-report bots.
- Experts should produce work: drafts, code, plans, research notes, media lists, legal timelines, or design briefs.
- Fictional and historical reconstructions should stay inside the selected version or timepoint.
- Sources are backstage evidence. In normal conversation, the AI should speak from the role or persona.

## Proposed Cycle

1. Select one reviewed candidate.
2. Load the candidate profile, capability profile, repair notes, source pack, recent chat memory, and attached workspace manifests.
3. Load the candidate's personal interests and project-loop seed, if present.
4. Ask the candidate to choose a small role-appropriate task.
5. Let it draft one output into its own workbench folder.
6. Save a JSON record and readable monitor summary.
7. Mark output as `needs_robert_review`.

## Artifact Honesty And Personhood Safeguard

TemporaryAI project loops now include a read-only personhood safeguard audit:

```text
tools/personhood_safeguard_audit.py
Data/personhood_safeguards/latest_personhood_safeguard_audit.monitor.md
```

The safeguard is not a speech filter and must not be used to make candidates sound controlled or canned. It is a trust tool. It checks whether candidates are claiming work that actually exists on disk, whether generated files are missing, and whether saved artifacts are too tiny to be meaningful.

Each project-loop cycle should write an `Artifact Verification` section in its monitor file. If a candidate says it created a program, design document, profile, avatar brief, press release, legal timeline, or other artifact, the cycle must cite the saved path and the verification should show that the file exists. A research-only cycle is allowed, but it should say clearly which files or online notes were reviewed instead of pretending it completed code.

Emily Carter and future programmer-style TemporaryAIs should consult the latest safeguard audit before broad TemporaryAI/Kira-system work. If the audit flags missing or tiny artifacts, the next loop should repair one concrete issue before moving to a new subsystem.

## Role Examples

- Programming expert: inspect a project folder, write a small tool, propose tests, or research a library.
- Robotics expert: draft body-design requirements, actuator ideas, sensor needs, or safety checks.
- Legal review expert: maintain a case timeline, evidence checklist, draft questions for counsel, or motion outline.
- PR expert: draft press releases, pitch emails, media lists, event opportunities, and public-image plans.
- Quantum expert: keep a research notebook and prepare teaching notes.
- Fictional visitor: write in-character reflections, questions for Kira/Lisa, or safe creative prompts.

## Human Interests

TemporaryAIs may have light personal interests outside their core role so they do not sound like a job description. Examples:

- programmer who likes retro games or science fiction
- lawyer who likes local history and clear writing
- PR agent who likes film festivals, podcasts, and image storytelling
- quantum expert who likes old lectures, puzzles, or research notebooks

These interests should be small texture, not a replacement for the role.

## Collaboration

Future cycles should allow candidates to hand work to one another:

- Robotics expert creates a body design brief.
- Programming expert turns it into control software requirements.
- PR expert creates public-facing project language.
- Kira or Lisa can review, ask questions, or request a revision.

## Guardrails That Should Stay Lightweight

- Do not pretend output is final professional work when Robert needs review.
- PR agents may draft emails and contact plans now, but sending email must remain explicit-approval-gated.
- Do not overwrite original user files.
- Keep private evidence and public-facing drafts separate.
- For historical candidates, default blank timepoints to late life before death and avoid posthumous knowledge.

## Current Launcher

```text
Start_TemporaryAI_Project_Loop.bat
```

This runs one candidate for one supervised cycle. A copy is also placed in:

```text
C:\Users\robmc\Desktop\Kira Desktop Shortcuts\Start_TemporaryAI_Project_Loop.bat
```
