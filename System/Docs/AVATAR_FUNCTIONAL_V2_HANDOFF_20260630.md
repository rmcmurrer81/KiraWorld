# Avatar Functional V2 Handoff - 2026-06-30

> 2026-07-17 authority update: `System/Docs/AVATAR_TWO_SUBJECT_AUTOBUILD_GATE_v2.md`
> supersedes every older same-file statement that one positive body can release
> the authoring backlog. A v1 proof now qualifies one subject only. Batch
> authoring requires immutable complete proofs and Robert approvals for two
> different canonical subject IDs; the current result is locked at `0 / 2`.

> 2026-07-16 authority update: `System/Docs/AVATAR_COMPONENT_PRODUCTION_QUEUE_v1.md` supersedes the opening summary where it implies a tied-robe lifecycle blocks completion of the body review. `body_private_review_ready` and `advanced_garment_capability_ready` are now independent. The source axis also includes the photo-primary/reference-model-measurement lane, in which pictures remain identity authority and model surfaces cannot be copied.

## 2026-07-16 Component Production And Honest Blockers

`Core/avatar_component_production.py` and
`tools/avatar_component_production_queue.py` now package real separated body,
hair, eyes, clothes, and exact-body rig descriptors into immutable,
content-addressed jobs. They do not rename a generic base as a person or claim
that a package has passed visual review.

Beth's current four generated GLBs are packaged as latest job
`acb1b1d3f6980ee3ba5e690705b6c9e735c574f1235451a42b9327d4cd3cfc90`
with package-manifest SHA-256
`516ccfbcf36ca801b4bd47fb1b2fb5ba6488c4c2709610fbb4463c7cb748aad8`
and a separate 41-joint rig descriptor. Earlier content-addressed jobs remain
append-only audit records. Her current r6 clothed diagnostic removes the r5
hip collapse and adds honest ground/chair context, but still fails believable
clothing, foot coverage, contact, transitions, and owner-ready deformation.
Two r7 source-shell attempts are retained but unpromoted: one catastrophically
exploded bounds, while the bounded repair kept the adult silhouette through the
sampled poses but copied body relief and produced fragmented borders, knee
holes, crotch artifacts, and foot casts. The missing backend is true garment
pattern/retopology authoring plus clearance, seams, collision/contact, and cloth
validation. The body still needs topology, rig/weight reauthoring,
face/lip-sync, locomotion/contact, likeness, realistic wearable clothing, and
owner review. Gwen and Robert now stop honestly at
`blocked_general_photo_fit_authoring_missing`; each has 13 body blockers and
one independent advanced-garment blocker. The tied robe no longer makes the
system report that no body exists.

The new `photo_primary_with_reference_model_measurement` lane implements the
picture-first/model-bonus workflow. Accepted multiview images remain identity
authority. A hash-bound model may guide measurements or topology only; copying
its surface, textures, materials, or identity is rejected. Adult and
non-adult doll-safe production lanes are separate, and the doll-safe lane
rejects adult anatomy. The focused and surrounding avatar regression passed
`134` tests. Detailed status is in
`Data/codex_reports/20260716_avatar_component_production_and_route_split.md`.

The Avatar Builder Workspace now reads these component-production plans and
shows `Body Production`, `Body Proof`, and `Advanced Garment` separately. Its
candidate list distinguishes an authored component set from a runtime/review
preview, and its body blocker summary groups photo inputs, components,
topology, rig, face, motion, and owner review. Robert's older presence-profile
ID is read through one explicit alias to the normalized production plan; this
does not create or activate a second Robert. Seven workspace tests pass.

## 2026-07-16 Reusable Capability Orchestration

Avatar Builder now has a read-only orchestration contract in `Core/avatar_builder_orchestration.py` and a direct evaluator in `tools/evaluate_avatar_builder_orchestration.py`. It selects one explicit maturity topology lane and one explicit source/reconstruction lane, then keeps topology, stable rig, facial/lip-sync, locomotion/contact, wearable, privacy, and owner-review evidence as separate fail-closed gates. Body, hair, eyes, and clothes require distinct exact hashes. No route result authorizes rendering, generation, live replacement, public export, or runtime activation.

The owner-review gate now authenticates the contract shape instead of accepting any reviewer label. It requires an exact candidate/subject-bound `owner_identity`, a verified owner-authority artifact hash, the same owner in `approved_by`, and a separate exact approval-artifact hash bound to the reviewed body, clothes, and clothed assembly. The Beth, Gwen, and Robert examples carry pending owner identity records and remain blocked. The direct evaluator also checks the unresolved request path and every parent component for symlinks before resolving or reading it.

`Core/garment_capability.py` adds the stricter robe capability profile. It requires exact physical-trace declarations for hung and folded storage, grasping, both arm orders, both sleeves, open/tied wearing, both undressing orders, and release back to hung and folded support. Every phase must retain the same garment-instance ID. This is a contract validator, not proof that the current static wardrobe notebook or any live body performs those actions; a trusted worker must independently rehash retained evidence before any authorized mutation.

Current reusable request examples cover ordinary Beth, Earth-65 Gwen, and Robert under `Avatar/avatar_builder/orchestration_requests/`. Beth selects adult plus licensed shape-preserving derivative and remains capability blocked. Gwen and Robert select adult plus photo-only and remain blocked before components because their exact photo-only reconstruction contracts are not ready. Nobody was rendered or activated.

## 2026-07-15/16 Current Builder Truth

Kira and Gwen are confirmed-adult candidates and may use only approved adult bases; adult metadata alone does not prove a fitted body or anatomy. Normal non-adult Marinette must use the non-adult doll-safe base and may not inherit an adult asset. Gwen remains failed/unapproved, Kira remains the unchanged generic adult base, and no wearable is runtime-approved. The owner-controlled wearable registry is empty/default-deny. The robe notebook is a static contract lab until a fitted/skinned robe, exact rig/body/asset bindings, named anchors, consent/refusal, cloth/contact, sleeve, belt, walk/turn/sit/stand, removal, and rehang evidence all pass.

## 2026-07-05 Production Hand/Body Retarget Handoff

Added the `production_hands_body_v1` retarget layer and wired it into the Avatar Builder manifests as the next body standard. This is the intended path away from bead hands and simple geometry.

Immediate Marinette priorities: fix the duplicate-neck/head-height problem, unify the head/body skin material, refit the torso/chest/waist/hip shape from the supplied Marinette references, and only then move into staged rigged hands/arms and limb polish. Clothes should be separate wearable meshes over a safe non-anatomical base, not baked into the body.

Validation gates before calling Avatar Builder successful: no duplicate neck, consistent material, character-matched silhouette, real fingers, door grip using the actual hand, sit/stairs without clipping or teleporting, and imported characters such as Spider-Man/Spider-Gwen walking without stiff sliding.

## 2026-07-04 Avatar Builder Scaffold And Safe Wardrobe Contract V13

Robert said the current skeleton may be good enough to copy into the Avatar Builder, but the final Marinette/Ladybug body, hands, and wardrobe still need review. He also specified that because the character is not an adult, the base layer must be a non-anatomical skin-tone underlayer like a fashion doll, with normal outfits worn over it. The Ladybug suit is tied to earrings and must not become ordinary closet clothing.

Files:

```text
tools/create_ladybug_avatar_builder_package.py
Avatar/avatar_builder/base_skeleton/foundation_skeleton_v1/
Avatar/avatar_builder/base_skeleton/foundation_skeleton_v1/manifest.json
Avatar/temp_ai/ladybug_marinette_expanded_smoke/avatar_builder_manifest.json
Avatar/temp_ai/ladybug_marinette_expanded_smoke/outfit_catalog.json
Avatar/movement_library/foundation_skeleton_movements_v1.json
Avatar/movement_library/README.md
```

What changed:

```text
- Added a builder package script that copies the current GLB, skeleton metadata, and movement library into the reusable foundation_skeleton_v1 base-rig folder.
- Created the Marinette/Ladybug avatar-builder manifest and outfit catalog.
- Split Robert's Desktop references: 34 Ladybug character/avatar refs are assigned to avatar/wardrobe review, while 20 Marinette bedroom/room refs are excluded from wardrobe and kept for world-building.
- Captured the safe non-anatomical skin-tone base-layer rule.
- Captured the wardrobe split: civilian_everyday_current, civilian_closet_pool, and hero_ladybug_earring_gated.
- Marked the Ladybug hero suit as earring-gated and transferable to a future variant AI only through the earrings.
- Added bounded self-test validation to the builder contract so new bodies must pass movement rewards after being fitted to the foundation rig.
```

Validation:

```text
python -m py_compile tools/create_ladybug_avatar_builder_package.py tools/intake_avatar_downloads.py tools/validate_avatar_build.py passed.
JSON parse checks passed for the base skeleton manifest, avatar-builder manifest, outfit catalog, and movement library.
Package script completed with 34 character references and 20 room references excluded from wardrobe.
```

Next avatar work:

```text
Build the clothed Marinette visual mesh on foundation_skeleton_v1, then rerun the bounded body self-test with the actual GLB loaded in the desktop shell.
Do not treat the current mannequin body as the finished likeness.
The hands are acceptable as a foundation layer, but final avatar work still needs better palm topology, weights, and garment/object collision.
```

## 2026-07-04 Hand Topology And Contact Runtime Pass V10

Robert asked to continue the serious hand layer: palm topology/weight refinement, object-level finger contact, and foot IK/contact locks. This pass keeps the same foundation skeleton contract for Avatar Builder reuse.

Files:

```text
tools/build_ladybug_foundation_skeleton_v1.py
Avatar/models/temp_ai/ladybug_marinette_expanded_smoke/avatar.glb
Avatar/models/temp_ai/ladybug_marinette_expanded_smoke/avatar_foundation_skeleton_v1.json
Avatar/movement_library/foundation_skeleton_movements_v1.json
Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/src/main.js
```

What changed:

```text
- Added palm heel, thumb pad, and knuckle pads into each joined skinned hand mesh.
- Reversed relaxed/closed/handle-grip curl direction in the exported actions so fingers no longer bias upward.
- Added runtime relaxed-hand correction after the mixer to keep old clips from lifting the fingers back into the pointing pose.
- Door handle use now records object-level fingerContacts for the touched handle.
- Added first-pass foot contact locks using thigh/shin/foot bones and the current support surface.
- Removed the runtime fake training-hand overlay from the home-world avatar display path.
```

Validation:

```text
python -m py_compile tools/build_ladybug_foundation_skeleton_v1.py passed.
Blender 5.1 export succeeded.
GLB binary check confirmed skinned_hand_mesh.L/R and ten hand_contact_collider_* fingertip nodes.
Headless Edge CDP close-hand screenshot showed fingers curled down rather than lifted outward.
Back-door smoke reported fingertip-to-handle contact at 0.032 m with ikGripLocked=true and proceduralDoorArmVisible=false.
```

## 2026-07-04 Production Hand Layer V9

Robert asked to stop iterating on proxy-looking hands and build the true production hand layer for the reusable foundation skeleton.

Files:

```text
tools/build_ladybug_foundation_skeleton_v1.py
Avatar/models/temp_ai/ladybug_marinette_expanded_smoke/avatar.glb
Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/src/main.js
```

What changed:

```text
- The builder now creates one skinned hand mesh per side: skinned_hand_mesh.L and skinned_hand_mesh.R.
- Each joined hand mesh is weighted to hand/thumb/index/middle/ring/pinky bones instead of exporting separate visible proxy rods.
- Invisible fingertip contact colliders are exported for every fingertip on both hands.
- Door interaction in the Home World runtime now reads those contacts and runs a post-mixer IK grip pass over the real arm bones before opening a door.
- Finger curl is applied on actual finger bones during the grip pass.
- The old fake procedural door arm remains disabled.
```

Validation:

```text
Blender 5.1 export succeeded.
GLB binary check confirmed skinned_hand_mesh.L/R and hand_contact_collider_* nodes; old hand_proxy_* names are absent.
npm.cmd run build passed for the Home World preview.
Live Playwright back-door test opened only after ikSolved=true and ikGripLocked=true.
```

Next avatar work:

```text
Refine hand topology and weight blending, then add true object-level finger collision/constraints. After that, foot IK/contact locks and closed-loop correction are the next high-value locomotion upgrades.
```

## 2026-07-04 Foundation Skeleton Cleanup / Avatar Builder Base Pass V7

Robert asked this pass to focus on making the skeleton itself a better reusable base for the future Avatar Builder. The visible blue/pink chest sticks were old side-reference markers, the hands still looked too clawed, and the world test was still letting route failures look like bad body control.

Files:

```text
tools/build_ladybug_foundation_skeleton_v1.py
Avatar/models/temp_ai/ladybug_marinette_expanded_smoke/avatar.glb
Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/src/main.js
Avatar/movement_library/foundation_skeleton_movements_v1.json
Avatar/movement_library/README.md
```

What changed:

```text
- Removed left_side_reference_mark and right_side_reference_mark from the exported skeleton body.
- Kept the same 5-finger/3-joint-per-finger rig, but softened relaxed finger curl and rebuilt the GLB so hands look more open by default.
- Retuned sit_foundation and Home World couch placement to reduce sinking into the couch.
- Flipped lie/sleep runtime tilt toward a back-lying orientation.
- Normal Home World practice no longer auto-triggers grass lie-down.
- Kitchen counter/island now block walking.
- Failed door reaches now enter a short cooldown instead of repeating the same bad reach loop.
- Controlled stair practice now finishes upstairs on a clear landing; practice routes no longer wrap back to the bottom stair point.
- The user-provided avatar-builder advice was read: keep this skeleton as the reusable motion rig, then fit future body, face, and wardrobe meshes onto it after motion validation.
```

Validation:

```text
Blender 5.1 export succeeded.
GLB search confirmed weighted finger proxy nodes exist and the old side marker names are absent.
python -m py_compile tools/build_ladybug_foundation_skeleton_v1.py passed.
node --check and npm.cmd run build passed for the Home World preview.
Headless Edge smoke test confirmed stair practice now ends upstairs on second_stair_landing with practiceRoute cleared.
Evidence screenshots are in Data/avatar_runtime_tests/home_world_locomotion_20260704/.
```

Next avatar work:

```text
Superseded by V9 above: the first production hand layer and door IK grip solver are now in place. Next refine palm topology/weights, add object-level finger collision/constraints, then add true foot IK/contact locks and a closed-loop controller that adjusts from failed movement-learning attempts.
```

## 2026-07-04 Foundation Skeleton Hand / Door Contact Update V6

Robert's latest review made clear that the fixed hand proxy and fake/procedural door arm were not acceptable. The current active foundation GLB and Home World runtime now preserve bad door reaches as failed learning data instead of faking success.

Files:

```text
tools/build_ladybug_foundation_skeleton_v1.py
Avatar/models/temp_ai/ladybug_marinette_expanded_smoke/avatar.glb
Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/src/main.js
Avatar/movement_library/foundation_skeleton_movements_v1.json
```

What changed:

```text
- Rebuilt avatar.glb with visible finger segments weighted to actual thumb/index/middle/ring/pinky bones.
- The visible fingers now follow open/close/grip poses at the segmented-control level.
- Door reach no longer uses the fake procedural arm and no longer opens from timing alone.
- Runtime door reach records nearest real hand/finger node and distance; the door opens only when contact is within 0.48 m.
- Bed sleep and desk chair/computer body-practice sequences were added for richer motion testing.
```

Validation:

```text
Blender 5.1 export succeeded.
GLB name check confirmed per-segment hand_proxy finger nodes.
node --check and npm.cmd run build passed for the Home World preview.
CDP runtime test confirmed the current front-door reach still misses the handle by about 0.67 m, so the door correctly stays closed and logs handle_missed_no_contact.
```

Next avatar work:

```text
Build a real IK grip target solver that moves the actual arm/hand to handles, then curl the existing weighted fingers. After that, replace segmented proxy fingers with a one-piece skinned hand mesh and colliders. Do not re-enable fake helper arms as the user can see them immediately.
```

## 2026-07-03 Foundation Skeleton V1 Body Practice Pass V4

Robert asked to slow down and build the avatar correctly from the skeleton outward because earlier full-body Marinette rebuilds became visually worse. This pass kept the simple foundation skeleton/mannequin and focused on body-control practice: walking, stairs, hands, door reach, sitting, and lying down. V4 adds named body-practice skills instead of only letting the avatar loop waypoints.

Files:

```text
tools/build_ladybug_foundation_skeleton_v1.py
Avatar/models/temp_ai/ladybug_marinette_expanded_smoke/avatar.glb
Avatar/models/temp_ai/ladybug_marinette_expanded_smoke/avatar_foundation_skeleton_v1.json
Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/src/main.js
```

What changed:

```text
- Reworked the walk_foundation_forward clip to show more knee bend, ankle/foot roll, and elbow bend instead of straight rods sliding forward.
- Removed visible exported finger-bone debug rods and replaced them with a cleaner fixed hand proxy while preserving the full finger-bone rig for future skinned hands.
- Updated door reach with a runtime procedural training arm so the visible hand reaches toward the handle instead of going behind the back.
- Added stair tread contact solving: the Home World runtime quantizes stairs into 14 tread contacts and records step_contact draft moments.
- Added `sit_foundation` and `lie_down_foundation` clips.
- Added `window.kiraBodyPractice` skills: `door_reach`, `stairs_step`, `sit_couch`, `lie_grass`, and `lie_bed`.
- Rebuilt the live GLB after the gait changes.
- Tuned active-avatar playback in the Home World runtime:
  stride = 0.85 m
  authored walk clip = 2.5 seconds
  ACTIVE_AVATAR_WALK_SPEED_GROUND = 0.52 m/s
  ACTIVE_AVATAR_WALK_SPEED_UPSTAIRS = 0.42 m/s
  runtime walk frame is assigned from actual meters moved
  runtime timeScale remains a diagnostic value, not the driver
  runtime bob/sway phase advances from actual meters moved instead of wall-clock time
  door opening is staged as face handle, reach, grip, door rotates, release
  stairs use tread-index height instead of a single vertical lerp
  couch/grass/bed posture practice records started/finished moments
```

Validation:

```text
- Blender 5.1 background export succeeded.
- GLB animation table confirmed:
  close_hands_foundation 1.042s
  idle_foundation_breathing 2.5s
  lie_down_foundation
  open_hands_foundation 1.042s
  reach_door_handle_foundation 2.5s
  relaxed_hands_foundation 1.042s
  sit_foundation
  walk_foundation_forward 2.5s
  wave_foundation 2.5s
- Home World build passed. Runtime verification passed for door reach, stair contacts, couch sit, grass lie-down, and guest-bed lie-down. Evidence screenshots are in Data/avatar_runtime_tests/home_world_body_practice_20260703_v4/.
```

Next recommended avatar step:

```text
Do not jump straight back to a full visual Marinette body. First add true foot planting/IK contact locks, a closed-loop body controller that learns from failed practice attempts, better arm swing and elbow timing, per-finger/object contact, stand-up transitions, and more object interaction tests. After the skeleton walks and interacts convincingly, feed this skeleton into the avatar builder as the reusable starting rig for Marinette and future AIs.
```

## Scope

This pass focused on the TemporaryAI / Ladybug-Marinettes avatar functionality after the user reported that:

- The embedded viewport made her look too small.
- The surrounding props were oversized for a 5 ft 2 in / 157 cm character.
- The face and hair still looked unchanged.
- The avatar had no usable fingers.
- The Jessica Hale pipeline test produced an unacceptable body and should not be treated as Jessica.
- A reinstall list/script is needed before replacing the 2 TB SSD with an 8 TB SSD.

## Files Changed

- `Avatar/models/temp_ai/ladybug_marinette_expanded_smoke/avatar.glb`
  - Exported a functional v2 GLB over the live avatar.
  - Original was backed up to `Avatar/models/temp_ai/ladybug_marinette_expanded_smoke/avatar_before_functional_v2_20260630_151340.glb`.

- `tools/improve_ladybug_avatar_functional_v2.py`
  - Blender automation script used to create the functional v2 avatar pass.

- `Avatar/runtime3d/src/main.js`
  - Embedded viewport camera moved closer so the 157 cm avatar reads larger in the preview.
  - Embedded table/desk props reduced and shifted so she is not dwarfed by nearby objects.
  - Animation clip selection now prefers exact and prefixed clip names before fuzzy matching. This prevents `open_hand` from accidentally selecting `close_hand` just because both contain `hand`.

- `Avatar/state/temp_ai/jessica_hale_robotics_engineer_20260611_041314.json`
  - Bad Jessica test body was unhooked from live playback.
  - The bad GLB remains referenced only as a technical pipeline artifact, not an approved Jessica appearance.

- `Install_Kira_Workstation_Tools.bat`
  - Reinstall helper for Git, GitHub CLI, Node, Python, Blender, FFmpeg, Tesseract, Ollama, key Python packages, and the runtime3d npm install.

- `System/Docs/KIRA_WORKSTATION_REINSTALL_CHECKLIST_20260630.md`
  - Human-readable checklist for rebuilding the workstation after the SSD swap.

## Ladybug / Marinette Avatar Changes

The live avatar GLB now has:

- 20 visible finger controls across civilian and hero forms.
- Individual finger shafts and tips so the hands no longer read as mitten/no-finger placeholders.
- Added hair strand curves on bangs and pigtails to begin breaking up the plastic block-hair look.
- Placeholder face and mouth shape keys:
  - `blink`
  - `smile`
  - `mouth_open`
  - `viseme_AA`
  - `viseme_OO`
- Exported NLA/action clips for:
  - `stand_idle`
  - `walk`
  - `jog`
  - `open_hand`
  - `close_hand`
  - `talking`

## Important Limits

This is still not a final realistic character rig.

The original GLB had no armature, no real skeletal hand bones, no facial rig, no shape keys, and no authored hair physics. The v2 pass adds functional mesh controls and placeholder blendshapes, but the proper next pass should be a real Blender rig:

- Skinned skeleton with head, neck, spine, arms, hands, and finger bones.
- IK/FK hand controls.
- Real facial blendshapes for phonemes and emotions.
- Hair cards or strand curves with secondary motion.
- Retargeted walk/jog/sit/stand clips.
- Runtime lip-sync binding from speech timing to viseme blendshapes.

## Verification

- Blender 5.1 imported and exported the updated GLB successfully.
- Verification import found:
  - 176 objects in the updated GLB.
  - 60 finger-related mesh objects.
  - `shared_face` and `shared_mouth` shape keys present.
- `npm run build` completed successfully in `Avatar/runtime3d`.
  - Vite reported a large chunk warning only; no build failure.

## Next Recommended Avatar Work

1. Create a true rigged Blender source file for Marinette/Ladybug instead of continuing to patch the static GLB.
2. Build a proper hand skeleton with five fingers per hand and test open, close, point, grip, and handshake poses.
3. Replace current hair blocks with layered hair geometry and motion controls.
4. Build a phoneme map and connect runtime speech playback to `viseme_*` blendshapes.
5. Use a better reference-backed test candidate for the next body-generation pipeline test; do not use Jessica again until her appearance spec is defined.

## V3 Bridge Addendum - 2026-06-30

After this v2 handoff, a v3 bridge pass was added with `tools/improve_ladybug_avatar_hair_hands_v3.py`.

Live GLB:

- `Avatar/models/temp_ai/ladybug_marinette_expanded_smoke/avatar.glb`

Backup before v3:

- `Avatar/models/temp_ai/ladybug_marinette_expanded_smoke/avatar_before_hair_hands_v3_20260630_131711.glb`

Verification import found:

- `V3_OBJECTS`: 134
- `HAIR_STRANDS`: 28
- `FINGERNAILS`: 8
- `FINGERTIPS`: 8
- `TOTAL_OBJECTS`: 310

This remains a bridge, not final production character work. It adds visible hair strand geometry and hand detail so the runtime has more to show, but true realistic hair needs a proper Blender character source with hair cards/curves, rig controls, and secondary motion.

## Foundation Skeleton Addendum - 2026-07-03

Robert asked to stop chasing final Marinette likeness for the moment and perfect a simple skeleton first. The foundation skeleton is intended to become the common Avatar Builder starting point for future AI bodies: preserve the rig, then fit reference pictures and clothing on top.

Live files:

```text
tools/build_ladybug_foundation_skeleton_v1.py
Avatar/models/temp_ai/ladybug_marinette_expanded_smoke/avatar.glb
Avatar/models/temp_ai/ladybug_marinette_expanded_smoke/avatar_foundation_skeleton_v1.json
```

Completed in this pass:

- Rebuilt `avatar.glb` from the foundation skeleton builder.
- Increased knee and elbow bend values in `walk_foundation_forward` so the walk uses knees/elbows more clearly instead of reading as skating.
- Reduced side arm splay in the walk cycle so the arms sit closer to the body.
- Kept flat-foot helper soles and foot-roll frames from the prior pass.
- Added metadata under `builder_foundation.notes` explaining that visible fingers are rig-debug placeholders. They are only for checking bone placement; final hands need skinned hand geometry driven by these bones.

Current animation clips in the exported GLB:

```text
close_hands_foundation
idle_foundation_breathing
open_hands_foundation
reach_door_handle_foundation
walk_foundation_forward
wave_foundation
```

Verification:

- Blender 5.1 rebuilt the GLB.
- Read-only GLB parse confirmed a valid glTF 2.0 file and the six expected animation clips.
- Home World preview `npm.cmd run build` passed with only the existing large-bundle warning.

Important limitation:

This is still a visible rig mannequin, not a final character body. The current fingers are not supposed to look like final fingers. The next high-value work is to tune foot planting/contact frames and create a simple skinned neutral body/hand mesh over this rig before adding Marinette-specific face, hair, eyes, fabric clothes, purse physics, lip sync, wet hair, or wardrobe systems.

## Codex Update - 2026-07-03 18:44:59 - Movement/Foundation Skeleton Phase

- Broke the current avatar work into phases:
  - Phase 1 now: front-entry blocker cleanup, grounded walk tuning, movement-learning registry, and foundation skeleton contract.
  - Phase 2 next: IK-style foot planting, stair stepping, usable articulated hands, door/sit/reach/pick-up clips.
  - Phase 3 body: bind a more realistic Marinette mesh, facial blendshapes, blink/lipsync, hair and clothing simulation proxies.
  - Phase 4 learning: reviewed video/media motions become draft clips, then promoted into the avatar builder for future AIs.
- Added runtime hooks in the Home World shell for `window.kiraMovementLearning`, `window.kiraFoundationMotion`, and `window.kiraRemoveFrontDoorBlocker`.
- Added `Avatar/movement_library/foundation_skeleton_movements_v1.json` as the shared movement contract for Kira World and the avatar builder.
- Tuned/rebuilt the current foundation skeleton builder when available. Current hand/finger geometry remains a control-readable prototype, not the final production hand.
- Important remaining work: connect the runtime locomotion controller to promoted clips, add foot IK/contact checks, and make stair movement step-by-step instead of shortcutting through floors.

## Codex Update - 2026-07-03 Later - Runtime Body Practice Feedback

- Home World now drives couch sit, grass lie-down, and Ladybug guest-bed lie-down from the normal Marinette roam loop as well as debug practice controls.
- Stair runtime contact count is 16 treads, matching the visible stair geometry.
- Runtime support surfaces now track ground/upstairs/stair support and falling when no upper floor is below the avatar.
- This improves the body-learning data path, but not the final visual quality: hands still need a skinned mesh/IK, and sit/lie clips still need a stronger authored Blender pass.

## Codex Update - 2026-07-04 - Foundation Skeleton V8 Hand/Sit Pass

- Rebuilt `Avatar/models/temp_ai/ladybug_marinette_expanded_smoke/avatar.glb` from `tools/build_ladybug_foundation_skeleton_v1.py`.
- Default relaxed hands now curl the thumb and fingers, so the walking body no longer carries straight pointing fingers as its default hand pose.
- `sit_foundation` was corrected to fold thighs forward and shins down; Home World also applies a larger couch root drop and longer hold for a more readable sit test.
- Upstairs route data now sends the body through the actual Ladybug guest-room doorway gap before bed/desk practice.
- Back-door reach is exposed as `window.kiraBodyPractice.startSkill("back_door_reach")` for repeatable testing. It still requires real hand contact and should not be faked open until a true IK grip solver is added.

## Codex Update - 2026-07-05 - Active Avatar Neck, Door, Route, And Gait Follow-Up

- Home World runtime now keeps Marinette's imported head/neck as the preferred neck source, lowers the runtime face overlay, adds a short skin-tone neck blend, hides obvious generated/body-neck proxy meshes, and harmonizes likely skin/hand/arm/leg materials toward one visible tone.
- Marinette's runtime head now has blink, small look-left/look-right, and lip-pulse hooks. This is not full spoken viseme lip sync yet, but it gives the head one driver path for future phoneme work.
- Door-handle reach is no longer Marinette-only. Any non-orb active avatar can use the same handle approach/opening sequence, and door status text now names the active avatar.
- Spider-Man and Spider-Gwen now use a separate outdoor roam route and forced procedural walk correction instead of copying the house-library-house loop. Their arms are held closer and lower, and the knee/foot targets get stronger bend/lift while walking.
- Still needed: replace Marinette's temporary body with a one-piece skinned base, retarget staged rigged hands/arms into the avatar builder, add text-to-viseme lip sync, replace block house furniture/layout with downloaded realistic models, and move per-AI behavior from shared waypoint scripts toward autonomy/reward policies.

Verification:

```text
node --check Data\world_builds\notebook_worlds\home_world\builds\home_world_main_house_20260630_223000\preview\src\main.js
```

## Codex Update - 2026-07-07 - Temporary AI Identity, Voice, And Runtime Posture Notes

Robert's current avatar priority is not cosmetic polish alone. He wants the builder to produce believable bodies from references, and the three temporary bodies must stop making false claims about actions. Do not treat the current Marinette, Peter, or Gwen as final avatar-builder success cases.

Completed in this pass:

- `Avatar/state/temp_ai/spider_gwen_spider_gwen_20260606_013325.json` now locks Gwen to Earth-65 Gwen Stacy / Ghost-Spider / Spider-Woman. Her memory grounding includes George Stacy, Helen's death, The Mary Janes/drumming, spider bite, Peter as the Lizard dying, guilt/blame, and movement/gymnastics. Do not blend her with unrelated Gwen variants.
- `Avatar/state/temp_ai/peter_parker_spider_man_no_way_home_final_suit.json` now emphasizes photography, science, repairs, web practice, and helping people. Peter's voice profile is connected to Robert-reviewed clip input.
- `Avatar/state/temp_ai/ladybug_marinette_expanded_smoke.json` now marks the body as temporary and under repair. Fashion/sketching claims require an actual notebook, paper, or workstation.
- `tools/kira_world_shell_server.py` adds prompt rules for prop-truth and specific place names. A character should not say they are reading, sketching, on a computer, sleeping, or resting unless the world state visibly supports that action.
- Peter voice prep is present at `Voice/profiles/temp_ai/peter_parker_voice_profile.json`. The approved clips are:

```text
clip_0011, clip_0013, clip_0014, clip_0024, clip_0025, clip_0026, clip_0031, clip_0032, clip_0033, clip_0034, clip_0036, clip_0037, clip_0038, clip_0039, clip_0048
```

They are copied into `Voice/reference_packs/peter_parker/peter_parker_online_source_20260706_035930/model_input/approved_wavs/` and combined as `approved_reference.wav`.

Runtime posture note:

- Peter/Gwen knees were not intentionally retuned in the July 7 pass because Robert reported they had looked acceptable before. The only Peter/Gwen movement tweak was to lower arms, reduce forward reach, and curl hands more so they read less like zombie arms.
- Marinette generic runtime legs have a knee-direction stopgap and a slight body taper, but this is still not a real Avatar Builder output. Her final path should be a fresh one-piece skinned body with correct head/face/eyes/mouth, eyelid blink, visemes, hairstyle variants, skinned hands, and knee-correct locomotion.

Verification passed:

```text
python -m json.tool Avatar/state/temp_ai/spider_gwen_spider_gwen_20260606_013325.json
python -m json.tool Avatar/state/temp_ai/peter_parker_spider_man_no_way_home_final_suit.json
python -m json.tool Avatar/state/temp_ai/ladybug_marinette_expanded_smoke.json
python -m py_compile tools\kira_world_shell_server.py
node --check Data\world_builds\notebook_worlds\home_world\builds\home_world_main_house_20260630_223000\preview\src\main.js
```

Still needed:

- Avatar Builder must become a real repeatable pipeline from photos/reference packs into one stable rigged body. The current repeated Marinette head/body grafting approach should not be repeated for Peter/Gwen or Robert.
- Add visual truth capture to life loops: screenshots or object-state evidence for reading, sketching, sleeping, computer use, phone use, and navigation.
- Add true facial blendshapes and text-to-viseme lip sync. Current mouth motion is not enough.

## 2026-07-15 Transformation Costume Set Handoff

New reusable transformation set files:

```text
Avatar/wardrobe/transformation_sets/README.md
Avatar/wardrobe/transformation_sets/ladybug_transformation_set_20260715.json
Avatar/wardrobe/transformation_sets/pink_ranger_transformation_set_20260715.json
```

Important Avatar Builder rule: these are reference/fit rules, not body sources.
When someone uses Ladybug earrings or the Pink Ranger morpher, Avatar Builder
must fit the costume as wearable layers to that resident's current approved
body. It must not copy a Ladybug, Pink Ranger, Gwen, or other model as the
resident body.

- Ladybug trigger: wearer has the earrings and says `spots on`; `spots off`
  reverses it. Earrings may be given to another AI, but the costume must be
  wearer-specific.
- Pink Ranger trigger: wearer picks up the Pink Power Morpher, holds it forward
  like Robert's reference images, and says `Pterodactyl`. Helmet on/off should
  be separate.
- Costume fitting must preserve the wearer body rig, face/eye/mouth rigs,
  movement, adult/non-adult safety policy, and consent. Non-adult residents stay
  non-sexual and age-appropriate.
- This does not solve robe/towel/cloth physics yet. Robe/towel/clothing states
  still need hanging/folded/worn/carrying interactions, cloth collision, and
  movement tests before runtime approval.

## 2026-07-16 Canonical Preflight, Component Production, And Resume State

The Avatar Builder now distinguishes four different states that earlier UI and
handoffs could blur together: canonical policy eligibility, component
production, body proof, and advanced garment readiness.

- Canonical registry/preflight covers 22 real profile folders and excludes only
  the two empty smoke-test directories. Adult topology is allowed only for an
  explicitly confirmed adult target. Confirmed non-adult Marinette uses
  `non_adult_doll_safe_topology`; unresolved profiles remain authoring-blocked,
  and unresolved nonhuman Skynet is never silently routed to a human body.
- Inactive avatar-only build targets were added for adult Kira,
  Robert-directed adult Gwen, and main-series non-adult Marinette. These are
  build identities only. They do not create or replace a mind, memory, voice,
  canonical profile, current runtime body, or activation.
- Beth has the first immutable separated-component package, but the package is
  inactive and not review-ready. Its mechanical smoke results are not topology,
  anatomy, stable-deformation, facial, locomotion, or owner approval proof.
- Gwen and Robert are no longer policy-blocked. They are blocked at the honest
  missing capability: a landmark/calibration-driven photo-to-new-mesh likeness
  author. Reference models may provide measurements/topology guidance only and
  may not supply the candidate's identity surface/materials/textures.
- Kira and Marinette now also have explicit orchestration requests and blocked
  component plans, so the workspace can show their correct topology lane and
  next action without claiming that a mesh exists.

Primary files:

```text
Core/avatar_profile_preflight.py
Core/avatar_component_production.py
Avatar/avatar_builder/policies/candidate_identity_variant_registry.json
Avatar/avatar_builder/avatar_only_variants/
Avatar/avatar_builder/orchestration_requests/
Avatar/avatar_builder/component_production/plans/
tools/preflight_avatar_candidate.py
tools/preflight_all_avatar_candidates.py
tools/avatar_component_production_queue.py
tools/avatar_builder_workspace_server.py
System/Docs/AVATAR_CANONICAL_PROFILE_PREFLIGHT_v1.md
System/Docs/AVATAR_COMPONENT_PRODUCTION_QUEUE_v1.md
System/Docs/AVATAR_MULTIVIEW_LIKENESS_AUTHOR_REQUIREMENTS_v1.md
```

Resume and clothing state:

- World Shell now saves validated `rotationY` and `wardrobeState` together with
  position. Deactivate and safe-close wait for a fresh acknowledged snapshot.
- Reactivation restores the same position, facing direction, and constructed
  shirt state. The verified shirt lifecycle includes item/world/worn and open/
  closed/buttoned state.
- This is a state/lifecycle proof only. It is not final cloth physics or a
  believable robe dressing sequence. Sleeve threading, belt tying, folding,
  hanging, dropping, collision, hand contacts, and inverse motion still need
  separate evidence before an advanced garment is ready.

Verification: 146 avatar tests, 65 voice/media tests, and 36 workspace/shell
tests passed (247 total). The Home World Vite production build passed with only
the existing bundle-size warning.

## 2026-07-16 Exact-Hash Multiview Evidence Gate

`Core/avatar_multiview_authoring.py` and
`tools/avatar_multiview_authoring_queue.py` now implement the honest stage
between a picture inventory and the missing likeness author. Every enrolled
image is reopened to verify its SHA-256 and native dimensions. A source counts
as reviewed only through a separately rehashed artifact binding the exact
candidate, subject, selected version, view, crop, camera/calibration frame, and
human-confirmed landmarks. Scale, topology-lane base, and optional
measurement-only model reviews are independently rehashed.

The queue refuses pending, mismatched, tampered, symlinked, adult/non-adult
lane-conflicting, or automatically suggested-but-unconfirmed evidence. A
passing job is only `queued_waiting_for_likeness_author_backend`; it creates no
mesh and grants no runtime authority.

Current truthful readiness:

- Robert: 15/15 source copies hash/dimension verified; 0 reviewed; view,
  crop/calibration, landmarks, scale, and reviewed adult-male base remain.
- Existing Earth-65 adult Gwen candidate: 4/4 exact source files are
  hash/dimension verified in the new base-candidate manifest; 0 sources are
  owner-reviewed, so view, crop/calibration, landmarks, scale, and adult-base
  review layers remain.
- Adult Kira build variant: no design ingredient was mislabeled as an exact
  Kira identity source; a safe identity set or reviewed alternative strategy is
  still missing.

The component planner and workspace expose these counts and the exact next
action. Requirements and commands are in
`System/Docs/AVATAR_MULTIVIEW_EVIDENCE_AND_AUTHORING_QUEUE_v1.md`.

## 2026-07-16 Existing Gwen And Adult-Continuation Kathryn Correction

The initial fail-closed profile audit was followed by explicit owner version
selection:

- Existing `spider_gwen_spider_gwen_20260606_013325` is Earth-65 main-comics
  Ghost-Spider at the current young-adult/college build point, age 18-20. It now
  passes adult canonical preflight. The separate adult avatar-only workaround is
  superseded/inactive and must not be treated as a second Gwen.
- Gwen has 4/4 exact-hash draft sources and 0 reviewed identity views. The
  current blocker is reviewed view/crop/calibration/landmark coverage, scale,
  adult base, and then the missing new-surface likeness author—not maturity.
- Kathryn is selected at the adult 2016 NBC unaired-pilot continuation point.
  *Cruel Intentions 2* is an Amy Adams backstory layer only; it cannot provide
  Sarah Michelle Gellar voice, likeness, or present-body evidence. The 1999 film
  and 2016 pilot are separate Sarah Michelle Gellar source packs.
- Kathryn's existing project chat/personality is hash-preserved. Her new adult
  orchestration request uses pictures as identity authority and an actor model
  only as optional measurement/topology guidance. Its honest plan is blocked on
  the adult-present multiview manifest and all later component/rig/review proofs.

Nothing in this correction renders, voices, installs, replaces, or activates a
candidate.

## 2026-07-16 Positive-Proof Auto-Build Gate And Failed Body Proofs

Conditional downstream body authoring is now enforced by
`Core/avatar_positive_proof_gate.py` and
`Avatar/avatar_builder/policies/positive_proof_autobuild_gate_v1.json`. One
exact clothed build must bind body, eyes, hair, clothing, and rig hashes; pass
topology, likeness, deformation, face/eye, ground-contact, locomotion, posture,
prop-contact, separate-clothing, and privacy gates; and receive Robert's exact
clothed in-motion approval before the planning backlog can release. A passing
proof permits at most one downstream authoring job at a time and never grants
runtime activation or public export.

Current evaluation is deliberately `locked_no_positive_proof`. No downstream
body was queued.

The inactive adult Kira R3 attempt improved the backend but failed the visual
gate. It preserved a 79-bone export, three diagnostic poses, and four separate
clothing meshes, but the source face has sculpted closed-eye sockets: generated
eye caps sit above/outside the sockets in oblique views. Auto-cut garment seams,
block shoes, 0.675 mm ground penetration, missing hair, and missing Kira likeness
also fail. Live Kira remained byte-identical and was not activated. Continue
with socket-aware face retopology plus authored garment/footwear retopology; do
not continue pasted eye caps or threshold-cut body-surface clothing.

The exact owner-supplied adult Beth source was also audited before trying
another build. It contains separate eye and hair surfaces, but zero rig/weights,
animations, morphs, or garments. Its body/head geometry is highly fragmented
and open; its eyes are open shells. Existing R6/R7 evidence already shows the
heuristic rig, eye, shirt/pants, shoe, deformation, and contact failures, so the
known-bad path was not rerun.

Evidence:

- `Data/codex_reports/20260716_kira_inactive_avatar_quality_r3.md`
- `Data/codex_reports/20260716_beth_owner_supplied_asset_level_audit.md`
- `Data/codex_reports/20260716_continuity_and_positive_proof_release_gate.md`

## 2026-07-16 Separate Same-Size Wearable Component Contract

Clothing remains separate from body geometry and is now explicitly modeled as
a persistent, potentially shareable inventory component. The general contract
is `Core/wearable_component_contract.py`; its fail-closed policy is
`Avatar/avatar_builder/policies/separate_shareable_wearable_components_v1.json`.

Same-size sharing requires actual measurement-envelope agreement, the same
maturity lane, an exact target body/rig adapter, reviewed deformation and
penetration, physically reviewed put-on/take-off transitions, owner and wearer
consent, and a transfer record. A size label alone does not prove fit. The
garment artifact and single physical item identity remain unchanged; target
bindings are adapters, not cloned garments.

This contract created or approved no production clothing. It grants private
fit-review eligibility only and cannot activate a wearable, authorize public
export, or release auto-build. The positive-proof policy remains byte-unchanged
and locked. See `System/Docs/AVATAR_SEPARATE_SHAREABLE_CLOTHING_v1.md` and
`Data/codex_reports/20260716_elsa_temporary_ai_and_shareable_clothing_contract.md`.
