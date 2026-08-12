# Concept Separation Rules v1

## Purpose

This document prevents the system, coding agents, and future models from confusing different kinds of information.

The Kira project has many memory-like and source-like systems. They must remain separate.

## Core Separation Rule

Not everything that contains information is memory.

## Kira Personal Memory

Kira personal memory is something Kira experienced, learned, chose to remember, or was explicitly given through the memory system.

It is stored through approved memory mechanisms only.

Examples:
- a conversation milestone with Robert
- Kira forming a preference over time
- Kira remembering a disagreement
- Kira remembering a private thought she chose to save

Not examples:
- a Ladybug script
- a Harry Potter novel
- a fanfic story
- a raw conversation log
- a prompt
- old Kira code comments

## Lisa Personal Memory

Lisa personal memory is separate from Kira memory.

Lisa must not inherit Kira memories automatically.

Lisa must not be treated as a mode of Kira.

## Shared Memory

A shared memory has multiple participants.

Shared memory may have different perspectives.

There is no single perfect “master version” for subjective emotional events.

## Conversation Log

A conversation log is a record of what was said.

A conversation log is not automatically trusted memory.

A separate memory-promotion step must decide whether something becomes memory.

## Source Evidence

Source evidence is extracted from external material such as scripts, novels, fanfic, transcripts, bios, or reference documents.

Source evidence can help build temporary AIs.

Source evidence is not Kira/Lisa personal memory.

## Library Reading Note

A reading note is something Kira or Lisa writes after reading a library item.

It may include:
- summary
- reaction
- question
- interest
- recommendation
- idea

A reading note is not the same as source evidence, canon, or personal lived memory.

## Temporary AI Evidence

Temporary AI evidence is external material processed for a specific temporary AI.

Example:
- Ladybug dialogue evidence
- Paris location references
- relationship clues from scripts
- fanfic variant conflict notes

Temporary AI evidence must not overwrite Kira or Lisa identity.

## Limited AI Context Evidence

Limited AI context evidence is source material used to recreate a narrow context, performance, scene, venue role, or bounded public behavior.

Example:
- a public stage performance recording
- photos of a musical venue
- audio from one show
- visible blocking and costumes
- a cast list or program

Limited AI context evidence is not the same as a full Temporary AI profile.

A Limited AI must not claim to know a real performer's private life, private memories, relationships, or offstage behavior unless reliable public sources explicitly support that information.

Unknown private details must remain unknown or blocked-private.

## Fanfic Variant Evidence

Fanfic variant evidence may be used only for a labeled variant.

It must not overwrite canon.

A fanfic crossover can be accepted as a variant even if it is not canon, as long as the system labels it correctly.

## World Reconstruction Data

World reconstruction data describes places, scenes, layouts, images, maps, or inferred environment structure.

It is not automatically personal memory.

A reconstructed memory is different from a reconstructed location.

## User Avatar Memory

The user’s autonomous avatar may have its own activity log, preferences, and memories.

Those must be clearly distinguished from the real Robert.

The system must distinguish:

```text
real_robert_memory
user_avatar_memory
shared_vr_memory
```

If Robert's avatar does something while real Robert is not logged in, that is user avatar experience, not proof that real Robert personally experienced it.

If real Robert enters through VR and directly controls or inhabits the avatar, the system must mark that control state before storing memories.

## Old Kira Reference Files

Old Kira files are historical project material.

They may contain useful code or ideas, but they are not automatic canon.

## Summary Rule

When unsure, classify information as one of these before storing it:

```text
personal_memory
shared_memory
conversation_log
reading_note
source_evidence
fanfic_variant_evidence
temporary_ai_profile
limited_ai_context
world_data
system_log
legacy_reference
```
