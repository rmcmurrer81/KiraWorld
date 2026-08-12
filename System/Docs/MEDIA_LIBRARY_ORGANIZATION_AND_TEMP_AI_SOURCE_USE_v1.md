# Media Library Organization and Temporary AI Source Use v1

## Purpose

`Data/library` can hold entertainment media Kira and Lisa use for watching, listening, reading, curiosity, and future source-backed Temporary AI work.

Kira and Lisa may use the library when they are bored, curious, relaxing, learning, waiting for Robert, spending private time, or looking for something to do together. Robert does not need to assign every item. The library is part of their daily life, not only a source extraction folder.

The folder layout should make it clear whether a file is:

- a movie,
- a TV episode,
- music,
- a music video,
- a script,
- a fanfic/story,
- a novel/book,
- reference material for future Temporary AI source extraction.

## Naming Rules

Prefer clean ASCII filenames.

Avoid:

- emojis,
- corrupted encoding characters,
- multiple spaces,
- download labels such as `YouTube`, `Full Movie`, `Full Episode`, or `WATCH PARTY`,
- vague names,
- typos like `epidode`.

Use stable names that help later indexing.

Recommended patterns:

```text
movies/<franchise_or_collection>/<movie_title>_<year>.mp4
tv_shows/<series>/season_04/s04e22_ephemeral.mp4
tv_shows/<long_running_franchise>/s06_series_name/series_name_s06e42_episode_title.mp4
tv_shows/<series>/specials/miraculous_world_new_york_united_heroez.mp4
scripts/<series>/season_05/s05e09_script.pdf
music/artists/<Artist_Name>/singles/artist_-_song_title.mp3
music/artists/<Artist_Name>/music_videos/artist_-_song_title_official_video.mp4
stories/fanfic/<series>/<title>.md
```

For long-running franchise shows such as Power Rangers, include the franchise season number in the folder and filename. This lets Kira, Lisa, and future TemporaryAI source tools sort episodes by franchise order even when the sub-series title changes.

Do not use uncontrolled automatic renames. Use the rename helper below so changes are planned, collision-checked, and followed by an index refresh.

## Automatic Rename Helper

The pre-GPU helper for keeping new library files in order is:

```text
tools/auto_rename_media_library.py
```

Safe preview:

```text
py tools/auto_rename_media_library.py
```

Apply one cleanup pass and refresh the media index/audit:

```text
py tools/auto_rename_media_library.py --apply
```

Watch mode for when Robert is adding files:

```text
py tools/auto_rename_media_library.py --watch --apply --interval-seconds 30
```

The helper normalizes obvious messy names into lowercase ASCII snake_case, removes common download labels, lowercases extensions, and writes:

```text
Data/indexes/media_library_rename_plan.json
```

It is conservative. It renames in place, skips anything whose target already exists, and does not create TemporaryAIs or source evidence. After an apply run, it rebuilds the media library index, audit, and update check so Kira and Lisa can see the current library layout.

## Detecting New Library Files

Use `tools/check_media_library_updates.py` to compare the current `Data/library` folder against the saved `Data/indexes/media_library_index.json`.

It detects:

- newly added files,
- removed files,
- files whose size or classification changed.

It does not modify the library and it does not refresh the index automatically. If it reports changes, run the media index builder again after reviewing the additions.

This is the pre-GPU version of auto-detection. A later 24/7 system can run the same check on a schedule or attach it to a file watcher.

For TemporaryAI source work, use:

```text
tools/scan_library_sources.py
```

This connects the update checker to the source pipeline:

```text
detect new/changed Data/library files
refresh the media index when needed
flag source-relevant additions
run the TemporaryAI source indexer
run source evidence extraction
write a character discovery brief
```

The discovery brief lives at:

```text
Data/processed/source_evidence/character_discovery_brief.json
```

Its job is to note who appears in the material and a small amount about their source/evidence status. For example, if a Miraculous script or fanfic contains Ladybug and Bunnyx, the brief should record both characters so Kira or Lisa can later ask whether Alix/Bunnyx should be tested as a TemporaryAI.

Pre-GPU source handling:

- scripts, transcripts, Markdown stories, text stories, and PDFs can be scanned now,
- fanfic is detected as variant material and must not overwrite canon,
- movies, TV episodes, music videos, and audio files are indexed as media now,
- video/audio/image files need a transcript, script, manual notes, or future media-analysis support before reliable character evidence can be extracted,
- detecting a character never creates or activates a TemporaryAI by itself.

## Daily Life Library Use

Kira or Lisa may choose anything in the approved `Data/library` index to read, listen to, or watch when current system permissions allow it.

They may use library material for:

```text
relaxing
curiosity
comfort
music listening
private time
shared Kira/Lisa time
learning
questions for Robert
questions for each other
future creative projects
future TemporaryAI proposal ideas
```

Library use may create:

```text
viewing note
listening note
reading note
preference
question
recommendation
TemporaryAI request idea
source-scan request
```

In the future 3D home, library items may also appear as physical-style objects:

```text
DVD or VHS cases on a shelf
season box sets
music albums
script binders
books or fanfic binders
reference cards
```

Kira or Lisa may browse the shelf, choose something, and either watch it on the virtual screen or sometimes play it in a virtual movie theater. The shelf object is only a representation of the file in `Data/library`; it does not create a new memory, TemporaryAI, or source claim by itself.

Library use must not automatically create:

```text
lived memory of the story
canon changes
TemporaryAI activation
permanent AI promotion
voice clone permission
avatar likeness permission
public sharing permission
```

If Kira or Lisa watches a show and becomes curious about a character, she may later ask Robert or the other core AI whether to scan that character for TemporaryAI source work. That starts a request/review path; it does not automatically instantiate the character.

## Current Notes

The current library folders are cleanly indexed and the filename audit currently reports no flagged names.

Good categories already present:

- `movies/power_rangers/`
- `movies/abbott_costello/`
- `tv_shows/miraculous_ladybug/`
- `tv_shows/teen_titans/`
- `music/artists/`
- `music/music_videos/by_artist/`
- `scripts/Miraculous_Ladybug/`
- `stories/fanfic/Miraculous_Ladybug/`

Future added files should still avoid emojis, corrupted encoding, multiple spaces, `Full Movie`, `Full Episode`, `YouTube`, `WATCH PARTY`, or `epidode`.

## Temporary AI Source Use

User-authorized local movies and episodes can now supply short private voice/movement candidates through `TEMP_AI_PRIVATE_LOCAL_MEDIA_INTAKE_v1.md`. The request must name exact time ranges and keep character, variant, speaker, and performer separate. Candidate extraction is not evidence approval: human identity review must reject mixed/overlapping speakers, music-heavy speech, narration, unclear movement tracks, and adaptation mix-ups before anything is promoted.

Movies and TV episodes may become source evidence for Temporary AIs later, but never automatically.

Example uses:

- Power Rangers movie files may support a future Kimberly Hart / Pink Ranger Temporary AI.
- Power Rangers and `Perfect Body` files may support a future Amy Jo Johnson public performer research request, while keeping the performer separate from the characters she played.
- Miraculous Ladybug episodes and scripts may improve the Ladybug Temporary AI.
- Teen Titans episodes may support a future Teen Titans character Temporary AI.
- Music videos may support style, performance, voice, or visual evidence only after review.

The pipeline must keep these separate:

```text
library media
source evidence
character profile
relationship tree
voice profile
avatar reference
temporary AI instance
```

Watching a movie does not create a Temporary AI.

Reading a script does not create canon memory.

Fanfic does not overwrite canon.

## Source Evidence Rule

When a file is used for Temporary AI work, extracted claims should be tagged:

```text
canon
movie_canon
series_episode
adaptation
performance_only
fanfic_variant
uncertain
```

For Kimberly Hart, the movie can support what is shown in that movie version. It should not automatically import every TV-series continuity detail unless the source set intentionally includes those files.

For a public performer such as Amy Jo Johnson, local movies and episodes are performance evidence only. The system should cross-reference them with reliable public filmography sources, official credits, interviews, and uncertainty notes. It must not treat roles as the performer's private memories or merge the performer profile with a character profile.

For Ladybug, scripts and episodes can improve source grounding, but the character's knowledge still depends on selected canon point and variant rules.

## Summary

The current folders are good enough to keep building. The next cleanup should be filename normalization, then source-evidence extraction for selected characters.
