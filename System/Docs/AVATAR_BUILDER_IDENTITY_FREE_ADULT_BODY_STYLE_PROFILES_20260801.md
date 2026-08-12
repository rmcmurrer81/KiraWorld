# Avatar Builder identity-free adult body-style profiles

Date: 2026-08-01  
Status: validated declarative tooling; no body built, saved, rendered, selected, or activated

## Outcome

Avatar Builder now has a reusable style-profile layer for confirmed-adult
female candidates. Body proportions, target height, skin, eyes, and hair
direction can be expressed in one small JSON file and validated in under a
minute. The layer does not author or certify adult anatomy. It may be applied
only after a separate adult foundation qualifies, and the exact styled result
must be independently requalified under its new artifact hash.

The first profile is:

`Avatar/avatar_builder/style_profiles/natural_athletic_warm_asymmetric_waves_v1.json`

It is deliberately identity-free. It contains no private-person measurements,
ratios, indices, landmarks, scans, or copied geometry. The sole numeric body
dimension is the owner-specified avatar target height of `1.651 m`.

## Strict separation from anatomy

The style profile can describe bounded deformation targets and appearance. It
cannot:

- qualify an adult foundation;
- add, remove, copy, or claim adult anatomy;
- change anatomy topology or relationship evidence;
- bypass confirmed-adult eligibility;
- authorize Blender, rendering, saving, export, clothing, publication, or live
  activation.

The required order is:

1. Qualify the complete adult foundation independently.
2. Reconfirm the intended candidate is a confirmed adult in the adult-female
   lane.
3. Validate the style profile and every exact local binding.
4. Apply the listed target weights deterministically through a separately
   authorized adapter.
5. Re-run topology, complete-adult-anatomy, deformation, eye, hair, material,
   and private owner-review gates against the styled candidate's new hash.

A valid profile is a recipe, not evidence that steps 1, 4, or 5 passed.

## Current natural-athletic direction

The current profile records the owner's qualitative direction:

- target height `1.651 m`;
- natural-athletic proportions;
- curvier hips and buttocks;
- a slightly narrower waist;
- a natural fuller adult bust;
- modest core, pelvis, back, upper-leg, and upper-arm tone;
- warm skin centered on the earlier `#C7A08E` direction instead of the pale
  R13 direction;
- natural brown irises with black-band artifacts explicitly forbidden;
- natural-black, shoulder-length loose waves with an asymmetric deep side
  part;
- required wind response and wet clumping, volume, darkening, specular, and
  gravity metadata.

“Earlier” means the earlier preferred visual direction. It is not an inference
about the subject's age.

The older audited render remains rejected engineering evidence. Its exact
render and audit hashes are retained only for qualitative warm-palette and
hair-silhouette direction. Geometry, topology, measurements, biometric
indices, identity landmarks, material acceptance, and body acceptance may not
be derived from it.

## Bound official MakeHuman targets

All target paths stay below the bundled official MakeHuman target root. Every
file is SHA-256 bound to the project copy and tied to the exact bundled CC0
asset-license evidence. Positive weights are capped at `0.25`; the current
weights are intentionally much smaller.

| Direction | Official target | Weight | Symmetry |
|---|---|---:|---|
| Curvier hips | `hip-scale-horiz-incr.target` | 0.100 | bilateral target |
| Curvier buttocks | `buttocks-volume-incr.target` | 0.140 | bilateral target |
| Slightly narrower waist | `measure-waist-circ-decr.target` | 0.070 | bilateral target |
| Fuller adult bust | `measure-bust-circ-incr.target` | 0.080 | bilateral target |
| Bounded bust projection | `breast-point-incr.target` | 0.035 | bilateral target |
| Core tone | `stomach-tone-incr.target` | 0.070 | bilateral target |
| Pelvis tone | `pelvis-tone-incr.target` | 0.050 | bilateral target |
| Upper-back tone | `torso-muscle-dorsi-incr.target` | 0.035 | bilateral target |
| Upper-leg tone | left/right `upperleg-muscle-incr.target` | 0.035 each | exact pair |
| Upper-arm tone | left/right `upperarm-muscle-incr.target` | 0.025 each | exact pair |

For unilateral MakeHuman targets, validation requires one left and one right
file with the same pair ID, intent, license binding, and weight. A left or
right file cannot be mislabeled as a bilateral target.

## Hair readiness is a contract, not a proof claim

The hairstyle specification requires a guide-curve/child-strand system or a
validated dynamic equivalent. Roots remain strongly pinned while guide
response varies by strand length and mass, with collision and damped
follow-through required for wind.

Wetness uses one normalized `hair_wetness_0_1` parameter. The profile provides
bounded ranges for clumping, volume loss, darkening, specular increase, and
gravity alignment. Its state remains
`SPECIFICATION_ONLY_NOT_RUNTIME_PROVEN` until separate runtime tests prove both
wind and wet behavior. Static hair cannot satisfy this contract merely by
looking realistic in one frame.

## Minute-scale use

1. Copy the validated JSON profile to a new file for another confirmed-adult
   female candidate.
2. Give it a new generic `profile_id`.
3. Change only qualitative direction, target height, bounded official target
   entries, and appearance metadata. Do not enter private measurements,
   ratios, indices, or identity landmarks.
4. Record the exact local SHA-256 for every newly selected official target and
   its license evidence.
5. Run:

   `py tools/validate_avatar_body_style_profile.py --profile Avatar/avatar_builder/style_profiles/<profile>.json`

6. Proceed only when the result says
   `VALIDATED_DECLARATIVE_STYLE_PROFILE` with no blockers.

This makes the styling decision a minute-scale configuration task. Blender
application and candidate qualification remain separate controlled steps;
this document does not claim that a complete body can skip those gates.

## Fail-closed checks

The pure-Python validator checks:

- exact schema and allowed fields;
- confirmed-adult/adult-only/female guards;
- anatomy/style separation and post-style requalification;
- the absence of private measurements and biometric/proportion indices;
- safe project-relative paths with no traversal or escape;
- exact SHA-256 for the schema, visual evidence, audit, license, and targets;
- the official MakeHuman target-root boundary;
- CC0 adaptation and style-use authority;
- unique targets and bounded positive numeric weights;
- complete, equal left/right pairs and truly bilateral single targets;
- the warm skin-distance bound, brown eye profile, and pale-direction block;
- wind/wet readiness requirements without a false runtime-proof claim;
- no build, Blender, render, save, export, or runtime side effects.

Focused verification:

`py -m unittest tools.test_avatar_body_style_profile -v`

Current result: `17/17 PASS`.

## Files

- Schema: `Avatar/avatar_builder/style_profiles/adult_body_style_profile_v1.schema.json`
- Reusable profile: `Avatar/avatar_builder/style_profiles/natural_athletic_warm_asymmetric_waves_v1.json`
- Validator: `Core/avatar_body_style_profile.py`
- Read-only command: `tools/validate_avatar_body_style_profile.py`
- Tests: `tools/test_avatar_body_style_profile.py`

## Rollback

No live state changed, so rollback requires no body restoration. Stop consuming
the profile or remove its future caller binding. Keep this file and the profile
as append-only evidence of the styling contract unless the owner explicitly
authorizes their removal.
