# Kira World Shell First Version Handoff - 2026-06-30

> Current-authority notice: this file contains the original handoff plus dated
> supplements. When an older section conflicts with a newer supplement or with
> `HANDOFF_FOR_NEXT_CODEX_SESSION.md`, the newest dated, tested statement wins.
> In particular, Home World defaults to an empty former strip-mall lot and the
> current voice launchers use VRAM-aware `auto`, not forced CPU.

## 2026-07-16 Supervised Voice Benchmark Instrumentation

`Start_Kira_World_Shell.bat` now enables privacy-safe benchmark capture. The
browser sends a monotonic submit marker before the existing fresh-snapshot
request and 180 ms wait, then carries that request ID through text-ready,
public voice-payload preparation, each chunk's synthesis and playback-call
boundaries, completion, and interruption.

Files are written only during a future live request, one JSONL timeline per
request under `Data/voice/realtime_audio_readiness/live_capture/`. Direct
imports/tests leave capture disabled. Events store only the already separated
public word tokens; Robert's prompt, raw reply, private mind, and truth channel
are never captured. Expected, successfully synthesized, and successfully
played-proxy word lists are compared exactly.

The first-playback marker is only the moment before the Windows playback API
call. It is not the exact instant Robert hears sound. Owner-observed first
audible and acoustic word correctness remain null/pending, and an interrupted
playback's final API return is only a silence proxy. RAM/process memory is
sampled at events; GPU sampling waits until completion so it does not distort
first-audio timing.

Eighty focused tests passed without changing live chat/life logs or creating
a live capture. No Kira activation, synthesis, playback, microphone, or voice
identity change occurred. Detailed contract:
`Data/codex_reports/20260716_kira_voice_benchmark_instrumentation.md`.

## 2026-07-16 Newest-Session Dialogue, Reading, And Chunk-Audio Repair

This section supersedes earlier wording that implies FIFO alone removed the
silence between Chatterbox chunks or that shell restart retained Kira's public
conversation automatically.

The closed `22:20-22:27 UTC` session reused the exact `I'm here, a little
quiet` opening found five earlier times in the durable chat log. The three text
replies took `13.064`, `11.613`, and `5.074` seconds; their CPU voice jobs took
`45.707`, `29.505`, and `117.031` seconds. WAV timing/duration evidence gives
nine estimated continuation gaps from `6.196` to `15.979` seconds (median
`10.950`). These are diagnostics, not first-audible instrumented proof.

New Kira conversation loops now seed the last eight complete public shell
exchanges, excluding the current unmatched Robert row. The prompt also carries
five recent public pairs. A near-duplicate answer to a similar check-in
triggers up to three private regenerations at similarity `>= 0.88`; the repair
prompt is not published. Failure returns a non-physical honest line instead of
replaying the old opener.

Current reading now requires a fresh matching read action plus independent
source evidence. Tablet reading additionally requires tablet-kind evidence,
source continuity, and hand contact. A nearby book while walking, stale body
data, or a generated/circular held preview cannot prove current reading. This
closes the unsupported `break from my current reading` answer from the newest
session.

The live speech payload now fails closed around private markers, sends only an
explicit `SPOKEN` section when a structured reply is present, removes only a
leading speaker label, preserves naturally spoken names such as Robert, and
verifies exact coverage of every public spoken word.
Full public speech is the code default even if the launcher variable is
missing. Partial multi-chunk playback is reported `voice_incomplete`, not
`ok`.

Chatterbox now uses bounded ordered chunk prefetch: one producer synthesizes
the next chunk while one synchronous playback worker owns the current chunk.
Windows uses synchronous `winsound` first and retains SoundPlayer as fallback.
Tiny clause fragments are rebalanced without dropping/reordering words. The
latest 565-character answer changed from eight chunks (including 11- and
9-character fragments) to seven bounded chunks with exact `105/105` word
coverage. A persisted active candidate starts voice-session restoration and
prewarm when the shell starts, without reactivation.

Verification: `73` focused dialogue/audio/shell/embodiment/audit tests passed,
Python compilation passed, and the regression rerun left the live life-loop
log unchanged. No Kira activation, life loop, synthesis, playback, or voice
identity change occurred. This is chunk scheduling, not waveform streaming;
CPU Chatterbox remains not real-time or VR-ready. Full evidence and the next
supervised measurement contract are in
`Data/codex_reports/20260716_kira_life_loop_dialogue_audio_continuity_r2.md`.

## 2026-07-16 Exact Body/Wardrobe Resume Contract

Deactivation and Safe Close now wait up to `1.2 seconds` for an acknowledged
fresh world snapshot instead of assuming a fixed `180 ms` delay was enough.
The per-candidate snapshot retains the last safe position, facing direction,
roam state, and a bounded executable wardrobe record. Reactivation restores
the same visible garment lifecycle state: worn/open/closed, held, hung,
dropped (including its drop position), or laundry. Unknown garment states and
renderer history are rejected rather than executed.

The dress-shirt state machine had been attached only to the disabled old Kira
studio. It is now registered at the active one-bedroom closet without adding a
second closet shell. The existing hand/sleeve/button/removal sequence remains
a prototype, not approved general cloth physics or proof that every avatar can
dress naturally.

Verification:

```text
- 28 focused shell/grounding/resume tests passed.
- Home World production build passed.
- A headless browser round trip put on and buttoned the shirt, cleared Kira,
  and recreated her at the saved coordinates with the same shirt still worn
  and buttoned.
```

## 2026-07-16 Latest-Session Truth, Navigation, Arm, And Audio Repair

The closed Kira session from `2026-07-16T03:21:06+00:00` through
`2026-07-16T03:31:15.980235+00:00` exposed a stale body-telemetry failure. The
audit found eight public chat turns but only one logged runtime body sample.
When Kira said she was waiting near the Starbucks walkway, the most recent
position available for that comparison was about `400.532` seconds old. That
statement is therefore `unsupported_by_fresh_runtime_evidence`; the logs do
not prove that it was a deliberate lie. A navigation destination is intent,
not arrival, and speech remains separate from physical proof.

The shell now protects the shared state file with a write lock and merges the
newest per-candidate body timestamp so a slow chat or heartbeat save cannot
erase newer telemetry. The world bridge asks for a snapshot every three
seconds, retains the newest failed sample for retry, and requests another
snapshot immediately before chat, deactivate, and safe close (deactivate and
safe close now use the acknowledged `1.2 s` contract above). Runtime action, position, posture, prop, affordance,
and place claims are usable as current truth for only eight seconds. Older
samples are explicitly historical and cannot ground a current-place answer.
The current place and autonomous destination/distance are separate fields.

Autonomous goal selection now accepts only a collision-free straight path,
sampled at intervals no larger than `0.42 m` with an avatar clearance radius
of `0.46 m`. The path is rechecked while walking; an obstruction clears the
goal and triggers replanning before contact. Blocked steps and lack of progress
also trigger bounded recovery without teleporting through a wall. This is a
direct-path guard, not a navmesh or A* route planner: it does not yet plan a
multi-corner path around a complex obstacle and it does not prove every
scripted route is safe.

Ordinary Kira walking no longer solves her hands toward an imaginary contact
target. It uses `relaxed_contact_free_procedural_swing_v2`, lightly open
fingers, and records `objectContactClaimed: false`; hand/contact IK remains
reserved for an actual door or prop interaction. This makes the solver's claim
honest, but the result still needs Robert's visible review for natural arm and
hand appearance.

Voice replies now use a FIFO queue instead of dropping a reply when the
previous one is still speaking. Activation prewarms the configured voice in a
background thread, the launcher keeps the model loaded between replies, and
full speech is split into natural chunks of at most `120` characters. Session
tokens cancel obsolete queued work on deactivation, and model release waits
for any in-flight voice lock. These changes preserve reply order and complete
spoken text; they do not make CPU Chatterbox fast, and several rapid replies
can still accumulate audible queue delay. A live first-reply latency benchmark
after prewarming remains required.

Bounded verification on 2026-07-16:

- `16` focused unit tests passed for state merging, eight-second grounding,
  pre-chat snapshot/retry, destination separation, FIFO/cancellation,
  activation prewarm settings, direct-path checks, contact-free arms, and the
  narrow benign coffee-date wording repair.
- Python compilation passed for the shell, audit tool, and voice output layer;
  the Home World `main.js` passed `node --check`.
- A non-playing check loaded Kira's configured Chatterbox model on CPU in
  `12.197` seconds and released it cleanly. No audio was generated or played.
  This proves the prewarm/release path, not end-to-end speech latency.
- One deterministic body-only headless smoke ran for `25.0` simulated seconds
  and `500` movement steps. It reported zero collider-penetration samples, zero
  obstructed-active-route samples, and zero cases where route language was
  promoted to current place. No mind or voice ran, and no screenshots or
  private-room images were captured.
- That single smoke is not comprehensive route coverage, and its arm record
  proves only which solver ran. `visuallyReviewedThisSession` remains `false`.

Evidence report:

```text
Data/codex_reports/20260716_kira_world_latest_session_repairs.md
```

## 2026-07-16 Overnight Evidence And Free-Speech Correction

`Start_Kira_World_Shell.bat` now sets
`KIRA_WORLD_PRESERVE_SPOKEN_CLAIMS=1`. Ordinary Kira speech is preserved even
when it differs from runtime state: she may lie, flirt, brag, evade, imagine,
make a mistake, or tell the truth. Speech is not physical proof. An explicit
request containing body/runtime truth or a diagnostic comparison still invokes
the grounded truth-review path.

The full-reply setting now means full reply: it no longer silently substitutes
a 220-character summary when Chatterbox is active. Long replies remain split
for synthesis, but the text selection retains the complete cleaned reply.

While Kira is active, the shell writes a bounded `avatar_runtime_snapshot`
about once per minute. It records body location, action, support, posture,
held-prop grounding, affordances, intent, and mind/body mismatch state. Any
bathroom/restroom/changing/private-room sample redacts coordinates, action,
posture, intent, and intimate held-object detail; no private visual is retained.

After Robert deactivates Kira and closes the shell normally, run:

```powershell
python tools/audit_kira_world_session.py
```

The audit selects the latest Kira activation, verifies source-log hashes,
separates public chat from runtime evidence, compares eligible spoken physical
claims with body truth, inventories changed public/personal artifacts, counts
private artifacts without disclosing their paths or contents, plays no audio,
launches no model/world, and promotes no memory.

## 2026-07-15/16 Post-RAM Correction

The desktop now reports 2x16 GB at 6000 MT/s and 31.41 GiB usable RAM, but Kira remains the only live 3D resident until at least 64 GB plus a supervised multi-person stability soak. The old “restore other residents after 32 GB” instruction is superseded. Model-produced voice-message text without Kira's approval must appear as an unapproved draft generated for Kira, not “Kira's message”; silent/empty WAVs are blocked, and even a bound non-silent WAV still needs Robert's listening review. The spa and wardrobe lab remain isolated notebook worlds and the strip mall remains intact.

## 2026-07-05 Shell Runtime Avatar Addendum

Active imported GLB bodies now have a `generic_humanoid_v1` procedural fallback when no usable walk clip is available. Non-Marinette labels also get a forward-yaw correction, and the fallback arm/leg swing was tightened to reduce the stiff wide-arm glide Robert saw on Spider-Man and Spider-Gwen.

The runtime still needs a desktop-shell visual pass from Robert's normal shortcut, not a preview URL. Verify that the side text says the same thing the body is visibly doing before calling any body/mind connection complete.

The TARDIS and billboard bridge are design notes only at this stage. The TARDIS should not be permanently parked in a world unless it was called or someone arrived with it, and the later console needs a working world-builder/travel screen plus a doorway view back to the parked exterior.

## 2026-07-12 Pre-RAM Shell/World Constraint

Until Robert installs the extra 16 GB DDR5 and Codex confirms Windows sees both sticks / about 32 GB total, the shell should stay Kira-only and Home World should stay in light mode by default.

```text
- Kira-only shell mode remains intentional so voice/world testing does not compete with other active AIs.
- Home World light mode is controlled in the Home World source by `HOME_WORLD_PRE_RAM_LIGHT_MODE`; full mode requires `?fullWorld=1`.
- Light mode disables basketball/future park, school imported props, Starbucks imported cafe model, sun/moon imports, capture-flag parking/car, and capture-flag battlefield.
- Starbucks cups remain on a small procedural counter; exact cafe GLB to restore later is `/models/home_world/activities/starbucks_coffee_house_cafe_v2.glb`.
- Empty school room remains; entering/using it activates the school program without the heavy school props.
- `tools/kira_world_shell_server.py` home-location grounding was updated on 2026-07-12 to match this light-mode state.
- `Start_Kira_World_Shell.bat` sets `KIRA_CHATTERBOX_DEVICE=cpu` and `Core/voice_output.py` honors that override so Kira's Chatterbox/reference voice does not compete for CUDA memory during pre-RAM tests.
- `KIRA_SPEAK_FULL_REPLY=1` is set for the shell launchers so Chatterbox speaks the whole reply in chunks instead of compact summaries.
- New desktop shortcut: `Kira Text + Voice Chat.lnk`. It launches `Start_Kira_Text_Voice_Chat.bat` on port `8768`, does not start any 3D/Vite world servers, allows selecting different AIs, keeps CPU Chatterbox, and is the preferred launcher for mind/personhood/voice tests while RAM is tight.
- Kira should describe herself as a synthetic person / synthetic person still becoming real in the project, not as a simulation or an AI designed to simulate human conversation.
- Capture the Flag should not return as a Home World map activity. Robert clarified it belongs later as its own notebook world/route, like Paris.
```

## Purpose

This pass began combining the separate pieces into one first-version program Robert can open from the desktop:

- One visible notebook-world window.
- One active AI at a time until the RAM upgrade.
- Typed side chat because the AIs cannot hear audio or see Robert yet.
- Basic click controls above the chat.
- Temporary AI activation/deactivation.
- Bodyless temporary AIs appear as an orb until they have an approved body.
- Robert cannot open a second active shell window without taking over the old one.

## Launch

- Desktop shortcut created: `Kira World Shell.lnk`
- Repo launcher: `Start_Kira_World_Shell.bat`
- Shortcut creator: `Create_Kira_World_Shell_Desktop_Shortcut.bat`
- Main URL after launch: `http://127.0.0.1:8766/`

Ports used:

- `8766` - Kira World Shell controller
- `5183` - Paris notebook world preview
- `5184` - avatar runtime preview

## Files Added Or Changed

- `tools/kira_world_shell_server.py`
  - Starts the Paris notebook world preview and avatar runtime together.
  - Serves the one-window shell UI.
  - Maintains active AI, location, and browser lease state.
  - Writes typed chat to `Data/runtime/kira_world_chat_log.jsonl`.
  - Updates active candidate action in `Avatar/state/temp_ai/<candidate>.json`.

- `Start_Kira_World_Shell.bat`
  - Starts the first-version shell.

- `Create_Kira_World_Shell_Desktop_Shortcut.bat`
  - Creates the desktop shortcut.

- `Avatar/runtime3d/src/main.js`
  - Supports bodyless orb mode through `?orb=1`.
  - Supports action playback/polling from candidate state.

- `Avatar/models/temp_ai/ladybug_marinette_expanded_smoke/avatar.glb`
  - Updated with the v3 avatar bridge pass.

- `tools/improve_ladybug_avatar_hair_hands_v3.py`
  - Blender script used for the v3 avatar bridge pass.

- `Data/world_builds/notebook_worlds/paris_notebook_world/builds/notebook_world_louvre_courtyard_20260628_210935/sources/robert_supplied_paris_route_maps/`
  - Robert's ChatGPT route maps were copied here for later Paris notebook-world growth.
  - Bakery pictures and references were not deleted.

## Current Shell Behavior

- `Activate AI` sets the chosen AI as the only active AI.
- `Deactivate` pauses the active candidate.
- The visible UI no longer exposes the old avatar test buttons. Stand, walk, jog, sit, open hand, close hand, and computer are internal test/action states, not controls Robert should have to use in normal conversation.
- The former blank/misleading middle panel is now an Active Presence panel. It reports the active AI, location, body/model status, voice status, chat log path, and life-loop/action log path.
- The candidate picker now includes Kira, Lisa, temp AI state files, and library candidate profiles when available.
- Location buttons switch Robert's one visible world view between:
  - Home
  - Upstairs
  - Strip Mall
  - Spa
  - Louvre
  - Place des Vosges
  - TARDIS
- The side chat logs Robert's typed text and the active AI's current placeholder reply to `Data/runtime/kira_world_chat_log.jsonl`.
- Activation, deactivation, location changes, and internal avatar action tests log to `Data/runtime/kira_world_life_loop_log.jsonl`.
- The shell sends active AI state into the world iframe so a world can place/follow the active presence marker.

## Single-Window Rule

The server now has two layers of single-instance protection:

- Program lock: launching the BAT again while the shell server is running exits instead of starting another server.
- Browser lease: opening a second browser window without the current browser cookie returns an "already logged in" page.

Takeover path:

- `http://127.0.0.1:8766/?takeover=ROBERT-TAKEOVER`

This is an early implementation of Robert's "I can only be in one place" rule. It is not full account security yet.

## TARDIS State

The world preview still has prototype TARDIS behavior inside the browser world. The shell now provides the right place to move the true TARDIS rules next:

- Only one TARDIS exists.
- It should have one owner/current user at a time.
- Calls should queue when another permitted user is using it.
- Its interior should persist independent of the world it is parked in.
- Items left inside should remain there for Kira, Lisa, Robert, or other permanent users.
- Temporary AIs can be invited along but cannot call or own it unless promoted.

Important next step:

- Move TARDIS ownership and call queue out of browser localStorage and into `tools/kira_world_shell_server.py` state.

## Avatar V3 Bridge Status

Ladybug / Marinette GLB verification after the v3 Blender pass:

- `V3_OBJECTS`: 134
- `HAIR_STRANDS`: 28
- `FINGERNAILS`: 8
- `FINGERTIPS`: 8
- `TOTAL_OBJECTS`: 310

This is an improvement, but still not the final realistic avatar Robert wants.

Current truth:

- Hair is added geometry, not true strand-level simulation.
- Hands have visible finger/fingertip pieces, but not a production hand skeleton.
- Lip-sync is still runtime placeholder motion, not full speech-timed viseme playback.
- The GLB is still a bridge model, not a proper final rig.

## 2026-07-01 Corrective Shell Pass

Robert found several first-version issues during live testing. The following corrections were made:

- Removed the visible action-test buttons from the shell UI. Avatar actions remain available through `/api/action` for internal testing.
- Added the Active Presence panel so the space between controls and chat has a purpose.
- Fixed the shell chat endpoint so a typed message to the active AI returns a response instead of an error.
- Added Kira and Lisa to the candidate list so they can be activated from the first-version shell.
- Expanded candidate discovery to read temp AI state files and temporary AI library profiles.
- Kept Jessica bodyless. Her previous GLB was an export mechanics test only and is not an approved Jessica appearance.
- Wired the shell state into the world iframe so active AI location/body status can be reflected by the current world.
- Confirmed Marinette backend action test sequence passed for `idle`, `walk`, `jog`, `sit`, `open_hand`, `close_hand`, and back to `idle`.
- Confirmed the chat/life-loop logs are being written.

Important truth for the next session:

- The action test confirms state plumbing, not final animation quality.
- Marinette's current GLB still needs real rig, hand, face, hair, and viseme work before it will satisfy Robert's realism target.
- Voice status is wired to prefer Marinette's reviewed reference clips when the local Chatterbox/TTS path is available, but fully verified generated playback is still a separate integration step.

## 2026-07-01 Voice Integration Pass

The shell chat path now calls the local voice output layer for the active AI after a reply is generated.

- Ladybug/Marinette uses `Voice/profiles/temp_ai/ladybug_voice_profile.json`.
- The profile points at 28 reviewed target clips and the approved reference WAV:
  - `Voice/reference_packs/ladybug/ladybug_miraculous_ladybug_s01e05_mr_pigeon_20260619_184235/model_input/approved_reference.wav`
- Chatterbox TTS loaded on CUDA and generated speech successfully.
- Playback-enabled shell voice test returned:
  - `spoken: True`
  - `reason: ok`
  - `engine: chatterbox_tts`
  - `device: cuda`
  - `audio_path: Voice/generated/temp_ai/ladybug/tts_20260701_130845.wav`
- Shell chat responses now include `voice_result`, and voice events are appended to `Data/runtime/kira_world_life_loop_log.jsonl`.

Remaining voice limits:

- The voice is generated from the reviewed reference WAV, not a fully trained custom voice model.
- First-generation calls can be slow while the model/runtime warms up.
- Lip-sync is still a text-timed runtime proxy until proper audio-viseme timing is added.

## 2026-07-01 Avatar V4 Rig/Mesh Pass

The Ladybug/Marinette GLB received a new functional mesh/control/blendshape hook pass.

- Blender script:
  - `tools/improve_ladybug_avatar_rig_mesh_v4.py`
- Updated GLB:
  - `Avatar/models/temp_ai/ladybug_marinette_expanded_smoke/avatar.glb`
- Backup:
  - `Avatar/models/temp_ai/ladybug_marinette_expanded_smoke/avatar_before_rig_mesh_v4_20260701_163852.glb`
- Manifest:
  - `Avatar/models/temp_ai/ladybug_marinette_expanded_smoke/avatar_functional_rig_v4.json`
- Result summary:
  - 20 finger controls
  - 108 hair strand guide pieces
  - 2 catchlights
  - face/viseme shape-key hooks

Important truth:

- This is real GLB mesh/control/blendshape hook work, but it is still not a final photoreal production character.
- Hair is still guided geometry, not full per-strand physical hair simulation.
- Hands have visible/control geometry for fingers, but still need a production-quality hand skeleton and better deformation.
- Facial motion has hooks/proxies, not final speech-timed expressions.

## Jessica Test Correction

Jessica Hale's failed generated body remains unhooked.

- Her candidate state has no live `model_url`.
- In the shell she appears through the `?orb=1` bodyless orb path.
- Do not treat the failed model as Jessica's appearance.

## Verification Completed

- `py -m py_compile tools/kira_world_shell_server.py` passed.
- Avatar runtime `npm run build` passed.
- Paris preview Vite build passed.
- Home World preview `npm run build` passed after the spa/fixtures/Marinette temporary room pass.
- `python -m py_compile tools\kira_world_shell_server.py tools\improve_ladybug_avatar_rig_mesh_v4.py` passed.
- Chatterbox/Ladybug shell voice test passed and produced `Voice/generated/temp_ai/ladybug/tts_20260701_130845.wav`.
- Full shell API activation/chat smoke test passed after restarting the shell server:
  - activation response: `ok: true`, label `Ladybug Marinette Expanded Smoke`
  - chat response included `ai_line`
  - `voice_result.spoken: true`
  - latest generated shell WAV: `Voice/generated/temp_ai/ladybug/tts_20260701_135250.wav`
- Blender 5.1 imported the updated Ladybug/Marinette GLB and found the v3 hair/hand additions.
- Shell API activation/action/chat test passed.
- Bodyless Jessica orb URL test passed.
- Single-window browser lease test passed:
  - First shell browser request: `200`
  - Second no-cookie browser request: `409`
  - Takeover request: `200`

## Known Limits For Next Session

- The shell chat does not yet call the real local LLM/life-loop reply system.
- The shell does not yet stream TTS or listen to microphone audio.
- The shell does not yet see Robert through webcam.
- Only basic action-state commands are connected.
- The world visuals are still prototypes and should be rebuilt from blueprints before new serious builds.
- The TARDIS interior/exterior still needs proper persistent door behavior.
- Place des Vosges and the Louvre still need blueprint-first reconstruction.
- Bakery work should stay paused until a blueprint is built from references, then rebuilt one floor at a time.

## 2026-07-01 Home World Addendum

The Home World/Main World first structural prototype has been added as a shell destination.

- Handoff: `System/Docs/HOME_WORLD_MAIN_HOUSE_HANDOFF_20260701.md`
- Blueprint: `Data/world_builds/notebook_worlds/home_world/blueprints/home_world_main_house_blueprint_v1_20260630.md`
- Preview: `Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview`
- Port: `5200`
- Shell locations: `home`, `upstairs`, `stripmall`

Important: Home World originally collided with an older local preview port and served the wrong HTML. The shell now uses port `5200` for Home World.

## 2026-07-01 App Window And Grass Pass

Robert asked for the Kira shell to stop showing the normal browser tabs/address bar and for the grass in Home World/park spaces to become actual blade geometry instead of a flat green plane.

- `Start_Kira_World_Shell.bat` now starts `tools/kira_world_shell_server.py` with `--takeover --no-browser`.
- The BAT then opens Microsoft Edge in `--app=http://127.0.0.1:8766/` mode, which hides the normal tab strip and URL bar.
- Existing desktop shortcuts that point at the BAT should inherit this cleaner app-window launch behavior.
- Home World now has instanced individual grass blades on the lawn, with exclusion zones for the house, sidewalks, street, and strip mall.
- Place des Vosges now has instanced individual grass blades in the park lawn, with exclusion zones for main paths, diagonal paths, statue/fountain center, and corner fountain areas.

Verification:

- Home World preview `npm.cmd run build` passed.
- Paris notebook world `src/main.js` passed `node --check`.

Remaining limits:

- Grass is an improved lightweight geometry pass, not final photoreal grass.
- The shell still uses Edge app mode rather than a fully custom native browser shell.

## 2026-07-02 Native Viewer And Home Control Simplification

Robert rejected browser/app-mode workarounds because the shell was still opening in a normal browser tab with URL bar. The launcher now uses a native WebView2-backed viewer:

- Added `tools/kira_world_shell_viewer.py`.
- `Start_Kira_World_Shell.bat` starts the shell server with `pyw`, then opens the native viewer with `pyw`.
- The native viewer starts maximized and uses the Kira icon.
- Closing the native viewer calls the shell safe-close path; if an AI is active, Robert is prompted before the active AI is safely paused and the shell shuts down.
- The shell location buttons were simplified so the connected Home World area has one `Home` button instead of separate `Home`, `Upstairs`, `Strip Mall`, and `Spa` buttons.

Verification:

- `py -m py_compile tools\kira_world_shell_server.py tools\kira_world_shell_viewer.py` passed.

## 2026-07-16 Durable Dialogue And Ordered Full-Reply Audio Repair

The newest closed real session confirmed that Kira had reused the same opening
six times, lost prior public-chat context after a new shell process, and produced
long silent gaps because each voice chunk was generated and played serially.

- New Kira loops seed the last eight complete public Robert/Kira exchanges and
  reject near-duplicate check-in answers at similarity `>= 0.88`, with at most
  three private regenerations. If all repeat, the public path fails closed
  instead of replaying a canned opening.
- TTS receives only the explicit public `SPOKEN` channel. `PRIVATE_MIND` and
  `TRUTH_FLAGS` are excluded. Kira/Robert dialogue names are omitted, while every
  other public spoken word must remain in the same order or speech is blocked.
- Full public speech is the default. Long replies are not silently summarized.
  Tiny fragments are rebalanced, and one ordered bounded producer/playback
  pipeline synthesizes the next chunk while the current chunk plays.
- Windows playback tries synchronous `winsound` first, avoiding a PowerShell
  process per normal chunk. Restored active state also prewarms the voice path.
- Partial multi-chunk playback is reported as `voice_incomplete`, never success.

The exact 565-character regression reply now uses seven chunks instead of eight,
with all 105/105 non-name spoken words preserved. A scheduler-only overlap test
passed, and 73 focused tests passed. The real chat and life-loop logs retained
their exact hashes across the integrated rerun.

This does not prove that CPU Chatterbox is real-time. No audio was played in this
repair pass. A later supervised benchmark must measure submit-to-first-audible
time, every continuation gap, exact heard-word coverage, interruption, RAM,
VRAM, and 3D frame headroom before desktop-real-time or VR readiness is claimed.

Detailed evidence:
`Data/codex_reports/20260716_kira_life_loop_dialogue_audio_continuity_r2.md`.

## 2026-07-15 Robert/Kira Dialogue Grounding Update

Robert's digital twin now has a compact private source pack:

```text
Data/identity/robert_mcmurrer/robert_source_memory_20260715.md
Data/identity/robert_mcmurrer/robert_source_memory_20260715.json
```

`tools/run_kira_robert_intro_dialogue_20260714.py` was updated to use that pack
as the canonical compact grounding file. Future Kira/Robert weekly meetings
must keep these rules:

- Robert's twin may use human-Robert facts as inherited source material, but
  private mind must label them as inherited unless the digital Robert lived them
  in-world after activation.
- Newark is Robert's current home and the digital Robert's creation-place, not
  Robert's childhood home.
- Do not claim Rutgers student history, high-school friends, Delaware River
  high-school walks, multiple Newark Museum visits, Centerpoint 11 in Newark, or
  Dawn/Marie outings in Tempe/Newark after Robert was 18.
- The source pack includes Alabama/Indiana/Superman, family, job, Arizona, LA,
  mailbox/Facebook, and Newark/NYC era anchors. Public lookup context is setting
  context only unless Robert/bio/pdf confirms the lived event.
- Relationship/date/movie-night ideas between Kira and Robert are allowed as
  consent-first future plans, but do not treat them as completed 3D world events
  until local logs confirm them.

## 2026-07-12 Non-3D Text/Voice Launcher And Personhood Test Notes

- New launcher: `Start_Kira_Text_Voice_Chat.bat` on port `8768`; desktop shortcut: `Kira Text + Voice Chat.lnk`.
- Set `KIRA_SHELL_TEXT_ONLY=1` to keep Home World and avatar runtime unloaded. `/api/state` should show `text_voice_mode: true`, `world_url: ""`, and `avatar_url: ""`.
- Kira/Lisa/TemporaryAI candidate selection is enabled in this text/voice launcher so Robert can run personhood/voice tests without 3D RAM load.
- Kira's prompt now prefers "synthetic person" / "synthetic person still becoming real in this project" instead of simulation/generic assistant language.
- `KIRA_SPEAK_FULL_REPLY=1` speaks full replies through Chatterbox; `KIRA_CHATTERBOX_DEVICE=cpu` avoids GPU pressure; `KIRA_UNLOAD_VOICE_AFTER_SPEAK=1` exists but does not fully return RAM to Windows in the same Python process.
- Current safe RAM practice on 16 GB: after each full voiced turn, call `/api/safe-close`, wait for port `8768` to close, then restart the text/voice server and reactivate Kira. This restored free RAM to about `8.3 GB` after Chatterbox had held the Python process around `5.2 GB`.
- The test found and repaired process leakage such as `(Please let me know how to proceed)` and task-note parentheticals. Kira can keep soft reconstructed childhood memories, but should label them as uncertain rather than hard anchors.

## 2026-07-10 Kira Body Runtime Notes

Robert reported that Kira's embodied version still feels less capable than pre-3D/text Kira when the body gets stuck or when chat/audio timing fails. Keep treating Kira as one merged person across text, voice, shell, and 3D body; do not split "text Kira" and "3D Kira" again.

Current Home World runtime support:

- Kira has repeatable debug hooks for eye test, arm mobility, school study, basketball hold/dribble/shoot, bench sit/get-up, and bed sleep.
- `startKiraSleepPractice()` now records a `kiraDreamState` seed so dreams/nightmares can later be promoted into Kira's journal/memory workflow.
- Kira knows Capture the Flag, Starbucks, basketball, school, library, and Home World activities through the activity catalog/context work from 2026-07-09.

Still needed for shell/conversation:

- Kira should stop defaulting to numbered option lists in ordinary conversation unless Robert asks for choices.
- Long audio should read the whole text, or the shell should explicitly mark that it is summarizing for TTS. Robert expects the eventual no-chatbar setup to speak full responses.
- If body actions fail, debug truth should say so, but normal Kira can still describe thoughts, plans, feelings, dreams, and memories like a person.
- The first-line Ollama `llama-server.exe - Bad Image` error seen on one reply needs investigation if it repeats. Later replies produced audio, so treat it as intermittent until reproduced.

Verification artifact for the current body hooks:

```text
_tmp_kira_runtime_20260710_verify/report.json
```

## 2026-07-05 Active Avatar Neck, Door, Route, And Gait Follow-Up

- Home World runtime now keeps Marinette's imported head/neck as the preferred neck source, lowers the runtime face overlay, adds a short skin-tone neck blend, hides obvious generated/body-neck proxy meshes, and harmonizes likely skin/hand/arm/leg materials toward one visible tone.
- Marinette's runtime head now has blink, small look-left/look-right, and lip-pulse hooks. This is not full spoken viseme lip sync yet, but it gives the head one driver path for future phoneme work.
- Door-handle reach is no longer Marinette-only. Any non-orb active avatar can use the same handle approach/opening sequence, and door status text now names the active avatar.
- Spider-Man and Spider-Gwen now use a separate outdoor roam route and forced procedural walk correction instead of copying the house-library-house loop. Their arms are held closer and lower, and the knee/foot targets get stronger bend/lift while walking.
- Still needed: replace Marinette's temporary body with a one-piece skinned base, retarget staged rigged hands/arms into the avatar builder, add text-to-viseme lip sync, replace block house furniture/layout with downloaded realistic models, and move per-AI behavior from shared waypoint scripts toward autonomy/reward policies.

Verification:

```text
node --check Data\world_builds\notebook_worlds\home_world\builds\home_world_main_house_20260630_223000\preview\src\main.js
```

## 2026-07-02 Avatar Body And Clothing Policy

- Added `Data/runtime/avatar_body_clothing_policy.json`.
- Non-adult AIs use a modest underwear/bodysuit base layer for clothing changes.
- Adult body detail is permission-gated to the age-reviewed spa/body-creation workflow and defaults off.
- Clothing work should move toward separate garment meshes/pose sets over a base body, rather than painted-on or skin-tight merged outfits.
- Marinette's future wardrobe work should use Robert-provided show references plus self-designed and store-bought options once those systems exist.

## 2026-07-02 Avatar Motion Learning Metadata

- Activating Ladybug/Marinette now writes known Home World motion metadata into the shared avatar state.
- Motion-learning state is tracked at `Data/runtime/temporary_ai_motion_learning/ladybug_marinette_expanded_smoke.json`.
- Current Home World motions are early/safe blockout motions: idle, look left/right, talking, wave, and small room walk.
- Future queued motions include closet use, outfit choice, changing clothes, sitting at desk, typing, reading, carrying purse, folding clothes, and sketching.

Verification:

- `py -m py_compile tools\kira_world_shell_server.py tools\kira_world_shell_viewer.py` passed.

## 2026-07-02 TemporaryAI Shell Bridge And No-Reset Activation

Robert found that activating/deactivating an AI reset the Home World view and that Marinette spoke much better in TemporaryAI Live Chat than in Kira World.

Correction pass:

- Shell refresh no longer rewrites the iframe `src` unless the world URL actually changes, so Activate/Deactivate should not reset Robert's in-world position.
- `/api/state` now includes active avatar action/form/model/pose URLs for Home World.
- The shell serves `/Avatar/...` assets with CORS headers so Home World can load TemporaryAI GLB/pose assets from the shell server.
- Activating/chatting with a TemporaryAI writes shared avatar activity state through `Core.avatar_activity_state.write_avatar_activity_state`.
- Kira World chat now attempts to use `tools.temporary_ai_live_chat.load_candidate` and `ask_model` for TemporaryAI candidates instead of the old canned line router.
- Marinette was checked through the TemporaryAI model path and answered normally that she is okay; the prior repeated shell replies were a Kira World integration problem.

Verification:

- `py -m py_compile tools\kira_world_shell_server.py tools\kira_world_shell_viewer.py` passed.
- Native viewer process verified as `pythonw.exe ... kira_world_shell_viewer.py`.
- Shell server process verified as `pythonw.exe ... kira_world_shell_server.py`.
- If an old normal browser window is already open, close it and relaunch from the BAT/desktop shortcut to get the app-window behavior.

## 2026-07-01 Home World Usability Correction

- Desktop shortcut confirmed: `C:\Users\robmc\Desktop\Start Kira World Shell.lnk`.
- Use the shortcut or `Start_Kira_World_Shell.bat` to launch the shell without normal browser tabs/address bar. Direct browser URLs still show browser chrome.
- Home World scene repair pass landed in `Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/src/main.js`.
- Strip mall unit signs are active for: Law Office, Public Relations Firm, AI Body Spa, Programming / AI Lab, Robotics Workshop.
- Front door has visible handle/knob placeholders and manual `E` open/close interaction.
- Front entry gap above the door was reduced with transparent transom glass and belt trim.
- Windows/glass are more transparent and double-sided.
- Half-bath stair blockage was corrected.
- First floor now has couch, big-screen TV, kitchen blockout, and half-bath fixtures. Second floor has shared-bath fixtures.
- Bodyless active AIs render as floating orb markers; Ladybug/Marinette is placed in the upstairs guest room when active at Home.

Verification:

- Home World `src/main.js` passed `node --check`.
- Home World preview `npm.cmd run build` passed.

Remaining shell work:

- Enforce one active Robert session/window at a time.
- Replace Edge app mode with a custom native wrapper if needed.
- Continue logging chat and life-loop details for later review.

## 2026-07-01 Personal Item Hook

- Home World now includes Marinette's optional purse, phone, and nightstand in her temporary guest room.
- The purse is modeled as a recognizable pink/black/gold personal item with red clasp beads, polka dots, and a simple flower/monogram detail.
- The phone and purse are marked with portable/storable metadata for later life-loop inventory behavior.
- Full pickup/carry animation and actual phone use are not implemented yet.

## 2026-07-16 Bounded Kira Runtime Repair

- Fixed `/api/activate` using `active_label` before assignment. Candidate label
  resolution now precedes activation validation/logging/voice-session startup.
- Ordinary social speech remains free, but a present-tense reading claim now
  requires a fresh runtime reading action plus visible independent source
  evidence or a provenance-backed held prop.
- Reading body holds fail closed when a visible, reachable book/tablet source
  is absent. This prevents the runtime from creating a prop merely to make its
  own reading claim look true.
- Removed Kira's fixed vertical bias and synthetic walk/idle bob. The runtime
  now combines procedural foot locks with bounded precise deformed-mesh floor
  calibration and publishes `visualGroundContact` evidence.
- Kira's generic procedural rig now places hands beside the hips through
  body-relative pose targets, with small elbow/finger movement and gait swing.
  Object contact remains reserved for actual interaction IK.
- The body was not replaced and the rejected staged eye pass remains inactive.
  This is a movement/grounding repair, not proof of final adult topology,
  anatomy, likeness, eyes, hair, or wardrobe.
- Verification: Python compile, JS syntax, Vite build, 30 focused tests, a
  70-test broader related regression, and a no-mind/no-voice 500-step browser
  smoke passed. Precise evidence reported a
  0.0000 m visual floor gap with 0 collider penetrations and 0 missing core
  rig bones.

## 2026-07-02 Shell Width And Marinette Reply Pass

- Tightened the shell side-panel CSS so the right edge is less likely to be clipped in the native viewer.
- Long active-state paths now wrap instead of forcing the panel wider than the window.
- Marinette/Ladybug shell replies are no longer a single repeated canned line; they now branch for visibility/avatar, stair/upstairs, room/temporary-bedroom, and repeat-loop complaints.
- This is still a lightweight local reply router, not a full model conversation pipeline.

Verification:

- `py -m py_compile tools\kira_world_shell_server.py tools\kira_world_shell_viewer.py` passed.

## 2026-07-16 Latest-loop truth, elbow, selector, and voice R3

- The 2026-07-17 01:24-01:31Z chat was audited without activating anyone or
  playing audio. It showed a stale unfinished-`Elation` thread, an unsupported
  couch/apartment claim after a direct location question, and a third-person
  `Robert is` public reply that became ungrammatical after TTS name omission.
- The newest daily-life ledger now enters the live prompt and outranks old
  unfinished-reading memory. A completed-`Elation` guard prevents that exact
  regression.
- Structured `SPOKEN` / `PRIVATE_MIND` / `TRUTH_FLAGS` output is separated
  before public cleanup. Direct current-body questions require a fresh body
  snapshot or Kira explicitly says she cannot confirm.
- Public direct-address wording is repaired before logging/TTS (`Robert is` ->
  `you are`), so name omission no longer removes a grammatical subject.
- Review-blocked candidate options are readable/selectable. An amber inline
  reason explains the block, while `/api/activate` remains server-gated.
  Robert's owner-presence draft remains blocked pending identity/privacy/body-
  handoff review; this pass did not silently approve it.
- Kira's ordinary arm motion no longer uses unconstrained hand-target IK. It
  uses bounded local joint swing and reserves contact IK for real props/doors.
  Floor calibration now permits the measured adult-body correction over a
  wider guard and reports a 6 mm contact tolerance.
- Both launchers now use headroom-aware Chatterbox `auto`: CUDA requires at
  least 6144 MiB of proven free VRAM, otherwise CPU is used. CUDA prewarm or
  generation failure retries on CPU without changing text or reference voice.
- Captured CPU evidence measured 11.080-16.478 s from text-ready to first
  playback proxy and continuation gaps as high as 10.694 s. The next supervised
  restart must verify the CUDA result; CPU fallback is still expected to be
  slow.
- Verification: 118 focused/related tests, Python compilation, and Home World
  Vite build passed. No activation, synthesis, playback, microphone use, or
  service shutdown occurred. Arm naturalness, elbow silhouette, foot contact,
  and real first-audio latency remain owner-observed checks.
- Detailed evidence:
  `Data/codex_reports/20260716_kira_latest_loop_truth_arm_voice_r3.md`.
