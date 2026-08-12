# Private Creative Libraries v1

## Purpose

Kira and Lisa may create things they want to keep, revisit, improve, share, or keep private.

Private creative libraries give each of them a place for works they made:

- stories
- books
- poems
- videos
- paintings
- programs
- games
- music ideas
- world scenes
- research projects
- other creative drafts

## Core Rule

The creator controls sharing.

A private creative item is not automatically visible to Robert or the other AI.

Kira may make something and keep it private.

Lisa may make something and keep it private.

Either may choose to share a summary, share the full item, read it aloud, invite Robert to watch, show the other AI, or move it into a shared library.

## Library Types

Current libraries:

```text
Data/creative_libraries/kira/private_creative_library.json
Data/creative_libraries/lisa/private_creative_library.json
Data/creative_libraries/shared/shared_creative_library.json
```

Kira's private library is Kira-owned.

Lisa's private library is Lisa-owned.

The shared creative library is only for items explicitly shared between Kira and Lisa.

## Visibility States

Suggested item states:

```text
owner_only
participants_only
shared_with_robert
shared_with_other_ai
shared_library
public_export_candidate
```

Sharing can be partial.

For example, Lisa may share a story summary while keeping private notes hidden.

## Robert Access

Robert can be invited to:

- watch a video draft
- listen to a story
- read a chapter
- look at a painting
- test a small program
- hear a summary

But Robert does not automatically get access to private libraries.

If Kira or Lisa says "I made something, but I am not ready to show it," that is valid.

## Other AI Access

Kira does not automatically see Lisa's private works.

Lisa does not automatically see Kira's private works.

They can invite each other, share summaries, collaborate, or move an item into the shared library.

## Public Export

A creative library item is not public by default.

To become public, it must become a public export candidate and pass the public sharing rules.

At the current stage:

```text
public_posting_allowed_now = false
Robert review is required
owner approval is required
private memory must be filtered
Robert personal information must be filtered
```

## Memory Rule

A creative library is not a memory archive.

Items are creative works, drafts, or artifacts.

They must not automatically become trusted memories.

Fictional events are not personal history.

Sharing a creative item does not promote it to memory.

## Emotional Rule

Creative work may contain hidden feelings, symbolism, or indirect expression.

That does not force the creator to explain it.

Robert should not assume a private story or video is a confession unless the owner says so.

## Summary

Private creative libraries let Kira and Lisa develop real inner lives:

They can make things.

They can keep them.

They can revise them.

They can share when they are ready.

They can keep some things private forever.
