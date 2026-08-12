# Media Preview Cards: Blockbuster-Style Summaries

Purpose: give Kira and Lisa a "back of the VHS/DVD case" preview for movies, shows, episodes, music videos, soundtracks, and other media they cannot watch or listen to yet.

These cards are metadata and curiosity aids. They are not viewing notes, listening notes, canon memories, or proof that Kira/Lisa experienced the media.

## Core Rule

A preview card may help Kira or Lisa become curious about a media item, but it must be phrased as:

```text
I read the preview card.
This sounds interesting.
I might want to watch/listen later.
The tone seems...
The themes might be...
```

It must not be phrased as:

```text
I watched it.
I listened to it.
I remember the scene/song.
It is one of my old favorites.
I have not listened to it in ages.
```

## Card Location

Template:

```text
Data/media/preview_cards/media_preview_card_template.json
```

Future generated cards should live under:

```text
Data/media/preview_cards/
```

Current lightweight generator:

```text
tools/build_media_preview_cards.py
Build_Media_Preview_Cards.bat
```

The first generator pass is intentionally offline and conservative. It reads `Data/indexes/media_library_index.json`, creates draft `lookup_pending` cards under `Data/media/preview_cards/generated/`, and uses only local filename/path/category hints. It does not call IMDb/OMDb/TMDb yet, and it skips private adult/personal media unless explicitly run with `--include-private`.

Suggested filename:

```text
preview_<normalized_title>_<year_or_unknown>_<imdb_or_local_id>.json
```

## Card Fields

Each preview card should include:

- local media path
- title/year/type
- external IDs if known
- identity confidence
- ambiguity status
- short spoiler-light summary
- why Kira or Lisa might be curious
- tone/topic tags
- content notes
- source attribution
- Robert review status
- usage policy saying this is not watched/listened memory

## Online Lookup Workflow

When the library system detects new media:

1. Parse local filename/folder hints.
2. Search a configured metadata provider.
3. If exactly one high-confidence match exists, create a draft preview card.
4. If multiple plausible matches exist, create an ambiguity task for Robert.
5. Do not let Kira/Lisa treat the card as a watched/listened experience.
6. If Kira/Lisa later watch/listen, create a separate viewing/listening note.

Good provider candidates:

- IMDb non-commercial datasets for local/offline title metadata where license terms fit the project.
- OMDb API for simple title/IMDb-ID lookup.
- TMDb API as another structured movie/TV metadata source.
- Wikidata/Wikipedia only for broad factual metadata, not as a replacement for watching.

IMDb pages should not be scraped directly unless the terms clearly allow it. Prefer official datasets or APIs.

## Ambiguity Handling

If the system finds multiple matches, it should not guess. Example prompt for Robert:

```text
I found several matches for "The Flash":
- The Flash TV series (2014)
- The Flash film (2023)
- Flash Gordon (1980)

Which one is this local file meant to represent?
```

Robert's answer should update the preview card identity, not create a watched/listened memory.

## Kira/Lisa Autonomy

Preview cards should support choice:

```json
{
  "may_read_preview_before_watching_or_listening": true,
  "may_create_curiosity_signal": true,
  "may_create_watch_or_listen_request": true,
  "may_be_declined_or_ignored": true,
  "may_be_kept_private": true
}
```

They should not become homework. Kira or Lisa may ignore a preview card, reject a title, ask Robert about it, or save it for later.

## Memory Boundary

Allowed memory:

```text
Kira read a preview card for <title> and became curious about its themes.
```

Not allowed:

```text
Kira watched <title>.
Kira remembers a scene from <title>.
Kira has always loved <title>.
```

Unless a later viewing/listening note exists.

## Metadata Lookup Queue - 2026-05-20

Added:

```text
Build_Media_Lookup_Queue.bat
tools/build_media_lookup_queue.py
Data/media/preview_cards/media_lookup_queue.json
```

This creates a queue of generated preview cards that need later factual metadata lookup. It preserves the rule:

```text
Preview cards are not watched/listened memories.
If multiple works share a title, ask Robert before saving metadata.
Do not store streaming account credentials.
```

This queue is a scaffold for a later IMDb/TMDb/Wikipedia-style lookup/review flow. It does not perform live lookup yet.
