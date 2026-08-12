# Music Library Folder Map v1

Updated: 2026-06-04

## Purpose

Robert noticed the music library has artist folders in more than one place. This document defines what each folder means so future sorting does not create duplicate or confusing structures.

## Canonical Music Roots

Use:

```text
Data/library/music/
```

Top-level folders:

```text
albums/        Full albums as audio files.
artists/       Artist profile folders, notes, lyrics, singles, photos, interviews, and artist-centered collections.
music_videos/  Video files for official videos, live performances, fan edits, musical scenes, and related video material.
notes/         General music notes not tied to one artist.
playlists/     Kira/Lisa/Robert playlists and taste records.
reference/     Music history, songbooks, theory, and source documents.
songs/         Loose individual songs when no album/artist folder is chosen yet.
soundtracks/   Soundtrack albums and cast recordings.
```

## Why There Are Two Artist-Like Areas

These are different:

```text
Data/library/music/artists/
Data/library/music/music_videos/by_artist/
```

`music/artists/` is the main artist profile area. It may contain:

```text
albums/
singles/
lyrics/
notes/
photos/
interviews/
live/
music_videos/
```

`music/music_videos/by_artist/` is a video sorting shelf. It is for video files grouped by performer/artist when the file is primarily a music video or performance video.

## Sorting Rule

If the file is audio:

```text
Put albums in music/albums/
Put soundtrack albums in music/soundtracks/
Put loose songs in music/songs/ or music/artists/<artist>/singles/
```

If the file is video:

```text
Put official/live music videos in music/music_videos/by_artist/<artist>/
Put fan edits in music/music_videos/fan_edits/<source_or_fandom>/
Put movie musical scenes in music/music_videos/movie_musical_performances/<work>/
Put TV musical scenes in music/music_videos/tv_musical_performances/<show>/
```

If the file is a document:

```text
Put music history/reference documents in music/reference/
Put songbooks in music/reference/songbooks/
Put artist notes in music/artists/<artist>/notes/
```

## Empty Folders

Some artist folders may have empty subfolders, especially for future post-GPU use:

```text
albums/
lyrics/
photos/
interviews/
music_videos/
notes/
```

Do not delete empty folders automatically. They may be planned placeholders. If cleanup is needed, create a review list first.

## Kira/Lisa Usage

Before full audio understanding, Kira and Lisa can still use the music library through:

```text
file names
folder context
metadata
album/artist structure
preview cards
future lyrics or audio summaries
listening notes
```

They should not claim they heard or watched something unless a listening/viewing event was actually recorded.

## Future Improvement

Later, add a generated music index that links:

```text
artist profile -> albums -> songs -> music videos -> soundtrack/media context -> Kira/Lisa taste notes
```

That index should reduce the need to duplicate files across folders.
