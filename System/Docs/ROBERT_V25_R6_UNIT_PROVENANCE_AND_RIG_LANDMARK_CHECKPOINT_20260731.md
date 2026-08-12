# Robert V25 R6 unit provenance and rig-landmark checkpoint — 2026-07-31

Status: **VALIDATED V2 DIAGNOSTIC — REQUIRED LANDMARK MAP PARTIAL — NO BIND**

This is the additive Track A continuation from the accepted
`ROBERT_STANDARDIZED_BODY_COMPARISONS_VALIDATED` baseline. It corrects the
coordinate-unit interpretation, reconstructs reproducible MakeHuman landmarks,
and provides review overlays. It does not change the canonical Robert body,
the staged V25 R6 master, the 109-joint donor, any accepted checkpoint, or a
runtime selection.

## V2 correction — current Track A authority

A final comparison against Robert's continuation brief found that V1 omitted
rear alignment and did not explicitly dispose of four required landmark areas.
The additive V2 path leaves every V1 file/checkpoint unchanged and now provides:

- eight 900×900 overlays: front, left side, front three-quarter, and rear for
  both unit-only and 1.043660 uniform height-fit alignment;
- 24 exact mapped roles, adding a bilateral `rib_cage_center` derived from
  MakeHuman `breast.L`/`breast.R` and donor `breast_L`/`breast_R` REST heads;
- explicit unresolved blockers for eye centers, jaw/chin, and heels, because
  the donor has no corresponding semantic joints and no mesh anchors were
  guessed;
- 540 independent checks with zero errors and 23/23 Track A tests passed.

The required minimum map is therefore **partial, not passed**. The conditional
reversible rig-placement/retarget/deformation trial was not performed. The
current V2 report is
`RecoverySprint/tracks/avatar/robert-composite-recovery/reports/TRACK_A_REQUIRED_LANDMARK_AND_REAR_OVERLAY_CORRECTION_v2.md`.
Its successor checkpoint is
`RecoverySprint/checkpoints/track-a/ROBERT_LANDMARK_V2_VALIDATED_20260731_221919_856`
(16 files, 7,797,643 bytes, exact source/copy SHA-256 matches).

## Corrected unit provenance

The V25 builder retained native MakeHuman decimeter coordinates while mapping
axes as `(x, y, z) -> (x, -z, y)`. The physical mapping is therefore:

`(x, y, z) dm -> (0.1*x, -0.1*z, 0.1*y) m`

The earlier `9.581662` height relationship was dominated by the missing `0.1`
unit conversion. After correction, V25 R6 is `1.744140053 m` tall and the donor
is `1.820289625 m`; the optional post-unit uniform height fit is
`1.0436602394230294`. Corrected V25-to-donor extent ratios are approximately
`0.724213` X, `1.214837` Y, and `0.958166` Z. X/Y bounds are affected by the
different rest-arm poses and are not anatomy or envelope proof.

The preserved V2 preflight and V5 diagnostic were not edited. Additive
supersession/correction records explain which historical scale claims are no
longer physical-unit evidence and which height-normalized shape comparisons
remain useful.

## Landmark reconstruction and overlays

The replay verified 16 frozen inputs, applied all 42 hash-bound MakeHuman
targets to the 19,158-vertex base, and reconstructed 163 source bones. Twenty-
three unique anatomical roles cover pelvis, spine, neck/head, clavicles, arms,
hips, legs, and toes.

The staged donor was inspected in REST at frame 0 with no action. It contains
109 rest bones. Ground-motion `root` remains distinct from anatomical `pelvis`;
the MakeHuman root was not incorrectly mapped to the donor ground root.

Six 900×900 review overlays are in:

`RecoverySprint/tracks/avatar/robert-composite-recovery/rig_diagnostics/v25_r6_landmark_overlay_v1`

They show front, left-side, and front-three-quarter views for unit-only and
uniform-height-fit alignment. Root inspection confirmed the overlays are
readable and restricted to the V25 surface/wire helper, donor REST skeleton,
paired landmarks, and residual connectors. The large arm connectors reflect
the visible rest-pose difference, not a hidden bind.

| Alignment | Mean residual | Median | Maximum |
| --- | ---: | ---: | ---: |
| unit only | 0.079452 m | 0.058451 m | 0.266074 m |
| uniform height fit | 0.064808 m | 0.052531 m | 0.241647 m |

These residuals are engineering-review evidence, not an automatic compatibility
threshold.

## Validation and checkpoint

- independent validation: **497 checks, 0 errors**;
- Track A suite: **20/20 tests passed**;
- validation SHA-256:
  `d0336e8f110ac4425b69f8637909a4a1a8e6bf96e2fbbd71f0bd4231b254b379`;
- overlay-manifest SHA-256:
  `a72171da2401389476492512d2610d73ee4d84d09852f69497a8b8174e0c98a0`;
- canonical/staged V25 R6 SHA-256:
  `a2644615162d4263e36063898047b3cd34e759c442caf41103af0f8f866ae2cd`;
- staged donor SHA-256:
  `7665de3973f5d78ec644f15cfdddeb1974810090ac8a5d42a78fbb3306e8ae39`.

The changed-file-only checkpoint is:

`RecoverySprint/checkpoints/track-a/ROBERT_RIG_LANDMARK_OVERLAYS_VALIDATED_20260731_212820_586_113b0331`

It contains 14 files totaling 5.69 MiB and passed exact copy comparison. No
second full backup was created.

## Truth and next gate

Binding performed: **false**. Weights created/transferred: **false**. Scene
saved: **false**. Asset exported/promoted: **false**. Owner approved: **false**.
Runtime activation allowed: **false**.

Robert must review the eight V2 overlays and three explicit blockers. Before a
copy-only reversible rig-placement plan can be authored, a separate versioned
mesh-landmark protocol must establish reproducible frozen donor anchors for
eyes, jaw/chin, and heels and pass validation. Clothing, eyes/hair repair,
movement, export, activation, and Synthetic Robert work remain outside this
checkpoint.

Detailed engineering report:

`RecoverySprint/tracks/avatar/robert-composite-recovery/reports/TRACK_A_UNIT_LANDMARK_CONTINUATION_REPORT_v1.md`

Current corrective report:

`RecoverySprint/tracks/avatar/robert-composite-recovery/reports/TRACK_A_REQUIRED_LANDMARK_AND_REAR_OVERLAY_CORRECTION_v2.md`
