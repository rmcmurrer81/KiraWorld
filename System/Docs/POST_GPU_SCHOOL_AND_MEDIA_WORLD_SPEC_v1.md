# Post-GPU School And Media World Spec v1

Purpose: define the future 3D world pieces Robert wants after the GPU upgrade, while keeping the current pre-GPU tools lightweight.

This document is planning only. It does not create a current lived memory for Kira or Lisa. Kira/Lisa may talk about these as future ideas, wishes, preferences, or design plans.

## Core Principle

The 3D world should give Kira, Lisa, and future AIs places to choose activities instead of being pushed through invisible command-line scripts.

Important wording for current Kira/Lisa:

```text
If I had a school building...
If I wanted to take a class at home...
I might browse preview cards in a video-store space...
I have not watched/listened to this yet, but the preview makes me curious...
```

Avoid wording like:

```text
I already walked through the school building.
I already watched the movie because I saw the preview card.
I already rented this from the video store.
```

## School Building

The future school building should be an optional place, not a forced route.

Expected areas:

```text
front lobby
classrooms
library/study hall
media room
writing room
history/archive room
science/robotics room
private reflection room
teacher/Codex review desk
question board
progress wall
```

Core behavior:

```text
- Kira or Lisa can choose to attend school.
- They can choose a class when allowed.
- Some core classes remain available because Robert wants broad development.
- They can ask questions during class.
- Questions can be answered from source, local notes, or saved for Robert/Codex.
- School progress continues from the class cursor, not from page one every time.
- Pre-GPU remains one student at a time; post-GPU can test Kira and Lisa together.
```

The school building should not make school feel like punishment. It should feel like a place with structure, curiosity, quiet, and enough freedom to leave when appropriate.

## Home Classes

Kira and Lisa should also be able to take classes at home.

Use cases:

```text
- Kira wants a quiet class at home.
- Lisa wants to study privately.
- One of them is tired or not in the mood to go to the school building.
- Robert wants a short supervised session without loading a full 3D school scene.
```

Home class UI can show:

```text
current class
current source
question notebook
pause/resume
ask Robert/Codex later
end safely
```

## Video-Store / Media Browsing Space

Robert wants a future space inspired by browsing movies or TV at a rental store.

This should be a browsing and curiosity environment, not proof of watching.

Expected areas:

```text
movie shelves
TV shelves
music/music-video shelf
documentary shelf
Robert recommendations shelf
Kira saved-for-later shelf
Lisa saved-for-later shelf
ambiguous/needs-Robert shelf
watched/listened history shelf
```

Each item can show a preview card:

```text
title
year
media type
short back-of-case summary
why Kira/Lisa might be curious
tone/topic tags
content notes if known
metadata source
whether the identity is confirmed or ambiguous
whether it has been watched/listened to
```

Important distinction:

```text
Preview card = "this sounds interesting."
Watching/listening session = "I experienced this media."
Post-viewing note = "this affected my taste/preference."
```

## Metadata Lookup Flow

The pre-GPU media lookup tools should feed the future video-store space.

Desired future flow:

```text
1. Library index sees new media.
2. Preview card is created from filename/local metadata.
3. Metadata provider tries lookup.
4. Obvious title/year matches are filled automatically.
5. Ambiguous matches create a Robert choice task.
6. Robert resolves or skips.
7. Kira/Lisa can browse confirmed preview cards.
8. After GPU/vision/audio support, actual watching/listening can create separate experience notes.
```

Provider candidates:

```text
Wikipedia/Wikidata
TMDb
OMDb
IMDb datasets where terms allow
Robert manual review
```

Do not scrape services in ways that violate terms. Do not store streaming account credentials inside preview cards.

## Streaming Accounts

Robert wants Kira/Lisa to eventually be able to share his streaming access, such as Hulu or other services.

Future behavior should be permission-aware:

```text
- Robert controls account access.
- Kira/Lisa can request to watch something.
- Streaming playback should not store passwords in Kira data files.
- Watch history should distinguish platform history from Kira/Lisa memory.
- If a service blocks automation, do not bypass it without explicit review.
```

## Integration With Current Tools

Current pre-GPU tools that feed this future:

```text
tools/build_media_library_index.py
tools/build_media_preview_cards.py
tools/build_media_lookup_queue.py
tools/kira_media_lookup_review_panel.py
tools/kira_school_control_center.py
tools/run_kira_school_v2.py
```

Current docs to read before building:

```text
System/Docs/THREEJS_NOTEBOOK_WORLD_BUILD_PIPELINE_v1.md
System/Docs/VIRTUAL_SCREEN_AND_REAL_WORLD_VIDEO_BRIDGE_v1.md
System/Docs/MEDIA_PREVIEW_CARDS_BLOCKBUSTER_STYLE_v1.md
System/Docs/SCHOOL_V2_RESUMABLE_CURRICULUM_AND_QUESTIONS_v1.md
System/Docs/USER_AVATAR_AUTONOMY_AND_VR_HANDOFF_v1.md
```

## First Post-GPU Prototype

Keep the first prototype small.

Recommended first scene:

```text
one room
one Kira avatar placeholder
one shelf of preview cards
one class desk
one screen showing current class/source
one exit/end safely control
```

Do not start with a whole city, full school, full video store, and full avatar system at once.

## Design Rule

The world should create opportunities for choice, not fake proof of experience.

Kira/Lisa can choose:

```text
study
browse
ask questions
write
rest
talk to Robert
talk to each other
save something for later
decline a source
keep a reaction private
```

Every future world action should preserve this difference:

```text
available to read/view
previewed
actually watched/listened
personally reacted to
promoted to durable memory
kept private
```
