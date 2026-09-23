# Reusing the World Builder core

Robert's September23 direction is to reuse the World Generator core in future
games and VR products that could help fund continued work, as KiraWorld voice
work is reused in Video Studio. This is an architecture direction for the current
codebase, not a new product, hackathon or claim of engine/VR readiness. Finishing
ordinary World Builder and Video Studio use remains the current priority.

Keep world data and deterministic construction separate from the desktop UI,
research/model jobs, personal memories and a particular renderer. Games and VR
could consume a versioned scene package through adapters. They should not need
to copy the owner's worlds, research cache or native application wholesale.

## What exists and what must be separated

| Current source | Reusable information | Current constraint |
|---|---|---|
| Compiled geometry | Room bounds/IDs, functional program, structural box primitives, portals, support surfaces, routes and colliders | Primarily axis-aligned rooms and supported horizontal walking |
| Authored dressing plan025 | Deterministic equipment IDs/kinds/roles, room membership, transforms, bounds, extra colliders and omissions | Habitat recipes; not a general catalog of every building type |
| Dressing renderer025 | Authored multipart objects and material choices | Imperative Three.js mesh/material/canvas construction; no neutral mesh recipe yet |
| Door/controller024–025 | Shared pose/collision, swing reservation, nearby action, open/close and obstruction states | Hinges and target angles are partly private implementation state; public assembly descriptions expose room names rather than canonical room IDs |
| Immutable preview027–028 | Exact source bindings, separate presentation revisions, repeatable reuse | Local filesystem paths and loopback presentation are installation details, not a portable asset format |

## Proposed neutral scene contract

Use a plain-data `scene.json` manifest with a schema version and producer revision.
This would be a new export contract, leaving compiled geometry and existing saved
preview contracts intact. Export authoring defaults separately from session state.

| Field | Required meaning |
|---|---|
| `coordinate_system` | Metres, right-handed, Y-up; explicitly declare front direction and quaternion component order. Adapters must convert units/axes once. |
| `rooms` | Stable ID, display name, functional role, bounds, access classification; labels do not imply working equipment. |
| `nodes` | Stable ID, parent ID, room ID, semantic kind, local transform and either a versioned primitive recipe or package-relative mesh reference. |
| `materials` | Neutral base colour, roughness, metallic and emissive values, plus package-relative generated texture references and colour-space declarations. Backend-only material options stay in adapters. |
| `colliders` | Stable collider and owning-node IDs, shape, local transform/bounds, static/kinematic classification and conservative-proxy status. Render visibility is independent of collision. |
| `navigation` | Entry/spawn, authored route checks and support regions, explicitly tagged as horizontal supported walking rather than a complete engine navmesh. |
| `interactions` | Action ID, target node, capability, reach/rule parameters and referenced state-machine version. No keyboard, mouse or VR-button codes. |
| `doors` | Portal and room IDs, leaf/frame IDs, local hinge transform, rotation axis, closed/open target angles, duration/rate, swing bounds and collision-policy version. |
| `provenance` | Source contract/revision hashes, original/authored/derived classification, package asset bindings and relevant ownership/licence information. Exclude absolute paths, research caches and personal memories by default. |
| `capabilities` / `limitations` | Explicit supported behaviour and unimplemented behaviour. Preserve procedural/unapproved status; a successful export is not a realism certificate. |

For example, an EVA locker remains a static visual object with its collider;
exporting `kind: eva_lockers` must not make its doors interactive. A habitat door
may expose `toggle_door`; a glovebox currently exposes no simulated science action.
Room function, visual representation and working behaviour are separate fields.

## Interaction and persistence boundary

An application submits an intent such as `{ action: "toggle_door", target_id,
actor_id }`. The controller validates actor position, interaction reach and
occupied swing space, then returns an accepted/held result. It advances with
bounded simulation time and emits pose/state changes for the renderer and
collision adapter. Desktop buttons, game controls or future tracked hands map to
the same intent interface; tracking itself is not currently implemented.

Current doors use conservative leaf AABBs and a swept reservation, not a general
rigid-body solver. Preserve that policy as an explicit supported mode. A future
engine-native physics adapter needs its own contact tests before replacing it.
Pressure interlocks, networking, arbitrary stairs, teleport and multiplayer
authority are outside the present implementation.

Session saves should later refer to a scene content hash and stable object IDs.
Keep camera/actor/door state in a separate versioned save, with migrations that
reject unknown objects. Today's session-local door state is not persistent; this
document does not add persistence or change any owner world.

## Smallest useful implementation sequence

1. Add a pure, opt-in metadata exporter over already verified compiled geometry,
   the dressing plan and an explicit door-definition description. Export relative
   asset IDs and a strict capability list. Do not fetch research or run models.
2. Refactor the existing authored multipart equipment routines into a plain-data
   primitive recipe consumed by the existing Three.js renderer. Prove unchanged
   transforms, material choices, bounds and door behaviour before any new adapter.
3. Add a portable visual asset path, potentially glTF/GLB, while retaining semantic,
   collision, navigation and interaction metadata in the scene manifest. A visual
   mesh container alone does not preserve game behaviour.
4. Exercise a round trip through a small independent consumer with the same
   synthetic fixture. Only then select an engine adapter and evaluate a specific
   game/VR use case, licensing/distribution model and device performance budget.

Acceptance tests should compare stable IDs, room membership, transforms, rendered
mesh bounds versus conservative colliders, closed-door blocking, opening/closing,
swing obstruction and a clear route through an open door. Add axis/unit round-trip
tests, schema rejection, missing assets and content-hash failure tests. A future
VR build additionally needs measured frame timing, locomotion comfort, tracked
input and accessibility review on actual hardware.

No exporter, engine integration, game, VR runtime or commercial licence decision
is implemented by this document. Root's027 visual review covered the doorway and
airlock only; the presentation remains procedural and other rooms need review.
028 current-preview reopening is the immediate product priority.
