# Actual Mars doorway interaction050 — isolated candidate

The saved Mars layout already has six framed, hinged doors, closed-leaf collision, animated leaf poses, occupancy-held swing volumes and an explicitly paired airlock. This audit found a separate everyday control fault: the F key and door button selected only by distance, regardless of camera direction. A nearby door behind the user could win over the door they were facing.

The fault was reproduced by walking through the actual saved geometry, not a substitute world. At airlock feet `[1.5, 0, -2.1]`, looking toward the corridor still targeted `opening_1` behind the user. After closing that entry, pressing F opened it again instead of opening the faced exit. At corridor feet `[1.5, 0, 2.74]`, looking either west or east targeted the Crew Living door. The Operations doorway to the west could not be selected from that position without moving closer or using a programmatic explicit ID.

## Bounded correction

The candidate changes two frontend files. The low-level `nearest(feet, yaw)` query optionally filters doors to the horizontal facing direction within plus/minus60 degrees; proximity-only `nearest(feet)` remains compatible. The walking controller passes its current yaw to both the snapshot's button target and the implicit F/button action. Explicit low-level door IDs preserve their existing proximity, swing and interlock rules. When no faced door is available, the action reports “Face a nearby door to open or close it,” and the existing button label gives the same instruction.

The candidate targets the exit while looking toward the corridor, Operations while looking west, and Crew Living while looking east. Looking sideways in the airlock produces no target and no door mutation. An open entry still blocks opening the exit; closing the first door remains possible after turning to face it. No movement, collision shape, leaf angle, reach distance or paired-door policy changed.

## Mechanical checks and existing room distinctions

Seven checks against the pinned actual saved Mars geometry pass, with the installed dressing plan's51 extra colliders included in the walking checks. All six door paths are blocked when closed, clear in both directions when fully open, and blocked after reclosing. Every sampled opening/closing pose, frame and collider array is exactly equal between installed and candidate door systems. The actual viewer callback and four button states are exercised in a Node VM with inert UI objects; this is code-level message verification, not browser or visual review.

The installed dressing plan provides16 equipment assemblies across six authored functional rooms: EVA lockers/bench/hoses, airlock controls/filter cylinders, operations consoles/server rack, bunks/galley/storage, laboratory glovebox/workbench/sample storage, and observation seating/growing rack. These are existing shaped assemblies, not merely names. This audit does not establish that their appearance convincingly communicates those functions; whole-room visual quality remains unapproved. The airlock still joins two interior spaces and is not an operational exterior EVA transition. There is no pressure, seal, atmosphere, or scientific-equipment simulation.

The existing040 research notes support visible construction, controls tied to real state, distinct room functions and shared drawn/collider/export geometry. They do not certify the present procedural habitat. This correction addresses control intent rather than adding signs or changing room labels.

## Export and installation hold

Nothing is installed. The two proposed frontend hashes would create a new immutable preview on an explicit refresh; old previews must retain their frozen behavior. The current export API accepts exact viewer/controller hashes, and its authored controller source still contains the previous distance-only query. Installing these two frontend files alone would make a freshly refreshed preview fail the current exporter appearance check. Therefore `REVIEW-PLAN.json` is a source proposal, **not a complete install plan**.

Before promotion, a coordinated successor must update the export controller source with this same selection behavior, retain its definitions/hinge ownership API, update reviewed producer/source pins and exporter eligibility, and validate an actual immutable preview/package round trip. The existing independent experimental package consumer has its own interaction code and is not silently claimed to inherit this fix. Geometry, paired-door metadata and exported mesh dimensions need not change. No native engine or VR behavior is established.

The selection cone is not pixel picking or an occlusion raycast; pitch is intentionally not used for a horizontal nearby-door action. Conservative AABB collision and full-sweep occupancy checks remain unchanged. A separate visual review is still needed before declaring the interaction comfortable or the habitat realistic.

## Preservation and test history

`BASELINE-TARGET-REPRODUCTION.json` records the actual wrong target. `ACTUAL-DOOR-TEST-RESULT.json` records corrected targets and all six route checks. `VIEWER-MESSAGE-RESULT.json` records inert callback/button tests. Source geometry bytes and all116 protected inputs remain unchanged. No source world was copied, no preview was refreshed, and no model, renderer, browser, native window, GPU job or installation ran.

The first route harness combined structural, door and furniture colliders into one list and hit the navigation helper's128-item limit. The real controller uses three separate bounded collections. The corrected harness checks all three collections separately; the faulty harness and receipt remain in `history/combined-collider-harness-failure`. No product limit was raised.

To reproduce, pass the explicit saved geometry path, its SHA256 and the installed engine directory to `test_actual_doors.mjs`. The source geometry is deliberately not bundled. `test_viewer_messages.mjs` needs only Node and the candidate viewer source. `SOURCE-PINS.json` records dependencies; `SOURCE.diff` is the exact frontend proposal.
