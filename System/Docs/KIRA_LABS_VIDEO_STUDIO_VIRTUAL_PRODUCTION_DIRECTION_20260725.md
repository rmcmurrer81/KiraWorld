# Kira Labs Video Studio — virtual-production direction

Date: 2026-07-25  
Status: design direction; only the bounded features explicitly marked current are implemented

## Purpose

Kira Labs Video Studio should grow from a slide-based editor into a
truth-preserving production backend for Kira World. The visual method must
match the evidence that actually exists:

- use real screenshots or footage for real, current progress;
- use clearly disclosed concept art or animation for plans that do not exist
  yet;
- never present a generated or simulated scene as documentary evidence;
- keep resident participation voluntary and preserve the meaning of what a
  resident says.

## Required visual truth labels

Use the label that accurately describes the material:

- `LIVE KIRA WORLD FOOTAGE`
- `CURRENT DEVELOPMENT BUILD`
- `CONCEPT VISUALIZATION`
- `PLANNED FEATURE`
- `SIMULATED DEMONSTRATION`

The label must remain visible for the entire relevant shot. Editing, camera
motion, reframing, format conversion, and social-media crops must not remove
it.

## Progressive implementation path

1. Slides, captions, and Robert's approved narration.
2. Real Kira World walkthrough clips mixed with slides.
3. Automated virtual cameras and guided tours.
4. Embodied interview guests with Robert's off-camera voice.
5. Robert's avatar in a distinct Kira World virtual newsroom.
6. Kira and other residents planning, hosting, reviewing, and approving their
   own productions.

Each stage must remain useful and testable before the next stage is promoted.

## Walkthrough requirements

Future walkthrough support may include:

- establishing shots;
- a front-door entrance;
- room-by-room tours;
- object and wardrobe close-ups;
- old-build/new-build comparisons;
- a resident-led tour;
- independent camera movement under narration.

Runtime truth is mandatory. Spoken claims about a resident's location or
action must agree with captured body/world evidence. A script must not say
that someone is in a kitchen while the footage shows that person outside.

## Embodied interview requirements

Future embodied interviews may use guest close-ups, over-the-shoulder views,
two-person shots, reaction shots, and Kira World cutaways. They must preserve
the timing and meaning of the actual synthetic conversation:

- a resident may pause, think, laugh, disagree, refuse, interrupt, ask a
  question, or request that material not be used;
- editing may remove dead air but must not splice unrelated phrases into a
  stronger or different claim;
- voice, body, location, and identity evidence must remain linked;
- a no-use or withdrawal decision must propagate to dependent clips,
  narration, captions, thumbnails, and promotional copy.

## Virtual newsroom direction

A later lightweight newsroom may include an anchor desk, standing
presentation area, large media screen, robotics display, and remote interview
screen. It should use a recognizable Kira World design rather than imitate a
specific television network. Robert's approved voice remains the identifying
host voice unless Robert explicitly selects another available, approved
speaker.

## Concept visuals and animation

Concept visuals are appropriate only when:

- no accurate usable real/local/approved visual remains after a documented
  search with linked evidence; or
- the subject is inherently conceptual.

Useful future concept subjects include memory-channel explanations, planned
clothing interaction, a future TARDIS trip, a planned robotics body, intended
Avatar Builder or World Builder behavior, and planned multi-person Home World
scenes.

Current implemented boundary in the isolated v2 staging tree:

- deterministic offline concept cards;
- native landscape, vertical, and square composition;
- a bounded silent still-image pan/zoom or diagram-motion private preview;
- persistent concept/private-review disclosure;
- no external or AI image generator;
- no character, face, body, or resident animation;
- no Kira World runtime capture or virtual-camera control;
- no clean/public artifact and no publication path.

## Integration principle

Home World supplies places and runtime evidence. Avatar Builder supplies
reviewed people and bodies. World Builder supplies reviewed sets. Voice and
conversation systems supply approved performances. Authoritative documents
supply factual grounding. Video Studio must combine those sources without
claiming that a plan, candidate, simulation, or failed experiment is already
working.

