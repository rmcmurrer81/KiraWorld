# Voyager Details Intake - 2026-07-06

Robert added a local reference folder for a future Star Trek Voyager notebook world:

`C:\Users\robmc\Desktop\voyager details`

This should be a notebook world, not scenery pasted into Home World.

## Local Reference Inventory

The folder currently contains 23 image files. Useful named references include:

- `616837-star-trek-uss-voyager-lcars-technology-architecture.jpg`
- `NCC-74656-Voyager-Schematics-1024x416.jpg`
- `uss-voyager-ncc-74656-sheet-10.jpg`
- `USS-Voyager-cargo-bay.jpg`
- `USS-Voyager-main-engineering-a.jpg`
- `USS-Voyager-mess-hall.jpg`
- `USS-Voyager-NCC-74656-sickbay.jpg`
- `e0fcda7418aded6019ab884331eaa36d--star-trek-voyager-bridges.jpg`
- `voyager.jpg`

## World Builder Direction

- Build Voyager from source-backed modules: exterior, corridors, bridge, sickbay, engineering, mess hall, cargo bay, transporter/utility rooms, and LCARS panels.
- Keep deck layout, scale, and guessed connections documented.
- Every interactive object needs an affordance tag: door, turbolift, console, chair, bed/biobed, replicator, transporter pad, computer display.
- Do not create the ship as one static mesh. Each room needs navigation, collision, lighting, and review camera points.
- The TARDIS should appear only through explicit travel/call behavior, not as normal room decoration.

## First Build Gate

Before constructing the world, create a `world_builder_request.json` with:

- chosen scale anchors,
- room/module list,
- required source images,
- unknown areas,
- test routes,
- screenshots to capture after build.
