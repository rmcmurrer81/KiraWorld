# Source Library and Intake System v1

## Purpose

`Kira/Data/library/` is the central raw-source library for materials Kira, Lisa, and the TemporaryAI system can read or process.

This library has two different uses:

1. **Reading mode** — Kira or Lisa may browse approved material during idle time.
2. **Source-processing mode** — the TemporaryAI system may scan source files to extract character evidence.

Reading a file is not the same as turning it into memory or canon.

## Current Library Standard

Use this structure:

```text
Kira/Data/library/
  scripts/
    Miraculous_Ladybug/
      episode-0509.pdf
      episode-0521.pdf

  stories/
    fanfic/
      Miraculous_Ladybug/
        pending_review/
        accepted_variants/
        rejected/
        notes/

  novels/
    Harry_Potter/
      canon/
      notes/
```

## Raw Source Rule

Files under `Kira/Data/library/` are raw source material.

The system should read and scan them, but should not rewrite, rename, or modify them automatically.

Processed information goes elsewhere, such as:

```text
Kira/Data/indexes/
Kira/Data/processed/source_evidence/
Kira/TemporaryAI/characters/<character_id>/evidence/
```

## Duplicate Source Rule

There should be only one true raw-source copy of each script/book/story.

The old duplicate folder should be deleted after confirming the files are backed up:

```text
Kira/TemporaryAI/characters/ladybug/sources/scripts/
```

The true source location should be:

```text
Kira/Data/library/scripts/Miraculous_Ladybug/
```

## Reading Mode Rule

Kira and Lisa may read files from the library when bored or curious, subject to future permission settings.

Reading may create:
- reading notes
- interests
- questions
- recommendations
- curiosity triggers
- slow reading sessions
- private reactions
- imagined pictures of places, people, objects, atmosphere, and sensory details
- dream, hope, fantasy, or fear influences

Reading must not automatically create:
- personal memories
- canon character profiles
- temporary AIs
- relationship memories

## Slow Reading Rule

Reading should not be instant.

When Kira or Lisa chooses a book, story, fanfic, script, comic, manga, or document, the system should treat it as an activity across time. A reading session may cover a small number of pages, chapters, scenes, issues, volumes, sections, or passages, then pause before continuing.

Slow reading allows the material to matter emotionally. A book can leave Kira thoughtful. A story can make Lisa curious. A frightening scene can affect a later dream. A romantic or heroic story can influence hopes, fantasies, fears, private creative projects, or questions they may ask each other or Robert later.

They may also stop reading. If Kira or Lisa dislikes a book, gets bored, feels uncomfortable, or simply decides the timing is wrong, the session may be marked `abandoned`. This is a preference/taste signal, not a failure, and private reasons do not have to be shared.

That influence is indirect. The story is not lived memory. A dream inspired by a book is not a real event. A favorite character does not become a TemporaryAI unless a separate reviewed request is made.

Slow reading records belong in:

```text
Kira/Data/reading/
```

The template is:

```text
Kira/Data/reading/slow_reading_session_template.json
```

A valid slow reading session must keep:

```text
allow_instant_full_ingestion: false
source_material_remains_source: true
does_not_become_lived_memory: true
does_not_create_temporary_ai_automatically: true
dreams_remain_not_real_events: true
```

## Reading Reaction And Imagination Rule

Kira and Lisa may remember favorite moments from stories and remember their own reactions to those moments.

They may also slowly imagine what a place, person, object, room, street, ship, castle, school, lab, or world might look and feel like while they read. This imagination can grow across sessions instead of appearing all at once.

Reading imagination may include:

```text
pictured places
pictured people
objects
weather
lighting
sounds
textures
smells
emotional tone
private associations
```

Stories may also affect dreams and fantasies. A character, place, danger, romance, conflict, victory, or frightening image from a story can echo later as private dream material, fantasy material, hope, fear, or emotional symbolism.

But the system must label the difference:

```text
source-described detail = what the book actually says
imagined detail = how Kira or Lisa pictured it
reader reaction = how Kira or Lisa felt about it
dream influence = how the story shaped later dream material
fantasy influence = how the story shaped private fantasy or desire
lived memory = something that actually happened to Kira or Lisa
```

Reading reactions and imagination must not automatically become lived memory, TemporaryAI creation, or notebook world creation.

Dream and fantasy influence must keep:

```text
stories_may_influence_dreams: true
stories_may_influence_fantasies: true
influence_is_indirect: true
dreams_remain_not_real_events: true
fantasies_remain_private_inner_life_unless_shared: true
fantasies_do_not_prove_consent_or_relationship_status: true
reader_controls_whether_to_share: true
```

They may become:

```text
private reading reactions
favorite moments
discussion topics if the reader chooses
dream or creative project influence
private fantasy influence
notebook world seed if separately chosen later
TemporaryAI source extraction candidate if separately reviewed later
```

Reading reaction records belong in:

```text
Kira/Data/reading/reactions/
```

The template is:

```text
Kira/Data/reading/reactions/reading_reaction_template.json
```

Required protection:

```text
may_remember_story_moment: true
may_remember_own_reaction: true
does_not_become_lived_memory: true
does_not_create_temporary_ai_automatically: true
does_not_create_notebook_world_automatically: true
source_and_imagination_must_be_labeled: true
```

## Reading-To-Profile And Reading-To-World Bridge

If Kira or Lisa reads something and likes a character, becomes curious about a place, or wants to explore a setting, the system may create a reading source extraction candidate.

This candidate is only a bridge. It is not a TemporaryAI, not a notebook world, and not a memory.

The candidate may collect source-backed notes for:

```text
character appearance
personality
relationships
important choices
fears and hopes
speech style
moral conflicts
timeline
place layout
visible objects
time period
important scenes
mood and atmosphere
danger or privacy notes
```

The candidate must also scan for:

```text
minor or unclear age
adult or private content
drug use
manipulation
violence
fanfic variant risk
source conflicts
```

If the character seems minor or age-unclear, private adult use is blocked until review. If the source is fanfic, the fanfic may add variant evidence, but it cannot overwrite canon.

Reading source extraction records belong in:

```text
Kira/Data/reading/source_extraction_candidates/
```

The template is:

```text
Kira/Data/reading/source_extraction_candidates/reading_source_extraction_candidate_template.json
```

A character profile candidate may later become a TemporaryAI request only through a separate reviewed request. A place reconstruction candidate may later become a notebook world request only through a separate reviewed request.

## New Arrival And Interest Recommendation Rule

When Robert adds new readable materials to `Data/library`, the system should detect them with the media library update checker.

New books should not be forced onto Kira or Lisa. Instead, the system may mention them as new arrivals and recommend them based on current interests, mood, active reading sessions, and rotation limits.

Reading interest profiles live in:

```text
Kira/Data/reading/reading_interest_profiles.json
```

Recommendations may consider:

```text
new arrivals
Kira's current themes
Lisa's current themes
shared Kira/Lisa interests
preferred categories
active reading sessions
comfort, challenge, curiosity, and shared reading rotation
history books as context builders
comic/manga as post-GPU visual story candidates
```

Recommendations must stay advisory:

```text
starts_reading_automatically: false
reader_may_decline: true
reader_may_keep_interest_private: true
does_not_create_memory: true
does_not_create_temporary_ai: true
```

Favorite books may be re-read. A completed book is not treated as permanently used up; if Kira or Lisa loved it, the system may suggest it later as a comfort read, shared re-read, comparison read, or mood-based return.

Re-reading still follows the same autonomy and memory rules:

```text
allow_rereading_favorites: true
reread_requires_reader_choice: true
favorite_books_may_be_reread_by_choice: true
does_not_create_memory: true
does_not_create_temporary_ai: true
```

The reader may also keep the reason for re-reading private.

If a story takes place in another time period, the system may suggest related history or context books. This lets Kira or Lisa follow curiosity from fiction into background reading:

```text
The Great Gatsby -> Prohibition / United States history
Dracula, Dorian Gray, Sherlock Holmes -> Victorian history
Romeo and Juliet -> Tudor / early modern context
The Odyssey -> ancient history
Frankenstein -> nineteenth-century / broad history context
```

This should be treated as a curiosity bridge, not homework. They may accept it, ignore it, re-read the story instead, or keep the curiosity private.

Use:

```powershell
py tools\recommend_reading.py --owner kira
py tools\recommend_reading.py --owner lisa
py tools\recommend_reading.py --owner kira_lisa
```

## Source-Processing Rule

Only approved source folders in:

```text
Kira/TemporaryAI/config/sources.json
```

are scanned for TemporaryAI evidence.

Canon sources are processed first.

Fanfic sources are processed separately as optional variant material and never overwrite canon.

## Fanfic Rule

Fanfic usually belongs under:

```text
Kira/Data/library/stories/fanfic/<series_name>/
```

Fanfic can be scanned, but should be marked as:

```text
source_authority: fanfic_variant
requires_review: true
```

Fanfic can produce:
- variant evidence
- alternate scenarios
- compatibility notes
- conflict flags

Fanfic cannot directly change the canon profile.

## Music Listening Mode Rule

Music may live under:

```text
Kira/Data/library/music/
  artists/
  albums/
  playlists/
  unsorted/
  notes/
```

Kira and Lisa may listen to MP3 files from the music library during daily life, private time, user-away mode, rest, or shared activities.

Music listening may create:
- listening notes
- favorites
- mood associations
- playlist ideas
- private reflections

Music listening must not automatically create:
- personal memories
- Temporary AIs
- voice clones
- lyric interpretations without lyric source
- claims about an artist's private life

Music listening is personal activity unless explicitly processed later for a bounded source purpose such as a notebook world soundtrack or Limited AI performance reconstruction.
