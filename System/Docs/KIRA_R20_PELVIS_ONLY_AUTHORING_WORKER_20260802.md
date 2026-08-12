# Kira R20 pelvis-only authoring worker

Date: 2026-08-02  
Status: preflight Attempts 01-03 failed closed; preflight Attempt04 passed;
Author Attempts 01-03 failed closed without a candidate Blend; the smallest
Author Attempt04 coordinate-space repair is prepared and not run

## Attempt01 diagnosis and Attempt02 correction

Fresh-process `preflight_attempt_01` stopped before mutation or Blend save with
`R19 exact regional material binding drifted`. Its exact failure file remains
unchanged at SHA-256
`c7b537780d4871679a298ccc47e0acab9b0e9d190afd7d48d3ccae999e35e03a`.

The material name was correct. The material slot was not. The original R20 plan's
slot-index-1 statement was a planning-record error copied into the worker and
config. Sealed R19 evidence establishes this zero-based order:

1. slot 0: Torso;
2. slot 1: Arms;
3. slot 2: Legs;
4. slot 3: Face;
5. slot 4: Ears;
6. slot 5: Genitalia.

The R19 assembly worker appends the six slots in that order and assigns the exact
376 patch faces to Genitalia. Attempt06 validates the same source order, derives
each bounded-surface-response material, and replaces it at the same index. Its
ordered build-evidence records confirm Arms is second and Genitalia is sixth.

Attempt02 therefore changes only the patch selector from zero-based slot 1 to
slot 5. It retains the exact material name, adds a fail-closed comparison of all
six slots with complete actual-versus-expected error evidence, preserves the old
plan and Attempt01 unchanged, and targets append-only `preflight_attempt_02`.
The exact evidence map is in
`RecoverySprint/continuation_20260802/kira_r20_pelvis_only_authoring_prepared/MATERIAL_SLOT_DIAGNOSIS_ATTEMPT_01_TO_02.json`.

## Attempt02 diagnosis and Attempt03 exact-identity correction

Fresh-process `preflight_attempt_02` passed the corrected material gate and then
stopped before mutation or Blend save with
`frozen separate mesh object missing: Icosphere`. Its exact failure file is
preserved at SHA-256
`ccbfe304673c5527f5be3897b54fc39ba1be23895de32f40dd1e5034303370e2`.

Read-only inspection of the exact sealed Blend's Zstandard frames and Blender 5
`LargeBHead8` ID blocks found no serialized `OBIcosphere`. It found one
unreferenced mesh datablock named `MEIcosphere.001`. Attempt06 had enumerated all
in-memory mesh objects before save; its canonical-name helper stripped `.001`, so
the later freeze ledger promoted that transient unlinked Object record to a
required persisted Object record. This was not a renamed component and no second
protected component is missing.

The original freeze ledger remains byte-for-byte unchanged at SHA-256
`b63bdff693d8efe239f982d72591e4523c860abe89107a79d7b4607e43243873`.
Attempt03 adds a separately hash-bound correction record. The saved protected set
is still exactly 32 components: the primary surface plus 31 persisted separate
objects. Before per-component geometry, UV, and weight hashes, the worker now
requires an exact whole inventory of those 32 protected object-to-mesh bindings
and the 15 exact review-context bindings. A failure reports every missing object,
extra object, and mesh-binding mismatch together. No prefix, suffix, canonicalized
object-name, or nearest-name matching is used.

The sealed diagnosis is:
`RecoverySprint/continuation_20260802/kira_r20_pelvis_only_authoring_prepared/FREEZE_IDENTITY_DIAGNOSIS_ATTEMPT_02_TO_03.json`
(SHA-256
`b4fa8d912761239df62b8d6a3e252bd5ccc07c98cd123d7087b0b89512acdafb`).

## Attempt03 diagnosis and Attempt04 correction

Fresh-process `preflight_attempt_03` passed the material, exact saved-component,
whole-package, geometry, UV, weight, and global freeze gates, then failed closed
before mutation or save because a historical breadth-first component list was
treated as a topological boundary cycle. Its exact failure is preserved at
SHA-256
`3afa5894348d862974e3829c3c4dad5fa0d1aed92bf7c7c503d058d75c0f50ab`.

The original interface probe's `boundary_loops()` traverses a connected
component with a queue. It does not edge-walk the 34-vertex degree-two loop, even
though its output field was named `ordered_boundary_cycles_world_m`. Attempt04
therefore derives adjacency and order only from the sealed R19 topology,
canonicalizes that real edge cycle, and requires a unique one-to-one match to
the 34 full-precision
`adult_boundary_to_base_vertices.records[*].base_world` points at `1e-8 m`.
The probe row order is never used as adjacency. Read-only reconciliation measured
a maximum correct set-match distance of `6.864699219669883e-10 m`; the prior
incorrect sequential comparison measured `0.12830215951281168 m`.

That same whole-preflight diagnostic found exactly four previously unplanned
attributes on the primary surface: CORNER `INT16_2D custom_normal`, CORNER
booleans `.uv_select_vert` and `.uv_select_edge`, and FACE boolean
`.uv_select_face`. Attempt04 gives each an explicit local rule. Every surviving
nonpatch raw element is matched by canonical face/corner identity and restored
exactly. New-patch UV selection values are explicitly false.

Blender 5.1.2 source establishes that `custom_normal` is not an XYZ vector. Its
signed-short pair is encoded relative to a topology-dependent smooth-fan
`CornerNormalSpace`, and `(0, 0)` means use the automatic normal. The production
mesh therefore never calls whole-mesh `normals_split_custom_set`, which can
rebuild all fans and sharp edges. Every surviving raw short2 remains exact;
every smooth new-patch corner receives explicit `(0, 0)`. Decoded corner normals
must remain exact outside the touched 34-vertex seam fan. At that fan, preserved
and new decoded normals must pass minimum/median dot-product continuity gates,
unit-length and same-vertex smoothness gates, followed by the two existing
opposite-light normal heatmaps. This is the smallest rule that does not pretend
byte-identical short2 and byte-identical decoded normals are simultaneously
possible after changing a fan's topology.

The sealed correction record, including Blender 5.1.2 commit-linked source
authority, is
`RecoverySprint/continuation_20260802/kira_r20_pelvis_only_authoring_prepared/INTERFACE_AND_ATTRIBUTE_DIAGNOSIS_ATTEMPT_03_TO_04.json`.

## Outcome

R20 now has a bounded, fail-closed authoring path for replacing only the rejected
R19 pelvic insert. The approved Kira face, head, eyes, brows, warmer skin graphs,
upper body, limbs, hands, feet, nails, native rig, weights outside the patch, and
movement actions remain frozen.

The implementation is not a generic body rebuild and does not reuse the rejected
R19 radial/centroid method. It creates a connected 3D clamped curvilinear surface
against the exact 34-vertex seam, with 740 new vertices and 756 quads. It creates
no separate anatomy object and uses no Boolean, shrinkwrap, join, global weld,
global normal recalculation, donor interior geometry, activation, assignment,
export, clothing, publication, or upload.

## Sealed inputs

- R19 Blend SHA-256: `dee1017f72c50dfba6583864bb1f9ec81405e2ef6d37f7c724831a24df49b53f`
- R19 49-member package-manifest SHA-256: `9c7038b60e2c712e49e810c0b7f7932bf36a18042dd00a6951834be59bb40f0c`
- R20 plan SHA-256: `d9907f9ac7db74999ce2853b8865f614ccacabfabacef82b3111374dd89d0035`
- R20 nonpelvic freeze-ledger SHA-256: `b63bdff693d8efe239f982d72591e4523c860abe89107a79d7b4607e43243873`
- R20 source/donor-decision ledger SHA-256: `3076b54d86a705d599a142816ace5688bf34b89ce230d0ba11bfddcd55964ee4`
- Licensed 34-vertex interface evidence SHA-256: `01beed05140bb22bff2de23922d280fb312952078b496f16fb4fd80d9d742c86`

The worker validates the manifest hash, every listed member's size and SHA-256,
duplicate paths, path containment, and exact member-set equality. It validates all
32 protected mesh components (primary plus 31 persisted separate objects), all 15
review-context meshes as a separate exact set, the 188-joint rest structure,
actions, material graphs, primary object transform/modifiers, and the canonical
nonpatch mesh subset.

## Exact patch and topology

The old mask must simultaneously satisfy all of these conditions before mutation:

- exact zero-based material slot 5 and material name
  `R19_WarmTexture_Genitalia_Attempt06_BoundedSurfaceResponse`;
- 376 selected faces in one face-connected component;
- 206 incident vertices;
- 172 removable vertices referenced by no preserved face;
- 34 interface edges and vertices forming one connected degree-two cycle;
- one selected and one unselected face on every interface edge;
- exact coordinate correspondence with the licensed interface within `1e-8 m`;
- exact sealed world bounds.

The replacement contract is:

- 34 existing seam vertices reused exactly;
- two 34-vertex clamped collar rings;
- a 21 by 32 feature-aligned core;
- 740 new vertices, 756 quads, 1,529 patch edges;
- connectivity SHA-256
  `761981c7b14b769fb1d750deef946ab95019821c2280383d7e1c5cf15c47b749`;
- expected joined body: 13,180 vertices, 38,517 edges, 25,316 faces,
  one component, 330 existing boundary edges, 23 existing boundary loops;
- maximum patch valence 6, minimum face area `1e-10 m²`, maximum quad edge
  ratio 3.0, zero degenerates, zero new boundary/nonmanifold edges.

The 34-to-102 transition uses a golden-tested two-quad pattern for each seam
segment. Local collar/inset floors and a fixed-boundary harmonic damping tail keep
the strict 3.0 edge-ratio gate on smooth and deliberately uneven seam fixtures.
They do not move the exact seam or alter topology.

## External landmarks and truth boundary

The same connected primary surface receives named point-domain semantic sets and
project-space centroid/bounds evidence for:

- mons;
- paired labia majora and minora;
- clitoral hood and restrained glans;
- vestibule;
- external urethral-meatus rim and shallow blind cap;
- vaginal opening/introitus rim and shallow blind cap;
- posterior fourchette;
- continuous perineum;
- separate anal-region rim and shallow blind cap.

The required visible order is hood/glans, urethral meatus, introitus, fourchette,
perineum, then the separate anal region. These are external-surface geometry and
semantic review hooks only. No bladder, ureter, urethral canal, sphincter, internal
vagina, cervix, uterus, ovary, bowel, rectum, pelvic-floor function, continence,
fluid transport, elimination, reproduction, pregnancy, or intimate behavior is
implemented or claimed.

The existing bounded regional material is retained byte-for-graph. New faces use
the existing material slot and harmonic seam-derived UVs. This preserves natural
texture response; it is not a painted substitute for absent geometry.

## Preservation and rigging

All 12,440 surviving body vertices and 24,560 nonpatch faces are compared using
canonical coordinate/topology records rather than unstable post-edit indices.
Coordinates, winding, material indices, UVs, weights, selections, edge sharpness,
modifiers, object transform, and every raw surviving planned attribute must
match exactly. Decoded custom normals must match exactly outside the locally
touched seam fan; the seam fan has the explicit continuity gate above. The same
hashes and local gate are rerun after save/reopen in a fresh process.

All 34 seam positions, UVs, and weights are pinned. Only the 740 new vertices get
new weights. Their weights are solved harmonically from the seam, then projected
deterministically to the strongest four existing native-bone groups and normalized
to one. No surviving weight is normalized or rewritten.

## Movement and clearance acceptance

The worker evaluates 14 required states against source-state baselines:

- neutral;
- left, right, and bilateral 30°, 55°, and 80° knee bends;
- bounded hip-open diagnostic;
- selected seated-open-hip;
- toilet-seated contact/clearance;
- selected supine.

Every state requires zero patch-related exact self-intersections, zero new nonpatch
pairs relative to the matching R19 state, zero patch-to-nail/eye intersections,
zero body-to-nail crossings, no collapsed/inverted patch quad, all external
landmark sets, unchanged actions/rest rig, and exact neutral restoration.

The toilet diagnostic records the exact seat/opening dimensions, patch vertices
inside the opening, vertices over the solid rim, minimum signed rim gap, maximum
penetration depth, penetration count, and the configured clearance. It is a
contact/clearance measurement, not a claim of internal bathroom function.

## Visual review package

Fresh-process verification renders 33 private PNGs per passing candidate:

- full-body front and both three-quarter views;
- protected neutral front, both three-quarter views, both profiles, inferior,
  and posterior relationship;
- hip-open front and inferior;
- seated front-three-quarter, side contact, and toilet contact;
- all nine knee-bend views;
- supine side and inferior;
- four wire overlays;
- two opposite-light normal heatmaps;
- one flat neutral-material comparison.

Ordinary material views remain controlling. Wire, normal, and flat views are only
diagnostics. The package asks Robert to compare directly against the exact R19
visible rejection: inverted trapezoid/triangular pasted panel, straight superior
edge, sharp diagonal borders, central dark cavity/crease, and missing readable
external landmark relationships. Passing structural tests is not visual approval.

## Prepared implementation

- Pure contract: `Core/kira_r20_curvilinear_pelvic_patch.py`
- Blender worker: `tools/blender_author_kira_r20_pelvis_only.py`
- Pure/static tests: `Testing/test_kira_r20_pelvis_only_authoring.py`
- Config: `RecoverySprint/continuation_20260802/kira_r20_pelvis_only_authoring_prepared/AUTHORING_CONFIG.json`

Revalidated after the Attempt04 interface/attribute correction on 2026-08-02 without
rerunning Blender or using the GPU:

```text
py -m py_compile Core\kira_r20_curvilinear_pelvic_patch.py tools\blender_author_kira_r20_pelvis_only.py Testing\test_kira_r20_pelvis_only_authoring.py
py -m unittest Testing.test_kira_r20_pelvis_only_authoring -v
Ran 20 tests in 10.835s - OK
```

The historical append-only `preflight_attempt_04` command subsequently ran once
and passed. Its manifest SHA-256 is
`f59922da78291131808ee691c1ec502c1b5f634f690ce8017978b01ff2037c99`.

## Author Attempt01 failure and Attempt02 correction

Author Attempt01 ran exactly once after Attempt04 preflight passed. Both
configured candidates failed closed before `_prepare_candidate_fields` and
`_apply_local_patch`, and neither candidate Blend was saved. The exact shared
error was `evaluated R20 patch contains a non-quad`.

That wording was false. `_author_candidate` first calls `run_pose_suite` on the
unchanged R19 source with `baseline_by_pose=None`. The old implementation
unconditionally called `evaluated_patch_quality`, which selected the rejected
376-face source panel through shared material slot 5 and applied the generated
R20 756-quad requirement to it. The exception occurred before either candidate
was constructed, so Attempt01 provides no evidence that either generated patch
contains a non-quad.

Attempt02 changes only this call boundary. The R19 baseline still records exact
self-intersection, body-to-nail, contact, pose-restoration, action, and rig
truth. It does not run generated-patch cross-intersection, 756-quad quality, or
R20 semantic-landmark gates when no generated patch exists. After
`_apply_local_patch`, the candidate suite still runs all three gates and every
existing structural, movement, contact, intersection, freeze, attribute, and
normal gate.

Unchanged hard requirements include:

- exactly 756 generated faces and every face a quad;
- minimum evaluated face area greater than `1e-10 m2`;
- zero collapsed or inverted generated quads;
- the same golden connectivity hash, topology, candidate parameters, UVs,
  weights, and all numeric thresholds;
- exactly two private, inactive, unassigned, unpublished candidates;
- no activation, export, publication, clothing, or runtime assignment.

Attempt02 pure/static verification on 2026-08-02:

```text
py_compile: PASS
Ran 23 tests in 10.557s - OK
Blender Author Attempt02 executed: NO
```

The exact proposed command is sealed in
`RecoverySprint/continuation_20260802/kira_r20_pelvis_only_authoring_prepared/AUTHOR_ATTEMPT_02_COMMAND.md`.

## Author Attempt02 failure and Attempt03 correction

Author Attempt02 retained the corrected source-baseline boundary and ran once.
Both candidates again failed closed before `_prepare_candidate_fields` or
`_apply_local_patch`, this time because `evaluated_pose` requested a generic
left lower-leg bone that does not exist in Kira's native R19 rig. Neither
candidate patch was constructed and no candidate Blend was saved.

The exact sealed R19 `BUILD_EVIDENCE.json` identifies the native shin bones as
`lShin_07` and `rShin_023`. Its two supported seated records prove the axis:
candidate A rotates both shins `[72, 0, 0]` degrees XYZ, and candidate B rotates
both `[78, 0, 0]`. The selected action remains
`KIRA_R19_ATTEMPT05_SEATED_OPEN_HIP_A`.

Attempt03 therefore changes only:

- the left manual-knee mapping to `lShin_07`;
- the right manual-knee mapping to `rShin_023`;
- the manual diagnostic rotation from Euler Z to Euler X.

The 30/55/80-degree diagnostic angles, complete pose inventory, selected seated
and supine actions, patch geometry and topology, both candidate shapes,
materials, and every numeric acceptance threshold remain unchanged. Static
tests also require the old generic names to be absent from the current worker
and config and parse the frozen R19 evidence for both exact native names and X
axis rotations.

The manual 30/55/80-degree states are controlled isolated shin-flexion stress
diagnostics, not exact reproductions of the complete R19 actions. The frozen
seated action also contains thigh and other pose-bone rotations. Natural seated
and supine owner views continue to use
`KIRA_R19_ATTEMPT05_SEATED_OPEN_HIP_A` and
`KIRA_R19_ATTEMPT05_SUPINE_FACE_UP_A` at frame 30.

```text
py_compile: PASS
Ran 26 tests in 10.579s - OK
Blender Author Attempt03 executed: NO
Attempt03 output exists: NO
```

The exact proposed command is sealed in
`RecoverySprint/continuation_20260802/kira_r20_pelvis_only_authoring_prepared/AUTHOR_ATTEMPT_03_COMMAND.md`.

## Author Attempt03 failure and Attempt04 coordinate-space correction

Author Attempt03 retained the corrected baseline boundary and exact R19 native
knee/action bindings. It completed the baseline pose suite, then both bounded
candidates failed inside `_prepare_candidate_fields`, before
`_apply_local_patch`, with:

`seam median edge scale is implausible: 1.8541125424006801`

The exact Attempt03 summary, top failure, and both candidate failures are
preserved. There were zero successful candidates, zero patch applications, and
zero Blend saves. The R19 source hash remained exact.

The failure was a unit-space mismatch. Source mesh coordinates are body-local,
while the pure geometry contract and its feature offsets/area thresholds are in
project meters. The immutable preflight04 canonical seam arrays establish:

- local median edge scale: `1.8541125424012472`;
- world median edge scale: `0.017658196540973933 m`;
- world/local ratio: `0.009523799735535436`.

Attempt04 therefore changes only the coordinate boundary:

1. It derives the live construction seam at full precision from the exact
   canonical seam IDs.
2. It independently cross-checks those points against the hash-bound
   preflight04 canonical arrays at the existing `1e-8 m` interface tolerance.
3. It applies the full exact R19 object matrix to seam and exterior-ring points.
4. For each seam sample, it inverse-transpose transforms and normalizes every
   incident exterior face normal before equal-weight averaging.
5. It constructs the patch, compares winding normals, and evaluates geometry
   quality in one project/world-meter space.
6. It inverse-transforms only the 740 generated positions for body-local BMesh
   insertion. The 34 original seam vertices and local coordinates are reused
   exactly.
7. Structural evidence distinguishes exact body-local seam identity from the
   world-meter seam delta.
8. Fresh saved-candidate verification transforms saved local positions to world
   meters before running the same quality contract.

The seam local/world/local roundtrip is bounded in body-local units. The
generated project/local/project roundtrip is separately bounded in meters.
Both bounds are `1e-9` in their explicitly named unit.

The worker requires the exact hash-bound R19 source matrix. Arbitrary transform
variation is not supported; nonfinite, singular, reflected, projective, or
different source transforms fail closed. The reusable pure affine math is
tested with nonuniform scale and shear, but this bounded authoring worker does
not broaden its accepted source beyond the exact sealed R19 matrix.

No topology, candidate parameters, acceptance thresholds, material binding,
pose/action inventory, manual knee angles, native shin mapping, candidate
count, or private/inactive policy changed.

```text
py_compile: PASS
Ran 33 tests in 10.377s - OK
Blender Author Attempt04 executed: NO
Attempt04 output exists: NO
```

The exact proposed command is sealed in
`RecoverySprint/continuation_20260802/kira_r20_pelvis_only_authoring_prepared/AUTHOR_ATTEMPT_04_COMMAND.md`.
