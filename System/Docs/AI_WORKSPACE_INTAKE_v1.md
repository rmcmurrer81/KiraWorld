# AI Workspace Intake v1

Purpose: let Kira, Lisa, TemporaryAI candidates, and later expert AIs work with local folders in a reviewed way.

Launcher:

```text
Start_AI_Workspace_Intake.bat
```

Main tool:

```text
tools/ai_workspace_intake.py
```

## What It Does

The tool scans a folder and creates a workspace under:

```text
Data/ai_workspaces/<owner>/<workspace_id>/
```

It writes:

```text
workspace_manifest.json
README.md
extracted_text/
outputs/
```

Original files are not modified.

## Supported v1 Inputs

```text
txt / md / json / csv / log / html / py / bat / ps1
pdf with selectable text
images through pytesseract OCR when possible
zip archives as inventories, with small text excerpts when possible
```

Large files are skipped by default rather than loaded into the model.

## TemporaryAI Attachment

If Robert supplies a TemporaryAI candidate id, the workspace manifest is attached to:

```text
TemporaryAI/candidates/<candidate_id>/temporary_ai_profile.json
TemporaryAI/candidates/<candidate_id>/creation_request.json
```

TemporaryAI live chat then loads the workspace excerpts into the candidate context.

## Writing Drafts

TemporaryAI live chat supports:

```text
/save filename.md
```

This saves the last candidate reply into the first attached workspace's `outputs/` folder.

Examples:

```text
/save application_answer_draft.md
/save motion_outline_draft.md
/save chapter_01_scene_draft.md
```

## Boundaries

Workspace files are source evidence, not memory.

AI-written outputs are drafts for Robert review.

For legal, medical, financial, admissions, or other high-stakes uses:

```text
The AI may summarize, organize, explain, and draft reviewable text.
The AI is not a licensed professional.
Final decisions and filings require qualified human review.
```

## Future Upgrades

Planned:

```text
GUI workspace picker
workspace manager panel
better docx support
better PDF OCR pipeline integration
per-workspace permissions
Kira/Lisa direct workspace loading
project writing workbench for Kira's books
legal document bundle mode for Laura-style experts
school/application counselor mode
```
