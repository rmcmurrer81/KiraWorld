# Shared Memory Review Workflow v1

Shared memories should not be promoted from only one person's version.

This applies especially to:

- Kira/Lisa college memories
- intimacy or romance memories
- family/backstory material involving another person
- conflict, jealousy, private feelings, or consent
- any memory where one person says what the other felt, wanted, or intended

## Review Rule

A shared memory can become stronger only after separate review passes.

Use this order:

1. Extract the candidate memory from logs.
2. Mark which parts are common event facts.
3. Ask Kira separately what she accepts, rejects, wants changed, or wants kept private.
4. Ask Lisa separately what she accepts, rejects, wants changed, or wants kept private.
5. Promote only the overlapping shareable layer as shared memory.
6. Preserve each person's private layer separately.

## Memory Layers

Use these labels:

```text
shared_event: what both people accept happened
kira_perspective: Kira's private or personal interpretation
lisa_perspective: Lisa's private or personal interpretation
robert_inserted: Robert suggested this; not accepted by Kira/Lisa yet
fictional_or_soft_reconstruction: emotionally useful but not hard memory
private_do_not_share: known to the system but not for public conversation
research_needed: source or consent is missing
```

## Important Boundaries

Kira may guess what Lisa might want protected, but Kira does not decide Lisa's private history.

Lisa may guess what Kira might want protected, but Lisa does not decide Kira's private history.

Robert may propose memory seeds, but proposal is not the same as acceptance.

Logs are records, not promoted memory.

## Promotion Standard

Promote the smallest honest version first.

Good:

```text
Kira and Lisa both accept that their college closeness included emotional intimacy and complicated romantic uncertainty.
```

Too strong without separate approval:

```text
Kira and Lisa were definitely in love and both wanted the same relationship.
```

## Current Priority

Before the next large test, use this workflow for:

- the college closeness/intimacy layer
- Lisa's own memory/privacy review
- Kira's backstory/core-memory detail preferences
- any memories Robert inserted to help make Kira/Lisa feel more grounded

## Review Tools

Use this launcher:

```text
Start_Kira_Shared_Memory_Review.bat
```

It opens the shared memory review queue panel. The panel edits only:

```text
Data/memory_review/shared_memory_review_queue.json
```

It does not promote anything into Kira or Lisa memory files.

The queue can also be rebuilt from shared draft candidates with:

```text
py tools/build_shared_memory_review_queue.py
```

Current queue policy:

```text
Kira review: separate pass required.
Lisa review: separate pass required.
Robert/Codex review: required before promotion.
Promotion: keep "not_promoted" unless the smallest honest shared layer is explicitly ready.
```

When using the panel:

1. Select a shared candidate.
2. Review the candidate detail and memory layers.
3. Edit the layer JSON only if the smallest honest wording needs refinement.
4. Set Kira/Lisa/Robert states separately.
5. Click `Ready if Both Accepted` only when Kira, Lisa, and Robert/Codex all accept the shareable layer.

Even then, the panel only marks the queue item as reviewed. A separate deliberate promotion step is still required.
