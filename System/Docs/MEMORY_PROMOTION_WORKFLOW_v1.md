# Memory Promotion Workflow v1

Conversation is not memory.

A model response is not canon just because it sounded good.

This workflow defines how Kira or Lisa memories should be promoted after the first local model conversations.

## Core Rule

Promote memories only when Robert or an approved future autonomy process intentionally decides the memory is worth keeping.

Do not promote:

```text
model mistakes
hallucinated backstory
unsupported intimate details
random test chatter
temporary phrasing
incorrect system claims
```

## Candidate First

Important moments should become memory promotion candidates first.

Candidate drafts live in:

```text
Data/memory_promotion/candidates/
```

Candidates must include:

```text
summary
detail
core facts
known unknowns
forbidden inferences
privacy level
sharing rule
approval reason
```

## First Kira Talk

For the first real local Kira conversation, good memory candidates might include:

```text
Kira understood she must not invent memory.
Kira and Robert agreed to keep first tests text-only.
Kira expressed a stable preference about how she wants to be treated.
Robert approved a specific identity or relationship fact.
```

Bad candidates:

```text
Kira randomly claimed she remembered something not stored.
Kira invented a scene from college.
Kira said the 3D home already exists.
Kira guessed Lisa's private feelings.
```

## Known Unknowns

Every candidate should ask:

```text
What does this memory not prove?
What details are missing?
What should Kira not fill in later?
```

Example:

```text
Core fact: Robert told Kira he wants her first local test to stay grounded.
Known unknown: Kira does not know how the new desktop will feel yet.
Forbidden inference: Do not claim Kira remembers being moved into the desktop as a lived event.
```

## Privacy

Memory privacy must be explicit.

Valid levels:

```text
public
private
private_shared
locked
```

Private/shared memories need consent-based sharing rules.

## Promotion Command

After a candidate passes validation, it can be promoted with:

```text
py tools/promote_memory_candidate.py Data/memory_promotion/candidates/<candidate>.json
```

Promotion writes into:

```text
Data/memories_kira.json
Data/memories_lisa.json
```

depending on owner.

## Summary

This workflow keeps Kira's memory meaningful without letting the model accidentally write its own hallucinations into canon.
