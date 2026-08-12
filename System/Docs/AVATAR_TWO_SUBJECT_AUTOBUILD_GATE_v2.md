# Avatar Two-Subject Auto-Build Gate v2

Date: 2026-07-17

## Purpose

Avatar Builder may not start batch authoring after one promising body. Two
different canonical people must each pass an exact, owner-approved body review
first. This prevents one lucky render, one overfit base, or two variants of the
same person from being treated as proof that the builder generalizes.

Implementation:

```text
Core/avatar_positive_proof_gate.py
Core/avatar_two_subject_autobuild_gate.py
tools/evaluate_avatar_positive_proof_gate.py
tools/evaluate_avatar_two_subject_autobuild_gate.py
Avatar/avatar_builder/policies/positive_proof_autobuild_gate_v1.json
Avatar/avatar_builder/policies/two_subject_autobuild_gate_v2.json
```

The evaluator is read-only. It has no mesh author, Blender worker, queue write,
activation, live-body replacement, registry promotion, or public-export path.

## Two distinct canonical subjects

The identity registry supplies both `canonical_candidate_id` and `subject_id`.
The gate requires at least two different `subject_id` values. Aliases, rebuilds,
outfits, spa variants, and other body variants of one person still count as one
subject. The two qualifications must also bind different body SHA-256 values;
two names cannot make one generic body count twice. A shared standard rig is
allowed only when each exact subject body independently passes its rig and
deformation evidence.

A legacy v1 positive proof now qualifies only one subject. Its result is:

```text
positive_proof_passed_subject_qualification_only
release_allowed: false
```

The legacy release-plan function always rejects. Its CLI never returns the old
batch-release success code: exit `3` means one subject qualified but the batch
gate remains mandatory; exit `2` means the subject qualification is blocked.

## Exact artifacts required for each subject

One qualification binds separate body, eyes, hair, clothing, and rig files by
path plus SHA-256. It must pass the existing complete positive-proof gate and
also bind six immutable domain records:

```text
topology
rig_and_deformation
skin_integrity
ground_contact
object_contact
clothed_visual_quality
```

Each domain record must:

- identify the exact candidate, canonical subject, and build;
- bind all five component hashes;
- record a complete `pass` decision against the exact observed build;
- bind at least one retained source artifact by exact path and SHA-256;
- keep runtime activation and public export false.

The domain checks retain the more detailed body gates: correct maturity
topology, stable rig, limb/face/posture deformation, skin/material continuity,
realistic eyes, walk/stop/turn, sit/stand/lie/rise, feet/ground contact, prop
contact, separate clothing, likeness, clothed visual integrity, privacy, and
owner visual review. A Boolean without its bound domain evidence cannot pass.

## Immutable owner review

Robert's approval record must be stored beneath the configured immutable owner
review root and named by its own SHA-256:

```text
<sha256>.json
```

It binds the exact canonical subject, build, five component hashes, and all six
domain-evidence hashes. It explicitly confirms clothed in-motion review,
full-body and face/eye review, skin/deformation, ground contact, and object
contact. It may count that body toward the two-subject gate, but it cannot
release auto-build by itself.

Subject proof and domain-evidence records use the same content-addressed rule.
Path escape, changed bytes, changed hashes, absolute paths, missing files, or a
symlink anywhere in a bound path fail closed. No tool in this pass creates or
forges owner approvals.

## What a passing batch gate permits

After two distinct subjects pass, the evaluator may report:

```text
two_subject_gate_passed_batch_authoring_eligible_not_queued
```

That permits only a dry-run, one-at-a-time authoring schedule. It does not
queue a job. Each later person still needs their own identity/version/maturity,
source, topology, rig, skin, contact, clothing, privacy, and owner-review gates.
It never grants runtime activation, live-body replacement, public export, or
automatic owner approval.

## Current status and command

Run:

```powershell
python tools\evaluate_avatar_two_subject_autobuild_gate.py --dry-run-plan
```

The current project result is intentionally:

```text
status: locked_awaiting_two_distinct_owner_approved_bodies
qualified bodies: 0
distinct canonical subjects: 0 / 2
batch auto-authoring allowed: false
queue created: false
```

No current Kira, Beth, Gwen, Robert, Marinette, or other body was silently
promoted to satisfy this gate.
