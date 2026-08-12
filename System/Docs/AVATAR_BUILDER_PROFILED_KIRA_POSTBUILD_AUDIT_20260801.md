# Profiled Kira private-candidate post-build audit — 2026-08-01

## Scope correction — legacy R15 contract only

This auditor is bound to the legacy R15 exact v1/v2 method IDs and 17-view
contract. It must not be applied to, or represented as having accepted, the
R17 23-core-plus-3-supplemental delivery package. R17 has its own bound build
evidence, component reports, source/live hash checks, and visual review, but no
claim is made that it passed this incompatible legacy auditor. A future R17
fresh-process auditor requires a separately versioned contract and explicit
owner authorization if additional work is requested after visual review.

This is the independent downstream engineering gate for a newly built
`kira_profiled_adult_candidate_*` Blend. It does not build or repair a body.
It opens one exact SHA-256-bound private candidate read-only, evaluates the
actual skinned mesh, and writes append-only evidence outside the candidate
folder. Passing this audit does not qualify runtime, approve activation, or
replace Robert's visual review.

## Safety and evidence boundary

- Input Blend, `BUILD_EVIDENCE.json`, and optional private GLB must be direct
  members of the same new `Avatar/private_owner_review/<candidate_id>` folder.
- The caller supplies the exact hash of every input. Each is rehashed before
  and after the audit.
- Main evidence is created only in a new direct child of
  `RecoverySprint/continuation_20260801/profiled_kira_candidate_audits` named
  `<candidate_id>__audit_attempt_<id>`.
- The main artifact is
  `PROFILED_KIRA_CANDIDATE_POSTBUILD_AUDIT.json`. It is never overwritten.
- Optional GLB evidence is appended later as
  `PROFILED_KIRA_PRIVATE_GLB_FRESH_IMPORT_AUDIT.json`; that filename also may
  not already exist.
- Both Blender stages require a background, empty, untouched factory-startup
  scene and disabled script auto-execution.
- The tools do not render, save a Blend, export, clothe, assign, register,
  activate, publish, upload, or mutate the candidate. Pose changes and removal
  of default factory objects occur only in unsaved process memory.

## Main Blend engineering gates

The main auditor requires all of the following:

1. The build evidence binds the exact candidate, current exact validated
   builder configuration, retained adult groups, inactive/private policy, and
   optional GLB hash.
2. Exactly one mesh is marked `primary_surface=True`. It must identify as a
   confirmed adult-female Kira-styled candidate using the exact continuous v1
   base method and configured v2 structured-detail method. The body, builder
   configuration, and `BUILD_EVIDENCE.json` must agree on both IDs. The v2
   report must prove no new exact intersection, unchanged topology, unchanged
   normalized rig weights and landmark names, no separate/Boolean/copied
   anatomy geometry, and curved-posterior-frame landmark rebinding. Exactly one
   intended official armature and one
   vertex-group armature modifier must be bound to it.
3. Every primary-body vertex has a normalized deform-bone weight sum within
   `1e-4`, no vertex is unweighted, no vertex has more than four positive rig
   influences, and no unknown non-landmark weight group carries a positive
   assignment.
4. The exact ten adult relationship groups and six required subgroups are
   retained. Geometry is measured in the exact qualified authoring frame
   scaled to the profile height of 1.651 m. Rest geometry must be connected,
   noncollapsed, have measurable area/extent/relief, and pass the established
   left/right, anterior/posterior, and outward/recessed margins.
5. Rest topology must be one closed component with zero boundary edges,
   nonmanifold edges, degenerate faces, coincident duplicate triangles, and
   exact genuine nonadjacent intersections.
6. The evaluated mesh is measured in seven states: rest, symmetric upper-leg
   flexion, asymmetric upper-leg lunge, symmetric pelvis opening, left knee
   flexion, right knee flexion, and combined bilateral knee flexion. The two
   knee states use the saved exact axis-solved actions, and the combined state
   applies both.
7. Every posed result must remain finite with the exact rest topology. Global
   edge ratios are bounded to `0.35..2.0`; edges wholly in the pelvic landmark
   patch are bounded to `0.55..1.55`. Every adult relationship region must
   retain at least 35% of rest extent, 35% of rest RMS radius, and 15% of rest
   incident area. Meaningful relationship ordering and relief must retain
   their recorded direction and bounded fractions of their rest margins.
   Every pose must add zero exact face-pair intersection touching a
   pelvic-patch face relative to the exact rest pair set; no pose may add more
   than eight exact global face pairs over the zero-pair rest baseline.
8. All 17 required private PNG names are inventoried, header-validated, sized,
   and SHA-256 hashed. The auditor does not inspect or accept their visual
   content. Missing views block the complete post-build gate.

Even when every engineering gate passes, the artifact records
`owner_visual_acceptance=false`, `runtime_qualified=false`, and
`activation_allowed=false`.

## R15 audit result

Audit attempt 1 for
`kira_profiled_adult_candidate_r15_20260801_114658` is preserved at
`RecoverySprint/continuation_20260801/profiled_kira_candidate_audits/kira_profiled_adult_candidate_r15_20260801_114658__audit_attempt_01`.
The evidence SHA-256 is
`ef3fae09292fdba1630751ff1ab6b92aaaa38a5cb1929e15e9c0716def29860b`.

The audit accepted the exact candidate/config/build-evidence binding, one
primary body, exact v1+v2 method metadata, intended armature, normalized
maximum-four weights, inactive/private safety flags, and all 17 required PNG
names. It rejected the body because rest had one exact pelvic intersection and
failed relationship ordering/relief. Every deformation pose failed at least
one edge-stretch or relationship-preservation gate; symmetric pelvis opening
added one exact pelvic pair and symmetric upper-leg flexion added 17. The
candidate therefore remains inactive and visually rejected. No GLB audit is
authorized or useful for this rejected attempt.

## Main command

Compute the three exact hashes first and choose a new append-only attempt name.
Run from the repository root in a new process:

```text
blender --background --factory-startup --disable-autoexec --python tools/blender_audit_profiled_kira_adult_candidate.py -- --blend Avatar/private_owner_review/<candidate_id>/<candidate_id>.blend --blend-sha256 <64-lowercase-hex> --build-evidence-sha256 <64-lowercase-hex> --output-dir RecoverySprint/continuation_20260801/profiled_kira_candidate_audits/<candidate_id>__audit_attempt_<id>
```

If the build produced a private GLB, bind it during the main audit too:

```text
--optional-private-glb Avatar/private_owner_review/<candidate_id>/<candidate_id>.private.glb --optional-private-glb-sha256 <64-lowercase-hex>
```

The auditor exits nonzero when a measured gate blocks, but still preserves the
new main JSON when safe input preflight succeeded. An unsafe path, wrong input
hash, or existing output directory blocks before Blender opens and creates no
evidence.

## Optional GLB clean-import command

Run this only after the main JSON exists. Hash that exact JSON, then start a
second clean process:

```text
blender --background --factory-startup --disable-autoexec --python tools/blender_fresh_import_profiled_kira_private_glb.py -- --glb Avatar/private_owner_review/<candidate_id>/<candidate_id>.private.glb --glb-sha256 <64-lowercase-hex> --audit-output-dir RecoverySprint/continuation_20260801/profiled_kira_candidate_audits/<candidate_id>__audit_attempt_<id> --main-evidence-sha256 <64-lowercase-hex>
```

This process imports the GLB into a disposable clean scene and inventories:

- primary-body mesh and metadata survival;
- armature, skin modifier, actions, and frame ranges;
- material names and per-object material binding;
- every source object's expected versus imported shape keys;
- responsive hair native-curve survival, curve-to-mesh conversion, missing
  groom objects, five response morphs, and wind/wet custom properties.

The report distinguishes `NATIVE_TYPE_SURVIVED`,
`CURVE_CONVERTED_TO_MESH`, changed type, and missing object. Fresh-import
readability and no observed loss are inventory findings only. This stage does
not execute a World runtime, prove wind/wet behavior, visually review hair, or
qualify the GLB for runtime.

## Pure verification

The focused suite is safe to run without Blender:

```text
py -m unittest tools.test_profiled_kira_candidate_postbuild_auditor -v
```

It exercises exact path/hash confinement, append-only refusal, input drift,
AST safety, required pose and adult-relationship gates, GLB survival truth
labels, and both documented clean-process commands. It creates fixtures only
inside the operating system temporary directory.
