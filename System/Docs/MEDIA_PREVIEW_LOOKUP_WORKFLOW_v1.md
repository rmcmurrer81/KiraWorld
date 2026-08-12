# Media Preview Lookup Workflow v1

Media preview cards are "back of case" descriptions for movies, TV, music, and other media Kira/Lisa cannot fully watch or listen to yet.

They support curiosity and taste formation, not watched/listened memory.

## Launchers

```text
Build_Media_Preview_Cards.bat
Build_Media_Lookup_Queue.bat
Start_Kira_Media_Lookup_Review.bat
Auto_Lookup_Media_Queue.bat
```

## Recommended Order

1. Build preview cards from the local media index.
2. Build or refresh the lookup queue.
3. Use Auto Lookup Media Queue for obvious Wikipedia matches.
4. Use Kira Media Lookup Review for ambiguous or failed items.
5. Mark correct items Resolved.

## Current Lookup Behavior

The lookup code now tries direct Wikipedia pages first, then ranked search candidates. It scores title, year, media type, disambiguation pages, film-series pages, and soundtrack pages.

Obvious matches become:

```text
resolved_auto
```

Uncertain matches become:

```text
ambiguous
```

Failed lookups become:

```text
lookup_failed
```

## Policy

Preview text may say:

```text
the preview suggests...
this might interest Kira/Lisa...
Kira/Lisa may want to watch/listen later...
```

Preview text must not say:

```text
Kira watched this
Lisa heard this soundtrack
Kira remembers this scene
```

## Known Limits

Wikipedia is good enough for a pre-GPU metadata pass, but it is not perfect.

Later improvements may use IMDb/TMDb/OMDb or a richer provider, with Robert resolving ambiguous titles when several works share a name.
