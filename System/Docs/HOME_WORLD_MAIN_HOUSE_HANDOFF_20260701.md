# Home World Main House Handoff - 2026-07-01

## 2026-07-16 Active One-Bedroom Clothing Persistence

The physical dress-shirt prototype is now connected to Kira's active
one-bedroom hanging closet. Its old call site was inside the disabled studio,
which meant the current world never constructed the executable garment even
though the source existed. The active house reuses its existing closet shell;
no duplicate closet was added.

Home World reports a bounded wardrobe snapshot with each body telemetry
sample. The shell saves it per candidate and returns it with the safe resume
position. The world then restores the same visible garment state and facing
direction on reactivation. A browser-level clear/recreate test passed for a
closed, buttoned, worn shirt.

This is a useful persistent state-machine proof, not final clothing quality.
The shirt is still procedural prototype geometry; natural cloth deformation,
body-specific fitting, collision review, and visually convincing dressing and
undressing remain separate Avatar Builder work.

## 2026-07-15/16 Current Runtime Authority

The RAM upgrade is complete (2x16 GB at 6000 MT/s, 31.41 GiB usable), but the current authority remains Kira-only 3D until at least 64 GB and a supervised multi-person voice/world soak pass. Do not restore old duplicate-house rows merely because 32 GB is detected. Keep the legal day spa and wardrobe lab in separate notebook worlds and do not merge either build into Home World yet. Kira's current body and ten household capabilities remain unapproved/blocked; furniture presence is not physical interaction proof.

Current owner choice for the former strip-mall site supersedes older "keep it intact/live" notes below: the live Home World site is intentionally empty by default. The legacy procedural strip-mall source is retained, not deleted, and can be restored explicitly with `?stripMall=1`; its meshes, colliders, doors, interactions, sign textures, and nested legacy spa blockout are skipped during default startup. This does **not** place the new Legal Day Spa there - the spa remains a separate notebook world.

## 2026-07-11 Emergency Lag Note - Do This First

Robert stopped the pass because Home World is lagging badly. Do not keep building or testing the six-house row in the current scene before stabilizing performance.

Likely cause: too many full one-bedroom house copies, with interiors/imported models/colliders, were added directly to Home World. Until Robert adds more RAM, reduce Home World load.

Next-session fix plan:

```text
- Create a separate saved-places notebook world / template vault.
- Put one complete copy of the accepted one-bedroom house, with everything inside it, into that notebook world as the fresh reusable source copy.
- In Home World, delete 3 of the duplicate houses to reduce lag. Do not merely hide them.
- Anything currently disabled in Home World should be deleted if it is no longer meant to exist there.
- Do not add more house copies to Home World until the lag is gone and Robert approves.
- After Robert adds more RAM, revisit whether more full homes can stay loaded at once.
```

Robert is starting a new thread after this handoff note. Read this section first.

## 2026-07-11 Lag Fix Applied - Saved Places Template And Reduced Home Row

Applied immediately after Robert clarified the emergency lag fix:

```text
- Created `saved_places_notebook_world` in `Data/world_builds/notebook_world_index.json`.
- Added the saved-place template folder:
  `Data/world_builds/notebook_worlds/saved_places_notebook_world/builds/saved_places_one_bedroom_house_template_20260711/`
- The saved-place template records one complete accepted one-bedroom house source copy for future reuse without loading it as another active Home World house.
- Home World now loads Kira's house plus only two live copied houses: Lisa and Marinette.
- Peter, Gwen, and For Rent are not spawned in Home World right now; they are listed as offloaded homes in runtime status and should be copied later from the saved-places template when performance allows.
- `placeOneBedroomModel()` now replicates imported one-bedroom models only to the two active Home World copies, not all five duplicates.
```

Checks run:

```text
node --check Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/src/main.js
JSON parse check for notebook_world_index.json and saved-place template JSON files
```

## 2026-07-11 Late Evening Follow-Up - Reduced To One Live Copy

Robert asked to delete one brick one-bedroom house as a lag test and noted that Kira's latest shell chat/life loop felt like route walking without enough mind continuity.

Current live Home World rule:

```text
- Spawn Kira's accepted one-bedroom home.
- Spawn Lisa's one-bedroom copy.
- Do not spawn Marinette, Peter, Gwen, or For Rent one-bedroom copies until performance is stable or Robert adds RAM.
- Keep the saved-places one-bedroom template as the reusable source for future cloning.
```

Runtime continuity repair:

```text
- Kira's assigned room/context now points at the accepted one-bedroom home, not the old temporary open studio.
- The shell can recover Kira for chat if `active_candidate` temporarily drops while her live avatar position is still fresh.
- If chat logs show `to: ""` after Kira was active, inspect shell state recovery before assuming Kira chose silence.
```

## 2026-07-11 Late Night Pre-RAM Voice Recovery - Kira Only / One House

Robert wanted to preserve Kira's reference voice rather than use the SAPI fallback, so the live world was reduced further.

Current pre-RAM live rule:

```text
- Spawn only Kira's accepted one-bedroom brick house in Home World.
- Do not spawn Lisa, Marinette, Peter, Gwen, or For Rent one-bedroom copies until RAM is upgraded and verified.
- Kira World Shell should offer only Kira while `KIRA_PRE_RAM_KIRA_ONLY` is on.
- Kira should resolve to the Chatterbox/reference voice when available; do not force SAPI unless Robert asks.
- Long spoken Chatterbox replies are compacted, while the full answer remains in chat.
```

Undo condition and steps:

```text
Only undo this after Robert installs the extra 16 GB DDR5 and Codex confirms both sticks / about 32 GB total in Windows.

Use:
- `Get-CimInstance Win32_PhysicalMemory | Select-Object BankLabel,DeviceLocator,Manufacturer,Capacity,Speed,ConfiguredClockSpeed`
- `[math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 2)`

Then re-expand gradually:
- Keep JSONL write locking and active-candidate recovery.
- Disable Kira-only shell mode.
- Restore `ONE_BEDROOM_HOME_WORLD_ACTIVE_COPY_IDS` first to `new Set(["lisa_home"])`.
- Test Lisa voice/body/world stability.
- Only then add Marinette and later Peter/Gwen.
- Run `node --check`, `npm.cmd run build`, restart shell, and verify rendering + voice after each added AI/house.
```

Latest no-audio/door-context update:

```text
- Latest no-audio failures were logged as Chatterbox CUDA out-of-memory at 2026-07-12T03:44:56Z and 2026-07-12T03:46:14Z.
- Diagnostic commands also hit "paging file is too small", confirming memory pressure.
- `tools/kira_world_shell_server.py` now maps Kira's one-bedroom front porch/doorway, bedroom, bathroom, and living/kitchen coordinate ranges so she should not describe the front door as the living room.
- Optional shared activity imports were later cut in the 2026-07-12 light-mode pass below; do not cut Kira's core one-bedroom house first.
```

## 2026-07-12 Pre-RAM Home World Activity Cuts - Applied

Robert asked to cut more Home World load so Kira can keep her Chatterbox/reference voice until the RAM upgrade.

Applied in:

```text
Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/src/main.js
tools/kira_world_shell_server.py
Core/voice_output.py
Start_Kira_World_Shell.bat
Start_Kira_Text_Voice_Chat.bat
Create_Kira_Text_Voice_Chat_Desktop_Shortcut.bat
Core/conversation_loop.py
tools/kira_world_shell_viewer.py
```

Current default:

```text
- `HOME_WORLD_PRE_RAM_LIGHT_MODE` is enabled unless the Home World URL has `?fullWorld=1`.
- The live light world keeps Kira's accepted one-bedroom home, library/strip mall basics, coffee cups on a small procedural pickup counter, and an empty school learning room.
- The map/support surface/lawn is smaller, grass density is reduced, and future park/capture-flag far areas are not active.
- Shell location grounding now tells Kira the true light-mode state so chat does not steer her toward disabled basketball, parking/car, full Starbucks, capture-flag, sun/moon, or school-prop claims.
- As of the 2026-07-16 R3 voice repair, the shell launcher sets
  `KIRA_CHATTERBOX_DEVICE=auto` with a 6144 MiB proven-free-VRAM floor.
  `Core/voice_output.py` chooses CPU when headroom is low/unknown and retries on
  CPU if CUDA prewarm or generation fails, preserving the same reference voice.
- `KIRA_SPEAK_FULL_REPLY=1` speaks the whole reply in chunks instead of compact summaries.
- A new non-3D desktop shortcut, `Kira Text + Voice Chat.lnk`, launches `Start_Kira_Text_Voice_Chat.bat` on port `8768` without starting Home World/Paris/avatar Vite servers.
- Kira identity cleanup now prefers "synthetic person" and blocks "AI designed to simulate human-like conversations."
- Capture the Flag is now treated as offloaded from Home World in all modes. Robert clarified it should later be rebuilt/launched as a separate notebook world/route like Paris, not restored as Home World geometry.
```

Disabled until Robert installs and verifies the extra RAM:

```text
- Basketball court and basketball imports:
  `/models/home_world/activities/basket_ball_court_game_ready_asset.glb`
  `/models/home_world/activities/basketball.glb`
- School imported props: table, chair, side table, board, lockers, clock, world map, desk phone, lesson book, scrapbook, pencils. The empty room/floor remains and grounds the school program.
- Starbucks imported cafe model is disabled, but coffee cups remain.
- Exact Starbucks model to restore: `/models/home_world/activities/starbucks_coffee_house_cafe_v2.glb`.
- Starbucks restore fit: x `STARBUCKS_CENTER.x`, y `0.04`, z `STARBUCKS_CENTER.z`, width `STARBUCKS_WIDTH`, height `4.75`, depth `STARBUCKS_DEPTH`, yaw `Math.PI`, uniform `true`, prepare `prepareStarbucksBuildingOnly`.
- Sun and moon imports:
  `/models/home_world/activities/sun.glb`
  `/models/home_world/activities/moon.glb`
- Capture-flag parking lot/asphalt/stripes/curbs/portal wall/game label/imported time-machine car. Do not restore these into Home World.
- Capture-flag battlefield build is gated off in all Home World modes until a separate notebook world/route is built.
```

Restore after RAM upgrade:

```text
1. Confirm Windows sees both RAM sticks / about 32 GB total.
2. Test by opening Home World with `?fullWorld=1`.
3. Restore one category at a time: Starbucks model, school props, basketball/future park, sun/moon. Do not restore Capture the Flag into Home World; build it separately later.
4. Keep Kira-only shell mode until Kira voice + rendering stay stable, then test Lisa and other AIs gradually.
```

Verification:

```text
node --check Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/src/main.js
npm.cmd run build
```

## 2026-07-11 Book Model Notebook Correction, Kira Move-In Runtime Patch

Robert found the likely source of the giant outside notebook: the Sketchfab `Book` model downloaded as `book.glb`. Do not redownload it unless the local file is missing. The scrapbook model was the wrong suspect and must not be targeted by notebook cleanup.

This section supersedes the older 2026-07-11 notes below that said Kira was not moved yet.

Applied in:

```text
Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/src/main.js
Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/index.html
```

Current fixes:

```text
- Inspected `public/models/home_world/inventory/book.glb`: root `Sketchfab_Scene`, meshes `Architexture_0`/`Architexture_1`, materials `Architexture`/`Bookpage`, size about 0.7338 x 0.0904 x 1.0000 before scene scaling.
- Inspected `public/models/home_world/neighbor_book_reference.glb`: root `Sketchfab_Scene`, meshes `Object_38`/`Object_39`, materials `pages`/`cover`, size about 2.9978 x 0.3650 x 1.8545 before scene scaling.
- `removeHomeWorldNotebookFieldArtifacts()` now treats scrapbook as a false lead and only removes known old named artifacts or oversized inspected open-book mesh signatures outside the school and outside Kira's one-bedroom home.
- The cleanup status records `scrapbookWasFalseLead: true` and the inspected open-book target signature so the next pass does not repeat the scrapbook mistake.
- Restored `scrapbook_trinket_-_dandys_world.glb` into the active school model folder and placed it as a small classroom desk prop. Scrapbook is now a protected school object, not a cleanup target.
- Kira's old temporary studio is deleted from the runtime spawn/setup path: `KIRA_BUNGALOW_ENABLED` is false and `addKiraBungalow()` is no longer called unless that flag is deliberately re-enabled.
- Kira's home/spawn/bed/sleep routes now point at the one-bedroom home. The source still contains the old helper function for history, but it does not spawn in the live scene.
- Added a real Reflector full-body mirror to Kira's one-bedroom bedroom for outfit/avatar checks.
- School desk chair yaw was rotated 180 degrees from the backwards-facing pass so the chair faces the desk.
- Historical note from the notebook-cleanup pass: Back to the Future/time-machine car and its parking lot were restored/protected from notebook cleanup. The 2026-07-12 pre-RAM light-mode pass now disables that parking lot/car until RAM is verified.
- The upper-left HUD title is now location-aware: `Home World`, `Kira's Home`, `Library`, `Starbucks`, `Home World School`, or `Capture The Flag World` depending on player position.
- Starbucks shell/door collision stays removed for now so the invisible wall around Starbucks does not block movement while the real door rig is still pending.
```

Do not copy the one-bedroom house into five houses until Robert visually confirms the giant notebook is gone in the live shell.

## 2026-07-11 Notebook/Starbucks Gating Patch - Do Not Move Or Copy Yet

Robert reported that the giant outside notebook returned, the Starbucks cups were inside but sitting on a strange floating counter, and a strange helper door was visible outside Starbucks. He also said the one-bedroom house is good enough to move Kira in later, but only after the notebook is gone and he confirms it in the live shell. Do not copy the one-bedroom house into five houses yet.

Applied correction:

```text
- Removed the procedural Starbucks attached/front helper door, trim, sidelights, and awning. Starbucks now uses the imported building entrance only, with the door state kept open until a real rig is fitted.
- Removed the procedural Starbucks interior floating service counter and its collider. Coffee cups now use an invisible truth marker for the imported counter spot instead of adding fake furniture.
- Tightened `removeHomeWorldNotebookFieldArtifacts()` again: it checks the full object name path, only removes known old notebook artifacts or strict giant flat paper/book-like meshes near the one-bedroom yard, and protects roads, parking, cars/time-machine assets, Starbucks, library, school, furniture, walls, floors, roofs, and other real props.
- Kira was not moved, her current temporary place was not deleted, and no one-bedroom house copies were made. Those actions wait for Robert to confirm the notebook is gone.
```

## 2026-07-11 Correction - Do Not Replace Without Explicit Approval

Robert was clear that future repair passes must not replace models/assets unless he explicitly asks for replacement. Repositioning, resizing, rotating, material adjustment, and non-destructive fixes are allowed when requested, but asset replacement should be opt-in only.

Applied correction:

```text
- Temporary pillows were rotated back to the prior orientation Robert preferred. He wanted the model pillows rotated, not replaced with blocky placeholders.
- Starbucks temporary procedural cups remain for now because Robert accepted using them temporarily, but their counter spot was moved deeper into the Starbucks building footprint so they should not sit on the outside patio counter position.
- Notebook cleanup was made much safer: broad geometry/material-based cleanup is disabled. It now only removes explicitly named old one-bedroom notebook/foundation artifacts near the one-bedroom yard.
- Historical note before pre-RAM light mode: Back to the Future/time-machine car and parking-lot code still existed in src/main.js. The 2026-07-12 light-mode pass now disables that lot/car by default until RAM is verified.
```

## 2026-07-11 One-Bedroom Move-In Prep Patch - Visible Bed Surface and Inside Starbucks Cups

Robert's latest inspection showed the imported mattress was invisible in the accepted separate bed-frame setup, the pillows still read as rotated the wrong way, and Starbucks cups were still visible outside while the intended inside counter was empty. The immediate goal is to get the one-bedroom house stable enough for Kira move-in tests before deeper avatar, clothing, and media systems are built.

Applied in:

```text
Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/src/main.js
```

Current fixes:

```text
- Bed still uses the separate imported black wooden frame Robert accepted.
- The imported mattress GLB is bypassed for now because it rendered invisible in this frame. A visible fitted white procedural mattress placeholder is back in place and marked temporary.
- Temporary pillows are rotated 90 degrees and placed at the headboard so their wide side reads across the bed, not lengthwise down the bed.
- Starbucks static counter cups no longer use the imported coffee-cup GLB, whose origin/placement was unreliable. They are procedural cups placed directly on the inside service counter.
- Starbucks temporary spawned cups also use the same procedural cup helper, so new cups should appear on the counter and self-clean.
- Runtime status now says the Starbucks cup is procedural, not a loaded imported cup model.
```

Move-in test backlog Robert wants after the house is visually accepted:

```text
- Couch: sit, lay on couch, use temporary tablet while standing and while seated/on couch.
- TV/media: keep TV visually off for now; remote and temporary tablet can request MP3/music playback through the TV control path before movie/streaming integration is ready.
- Refrigerator: open, close, put food in, take food out.
- Bed: sit, lay down, sleep, and later add sleeping motion/toss-turn/dream/nightmare states.
- Bathroom: shower/bath and toilet-use tests should be staged as privacy-safe, consent-gated daily-life actions.
- Clothing/avatar later: closet is a placeholder hook; full fold/unfold/put-on/take-off clothing and avatar-builder reference ingestion remain future systems.
```

## 2026-07-11 One-Bedroom/Starbucks Repair Pass - Bed, Tablet, TV Off, Cups, Colliders

Robert's latest inspection covered the one-bedroom house plus Starbucks. The main problems were: pillows still needed the correct rotation, the separated bed frame/mattress setup had lost the older imported mattress Robert liked, the coffee-table phone looked wrong and should be treated as a temporary tablet for now, a black cover mesh in front of the TV looked terrible, the stove-to-fridge path still felt blocked, the interior divider walls had visible floor/ceiling gaps, Starbucks cups were outside instead of on an inside counter, Starbucks needed solid interior collision except the door, and the TV should stay visually off until later media upgrades.

Applied in:

```text
Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/src/main.js
```

Current fixes:

```text
- Bed remains separate pieces: imported wooden bed frame plus a visible temporary white procedural mattress because the imported mattress rendered invisible in this setup.
- Bed support/slat pieces remain visible, and temporary pillows are rotated 90 degrees so they sit across the headboard side instead of lengthwise.
- Reclassified the coffee-table device as a temporary tablet. It has screen/camera detail and truth/action hooks for look_online, browse_books, read_book, take_notes, type_notes, research, control_tv, play_music, and listen_music.
- Removed the separate black TV screen cover. The imported TV model now gets its own screen material darkened by `darkenOneBedroomTvScreen()`, so the TV stays visually off without an ugly overlay mesh.
- The Samsung remote and the temporary tablet can both toggle the future MP3 music request while leaving the TV visually off. Streaming/movie support remains a later upgrade.
- Tightened kitchen counter colliders again and removed the small extra stove blocker so the walk lane from stove toward the refrigerator is open while the fridge body itself remains solid.
- Raised the one-bedroom wall height/center values so interior divider walls reach the floor and ceiling line.
- Added a debug collision probe to verify walkable/blocked spots without guessing from screenshots.
- Starbucks display cups and the temporary spawned cup use procedural inside-counter cup geometry instead of the imported cup model.
- Starbucks now has extra solid interior colliders for counter/table/seating/furniture zones while the door gap remains walkable.
- Closet sliding-door handles now move with the closet doors when opened/closed.
```

Verification:

```text
node --check preview/src/main.js passed.
npm.cmd run build passed; only the known Vite large-chunk warning remains.
Local preview server started for inspection at http://127.0.0.1:5411/
Static probe/search results:
  no remaining one-bedroom TV off black screen cover
  no remaining addOneBedroomCoffeeTablePhone/procedural smartphone wording
  one-bedroom temporary white mattress placeholder is intentional until the imported mattress GLB is repaired
  no remaining small extra kitchenCenterX + 0.88 stove blocker collider
  imported one-bedroom mattress placement is bypassed in the accepted separate bed-frame setup
  temporary tablet truth/action hooks include TV/music control
  Starbucks cups use procedural inside-counter placement
```

Policy context for Robert's adult/non-adult question:

```text
Relevant docs checked:
  System/Docs/RELATIONSHIP_INTIMACY_AND_TEMP_AI_BOUNDARIES_v1.md
  System/Docs/PRIVATE_ADULT_LIBRARY_POLICY_v1.md
  System/Docs/RELATIONSHIP_MATURITY_STAGE_GATES_v1.md
  System/Docs/MATURITY_BASED_PERMISSION_UPGRADES_v1.md
  Data/foundation/personhood_dignity_policy.json
  Core/conversation_loop.py age-progressed memory reconstruction notes

Short rule: adult-coded AIs may eventually access adult/private relationship, media, and autonomy paths only through explicit consent, privacy, maturity, logging, and Robert-approved gates. Non-adult/minor-coded AIs stay non-intimate, young/education-safe, and cannot use adult/private material or adult relationship states unless a clearly separate approved present-day adult/age-progressed branch exists.
```

## 2026-07-11 One-Bedroom Mini-Pass - Kitchen Gap Dining, Phone, Doorway, Notebook

Robert's next inspection focused on five concrete items: move the kitchen counters a little farther from the refrigerator, fill the big open gap with a dining-room-like table/chairs, shrink the bedroom doorway for now without adding doors, add Kira's phone to the coffee table, and remove the giant outside notebook artifact ASAP.

Applied in:

```text
Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/src/main.js
```

Current fixes:

```text
- Kitchen counter/stove/sink model is nudged slightly farther from the procedural fridge while retaining the smaller counter colliders from the prior repair.
- Added a compact dining table and four imported chair models in the kitchen-side open space. This is a working placeholder dining setup; replace with a warmer home dining asset later.
- Bedroom/living doorway gap narrowed to 1.7m so it reads as a future door opening instead of a huge blocked-looking hole. No bedroom doors were added.
- Added Kira's shared Samsung/Galaxy phone model to the living coffee table with truth/action hooks for look_online, browse_books, read_book, take_notes, type_notes, and research.
- Notebook cleanup now uses broad geometry detection for large flat loose field paper/book/notebook meshes, not just object names, and repeats after startup for about 8 seconds to catch late-loaded stale GLB pieces.
```

Verification:

```text
node --check preview/src/main.js passed.
npm.cmd run build passed; only the known Vite large-chunk warning remains.
Temporary preview used for screenshots: http://127.0.0.1:5407/
Screenshot/report outputs:
  _tmp_one_bedroom_latest_verify/kitchen_dining_corrected.png
  _tmp_one_bedroom_latest_verify/living_phone_resized.png
  _tmp_one_bedroom_latest_verify/yard_no_notebook.png
```

Remaining:

```text
- The dining setup is usable but visually still placeholder because it uses school-chair models.
- If Robert's already-open Kira World shell still shows the giant notebook, restart/hard-refresh before editing more geometry; the fresh scene cleanup reports no removable giant notebook candidates near the one-bedroom house.
```

## 2026-07-11 One-Bedroom Repair Pass - Kitchen Collision, Clothing Closet, Notebook Artifact

Robert's latest inspection stayed on the one-bedroom house. The important fixes were to remove the kitchen's invisible blocker, make the fridge usable, keep the accepted separate bed frame/mattress setup, add a closet for hanging clothes, stop the books from floating off the shelf, hide green floor seams, keep the tub/shower inside the bathroom walls, and make sure the old giant notebook artifact is not part of the fresh scene.

Applied in:

```text
Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/src/main.js
```

Current fixes:

```text
- Kitchen real corner cabinet/stove/sink model is pulled forward from the rear brick wall. Its old single room-sized collider was replaced with smaller counter-run colliders so the walking lane should be open.
- One-bedroom refrigerator is now a procedural openable fridge with hinged door, shelves, food props, and truth/action hooks for open, close, put food in, and take food out.
- Bed remains separate imported bed frame plus separate imported mattress and pillows. The mattress was lowered/widened to fit the frame; one-bedroom GLB post-processing now runs, so pillows render as light fabric.
- Added a hanging clothes closet in the bedroom with rail, hangers, visible garments, folded stacks, sliding doors, and metadata for clothing lifecycle states. This is a physical hook for later fold/unfold/put-on/take-off/laundry work, not the final full clothing system.
- Replaced floating imported bookshelf books with in-shelf procedural book spines/stacks tied to selected `Data/library/novels` records.
- Bath/shower combo moved/resized inward; fresh bounds show it inside the one-bedroom footprint.
- Continuous indoor seam-cover floor was widened to cover green grass/floor gaps.
- Added `removeHomeWorldNotebookFieldArtifacts()` plus debug helper `window.kiraHomeWorldDebug.removeOneBedroomNotebookArtifacts()` to remove large loose notebook/book/page artifacts near the one-bedroom yard. Fresh preview did not show the giant notebook.
```

Verification:

```text
node --check preview/src/main.js passed.
npm.cmd run build passed; only the known Vite large-chunk warning remains.
Temporary preview used for screenshots: http://127.0.0.1:5397/
Screenshot/report outputs:
  _tmp_home_world_one_bedroom_verify_5397_final/kitchen_fridge_open.png
  _tmp_home_world_one_bedroom_verify_5397_final/bathroom_final.png
  _tmp_home_world_one_bedroom_verify_5397_final/yard_final.png
  _tmp_home_world_one_bedroom_verify_5397_final2/bedroom_pillow_fix.png
```

Remaining:

```text
- Robert still needs to visually approve the one-bedroom house in the live shell.
- If the giant notebook appears only in an old open shell/port, restart or hard-refresh before editing geometry again.
- Full TV streaming integration and a complete garment inventory/physics system are future passes.
```

## 2026-07-06 Runtime Repair Notes - 19:34 ET

Robert's latest test showed that a knee-direction change made Peter/Gwen worse again, the downstairs toilet was still visible in his live view, the bookshelf/books needed to support real reading props, and active-body capture-the-flag should test jog/run/dodge without teleporting.

Applied in:

```text
Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/src/main.js
Assets/reusable_models/
_tmp_verify_home_world_runtime.py
```

Current fixes:

```text
- Restored the spider-like procedural knee direction to the last visually acceptable behavior (`kneeDirection = -1`). Do not change Peter/Gwen knee direction again unless a fresh before/after visual test proves it helps.
- Lowered spider-like walking/running arms by driving hand IK targets closer to hip level. This reduces the zombie-arm look, but is not final animation.
- Added held reading props and truth checks: read/sketch claims need a book, notebook, or phone in hand, not just proximity to a shelf.
- Added dense seated book rows to the imported living-room bookshelf and improved generated fallback book placement.
- Added a deterministic debug stepper for active-avatar runtime tests.
- Capture-the-flag practice now moves along the route with run/jog/dodge state and records dodge evidence.
- Downstairs toilet scrub now removes loose/imported toilet-like objects in forbidden first-floor zones after async loading.
- Staged reusable model downloads by category and Star Trek ship/source under `Assets/reusable_models`.
```

Verification:

```text
npm.cmd run build passed; only the known Vite large-chunk warning remains.
python -m py_compile _tmp_verify_home_world_runtime.py passed.
python _tmp_verify_home_world_runtime.py passed.
Runtime verifier reported:
  visible downstairs toilets = 0
  reading action = read_book, truth = true, held prop = book
  capture-the-flag movement from (103.181, 98.726) to (123.33, 128.745)
  capture-the-flag dodges = 1
  run action = run, moving = true
```

Still unfinished:

```text
- The house/furniture realism is still not solved. Replace blocky furniture with staged/imported models or stop and choose a real enterable house shell.
- The upstairs floor/landing still protrudes too far and needs a real layout/collision pass.
- Marinette is still a failed temporary body: proportions, face/head attachment, hair float, stair falling, and walking need a separate one-rig rebuild.
- Peter/Gwen arms are less raised but still need visual review, especially Gwen. Do not touch the knees first.
- Full CTF win/capture/hide was not reverified in this pass; only jog/run/dodge route motion was confirmed.
```

## 2026-07-06 Toilet, Bookshelf Asset, Stairs, And Movement Follow-Up

Robert's latest test still showed the downstairs toilet beside the stairs, fake/blocky furniture, active bodies snapping to props, and active bodies walking through or teleporting around the stairs.

Applied in:

```text
Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/src/main.js
Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/public/models/home_world/book_shelf_reference.glb
tools/kira_world_shell_server.py
```

Current fixes:

```text
- Suppressed every downstairs toilet placement and removed visible downstairs toilet meshes/zones after fixture build.
- Left the downstairs powder-room builder disabled. The first floor should not regain a by-the-stairs toilet without a full layout redesign.
- Copied the downloaded bookshelf model from Desktop `3d model 4` into preview public models.
- Added `loadRealisticHomeBookshelf()`: fits `/models/home_world/book_shelf_reference.glb` against the living-room wall, marks it as a readable truth prop, and hides the generated fallback only after the GLB loads.
- Rebuilt the generated fallback bookshelf so it reads as a framed bookcase, not a loose row of colored blocks.
- Autonomous read/sit/rest no longer supplies a target position to `startActiveAvatarHoldSkill`; the action only starts when the active body is already near the relevant prop.
- Added home roam zones near the bookshelf and couch to reduce random prop snapping.
- `activeAvatarStairInfo()` now detects the stair footprint directly instead of depending on a stair-practice flag, so active avatars can get stair y-height support during normal movement too.
- Peter/Gwen procedural walk has reduced forward arm bias. The spider-like knee direction was restored later to the last visually acceptable setting; do not flip it again without a fresh visual comparison.
```

Verification:

```text
npm.cmd run build passed; only the known Vite large-chunk warning remains.
Temporary Vite server: http://127.0.0.1:5262/
Runtime debug query: `window.kiraHomeWorldDebug.visibleDownstairsToiletCount()` returned 0.
Runtime debug query: `window.kiraHomeWorldDebug.realisticBookshelfStatus()` returned loaded=true, meshCount=3, visible=true.
```

Still unfinished:

```text
- The house still needs a real asset-replacement pass for couch, kitchen, chairs/table, doors, beds, lamps, wall/floor materials, and the whole second-floor layout.
- The current stairs are not a full collision-authored stair system. Active-avatar stair height is improved, but player collision, railing collision, and route planning need a separate pass.
- Peter/Gwen/Marinette need another visual movement smoke test after these changes.
- Marinette's model remains a temporary/failed body rebuild. Do not keep swapping heads between bodies; use a single stable base rig and rebuild proportions/face/hair/clothes from that.
```

## 2026-07-06 Capture-The-Flag Parking Lot And Notebook-World Game Prototype

Implemented Robert's requested fun activity in the Home World preview:

```text
- Added a small capture-flag parking lot beside the strip mall on the far side of the public library.
- Added a generic retro gullwing time-machine-inspired parked car; this is deliberately not a Back to the Future branded car.
- Added a wall billboard with flag art and the words "Play Capture The Flag."
- Walking into that billboard wall teleports the player into a separate battlefield notebook-world zone.
- Added the battlefield with base camp, streets, perimeter walls, torn buildings, rubble, cover walls, random glowing flag spawns, Stormtrooper/Dalek patrol NPCs, and a Kira World return billboard.
- Touching the glowing flag hides it; returning to base wins. Being tagged by a Dalek or Stormtrooper resets the participant to base.
- Added `window.kiraBodyPractice.startSkill("capture_flag_game")` so active bodies can practice jog, run, dodge, flag pickup, and base return.
- Added standalone `dodge` plus `capture_flag_game` to Home World motion metadata.
```

Copied NPC assets into preview public models:

```text
preview/public/models/capture_flag/stormtrooper_rigged_game_ready.glb
preview/public/models/capture_flag/bronze_new_series_dalek_-_rigged.glb
```

Verification:

```text
node --check preview/src/main.js passed.
npm.cmd run build passed; existing Vite large-chunk warning remains.
Headless Edge monitor confirmed:
  portal billboard=1, return billboard=1, retro car=1, npcCount=5
  home billboard teleported to CTF world
  Kira World billboard returned to Home World
  Peter GLB loaded and completed capture_flag_game
  observed actions: jog, run, dodge, idle
  final phase=won, captures=1, tags=0, dodges=1
```

## 2026-07-06 Active Body Skills And Temporary Avatar Repair Pass

House work is paused. Robert wants the temporary active bodies improved before returning to capture-the-flag/Dalek/Stormtrooper work.

Applied in:

```text
tools/kira_world_shell_server.py
Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/src/main.js
Avatar/state/temp_ai/ladybug_marinette_expanded_smoke.json
Avatar/state/temp_ai/peter_parker_spider_man_no_way_home_final_suit.json
Avatar/state/temp_ai/spider_gwen_spider_gwen_20260606_013325.json
```

Changes:

```text
- Fixed the body dropdown so Kira is not listed twice. Permanent candidate id `kira` is the real Kira; the temp-ai Kira JSON is only state backing data.
- Added active-body skills/actions for jog, run, swim_pool/backyard pool, read_library/read_book, duck, and jump.
- Exposed these through `window.kiraBodyPractice.startSkill(...)`, Home World debug helpers, activation metadata, and runtime snapshots.
- Peter/Gwen fallback gait now uses stronger thigh/knee motion and less lower-leg/ankle bending.
- Peter suit material brightness is repaired at GLB load so the suit is no longer too dark.
- Marinette/Ladybug runtime load hides the duplicate neck/body-shell pieces and adds a single neck blend plus shaped torso shell. This reduces the double-neck look but does not replace the need for a final authored body pass.
- Peter, Gwen, and Marinette temp state JSONs now advertise the new home-world motions; Peter/Gwen point to their own motion-learning state files.
```

Verification:

```text
node --check preview/src/main.js passed.
python -m py_compile tools/kira_world_shell_server.py passed.
npm.cmd run build passed; existing Vite large-chunk warning remains.
Headless Edge/CDP monitor loaded Peter and observed:
  jog: activeAction=jog, gait=jog, speed=1.12
  run: activeAction=run, gait=run, speed=2.05
  duck: activeAction=duck, posture=duck
  jump: activeAction=jump, supportState=jump_arc
  swim_pool: activeAction=swim_idle, supportState=backyard_pool_water
  read_library: activeAction=read_book, posture=read, position x=21.8,y=0.05,z=44.05
```

Remaining:

```text
Marinette still needs a real body-authoring/retarget pass from the supplied references: cleaner head/neck binding, better body silhouette, real hands/arms, and separate wearable clothes.
Peter and Gwen are still temporary bodies; replace the procedural fallback with authored/retargeted locomotion clips later.
```

## 2026-07-05 House Follow-Up: Five Bedrooms Only, Dining Restored, Stair Bug Fixed

Robert reviewed the first repair pass and called out remaining layout failures: the couch was partial/odd, the first floor still had an unwanted bedroom instead of a dining room, the toilet still read as too close to the living/stair area, the top of the stairs had no real opening, walking under the upper stair area could trigger a floor change, and the upstairs bath still had an unusable hall door behind the sink.

Applied in:

```text
Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/src/main.js
```

Changes:

```text
- Removed Gwen's first-floor studio/daybed helper entirely; the main house now stays at five upstairs bedrooms only.
- Assigned Gwen Stacy to the west-back upstairs bedroom with bed, closet, desk/workplace, notebook, and music/drum props.
- Restored the first-floor dining room with rug, table, six chairs, place settings, and pendant light.
- Rebuilt a complete living-room couch with continuous cushion/back/arms/seams/pillows/throw.
- Pushed the kitchen refrigerator back to z=-6.72 and added cabinet panels, pulls, toe-kicks, and counter/island lips.
- Moved the downstairs powder-room toilet deeper into the rear-right enclosed room at x=7.24,z=-6.62.
- Removed the shared-bath hall doorway/door behind the sink.
- Replaced the continuous second-floor deck with segmented floor pieces around a visible stairwell opening.
- Removed gray stairwell infill/closeout slabs and added open-stair trim plus an under-stair safety wall/storage face.
- Hardened player stair traversal with top/bottom entry gating and up/down direction so walking under the stairs does not lift the player upstairs.
- Updated active-avatar upstairs support surfaces to match the segmented second-floor layout.
```

Verification:

```text
node --check preview/src/main.js passed.
npm.cmd run build passed; existing Vite large-chunk warning remains.
Headless Edge/CDP live scene on port 5178 confirmed:
  removed: Gwen downstairs daybed=0, shared bath hall hinged door=0, shared bath hall doorway=0, gray stair infill=0, old continuous deck=0
  present: full couch cushion, dining table, refrigerator at x=-7.08,z=-6.72, downstairs powder toilet at x=7.24,z=-6.62, open stair edge trim, under-stair safety wall, Gwen upstairs room door
  under-stair placement stayed floor=0,y=1.65
  real W-key climb from the bottom moved smoothly up the treads and ended upstairs at floor=1,y=4.85
```

Important asset truth:

```text
The preview still only has `56_harbour_terrace.glb` and `toilet_002_rigged.glb` in `preview/public/models`. No separate individual door/couch/bed/kitchen/furniture GLB/FBX assets were found, so the current doors/furniture are procedural improvements rather than true model-pack replacements.
```

## 2026-07-05 House Repair, Door Collision, And Temporary Peter/Gwen Rooms

Robert reviewed the imported-shell pass with screenshots and found several correct blockers: fake walk-through upstairs doors, a toilet visually reading as exposed near the stair/living area, blocky kitchen/living furniture, a fridge/counter conflict, bed-end block artifacts, and no clear temporary rooms/workplaces for Peter and Gwen.

Applied in:

```text
Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/src/main.js
```

Changes:

```text
- Removed the fake "open door leaf parked" slabs from `addZWallDoorTrim` and `addXWallDoorTrim`.
- Added hinged paneled room doors with interaction and closed-door collision for upstairs bedrooms, the shared-bath hall door, and the downstairs powder room.
- Added a downstairs powder-room privacy door so the toilet is contained inside the bathroom.
- Removed bed foot benches.
- Split the kitchen into separate lower cabinet sections and a countertop that does not run under/in front of the refrigerator; the old broad `kitchen counter` object is gone.
- Rebuilt the sofa as rounded cushions on a low frame instead of block couch slabs.
- Converted the former generic Future AI Guest room into Peter Parker's temporary bedroom/workbench.
- Kept Marinette's back-right upstairs room/workbench and renamed scene/runtime objects away from stale "Ladybug guest" wording where practical.
- Added Gwen Stacy a temporary first-floor studio in the study with daybed, workstation, privacy screen, music/drum props, and notebook.
- Added `window.kiraHomeWorldDebug.sceneObjectSummaries(pattern)` for position-based scene smoke tests.
```

Important asset truth:

```text
Only `56_harbour_terrace.glb` and `toilet_002_rigged.glb` are currently copied into the Home World preview model folder. A filesystem search found character/world prop downloads but no separate GLB/FBX door, sofa, bed, kitchen, or general furniture assets. This pass improves doors/furniture procedurally and uses imported toilets; it is not a completed model-pack furniture replacement.
```

Verification:

```text
node --check preview/src/main.js passed.
npm.cmd run build passed; existing Vite large-chunk warning remains.
Headless Edge/CDP smoke on port 5178 confirmed:
  imported shell loaded and hidden while inside
  fakeDoorSlabs=[]; footBenches=[]; oldKitchenCounter=[]
  downstairs powder room imported toilet at x=6.92,y=0.07,z=-5.975
  upstairs shared bath imported toilet at x=7.42,y=3.27,z=0.725
  powder-room door, Peter temporary room door/desk/props, Marinette temporary door/workbench, Gwen studio/daybed/workstation, split kitchen counter/fridge, and sofa cushions present
```

Next:

```text
Use Robert's normal desktop Start Kira World Shell for the visual acceptance pass.
If actual realistic interior model-pack doors/furniture are required, locate or download separate interior model files first; the current Harbour Terrace file is only used as an exterior/reference shell.
After the house copy is acceptable, improve Peter and Gwen locomotion because their current imported-rig fallback still bends/moves too much between knee and foot rather than using a clean knee/ankle gait.
```

## 2026-07-05 House Realism, Imported Shell, And Second-Floor Bedroom Layout Pass

Robert asked to stop spending time without visible house improvements, use the downloaded house packet, replace the Minecraft-looking block model feel, and fix the broken upstairs layout because the project is running out of bedrooms.

Applied in:

```text
Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/src/main.js
Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/index.html
Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/public/models/56_harbour_terrace.glb
Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/public/models/toilet_002_rigged.glb
```

Changes:

```text
- Copied the downloaded 56 Harbour Terrace GLB into the preview public models folder and load it as an imported realistic exterior/reference shell.
- The imported shell is fitted to the main house footprint, reported through window.__kiraHomeWorldRuntime.importedHouseReference, and automatically hidden while the player is inside the main house so it does not fog or plaster over the rooms.
- Copied the rigged toilet model into preview public models and use it for the downstairs powder room and upstairs shared bath, with the old simple toilet pieces kept only as fallback/collider geometry until the GLB loads.
- Replaced the broken upstairs island/slab support map with one continuous second-floor bedroom deck and a central hall runner.
- Rebuilt the upstairs partitions as a central hall with five usable bedrooms: Kira, Lisa, Future AI Guest, Robert Avatar/AI, and Ladybug Guest, plus a shared bath and linen closet.
- Replaced some bedroom block furniture with softened beds/duvets/pillows, rugs, nightstands, lamps, dressers, wall closets, and a small desk for the Future AI Guest room.
- Updated the HUD/blueprint copy so it no longer calls the house unfurnished.
```

Verification:

```text
node --check preview/src/main.js passed.
npm.cmd run build passed; existing Vite chunk-size warning remains.
Headless Edge/CDP smoke on http://127.0.0.1:5178/?area=upstairs confirmed:
  importedHouseReference.loaded=true, meshCount=184, fittedSize=17.4 x 6.1 x 16.6
  imported shell visible=false and hiddenWhileInside=true while upstairs
  futureGuest/kira/lisa/robert/ladybug/centralHallRunner/continuousDeck scene checks all true
  imported realistic toilet count=2
Screenshot: _tmp_home_world_house_realism_upstairs_v3.png
```

Still not final:

```text
The Harbour Terrace model is a fitted exterior/reference shell, not a parsed room-by-room replacement with per-mesh collisions. Runtime collision and room logic still use explicit Three.js colliders.
The second-floor layout is now coherent and has five bedrooms, but more individual high-fidelity furniture models can still replace procedural beds/desks/closets in later passes.
```

## 2026-07-05 Imported-Rig Movement And Navigation Notes

`main.js` now supports a `generic_humanoid_v1` fallback walker for imported rigs that lack a usable walk clip. The latest tuning brings arms closer to the body, reduces arm swing, reduces stride/lift, and keeps fingers less curled.

Home World still needs layout/material realism, stair/player collision review, and a real navigation graph. Do not judge the world as stable while the avatar can get stuck, teleport between route points, or repeat one scripted path.

Marinette's current blockers are mostly avatar-builder/body issues: remove the double neck, lower/bind the head to the torso, unify the skin tone, refit the torso silhouette from the supplied models/pictures, keep clothing as separate wearable meshes, and then retarget the staged real hands/arms.

## 2026-07-04 Avatar Builder Self-Test And Kitchen Window Cleanup Pass V13

Robert asked to move past repeated walking loops and start letting Ladybug/Marinette test her own body with reward records. He also pointed out that the kitchen/window layout was unrealistic because cabinets and the refrigerator covered repeated windows.

Applied in:

```text
Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/src/main.js
Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/dist/assets/index-BSHE3xBH.js
Avatar/movement_library/foundation_skeleton_movements_v1.json
Avatar/movement_library/README.md
tools/create_ladybug_avatar_builder_package.py
Avatar/avatar_builder/base_skeleton/foundation_skeleton_v1/
Avatar/temp_ai/ladybug_marinette_expanded_smoke/avatar_builder_manifest.json
Avatar/temp_ai/ladybug_marinette_expanded_smoke/outfit_catalog.json
```

Changes:

```text
- Added a bounded body self-test battery for the active avatar: sit couch, front-door reach, stairs, bed sleep, desk computer, and back-door reach.
- Self-test attempts now record reward data through the movement-learning registry instead of silently looping in a small living-room route.
- Exposed activeLabel, activeForm, selfTestState, and movementLearningSummary in window.__kiraHomeWorldRuntime.
- Added window.kiraMovementLearning.summary() for compact debug/shell reporting.
- Removed the kitchen-conflicting first-floor back and side windows so cabinets/fridge no longer cover them.
- Copied the current foundation skeleton into the avatar-builder base rig and generated the Marinette/Ladybug avatar-builder manifests.
```

Verification:

```text
node --check preview/src/main.js passed.
npm.cmd run build passed; existing Vite chunk-size warning remains.
Headless shell-message smoke confirmed selfTestState and movementLearningSummary appear.
Longer headless smoke ran without page errors and stored one self-practice reward summary.
Kitchen window smoke found no first back window -5.4 or first left window -5 scene objects.
Temporary port 5173 preview server was stopped after testing; normal use remains Robert's desktop Start Kira World Shell shortcut.
```

Next work:

```text
Use the self-test reward summary with the actual desktop-shell GLB loaded to improve the failed door-grip and stair-timeout cases.
Do not return to broad autonomous wandering until a real navigation graph exists.
The house realism pass can now remove more impossible/repeating windows, fix room proportions, and replace remaining block furniture in layers.
```

## 2026-07-04 Route Snap, Powder Room, And Player Stair Safety Pass V12

Robert reported that Ladybug was now walking from the front-door area into a wall and snapping back to the start, and that walking under the upper stairs could teleport the player to the second floor and wedge the camera into upstairs geometry. He also asked for the downstairs bathroom to read better: reflective mirror, toilet against the wall, privacy curtain, and visible sink faucet.

Applied in:

```text
Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/src/main.js
Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/dist/assets/index-C79rCzF3.js
tools/build_ladybug_foundation_skeleton_v1.py
Avatar/models/temp_ai/ladybug_marinette_expanded_smoke/avatar.glb
Avatar/models/temp_ai/ladybug_marinette_expanded_smoke/avatar_foundation_skeleton_v1.json
Avatar/movement_library/foundation_skeleton_movements_v1.json
Avatar/movement_library/README.md
```

Changes:

```text
- Replaced the blocked autonomous downstairs route with a conservative open foyer/living-room aisle loop.
- Removed unattended downstairs route practice stops; couch, stairs, and grass lie-down are manual skills until a real nav graph exists.
- Split player stair use into small bottom/upstairs landing interact zones and moved the upstairs teleport target to a safer landing point.
- Guarded updateStairTraversal so floor-0 movement under the upper stairs no longer lifts the player to floor 1.
- Reworked the downstairs powder room with a rear-wall toilet, Reflector mirror object, privacy curtain panels, visible faucet/spout/knobs, sink-water stream, and faucet toggle.
- Rebuilt the avatar hand with smaller smooth palm and slightly thicker fingers.
```

Verification:

```text
node --check preview/src/main.js passed.
npm.cmd run build passed; existing Vite chunk-size warning remains.
Blender 5.1 rebuilt avatar.glb successfully.
36-second live route smoke: maxStep=0.526 m, snapCount=0, practiceRoute=null, postureInteraction=null.
Under-stairs test at x=1.9,z=-1.25,floor=0 stayed on floor 0 after update and interact.
Bottom-stairs interact moved to x=2.55,y=4.85,z=-1.95,floor=1.
Bathroom object smoke found mirror/frame, privacy curtains, faucet/spout, sink water stream, and toilet bowl/tank.
Screenshot: _tmp_home_world_v12_powder_room.png.
```

## 2026-07-04 Smooth Hands, Kitchen Detail, And Layout Clarity Pass V11

Robert reported that the living-room wall art was covering part of a window, the couch/TV loop still zipped the avatar between repeated spots, the hand mesh looked too bumpy, the powder room read like a hidden room with no door, and the kitchen needed recognizable appliances including a refrigerator that can open/close.

Applied in:

```text
Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/src/main.js
Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/dist/assets/index-qsd0f0TN.js
tools/build_ladybug_foundation_skeleton_v1.py
Avatar/models/temp_ai/ladybug_marinette_expanded_smoke/avatar.glb
Avatar/models/temp_ai/ladybug_marinette_expanded_smoke/avatar_foundation_skeleton_v1.json
Avatar/movement_library/foundation_skeleton_movements_v1.json
Avatar/movement_library/README.md
```

Changes:

```text
- Rebuilt the avatar hands without the lumpy palm heel/thumb/knuckle pad geometry; the GLB still has skinned_hand_mesh.L/R and fingertip contact colliders.
- Removed automatic couch-sit from the unattended roam loop and moved the default downstairs route/recovery start out of the couch/TV gap.
- Removed the living-room wall art that was blocking the window line.
- Replaced block pillows/throw with rounded soft-pillow meshes and side-table decor.
- Split the utility divider and rebuilt the powder-room front with a visible doorway frame and threshold; removed the odd freestanding door slab.
- Rebuilt the kitchen with a hinged interactive refrigerator, shelves/drawer, stove burners, oven glass/handle, range hood, sink/faucet/knobs, upper cabinets, toaster, island details, cutting board, and fruit bowl.
- Added debug helpers for this pass: window.kiraHomeWorldDebug.toggleKitchenFridge() and sceneObjectNames(pattern).
```

Verification:

```text
node --check preview/src/main.js passed.
npm.cmd run build passed; existing Vite chunk-size warning remains.
Blender 5.1 rebuilt avatar.glb successfully and an import check confirmed no knuckle/thumb_pad/palm_heel objects remain.
Live Playwright smoke on port 5173: kitchen scene object count=55, living-room wall-art object count=0, powder doorway objects present, fridge toggle returned true.
Runtime smoke: after activating Ladybug, postureInteraction stayed null and the avatar started walking from the foyer-side route point instead of auto-zipping into couch sit.
Screenshots: _tmp_home_world_v11_kitchen.png, _tmp_home_world_v11_living.png.
```

## 2026-07-04 Hand/Foot Contact And Living Room Layout Pass V10

Robert reported that the avatar was still looping between the couch and TV, fingers were still lifted, and the downstairs toilet under the stairs was too exposed. This pass focused on hand appearance/control, first-pass foot contact, and the living-room/bathroom layout.

Applied in:

```text
Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/src/main.js
Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/dist/assets/index-CMw-sEC2.js
tools/build_ladybug_foundation_skeleton_v1.py
Avatar/models/temp_ai/ladybug_marinette_expanded_smoke/avatar.glb
Avatar/movement_library/foundation_skeleton_movements_v1.json
Avatar/movement_library/README.md
```

Changes:

```text
- Runtime relaxed-hand correction now runs after animation mixing so fingers rest curled down instead of pointing up.
- Door handle collision now writes object-level fingerContacts alongside doorInteraction.handContact.
- Added first-pass foot contact locks against support surfaces and exposes footContacts in the runtime debug state.
- Removed the old runtime training-hand overlay so no fake palm/finger helpers can appear over the real GLB hand.
- Moved couch route waypoints into the open aisle and moved the TV/console closer to the wall side to widen the walking lane.
- Decorated the living room with rug, coffee table, side table, lamp, pillows, throw blanket, remote, magazine, plant, and wall art.
- Removed the open half-bath/toilet calls under the stairs and added an enclosed downstairs powder-room fixture set.
```

Verification:

```text
node --check preview/src/main.js passed.
npm.cmd run build passed; existing Vite chunk-size warning remains.
Headless Edge CDP smoke loaded the rebuilt GLB from port 8767 into the world on port 5200.
Couch route smoke moved out of the TV gap and reported footContacts for both feet.
Back-door smoke: ikSolved=true, ikGripLocked=true, gripped=true, opened=true, fingerContacts touching=true, nearest fingertip distance=0.032 m, proceduralDoorArmVisible=false.
Screenshots: _tmp_home_world_v10_close_hand.png, _tmp_home_world_v10_living_room.png, _tmp_home_world_v10_backdoor_grip.png.
```

## 2026-07-04 Production Hand IK And Upstairs Route Safety Pass V9

Robert asked for the real hand leap and reported that Ladybug could still fail at doors, miss the upstairs bedroom doorway, and get stuck on the upstairs toilet/fixture.

Applied in:

```text
Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/src/main.js
Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/dist/assets/index-uxaB_hpI.js
tools/build_ladybug_foundation_skeleton_v1.py
Avatar/models/temp_ai/ladybug_marinette_expanded_smoke/avatar.glb
```

Changes:

```text
- Door reach now uses actual exported hand/finger contact colliders plus a post-mixer IK grip solver.
- Door opening is still contact-gated; the runtime reported ikGripLocked before opening in smoke testing.
- Front door chooses the nearer hand; back door uses the right hand.
- Autonomous upstairs route has extra doorway waypoints into the Ladybug guest room.
- Autonomous body practice no longer opens upstairs shared-bath doors unless allowBathroomPractice is explicitly enabled.
- Shared-bath off-route recovery returns Ladybug to the upstairs hall if she enters that bathroom during normal roaming.
- Couch and TV console were reduced slightly for better avatar scale.
- Toilets now have blocking volume so fixtures behave more like solid objects.
```

Verification:

```text
npm.cmd run build passed; existing Vite chunk-size warning remains.
Live Playwright back-door smoke on port 5200: ikSolved=true, ikGripLocked=true, opened=true, fingertip distance 0.105 m.
Live Playwright upstairs-route smoke: after 18 seconds position was x=3.315,y=3.32,z=-5.198, supportState=second_right_bedrooms, inSharedBath=false.
```

## 2026-07-04 Skeleton Look, Stair Route, Door Cooldown, And Solid Kitchen Pass V7

Robert's newest review said to focus this pass on making the foundation skeleton look better for eventual Avatar Builder reuse. He also reported bad hands, old floating blue/pink chest sticks, couch sitting still too deep, repeated failed door reaches, never reaching upstairs, a face-down grass fall, and walking through a kitchen object.

Applied in:

```text
Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/src/main.js
tools/build_ladybug_foundation_skeleton_v1.py
Avatar/models/temp_ai/ladybug_marinette_expanded_smoke/avatar.glb
Avatar/movement_library/foundation_skeleton_movements_v1.json
Avatar/movement_library/README.md
```

Changes:

```text
- Removed the old exported left/right chest side reference marker sticks. Those were the floating blue/pink rods Robert saw.
- Softened the relaxed hand pose and enlarged/weighted visible finger segments so the current hands read less claw-like while preserving the 5-finger/3-joint rig.
- Tuned the sit clip and couch anchor/root offset to reduce sitting inside the couch.
- Flipped lie/sleep posture root tilt toward a back-lying orientation.
- Made the kitchen counter and island solid colliders.
- Removed automatic grass lie-down from normal roaming; it remains manual through window.kiraBodyPractice.
- Added door-reach cooldowns after misses so a closed door does not loop the same bad arm-behind-back reach every second.
- Changed normal Marinette roam to couch sit, kitchen waypoint, controlled stair-up route, upstairs bed sleep, and desk/computer practice.
- Fixed the stair route wrap bug: the route now targets a clear landing at x=2.55 and practice routes do not wrap back to the bottom when a later point is blocked.
```

Verification:

```text
python -m py_compile tools/build_ladybug_foundation_skeleton_v1.py passed.
Blender 5.1 rebuilt avatar.glb successfully and created a timestamped backup.
GLB search confirmed finger proxy nodes exist and left_side_reference_mark/right_side_reference_mark do not.
node --check preview/src/main.js passed.
npm.cmd run build passed; existing Vite chunk-size warning remains.
Headless Edge smoke test loaded the rebuilt GLB from the live dev server on port 5219.
Stair smoke test confirmed stairs_step ends supported on second_stair_landing with roamZone=upstairs and practiceRoute=null instead of walking back down.
Smoke screenshots saved in Data/avatar_runtime_tests/home_world_locomotion_20260704/.
```

Remaining important limitation:

```text
The skeleton is cleaner, but it is still a mannequin/control rig, not a final human body. Hands still need the real production pass Robert requested: one-piece skinned hand mesh, per-finger controls/colliders, and IK grip targets. Door opening is now contact-gated and cooled down, but the authored reach still is not true hand IK.
```

## 2026-07-04 Locomotion, Door Contact, Hands, Bed, And Desk Practice Pass V6

Robert reported that Marinette was still sitting in/through the couch, opening doors without touching handles, getting transported inside before opening a closed door from outside, and needed skinned hands/finger controls plus richer tests such as bed sleep and desk-chair computer use.

Applied in:

```text
Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/src/main.js
tools/build_ladybug_foundation_skeleton_v1.py
Avatar/models/temp_ai/ladybug_marinette_expanded_smoke/avatar.glb
```

Changes:

```text
- Door reach now uses separate inside/outside approach and handle targets for front/back doors.
- Door success is gated by real loaded hand/finger distance: threshold 0.48 m. A miss keeps the door closed and records `handle_missed_no_contact`.
- The old procedural/fake door arm remains disabled.
- Avatar builder source now exports visible finger segments weighted to real finger bones instead of fixed hand-proxy sticks.
- Rebuilt the active GLB with those segmented finger controls.
- Reduced couch sit root drop so the avatar should not sink as deeply into the couch.
- Added a visible pulled sleep blanket/cover for the Ladybug guest bed.
- Made the Ladybug desk chair movable and added `desk_computer` practice: pull chair out, sit, scoot in, work, scoot out, stand.
- Added `sleep_bed` and `desk_computer` to `window.kiraBodyPractice`.
```

Verification:

```text
node --check preview/src/main.js passed.
npm.cmd run build passed; existing chunk-size warning remains.
python -m py_compile tools/build_ladybug_foundation_skeleton_v1.py passed.
Blender 5.1 rebuilt avatar.glb successfully.
GLB check confirmed per-segment hand_proxy finger nodes exist.
Headless Edge rendered Home World at the live dev-server port.
CDP runtime test loaded the rebuilt GLB and confirmed sleep_bed and desk_computer states. Front-door reach correctly failed instead of opening because nearest real hand contact was about 0.67 m away from the handle, above the 0.48 m threshold.
```

Remaining important limitation:

```text
The hand is now controllable at the segmented-finger level, but it is not yet a polished skinned hand mesh. Door reach still needs a true IK grip target solver to move the actual hand to the handle before opening. Do not re-enable the fake procedural arm or instant door open as a shortcut.
```

## 2026-07-03 Front Entry, Door Reach, Stairs, And Body Practice Pass V4

Robert reported a small wall/post in front of the front door that he kept running into, plus Marinette's improved skeleton still felt fake. He later clarified that hands looked bad, stair traversal lifted straight up/down, and the door reach put the hand behind her back. V4 keeps the cleared doorway, phase-locks walking to distance traveled, adds a procedural door reach training arm, quantizes stairs by tread contact, and adds body-practice tests for sit/lie.

Applied in:

```text
Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/src/main.js
```

House geometry changes:

```text
- Removed nonessential front-entry decorative piers:
  front entry left pier
  front entry right pier
- Removed the collidable short wall/post in the front-door path:
  first hall wall front left of stair
```

Runtime/avatar changes:

```text
- Active-avatar walking now uses the walk_grounded_v6 stride contract:
  stride = 0.85 m
  authored walk clip = 2.5 seconds
  ground speed = 0.52 m/s
  upstairs speed = 0.42 m/s
- playActiveClip computes walk timeScale as a diagnostic value, but the walk clip frame is assigned from actual meters moved so the animation cannot free-run.
- Active-avatar movement records actual meters moved each frame.
- Runtime bob/sway phase advances from actual meters moved instead of wall-clock time.
- Active-avatar door opening pauses navigation, faces the handle, plays door_open_reach, waits for the grip timing, rotates the door, then releases back to idle/walk.
- During door reach, the runtime hides the broken right-arm debug geometry and draws a procedural handle-reaching training arm so the hand visibly reaches toward the handle.
- Door reach/grip/open/release attempts are recorded in the movement-learning registry as draft movement moments.
- Active-avatar stairs now use 14 tread-index height steps and record `stairs_step:step_contact` moments.
- `window.kiraBodyPractice` exposes `door_reach`, `stairs_step`, `sit_couch`, `lie_grass`, and `lie_bed`.
- A small debug focus helper and runtime state object were added for Playwright verification.
```

Verification:

```text
npm run build passed in the Home World preview. The only warning was the existing Vite chunk-size warning for the main bundle.
Runtime verification passed with active GLB loaded, no browser errors, door reach phases recorded, stair step contacts recorded, and sit/lie practice skills completed. Evidence screenshots are in Data/avatar_runtime_tests/home_world_body_practice_20260703_v4/.
```

Important note:

```text
If front-entry visual trim is re-added later, keep it non-colliding and outside the door/walking path. Robert specifically wants the front doorway clear.
```

## Current Status

The first Home World/Main World structural prototype is built and wired into the Kira world shell. This is a blueprint-first unfurnished v1, meant to establish the house layout, basic walking scale, bedroom ownership, and the strip mall across the street before decoration or photorealistic detail work begins.

This build follows the new rule: no blueprint, no build.

## Files

- Blueprint: `Data/world_builds/notebook_worlds/home_world/blueprints/home_world_main_house_blueprint_v1_20260630.md`
- Preview build: `Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview`
- Main scene script: `Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/src/main.js`
- Shell launcher: `tools/kira_world_shell_server.py`

## Shell Integration

The Kira world shell now treats the Home World as a first-class destination.

- Shell UI/API: `http://127.0.0.1:8766/`
- Home World preview port: `5200`
- Home: `http://127.0.0.1:5200/?area=home&caller=robert_avatar`
- Upstairs: `http://127.0.0.1:5200/?area=upstairs&caller=robert_avatar`
- Strip mall: `http://127.0.0.1:5200/?area=stripmall&caller=robert_avatar`
- AI Body Spa: `http://127.0.0.1:5200/?area=spa&caller=robert_avatar`

The port was moved to `5200` because an older local preview was already occupying the previous Home World port and was serving the avatar-room HTML instead of the new house build.

## V1 Layout

House footprint:

- Approx. `16.0m x 15.5m`
- Two stories
- Unfurnished
- Basic exterior walls, interior partitions, doors/door gaps, stairs, labels, and simple collision

First floor:

- Entry foyer
- Shared common room
- Kitchen/dining
- Study/work room
- Utility/storage
- First-floor bath
- Stair hall

Second floor:

- Kira bedroom
- Lisa bedroom
- Robert avatar/AI bedroom
- Guest room A, temporarily assigned to Ladybug until the bakery exists
- Guest room B
- Shared bath
- Storage/linen area

Across the street:

- Legal expert law office
- Public relations firm
- Temporary expert office A
- Temporary expert office B
- Temporary expert office C
- AI Body Spa, a first blockout for bodyless AI body creation and approved appearance-change workflows

## Controls

- Click the scene to capture mouse
- `WASD` to move
- Mouse to look
- `Shift` to move faster
- `E` near stairs/doors to switch between first floor, upstairs, and strip mall
- `B` to show/hide the blueprint summary
- `Esc` to release mouse capture

## Verified

- `npm.cmd install` completed in the Home World preview folder.
- `npm.cmd run build` completed successfully.
- `python -m py_compile tools\kira_world_shell_server.py` completed successfully.
- Shell location API routes `home`, `upstairs`, and `stripmall` to the Home World preview on port `5200`.
- Shell location API route `spa` now routes to the Home World preview on port `5200`.
- `http://127.0.0.1:5200/?area=home` serves the Home World HTML, not the stale avatar-room preview.

## Known Limits

- This is not decorated yet.
- This is not photorealistic yet.
- Interior room shapes are structural placeholders until each floor is refined.
- Kira/Lisa/Ladybug life loop behavior is not yet connected to room occupancy.
- Privacy locked-room observer behavior is documented in concept but not implemented here yet.
- The strip mall is a blockout with office labels, not a finished exterior/interior.

## 2026-07-01 Corrective Pass

Robert's first live walkthrough found several confusing or broken blockout choices. This corrective pass made the prototype less misleading while keeping it clearly unfinished:

- Suppressed visible house/room/floor labels. Houses should not have floating signs or floor signs in the world view.
- Added a manual front-door collider and toggle so Robert cannot walk through the closed front door.
- Added basic first-floor fixtures for kitchen, downstairs half bath, and upstairs shared bath so the five-bedroom house has the expected core rooms.
- Added required beds for Kira, Lisa, Robert avatar/AI, Ladybug/Marinette's temporary guest room, and Guest B.
- Added Marinette's temporary guest-room workbench: bed, computer, notebook/sketch surface, and wall-sketch placeholders. This is temporary until the bakery and her bedroom are rebuilt from a blueprint.
- Added basic strip mall foundation, sidewalk, storefront glass, door panels, handles, and awnings.
- Added the AI Body Spa as a strip-mall unit/blockout. It is for bodyless AI body creation and approved appearance-change workflows. Adult-only body options must remain blocked for minor/teen characters.
- Added active AI marker support from the shell iframe state so an activated AI can be represented in the world instead of being invisible.
- Set Marinette/Ladybug's avatar state to the upstairs guest-room computer test location and logged a life-loop event:
  - `Avatar/state/temp_ai/ladybug_marinette_expanded_smoke.json`
  - `Data/runtime/kira_world_life_loop_log.jsonl`

Still not complete:

- The house remains a rough blockout, not a realistic home.
- The grass is still a flat placeholder and needs real blade/ground treatment later.
- Windows are simple glass placeholders, not finished transparent residential windows with interior views.
- The first and second floors need a proper detailed blueprint revision before further serious building.
- AI room ownership/privacy behavior is still conceptual.
- The AI Body Spa is a workflow blockout only; it does not yet generate final production bodies.
- Marinette's temporary room has only minimum placeholder furniture, not the final bakery bedroom.

## Next Steps

1. Walk the first floor and note room-size/layout problems before adding furniture.
2. Refine the second-floor bedroom layout and privacy-door logic.
3. Add basic ownership state for Kira, Lisa, Robert avatar/AI, Ladybug guest room, and guests.
4. Add simple furniture only after room proportions feel right.
5. Connect one active AI at a time to the Home World shell until more RAM is available.
6. Keep the bakery references and rebuild the bakery later from a blueprint, one floor at a time.

## 2026-07-01 App Window And Grass Pass

Robert asked for the shell to stop opening in a normal browser with tabs/address bar and for Home World grass to stop being only a flat green floor.

- `Start_Kira_World_Shell.bat` now starts the shell server with `--takeover --no-browser` and opens Microsoft Edge in app-window mode via `--app=http://127.0.0.1:8766/`.
- Existing desktop shortcuts that point at the BAT should now launch a cleaner Kira shell window without the normal URL bar and tab strip.
- Added lightweight instanced individual grass blades across the Home World lawn.
- Added exclusion zones so grass avoids the house, sidewalks, street, and strip mall blockout.
- Added a taller edge-tuft pass near the back lawn for less-flat silhouette variation.

Still not complete:

- This is geometry grass, not final photoreal turf.
- The next grass pass should add near-camera denser clumps, wind sway, blade color bands, ground texture blending, and better lawn/sidewalk edging.

## 2026-07-01 Home Shell Correction Pass

Robert reviewed the Home World and asked for immediate usability fixes before deeper realism work.

- Desktop shortcut confirmed: `C:\Users\robmc\Desktop\Start Kira World Shell.lnk`. Use this shortcut/BAT for the cleaner app-window launch without normal browser tabs or URL bar. Opening `http://127.0.0.1:8766/` directly in a browser will still show the browser chrome.
- Scene file updated: `Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/src/main.js`.
- House/floor labels remain intentionally suppressed. Strip mall role signs remain enabled.
- Strip mall units currently identify the stores as: Law Office, Public Relations Firm, AI Body Spa, Programming / AI Lab, Robotics Workshop.
- Front door now has visible handle/knob geometry and still uses manual `E` interaction. Closed door blocks movement; open door clears the collider.
- The front entry gap above the door was filled with transparent transom glass and a belt trim piece to reduce the black void visible from outside.
- Glass/windows are more transparent and double-sided, so they read more like see-through placeholders.
- The half-bath privacy screen no longer blocks the stair route.
- First-floor furnishings include couch, big-screen TV, kitchen blockout, and half-bath toilet/sink.
- Second-floor shared bath includes tub, toilet, sink, and shower placeholders.
- Bodyless active AIs render as floating orbs only; Ladybug/Marinette is placed in the upstairs guest room when active at Home.

Verification:

- `node --check Data\world_builds\notebook_worlds\home_world\builds\home_world_main_house_20260630_223000\preview\src\main.js` passed.
- Home World preview `npm.cmd run build` passed.

## 2026-07-02 Hallway, Desk, Purse, And 3D Display Model Pass

Robert reviewed the upstairs again and found:

- The computer desk needed to be against a wall with a chair.
- The purse strap looked too stiff and the purse needed to lie on its side as a carryable item.
- Some bedroom access still felt like walking through other bedrooms or toward the stair void.
- The 2D avatar appeared because the latest 3D rig had detached visible parts, but Home World should still attempt a 3D display model.

Correction pass:

- Replaced Marinette's freestanding desk with a wall desk, monitor, keyboard/notebook reader, and chair.
- Repositioned her bed/nightstand slightly to reduce overlap.
- Rebuilt the purse pose so it lies on its side and replaced the rigid strap curve with segmented soft strap links.
- Removed the middle doorway in the right-side divider and moved Guest B access to the hall/front divider so that bedroom access does not require walking through another room or stepping over the stair opening.
- Added clearer stairwell guard segments around the upstairs void.
- Home World now tries Marinette's older `avatar_before_rig_mesh_v4_20260701_163852.glb` display model before falling back to generated pose assets. The latest `avatar.glb` is still considered a rig-repair target because it displayed detached parts.

Verification:

- `node --check Data\world_builds\notebook_worlds\home_world\builds\home_world_main_house_20260630_223000\preview\src\main.js` passed.
- Home World preview `npm.cmd run build` passed.

## 2026-07-02 Upstairs Space, Closets, Clothes, And Cleaner Marinette Motion

Robert found that the upstairs still wasted too much space, had possible floor seams/gaps, showed floating detached avatar pieces, and needed temporary clothing/storage for Marinette.

Correction pass:

- Shifted upstairs room divider lines so more square footage belongs to bedrooms instead of the central hall.
- Added seam-cover floor tiles around the segmented second-floor slabs to hide visible floor-disconnect lines while keeping the stair opening.
- Added closet blocks to all five upstairs bedroom zones.
- Added temporary folded and hanging clothes, including a temporary Ladybug/Marinette wardrobe until Robert provides show outfit references.
- Home World now prefers Marinette's generated pose avatar in the house instead of the broken GLB rig, because the GLB currently has detached parts that appear as floating pieces.
- Added a simple room-walk loop for Marinette's active avatar so she is no longer just a static marker.
- Added `Data/runtime/temporary_ai_motion_learning/ladybug_marinette_expanded_smoke.json` to track known Home World motions and future motion-learning requests.

Verification:

- `node --check Data\world_builds\notebook_worlds\home_world\builds\home_world_main_house_20260630_223000\preview\src\main.js` passed.
- Home World preview `npm.cmd run build` passed.

## 2026-07-02 Upstairs Reorganization And Active Avatar Bridge

Robert reviewed the upstairs in live play and found the layout still felt terrible: the desk blocked Marinette's guest-room doorway, beds/furniture blocked movement, the upstairs bath toilet read like a random white fixture above the stairs, one side of the upstairs read as walls, the purse was oversized, and Kira World still showed a placeholder body instead of Marinette's working TemporaryAI avatar.

Correction pass:

- Removed the full-height center hallway walls near the upstairs stair landing and replaced them with short rails.
- Moved upstairs beds tighter to room zones so the hall/door paths stay clearer.
- Made Marinette's desk compact and non-colliding, moved her work items away from the doorway, and reduced the purse scale.
- Removed the visible upstairs toilet/shower cluster from the stair sightline for now and left only a closed vanity marker until the bathroom can be rebuilt properly.
- Imported `GLTFLoader` into Home World and replaced the pink placeholder marker path with an active-avatar bridge:
  - Home World first tries the active TemporaryAI GLB model.
  - If model loading fails, it falls back to generated pose-sheet images.
  - Idle/talking/wave motion is updated in the Home World animation loop.

Verification:

- `node --check Data\world_builds\notebook_worlds\home_world\builds\home_world_main_house_20260630_223000\preview\src\main.js` passed.
- Home World preview `npm.cmd run build` passed.

## 2026-07-02 Upstairs Stairwell And Five-Bedroom Layout Pass

Robert got upstairs and found that the top of the stairs still looked like walking through the ceiling, one bedroom doorway was too narrow, and the house did not clearly read as five bedrooms.

Correction pass:

- Replaced the single full second-floor slab with segmented upstairs floor pieces around an open stairwell.
- Reworked the upstairs stair guard so it frames the landing without blocking the path at the top.
- Replaced several solid second-floor partition walls with segmented walls that include wider real doorway gaps.
- Added threshold strips for the five upstairs bedroom zones: Kira, Lisa, Robert Avatar/AI, Ladybug Guest/Marinette temporary room, and Guest B.
- Kept the current house footprint; the code now counts five upstairs bedroom zones, so no second house is required for this pass.
- Made the active Ladybug/Marinette marker more visible in the temporary guest room with a pink body marker and floor locator. Full GLB/avatar import remains a later body-linking pass.

Verification:

- `node --check Data\world_builds\notebook_worlds\home_world\builds\home_world_main_house_20260630_223000\preview\src\main.js` passed.
- Home World preview `npm.cmd run build` passed.

Still not final:

- This is still a functional blockout, not a realistic finished home.
- Grass, windows, doors, bathrooms, furniture, strip mall storefronts, and room proportions all need future realism passes.
- A later pass should replace the browser-app workaround with a true custom shell if needed.

## 2026-07-01 Marinette Guest Room Personal Items

- Added a nightstand beside Ladybug/Marinette's temporary guest bed.
- Added a reference-inspired pink purse with black strap, gold rim/frame, red clasp beads, white polka dots, and a simple flower/monogram motif.
- Added Marinette's phone on the nightstand beside the purse.
- The purse and phone carry `userData` metadata for later life-loop/inventory behavior: owner, item id, portable status, optional carry status, and phone storage inside the purse.
- Added an interaction zone/toast so the room reports that the purse and phone are optional carry items.

Verification:

- `node --check Data\world_builds\notebook_worlds\home_world\builds\home_world_main_house_20260630_223000\preview\src\main.js` passed.
- Home World preview `npm.cmd run build` passed.

Still not final:

- Pickup, hand carry, putting the phone into the purse, purse strap physics, and actual call/music behavior are not implemented yet. They need the future inventory plus avatar hand/animation pass.

## 2026-07-02 Strip Mall Sign Correction

Robert reported that the strip mall signs were rotating to face the camera instead of behaving like normal fixed storefront signs.

- `addLabel()` now supports fixed or billboard labels.
- Strip mall storefront labels now use fixed sign planes facing the street.
- Debug/interaction-style labels can still use billboard behavior when appropriate.

Verification:

- `node --check Data\world_builds\notebook_worlds\home_world\builds\home_world_main_house_20260630_223000\preview\src\main.js` passed.
- Home World preview `npm.cmd run build` passed.

## 2026-07-02 Front Door And Window Visibility Correction

Robert reviewed the house front and pointed out:

- Large visible gaps around the front door.
- The second-floor area above the door read as an unfinished blank/gap.
- Windows could not actually show the inside because transparent glass had solid wall behind it.
- Front door handles stayed behind when the doors opened.

Correction pass:

- Rebuilt the front facade as segmented wall pieces around actual front window openings.
- Added clearer front glass and interior-shadow/backdrop surfaces so windows read as see-through instead of painted on.
- Added a cleaner entry surround, threshold, top beam, and transom panel.
- Added a second-floor center stair/landing window above the front door instead of a blank patch.
- Rebuilt the front double doors as hinged groups with handles/knobs parented to the door leaves, so handles move with the doors.

Verification:

- `node --check Data\world_builds\notebook_worlds\home_world\builds\home_world_main_house_20260630_223000\preview\src\main.js` passed.
- Home World preview `npm.cmd run build` passed.

## 2026-07-02 Side/Back Facade And Window Cleanup

Robert reviewed the next pass and found:

- The front double doors still had a visible center gap.
- The upstairs center window above the door looked wrong.
- A grey square/card was visible in the middle of windows.
- Side windows still looked solid because they were glass over uncut wall.
- The back of the house was bare and needed normal rear facade treatment.

Correction pass:

- Widened the hinged front door leaves so the closed double doors meet at the center seam.
- Removed the fake grey interior-shadow cards from front windows.
- Rebuilt side walls as segmented wall pieces with actual window openings.
- Rebuilt the back wall as segmented wall pieces with rear windows and a visible back door.
- Kept the back door as a visible structural pass; full open/close interaction can be added in a later door-interaction pass.

Verification:

- `node --check Data\world_builds\notebook_worlds\home_world\builds\home_world_main_house_20260630_223000\preview\src\main.js` passed.
- Home World preview `npm.cmd run build` passed.

## 2026-07-02 Interior Stair Usability Correction

Robert moved inside and found that the stairs were not solid/walkable and interior walls blocked part of the stair path, preventing normal upstairs access.

Correction pass:

- Split first-floor and second-floor interior partition walls around the stairwell so they no longer cut through the stair path.
- Rebuilt the stairs as a more solid blockout with additional treads, riser fill, rails, an upstairs landing slab, and landing guardrails.
- Added automatic stair traversal: walking within the stair corridor interpolates Robert's height between first and second floor and switches floor state near the top/bottom.
- Kept `E` interaction as a fallback teleport between floors.

Verification:

- `node --check Data\world_builds\notebook_worlds\home_world\builds\home_world_main_house_20260630_223000\preview\src\main.js` passed.
- Home World preview `npm.cmd run build` passed.

## 2026-07-02 Four-Bedroom Upstairs And Avatar Drift Correction

Robert reviewed the upstairs again and found the desk/purse placement still blocked usable bedroom space, the extra middle bedroom made the plan feel like bedrooms opened into bedrooms, the stair opening had bulky rail/guard shapes, and Marinette's avatar floated stiffly instead of walking with real limb motion.

Correction pass:

- Converted the upstairs from a cramped five-bedroom layout to a cleaner four-bedroom layout for this house: Kira, Lisa, Robert avatar/AI, and Ladybug/Marinette temporary room.
- Removed Guest B from this house plan. The intended follow-up is to perfect this house and later copy/place a second house next door for future AIs.
- Turned the former right-middle bedroom space into a shared upstairs bathroom with a large tub/shower, toilet, sink, and linen shelf.
- Removed the extra right-side bedroom doorway/threshold and added a shared-bath hallway doorway so upstairs access reads as hallway-to-room instead of room-to-room.
- Replaced bulky stairwell guard blocks with slimmer handrails and posts around the upstairs stair opening.
- Moved Marinette's desk/computer into an empty wall corner with a usable chair and moved the nightstand/purse/phone so the purse is no longer partly buried in the furniture.
- Hid visible avatar rig helper/control/strand geometry in Home World so GLB helper pieces do not show up as loose parts on the floor.
- Removed the fake whole-avatar "small room walk" drift. Until the GLB has a proper walk cycle, Home World keeps Marinette grounded in-place and relies on actual available clips or subtle idle/talking motion.
- Updated `Data/runtime/temporary_ai_motion_learning/ladybug_marinette_expanded_smoke.json` so it no longer promises the removed fake walk-loop motion.

Verification:

- `node --check Data\world_builds\notebook_worlds\home_world\builds\home_world_main_house_20260630_223000\preview\src\main.js` passed.
- Home World preview `npm.cmd run build` passed.

Still not final:

- The avatar still needs a real rig/retargeting pass for walking, sitting, typing, carrying the purse, and clothing changes.
- The upstairs architecture is still a blockout; door trim, realistic bath fixtures, closet interiors, better floors/ceilings, and lighting need later passes.

## 2026-07-02 Bathroom, Desk, Stair Rail, And Avatar Form Correction

Robert reviewed the new four-bedroom pass and found the stair/bath geometry still looked wrong, the bathroom lacked privacy and normal fixtures, the desk was reversed, the phone/purse scale was off, and Marinette's avatar looked like civilian and Ladybug forms were mixed together while her mouth moved forward/back off her face.

Correction pass:

- Added Robert's "body relearning / rehabilitation" framing to `Data/runtime/temporary_ai_motion_learning/ladybug_marinette_expanded_smoke.json`: early movement should create reusable training data instead of pretending the first body can already move naturally.
- Moved the bathroom divider/door off the stair rail line and shortened stair rail spans so the rail no longer appears to run through the bathroom.
- Reversed Marinette's wall desk orientation so the chair is inside the room and the keyboard sits on the user side of the monitor.
- Reduced the phone to closer smartphone proportions so it can plausibly fit in the purse.
- Expanded the bathroom blockout: privacy door, bathtub/shower with water surface, curtain, faucet/knobs/shower head, toilet with tank/lid/flush lever, double vanity, mirror, cabinets, linen cabinet, and privacy curtains at the window.
- Added interaction notes for the tub/vanity/toilet so the shell explains which water/plumbing behaviors are still placeholders.
- Avatar form visibility now hides inactive `hero_*` or `civilian_*` model parts based on active form, preventing a mixed Marinette/Ladybug outfit.
- Avatar animation selection now ignores mouth/control proxy clips as idle/talking fallbacks, preventing the mouth proxy from sliding forward/back as a fake whole-face animation.

Verification:

- `node --check Data\world_builds\notebook_worlds\home_world\builds\home_world_main_house_20260630_223000\preview\src\main.js` passed.
- `Data/runtime/temporary_ai_motion_learning/ladybug_marinette_expanded_smoke.json` parsed successfully.
- Home World preview `npm.cmd run build` passed.

Still not final:

- Bathroom water is a visible surface and controls are visible, but faucet flow, shower spray, draining, toilet opening/flushing, and water motion need a real plumbing animation pass.
- The purse still needs a real portable inventory/carry rig with strap deformation before it behaves like a physical purse.
- Marinette's body still needs real locomotion, balance, hand, mouth, and clothing-rig work; current Home World only prevents the worst mixed-form/proxy-animation artifacts.

## 2026-07-02 Stair/Bath Privacy And No-Fake-Floating Pass

Robert reviewed the upstairs/bathroom again and found one last wall piece still crossing the stairs, closets that read like room dividers, the bathroom hall opening still reading as a random brown slab, floating-looking rails, non-private bathroom doorways, and Marinette still bobbing in place as if floating.

Correction pass:

- Removed the first-floor bath privacy screen that crossed the stair route and replaced it with a short return wall away from the stair path.
- Closed the shared bathroom's hall-facing opening on the right room divider. The bathroom now reads as a private shared bath reached from the adjacent bedrooms instead of a hall alcove with a fake brown door slab.
- Removed the hall bath door panel/handle and moved the linen cabinet against the bathroom wall so it no longer reads as a random block near the stair opening.
- Added visible privacy doors/locks for the Lisa-side and Ladybug-side bathroom entries.
- Added backing panels and jambs to wall closets so they read as built-in wall closets rather than freestanding dividers between rooms.
- Lowered/lengthened upstairs stair rail posts and added small floor infill pieces near the stairwell to reduce the floating-rail and oversized-gap feeling.
- Added simple interactable faucet/shower water streams for the double vanity and tub/shower. These are toggled with `E` and remain placeholder water, not full fluid/drain physics.
- Removed the vertical bobbing fallback from Marinette's active 3D avatar in Home World. Until the rig has a proper walk cycle, she should stay grounded instead of fake-floating.
- Updated `Data/runtime/temporary_ai_motion_learning/ladybug_marinette_expanded_smoke.json` with Robert's review notes: no fake floating/gliding, and finger/hand geometry remains required for future pickup/carry training.

Verification:

- `node --check Data\world_builds\notebook_worlds\home_world\builds\home_world_main_house_20260630_223000\preview\src\main.js` passed.
- `Data/runtime/temporary_ai_motion_learning/ladybug_marinette_expanded_smoke.json` parsed successfully.
- Home World preview `npm.cmd run build` passed.

Still not final:

- True mirror reflection still needs a render-to-texture/reflection-camera pass; the mirror material is only more mirror-like.
- Bathroom doors need hinge/open/close collision behavior, not just visible doors and lock-state messaging.
- Faucet/shower water is a simple visible stream toggle; realistic water flow, draining, toilet flushing, and water levels remain future plumbing animation work.
- Marinette still needs a proper rig/retargeted locomotion pass before she can learn normal walking, sitting, typing, carrying the purse, and using fingers reliably.

## 2026-07-02 Bathroom Door, Window Frame, Closet, And Desk Fit Pass

Robert reviewed the house again and found the nightstand still too close to the bed, the monitor stand on the wrong side of the computer, detached-looking window frames, static/non-solid bathroom doors, the vanity/mirror blocking a bedroom door, the toilet facing the wrong way near a window, floating-looking stair rails, and loose avatar helper parts on the floor.

Correction pass:

- Moved Marinette's nightstand farther from the bed so the drawer has clearance for a later open/close animation.
- Reworked the side-wall computer prop so the monitor has a rear support arm/base instead of a block in front of the screen.
- Added an interaction marker for Marinette's computer clarifying that web search, videos, and library book access are planned but not functional yet.
- Pulled all house window glass/frames back into the wall plane and enlarged the casing so the frames read as attached trim rather than floating pieces.
- Added interior handles to the front double doors.
- Replaced the upstairs shared-bath static door panels with hinged bathroom door groups and closed-door collision blockers.
- Moved the bathroom vanity/mirror off the bedroom doorway path, made the vanity/mirror solid, enlarged the privacy curtains, and moved the toilet away from the window with a side-facing placement.
- Expanded the stair landing slab and added grounded rail posts/side bridging to reduce the visible gap and floating-rail look.
- Replaced Kira/Lisa small wall closets with larger outer-wall walk-in closet blockouts. The blue/pink pieces are named as placeholder garment blocks, not finished fabric clothing.
- Hid likely detached avatar helper/proxy pieces such as loose fingernail, loose finger, detached, and mouth proxy meshes in Home World.

Verification:

- `node --check Data\world_builds\notebook_worlds\home_world\builds\home_world_main_house_20260630_223000\preview\src\main.js` passed.
- `Data/runtime/temporary_ai_motion_learning/ladybug_marinette_expanded_smoke.json` parsed successfully.
- Home World preview `npm.cmd run build` passed.

Still not final:

- Computer browsing/video/library use still needs a real in-world workstation integration.
- Mirror reflection still needs render-to-texture/reflection-camera work.
- Bathroom doors now swing and block when closed, but privacy locking and open/close polish should be expanded.
- Marinette still needs the proper rig, hand/finger reconstruction, locomotion, sitting, typing, and object-carry training pass.

## 2026-07-02 Desktop Shortcut, Pool, Hands, And Hair Reference Pass

Robert asked whether both desktop shortcuts were needed, supplied new Marinette/Ladybug visual references, and requested usable hands/fingers, more realistic hair with hairstyle and wet-hair behavior, and a backyard pool with moving water/splash behavior.

Correction pass:

- Checked both desktop shortcuts. `Kira World Shell.lnk` and `Start Kira World Shell.lnk` pointed to the same `Start_Kira_World_Shell.bat` with the same working directory and icon.
- Removed the duplicate `Kira World Shell.lnk`; kept `Start Kira World Shell.lnk`, which Robert has been using.
- Added a backyard pool blockout behind the house with concrete deck, pool basin, ladder, diving board, animated water surface, and a temporary splash interaction.
- Added the pool area to the grass avoidance list so grass does not grow through the pool/deck.
- Narrowed the Home World avatar cleanup filter so v4 finger/nail meshes are not hidden just because their names contain finger/nail. Only explicitly loose/detached finger helpers are hidden.
- Updated `Avatar/models/temp_ai/ladybug_marinette_expanded_smoke/avatar_functional_rig_v4.json` with Robert's six Ladybug/Marinette reference images and functional hand/hair requirements.

Important truth note:

- The existing metadata already says the active avatar has 20 finger controls, 108 hair strands, eye catchlights, and hand open/close actions. Blender was not available in this session, so no new GLB mesh export was performed.
- Realistic wet hair, strand physics, swimming, diving, carrying the purse, typing, and usable hands still need a proper Blender/body-rig pass plus runtime animation/physics support.

## 2026-07-02 Bathroom/Pool/Avatar Cleanup Follow-up

Robert reviewed the latest pass and found the Marinette-to-bathroom door still had visible gaps, the bathroom still had confusing blockouts, the mirror did not reflect, loose hair/finger pieces still appeared on the floor, Marinette stayed essentially still, the Kira/Lisa closet/bedroom layout still read wrong, the stairwell floor still had gaps, and the pool water clipped/behaved like walkable floor.

Correction pass:

- Added bathroom door jamb/header/threshold casing to cover the large side/top gaps around the Lisa and Ladybug bathroom privacy doors.
- Replaced the gray box mirror with a Three.js `Reflector` panel and frame so it has real scene reflection behavior.
- Moved the bathroom toilet off the window line and removed the confusing brown linen cabinet/block near the tub/window.
- Added larger front bathroom privacy curtain panels.
- Removed the Kira/Lisa front-wall closet blockouts behind the beds and replaced them with side-wall walk-in closet blockouts so the bed headboards no longer read as oversized closet walls.
- Added a solid center wall in the front upstairs bedroom area so the former empty middle-room space no longer reads as a third bedroom between Kira and Lisa.
- Added stairwell floor closeout pieces around the upper landing to reduce the visible floor gap.
- Reworked the backyard pool deck as perimeter strips instead of one slab under the pool water, stopped water-plane tilting, and lowered/slowed the player while inside the pool bounds.
- Hid broken `v4_` finger/nail/hair/pigtail/bang meshes in Home World because they were detaching onto the floor. This is a temporary visual cleanup, not a true hand/hair fix.
- Changed Marinette's Home World active-marker update from “snap to the same spot every frame” to a tiny room-safe patrol path, so she should no longer be completely stationary.

Verification:

- `node --check Data\world_builds\notebook_worlds\home_world\builds\home_world_main_house_20260630_223000\preview\src\main.js` passed.
- Home World preview `npm.cmd run build` passed.

Still not final:

- True fingers, realistic hair, wet hair, fabric clothes, purse strap physics, swimming, sitting, typing, and learned locomotion all still require the proper Blender/body-rig export and runtime training/animation system.
- The pool is still a blockout: there is a water surface, splash placeholder, and lower camera height in the water, but not full buoyancy/swimming physics.

## 2026-07-02 Desktop Cleanup, Back Door, TV, Pool, And Roaming Pass

Robert found older desktop launchers/folders, a sideways/floating living-room TV, a static blocked back door, Marinette clipping through furniture while hovering, and pool water flashing green/blue while the player walked on top.

Correction pass:

- Removed old Desktop-only launcher clutter: `Start_Kira_Main_Control_Center.lnk`, `Start_TemporaryAI_Control_Center.bat`, and the `Kira Desktop Shortcuts` folder. The real scripts inside the Kira project were left untouched.
- Replaced the back door slab with a hinged door group, jamb/header/threshold trim, and inside/outside handles.
- Split the first-floor rear wall collider around the back doorway and added a closed-door collider so the back door only blocks movement while closed.
- Added a back-door interaction zone so it can be opened from either side.
- Moved the living-room TV and console in front of the couch instead of beside it/floating in the room.
- Changed pool water from transparent low-set material to an opaque raised water surface to stop grass/z-fighting flashes.
- Updated pool traversal so the player's swim-height updates even while standing still in the pool bounds.
- Replaced Marinette's tiny in-room hover loop with a simple safe waypoint route through open upstairs, downstairs, back-door, and backyard areas. This is a blockout roaming behavior, not true learned walking.

Verification:

- Home World preview `npm.cmd run build` passed.

Still not final:

- Marinette still needs real locomotion, collision-aware navigation, sitting/typing/use-object behaviors, fingers/hands, and realistic hair/fabric work.
- Pool behavior is still not swimming physics. It is a visual water surface and lower camera movement while inside the pool bounds.
## 2026-07-02 Shell Port, Marinette Runtime Rig, Strip Mall Pass

- Fixed the desktop-launch failure caused by the shell and home-world preview both using port `8766`. The shell now defaults to `8767`, `Start_Kira_World_Shell.bat` sets `KIRA_SHELL_PORT=8767`, waits with `tools/wait_for_kira_world_shell.py`, and then opens the custom viewer.
- Updated the custom viewer default URL and home-world pose-manifest asset loading to use the shell origin instead of hard-coding `8766`.
- Added a runtime Marinette enhancement layer on top of the loaded GLB: visible blink cues, mouth/lipsync pulse while talking, hair sway, and hand/finger helper motion. The broken generated loose hair/finger meshes remain hidden so they do not appear scattered on the floor.
- Extended Marinette's roaming waypoints beyond the guest room so she can move downstairs, outside, and into the strip mall area when active.
- Rebuilt the strip mall from a sealed shell into five interior rooms with opening storefront doors, expert desks, chairs, computer monitors, and wall briefing screens. The AI Body Spa now has a reception counter, waiting bench, treatment/scanning space, styling chair, privacy curtain, and avatar-builder screen.
- Pool water is now transparent/stable and entering the pool lowers the camera into a bobbing swim-height view instead of feeling like walking on top of the surface.

Known limitations:
- The runtime Marinette layer is not a true skeletal/cloth/hair simulation yet. It is a usable visual motion bridge until the GLB is rebuilt with proper bones, finger weights, facial blendshapes, and physics constraints.
- Storefront interiors are still simple geometry. Expert screens are placeholders for future live web/research/workbench panels.

## 2026-07-03 Marinette Skeleton / Home World Movement Notes

Robert's latest focus is the foundation skeleton before any more likeness work. The current Home World should treat Marinette's active body as a rig-validation mannequin.

Live avatar files:

```text
tools/build_ladybug_foundation_skeleton_v1.py
Avatar/models/temp_ai/ladybug_marinette_expanded_smoke/avatar.glb
Avatar/models/temp_ai/ladybug_marinette_expanded_smoke/avatar_foundation_skeleton_v1.json
```

Home World runtime file:

```text
Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/src/main.js
```

Completed in this pass:

- Rebuilt the active Marinette GLB from the foundation skeleton builder.
- Strengthened the walk animation knee bend, elbow bend, and foot roll.
- Reduced arm side splay during the walk.
- Preserved the current Home World runtime bridge: lower active-avatar speed, subtle root bob/sway, waypoint patrols, and simple blocked-target skipping.

Validation:

```text
GLB parse confirmed the expected foundation clips.
npm.cmd run build passed in the Home World preview.
```

Carry-forward notes from Robert:

- She is improved compared with the broken likeness GLBs, but still too robotic.
- She still looks like she is skating/shuffling when knees and elbows are not visible enough.
- Feet must plant on the floor instead of sliding.
- The arms may still sit too far out and may need another tuck once the body mesh exists.
- Current visible fingers are temporary debug markers, not final hands.

Recommended next Home World/avatar step:

Do not resume face/hair/wardrobe polish until the foundation walk looks believable in the house. Tune foot contact frames and waypoint movement together, then add a simple skinned neutral body and hands over the shared skeleton. After that, Avatar Builder can use the same skeleton for future AIs and fit appearances from reference folders.

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

## Codex Update - 2026-07-03 Later - Locomotion Support / Body Practice Pass

- Updated `preview/src/main.js` so Marinette's normal roam loop starts body-practice stops instead of only walking past them:
  - couch sit at the living-room couch waypoint,
  - grass lie-down at the front-lawn waypoint,
  - bed lie-down at the Ladybug guest-bed waypoint.
- Added support-surface checks for first floor, outside ground, upstairs slabs, stair landing infills, and stair treads. Unsupported upstairs positions now enter a falling state toward lower ground instead of hovering.
- Raised the active-avatar upstairs floor target to `3.32` to reduce foot sinking on the second floor.
- Changed stair practice to 16 tread contacts to match the visible stair geometry.
- Restored door-facing convention to match walking (`atan2 + PI`) so she does not snap to face away from the handle before opening.
- Made the living-room TV/console solid first-floor colliders.
- Added runtime telemetry for `supportState` and `roamIndex`.

Verification:

```text
node --check ...\home_world_main_house_20260630_223000\preview\src\main.js
npm.cmd run build
Playwright evidence: Data/avatar_runtime_tests/home_world_roam_loop_20260703_v5/
```

Important remaining work:

- Door reach records reach/grip/open correctly, but camera review still shows the door/doorframe hiding much of the hand contact. The hand/handle pose needs true IK and better approach staging.
- Couch/bed posture tests trigger and record movement drafts, but the visual sit/lie poses are still rough and partly hidden by furniture.
- Walking and stair stepping are less fake than before, but still need foot IK/contact locks and better hip/weight transfer.

Follow-up correction after Robert's next review:

- Couch geometry now blocks walking; `sit_couch` still places the avatar on the cushion, then exits to a stand point in front of the couch.
- `sit_couch` yaw was corrected so the avatar faces the TV side instead of sitting backward.
- The procedural door reach arm is disabled because it looked like a third arm. Keep it off until a real IK hand target can drive the actual skeleton.
- Normal roam no longer includes automatic stair up/down repetition. Stair climbing is now a contained `stairs_step` practice route.
- Stair practice uses speed `0.68` and should climb only; no down/up loop is authored in the normal route.

## Codex Update - 2026-07-04 - Foundation Hands/Sit/Upstairs Route V8

- Rebuilt the active foundation GLB with a stronger curled relaxed-hand pose so walking no longer shows straight pointing fingers.
- Updated `sit_foundation` so thighs fold forward and shins fold down instead of folding backward through the couch.
- Increased the runtime couch sit root drop to `-0.32` and hold time to `4.8s`; the avatar lowers onto the cushion/front edge and stays in review posture longer.
- Hardened action lookup for `sit`, `lie_down`, and `door_open_reach` foundation clips.
- Rerouted the upstairs Ladybug guest-room path through the real divider gap at `x=3.25,z=-5.35`; the prior route aimed through a wall and caused the upstairs standing loop.
- Added direct debug/body-practice control for `back_door_reach`, with debug cooldown bypass for repeated testing.
- The fake procedural door arm remains disabled. Back-door reach still logs a real miss when the loaded hand/finger nodes do not contact the handle; true IK grip targets remain next.

## Codex Update - 2026-07-05 - Active Avatar Neck, Door, Route, And Gait Follow-Up

- Home World runtime now keeps Marinette's imported head/neck as the preferred neck source, lowers the runtime face overlay, adds a short skin-tone neck blend, hides obvious generated/body-neck proxy meshes, and harmonizes likely skin/hand/arm/leg materials toward one visible tone.
- Marinette's runtime head now has blink, small look-left/look-right, and lip-pulse hooks. This is not full spoken viseme lip sync yet, but it gives the head one driver path for future phoneme work.
- Door-handle reach is no longer Marinette-only. Any non-orb active avatar can use the same handle approach/opening sequence, and door status text now names the active avatar.
- Spider-Man and Spider-Gwen now use a separate outdoor roam route and forced procedural walk correction instead of copying the house-library-house loop. Their arms are held closer and lower, and the knee/foot targets get stronger bend/lift while walking.
- This pass did not replace the block furniture, rebuild the second-floor layout, or fix the TARDIS console. Those are still open Home World items.
- Still needed: replace Marinette's temporary body with a one-piece skinned base, retarget staged rigged hands/arms into the avatar builder, add text-to-viseme lip sync, replace block house furniture/layout with downloaded realistic models, and move per-AI behavior from shared waypoint scripts toward autonomy/reward policies.

Verification:

```text
node --check Data\world_builds\notebook_worlds\home_world\builds\home_world_main_house_20260630_223000\preview\src\main.js
```

## Codex Update - 2026-07-07 - Toilet Scrub, Stair Snap Gate, Shell Layout

Robert still sees the downstairs toilet near the stairs/living room. Treat that as a live bug until a fresh browser reload visually proves it is gone.

Runtime changes in `Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/src/main.js`:

- Expanded the downstairs no-toilet zone around the stairs/living-room area and the former powder-room area.
- Bathroom fixture removal now removes the likely imported ancestor/root object, not just the visible child mesh.
- Downstairs toilet/powder-room interact zones are removed when the scrub runs.
- Added stronger debug reporting through the existing downstairs toilet snapshot/count helpers.
- Stairs now gate tread support through `activeAvatarCanUseStairSupport`; avatars should only snap to a stair when actually close to that tread or when running a stair-specific route. This targets the reported top-of-stairs first/second-floor jump.
- The in-world Observe / Follow overlay is hidden by default and only appears with `?showObserveOverlay=1`; use the shell-side control instead.
- Peter/Gwen arm and hand posture got a runtime nudge toward lower arms and more curled fingers. Peter/Gwen knees were intentionally not retuned in this pass.
- Peter suit material repair now targets brighter red/blue values so the runtime does not darken him again.
- Marinette's temporary procedural body gets a small X/Z taper only. This is not a final body rebuild.

Shell changes in `tools/kira_world_shell_server.py`:

- Right-side panel widened to `clamp(420px, 25vw, 560px)` with a smaller-screen fallback.
- TemporaryAI prompt now includes location context and prop-truth rules so characters should say "main house", "living room", "library", "strip mall", "spa", "pool", "road", or "upstairs landing" instead of generic "Kira World", and should not claim book/sketch/computer/sleep actions without matching visible props/furniture.
- Long voice replies are shortened for TTS playback while full text remains in chat, reducing the audio lag Robert reported.

Verification passed:

```text
node --check Data\world_builds\notebook_worlds\home_world\builds\home_world_main_house_20260630_223000\preview\src\main.js
python -m py_compile tools\kira_world_shell_server.py
npm.cmd run build
python _tmp_verify_home_world_runtime.py
```

Remaining Home World work:

- Live reload and visually confirm the toilet is removed. If still present, inspect the object path with `window.kiraWorldDebug.downstairsToiletDebugSnapshot()` and remove the exact root.
- Replace blocky furniture/kitchen/doors/stairs/railings/materials with downloaded models. The current patch did not complete the realism pass.
- Fix upstairs floor overhang/layout and create a safer stair landing with no fall-through or snap gap.
- Add real book/phone prop pickup before characters claim reading or phone use.

## 2026-07-10 Kira Runtime Movement, Court, School Chair, And Sleep Hooks

Runtime file updated:

```text
Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/src/main.js
```

Changes:

- The old generated/block time-car fallback is now hidden when the imported car is available, preventing the hated block car from flashing on startup. The real imported car remains the visible parked car.
- Kira's procedural eye pieces were moved closer to the intended eye sockets and scaled down. This is still not a final face rig; verify with front/side screenshots before calling it done.
- Kira's default arm pose was lowered and relaxed, and a repeatable `startKiraArmMobilityTest(seconds)` debug hook now cycles arm-control phases.
- School chair placement moved behind the school desk; `startSchoolStudyHoldAtDesk()` uses that corrected target.
- Basketball ball placement/rest height was corrected; `startBasketballHoldAtCourt()` now hides the world ball, puts the ball in Kira's hands, dribbles, then attempts a shot arc.
- Added basic basketball court colliders for perimeter/gates/hoops/benches and `startBasketballBenchSitStand()` for bench sit/get-up testing.
- Added `startKiraSleepPractice()` for Kira's bungalow bed. It records a runtime dream/nightmare seed in `kiraDreamState`.
- Added a real Reflector full-body mirror in Kira's temporary studio for avatar/body/clothing review. Runtime status exposes it as `kiraBungalow.fullBodyMirror`.
- Runtime status now exposes `kiraArmTest`, `basketballPractice`, and `kiraDreamState` through `window.__kiraHomeWorldRuntime` and `homeWorldActivityStatus()`.

Verification:

```text
node --check Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/src/main.js
npm.cmd run build
python _tmp_verify_kira_runtime_20260710.py
```

Evidence:

```text
_tmp_kira_runtime_20260710_verify/01_kira_eye_arm_test.png
_tmp_kira_runtime_20260710_verify/02_school_chair_alignment.png
_tmp_kira_runtime_20260710_verify/03_basketball_practice.png
_tmp_kira_runtime_20260710_verify/04_bench_sit_test.png
_tmp_kira_runtime_20260710_verify/05_kira_sleep_test.png
_tmp_kira_runtime_20260710_verify/report.json
_tmp_kira_runtime_20260710_verify/latest_after_mirror.log
```

Known rough edges:

- Sleep pose is still visually rough; Kira reaches the bed and records dream state, but needs a true bed-length prone/supine pose.
- Court collision is usable for a first test but not full object-accurate physics.
- The bungalow still contains small/awkward props that should either become usable or be removed.
- Kira arms and hands need more training/tuning against real human motion references.
- The full-body mirror is only the Home World prop/interaction hook; Robert avatar review/takeover still needs the avatar-control work.

## 2026-07-12 Pre-RAM Home World Offload And Text/Voice Testing

- Robert clarified Capture the Flag battlefield was never supposed to be part of the Home World map. It should return later as a separate notebook world/route like Paris. Do not restore it as Home World geometry.
- The Home World pre-RAM cut keeps 3D load lower while Robert is still on 16 GB. The text/voice launcher should be used for Kira mind/personhood/voice tests instead of loading the 3D world.
- Use `Start_Kira_Text_Voice_Chat.bat` / desktop shortcut `Kira Text + Voice Chat.lnk` for non-3D tests. It runs on port `8768` with `text_voice_mode: true`, empty `world_url`, and empty `avatar_url`.
- Full Chatterbox voice on CPU can make the Python server grow to about `5.2 GB` during/after a reply. Until RAM is upgraded, the reliable pattern is to safe-close/restart the text/voice server after each voiced test turn, then reactivate Kira. This returned free RAM to about `8.3 GB` during the July 12 cleanup.
- Do not kill Robert's normal Edge, VS Code, Windows services, Codex, or Ollama when doing RAM cleanup. Stop only stale Kira 3D/dev/text server processes that are clearly not needed.

## 2026-07-15 Home World Item/Identity Notes

- Robert's private source pack for the Robert digital twin is now at
  `Data/identity/robert_mcmurrer/robert_source_memory_20260715.md` with JSON at
  `Data/identity/robert_mcmurrer/robert_source_memory_20260715.json`. Use this
  before any Home World meeting between Kira and Robert's digital twin.
- Reusable transformation sets are staged under
  `Avatar/wardrobe/transformation_sets/`.
- Ladybug earrings rule: if a resident chooses to wear the earrings and says
  `spots on`, Avatar Builder should fit a Ladybug costume to that resident's
  approved body. `spots off` reverses it. The earrings can be passed to another
  resident, but the costume must be generated/fitted for that wearer.
- Pink Ranger morpher rule: the resident must pick up/hold the morpher forward
  and say `Pterodactyl`; helmet on/off is optional and should be a separate
  wardrobe mode.
- These transformation items are not runtime-approved clothing yet. Do not
  place them into daily autonomous use until Avatar Builder proves the costume
  can appear, move, sit, lie, use doors/props, and reverse without corrupting
  the base body.
