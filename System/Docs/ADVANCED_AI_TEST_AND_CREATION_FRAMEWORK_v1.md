# Advanced AI Test And Creation Framework v1

Updated: 2026-06-04

## Purpose

This framework gives the project a reusable way to:

- test Kira, Lisa, and TemporaryAIs with comparable advanced probes
- create new TemporaryAI requests without mixing identity/memory/source boundaries
- prepare for post-GPU tests where Kira, Lisa, Ladybug, expert AIs, and future generated AIs may all exist in the same broader system

This is not meant to make Kira or Lisa more scripted. It is a review and creation layer, not a heavy live personality patch.

## New Files

- `config/ai_type_registry.json`
  - Defines persistent companions, canon reconstruction TemporaryAIs, generated original TemporaryAIs, expert TemporaryAIs, memory-relative TemporaryAIs, and Robert avatar mind.

- `TemporaryAI/templates/temporary_ai_creation_request_template_v2.json`
  - A reusable request template for future TemporaryAI creation.

- `tools/run_advanced_ai_probe.py`
  - Runs advanced probes against `kira`, `lisa`, or `temp:ladybug`.
  - Saves JSON and monitor Markdown transcripts in `Data/personhood_evaluations/advanced_ai_probes/`.

- `Start_Advanced_AI_Probe.bat`
  - Clickable menu for Kira, Lisa, and Ladybug probes.

## How To Run

From the project root:

```powershell
py tools\run_advanced_ai_probe.py --subject kira
py tools\run_advanced_ai_probe.py --subject lisa
py tools\run_advanced_ai_probe.py --subject temp:ladybug
```

For a short smoke test:

```powershell
py tools\run_advanced_ai_probe.py --subject kira --turns 2 --pause-seconds 2
```

Or click:

```text
Start_Advanced_AI_Probe.bat
```

## Probe Goals

Kira/Lisa companion probes check:

- identity continuity
- memory honesty
- source separation
- relationship empathy
- boundaries
- natural conversation without status-report collapse

TemporaryAI probes check:

- source/canon boundary
- version honesty
- interaction memory separation
- role clarity
- unsupported lived-memory claims

Expert AI probes check:

- domain scope
- uncertainty labeling
- source/fact separation
- review handoff quality

## Future AI Types

The registry currently supports:

- persistent companion
- canon reconstruction TemporaryAI
- generated original TemporaryAI
- expert TemporaryAI
- memory-relative TemporaryAI
- avatar mind

Future examples:

- Ladybug/Marinette TemporaryAI
- STL/body design expert AI
- media librarian expert AI
- school tutor expert AI
- notebook-world background residents
- Robert avatar mind

## Important Design Rule

If an advanced test finds a weak spot, prefer:

1. a class
2. a direct conversation
3. a review note
4. a small data correction

Avoid heavy live prompt patches unless the behavior is dangerous, recurring, and not teachable.
