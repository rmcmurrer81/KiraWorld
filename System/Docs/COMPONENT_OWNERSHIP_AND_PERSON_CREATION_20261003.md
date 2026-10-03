# Component ownership and person creation

Recorded from Robert's October 3, 2026 clarification. This records intended
ownership and integration requirements; it does not claim new runtime wiring.

| Component | Responsibility | Project home |
|---|---|---|
| Temporary Creator | Gather subject information and create the mind; pass body and voice requirements onward | Kira World |
| Avatar Builder | Build and validate anatomy, mesh, rig, movement and sensory feedback | Kira World |
| Voice generator | Reuse an existing assigned voice or create a voice from the authorized reference | Kira World |
| NewBrain | Develop and test a learned cognitive backend, with independent persistent identity/history storage | NewBrain research; Kira World integration |
| Video Studio | Future connected production for podcasts, movies and shows starring Kira World participants | Video Studio |

## Creation handoff

Temporary Creator gathers the requested person's information and creates
the mind. It sends a stable identity reference and the relevant body
requirements to Avatar Builder, and sends voice requirements to the voice
generator only when a suitable assigned voice is absent. Robert identifies
Chatterbox with an authorized voice sample as the current voice route,
including his earlier example. Existing voices and histories must be
preserved rather than silently recreated when the brain or body changes.

Record source ownership, requested appearance, body/voice status and actual
backend separately. A body output requires its own anatomy/mesh/rig/movement
and sensory-feedback evidence. Body-specific virtual physiology is another
validation layer. A finished artifact or mind does not by itself activate a
live persona. Private reference media, voice samples, histories and learned
weights stay local and outside source publications.

## Future Video Studio bridge

A later Video Studio version will connect to Kira World to make podcasts,
movies and shows with its participants. Keep stable identity, body and voice
references across the bridge and report actual production outputs. No new
working bridge or filming capability is established by this document.

## Current correction and status

The generic pre-surface rest attachment candidate belongs under
`Avatar/avatar_builder/candidate_sources/rest_attachment_pre_surface_20261003/`.
Its earlier placement in Video Studio recovery commit
`fb0df4af3bc93a46da7454d3c8c5af74306929b8` was a repository grouping mistake.
Compiler fixtures 22 and optional integration fixtures 18 remain unrun.
The packet is not a complete body, promoted reusable method or installed
builder skill. This Kira World project is separate from the paused
standalone New World Builder authoring work.
