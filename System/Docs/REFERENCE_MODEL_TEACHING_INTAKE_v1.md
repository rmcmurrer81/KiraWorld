# Reference Model Teaching Intake v1

## Purpose

`Core/reference_model_teaching_intake.py` inventories a supplied 3D-model
folder without modifying or copying its files. The intake is a private teaching
and review boundary for Avatar Builder, the movement library, and World
Builder. It is not a model-training, import, activation, or approval command.

Run it with:

```powershell
py tools\intake_reference_model_teaching_folder.py C:\Users\robmc\Desktop\91
```

The output is content-addressed under:

```text
Data/reference_model_intake/<folder>/<inventory-hash-prefix>/
```

It contains a full manifest and four routes:

- Avatar Builder structural/motion references;
- movement-library untrusted draft sources;
- World Builder context references;
- blocked/restricted/manual-review references.

Immutable pointer records are also written beneath each consumer's normal
reference-intake area:

```text
Avatar/avatar_builder/reference_intake/
Avatar/movement_library/reference_intake/
Data/world_builder/reference_intake/
```

The pointers bind the source manifest and route by SHA-256. They expose the
evidence to builder tooling while retaining `automatic_import_allowed=false`.

## What is inspected

Every file receives its relative path, byte size, modification time, SHA-256,
family grouping, exact duplicates, and matches against existing Avatar Builder
catalog hashes.

For GLB files, the intake reads the glTF JSON chunk and records container
integrity, meshes, primitives, materials, textures, skins, joints, joint/weight
attributes, animations, animation channels/durations, morph targets, and a
bounded sample of node/joint names. It does not render the model or claim that
an animation looks natural.

For ZIP and USDZ files, it reads archive metadata only. It records entry types,
compressed/uncompressed sizes, embedded model names, license/readme entries,
encryption, unsafe paths, and extreme compression ratios. It never extracts an
archive during intake.

## Fail-closed rights and runtime rules

Downloaded models are reference evidence, not resident bodies or ready-made
world assets. Unknown-rights files are context-only. License-looking text found
inside an archive is recorded as an unreviewed claim; it is not reuse authority.

Every route therefore sets these values to false:

```text
model-weight training
copying into the builder library
copying as an avatar body
animation retargeting
runtime world import
person/body activation
public export
```

A later exact-hash license review may authorize a narrowly defined use. It
still does not prove body topology, likeness, maturity, stable deformation,
ground contact, object contact, navigation, realism, or owner approval.

## How motion references may help

Human animations can teach *hypotheses* about cadence, weight shift, joint
paths, arm swing, seated posture, hand reach, or contact timing. A source clip
does not become a Kira motion merely because it has an animation track.

Before promotion, a separately licensed source must be mapped to the shared
foundation rig and stored as an untrusted draft. Visible evidence must then
show that body state, foot/hand contacts, route, prop state, and spoken activity
all agree. Stylized dance, zero-gravity, weapon, environmental, and other
special-purpose animations are kept separate from neutral daily movement.

## How World Builder references may help

Door, room, furniture, prop, and environmental models can teach component
breakdown, likely interaction anchors, scale questions, and performance-budget
questions. Unknown-rights geometry cannot satisfy the World Builder reference
evidence gate and cannot be imported. Real-location reconstruction still needs
the required photo/video/plan/measurement evidence, and unsupported rooms stay
behind closed, locked, collision-solid portals.
