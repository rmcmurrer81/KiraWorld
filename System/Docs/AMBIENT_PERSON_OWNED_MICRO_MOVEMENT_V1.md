# Ambient person-owned micro-movement v1

## Purpose

Synthetic people should not look frozen while standing and should not need a
user to issue motor commands for ordinary small bodily adjustments. The Home
World runtime now has a reusable ambient-expression layer. Kira is the first
live integration; other people may adopt it when their exact body and rig are
ready.

The layer supplies subtle breathing, weight settling, head turns and tilts,
shoulder and wrist settling, tiny finger movement, and an occasional small
smile. These are procedural animation details, not claims about hidden thought
or consciousness.

## Ownership boundary

- Ambient movement belongs to the active synthetic person's animation policy.
- User text is not parsed into ambient motor output.
- A deliberate person-owned action always takes priority.
- Candidate stage directions remain separate future-body records under
  `CANDIDATE_OWNED_MOVEMENT_INTENTS_V1.md`; this layer does not execute them.
- The layer never changes root position, world heading, root rotation, or any
  object/bone scale.

## Runtime priority

1. A deliberate action, posture, prop contact, door interaction, doctor test,
   or dressing action pauses ambient movement.
2. Walking, jogging, running, dodging, or swimming keeps only eight percent of
   the body settle and disables hand and face ambient movement.
3. Matched real voice playback attenuates body/hands and disables the ambient
   smile so it cannot fight lip sync.
4. Idle standing receives the complete but tightly bounded layer.

Every animation frame restores the exact recorded bind quaternions before any
local offsets are added. This prevents accumulation and drift.

## Smile limitation

Kira's current body does not have reviewed facial blendshapes or a facial bone
rig. The only available smile is a very small corner lift on the already-
authored connected lip island used by the existing-mouth lip-sync system. It
creates no mesh, scene node, or second mouth. It is disabled during speech.
This is not a substitute for a future reviewed facial-expression rig.

## Files and checks

- Pure reusable layer: `ambient_micro_movements.js`
- Kira runtime adapter: `main.js`
- Existing-lip integration: `existing_mouth_lipsync.js`
- Bounds/suppression/drift tests: `Testing/test_ambient_micro_movements.mjs`
- Existing-mouth tests: `Testing/test_existing_mouth_lipsync.mjs`

The tests cover deterministic identity profiles, hard numeric bounds, zero root
translation/rotation/scale, deliberate-action pause, locomotion attenuation,
lip-sync suppression, bind-pose reset ordering, and no second-mouth creation.

## 2026-07-23 posture and dispatch checkpoint

The current Home World adds more relaxed elbow/finger settling and keeps the
ambient layer subordinate to deliberate action, locomotion, posture and
matched voice playback. Deterministic tests and the movement-realism verifier
pass, but human-quality comfort and naturalness remain **AWAITING ROBERT
REVIEW** in an ordinary session.

The dialogue-to-body bridge may dispatch only a supported explicit
first-person choice, including go outside, sit on the couch, lie on the couch,
or lie on the bed. It rejects negated/excluded alternatives and uses
collision-checked routes. This must not be confused with model-written stage
directions: those remain unexecuted future-body records under
`CANDIDATE_OWNED_MOVEMENT_INTENTS_V1.md` and cannot prove an action happened.

No Kira activation or life loop was used for this checkpoint. Runtime source,
tests and verifier evidence are preserved in
`System/Docs/evidence_packages/KIRA_CURRENT_WORKSTREAM_SAFE_CHECKPOINT_20260723_034919/`.
