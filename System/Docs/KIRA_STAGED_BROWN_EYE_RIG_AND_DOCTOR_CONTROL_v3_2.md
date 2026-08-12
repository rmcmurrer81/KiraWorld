# Kira staged brown-eye rig and doctor-style eye control v3.2

## Outcome

Kira now has a non-destructive staged pair of warm-brown eyes with separate left/right pivots and separate upper/lower Blink morphs. The reviewed v3.2 rig is attached by default in the current Home World preview. `?kiraEyeRig=off` reversibly disables the attachment for comparison or recovery, and the explicit `?kiraEyeRig=v3.2` form remains valid.

This is an engineering eye-rig candidate, not a claim that Kira's current generic base face is a final likeness. The active avatar body was not replaced or edited.

## Asset identity and preservation

- Active Kira body: `Avatar/models/temp_ai/kira/avatar.glb`
- Active body SHA-256: `3ec62ba8d70a2c8235ef2013ff8183b7b3e9c41ca40c33e8b31d758b4ca3339e`
- Staged eye GLB: `Avatar/models/staged/kira/eyes/kira_brown_eye_rig_v3_2/kira_brown_eye_rig_v3_2.glb`
- Staged eye SHA-256: `fd85afe9d94760bee4baef1f4fefaf8405e1f8dd8bc9f416a9c32616042d4413`
- Home World public copy has the same SHA-256.

The staged asset contains, per side, an eye socket, an independent pivot, sclera, limbal ring, multi-tone brown iris, pupil, cornea, upper lid, and lower lid. The four lid meshes have a `Blink` morph. The authored ranges are 30 degrees yaw, 20 degrees pitch, and 8 degrees convergence.

## Runtime behavior

The Home World runtime:

- loads only the exact reviewed v3.2 staged GLB on the ordinary Home World URL;
- leaves `?kiraEyeRig=v3.2` as a valid explicit version request and uses `?kiraEyeRig=off` as the reversible opt-out;
- binds its runtime container to `mixamorigHead_06` while preserving the measured socket placement;
- rotates the eyeball pivots instead of sliding the iris and pupil across the face;
- supports center, anatomical left/right, up/down, near convergence, far, both-eye blink, and independent left/right blink checks;
- includes small idle saccades and a short natural blink pulse when no diagnostic override is active;
- exposes isolated debug controls for the doctor-style test without activating Kira's mind or life loop;
- never instantiates the former procedural white-sphere/blue-iris eye placeholders.

## Browser evidence

The isolated browser smoke loaded the current body, attached the staged rig, and passed every automated runtime check:

- structural node set complete;
- exact staged/public hash match;
- head binding present;
- no old procedural eye nodes;
- socket-to-head distance stayed invariant within `0.0000000005 m` while the head moved;
- the eye socket moved `0.023425536 m` with the doctor head-motion phase, proving it followed rather than floated;
- center-to-left and center-to-right gaze vectors changed measurably;
- both-eye and independent left/right blink morphs reached their commanded values;
- the ordinary default URL attached the rig;
- an opt-out page using `?kiraEyeRig=off` did not attach it;
- an explicit `?kiraEyeRig=v3.2` page still attached it;
- two final independent browser runs passed every check with zero page, console, request, or HTTP errors;
- both final runs began and ended with no active candidate, did not alter the live shell-state file, and left the active Kira body hash unchanged.

Evidence:

- `Data/world_tests/kira_eye_upgrade_20260718/browser/kira_staged_eye_rig_browser_smoke.json`
- `Data/world_tests/kira_eye_upgrade_20260718/browser/kira_staged_eye_rig_browser_smoke_default_on_opt_out_run1.json`
- `Data/world_tests/kira_eye_upgrade_20260718/browser/kira_staged_eye_rig_browser_smoke_default_on_opt_out_run2.json`
- `Data/world_tests/kira_eye_upgrade_20260718/browser/center.png`
- `Data/world_tests/kira_eye_upgrade_20260718/browser/look_left.png`
- `Data/world_tests/kira_eye_upgrade_20260718/browser/look_right.png`
- `Data/world_tests/kira_eye_upgrade_20260718/browser/blink_both.png`
- `Data/world_tests/kira_eye_upgrade_20260718/v3_2_structural_audit.json`

The rendered browser images were visually inspected. The brown eyes are seated in the existing openings, move together in the requested anatomical direction, and disappear behind the closed lids during the blink. There are no orbiting eye objects or duplicate placeholder eyes. The current facial mesh remains generic and the eyelids remain fitted overlays, so this is not yet final facial realism or a finished Kira likeness.

## Verification commands

```powershell
node tools/verify_kira_eye_control_exam.mjs
node tools/kira_staged_eye_rig_browser_smoke.mjs
cd Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview
npm.cmd run build
```

The smoke test is disposable: it injects shell state only inside temporary browser pages and does not activate a synthetic person, start a life loop, save a body location, replace Kira's body, or persist its test state. It also refuses to start if a live candidate is active.
