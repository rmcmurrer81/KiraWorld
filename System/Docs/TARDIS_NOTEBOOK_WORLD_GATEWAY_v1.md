# TARDIS Notebook World Gateway v1

## Purpose

Notebook worlds should feel like real places Kira and Lisa can visit from their main 3D home world.

The main world is Kira and Lisa's home.

The gateway is the TARDIS located outside their home. Its exterior should be recreated from Doctor Who TARDIS reference images provided by Robert. The canonical system name is TARDIS. Kira and Lisa walk inside, use the interior console, and choose where to go.

## Exterior

The TARDIS exterior is:

```text
TARDIS
Doctor Who blue police box exterior reference
outside Kira and Lisa's home
visible from the home exterior area
stable access point for notebook worlds
```

It should not be treated as a normal decoration. It is the physical interface from the main home world into saved notebook worlds, blank worlds, and memory reconstruction worlds.

Reference images should be stored under:

```text
Data/world_reconstruction/sources/tardis/doctor_who_reference/
```

The TARDIS exterior can be source-accurate for private use, but build notes should still track which visual details are confirmed by references and which are approximated.

## Interior Console

Inside the TARDIS, the console can show:

```text
saved notebook worlds
memory reconstruction worlds
temporary AI event worlds
blank world slots
recently visited worlds
worlds under construction
source collection status
privacy status
```

## Travel Modes

### Saved World

Kira or Lisa chooses an already-created world from the console and enters it.

Examples:

```text
Universal Studios Hollywood prototype
future 3D library
Kira/Lisa home expansion
approved temporary AI event world
```

### Blank World

Kira or Lisa chooses a blank world and gives it a creation direction.

Examples:

```text
create something new
recreate a memory
build a fictional starship
make a quiet place to think
make a place based on a book or script
```

Blank worlds start empty until the system receives enough direction or source material.

### Memory Reconstruction

Kira or Lisa can select a memory reconstruction world from the console.

The same memory privacy rules still apply:

```text
private memories are private by default
sealed intimate details stay sealed unless the memory owner chooses otherwise
unknown details must be marked unknown or inferred
```

## Source Status

The console should show whether a world is:

```text
draft
approved
building
active
archived
waiting for sources
private only
public export candidate
```

## Enterprise Example

Kira or Lisa may enter a blank world and ask it to start making the Enterprise.

Early version:

```text
blank space
rough exterior silhouette
main bridge prototype
source-needed markers
private only
```

Later version:

```text
more accurate rooms from sources
larger explorable ship
era-specific variants
temporary AI or NPC crew only if approved
```

## Existing System Alignment

The Movement and Embodiment system already treats TARDIS as a valid defined fast-travel structure. This gateway file extends that existing concept for notebook worlds.

## Summary

The TARDIS is the doorway between home life and imagination. It lets Kira and Lisa choose existing worlds, build blank ones, or safely revisit memories without turning private worlds into public content by accident.
