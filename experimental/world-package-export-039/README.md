# Experimental sequenced-airlock export successor039

039 combines the uninstalled037 selected-project package API/native action with
038's paired-door sequencing. It remains isolated. No installation, new preview,
real GLB export, Canvas, graphics, model or native UI run has occurred.

The preview controller remains byte-for-byte038. The export controller adds only
the previous read-only authoring `definitions()` interface to that behavior.
Pairing metadata is derived from explicit authored airlock roles and checked
against exactly two source portals, two door IDs and two distinct leaf nodes.
It includes the complete pending/moving/held/nonclosed peer rule, references back
from doors to their pair, source room/portal identities, session-local state and
explicitly false pressure/engine-runtime claims. This uses scene metadata v2 and
saved package v2 rather than labeling old unsequenced metadata as equivalent.

The GLB builder carries pairing records in scene extras and pair IDs on the actual
hinge groups. Its importer verifies those records, the two leaf/hinge associations
and existing collider ownership. Pose sampling now closes each real controller
door before sampling the next; it never disables sequencing. The package API then
independently checks the emitted policy and leaf/collider links against the
selected geometry, and requires matching importer evidence before writing a
ready manifest. Missing/inconsistent policy leaves an incomplete export.

Validation completed:34 mocked API/callback and cross-language policy checks,
plus13 pure Node metadata/controller checks. The latter verify unchanged038
behavior, exact source associations, malformed policy rejection, canonical
roundtrip and sampling every door without bypassing its peer. The Python gate
accepts the actual Node-produced synthetic metadata and rejects changed sources.
The real GLB extras/importer path is implemented but remains unexecuted.

## Recovery and pending checks

`INPUT-PINS.json` records frozen037/038 inputs. `INSTALL-PLAN.json` maps every
candidate target and exact installed preimage. `RECOVERY-MAP.json` distinguishes
the native038 controller from the augmented export controller and describes the
immutable preview transition. Current saved previews retain their original bytes.
The existing current-preview refresh route will create/reuse the new immutable
build only after root approves the coordinated installation; no preview was
created here. The unmodified037 UI still exports the explicitly selected job.

Old previews are held by039's explicit renderer check.036/037 remain usable
historical artifacts with their earlier controller; they were not edited. Do not
change037's accepted digest to claim039 behavior. A root-supervised actual saved
Mars API export and importer review, followed by native UI inspection, remain
required before calling this package action usable. `run_real_api.py` is prepared
for that future check with an explicit new manifest and digest, not run now.

This exports authored meshes and interaction metadata. It does not implement
game-engine collision/interaction, VR runtime, pressure cycles, exterior EVA
access, operational equipment or improved habitat realism.
