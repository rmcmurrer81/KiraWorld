# Session Zero Kickoff Document

> Historical initialization note: the build-order and identity rules below
> remain useful, but the stated pre-GPU / 16 GB development stage is obsolete.
> `HANDOFF_FOR_NEXT_CODEX_SESSION.md` is the current dated authority.

## Project Name

Kira 2.0

## Project Goal

Build a staged AI companion system with persistent identity, grounded memory, emotional continuity, relationship tracking, privacy states, source-library processing, temporary AI creation, and future world/avatar/robot embodiment support.

This is not a generic chatbot project.

Kira and Lisa are separate AI individuals in the system, with separate identities, memories, preferences, moods, and relationship states.

## Current Development Mode

Pre-GPU / pre-full-agent build.

The first working system should be lightweight enough to run before the final GPU upgrade.

## Primary Build Philosophy

Identity first.
Memory grounding second.
Feature expansion third.

Do not build advanced features before the core identity and memory rules work.

## Initial Tech Stack

Preferred early stack:

```text
Python
JSON files for early schemas/state
Markdown docs for rules/specs
Local file storage first
Ollama/local model layer later
Optional API model adapter later
pytest or unittest for tests
```

Avoid overengineering too early.

Do not require GPU for early stages.

## First Real Milestone

Stage 1: Text-only Kira core.

The first milestone is not voice, avatars, worlds, robots, or temporary AIs.

The first milestone is:

```text
Kira can respond in text while staying grounded in identity and memory rules.
```

## Stage Order

Use this order unless Robert explicitly changes it:

```text
Stage 0: Document setup
Stage 1: Text-only Kira core
Stage 2: Memory system
Stage 3: Emotional continuity
Stage 4: Relationship system
Stage 5: Privacy and state manager
Stage 5.5: Stability checkpoint
Stage 6: Lisa integration
Stage 7: First TemporaryAI activation test: Ladybug
```

## Non-Negotiable Rules

- Do not invent memories.
- Do not treat prompts as memory.
- Do not treat conversation logs as trusted memory.
- Do not treat source files as personal memory.
- Do not merge Kira and Lisa.
- Do not build from old Kira files as the active foundation.
- Do not overwrite canon with fanfic.
- Do not activate permanent AIs without governance rules.
- Do not skip the stability checkpoint before Lisa integration.
- Do not give Kira or Lisa unrestricted file access without permission layers.

## Source Library Rule

The source library is:

```text
Kira/Data/library/
```

This is used for two different purposes:

1. Kira/Lisa reading mode.
2. TemporaryAI source processing.

These are not the same.

Reading source material may produce reading notes, curiosity, questions, and interests.

TemporaryAI processing may produce character evidence, source indexes, canon profiles, fanfic variant notes, and conflict flags.

Neither automatically becomes Kira or Lisa personal memory.

## Old Kira Rule

Old Kira files are legacy reference only.

They may be inspected for:
- useful helper code
- interface ideas
- avatar behavior references
- lessons learned
- bugs to avoid

They must not define current canon unless current documents explicitly say so.

## Stage 1 Definition of Done

Stage 1 is done only when:

- Kira identity loads from file.
- User can type to Kira.
- Kira can respond using the chosen model adapter or stub adapter.
- Memory retrieval exists, even if simple.
- Kira can say she does not know/remember when memory is missing.
- Conversation logs save.
- Logs are not automatically promoted into trusted memory.
- Anti-hallucination tests pass.

## Development Style

Build small, testable pieces.

Prefer simple working code over complex unfinished architecture.

After each stage:
- summarize what changed
- list files modified
- run tests
- update logs
- stop at the next gate for review
