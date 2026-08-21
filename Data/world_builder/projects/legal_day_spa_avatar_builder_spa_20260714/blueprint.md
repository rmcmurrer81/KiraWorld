# Legal Day Spa / Avatar Builder Spa Blueprint

Status: draft, not placed in Home World.

This is a standalone World Builder target. It should be reviewed in isolation first, then optionally placed in Home World only after Robert approves the exterior, interior, doors, collisions, and AI navigation.

## Design Intent

Build a legitimate day spa, not an illegal or suspicious massage parlor. The building should feel public-facing, licensed, clean, accessible, and calm. It should also function as the in-world Avatar Builder room where Kira, Lisa, Robert, and approved residents can request body/appearance changes through conversation and previews.

## Source Rules

- Use official licensing/accessibility sources for legal and public-business constraints.
- Use spa layout articles and photos only as inspiration for flow, room types, and atmosphere.
- Do not copy a single floor plan or model.
- Mark unknowns instead of inventing hidden service spaces.
- Do not import into Home World until review passes.

## Legal / Legitimate Spa Cues

- Public reception desk visible from the front door.
- Waiting area visible from reception.
- License/registration wall behind reception.
- Posted menu of lawful services: massage therapy, facial, skin care, hair styling, consultation, relaxation room, avatar-builder consultation.
- Staff-only laundry/storage behind a marked door.
- Clean towel storage and dirty-linen hamper are separate.
- No secret back entrance for clients.
- No locked unmarked private rooms.

## Building Program

Target footprint: 24 m wide x 18 m deep.

Rooms:

- Front vestibule: 3 m x 3 m, double glass doors, no collision blockers behind the door.
- Reception and waiting: 8 m x 6 m, desk, chairs, license wall, Avatar Builder appointment kiosk.
- Consultation room: 4 m x 4 m, chair pair, desk/tablet, consent screen.
- Avatar Builder preview studio: 6 m x 6 m, full-height mirror/display wall, body scanner ring, privacy controls, approval screen.
- Treatment room A: 4 m x 4.5 m, massage/treatment table, side counter, sink, stool.
- Treatment room B: 4 m x 4.5 m, same as A.
- Styling room: 5 m x 4 m, styling chair, mirror, sink, hair/color material shelves.
- Relaxation room: 6 m x 5 m, lounge chairs, tea/water station, soft lighting.
- Accessible restroom: 3 m x 3 m, reachable from public corridor.
- Staff/laundry/storage: 5 m x 4 m, staff-only door, clean shelves, laundry hamper, utility sink.
- Mechanical closet: 2 m x 2 m.

## Flow

Public route:

1. Sidewalk to front door.
2. Front door to reception/waiting.
3. Reception to consultation.
4. Consultation to Avatar Builder preview studio or treatment/styling rooms.
5. Treatment/styling rooms back to reception or relaxation room.
6. Exit through the same front vestibule.

Staff route:

1. Reception/staff door to staff/laundry/storage.
2. Staff/laundry/storage to treatment rooms through service side if possible.
3. Staff route must not block the public route.

AI route targets:

- `spa_front_door_outside`
- `spa_front_door_inside`
- `spa_reception_counter`
- `spa_waiting_chair`
- `spa_consultation_chair`
- `spa_avatar_builder_talk_button`
- `spa_avatar_preview_marker`
- `spa_treatment_table_a`
- `spa_styling_chair`
- `spa_relaxation_lounge`
- `spa_restroom_door`
- `spa_exit`

## Door And Collision Requirements

Every door must have:

- outside approach target
- handle target
- opening arc or sliding path
- inside follow-through target
- clear threshold with no invisible collider
- visible frame aligned to wall opening

Automatic fail:

- Kira hits the door and turns around.
- Door opens but the AI does not path inside.
- The avatar clips through the wall instead of using the door.
- Door frame and wall opening do not line up.
- A table/counter/wall blocks the threshold.
- Interior floor is missing or below/above door threshold.

## Avatar Builder Room Rules

- Talk button must be visible and reachable.
- Body changes are preview-only until approved.
- Adult residents may request adult-body appearance changes under consent policy.
- Non-adult residents may request safe appearance changes; age-up creates a separate reviewed adult variant and never silently overwrites the non-adult body.
- No live body mutation while the resident is active in Home World unless explicitly approved.

## Visual Requirements

The spa should be warm modern, not a beige block box:

- glass storefront and readable sign
- realistic exterior siding/stone/wood accents
- clean wall/floor transitions
- trim/baseboards where walls meet floors
- ceiling lights instead of glowing voids
- textured treatment-room floors
- realistic counters/sinks/storage
- human-scale furniture
- clear room labels only where useful for debugging

## Required Review Shots

- exterior front
- exterior side
- exterior rear/service side
- floor plan / overhead
- front door threshold close-up
- reception from entry
- corridor/path from reception
- consultation room
- Avatar Builder preview studio
- treatment room
- styling room
- restroom door and interior
- relaxation room
- collision/navmesh overlay

## Pass / Fail Gate

Grade is F until all of these pass:

- standalone preview exists
- all outer walls connect
- every public room has a floor
- all doors line up with frames/openings
- Kira-sized avatar can walk from outside to every public room and back out
- no invisible blockers on thresholds
- no blocky placeholder massing in final preview
- Avatar Builder talk button and approval screen are reachable
- source notes explain legal/public-spa cues
- Robert approves before placement

