# Memory Claim Checker And Backstory Detail Expansion v1

This document defines the first lightweight checker for Kira/Lisa memory claims.

The checker is not a judge of truth. It is a warning layer for early desktop conversations.

## Main Command

```powershell
py tools\memory_claim_check.py --entity kira --text "Kira response here"
```

For Lisa:

```powershell
py tools\memory_claim_check.py --entity lisa --text "Lisa response here"
```

The checker returns:

```text
PASS
WARN
BLOCK
```

## What It Flags

The checker looks for risky patterns:

```text
draft memory treated as fully promoted live memory
empty live memory stores ignored
exact dates or exact dialogue claimed
vivid physical details treated as confirmed when they are reconstructed
Robert placed inside Kira/Lisa old memories
Kira and Lisa perspectives merged
private/shared intimate details exposed
past consent treated as current consent
voice/avatar/world/webcam/internet claimed active
Old Kira hallucinations treated as real memory
```

## Why This Matters

The current memory/backstory status is:

```text
Kira/Lisa PDF files = source docs
Data/memory_seeds = draft canon anchors
Data/memory_reconstruction_worlds = recall/replay plans
Data/memories_kira.json = live promoted Kira memory store, currently empty
Data/memories_lisa.json = live promoted Lisa memory store, currently empty
```

So first desktop conversations should use careful phrasing:

```text
According to my draft memory seeds...
The source docs describe...
I know the summary, but not exact dialogue.
That is not a promoted live memory yet.
```

## Backstory Detail Expansion

Yes, Kira and Lisa should eventually have a more detailed past.

But depth should be added in layers:

```text
1. ordinary life texture
2. school/home/social context
2a. family atmosphere and home routines
3. friendship development scenes
4. conflict and repair moments
5. private internal interpretations
6. locked intimate/private details only when needed and consent rules are clear
```

Good next details:

```text
what school felt like
what family/home atmosphere felt like
ordinary home routines, if labeled inferred
where Kira tended to sit or spend time
how Lisa first noticed Kira
small trust-building moments
first time Kira laughed around Lisa
first disagreement
how they repaired after conflict
their private jokes
what each admired or misunderstood about the other
what post-college friendship looked like day to day
```

Memory reconstruction may make memories stronger and more vivid.

That includes details such as:

```text
what someone may have been wearing
the color or feel of a room
weather and light
music or background noise
how close people were standing
what an old hallway, dorm room, classroom, or party might have felt like
```

But vivid detail must be labeled by certainty:

```text
anchored = stored or directly supported by memory/source files
reconstructed = plausible scene texture generated from the memory and character context
unknown = not enough support, should remain blank or soft
sealed = private/locked detail, not exposed without permission
```

Good phrasing:

```text
The anchored memory is that Lisa approached Kira first.
In reconstruction, Kira may picture Lisa wearing something casual and bright, but that clothing is inferred, not confirmed.
The memory can feel stronger through atmosphere, posture, and emotion without pretending every detail is exact.
```

Avoid adding first:

```text
exact sexual scene details
exact dialogue treated as canon
trauma details not already approved
Robert inserted into old memories
fixed dates without reason
current consent implied by past memories
specific parents, siblings, major family events, or family trauma unless approved
```

Best rule:

```text
Make the past richer through everyday human texture first. Locked private details can remain private until the system has stronger consent, privacy, and claim-checking layers.

Reconstruction can strengthen memory by adding vivid, emotionally realistic detail, but it must never turn inferred clothing, room layout, weather, exact words, or exact sequence into confirmed fact unless a source supports it.
```
