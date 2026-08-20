# Static Body, Face, and Station review material

This directory contains a small, exact set of accepted **static data-only**
artifacts so David's team can see the current body/face requirements while the
mind/runtime and Hanson bridge are reviewed. None of these files is a body,
avatar, Blender result, robot controller, or authorization to materialize or
operate hardware.

## Exact included identities

| File | Bytes | SHA-256 | Meaning |
| --- | ---: | --- | --- |
| `MIND_BODY_STATIC_READINESS_BASELINE_20260818.json` | 14,775 | `689a8d0edc0385f9d83b691b28d32eaee159f54ec47490cba525f000a2125470` | Cross-lane static readiness baseline |
| `BODY_FACE_STATION_INTAKE_WORKSHEETS_20260818.json` | 26,572 | `556acabd3a32dcc3cd26c6fe18767a0524095a0410878d5733b43d15f9237b16` | Blank intake worksheets for Body, Face, and Station evidence |
| `BODY_FACE_STATION_FUTURE_EVIDENCE_ORDER_20260818.json` | 47,970 | `6392052b662231854bef15073ded3b922412895c9e02832797a5d4f531a96163` | Future evidence ordering; no acquired output |
| `INTENDED_BODY_NEUTRAL_CANDIDATE_ACQUISITION_BOUNDARY_V5.json` | 38,048 | `fdd3384758b665c7c082bf59674b74006a4e5056653d93caff7c8de1038e5e99` | Nine blank future body-receipt classes |
| `INTENDED_BODY_V5_AUDIT_DECISION.json` | 1,527 | `ad8256e6ca68c2c105ede7b21290ef25b610434e02a0bc52542fc64349bfcada` | Independent static-only decision for Intended Body V5 |
| `FACIAL_BLINK_LIPSYNC_EXACT_RIG_CONTROL_MAPPING_ACQUISITION_BOUNDARY_V4.json` | 81,987 | `1b2da41b8a73ae6d121697aca8c49219074bddc3f623c436063360d211c8cc67` | Schema for 52 logical controls and 40 timeline events |
| `FACIAL_V4_AUDIT_DECISION.json` | 1,533 | `314fcd4a891f84af63965fdba3b125cb7d274483b0b3703735285599b4eedf09` | Independent static-only decision for Facial V4 |

The “Station” worksheets describe a garment-mechanics test station. They are
not a robot docking station, embodiment chamber, or Hanson interface.

## Current 3D/avatar reality

- This repository currently ships no portable `.glb`, `.blend`, `.fbx`, or
  `.obj` avatar/world asset in this handoff.
- Local Kira avatar work remains an owner-review trial with unresolved anatomy,
  likeness, eye-fit, motion, and clothing review. It is not distributed here.
- Synthetic Robert has no approved 3D body in this package.
- The chamber/pod is an architecture and visual design concept, not a shipped
  3D scene or a source of execution authority.
- Facial V4 records the evidence that a future exact rig mapping must supply;
  all acquisition slots remain blank.

The body-residency architecture and hardware qualification plan are in
[`../BODY_RESIDENCY_AND_AVATAR_TRANSITION.md`](../BODY_RESIDENCY_AND_AVATAR_TRANSITION.md).
Current source-review entry points and observed test counts are in
[`SOURCE_REVIEW_ENTRY_POINTS.md`](SOURCE_REVIEW_ENTRY_POINTS.md).
The Hanson bridge remains limited to high-level speech, gaze, expression, and
allowlisted gesture intentions until Hanson provides authoritative simulator
and interface details.

## Validator note

Historical validators copied under `mind_v21_static/validators/` retain their
original workspace-relative assumptions and are evidence/reference code, not a
portable command in this handoff. Use the top-level handoff validator for the
current package. This directory's exact seven artifacts can be checked with:

```text
python -B static_body_review/validate_static_body_review.py
python -B static_body_review/test_validate_static_body_review.py -v
```

Run those commands from the handoff root. The expected result is
`PASS_STATIC_DATA_ONLY_NO_GO` and 3/3 validator tests.
