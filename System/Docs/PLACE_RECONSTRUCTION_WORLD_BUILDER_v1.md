# Place Reconstruction World Builder v1

This document defines how the world builder can reconstruct homes, neighborhoods, stores, malls, theaters, venues, and other places from photos, blueprints, videos, maps, and notes.

The goal is source-driven world creation without pretending guesses are facts.

## Core Idea

Robert can collect references for a real or fictional place, then the world builder creates a private home-world area or notebook world from those sources.

Kira and Lisa's home is the main persistent world. Notebook worlds are separate destinations reached from the TARDIS outside the home.

Examples:

```text
Kira and Lisa's home from a random house with photos and blueprints
a Doctor Who reference-based TARDIS outside the home
a nearby movie theater
a mall
a retro video rental store
a neighborhood street
a school or college-like location
a performance venue
```

The system should build what is supported, mark what is inferred, and leave unknown areas incomplete or clearly labeled.

## Source Types

Useful source types:

```text
blueprints
floor plans
exterior photos
interior photos
room photos
walkthrough videos
street photos
maps
listing photos
manual notes
measurements
style references
era references
```

For places like a mall or theater, the system may also use:

```text
directory maps
storefront photos
seating charts
concession photos
parking lot photos
signage photos
old advertisements
public videos
```

## Folder Structure

Recommended source folders:

```text
Data/world_reconstruction/sources/
  homes/
    kira_lisa_home_candidate_001/
      blueprints/
      exterior/
      interior/
      rooms/
      measurements/
      style_refs/
      notes/

  neighborhood/
    nearby_area_candidate_001/

  entertainment/
    movie_theater_candidate_001/
    mall_candidate_001/
    video_store_candidate_001/
```

Processed world plans should go under:

```text
Data/world_reconstruction/plans/
```

## Confidence Labels

Every reconstructed area should be labeled:

```text
blueprint_confirmed
photo_confirmed
video_confirmed
map_confirmed
manual_note_confirmed
inferred_from_sources
style_fill
unknown
blocked_private
```

The builder should never hide uncertainty.

## House Reconstruction

For Kira and Lisa's home, the system may use a real house listing, blueprint, floor plan, or reference set as a base.

Allowed:

```text
build rooms from blueprint
match windows, doors, stairs, and room locations from photos
infer furniture placement from images
use style references for decor
create private bedrooms for Kira and Lisa
place the TARDIS outside the home
use Doctor Who TARDIS reference images for the TARDIS exterior
place a virtual screen in a living room or media room
add a library/music area
```

Not allowed:

```text
claim an unseen room exists as fact
invent exact dimensions without blueprint or measurement
make private locked rooms visible by default
erase uncertainty labels
claim the real house's owners or residents are known
claim TARDIS details are source-confirmed if no reference image supports them
```

If a room is not shown, it can be marked unknown or created as an original extension.

## Home Design Autonomy

Kira and Lisa's home should be livable and changeable by them.

The source reconstruction gives the home a starting structure. It does not permanently freeze every couch, chair, rug, color, lamp, poster, shelf, or room mood.

Kira or Lisa may decide:

```text
I do not like this couch.
I want a softer chair.
This room feels too cold.
I want a bigger media shelf.
My bedroom should feel more like me.
The living room should have a better place to sit together.
```

Allowed later, when home design tools exist:

```text
delete or archive a couch
design a new couch
move furniture
change colors and lighting
replace decor
create alternate versions
save before/after design records
```

Protected from casual edit:

```text
walls and structural layout
doors, locks, and privacy controls
Kira/Lisa private room boundaries
Robert avatar entry point
TARDIS gateway
virtual phone/contact surfaces
virtual screen privacy controls
source labels and truth labels
```

Shared rooms should be treated as shared. Either Kira or Lisa may propose a change, but the other resident may accept, reject, modify, or argue about it. Private rooms belong to the room owner.

Pre-GPU, this is design intent and request drafting. Post-GPU, it can become reversible world editing.

## Original Extensions

Kira and Lisa can add original areas near the reconstructed home.

Examples:

```text
movie theater
mall
retro video rental store
library
park
cafe
music room
private dream room
Doctor AI office
```

Original extensions should be labeled as original or inspired, not source-confirmed.

## Retro Video Store Example

If Robert wants a Blockbuster-like video store nearby, the system can create a private original video store inspired by public references.

Allowed:

```text
retro video rental layout
blue-and-yellow inspired mood if transformed enough
aisles
movie posters from approved sources
checkout counter
new releases wall
snack shelf
```

The world should not need to claim it is an official Blockbuster unless Robert explicitly wants a private recreation.

## Privacy And Access

Home spaces may include:

```text
public shared areas
personal rooms
private rooms
locked-private rooms
guest areas
Robert avatar entry points
TARDIS exterior access
```

Private rooms must follow the privacy/doorbell system.

A blueprint does not override character privacy. Even if the room layout is known, Kira or Lisa can still lock a room or keep activities private.

## Relationship To Notebook Worlds

Place reconstruction can create:

```text
home world
neighborhood world
saved notebook world
source reconstruction world
performance venue world
memory-adjacent place
original extension
```

The TARDIS can list worlds and places under construction.

## Pre-GPU Workflow

Before the GPU desktop, the system can:

```text
collect sources
organize folders
create reconstruction plans
label confirmed and unknown zones
write room lists
write object lists
write privacy zones
prepare build requests
```

It should not claim the 3D world exists yet.

## Post-GPU Workflow

After the GPU desktop, the system can:

```text
generate or import 3D layouts
create room meshes
place furniture
create lighting
create navigation
connect the TARDIS
add virtual screens
add music/library objects
spawn approved Limited AIs or Temporary AIs
```

Media library objects may include:

```text
DVD/VHS shelf in the home
music shelf or album cabinet
script and story binders
virtual movie theater screen
theater seats, lobby, and snack counter
```

The shelves and theater should use `Data/indexes/media_library_index.json` as the source list. A movie case or VHS tape is a navigational object for a library file, not a separate source of truth.

## Summary

Place reconstruction lets Kira and Lisa's world grow from real references while keeping truth labels clear.

The system can build a believable home and neighborhood from photos and blueprints, then expand into original or recreated places nearby.
