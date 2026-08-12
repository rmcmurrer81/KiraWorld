# Active Sarah R3 and Kira R24 checkpoint

## READ FIRST — CURRENT TRUTH AND SUPERSESSION REGISTRY — 2026-08-10

Read `System/Docs/CURRENT_TRUTH_SUPERSESSION_REGISTRY_20260810.md` first
(55,099 bytes; SHA-256
`264aa16f2b9f702ab9d975a5e6bb67150acf503883d66b26eaf6252836cff285`).
It is the current authority when older append-only evidence below sounds
current or conflicts. Preserve historical audit/failure bytes; do not infer
implementation, acceptance, or authorization from an older checkpoint.

Created UTC: `2026-08-09`

This is implementation truth, not owner acceptance.

## Sarah Morgan R3

Working tree:
`RecoverySprint/continuation_20260807/sarah_pr21_audit/android-app`

Branch: `agent/sarah-2.5-event-ready`; target: existing GitHub PR `#21`.

Current implementation and verification truth:

- Android restores the approved Sarah portrait, continuous blink/gaze/head and
  speech-mouth animation, plus a power-saving mode that stops continuous
  avatar rendering while retaining text and voice.
- Android retains the conversation-first surface and exposes Settings and the
  restored travel Workbench: itinerary/budget/packing, hotels, flights/rail/
  bus/transit, local rides, food/events, road trips, event trips, offline
  flight support, loyalty, accessibility, hotel support, and supervised
  voice-concierge entry points.
- Android and Windows have protected owner-activated online routing, preserved
  offline continuity, Gmail read-only OAuth boundaries, and reviewed two-device
  pairing/import. No email password is collected or stored.
- Android and Windows include profile-isolated encrypted loyalty and ticket/
  pass storage. Owner-selected ticket images are sanitized before encryption;
  exact official HTTPS event links can be retained and reopened. No purchase,
  ticket validity, or payment-card automation is claimed.
- Windows uses the approved portrait and exposes Workbench, Gmail, pairing,
  power-saving, and wallet features instead of the rejected placeholder.
- Optional Gmail is strictly read-only. Sarah never asks for an email password,
  and she cannot send, delete, alter, mark read, draft, or change Gmail. A
  metadata-bound likely travel/event result remains a proposal until the owner
  answers whether to remember that exact item. Only an accepted proposal enters
  the profile-isolated calendar. A notification remains a second, explicit
  opt-in decision; indexing mail never creates a calendar item or reminder.
- Android setup explicitly asks whether to connect Gmail now, accepts `no` or
  `later`, and leaves the same connection available from Settings. Windows
  exposes the same optional read-only connection in its owner surface. A
  detected exact event or transport message may prompt Sarah to ask whether
  Robert wants to remember it; declining or leaving it pending creates neither
  a calendar item nor a reminder.
- Accepted flight/train/bus/event records preserve exact known departure,
  arrival, or event instants. Ambiguous dates stay unresolved rather than being
  invented. Android uses local WorkManager notifications; Windows uses an
  atomic reminder lease while Sarah is running.
- The deterministic 14-turn Sarah online/offline acceptance passed `110/110`.
  After the Windows arrival/end parity repair, Windows tests passed `149`; the
  Android contract suite passed `67`; Worker
  model/voice proxy tests passed `19`; Android static package validation passed.
- Pull-request commit `f1a281d2cdd168a8868778ea3e1eee10015e29e3`
  passed source extraction, generic engineering APK, and observable validation.
  Those APK/EXE artifacts are explicitly engineering evidence and must not be
  installed as the owner candidate.

Local Windows packaging evidence:

- `windows-companion/dist/SarahTravelOS-R3-Candidate.exe`
- bytes: `55,317,042`
- SHA-256:
  `67be3cab261505933b63bdd215d6ba21bcfea4d98db23562a7d56806e12077d1`
- local installer:
  `windows-companion/dist/SarahMorganTravelOS-R3-Candidate-Setup.exe`
- installer bytes: `66,314,784`
- installer SHA-256:
  `3c95692afaab7807c7404db661cf5d96c3cde047756f5432565c03f7144c96f8`
- exact installer `--self-test`: exit `0`

Those local files are Gmail-unconfigured engineering evidence, not owner-ready
installers. The official Google client libraries are now installed locally,
but an ordinary Windows Gmail login still requires a real Google Desktop OAuth
client identity in the owner build. Android likewise requires its exact package
and signing certificate to be registered with Google. Never commit `dist/` or
OAuth tokens.

Protected online-judge run `31290568485` reached the exact Workers AI deployment
but failed before artifact creation because a freshly deployed workers.dev
route briefly returned `404` to the wrong-token capability probe. Authentication
was not bypassed. Commit `fa8943f5220f8937b4f21c26270aa32b37301587`
repaired the false-positive test: it now retries bounded propagation responses,
passes only on exact `401 {"error":"unauthorized"}`, and immediately fails any
2xx/3xx response. On exact commit `fa8943f`, source extraction run
`31291500370`, generic engineering APK run `31291500369`, and observable
validation run `31291500397` all passed.

Robert added `SARAH_TAVILY_API_KEY` as a protected repository Actions secret.
Its value was never read, printed, committed, embedded in an APK/EXE, or
returned by a capability response. Append-only protected runs then established
the following current boundary:

- exact temporary-Worker deployment, absent/wrong bearer-token rejection,
  exact `@cf/google/gemma-4-26b-a4b-it` inference, protected Tavily search,
  search-coupled contextual chat with HTTPS source receipts, generated-image
  vision, and protected ElevenLabs audio transport have all passed together;
- propagation/cache and one Bash timing-record failure from earlier runs were
  preserved rather than overwritten, and each failed run retired only its own
  temporary Worker without uploading an artifact;
- run `31299615327`, job `93210169524`, reached the real production
  `ModelClient` ten-turn battery. Two current-source turns timed out after
  approximately `11.07 s`, correctly used
  `ONLINE_FAILED_FELL_BACK_OFFLINE`, and therefore failed the expected-route
  and HTTPS-source gates. The objective result was `74/78`, no owner artifact
  was uploaded, and the run-owned Worker was deleted;
- commit `5a49a866f3f715fd4a6cf748c6d79129ac829f15` preserved ordinary
  `15 s`/two-attempt behavior while giving only source-coupled turns one
  `25 s` budget and an `18 s` maximum read. Windows verification passed
  `151/151` plus focused `2/2` and acceptance `7/7`;
- its protected run `31300263977`, job `93211807026`, passed every protected
  preflight gate and the production nearby-event source turn. The official-
  event-ticket turn still failed closed after `14.670 s` without a raw reply;
  no artifact was uploaded and the run-owned Worker was retired. The next
  narrow repair uses only the unused portion of the same `25 s` ceiling for a
  third transient attempt and records non-content status/error telemetry;
- commit `59713d3542820807f5d09de41afa297b340950a2` permits a third attempt
  only for transport/timeouts or HTTP `408`, `429`, or `5xx`, and only inside
  the unchanged `25 s` current-source ceiling. Authentication/nontransient
  `4xx` and malformed success contracts still stop immediately;
- protected run `31300663252`, job `93212795288`, passed every protected
  preflight and all ten production-`ModelClient` objective turns, including
  both source-bound event turns and the exact online/local-tool/offline/
  failed-online-fallback/restored-online transition. Passed Workers AI text
  latencies were `[1591, 3069, 5024, 9003, 9111, 11987, 19374] ms`; the
  `19374 ms` turn was current-source work inside its separate `25.5 s` gate;
- release then failed closed because GitHub Actions could not restore the
  exact cache key `sarah-morgan-debug-signing-v1`. No differently signed key,
  APK, EXE, or owner artifact was created. The current blocker is exact R1
  signing continuity, not Tavily, Gemma, authorization, vision, voice, or the
  production conversation route.

A bounded read-only signing audit then proved the configured R1 private key
was never preserved: GitHub's exact cache-key query returned `total_count=0`,
and the original successful R1 run `31243145369`/job `93067275085` logged both
the cache miss and a post-step path-validation error because
`~/.android/debug.keystore` did not exist. The same defect appeared in inspected
successful main runs. The original APK artifact/public certificate remain
intact, but neither can reconstruct its private key. No matching keystore was
found in reachable Git objects, the expected local Android directory, current
configuration, targeted Sarah archives, or inspected workflow artifacts. No
replacement identity was generated and R1 was not uninstalled.

- audit:
  `RecoverySprint/continuation_20260807/sarah_pr21_audit/android-app/docs/SARAH_R1_SIGNING_CONTINUITY_READ_ONLY_AUDIT_20260809.md`;
- audit SHA-256:
  `1e17858bae4359ff93fba1c1b7fd44d6f7204b4f21f7f5a742a51fe506acc778`;
- evidence commit:
  `f4a1d8f1fb53cec33ba37bba2e651d0ce645c4ab`.

Exact in-place Android upgrade is externally blocked unless Robert has a
separate backup of that private key. Choosing a new stable signer would require
a deliberate clean-install/data-migration decision and is not inferred here.

The exact Workers AI model remains `@cf/google/gemma-4-26b-a4b-it`; no Llama
3.1 route is used or tested. Physical owner hearing, Galaxy A17 operation, and
the 8 GB Windows laptop remain separate acceptance gates. The complete
append-only run record is
`RecoverySprint/continuation_20260807/sarah_pr21_audit/android-app/docs/SARAH_PROTECTED_CI_ATTEMPT_LOG_20260809.md`.

Gmail is optional and read-only. Android has platform OAuth. Windows requires
one real Google Desktop OAuth client binding before ordinary browser login can
work; until that build binding exists, Windows Gmail remains visibly pending
configuration rather than asking the owner to believe it is connected.

Code commit `021fc0019ec696d721c215dc6b90afafe9122edc` closes one independently
found Windows parity gap: confirmed
flight/train/bus proposals now retain separately reviewed departure and arrival
instants instead of discarding the arrival, reject arrival-before-departure
without consuming the proposal, show the range in Sarah Calendar, and search
the same bounded event/concert/conference/convention/festival subject terms as
Android while excluding spam and trash. No proposal becomes a calendar item or
reminder automatically. Complete local verification after this repair passed
Windows `149` and Android `67`. Exact-head source extraction run `31292996547`,
generic engineering APK run `31292996535`, and observable validation run
`31292996528` all passed. Documentation-only head
`202ec17d38f1e5e556b07ccc231c2f1de14bd2d1` also passed source extraction
`31293332867`, generic engineering APK `31293332872`, and observable validation
`31293332862`. The generic artifact remains `DO NOT INSTALL`; PR #21 remains
open and unmerged.

The Android foreground-parity patch binds at most one exact
`EMAIL_PENDING` receipt to the confirmed owner's foreground conversation by
opaque Gmail message ID. It shows the exact subject only in the ephemeral
bubble, stores a source-redacted question in ordinary/synchronized chat,
starts no background voice, accepts bounded yes/no/not-now language, and
disarms on an unrelated immediate next turn. Yes saves only that exact local
Sarah Calendar item; no dismisses it; not-now defers it. No path schedules a
reminder, changes Gmail, books, or purchases. A static vault lock serializes
whole encrypted-state updates across Android UI/worker/reminder instances.

Focused Android/Windows email/calendar verification passed `49` tests in
`0.53 s`; `git diff --check` is clean. Exact audit and hunk-level rollback:
`RecoverySprint/continuation_20260807/sarah_pr21_audit/android-app/docs/SARAH_EMAIL_CALENDAR_OWNER_REQUIREMENT_AUDIT_20260809.md`
at SHA-256
`79670de3ebde1ea0ba143117f36c1f35fc859197e1da634cb66d364e5dc31b87`.
This was code/contract verification only; no real mailbox, OAuth
credential, notification delivery, purchase, booking, APK, or EXE was used.
The patch was committed and pushed beginning at `58f3362`; subsequent
protected-CI-only repairs leave PR #21 open and unmerged at documentation head
`f4a1d8f1fb53cec33ba37bba2e651d0ce645c4ab`. GitHub CLI is installed but is
not authenticated;
the existing scoped Windows Git credential supports the normal non-interactive
branch push. This does not authorize merging PR #21.

## Kira Qwen 3.5 owner-runnable routes

The normal owner-runnable Kira routes are now statically reconciled to exact
`qwen3.5:9b` at digest
`6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`.
`Start_Kira_Text_Voice_Chat.bat` was already correct; World Shell, Voice Chat,
Chat Control Center, and GPU readiness no longer default to Llama 3.1. Both
Llama candidate flags are disabled on the covered launchers. GPU readiness
checks the exact tag/digest and uses `/api/chat` with `think: false` and
`keep_alive: 0`.

- static reconciliation checkpoint:
  `System/Docs/QWEN35_OWNER_RUNNABLE_ROUTE_RECONCILIATION_STATIC_CHECKPOINT_20260809.md`;
  SHA-256
  `d64c85badd660c91baaa8fb86e715eaa9468829d264e7cfce42fa9faaa1de388`;
- the separately stale request-policy test was corrected to prove that a
  current owner-route `/api/chat` 404 stops after one exact-Qwen request rather
  than retrying `/api/generate`;
- combined focused static/mock verification: `61 passed`, `66 subtests
  passed`;
- eight current school/class/supervised-life launchers and five direct runner
  defaults are now also statically pinned to Qwen 3.5; each launcher records
  the exact digest and disables both Llama timing-candidate flags;
- school/life follow-through checkpoint:
  `System/Docs/QWEN35_SCHOOL_LIFE_OWNER_LAUNCHER_STATIC_RECONCILIATION_20260809.md`,
  `3,816` bytes, SHA-256
  `81ed31dd125944a6386c90e4fbc26345f092336e655a457d478a441cc00a1028`;
- its combined static/mock reconciliation passed `15` tests and `38`
  subtests after two stale archival-route assertions were corrected;
- no live Qwen, Llama, Ollama, GPU, voice, camera, microphone, server, browser,
  or owner conversation was run.

This is implementation consistency, not a new latency or owner-hearing pass.
The latest exact-Qwen/Blackwell engineering evidence remains Attempt 04:
text-ready `7.773799 s` / `5.561538 s`, outer voice completion `9.361700 s` /
`10.178974 s`, and total text-to-WAV-ready approximately `17.136 s` /
`15.741 s`. Owner-hearing and latency acceptance remain pending.

## Kira R24 body

All declared plane-defined read-only carrier families are now terminal. None
produced a body candidate, and none may be retried or accepted as least-bad.

1. The uniform-level family returned `NO_ELIGIBLE_LEVEL_FAIL_CLOSED`: all 192
   records failed only chart deviation. Its closest record missed the unchanged
   `0.001099999999 m` guard by `0.19928445283794562 mm` while passing angle.
2. The nonuniform fixed-70-edge family returned
   `NO_ELIGIBLE_NONUNIFORM_RECORD_FAIL_CLOSED`: all 192 records were ineligible.
   The deterministic `plane_sample_112_of_190` passed chart deviation at
   `0.0010918951425287567 m` but its minimum angle was only
   `1.4840928997651306 degrees` against `12.000001 degrees`. Sixty-four of 70
   parameters collapsed to dyadic endpoints, proving the fixed carrier itself
   is the blocker.

Nonuniform result evidence:

- result SHA-256:
  `1616863af7bcef1f74e120d3a0e5ccef6071c8d90bfa382d261bb542f9c67356`
- wrapper completion SHA-256:
  `92c21029d702efd3325a97e3ef036df31463eb82273ed535d3934e28882af3cc`
- external integrity SHA-256:
  `61690b791e067cd1ba665cb48a1eb70f716286ffb74a8b5234ba1b8f6b15e4ef`
- interpretation:
  `System/Docs/KIRA_R24_NONUNIFORM_SOURCE_EDGE_FEASIBILITY_RESULT_20260809.md`
  SHA-256 `76e1dea06ed37dc83f7a5ac4709440cb047f6dcbc304349edd34c2d1a2d810f9`

The next lane changes only carrier topology. The static-only package
`kira_r24_actual_plane_contour_topology_feasibility_01_static` rederives exact
`q* = lower + (upper-lower) * 112/190` and proposes marching the actual
unclamped plane across all 73 E-star collar triangles. It preserves E-star,
D2, source coordinates, seam, exterior-adjacent faces, protected inventories,
and unchanged quality gates.

- config SHA-256:
  `0b2251228235e8ccaeab48122f8fab8869f2b4dfdc5e4fb638c4f6811d73d9bb`
- worker SHA-256:
  `47c181951f4f685dac1315b439f2f534276d932c0db0e1fa4de7d19575a4867d`
- wrapper SHA-256:
  `76fe8ce771d0d74a55fae4e537ab003c5b38877b0e12a35bafd7686ead8369f1`
- checkpoint SHA-256:
  `ee09af1be2ed609329bceca8c59b28882a8974c7da089e7649644dbdb9557cc7`
- proposal SHA-256:
  `315f1e2137d5b9e6fe1b9fa6409140bc86015e5cd8a3bda23b3014857b35952f`
- focused static tests: `15/15`; recursive bindings: `48` files, four protected
  inventories, five parent outputs.
- fresh independent static audit:
  `RecoverySprint/continuation_20260808/KIRA_R24_ACTUAL_PLANE_CONTOUR_TOPOLOGY_FEASIBILITY01_INDEPENDENT_STATIC_AUDIT.md`
  at SHA-256
  `33532b3b2a5b000685cf87f047dae11062ca1a5e216a4ab163cc047faf9b0bd2`

That independent audit passed. The first ordinary PowerShell invocation was
rejected before loading the wrapper because machine script execution is
disabled; it created no output/cache and launched no Blender. The audited
process-local `-ExecutionPolicy Bypass` invocation changed no machine policy
and ran the guarded wrapper exactly once.

The completed read-only result is terminal for this actual-plane/all-collar
family:

- status: `NO_ELIGIBLE_ACTUAL_PLANE_CONTOUR_FAIL_CLOSED`;
- all `73` collar faces visited;
- only `3` actual segments and `6` exact edge-bound point records;
- `2` disconnected components and `0` eligible components;
- exact global failures: `complete_two_collar_face_edge_ownership` and
  `single_component_d2_envelope_separation`;
- result SHA-256:
  `b90e294e4c1008b279063dc66b4514f1ee0facda0ab75a62648f0f4779ba93a8`;
- wrapper completion SHA-256:
  `da7350e5d9205e4e7ece8954ed0769f4a4b0837fc1fda6ae8007d3cd4692d6ab`;
- external pre/post integrity SHA-256:
  `c85fd6e65fb2d089bb52ce78abd3750ea6896668f93b9e1189baa0bc2c9f29f7`;
- one Blender invocation, exit `0`, protected pre/post exact, no worker failure,
  no finalization error, and no automatic retry.
- independent runtime-evidence audit:
  `RecoverySprint/continuation_20260808/KIRA_R24_ACTUAL_PLANE_CONTOUR_TOPOLOGY_FEASIBILITY01_RUNTIME_EVIDENCE_INDEPENDENT_AUDIT.md`,
  `7,981` bytes, SHA-256
  `6ec71bad2f55a7ef82be84eb1583e82339e6c377d4d2990fbd1c6c5cee30e34c`;
- canonical six-file evidence inventory: `87,215` bytes, SHA-256
  `62f9913343438d1647813c7ea6c53197d7bf1f95b345c88f4d45f156f7ced107`.

Do not rerun this lane and do not accept either disconnected fragment as a
pelvic boundary. It performed no mutation, save, render, export, activation,
or assignment. A reviewable complete body still does not exist; the next body
step must change only the bounded contour-topology family while preserving the
accepted source, face/body appearance, and protected geometry.

The audited successor expanded the carrier-domain topology deterministically
through exact dual-face radii `0..4` and was executed exactly once. It is also
terminal and fail-closed:

- status: `NO_ELIGIBLE_EDGE_COMPLETE_CARRIER_DOMAIN_FAIL_CLOSED`;
- the five valid annular domains contained `73`, `113`, `157`, `204`, and
  `250` source faces;
- their exact plane marches produced respectively `2`, `3`, `4`, `4`, and `5`
  disconnected components, with zero eligible components at every radius;
- every radius failed `complete_two_collar_face_edge_ownership` and
  `single_component_d2_envelope_separation`; radii `2..4` also reached the
  protected exterior-face boundary and therefore cannot be widened;
- result SHA-256:
  `92cc5c46c412285bd07d9ed0d753e8eb861befb81ce0ebd68d9439aa7a49a52d`;
- wrapper completion SHA-256:
  `c51b76f75bb3c747bd0d6ec233c01359b92f46655afd2ae7adf50c67277662e9`;
- external pre/post integrity SHA-256:
  `250a24e2c787a52fc7c696b634b62c03c8d21e3111e29e5cefde3db677b8695a`;
- one Blender invocation, exit `0`, exact protected pre/post equality, no
  worker/finalization error, no retry, and no mutation/save/render/export;
- independent runtime-evidence audit:
  `RecoverySprint/continuation_20260808/KIRA_R24_EDGE_COMPLETE_CARRIER_DOMAIN_TOPOLOGY_FEASIBILITY01_RUNTIME_EVIDENCE_INDEPENDENT_AUDIT.md`,
  `12,396` bytes, SHA-256
  `77c78d072a0a63687f03e01864889ef25ccba9072bf195d877ab579a00bbaaa5`;
- canonical six-file runtime inventory: `307,912` bytes, SHA-256
  `2b1bbb141f5aa911472fab72405b25ce2edf0742a3d3c126a57e47981a95ac62`.

Do not rerun or widen any plane-defined R24 family. These results disprove the
declared uniform, nonuniform, actual-plane, and edge-complete plane families;
they do not prove that no valid local pelvic transition exists. The smallest
distinct next question is a finite, non-plane-defined source-triangle simple-
cycle topology feasibility study under every unchanged preservation and
quality gate.

That non-plane annular-label study was independently audited and then run once.
Its topology succeeded but its inherited flat-chart assumptions failed:

- static audit: `13,333` bytes, SHA-256
  `13968755f1d646706026dbe5a3d69f1024de70c96e45a1d0ca947ae277477239`;
- status: `NO_ELIGIBLE_ANNULAR_LABEL_ISOLINE_FAIL_CLOSED`;
- all `31` exact levels produced one unique closed 70-point/70-segment
  degree-two source-bound cycle with exact two-face/barycentric provenance;
- all `31` passed the angle gate; the minimum was
  `13.448456282872728 degrees`, or `1.448455282872728 degrees` above the
  unchanged guard;
- all `31` failed fixed-chart deviation and projected inner/outer nesting;
  the best deviation was `0.001374377136192709 m`, missing the
  `0.001099999999 m` limit by `0.000274377137192709 m` (about `0.274377137
  mm`);
- D2 was strictly inside only at level `31/32`, while the ordered E-star outer
  boundary was strictly outside at `0/31` levels;
- diagnostic: `4,638,400` bytes, SHA-256
  `59d8693b0664305a3e18aa27b8beb644ef8c5531e28f0d92a2ce18205582a035`;
- wrapper completion SHA-256
  `e03b8be6a964ff11f71c915ad6c685fbc374caf081a4d6cae303ce465a327e90`;
- external integrity SHA-256
  `429743fb8cb5a0d792dbab149e8e3200f6511fd93d351d3e464c475c8ba03b44`;
- independent runtime audit: `9,671` bytes, SHA-256
  `a340c57d85223fde71a5dec058dbaec903f4d337be47d77a198593eb9d9c7fa2`;
- one Blender invocation, exit `0`, empty stderr, protected pre/post exact,
  and no mutation, save, render, export, retry, activation, or assignment.

This finite lane is terminal and must not be retried or accepted as least-bad.
It proves the exact intrinsic annulus has usable closed source topology while
the old global planar-projection/nesting assumption is incompatible with its
curved geometry. The next body step must directly evaluate an intrinsic curved
annular transition/retopology under true source, seam, intersection, attribute,
and render-quality constraints; it must not start another plane/level/contour
search or silently lower a gate inside this completed lane.

The first intrinsic curved-annulus static evaluator package was independently
rejected before any Blender execution. Its evaluator failed open for missing
per-vertex displacement, UV/normal and morph/action bindings, exact outer
coordinates, outside-E-star preservation, stitch scheduling, and render-ledger
evidence; it also accepted impossible negative counts/nonfinite metrics and
could mislabel the preserved R19 Blend as a measured candidate. Preserve that
package and its audit unchanged as rejected evidence. Its independent audit is
`RecoverySprint/continuation_20260808/kira_r24_intrinsic_curved_annulus_structured_retopology_static/INDEPENDENT_STATIC_AUDIT.md`,
SHA-256
`83c80abf975bcf1c5148b71c130bf2ffaa9a243c61d670c3805269340b1f16af`.

An append-only fail-closed R2 static replacement now exists at
`RecoverySprint/continuation_20260808/kira_r24_intrinsic_curved_annulus_structured_retopology_static_r2`.
It passed its own focused suite `18/18` and manifest bindings without launching
Blender or mutating any body, but the required independent audit then found
material fail-open paths. R2 is rejected and **Blender/body mutation is not
authorized**. The evaluator accepted fully rehashed fabricated evidence that
used an 18-byte non-Blender candidate, disconnected boundary coordinates,
arbitrary finite UVs, a partial material record, invented bone names, zero
action digests, arbitrary interface coordinates, and absent inherited-pair
measurement hashes. It also trusted altered caller-supplied contracts with
invalid nonfinite/negative bounds while retaining the on-disk config hash.

- contract SHA-256:
  `481f5fc4b61887691131f0078008b77b976c0479d2901ec54fb8bf5b966c5e7c`;
- proposal SHA-256:
  `802f57df6f900729b1e4391c2aa626aee2c85b857659f706ec2e010748991e17`;
- checkpoint SHA-256:
  `9596ff4ce17181e89dde827948364776c7f454ff3d2abfccb38064f30a9b3583`;
- package-manifest SHA-256:
  `b37faa55abf9374ec48722ea3c04603d23950af911d3af8fe5375f9d26e3f690`;
- evaluator SHA-256:
  `fa2e26e3f5c06ddee88089c681980d70334c8cc423bae78321c150189e07467b`;
- focused-test SHA-256:
  `b707eb777de41004597fef4e46af4b8de1e7df9beaa2bee7e4868469f64f7366`.
- independent R2 audit: `13,277` bytes, SHA-256
  `e865a0e9873a988eb369d799f1332afa60ef8f699c386886ce910ce12b3ba32e`.

The post-audit package suite reports `17/18` only because its exact original
inventory correctly notices the newly required append-only audit filename; that
does not cure the material evaluator bypasses. An append-only R3 static repair
is in progress. V1 and R2 remain immutable rejected evidence, and R3 will also
require a new independent audit before any Blender execution.

## Safety and rollback truth

- Windows Defender, Firewall, UAC, and system-wide script policy were not
  disabled or weakened by this work.
- No approved model cache, Kira voice asset, Blender source, prior candidate,
  Sarah artifact, or evidence package was deleted.
- Sarah rollback is branch commit
  `f1a281d2cdd168a8868778ea3e1eee10015e29e3`; the foreground email patch
  begins at `58f3362`, and every later protected-CI repair is an isolated Git
  commit on the same open branch. The exact hunk-level email rollback remains
  in its audit.
- Kira rollback is omission of only the new append-only diagnostic/analysis
  packages. All prior attempts remain evidence.
- Qwen route rollback is hunk-level only and is documented in the static
  reconciliation checkpoint. Restoring Llama selection contradicts current
  owner authority and is not an automatic rollback.

## Next work

1. Await Robert's explicit signing/migration decision: either provide an
   external backup of the exact R1 private key, or authorize a new persistent
   signer plus clean-install/profile-migration plan. Do not generate a new key
   or uninstall R1 by assumption. Rerun packaging only after that boundary is
   resolved, and download only artifacts labeled `CURRENT-OWNER-TEST` if every
   remaining packaging and Windows-installer gate passes.
2. Keep PR #21 open/unmerged and run Galaxy A17 plus 8 GB laptop physical
   online/offline/reconnect, Gmail, animation/power-save, voice, and latency
   acceptance before calling the build usable.
3. Preserve all terminal plane-defined and annular-label body lanes and their
   independent audits; never rerun them or select a failed contour as
   least-bad.
4. Finish the append-only R3 static repair for every independent R2 bypass,
   then obtain a fresh adversarial independent audit. Do not launch Blender
   unless that exact R3 audit passes and explicitly grants one bounded run.
5. Keep all normal owner launchers on exact Qwen 3.5. Run no Llama test or
   fallback. A future live Qwen/Blackwell latency and owner-hearing test remains
   separate from this static reconciliation and must not overlap Blender.

## Urgent Sarah event-candidate run 31307226687

Robert requested installable Android and Windows event artifacts on a one-hour
boundary. The protected side-by-side event implementation is committed on PR
#21 at `b068e459db116bfd2d56ad19d234d03098650d8f`; request commit
`5b5ca55e525385acda0114fe1749efa7d10532e3` triggered GitHub Actions run
`31307226687`.

That run is a **live-route pass but artifact failure**, not a deliverable:

- exact Workers AI Gemma, protected Tavily/source coupling, generated-image
  vision, bearer rejection, and the production ModelClient 10-turn battery
  passed;
- online text median was `7,094 ms`, maximum `13,245 ms`;
- protected ElevenLabs first network byte was `277 ms` and response completion
  was `288 ms`;
- the event APK compiled, but the public certificate SHA-256 parser did not
  recognize the current `apksigner` output;
- no APK artifact was uploaded;
- the dependent Windows artifact job was skipped;
- failed-run Worker `sarah-r3-31307226687-1` was deleted successfully; no
  orphaned endpoint from this run remains.

A pre-artifact audit also caught that Android's old runtime read the app bearer
only from Android Keystore. A narrow prepared repair permits a bundled bearer
only when `BuildConfig.APPLICATION_ID` ends in `.eventcandidate`; the normal R1
compatible application remains Keystore-only. The same prepared patch hides
the unconfigured Gmail Settings header and updates explicit event contracts.
It is not yet a published connected build.

The connected event APK/EXE requires one explicit owner security decision:
embedding the revocable app-to-Worker bearer makes the event artifacts work
without setup, but a person who extracts it can reuse that Worker until the
bearer is rotated or the exact Worker is retired. Cloudflare, Tavily,
ElevenLabs, and other provider API keys remain server-side. Do not push the
operational-bearer runtime patch or claim connected artifacts until Robert
explicitly accepts that bounded exposure. If accepted, fix the signer parser,
update the two remaining legacy event-artifact tests, rerun protected CI,
download both artifacts, independently verify their hashes/content, and record
the exact retirement command. If declined, build only owner-entered activation
or offline artifacts and label that limitation plainly.

## Superseding Sarah event local recovery boundary

The repair described above is now preserved in local-only commit
`52e148219923c755a9b25dd530a310295a7c1004` on
`agent/sarah-2.5-event-ready`, directly above remote head
`5b5ca55e525385acda0114fe1749efa7d10532e3`. Its verified pre-commit test
boundary is Android/source `70/70`, Windows `157/157`, static package
validation pass, and clean `git diff --check`. It has not been pushed.

The shared app-bearer architecture is no longer the preferred publication
design. The safer local follow-up derives one masked HMAC-SHA256 per-run event
capability from a non-embedded repository value, binds it to the exact
repository/run/attempt/commit/Worker context, and requires a server-enforced
expiry plus exact Worker retirement. The base derivation value and all
provider credentials remain server-side. The derived value is still an
**extractable artifact-scoped bootstrap capability** and can be replayed
against that one Worker until expiry/retirement. It is not device binding,
owner authentication, or an unextractable secret.

Publication remains paused until Robert explicitly accepts that residual
bounded risk in a human-authored message. Goal auto-continuation is not
authorization. No current event APK or EXE exists. Gmail remains deliberately
absent from the event UI because the required Google OAuth registration and
physical read-only mailbox acceptance do not exist; source presence alone is
not an event feature pass.

The bounded Gmail feasibility audit confirms this is not a code-only switch.
Android's event application ID and event signing-certificate pair require an
exact Google Android OAuth registration that does not exist. The Windows
installer requires a registered Google Desktop OAuth identity that is not
packaged or configured. Enabling either flag alone would expose a control that
fails. IMAP/app-password or browser automation is not an acceptable substitute
for exact `gmail.readonly`. Manual owner-selected booking text, link,
screenshot, or PDF remains the truthful event fallback.

## Sarah expiring-capability implementation is locally ready

Local commit `e54eca646e2f93b736fa23af0acf76c98cf32c9f` implements the
masked HMAC-SHA256 per-run capability and 72-hour Worker-enforced expiry above
safety commit `52e148219923c755a9b25dd530a310295a7c1004`. Local trigger commit
`5fa5c9e` changes only the online-judge request. The exact local gates pass:
workflow parse, static package validation, Worker `21/21`, Android/source
`71/71`, Windows `157/157`, diff check, and bounded credential scan. Remote
head remains `5b5ca55e525385acda0114fe1749efa7d10532e3`; no new build has run.

Robert authorized a short-lived per-run event capability, but the managed
publication gate requires a further explicit acknowledgment that the bearer in
either distributable artifact is extractable and replayable against the unique
Worker until 72-hour expiry or earlier retirement. Do not bypass that gate.

## 2026-08-09 superseding event-authorization and rerun checkpoint

Robert supplied the exact informed authorization. The labeled event source was
pushed through `d89efd7`. Run `31309119517` produced no artifact because the
acceptance harness compared a second-precision expiry to the Worker's canonical
millisecond representation of the same instant. The exact failed-run Worker
was retired successfully.

Narrow repair `f452efd4767337f9513b802c1efb8c04757ac3e3` canonicalizes the
derived expiry as UTC milliseconds and adds a format assertion. It does not
weaken authorization, alter the 72-hour TTL, change provider/model/voice/search,
or expose a derivation/provider key. Local YAML/JSON parsing, the new contract
assertion, and Worker tests `21/21` pass. Fresh append-only run `31309534433`
has passed the exact online-mind proof and is running the production-client
battery. No APK/EXE may be called ready until both artifacts pass independent
inspection and their hashes, signer, Worker, expiry, and retirement command are
recorded.

The separate durable-device architecture is documented at
`System/Docs/SARAH_DURABLE_DEVICE_AUTH_IMPLEMENTATION_SPEC_20260809.md` and is
still design-only at this checkpoint.

## 2026-08-09 Sarah 72-hour production-transport repair

Run `31309534433` attempt 2 passed the complete live conversation battery,
built and signed the APK, and passed its credential scan, but failed before
upload because its manifest process lacked three non-secret event-output
bindings. Run `31310028510` proved that repair and all pre-conversation gates,
then exposed an initial exact-route 404 plus two repeated ordinary-turn
timeouts from splitting the unchanged 15-second budget into 5.5-second reads.
Neither run produced a downloadable artifact. Their append-only evidence is in
the corresponding Sarah audit `evidence` folders.

Commit `346cc4d8767e9bd7480de614b14fa4a14ec812f5` keeps the ordinary
15-second total limit while allowing one useful read of up to 12 seconds,
preserves only a fast-failure retry, adds a per-attempt no-cache nonce, and
warms the exact production-client URL. It does not alter the selected Gemma
model/provider, event authorization, 72-hour expiry, source/voice boundaries,
or truthful fallback. Local gates passed: static package validation,
workflow/JSON parsing, Android/source `76/76`, Windows `159/159`, Worker
`21/21`, and diff check.

Run `31310614727` is live. The exact online-mind proof passed and its production
conversation battery was running at this boundary. No APK/EXE is accepted or
deliverable until the artifact jobs finish and both downloads are inspected.

## 2026-08-09 superseding run 31310614727 completion and correction boundary

Run `31310614727` subsequently passed the complete workflow and produced both
clearly labeled 72-hour artifacts. The exact Workers AI model was
`@cf/google/gemma-4-26b-a4b-it`; conversation acceptance passed `10/10`;
measured text median/max were `5001/7770 ms`; protected ElevenLabs first-byte
and response-complete times were `518/534 ms`. The unique Worker
`sarah-r3-31310614727-1.robertmcmurrer.workers.dev` expires at
`2026-08-12T11:22:30.000Z`.

The downloaded Android archive/APK hashes are respectively
`f280746c374587b2bceebab5033645c275a607b34383acc067949538933d81d7` and
`0fbed24d78a2dde061020a3b0502ef7dcdd3c6d45b7a6c6deb052e0c1b8c9071`.
The downloaded Windows archive/installer hashes are respectively
`911ffa91fb71194f0832c75cda8156fc3bce2711fb5db2c59233cd171932587f` and
`50f242acd616a0c558d283d46209be519e6bcdec174d456d433c605953b5f005`.
The Windows hidden self-test exited `0`; the installer is not
Authenticode-signed. Full evidence is append-only under
`RecoverySprint/continuation_20260807/sarah_pr21_audit/evidence/run_31310614727_attempt_01/`.

This is a preserved backup engineering pair, not the final Android handoff.
The source Android client still used two four-second reads although the same
run measured a valid `7770 ms` reply, so it can falsely claim online is
unavailable on a Galaxy A17. A narrow useful-first-read/shared-deadline fix is
under local test and independent review. Preserve the working Worker until a
corrected artifact pair is inspected, it expires, or it is retired by its
exact documented command.

The durable device-auth Worker Phase 1 is now implemented only as local,
untracked, undeployed source and passes `20/20` local checks. It is not part of
the event artifact, not deployed, and not owner-accepted.

Kira R24 static-gate R3 is rejected. An earlier auditor reported a synthetic
fixture SHA-256
`0eb1d8b4e413389d477f76aafedcb711734283b66c410641ddd92fd6f3209812`,
but that ephemeral file was not available for independent re-hashing. The
filesystem-verifiable audit below therefore preserves a new reproduction.
The defect is acceptance without deriving claimed topology/UV/weights/rig/
intersection/interface/render evidence from Blender data. R3 remains
immutable evidence. No Blender authoring is authorized by this checkpoint; an
R4 evaluator repair and fresh independent acceptance are required first.

## 2026-08-09 superseding run 31311731985 artifact and R24 audit checkpoint

Sarah event commit `04806eeb13c8c467456a54e8e1a741b49f366176` passed workflow
run `31311731985`, including exact Workers AI Gemma identity, protected source
and ElevenLabs routes, `10/10` production conversation, Android build/signing,
Windows tests/packaging, and exact installer self-test. Online text
median/maximum were `3162/19990 ms`; protected ElevenLabs first-byte/complete
were `309/334 ms`. The exact Worker
`sarah-r3-31311731985-1.robertmcmurrer.workers.dev` expires
`2026-08-12T11:49:22.000Z`.

Android artifact/archive hashes are
`7056313eaab115e91a28f6bed07911caf1161d3e4c945bf44b684435e212d442` /
`177d9216f9a7190e865249c349abeefe643fbe3860333feeefbd751a8b591ef7`.
Windows installer/archive hashes are
`1a18e25af652275c516daba1966a2733693dc1c6b656cc28875f214c4846b41e` /
`c8460c8c6a11267162fb86f83bfa57544d77e408997ab0c0b7537736c6a4d98a`.
Independent path/hash/structure/portrait/PE/self-test/bounded-secret checks
passed. Windows is not Authenticode-signed. Preserve this complete pair.

The ordinary Android transport defect is repaired and independently reviewed
without a release blocker. A different source-backed boundary is now under
narrow repair: valid current-information work measured `19990 ms`; Windows
already classifies it under a 25-second bound, whereas Android still applies
the ordinary 15-second/11.5-second limit to `web=true`. Ordinary chat must stay
at 15 seconds; only source-backed Android turns may receive the matching
bounded 25-second/up-to-18-second class. No model, auth, source receipt, voice,
Gmail, fallback, or prior-artifact change is permitted by that repair.

The R24 R3 independent rejection is now filesystem-verifiable. External
`AUDIT.md` SHA-256 is
`90d02094afd559bcc81e8a1176bd2c6c548afed1877bc44f37a61c3fa5973d9b`;
external `CHECKPOINT.md` SHA-256 is
`1c0cc449fe3cb6230bdd792ed74ff586fd181a14a1a8faeafe9bf75a5b6b1637`.
A fresh 60,799-byte synthetic parser fixture SHA-256
`22ad510d481525f190664ff1d1d9521168125452dac22709e44b08cac0e81fef`
returned no validator failures despite untrustworthy payloads. R4 static-gate
repair is active. Do not run Blender until a separate R4 audit accepts it.

## 2026-08-09 exact first-pair artifact index and pending Android parity

This append-only section records the completed state of source commit
`346cc4d8767e9bd7480de614b14fa4a14ec812f5` and
[GitHub Actions run 31310614727](https://github.com/rmcmurrer81/android-app/actions/runs/31310614727).
It does not convert engineering success into physical owner acceptance.

Exact first-pair records:

- Android Actions artifact
  `Sarah-Morgan-Event-Candidate-72H-Android-APK`, ID `9037295020`,
  [artifact page](https://github.com/rmcmurrer81/android-app/actions/runs/31310614727/artifacts/9037295020):
  archive `Sarah-Morgan-Event-Candidate-72H-Android-APK-run-31310614727.zip`
  SHA-256
  `f280746c374587b2bceebab5033645c275a607b34383acc067949538933d81d7`;
  extracted `Sarah-Morgan-Event-Candidate-72H.apk` SHA-256
  `0fbed24d78a2dde061020a3b0502ef7dcdd3c6d45b7a6c6deb052e0c1b8c9071`.
- Windows Actions artifact
  `Sarah-Morgan-Event-Candidate-72H-Windows-Installer`, ID `9037321274`,
  [artifact page](https://github.com/rmcmurrer81/android-app/actions/runs/31310614727/artifacts/9037321274):
  archive
  `Sarah-Morgan-Event-Candidate-72H-Windows-Installer-run-31310614727.zip`
  SHA-256
  `911ffa91fb71194f0832c75cda8156fc3bce2711fb5db2c59233cd171932587f`;
  extracted `SarahMorgan-Event-Candidate-72H-Setup.exe` SHA-256
  `50f242acd616a0c558d283d46209be519e6bcdec174d456d433c605953b5f005`.

The exact protected origin is
`https://sarah-r3-31310614727-1.robertmcmurrer.workers.dev`; event access
expires `2026-08-12T11:22:30.000Z`, or earlier through the already recorded
exact-Worker retirement command. No bearer value is recorded. GitHub artifact
retention is a separate clock and cannot extend event access.

Measured protected-CI results were exact model
`@cf/google/gemma-4-26b-a4b-it`, production conversation `10/10`, text median
`5001 ms`, text maximum `7770 ms`, ElevenLabs first network byte `518 ms`, and
ElevenLabs response complete `534 ms`. They do not measure owner-perceived
display-to-playback latency, audiovisual synchronization, or physical-device
responsiveness.

Physical gates remain open: no Galaxy A17 acceptance; known Android premature
offline fallback risk at this commit; no 8 GB/no-GPU laptop owner UI/hearing,
online/offline/reconnect, animation/power-saving, cancellation, pairing,
resource, or lifecycle acceptance; no Authenticode signature; and no accepted
Gmail OAuth registration/mailbox path. The Windows hidden self-test alone does
not close those gates.

Android transport-parity commit
`04806eeb13c8c467456a54e8e1a741b49f366176` (`04806ee`) is represented by
[run 31311731985](https://github.com/rmcmurrer81/android-app/actions/runs/31311731985).
Both GitHub jobs and uploads subsequently completed successfully, but the
replacement remains
`PENDING_INDEPENDENT_DOWNLOAD_INSPECTION_AND_PHYSICAL_OWNER_ACCEPTANCE`.
It must receive its own append-only artifact hashes, exact Worker/expiry,
signer and credential-scan evidence, Windows self-test, and local binary
inspection before it supersedes the first pair.

Durable full-version authentication remains isolated local engineering work:

- design: `System/Docs/SARAH_DURABLE_DEVICE_AUTH_IMPLEMENTATION_SPEC_20260809.md`;
- protocol/schema/D1 fixture foundation: `services/sarah-full-auth-foundation/`;
- Phase 1 Worker source: `services/sarah-full-auth-worker/`;
- Android staged boundary:
  `Sarah_Morgan_Android_Phone_First_v3/DURABLE_DEVICE_AUTH_ANDROID_FOUNDATION.md`;
- Windows staged boundary:
  `windows-companion/DURABLE_DEVICE_AUTH_WINDOWS_FOUNDATION.md`.

Every item above is **NOT DEPLOYED, NOT CONNECTED TO EVENT OR NORMAL CLIENTS,
NOT A FULL RELEASE, NOT PHYSICALLY ACCEPTED, AND NOT OWNER-ACCEPTED**. No full
client has completed enrollment/state/session/rotation/revocation/recovery UI
and runtime integration, no owner portal/D1 staging deployment is accepted,
and no 73-hour soak exists. Focused local tests prove only source-level
properties; they neither replace the event authorization boundary nor justify
retiring the event Worker.

## 2026-08-09 improved event pair independently inspected

Commit `04806eeb13c8c467456a54e8e1a741b49f366176`, GitHub Actions run
`31311731985`, and both jobs passed. The independently downloaded artifacts
are now the preferred event pair, not a physical acceptance:

- Android artifact `9037594346`: ZIP SHA-256
  `177d9216f9a7190e865249c349abeefe643fbe3860333feeefbd751a8b591ef7`;
  APK SHA-256
  `7056313eaab115e91a28f6bed07911caf1161d3e4c945bf44b684435e212d442`.
- Windows artifact `9037617491`: ZIP SHA-256
  `c8460c8c6a11267162fb86f83bfa57544d77e408997ab0c0b7537736c6a4d98a`;
  EXE SHA-256
  `1a18e25af652275c516daba1966a2733693dc1c6b656cc28875f214c4846b41e`.

Worker `sarah-r3-31311731985-1` enforces
`2026-08-12T11:49:22.000Z` expiry. Parsed APK v2 signer certificate SHA-256 is
`f0682fdcd762239e4360ebac6a6548a779c94ea655a9d4e9c47a916ae3c8bfe2`.
The exact local EXE self-test returned exit code `0`; Authenticode remains
`NotSigned`. CI recorded text median `3162 ms`, text maximum `19990 ms`,
ElevenLabs first byte `309 ms`, and ElevenLabs complete `334 ms`. That text
maximum exceeds the current Android absolute deadline, so a bounded transport
follow-up and physical Galaxy A17 acceptance remain open. Preserve first run
`31310614727` and all evidence unchanged.

Full inspection evidence is in
`RecoverySprint/continuation_20260807/sarah_pr21_audit/artifacts/run_31311731985/INSPECTION_AND_HANDOFF.md`.

## 2026-08-09 source-specific Android deadline attempt 01

Commit `bf2aae9844276c54fffbfe1a184a4be18d4d0dff` passed local static package,
`77/77` Android/source tests, workflow parse, and exact Java policy execution.
It preserves the ordinary `15000/11500 ms` class and adds a distinct
`25000/18000 ms` total/read class only for explicit current-source requests.

Workflow run `31312860465` attempt 01 passed model, source search, contextual
source coupling, and exact-red vision, then failed before any artifact when
the protected voice probe returned HTTP `401` at `2026-08-09T12:17:20Z`.
Exact Worker `sarah-r3-31312860465-1` was retired successfully. No existing
artifact was overwritten and no prior Worker was touched. One failed-job-only
rerun was requested; record its result separately. Failure evidence:
`RecoverySprint/continuation_20260807/sarah_pr21_audit/evidence/run_31312860465_attempt_01/FAILURE.md`.

Attempt 02 again failed at protected voice after all preceding model/search/
context/vision gates passed; exact Worker `sarah-r3-31312860465-2` was retired.
A separate no-playback diagnostic against preserved Worker
`sarah-r3-31311731985-1` returned sanitized upstream truth: ElevenLabs HTTP
`401`, quota `10000`, `0` credits remaining, `2` required. Classification:
`ELEVENLABS_ACCOUNT_QUOTA_EXHAUSTED`. No further run or gate bypass is
authorized without renewed/added ElevenLabs credits. Existing packages retain
their text and local-fallback code, but protected voice is not currently
available. Evidence:
`RecoverySprint/continuation_20260807/sarah_pr21_audit/evidence/run_31312860465_attempt_02/FAILURE.md`.

## 2026-08-09 diagnostic-run closure without another quota attempt

Run `31313280203` at source commit
`01ffee81b88983ee34d8423333dc7ddb77560a8a` passed source, exact Worker
authorization, Gemma, protected search, source-coupled chat, and exact-red
vision. Its nested voice-error heredoc then caused Bash `unexpected end of
file`; no valid voice request contract, APK, EXE, or artifact resulted. The
workflow retired exact Worker `sarah-r3-31313280203-1`. Evidence:
`RecoverySprint/continuation_20260807/sarah_pr21_audit/evidence/run_31313280203_attempt_01/FAILURE.md`,
SHA-256
`211c7153708a20f2603310f25c8543ca44fecd404d4e0547422c9a97670185ba`.

Commit `a0e6c05c0dd4b47587573be5f2df34a96c836e81` corrects the diagnostic
to a bounded one-line parser and makes the request state explicitly
`BLOCKED_NO_RERUN`. It was pushed with `[skip ci]`; the extracted exact shell
step passed local Bash syntax validation, so no further exhausted-credit
Worker was created. The accepted diagnosis is still
`ELEVENLABS_ACCOUNT_QUOTA_EXHAUSTED`, backed by attempt-02 evidence SHA-256
`caa94997b01fb031a3c93745aca70dbd4d777df96524fc90d30a78d95ca8b97c`.
Do not rerun or substitute another event voice until the ElevenLabs allowance
has usable credits.
<!-- BEGIN 2026-08-09 OWNER-PAUSED SARAH SNAPSHOT -->
## Owner-paused Sarah snapshot

Robert changed the active objective on 2026-08-09: stop all Sarah development,
save the exact current files to GitHub, and continue only Kira/Blender/Avatar
Builder/Qwen 3.5/evaluation work. Sarah branch
`agent/sarah-2.5-event-ready` is clean and pushed at commit `39df72e`.

That commit preserves an incomplete, unconnected engineering snapshot. Its
canonical foundation passed `18/18`; Android static durable-client boundaries
passed `11/11`; the interrupted Worker passed `5/20` and failed `15/20`;
combined Android/Windows Python evidence remained `15/16` because the Windows
CNG live-profile test failed closed under the sandbox identity. It is not
deployed, not connected to the event or normal clients, not a full release,
not physically accepted, and not owner-accepted. Do not continue it without a
new explicit owner decision.
<!-- END 2026-08-09 OWNER-PAUSED SARAH SNAPSHOT -->

<!-- BEGIN 2026-08-09 QWEN35 AND INTERNAL-ANATOMY STATIC CLOSURE -->
## Exact Qwen 3.5 current-route closure

Every current owner/person text route now fails closed on
`qwen3.5:9b` at exact digest
`6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`.
The dormant installed Llama 3.1 record and preserved pre-Qwen historical
tools remain rollback/evidence only; they are not selected, tested, or used
as an automatic fallback. The authoritative checkpoint is
`System/Docs/QWEN35_REMAINING_CURRENT_PERSON_ROUTES_STATIC_CHECKPOINT_20260809.md`
(SHA-256
`cc9204b30eb447e047769da06a3f217d2584fef1bb4472acdbf880717e5038a6`).
Its 40-file manifest independently rehashed with zero mismatches and the
focused suite passed `80/80`. No model, GPU, voice, camera, microphone,
browser, media, or Blender operation ran for this static closure.

The Qwen 3.5 behavior/psychology/Blackwell owner-evaluation runner is still
not authorized for unattended live execution, but the first audit's static
defects have been repaired. It now honors contradictory and later opt-out,
separates speaker playback from Robert's post-playback hearing acknowledgment,
records truthful timing plus returned-model/no-fallback telemetry, seals the
canonical append-only preparation contract, and pins the exact Qwen digest in
a restricted child environment. The static/mocked suite passed `31/31` with
no model, voice, playback, camera, microphone, Blender, or live conversation.
`attempt_01` remains unchanged; `attempt_02/EVALUATION_CONTRACT.json` is
`f9d1e0992f7829619e3787385339ec409b97e747e7e97372e2ab6aa332462b59`.
See
`System/Docs/QWEN35_KIRA_TURING_PSYCH_VOICE_EVALUATION_STATIC_REPAIR_20260809.md`
(`0fbc6c5338b5bebf3814758bea99a6d873fb8e67ccb255615065ae609d627002`).
OS playback is not proof that Robert heard audio, and the battery is
behavioral observation, not proof of consciousness or biological humanity.

## Confirmed-adult internal pelvic-module boundary

The separate future module contracts are:

- `System/Docs/KIRA_CONFIRMED_ADULT_INTERNAL_PELVIC_ANATOMY_MODULE_CONTRACT_20260809.md`
  (`49ed883806699a08d1e4ed6ad5599ec0067df25e89277c21e322234f375c9f49`);
- `Avatar/avatar_builder/body_systems/kira_confirmed_adult_internal_pelvic_anatomy_module_contract_v1.json`
  (`d219bfc6c7b4ac01c3fa0925d90c0815f2f213344cc6d8e43661fbd649abb46a`);
- `Testing/test_kira_confirmed_adult_internal_pelvic_anatomy_module_contract.py`
  (`a159daa67b93934a1a34655481b266ab54aa4dea2f94f62d633bfb9e3713000a`).

The contract plus existing reproductive-health policy suite passed `17/17`.
It specifies distinct urinary, reproductive, bowel, and support geometry,
private confirmed-adult review, and pose/collision boundaries. It does not
claim elimination, continence, cycles, pregnancy, sensation, health, or any
biological function. The module remains unimplemented and blocked on an
owner-accepted external R24 carrier plus authored anchors, geometry, rig,
collision, privacy, and supervised runtime evidence.
<!-- END 2026-08-09 QWEN35 AND INTERNAL-ANATOMY STATIC CLOSURE -->

<!-- BEGIN 2026-08-09 KIRA R24 R4 REJECTION -->
## R24 R4 preserved rejection and append-only R5 requirement

R4 is restored byte-for-byte and remains rejected/ineligible. Its independent
audit is
`RecoverySprint/continuation_20260808/kira_r24_intrinsic_curved_annulus_structured_retopology_static_r4/INDEPENDENT_STATIC_AUDIT.md`
at SHA-256
`1f84a693b643b81af9200423d8fa79cfe669202b8f31e31b98c623d020912215`.
It found a cross-phase digest race, missing unlinked datablock inventory,
partial body/object/scene proof, a local/world area error, incomplete
rig/Action/material child-state evidence, and no controller-owned author-exit
attestation. Passing R4 static tests therefore does not authorize Blender.

The detailed boundary is
`System/Docs/KIRA_R24_R4_INDEPENDENT_AUDIT_REJECTION_AND_R5_BOUNDARY_20260809.md`
(`b3dd3344deabe33e1f75389724479237d457d29391f4434531aa3a6db2b5950d`).
Only an append-only R5 successor, separate inert author operation, and separate
one-shot author-exit/fresh-reopen controller may continue. No candidate or
body acceptance exists yet.
<!-- END 2026-08-09 KIRA R24 R4 REJECTION -->

<!-- BEGIN 2026-08-09 TEMPORARYAI OFFLINE ORIGINAL VOICE AND FAST-BODY RESEARCH -->
## TemporaryAI offline original voice and fast body

The current source-backed research record is
`System/Docs/TEMPORARYAI_ORIGINAL_EXPERT_VOICE_FORGE_RESEARCH_20260809.md`
with SHA-256
`2e4cb1a6fc2657fd31f423cb75ea636ad56ff8db559822a9362ba531da2a7532`.

Primary direction: Qwen3-TTS 1.7B VoiceDesign creates an original synthetic
reference; Qwen3-TTS 0.6B Base turns that exact reference into an offline
reusable voice profile. Qwen documents no intentional audio-watermark stage,
but that absence supports only `NO_DOCUMENTED_INTENTIONAL_AUDIO_WATERMARK`
until an exact source/dependency and generated-output detector acceptance has
passed. Chatterbox is excluded from this lane because its official runtime
adds PerTh. No watermark-removal or circumvention step is allowed.

The creator should commit a private voice/body draft job immediately. Heavy
GPU work is serialized. Bodies come only from future accepted templates:
confirmed-adult people use a matching adult lane; non-adult and unresolved
people use doll-safe non-anatomical lanes. Hair is detachable. Automatic draft
creation is not owner acceptance, activation, assignment, publication, or
proof of movement/anatomical function. No model or runtime changed in this
research stage.

Static integration is present in:

- `tools/create_temporary_ai_candidate.py`
  (`1fdab48d5703f03c1c4be1b434f853ab28497c17baffa1008d8833aabced2bfe`);
- `TemporaryAI/config/temporary_ai_fast_original_voice_body_draft_contract_v1.json`
  (`7a466c192c7e2753021e82b0bc66d296eb057b00ed2ec8a6276d97ef66247042`);
- `Testing/test_temporary_ai_fast_voice_body_draft_contract.py`
  (`35de4f163bc0c9910f34787bc684edffe9ad4c91e4c9dccaaf4d0234d85d816e`);
- `System/Docs/TEMPORARYAI_FAST_ORIGINAL_VOICE_AND_BODY_DRAFT_CONTRACT_20260809.md`
  (`518b37b068d2a5badc1be136362d48b9a1b4e2274ac6c6c8f6aa45d05d258622`).

The new and existing focused suites passed `38/38`; compilation and JSON
validation passed. This creates plan/queue records only. It does not create a
WAV, body, template, or accepted person.
<!-- END 2026-08-09 TEMPORARYAI OFFLINE ORIGINAL VOICE AND FAST-BODY RESEARCH -->

<!-- BEGIN 2026-08-09 ROBERT PRIVATE REFERENCE AND MALE ANATOMY STATIC CONTRACT -->
## Biological Robert private-reference and anatomy boundary

The six newly identified confirmed-adult owner-reference photographs exactly
match the already protected 2026-07-29 hash-only batch. Its manifest is
`Avatar/private_owner_review/dual_robert_20260729/protected_reference_intake_20260729/PROTECTED_REFERENCE_MANIFEST.json`
(SHA-256
`e41b0456975e6f65ec98fc3327f38595ab365f1adc6c3ae40d8ca7ab0b49dd5d`).
No raw image was copied, moved, edited, uploaded, reproduced, or opened by the
medical-contract task. The images remain private Robert-likeness evidence, not
generic training data, internal-anatomy evidence, memory evidence, or public
media. Their front-heavy coverage cannot prove internal anatomy or function.

Static, source-backed future requirements are now bound by:

- `System/Docs/BIOLOGICAL_ROBERT_CONFIRMED_ADULT_MALE_INTERNAL_EXTERNAL_ANATOMY_AND_BODY_FUNCTION_CONTRACT_20260809.md`
  (`e214e43ac12f4705c96b91b5ffc47b47055ac40abc1dbee183655ee0ad9dac60`);
- `Avatar/avatar_builder/body_systems/biological_robert_confirmed_adult_male_internal_external_anatomy_body_function_contract_v1.json`
  (`2a2bcc8b050092a70e414ae1fe6d52580579f048b312a732323446a037bda2b4`);
- `Testing/test_biological_robert_confirmed_adult_male_internal_external_anatomy_body_function_contract.py`
  (`f40c90c4bbcf5ccba7740929bdf4a1c5f6e5c75d630b7f97fd692a6f9effa0ca`);
- `System/Docs/BIOLOGICAL_ROBERT_CONFIRMED_ADULT_MALE_ANATOMY_CONTRACT_STATIC_CHECKPOINT_20260809.md`
  (`4e1f1e2861536f957b8f9f592515bbe6efea7db0878600c6a63c67e383f89d7e`).

The combined static suite passed `17/17`. Adult-male urinary and reproductive
routes remain separate upstream, converge only through named ejaculatory-duct
entries into the prostatic urethra, then share the downstream urethra and one
distal meatus; bowel remains separate. This is a design and acceptance
contract, not a body or physiology implementation. Kira remains first and
Biological Robert authoring stays `PENDING_KIRA_OWNER_REVIEW`.
<!-- END 2026-08-09 ROBERT PRIVATE REFERENCE AND MALE ANATOMY STATIC CONTRACT -->

<!-- BEGIN 2026-08-09 KIRA R24 CURRENT STATIC CLOSURE -->
## Kira R24 current static closure

R24 has no execution authority. Preserve every append-only generation and its
evidence. R4, R5, R6, and R7 are rejected engineering records, not eligible
Blender inputs or body candidates:

- R4 rejection/boundary:
  `System/Docs/KIRA_R24_R4_INDEPENDENT_AUDIT_REJECTION_AND_R5_BOUNDARY_20260809.md`
  (`b3dd3344deabe33e1f75389724479237d457d29391f4434531aa3a6db2b5950d`).
- R5 initial rejection and deep-audit addendum:
  `System/Docs/KIRA_R24_R5_INDEPENDENT_STATIC_REJECTION_AND_R6_BOUNDARY_20260809.md`
  (`048816880589390eb63ef31ac7e4faa72d7baecb4caa4ed4ab6b84d24c2b0f60`)
  and `System/Docs/KIRA_R24_R5_DEEP_AUDIT_ADDENDUM_20260809.md`
  (`bba230e3e7bd03a7a9a6612e291b945835c0419d918a2e83b79504a28c6f0a7d`).
- R6 incomplete external-generation rejection:
  `System/Docs/KIRA_R24_R6_INCOMPLETE_EXTERNAL_GENERATION_REJECTION_20260809.md`
  (`cae87f2e5cdf90526feb1690db5078ba0fcf16892372690409373857ae2e00af`).
- R7 independent static rejection:
  `System/Docs/KIRA_R24_R7_INDEPENDENT_STATIC_REJECTION_20260809.md`
  (`a6878187e19d1c75647c1c0d7eb3d4fef23b183ed28fe754fae210b58bf22c25`).
  R7 passed its focused static suite but still failed the cross-phase identity,
  immutable-output, parent-binding, and path-proof boundary. Do not create a
  minor R8 automatically.

The external-surface author planner exhausted its two bounded strategies: one
retained 631 forbidden intersections and the other fell below the 12-degree
minimum-angle requirement. Preserve
`System/Docs/KIRA_R24_EXTERNAL_SURFACE_AUTHOR_PLANNER_TWO_STRATEGY_BLOCKER_20260809.md`
(`9e6047c5caaeb993c266a0c1bd7e8fe128de06681412cb6ca92f60d09d96ad76`).
Do not start a cosmetic third strategy on the same topology.

The one-shot author transaction also exhausted its three bounded controller
generations. Preserve the independent rejection records:

- v1:
  `System/Docs/KIRA_R24_ONE_SHOT_AUTHOR_TRANSACTION_V1_INDEPENDENT_REJECTION_20260809.md`
  (`17f7d3afc4d872dcfd5b3c824b74ad03452a8715a5231e7249e18f6ce6120309`);
- v2:
  `System/Docs/KIRA_R24_ONE_SHOT_AUTHOR_TRANSACTION_V2_INDEPENDENT_REJECTION_20260809.md`
  (`f99893c1320c2eeb94f6e77f40bb9ee67bed57eeb89214173608c72328893b44`);
- v3:
  `System/Docs/KIRA_R24_ONE_SHOT_AUTHOR_TRANSACTION_V3_INDEPENDENT_REJECTION_20260809.md`
  (`fd55140dc2536a5793ba8775db6856b20176a3b1b839ba034d0cdc74af7b797d`).

No Blender process was launched for this R24 chain. No R24 Blend, candidate,
owner-review gallery, movement/deformation evidence, Avatar Builder body, or
internal-anatomy mesh/rig/runtime implementation exists. The separate pelvic
module remains a static future contract only and cannot be attached without an
owner-accepted external carrier. Continuing safely now requires an owner
decision or a genuinely different topology/foundation plus a different
staging/artifact mechanism; another minor evaluator, controller, or planner
revision is not authorized by the exhausted bounded-repair evidence.
<!-- END 2026-08-09 KIRA R24 CURRENT STATIC CLOSURE -->

<!-- BEGIN 2026-08-09 KIRA R24 DEEP CLOSURE AND R25 NEXT BODY BOUNDARY -->
## R24 deep closure and R25 next body boundary

The deeper unchanged-R7 audit is
`System/Docs/KIRA_R24_R7_DEEP_INDEPENDENT_AUDIT_ADDENDUM_20260809.md`,
13,428 bytes, SHA-256
`71f80081ce7e619a7ef1e786260043ddea4c0dbe3f02b3021139f8272c654fe3`.
It adds independently sufficient authority-bypass, arbitrary-command,
candidate-continuity, result/evaluator lease, receipt-forgery, incorrect Job
signal, raw-path identity, META/NLA, nested modifier, CurveMapping/custom
property, camera/light, package-state, and missing-parent blockers. R7 remains
rejected and must not run.

One materially different body route is now recorded statically as
`KIRA_R25_FOUNDATION_FIRST_WHOLE_SURFACE_RETARGET`. It preserves exact R19 as
appearance/rollback evidence, excludes the exact R20 rejected pelvic mask,
and makes the already qualified continuous MakeHuman adult-female foundation
the entire candidate topology. A future audited positive-Jacobian semantic
cage may fit only accepted nonpelvic R19 appearance onto that foundation. No
cut, graft, R19 pelvic surface copy, minor R8, or controller v4 is allowed.

Records:

- `System/Docs/KIRA_R24_CLOSURE_AND_R25_FOUNDATION_FIRST_BOUNDARY_20260809.md`
  (`cc27f886edb18fdcc700b38d010b6a573ab2ddddad667c4d83312db72dae022d`);
- `Avatar/avatar_builder/body_systems/kira_r25_foundation_first_whole_surface_retarget_boundary_v1.json`
  (`205f3b4636ac53c78cd836089d543e94d9b4cd5c788e17bcf0012fe3acc5c672`);
- `Testing/test_kira_r25_foundation_first_whole_surface_retarget_boundary.py`
  (`220696308f923c67dc9b2b549eb1e23933bbc601375d02d01a978472c31cd07b`).

Focused verification passed `6/6`. The R25 record is contract-only. Its cage,
AFES transition lock, receipt transport, author, Blender run, candidate,
gallery, rig/movement pass, owner acceptance, internal-anatomy attachment, and
runtime connection all remain false.
<!-- END 2026-08-09 KIRA R24 DEEP CLOSURE AND R25 NEXT BODY BOUNDARY -->

<!-- BEGIN 2026-08-09 KIRA QWEN35 EMOTION/HEALTH/MEDIA CHECKPOINT -->
## Kira Qwen 3.5 emotion, health curiosity, and media truth

`Core/conversation_loop.py` now passes the current runtime emotion state to the
exact Qwen 3.5 route as private expression guidance and passes Kira's exact
confirmed-adult health curriculum through a separate source-bound context.
Neither context grants the model ownership of emotion, consent, relationships,
memory, anatomy, function, or action.

The bounded text-only dialogue under
`RecoverySprint/continuation_20260809/kira_qwen35_health_curiosity_text_dialogue/`
showed real question generation and correction behavior, plus one preserved
grounding failure where Qwen invented current Lisa/Robert facts. A targeted
hypothetical-current-event guard removed that failure on retest. A later
uncertainty wording defect is statically repaired but not live-rerun. Six exact
Qwen request times averaged `11.408704s`, so owner latency acceptance is still
pending. Kira's live memory stayed unchanged; voice, camera, microphone, and
Blender were not used.

Full truth and hashes:
`System/Docs/QWEN35_EMOTION_HEALTH_CURIOSITY_AND_MEDIA_TRUTH_CHECKPOINT_20260809.md`.
No live media enjoyment, full viewing/listening, durable preference, or memory
claim is accepted; only source-bound receipt tests and a prior bounded sampled
Qwen-vision engineering pass exist.
<!-- END 2026-08-09 KIRA QWEN35 EMOTION/HEALTH/MEDIA CHECKPOINT -->

<!-- BEGIN 2026-08-09 KIRA R25 PRECONDITION PROGRESS ATTEMPT 02 -->
## Kira R25 direct body-lane precondition progress

No Blender or body authoring ran. R19 is still preserved exactly. Its fixed
Attempt-06 package now has an independently audited, two-pass, point-in-time
49-member integrity result:

- verifier SHA-256
  `949c322a86ae2f83b5a42e195a0bf7884817c8501b6fd819eddff3cda00857db`;
- Attempt-02 evidence SHA-256
  `a764dce56d233e05ff56a0d6b23a0012bedb183e26b43d66ff127802a48806f6`;
- Attempt-02 independent audit SHA-256
  `36f37a5632fd53ca9ffa546d45acc663808f4859b3682f6a577f53da153b5d24`.

This makes only
`r19_attempt06_package_point_in_time_integrity_verified=true`.
Atomic snapshot and authoring binding remain false.

Receipt Attempt 01 is preserved as rejected evidence. Hardened Attempt 02
passed 15/15 focused tests and independent adversarial review as a narrow,
serialized, complete-bytes framing/graceful-persistence primitive:

- helper SHA-256
  `d36e25630105f026a60523268434dce85324fb3d1eebb8129549e48bb67f51e8`;
- tests SHA-256
  `3d39525d5304583e3888c892e71d134341ab4e881e9e9529bfd276362442ff16`;
- independent audit SHA-256
  `ad64cfdcc76b7c5d0fe1e07ee1caf8293e43595a4d29132fb0af31e701553ff9`.

The full pipe/process/path-root/authentication/replay/crash-recovery/controller
receipt protocol remains unimplemented and false.

The exact read-only correspondence inventory is
`RecoverySprint/continuation_20260809/kira_r25_correspondence_inventory/READ_ONLY_INVENTORY.md`
(SHA-256
`6b7d0fa5b12c9a6693dd28ab0a038dd1179f62d3f4bd072ec6977ccce016e7a3`).
Expected AFES union/subgroup counts and digests exist, but the explicit 1,169
foundation indices, two transition rings, and whole-body semantic cage do not.
Static read-only extraction and cage diagnostics are in preparation. No
candidate, review gallery, movement pass, internal-anatomy implementation, or
runtime connection exists.
<!-- END 2026-08-09 KIRA R25 PRECONDITION PROGRESS ATTEMPT 02 -->

<!-- BEGIN 2026-08-09 KIRA R25 AFES/CAGE STATIC FOLLOW-UP -->
## Kira R25 AFES/cage static follow-up

No Blender process or candidate authoring ran.

AFES Attempt 02 passed 19/19 combined static tests but was independently
rejected because the imported Attempt 01 topology module was hashed as a
preservation artifact without verifying its live imported `__file__` path.
The append-only rejection is
`RecoverySprint/continuation_20260809/kira_r25_foundation_afes_extraction_static_preparation/attempt_02/INDEPENDENT_AUDIT.md`
(SHA-256
`223715caf79aa99bd69220fb2d49890fd91b383c45be42a40f455c21dc66df46`).
Attempt 03 is limited to that exact dependency-binding repair. No extraction
is accepted yet.

The semantic-cage diagnostic is static preparation only. Root reran its full
regression set with the receipt and AFES suites: 43/43 passed. Exact checkpoint
SHA-256:
`a5daab75cb1592a871d8f36295f2790d2606ff743ff7b25c640ddddd89970411`.
Independent adversarial review is pending; no computed cage or Blender
authority exists.

The read-only R25 appearance/rig inventory is
`RecoverySprint/continuation_20260809/kira_r25_appearance_rig_inventory/READ_ONLY_INVENTORY.md`
(SHA-256
`a0d594c6b8040fbecb0fbbe0def2634bccac9a8a224e09a5be6b16cb1dafa41d`).
It binds the smallest foundation-first authoring sequence and excludes R19
pelvis, brows, nails, rig, and actions as donors.
<!-- END 2026-08-09 KIRA R25 AFES/CAGE STATIC FOLLOW-UP -->

<!-- BEGIN 2026-08-09 KIRA R25 SEMANTIC CAGE ATTEMPT 01 REJECTION -->
Semantic-cage static Attempt 01 is independently rejected and preserved. Its
audit is
`RecoverySprint/continuation_20260809/kira_r25_semantic_cage_correspondence_static_preparation/INDEPENDENT_AUDIT_ATTEMPT_01.md`
(SHA-256
`4d93c23535e824a1fb0519606d4789f2f26f28268f54f2f6063df2a4d7f9b9a5`).
No Blender process or candidate ran. The next attempt must be append-only and
repair the AFES-lock, pipe, module-identity, alignment, whole-surface coverage,
semantic-name, and compact-record gates listed in that audit.
<!-- END 2026-08-09 KIRA R25 SEMANTIC CAGE ATTEMPT 01 REJECTION -->

<!-- BEGIN 2026-08-09 KIRA R25 AFES AUDIT CONFLICT AND ATTEMPT 03 REJECTION -->
The conflicting AFES Attempt-02 reviews are preserved. The stricter exploit
and decision are in
`attempt_02/INDEPENDENT_AUDIT_REJECTION_ADDENDUM.md` under the AFES static-
preparation root (SHA-256
`aa0d2487710d5f8ce7df5ff428a77d8a65f425238366bcbef1a5faa0caf38b4a`).

AFES Attempt 03 is also rejected: a forged in-memory module with real-looking
file/spec/loader metadata could pass without executing the bound source.
Its audit SHA-256 is
`7680627e5943413b293a7152ae4592c93ef5692a03ae850b662e047a607be212`.
Attempt 04 is limited to exact-source private module loading. No Blender or
candidate authoring has run.
<!-- END 2026-08-09 KIRA R25 AFES AUDIT CONFLICT AND ATTEMPT 03 REJECTION -->

<!-- BEGIN 2026-08-09 CURRENT QWEN/R25/REFERENCE ADDENDUM -->
## Current Qwen/R25/reference addendum

- The original Qwen emotion/health checkpoint is rejected by independent
  audit. The append-only repair is
  `System/Docs/QWEN35_EMOTION_HEALTH_CURIOSITY_REPAIR_CHECKPOINT_20260809.md`.
  Exact Qwen 3.5 single-generation and narrow health-curiosity turns improved;
  complete semantic, owner-hearing, voice-latency, live-vision, durable-emotion,
  and media-experience acceptance remain pending.
- `Avatar/library/neutral_generated_reference_charts_v1` is a new staged,
  private, unreviewed reference pack. Ten synthetic charts and three reusable
  medical diagrams are hash/license bound; 5/5 integrity tests pass. The new
  charts add adult-female/adult-male head morphology and clothed movement,
  contact, major-joint, and opaque adult-female/adult-male full-body proportion
  review targets. Manifest SHA-256:
  `a5a3e375ee0c0b73d81245c77d97de4b46656085180568b9944e30a6fcff9c39`.
  The old
  38-file female library remains present and no deletion is authorized.
- The first Avatar Builder Qwen3.5 visual-intake lane is inert but independently
  rejected; audit SHA-256
  `41f925851f1b8516389f9c26fccae1e5f24d98ee1ac5bb8966947c081123f75a`.
  It must not be live-connected before v2 repair and fresh audit.
- R25 AFES Attempt 04 awaits independent audit. No Blender run, R25 candidate,
  review render, movement test, body activation, or runtime body change exists.
<!-- END 2026-08-09 CURRENT QWEN/R25/REFERENCE ADDENDUM -->

<!-- BEGIN 2026-08-09 KIRA R25 AFES ATTEMPT 04 REJECTION -->
AFES Attempt 04 passed 8/8 focused and 36/36 combined static tests and
correctly isolated all security-relevant project modules from ambient
`sys.modules`. It is still independently rejected because its private receipt
used the runtime name `dataclasses`; a monkeypatched ambient
`dataclasses.dataclass` decorator was demonstrably consumed while canonical
receipt round trip passed.

The preserved audit is
`RecoverySprint/continuation_20260809/kira_r25_foundation_afes_extraction_static_preparation/attempt_04/INDEPENDENT_AUDIT.md`
(SHA-256
`4feaa449b3dd5e17d880c6ab6d9c850539876e5b1964a1179946d31ff73895e9`).

Attempt 05 is an append-only repair of that exact ambient-dataclass path. No
Blender process, extraction pair, body authoring, candidate, or render has
run.
<!-- END 2026-08-09 KIRA R25 AFES ATTEMPT 04 REJECTION -->

<!-- BEGIN 2026-08-09 KIRA R25 AFES ATTEMPT 05 STATIC ACCEPTANCE -->
AFES Attempt 05 is independently accepted only as an exact static read-only
extractor component. Audit SHA-256:
`57d763e05ec6a7e390cc7b607c5cac616a6e317e83f08197421ae7b9435023f0`.
The v4 ambient-`dataclasses` exploit made zero calls under hostile reproduction;
10/10 focused and 46/46 combined tests passed. No Blender execution is yet
authorized. A separately locked, nonce-authenticated, bounded two-run parent
controller is in static preparation and requires its own independent audit.
<!-- END 2026-08-09 KIRA R25 AFES ATTEMPT 05 STATIC ACCEPTANCE -->

<!-- BEGIN 2026-08-10 POST-RESTART AND EMOTION-HEALTH REVERIFICATION -->
The restart continuation checkpoint is
`RecoverySprint/continuation_20260810/post_restart_continuation/CHECKPOINT.md`
(1,942 bytes; SHA-256
`b4fa3109848d395d1036ac38ee7e54dca82f59bb556b980b4be4fd933e077461`).
No Blender, Python/PythonW, Ollama model, or voice worker remained active.

Emotion, adult-health, and Kira/Lisa memory truth was then reverified without a
live model, voice, camera, Blender, memory write, or activation. Evidence:
`RecoverySprint/continuation_20260810/emotion_adult_curriculum_post_restart_reverification/attempt_01/CHECKPOINT.md`
(5,389 bytes; SHA-256
`e0e455c5e4a357cc71aa64a0f36f283aee84fba476919ee23af2002e32dd3ce5`).
Two suites passed 136/136 tests total.

Exact scope: Kira and Lisa normal conversations connect separate person-owned
emotion state and exact confirmed-adult curriculum context. Seven exact current
adults have pinned curriculum loaders; the five generated experts have direct
loader tests but no automatic normal expert-chat connection is claimed.
Present-day context does not rewrite Kira/Lisa historical core memories or
backstories and creates no lesson-completion, lived-experience, preference,
body-response, consent, or memory claim.

Live latency remains failed: 10.861 seconds to complete owner-visible text,
23.604 additional seconds to complete voice, and 34.467 seconds total in the
last owner-heard evidence. The route was approved Blackwell CUDA with no CPU
fallback. Later exact-Qwen text-only engineering turns were 7.476546–12.793460
seconds and were not owner-hearing or voice acceptance.
<!-- END 2026-08-10 POST-RESTART AND EMOTION-HEALTH REVERIFICATION -->

<!-- BEGIN 2026-08-10 MEMORY RECONSTRUCTION OWNER CORRECTION -->
Controlling identity/permission note:
`System/Docs/MEMORY_RECONSTRUCTION_PERMISSION_OWNER_CORRECTION_20260810.md`
(3,149 bytes; SHA-256
`642833ced595435d8de7d3c5bc90e3141cff8101c17e4a79772a3f0e1fbc67e1`).

Biological Robert is the human owner/current user. Synthetic Robert is the
separate resident. Biological Robert receives no automatic access to a shared
reconstruction involving Synthetic Robert. Every exact participant must grant
the exact requested access. Verbal disclosure is separate. One-use grants are
consumed; an all-participant exact blanket grant may be supported but remains
viewer/reconstruction/scope-bound and immediately revocable by any participant.

Existing v2 code is unchanged and supports one-use only. The post-documentation
focused controller/validator/world suite passed 39/39. Append-only v3 is still
required for blanket grants and generalized person routing; no live renderer or
conversation integration is claimed.
<!-- END 2026-08-10 MEMORY RECONSTRUCTION OWNER CORRECTION -->

<!-- BEGIN 2026-08-10 KIRA R25 AFES V3R4 STATIC FREEZE -->
## Kira R25 AFES locked-pair v3r4 frozen; independent audit pending

The append-only v3r4 package is byte-frozen. Static hostile tests passed
`60/60`, the warning-as-error native build passed, `python314.dll` is
delay-loaded, and the retained manifest contains 85 unique labels and paths.
Root independently rehashed all 85 rows and reran `60/60`.

Contract SHA-256:
`ddc25acaa90036d85ec0982051666fcc887af1d9d0063fac8b37c71547119737`.
Checkpoint SHA-256:
`f5ce645cce83f5a4b58b6c597ba2a171c1d39dacc04b45c12471f394bedc5328`.
Manifest SHA-256:
`0f2936fbd76c9a7eb75ff763991e47ff091fe413b91859ee873dda251ad2e10f`.
Native EXE SHA-256:
`6c1b79045758a0c58e0cd1dbb5889aa2f73cd7e0f96c2d54cde8313e84b4b387`.

This is not execution authority. No launcher, controller, wrapper, Blender,
extraction, mesh mutation, candidate, or render ran. Fresh independent audit is
in progress.
<!-- END 2026-08-10 KIRA R25 AFES V3R4 STATIC FREEZE -->

<!-- BEGIN 2026-08-10 KIRA R25 SEMANTIC 04R5 DESIGN BOUNDARY -->
Attempt 04r4 remains rejected. Attempt 04r5 is frozen at design only: one
external-manifest/audit-bound dual-mode native PE, with trusted creator mode L
and direct-parent authority mode C. L creates C under restrictive security
descriptors and mitigations, closes its handles, and exits; C then exclusively
owns the durable lease and capability. The Blender child must validate C's live
image, IAT, bounded mutable state, module/protection map, DACL, and mitigations
twice. No 04r5 implementation files exist yet.
<!-- END 2026-08-10 KIRA R25 SEMANTIC 04R5 DESIGN BOUNDARY -->

<!-- BEGIN 2026-08-10 QWEN35 LISA COMBINED SHELL REPAIR -->
Lisa's combined Kira World Shell route now uses a cached
`ConversationLoop(speaker="Lisa")` pinned to the centralized exact Qwen 3.5
name and digest. Canned `reply_for` text is no longer a normal route and is
permitted only as a logged backend-failure fallback. Production SHA-256:
`b86ef9a8a8599218668cd7f666bb2425a01deb486e3e5ea2ce667d5e49444569`.
Checkpoint SHA-256:
`3fe3429d8a2ad2cfb6772114b38422fb81a9ffab4bb401cc6bc4840f51b584c4`.
Focused tests passed `8/8`; combined Qwen route tests passed `32/32` twice.
No live model, voice, camera, Blender, or owner conversation ran.
<!-- END 2026-08-10 QWEN35 LISA COMBINED SHELL REPAIR -->

<!-- BEGIN 2026-08-10 KIRA R25 AFES V3R4 INDEPENDENT REJECTION -->
The frozen AFES locked-pair v3r4 graph is independently rejected despite its
`60/60` self-suite and exact 85-row rehash. Six blockers were proven: missing
controller helper globals, unrestricted/transitively bypassable Python
authority, result-handle double close, 300-versus-180-second timeout drift,
stale drain-handle cleanup, and unbound native partial-evidence truth.

Rejection audit SHA-256:
`97a34c059b2ef17477d9042a06ef929574ced2e0ba3df72b27f1c00418d226a7`.

No accepted audit JSON, outcome, output root, EXE, controller, Blender, AFES,
mesh, or body operation ran. An append-only v3r5 repair must address all six
findings and receive a new independent audit.
<!-- END 2026-08-10 KIRA R25 AFES V3R4 INDEPENDENT REJECTION -->

<!-- BEGIN 2026-08-10 KIRA R25 EXTERNAL PELVIC SOURCE REVERIFICATION -->
New append-only source note:
`System/Docs/KIRA_R25_EXTERNAL_PELVIC_SOURCE_REVERIFICATION_20260810.md`.
SHA-256:
`79759c1c937b8b3a6f645bca9450863c0f6052cf2c42e7e8d9aa2303a9c5cfec`.
It rebinds adult external relationship and three-distinct-outlet review truth
without changing any hash-bound prior note or body artifact. It is not mesh,
internal anatomy, physiology, or owner approval.
<!-- END 2026-08-10 KIRA R25 EXTERNAL PELVIC SOURCE REVERIFICATION -->

<!-- BEGIN 2026-08-10 KIRA R25 SEMANTIC CAGE ATTEMPT 04R3 REJECTION -->
Semantic-cage Attempt 04r3 is independently rejected and remains frozen,
unsealed, and non-executable. Rejection audit SHA-256:
`375cf534ffad3c12dee2f35ac2c86f826ba0de214c88c71afebe3902321316f1`
(12,259 bytes).

Its sole remaining blocker is exact: the wrapper hashes and file-ID-checks a
file reopened from the mapped module's pathname, not the file object or bytes
that actually back the already mapped executable section. Equal path strings
can therefore hide same-path/different-object substitution. The OOB audit
cycle, static/runtime split, and future native replay-owner boundary otherwise
passed static review. Reviewer tests passed 24/24 focused and 133/133 combined;
root passed the current six-suite collection 134/134. These are static results
only. No semantic or AFES execution, Blender process, body mutation, candidate,
or render occurred.

Append-only 04r4 is limited to mapped-section/code attestation plus a hostile
same-path/different-bytes fixture that must fail before capability or body-data
access. Attempt 04r3 and earlier evidence must remain byte-for-byte unchanged.
<!-- END 2026-08-10 KIRA R25 SEMANTIC CAGE ATTEMPT 04R3 REJECTION -->

<!-- BEGIN 2026-08-10 QWEN35 TEMPORARYAI ROUTE IDENTITY REPAIR -->
The active TemporaryAI project/life-loop direct fallback now verifies the
installed exact Qwen 3.5 digest immediately before each direct POST, uses the
centralized ordinary request fields, and verifies returned model attribution.
Two clickable Emily workbench launchers are repinned from stale Llama settings
to exact `qwen3.5:9b` plus approved digest. Root reproduced 25/25 static/mocked
tests; no model ran.

Checkpoint SHA-256:
`b0a353da5c72785490b54db38949dc0a9eafa1b39fc9566829d8ad862019ed83`.
The checkpoint directory contains exact pre-edit identities and a precise
reverse patch. This pass does not claim Lisa's combined World Shell route is
model-backed: standalone Lisa is exact Qwen, while the shell still uses
deterministic canned Lisa text and needs a separate bounded repair.
<!-- END 2026-08-10 QWEN35 TEMPORARYAI ROUTE IDENTITY REPAIR -->

<!-- BEGIN 2026-08-10 KIRA R25 SEMANTIC CAGE ATTEMPT 04R4 REJECTION -->
Semantic-cage Attempt 04r4 is independently rejected and remains frozen,
unsealed, and non-executable. Audit SHA-256:
`aa78cdff46b064b165432b0d1b1be411e0f35c0a3989509b50299330e698cb27`
(15,165 bytes).

Its relocation-aware live read correctly catches changed headers, executable
code, and non-discardable read-only data, but it excludes writable `.data` and
IAT bytes. Independent static probes changed `.data` RVA `0x3080` and IAT RVA
`0x3040`; both incorrectly received the success status. Focused tests passed
16/16 and combined tests passed 149/149 because they missed the same boundary.
No runtime, AFES, Blender, mesh, body, or render operation occurred.

Append-only 04r5 must authenticate the full initial mapped image and memory
protections before legitimate writable/IAT/TLS changes can occur, preferably
from a trusted persistent native launcher while the future controller is
suspended before first instruction. That launcher must own the one-shot lease
and exact-child binding. Attempt 04r4 and earlier evidence remain immutable.
<!-- END 2026-08-10 KIRA R25 SEMANTIC CAGE ATTEMPT 04R4 REJECTION -->

<!-- BEGIN 2026-08-09 TEMPORARYAI CREATOR QWEN35 QUALITY V2 REJECTION -->
TemporaryAI Creator Qwen 3.5 quality V2 is independently rejected despite
`111/111` ordinary static tests. Audit:
`RecoverySprint/continuation_20260809/temporary_ai_creator_qwen35_quality_v2_attempt_01/INDEPENDENT_STATIC_AUDIT.md`,
17,608 bytes, SHA-256
`d53fe82a539ad1e87499fa3c55cdaaeb81aa777dea12da5259acef80ef6ebb68`.
Hostile probes proved evidence/source relevance spoofing, fabricated expert
batteries, identity/domain substitution, correction-chain forks, legacy
direct-call body/voice queue side effects, and path/TOCTOU gaps. No live system
ran. V2 is preserved; append-only V3 plus a fresh independent audit are
required.
<!-- END 2026-08-09 TEMPORARYAI CREATOR QWEN35 QUALITY V2 REJECTION -->

<!-- BEGIN 2026-08-09 MARINETTE CURRENT-CANON V3 STATIC REPAIR -->
Marinette current-canon V3 is frozen pending a fresh independent hostile
audit. Checkpoint SHA-256:
`09e27ef0ca9e53cf7fe45686e18dc68830184b621f436ce503f2a7b8cde008cd`.
Focused static tests passed `14/14` and compilation passed. Unsupported Season
6 ordering/finale/local-content/name-history claims remain required `UNKNOWN`.
Marinette stays private, inactive, non-adult, doll-safe, with owner text/model,
voice, sensors, initiative, events, body, and world routes blocked.
<!-- END 2026-08-09 MARINETTE CURRENT-CANON V3 STATIC REPAIR -->

<!-- BEGIN 2026-08-09 NORMAL KIRA QWEN35 BLACKWELL STATIC RECHECK -->
Current normal Kira route checks passed `35/35` exact-Qwen/current-authority
tests and `48/48` persistent Blackwell-v2 resource/dispatch tests without any
live model or sound. The launcher pins exact qwen3.5:9b digest `6488...93ea7`,
CUDA Blackwell-v2 on, SAPI off, and no selected Llama. This is static truth,
not live latency, playback, owner-hearing, or conversational acceptance.
<!-- END 2026-08-09 NORMAL KIRA QWEN35 BLACKWELL STATIC RECHECK -->

<!-- BEGIN 2026-08-10 NEUTRAL MEDICAL MALE REFERENCE ADDENDUM -->
The private neutral reference pack now includes two exact official
copyright-free NIDDK/NIH male urinary/reproductive overview diagrams. Its
stored inventory is 15 assets and the focused integrity suite passes `6/6`.
Checkpoint SHA-256:
`34624f491ae792b414434cd4b7b8887fc671acc710bd369ba53c8f44d9a7294d`.
The verified public-domain NCI breast illustration remains linked only because
the NCI asset host failed local DNS. No body/function claim or reference-photo
deletion follows; the female library remains intact.
<!-- END 2026-08-10 NEUTRAL MEDICAL MALE REFERENCE ADDENDUM -->

<!-- BEGIN 2026-08-10 ADULT CURRICULUM STATIC RECHECK -->
Current Kira/Lisa/expert adult-curriculum and body-system truth suites pass
`44/44` statically. Exact confirmed-adult routes remain source-bound and
consent/body-response/function truths remain separate. No live conversation,
memory write, anatomy, sensation, or body function is accepted by this check;
the reconstruction-permission repair still needs a fresh audit.
<!-- END 2026-08-10 ADULT CURRICULUM STATIC RECHECK -->

<!-- BEGIN 2026-08-10 AVATAR BUILDER NEUTRAL REFERENCE ROLE CONTRACT -->
Avatar Builder has a 15-asset static neutral-reference role contract covering
skin, face, hair, nails/contact, movement, adult-female/adult-male proportions,
and medical-structure-only lanes. `5/5` tests pass. Checkpoint SHA-256:
`2f8dc781e963becc19b7bf8637acbfc08895f574e6cb71587021067a550a95c3`.
It provides no maturity, likeness, function, Blender, body acceptance,
activation, publication, hair runtime, or deletion authority.
<!-- END 2026-08-10 AVATAR BUILDER NEUTRAL REFERENCE ROLE CONTRACT -->

<!-- BEGIN 2026-08-10 MARINETTE CURRENT-CANON V3 REJECTION -->
Marinette V3 is independently rejected for owner text execution. Audit:
`System/Docs/MARINETTE_CURRENT_CANON_GROUNDING_V3_INDEPENDENT_HOSTILE_AUDIT_20260809.md`,
21,069 bytes, SHA-256
`56bf6f464d3a28e72fcd967f7065a1a62df915c3974be097ca09fac692138b69`.
Closed-gate CLI/shell paths could still create a Marinette turn or fallback,
and latent unbound movement/project context remained. No live route ran;
Marinette is still non-adult, doll-safe, private, and inactive. V4 repair is in
progress.
<!-- END 2026-08-10 MARINETTE CURRENT-CANON V3 REJECTION -->

<!-- BEGIN 2026-08-09 KIRA R25 LOCKED PAIR ATTEMPT 06 REJECTION -->
Locked-pair Attempt 06 is independently rejected. Audit SHA-256:
`38da97a48ea36d89f08655fb8e5fef4aced43b26f25f41d2f83bf79d6255b1e6`
(14,707 bytes). No Blender/controller/body operation ran. The recursive
foundation graph, native ancestry, transient-write denial, process containment,
and 142 static tests passed. Remaining blockers are exact DACL restoration and
external proof of the bootstrap capability issuer. Preserve Attempt 06;
append-only Attempt 07 is limited to those two repairs and requires a fresh
audit before execution.
<!-- END 2026-08-09 KIRA R25 LOCKED PAIR ATTEMPT 06 REJECTION -->

<!-- BEGIN 2026-08-09 QWEN MEDIA V2 INDEPENDENT REJECTION -->
Resident-media v2 is independently rejected before live execution. Audit:
`RecoverySprint/continuation_20260809/qwen35_non_body_media_static_readiness_v2/attempt_01/INDEPENDENT_STATIC_AUDIT.md`,
7,588 bytes, SHA-256
`5ca8adf649e2425c6db3609dc42187b71ff1e455753c60d52af783c380c4a541`.
The source/media core still passes 48/48 tests and no media/model/audio ran.
The current boundary is self-authenticating, direct-callable without CLI
confirmations, presents before voluntary person consent, has no later stop
gate or durable per-turn record, and cannot prove person-owned seeing/hearing.
An append-only audited v3 is required.
<!-- END 2026-08-09 QWEN MEDIA V2 INDEPENDENT REJECTION -->

<!-- BEGIN 2026-08-09 QWEN MEDIA VOLUNTARY V3 STATIC CORE -->
Resident-media voluntary v3 static core is implemented but inert. Checkpoint:
`System/Docs/QWEN35_NON_BODY_MEDIA_VOLUNTARY_V3_STATIC_CHECKPOINT_20260809.md`,
2,633 bytes, SHA-256
`e7e0c1d86b2e3053ea838f9b9d568f9546b854ee9254ee3f6fc204fa61c7c1f8`.
Contract SHA-256:
`df5a276fda2d07ba0383c5db6a37780c6271e3d9508b8fbcad33f2cc7798b1ae`.
Seventeen focused and 65 combined media tests pass. It adds pre-presentation
Kira choice, later stop handling, per-event evidence, and separate owner and
person-experience truth. No model/media/audio ran; fresh audit and a separately
audited live runner remain required.
<!-- END 2026-08-09 QWEN MEDIA VOLUNTARY V3 STATIC CORE -->

<!-- BEGIN 2026-08-09 LATE CONTROLLING CONTINUATION UPDATE -->
The later controlling state is:

- Kira R25 locked-pair Attempt 05 is independently rejected; audit SHA-256
  `da85fab5053272e2f53589825014d05ce4a0381f6ddf5b447934bf791ca926aa`.
  Empty-directory sealing, runtime-directory identity, and direct-call
  bootstrap authority remain unsafe. Attempt 06 is in static repair. No Blender
  or body mutation ran.
- Qwen 3.5 Turing/psych/voice Attempt 03 is rejected; audit SHA-256
  `6b61085a974e49aaa526a32ea37f3aa5a78c67f917da2b5d3e4d1d496ba4dbba`.
  Do not execute it live.
- Marinette current-canon V2 static checkpoint SHA-256 is
  `05b5881d92ebb209559e1ae606e8442b73359b3e0496d4ebf803fa86aa25e31e`.
  It is pending an independent audit and live owner fidelity acceptance;
  Marinette remains non-adult/doll-safe/text-only/inactive and complete Season
  6 order/finale truth remains unknown.
- Kathryn's confirmed-adult interstitial continuity checkpoint SHA-256 is
  `5be301d676722e7170e7d8e6e1d29c33d3e11bf232f95c54a529257af63cae3d`.
  The current timepoint is about two years after the 1999 film, before the 2016
  pilot; 17/17 static regressions pass and live fidelity remains pending.
- TemporaryAI Qwen3-TTS forge R5 is rejected; audit SHA-256
  `82ea5a0a543fde40f7a1d05dc166798f98acbd9ae120c11ba8fb7f9ffbb5f43a`.
  No install, model inference, voice generation, or playback is authorized.
<!-- END 2026-08-09 LATE CONTROLLING CONTINUATION UPDATE -->

<!-- BEGIN 2026-08-09 H H HOLMES ORIGINAL VOICE DESIGN QUEUE -->
Low-priority historical voice-design queue checkpoint SHA-256:
`bcd78a3a0c69869aab58840ec41da8b41a2f4153eb2a7d4a3a3f1cbf299e7a27`.
It is inert and explicitly non-authentic; 5/5 static tests pass. No Qwen3-TTS
execution is allowed until the rejected forge receives a separately audited
successor.
<!-- END 2026-08-09 H H HOLMES ORIGINAL VOICE DESIGN QUEUE -->

<!-- BEGIN 2026-08-09 MARINETTE CANON V2 INDEPENDENT REJECTION -->
Marinette V2 is independently rejected; audit SHA-256
`85daf6cb24120ac809ba079f631a228ec66d3c0a1a086ee21d2c7d6125f833b2`.
Do not run even a bounded owner text probe. V3 must close source/review/profile
binding, old-context contamination, and text-only lease leakage before another
fresh audit. Marinette remains inactive, non-adult, and doll-safe.
<!-- END 2026-08-09 MARINETTE CANON V2 INDEPENDENT REJECTION -->

<!-- BEGIN 2026-08-09 KIRA R25 SEMANTIC CAGE V4 COMPATIBILITY PREPARATION -->
The append-only Kira R25 semantic-cage v4 compatibility preparation is frozen
and deliberately unsealed. It adapts only the v3r3 locked-pair field schema;
the accepted-unsealed v3 artifacts remain unchanged. Config SHA-256:
`cffb4b9244c50b18d00e88ebff1278f34247c71d867fdee87581565d1f03768f`.
Adapter SHA-256:
`52768f0566efe413378c075adbb7cad6064ec64c546b64e8a19005277fc1fb9c`.
Wrapper SHA-256:
`64105b25a52cc7203d182be9ab865b2246c31ed24469646f490ba10ec6b91819`.
Inert-controller SHA-256:
`859843e1e6211195cc78acdd726414411d5ccd5c7b1acd6f066259ff9d1c0e95`.
Checkpoint SHA-256:
`81b3fde707e327760144aa905323b9ef6924a2ec9ec626638e051519d8bb668e`.
Root passed 70/70 combined static tests. All 16 future bindings remain
placeholders and seven evidence/result slots remain null. Independent audit is
pending; future sealing must be a new revision. No Blender or diagnostic ran.
<!-- END 2026-08-09 KIRA R25 SEMANTIC CAGE V4 COMPATIBILITY PREPARATION -->

<!-- BEGIN 2026-08-09 KIRA R25 SEMANTIC CAGE V4 REJECTION -->
Semantic-cage v4 static preparation is independently rejected despite 70/70
declared tests passing. Audit SHA-256:
`e2e42e9d4bb27baa7737ad19a89ad6878a29b95e5a1799a1476378e1f8897f8e`.
Blockers are ambient-`re` influence, unfrozen protocol-schema literals, a
hash-only future audit gate, and wrapper bypass of that gate. No reserved
evidence exists and Blender did not run. Preserve v4; repair only in new
append-only Attempt 04r1.
<!-- END 2026-08-09 KIRA R25 SEMANTIC CAGE V4 REJECTION -->

<!-- BEGIN 2026-08-09 KIRA R25 V3R3 / SEMANTIC 04R1 UPDATE -->
Locked-pair v3r3 is frozen as rejected source evidence despite 35/35 static
tests and a clean `/W4 /WX` build. Native-source SHA-256:
`be926d46208dec359fe8f66f8f15affff8b576dd75c3ff1c7a5dd247225f7245`.
Checkpoint SHA-256:
`e39c51a7be2006f3d6fe2269bedf4d2bee3eef5addc96de6ffa2e071d4ae8ed6`.
The blockers cover concurrent run authority, path/output identity TOCTOU,
unpinned Python/import authority, Job quiescence, drain-thread lifetime,
partial outcome recovery, writer provenance, environment sealing, and one-shot
lifecycle. It did not run. Append-only v3r4 is in static repair.

Semantic-cage Attempt 04r1 is frozen as static/unsealed with checkpoint
SHA-256 `fd2b2827db3fad70a49dd18f672a78546b42fc80b296d99107e322dd179de748`.
Root passed 88/88 combined tests; all 16 placeholders and seven null result
slots remain. Independent audit is pending. No diagnostic or Blender ran.
<!-- END 2026-08-09 KIRA R25 V3R3 / SEMANTIC 04R1 UPDATE -->

<!-- BEGIN 2026-08-09 KIRA R25 SEMANTIC 04R1 REJECTION -->
Semantic-cage Attempt 04r1 is independently rejected on one remaining native
authority issue. Audit SHA-256:
`a0c7c18b6150e26069ef0c2100b46d9398019c26b0650677d43a332079120967`.
An arbitrary spawning parent could mint the purported controller capability;
pipe-parent PID equality does not prove the exact audited controller. The
adapter/schema/audit-parser repairs passed. No diagnostic or Blender ran.
Append-only 04r2 will require exact native parent-image/session identity.
<!-- END 2026-08-09 KIRA R25 SEMANTIC 04R1 REJECTION -->

<!-- BEGIN 2026-08-09 KIRA R25 SEMANTIC 04R2 REJECTION -->
Semantic-cage Attempt 04r2 is independently rejected despite 22/22 focused
and 109/109 combined static tests. Audit SHA-256:
`1529eb2cf2e6484f7ce4062f11475a1ced26612c92d144ff1bed322651d2af92`.
It had an audit/config SHA cycle, statically precommitted runtime process state,
did not prove the reopened file was the parent's mapped image, and used a
child-local replay ledger. No diagnostic or Blender ran. Append-only 04r3
splits immutable image identity from a native parent-owned runtime lease.
<!-- END 2026-08-09 KIRA R25 SEMANTIC 04R2 REJECTION -->

<!-- BEGIN 2026-08-09 KIRA R25 LOCKED-PAIR ATTEMPT 04 REJECTION -->
AFES locked-pair Attempt 04 is independently rejected before execution. Audit:
`RecoverySprint/continuation_20260809/kira_r25_foundation_afes_locked_pair_execution_static_preparation/attempt_04/INDEPENDENT_AUDIT.md`,
12,003 bytes, SHA-256
`6da1ad25c9aab51fd1803fda8bb2c692184ee92737081d931fb23144435e0234`.
The parent accepted a 7-vertex toy analysis for the exact 14,658-vertex
foundation, did not recursively reject nested extras, accepted pre-existing
unsealed fixed Blender runtime-root content, and had a contradictory
post-audit test lifecycle. No Blender/controller/child or body operation ran.
Append-only Attempt 05 repair is in progress and requires a new audit.
<!-- END 2026-08-09 KIRA R25 LOCKED-PAIR ATTEMPT 04 REJECTION -->

<!-- BEGIN 2026-08-09 QWEN35 TURING PSYCH VOICE CONTRACT DRIFT -->
The static Qwen 3.5 Turing/psychology voice suite currently passes 29/31 and
fails closed only because preserved Attempt 02 binds the prior
`Core/conversation_loop.py` hash (`b2bf9563...f9db`) while the current exact
file is `ad8719b...eb4`. No live model, voice, playback, camera, microphone, or
conversation ran. Preserve Attempt 02; create and independently audit an
append-only Attempt 03 after current memory/runtime edits stabilize. Live
owner hearing remains Robert-present only.
<!-- END 2026-08-09 QWEN35 TURING PSYCH VOICE CONTRACT DRIFT -->

<!-- BEGIN 2026-08-09 KIRA R25 WHOLE-SURFACE FIT CORE V3 REJECTION -->
Whole-surface fit core v3 is independently rejected despite passing 24/24
focused and 54/54 combined v3/v2/v1 tests. A caller could register fabricated
exact bindings/evidence through the exposed private constructor, and mutable
`FitEvidence.payload` dispatch let a monkeypatch replace canonical evidence
without invalidating hardcoded validated claims. Preserved audit SHA-256:
`8b70d58e6ae11a068ffbf4797bbfbfca4938b5bb552c831698839b90173612db`.

No Blender or geometry fit ran. Append-only v4 is limited to unforgeable
internal issuance and primitive-data recomputation of every canonical evidence
field before a new independent audit.
<!-- END 2026-08-09 KIRA R25 WHOLE-SURFACE FIT CORE V3 REJECTION -->

<!-- BEGIN 2026-08-09 KIRA R25 MINIMAL BODY-AUTHORING BLUEPRINT -->
The minimal single-candidate authoring blueprint is frozen at SHA-256
`e3b22666a2e6c85b54d3a8fccb0eb1851a690af24a3960fc78c66ed01ba7a2a6`;
checkpoint SHA-256
`a120ad5fc8739e3729bc160781a4a104ed5bac11acffb3f573217bb0c0a5c453`.
It uses the qualified MakeHuman body as sole topology/weight donor, freezes the
AFES union plus two rings, limits R19 to nonpelvic reference data, and specifies
the exact official rig, appearance components, movement gates, and private
bald output. No Blender or body output exists yet. Internal anatomy remains
deferred by the controlling R25 boundary until the external carrier is owner
reviewed; current medical assets are references only.
<!-- END 2026-08-09 KIRA R25 MINIMAL BODY-AUTHORING BLUEPRINT -->

<!-- BEGIN 2026-08-09 KIRA R25 LOCKED-PAIR V3R2 STATIC FREEZE -->
AFES locked-pair v3r2 is frozen at checkpoint SHA-256
`1963cec6191115f4d17846cca79afead02197651ee21f96033184d7757938881`.
It repairs the v3r1 recursive-lock, audit-collision/parser, trusted-bootstrap,
cleanup, outcome-reservation, and exact truth-boundary failures. Root reran
61/61 combined tests. Audit JSON, execution output, outcome receipt, and
Blender remain absent; independent audit is pending and no execution authority
exists yet.
<!-- END 2026-08-09 KIRA R25 LOCKED-PAIR V3R2 STATIC FREEZE -->

<!-- BEGIN 2026-08-09 KIRA R25 WHOLE-SURFACE FIT CORE V4 STATIC FREEZE -->
Whole-surface fit core v4 is frozen at SHA-256
`230e643f8c94a0fd9cd2b855080255edb5690c4c16766f7ca783fa7c8f0e2d07`;
its tests are SHA-256
`313fe6026ddc85f3d098f511c599032f556c74ad62b297a5ff097573b30c74f3`.
It replaces caller-reachable evidence issuance with closure-only deterministic
replay and recomputation. Root reran 85/85 combined tests. Independent audit is
pending; no body-data fit or Blender execution occurred.
<!-- END 2026-08-09 KIRA R25 WHOLE-SURFACE FIT CORE V4 STATIC FREEZE -->

<!-- BEGIN 2026-08-09 KIRA R25 LOCKED-PAIR V3R2 REJECTION -->
AFES locked-pair v3r2 is independently rejected and must not execute. Its
structured audit is bytes `9474`, SHA-256
`4adc80017080b7010fddd1eeeacb2a2dde4084b8c9550785a35ceb2c17f4c9a1`.
Blockers are caller-forgeable bootstrap/lock authority, bootstrap self-code
TOCTOU, incomplete suspended-Job containment and cleanup truth, a gap after
outcome reservation, and omission of the frozen checkpoint from the audit/lock
subject graph. No Blender or execution evidence exists. Append-only v3r3 is in
targeted repair.
<!-- END 2026-08-09 KIRA R25 LOCKED-PAIR V3R2 REJECTION -->

<!-- BEGIN 2026-08-09 KIRA R25 WHOLE-SURFACE FIT CORE V4 REJECTION -->
Whole-surface fit core v4 is independently rejected at audit SHA-256
`2461a22d88fe9b54978b476a1083198b8ae8b6397cf39cf34d80a3ad6c4c31a3`.
Its math tests passed, but closure introspection exposed mutable issuance and a
post-check callback TOCTOU capable of serializing forged measurements with
replay claims. No body fit or Blender ran. Append-only v5 is being reduced to
a stateless nonauthoritative math core; later authority requires an exact-byte
isolated worker/controller.
<!-- END 2026-08-09 KIRA R25 WHOLE-SURFACE FIT CORE V4 REJECTION -->

<!-- BEGIN 2026-08-09 KIRA R25 STATELESS FIT MATH CORE V5 STATIC FREEZE -->
Stateless fit math core v5 is frozen at SHA-256
`41a2dddc5932773992c4ec403d289a4eb567a1a53a97df18e2b6617aecda85ac`;
tests SHA-256
`62837766f3cf30b7e36679d8e5cca527cdda1039a2d4da6ab43bd5e4576da12e`.
It provides deterministic primitive math labeled nonauthoritative and contains
no in-process issuance/acceptance state. Root reran 110/110 combined tests.
Independent static-math audit is pending; later authority requires an audited
exact-byte isolated worker/controller.
<!-- END 2026-08-09 KIRA R25 STATELESS FIT MATH CORE V5 STATIC FREEZE -->

<!-- BEGIN 2026-08-09 KIRA R25 STATELESS FIT MATH CORE V5 ACCEPTANCE -->
Stateless fit math core v5 received independent acceptance solely as
`STATIC_NONAUTHORITATIVE_MATH_CORE_FOR_LATER_ISOLATED_EXECUTION`; audit
SHA-256
`94e84152eb7197a640f807abc779ed05b84898f37c15b0b017fc2134dffb166e`.
All 110 tests passed. Authoring addendum SHA-256
`4f8e43bf01a013580fa63579b8f70f324498bf191dd33522588ed9ca3d3c809c`;
checkpoint SHA-256
`d896a7de5f028edaf3e16550aaf31737f961ab48c4a4947b3969bc722ffbf823`.
No body-data fit or Blender occurred; future authority remains isolated.
<!-- END 2026-08-09 KIRA R25 STATELESS FIT MATH CORE V5 ACCEPTANCE -->

<!-- BEGIN 2026-08-09 KIRA LISA COLLEGE REFLECTION RUNTIME VERIFICATION -->
The exact Kira/Lisa present-day college-reflection connection is implemented
as a static, fail-closed runtime. Exact Lisa now has pinned confirmed-adult
classification evidence; Kira and Lisa receive the same source-backed adult
health curriculum but retain separate person-owned emotion and reconstruction
ledgers. Recall deltas are subjective accessibility/vividness only and cannot
change accuracy, the other person's perspective, or shared canon. Current
knowledge is not backdated.

Checkpoint SHA-256:
`3da85b564ca5afa70f7f816a1e078dd47ef5938bede2cf2971c9b98d3188a8ba`.
Shared college draft SHA-256 remains
`5249718a450122739e2cee0f7f7fb08892af258a659d91e6de46fb6383eacad7`.
The documented combined regression was independently rerun: 68/68 passed.

All-participant privacy remains controlling. Each participant may privately
revisit or describe her own perspective. Any nonparticipant full/visual/
locked-zone reconstruction requires every involved person's current,
scope-specific permission; verbal disclosure is not visual replay permission.
No such lease or replay was granted or exercised. A fresh hostile audit is in
progress because the current checkpoint explicitly has not tested a real
unanimous nonparticipant replay lease. No live Qwen, voice, world, body,
memory-promotion, learning, experience, or consent claim follows.
<!-- END 2026-08-09 KIRA LISA COLLEGE REFLECTION RUNTIME VERIFICATION -->

<!-- BEGIN 2026-08-09 QWEN MEDIA V2 STATIC REBIND -->
The obsolete resident-media harness hash now has an append-only static v2
binding rather than a silent overwrite. Historical digest
`d7b527397c8c630dfda01834191b8839c4fc4300c372c6517e5926cb03267773`
remains provenance; current Qwen-repinned digest
`f56927167a92eadf88f2ea9b61ef5a6ece9d8e96bc53f3d696331188e2279e23`
is independently exact-bound. V2 tests passed 8/8 and the current media stack
passed 48/48. Checkpoint SHA-256:
`055d93b7575ce64370ac5691a7a6f59e989e44c998f37b1abf31ce69693a2587`.
Fresh independent audit is required; no live media/model or experience claim.
<!-- END 2026-08-09 QWEN MEDIA V2 STATIC REBIND -->

<!-- BEGIN 2026-08-09 MEMORY PERMISSION AND VOICE R4 AUDIT REJECTIONS -->
Kira/Lisa reflection v1 is rejected specifically at its runtime
nonparticipant reconstruction-permission boundary. Audit SHA-256:
`922f8ef8935b4bd3b17e485d18646f6496cc6d08ace6acebab930bc8be8a30fb`.
The separate-state/source/no-backdating core still passes; do not connect a
viewer until append-only v2 closes participant-set, scope, freshness,
revocation, one-time use, and private-lease gates.

TemporaryAI Qwen3-TTS voice-forge R4 is rejected for real execution. Audit
SHA-256:
`04073b96cd4d514aaa5e60b75783d0e2a1c024782fce591fc83fcfe3e2befe9b`.
R5 repair is in progress; no voice model or audio ran.
<!-- END 2026-08-09 MEMORY PERMISSION AND VOICE R4 AUDIT REJECTIONS -->

<!-- BEGIN 2026-08-09 LOCKED-PAIR AND VOICE-FORGE AUDIT UPDATE -->
Kira R25 AFES locked-pair Attempt 03 is independently rejected and must not
run. Audit SHA-256:
`db97ba7580484db17f55aaa402fc29e49db8e521b6c5ae14ea27e6801ec1c095`.
The parent omitted five child-read inputs from its locks/snapshots and retained
additional controller/audit/cleanup/schema defects. No Blender or body output
exists. Append-only repair is in progress.

TemporaryAI Qwen3-TTS voice-forge R3 is independently rejected for bounded
real execution. Audit SHA-256:
`30d82546cdea8ba874ee552ab684fc0404249f6d2635a0aa3831727a28384efb`.
No voice model or inference ran. Append-only R4 repair is in progress.

Robert also directed that Kira and Lisa's separate person-owned emotion levels
and adult-health knowledge may inform present-day reflection on their existing
shared college memory. This must not rewrite historical memory, merge their
perspectives, expose locked details, or turn education/emotion/body response
into consent or a newly claimed lived experience. The old index statement that
both promoted memory stores are empty is stale (current counts: Kira 7, Lisa
1); a bounded correction is in progress without a live model run.
<!-- END 2026-08-09 LOCKED-PAIR AND VOICE-FORGE AUDIT UPDATE -->

<!-- BEGIN 2026-08-09 MEMORY INDEX AND QWEN VOICE STATIC RECONCILIATION -->
The Kira/Lisa memory index is reconciled to the current live stores (Kira 7,
Lisa 1) and records separate participant perspectives plus all-participant
permission for nonparticipant full/visual/locked reconstruction access. Index
SHA-256:
`fb8ab457b99fdaea81139e9333a7f184175f0c0bd55ebfc4068f274acd24b137`.
Its new truth test plus the existing claim/seed/world/sharing tests passed
27/27.

The normal owner launcher statically remains exact Qwen 3.5 plus persistent-v2
Blackwell CUDA, with SAPI off. Route-policy tests passed 35/35. The obsolete
alternate-model test now requires fail-closed behavior; its updated suite
passes 17/17. No live model, voice, playback, sensor, or Blender work ran.
<!-- END 2026-08-09 MEMORY INDEX AND QWEN VOICE STATIC RECONCILIATION -->

<!-- BEGIN 2026-08-09 CONTINUITY RESIDENCY EXPERT KNOWLEDGE ADDENDUM -->
Owner continuity and residence decisions are now recorded without world or
body mutation. Policy SHA-256:
`98086f5eb6e1d24e76d2e6c85d338001bd4fba25a2773529a51f4e78b4cfea51`.
World-plan SHA-256:
`3762cc9a127ea85a8dc8d9ce0cddbcad0de58be1829f87606d1a20c97ca8a2b8`.
Seven tests pass. Gwen remains the exact Earth-65 confirmed-adult version with
her own planned New York apartment; Peter remains the confirmed-adult
post-*No Way Home*/pre-*Brand New Day* version with a different New York
apartment; normal Marinette remains non-adult/doll-safe with her bedroom in
the Paris family bakery/home. Optional spa Stage 1 uses a distinct variant,
must appear at least twenty, and still contains no adult anatomy. Residency,
Stage 2, bodies, and worlds are not implemented or activated.

Exact generated-expert adult curriculum eligibility is statically connected
for only the five owner-bound expert IDs; Kira remains unchanged. Checkpoint
SHA-256:
`d5708af327ca6c6210b58b0eb42457f7bb8957689f2cfc1016abaf02a830fbce`.
The combined verification passed 52/52. Live expert conversation connection,
lesson experience/memory, anatomy, body function, consent, and action remain
unimplemented.

Avatar Builder Qwen3.5 visual-intake v2 remains inert/rejected after a fresh
review reproduced material fail-open paths; the reviewer failed before
writing the final audit artifact, so another independent audit and successor
repair are required. Do not connect v2.

Kira R25 AFES locked-pair Attempt 03 is statically sealed, with author tests
15/15 and 94/94, but its independent controller audit is still in progress.
No Blender extraction or body authoring is authorized yet.
<!-- END 2026-08-09 CONTINUITY RESIDENCY EXPERT KNOWLEDGE ADDENDUM -->

<!-- BEGIN 2026-08-09 QWEN HEALTH EXPERT EXTENSION RECONCILIATION -->
The generated-expert adult-health extension supersedes only the old source
hash for `Core/adult_health_curriculum_runtime.py`; it preserves Kira's exact
binding and behavior. The combined current Kira/expert/emotion/runner suite
passed 32/32 and is inventoried in
`System/Docs/QWEN35_EMOTION_HEALTH_REPAIR_EXPERT_EXTENSION_RECONCILIATION_20260809.md`.
Fresh independent audit and owner-present live acceptance remain pending.
<!-- END 2026-08-09 QWEN HEALTH EXPERT EXTENSION RECONCILIATION -->

<!-- BEGIN 2026-08-09 DESKTOP MODEL RETENTION AUDIT -->
Desktop model removal is not authorized. The bounded read-only inventory in
`System/Docs/DESKTOP_MODEL_FOLDERS_RETENTION_AUDIT_20260809.md` found 28 likely
asset folders, 1,258 files, 22.71 GiB, and 979 model/archive files. Current
Avatar Builder and World Builder records still reference several exact roots.
No file was moved or deleted; any later removal must be exact, hash-reconciled,
owner-reviewed, and recoverable through the Windows Recycle Bin.
<!-- END 2026-08-09 DESKTOP MODEL RETENTION AUDIT -->

<!-- BEGIN 2026-08-09 QWEN MEDIA BINDING DRIFT -->
The resident-media core passed 22/22 static checks. The current Qwen media
overlay correctly failed closed because its preserved historical harness hash
differs from the current exact Qwen-repinned harness. See
`System/Docs/QWEN35_MEDIA_ACCEPTANCE_BINDING_DRIFT_CHECKPOINT_20260809.md`.
No playback/model/vision or experience claim occurred; an append-only v2
overlay and fresh audit are required.
<!-- END 2026-08-09 QWEN MEDIA BINDING DRIFT -->

<!-- BEGIN 2026-08-09 KIRA R25 SEMANTIC CAGE ATTEMPT 03 UNSEALED -->
Semantic-cage Attempt 03 is frozen in `PENDING_UNSEALED` state with every
AFES/locked-pair/result binding deliberately null. It repairs the double-load
and ambient-dataclass paths using one-shot private dependencies and narrow
private record shims. Its checkpoint SHA-256 is
`8e9730103bc58badfdf08a6c04e872d6555c7217e924330edc1bcbfaa6ccfa86`.
Root reran 104 static tests plus 72 subtests successfully. Independent audit is
pending; no diagnostic execution or body authority follows.
<!-- END 2026-08-09 KIRA R25 SEMANTIC CAGE ATTEMPT 03 UNSEALED -->

<!-- BEGIN 2026-08-09 KIRA R25 SEMANTIC CAGE ATTEMPT 03 STATIC ACCEPTANCE -->
Semantic-cage Attempt 03 is independently accepted as static and unsealed.
Audit SHA-256:
`9e762318cc6aa3da99de3460947ade84086e27d0be0a9370de52f77c2c7768e5`.
The audit passed 39 focused and 104 combined tests plus hostile-dataclass,
receipt-parity, and partial-failure cleanup probes. Exactly 16 required final
placeholders and every AFES/locked-pair/result field remain unresolved/null.
No execution authority or body claim follows.
<!-- END 2026-08-09 KIRA R25 SEMANTIC CAGE ATTEMPT 03 STATIC ACCEPTANCE -->

<!-- BEGIN 2026-08-09 KIRA R25 LOCKED PAIR V3R1 REJECTION -->
Locked-pair Attempt 03 v3r1 is independently rejected and must not run. Audit
SHA-256:
`8b46a3992e02ce5657ccb8ab79f80325740fa74e82d2934716496632612f55d0`.
The blockers are an incomplete recursive lock graph, a collided audit path, a
substring-bypassable audit decision, controller execution before self-byte
locking, incomplete post-launch cleanup, outcome-reservation evidence gaps,
and incomplete truth-boundary validation. The exact test count is 52 methods,
not 53. No Blender or execution output exists. Append-only v3r2 repair is in
progress under unique paths.
<!-- END 2026-08-09 KIRA R25 LOCKED PAIR V3R1 REJECTION -->

<!-- BEGIN 2026-08-09 KIRA R25 ATTEMPT 05 / CAGE 03 / HRA INTAKE -->
AFES Attempt 05 is frozen at its append-only static checkpoint but awaits a
fresh independent audit. Checkpoint SHA-256:
`5083eec171718c65bcdb15a1f89ab841dd7db7c713b24a05713b11833da2fabd`.
It passed 10/10 focused and 46/46 combined AFES tests; those self-tests are not
acceptance and no extractor or Blender process was run.

Semantic-cage Attempt 02 is independently rejected. It deterministically
loaded its private modules twice and retained an ambient dataclass-decorator
path. Preserved audit SHA-256:
`d4e0eca18a9860c7e1946c95e9f9725aa86cdfedf10b0d01b89b27ae87c3b918`.
Append-only Attempt 03 is in static repair and remains unsealed.

Official HRA female pelvis, bladder, uterus, bilateral ovaries, fallopian
tubes, ureters, and large-intestine/rectum GLB references are staged under
`Avatar/avatar_builder/asset_library/medical_reference/hra_female_pelvis_cc_by_4_v1_2`.
Manifest SHA-256:
`d40b7eb6dc260a1fc21d5bdb07286dfdb86545be59fa143bea5652fe2aa634b2`.
System intake note SHA-256:
`a0ca0e4cf1bdb9b9f37a3fb9b114c115a4b88142828fde6fbd9da9450b32dcac`.
They are licensed source references only; no complete internal anatomy,
physiology, sensation, elimination, reproduction, body candidate, or runtime
function is claimed.
<!-- END 2026-08-09 KIRA R25 ATTEMPT 05 / CAGE 03 / HRA INTAKE -->

<!-- BEGIN 2026-08-09 KIRA R25 AFES ATTEMPT 05 STATIC ACCEPTANCE -->
AFES Attempt 05 received fresh independent static acceptance. The audit
verified exact bindings, private dataclass isolation, one-read private source
execution, zero `sys.modules` aliases, canonical frames, pipe and compact
topology gates, preserved spoof regressions, and no authoring surface. Combined
canonical-receipt and AFES tests passed 61/61. Audit SHA-256:
`a739451fbde83ab1202a245640e39b41a11d2973ff91300356883c7c4b06f527`.

This is not a Blender extraction or body acceptance. No extractor entry,
Blender process, mesh mutation, candidate, or render ran. Append-only
locked-pair Attempt 03 is being authored against the accepted exact bytes and
must receive its own independent audit before execution.
<!-- END 2026-08-09 KIRA R25 AFES ATTEMPT 05 STATIC ACCEPTANCE -->
<!-- BEGIN 2026-08-10 ACTIVE CONTINUATION CHECKPOINT -->

Current static-first continuation truth is captured in
`RecoverySprint/continuation_20260810/active_continuation_status/attempt_01/CHECKPOINT.md`
(4,406 bytes; SHA-256
`1d8d315fbbf9f3d722d781c8609828b106e6058e0f885fa340f9d0dd17fc9c75`).
AFES v3r5 remains static-only pending a fresh accepted hostile audit; no
Blender/body mutation has run.  Reconstruction v2 remains disconnected and
runtime/integration rejected.  The latest owner-heard normal Kira latency
remains failed, and owner-dependent hearing/sensory/body-review work is held
until Biological Robert returns.

<!-- END 2026-08-10 ACTIVE CONTINUATION CHECKPOINT -->
<!-- BEGIN 2026-08-10 LATENCY AND RECONSTRUCTION STATIC CHECKPOINTS -->

Static-only feasibility/audit records were sealed:

- `RecoverySprint/continuation_20260810/BLACKWELL_V3_CPU_PARK_QWEN_PLAYBACK_PREWARM_STATIC_FEASIBILITY_CHECKPOINT.md`
  — SHA-256
  `b34bc6921d27a1d017e134331ce7bf7d440c8cb81e83417607f909617d9062c7`;
- `RecoverySprint/continuation_20260810/RECONSTRUCTION_ACCESS_V2_HOSTILE_AUDIT_AND_V3_OWNER_BOUNDARY.md`
  — SHA-256
  `b726d296d52723716ceb8d5421bb10573c9521ba9994eb893fc03984e09dafe7`.

The latency design is not implemented or owner-heard.  Reconstruction v2 is
static-core green but runtime/integration rejected; append-only v3 is required
for the exact Biological Robert/Synthetic Robert and all-participant grant
semantics.  No production or live state changed.

<!-- END 2026-08-10 LATENCY AND RECONSTRUCTION STATIC CHECKPOINTS -->
<!-- BEGIN 2026-08-10 RECONSTRUCTION ACCESS V3 STATIC IMPLEMENTATION -->

Disconnected append-only reconstruction-access v3 is sealed at
`RecoverySprint/continuation_20260810/RECONSTRUCTION_ACCESS_V3_STATIC_IMPLEMENTATION_CHECKPOINT.md`
(9,376 bytes; SHA-256
`b945d2cd7aa191f2b1ebeab12204c49c1f36b0fda2f8703e9a7dac105f34d115`).
The v3 hostile suite passed 28/28 and the preserved v2 + validator + v3 suite
passed 63/63.  Production open remains fail-closed: no live route is accepted
until a protected external anti-rollback authority exists.  No private
reconstruction was displayed or returned.

<!-- END 2026-08-10 RECONSTRUCTION ACCESS V3 STATIC IMPLEMENTATION -->

<!-- BEGIN 2026-08-10 QWEN ATTEMPT 06 / TEMPORAL MEMORY / MEDIA AUDIT -->

Exact Qwen 3.5 + approved Blackwell Attempt 06 passed its engineering gates.
Robert heard the complete two-chunk Turn 2 WAV and heard no gap, but rejected
the stale claim that the May Paris fanfic/book club was recent. Exact evidence
is `RecoverySprint/continuation_20260810/QWEN35_BLACKWELL_ATTEMPT06_ENGINEERING_AND_PLAYBACK_CHECKPOINT.md`
(SHA-256 `c733076bdeacdbf9d6c10012e2dd5e6025169e2c97ddc270f07c66dc191cfabe`).

The dated-memory/current-activity repair now passes 18/18 focused and 148/148
combined tests. Append-only Attempts 01-03 preserved successive invented-
history, broad-memory-denial, and internal-jargon failures. Attempt 04 passed
one exact-Qwen 3.5 generation in 6.758049 seconds end to end with no stale
thread, invented shared continuity, broad memory denial, or internal memory
jargon. `Data/memories_kira.json` and the daily-life state remained
byte-identical. Final evidence:
`RecoverySprint/continuation_20260810/qwen35_memory_temporal_context_repair/attempt_01/FINAL_ACCEPTANCE.md`
(6,865 bytes; SHA-256
`67a7589e72a7a26d55a16c47aeb8b3e6ad6a9baca5019cc56c302d9e78b51ed0`).

Resident-media policy and connected shell coverage passed 53/53. Live resident
media perception/enjoyment remains unaccepted. Checkpoint SHA-256:
`3eab84b8a07cc13a8c2a8274c98bc10e43e667253f0b3a24a200644a9d33c498`.

Voluntary-media v3 is independently rejected as a live trust root despite
17/17 focused tests. Fresh probes accepted a plain decline as `YES`, an
arbitrary source digest, a reused nonce, and a future-dated choice; durable
event append/reopen is not an atomic state-transition precondition. Preserve
v2/v3 unchanged and do not run the old media harness. Exact audit:
`RecoverySprint/continuation_20260810/resident_media_voluntary_v3_fresh_static_audit/attempt_01/CHECKPOINT.md`
(5,396 bytes; SHA-256
`cd1425598b27af574e253e36d0f8115330fcbdb8697fb40d5df26f891baa6eb4`).

Blackwell voice latency v3 is independently rejected before live use despite
passing its own 25/25 tests. Fresh hostile audit reproduced ten cleanup,
residency, locking/cancellation, finite-resource, identity/configuration,
TTL/ownership, and measured-unload blockers. No live CPU park, GPU/audio, or
owner-hearing run is authorized for v3; v2 remains unchanged. Audit SHA-256:
`a7d0aa53aae4cf03d5c424b6bba169acec5373fe8dd63756bf07f211bc38c3b0`.
Append-only v4 passed its own 27/27 static tests but is independently rejected
before live use. Fresh hostile audit reproduced seven remaining blockers:
Qwen/voice overlap races during initial load and resume, malformed-stream
state/ownership leakage, unbounded backend cancellation, invalid/nonexistent
artifact acceptance, mutable resource limits, and configuration-drift cleanup
that can leave CUDA voice loaded. Playback remains unimplemented. No live CPU
park, Qwen sequence, synthesis, playback, or owner-hearing run is authorized
for v4. Preserve v2/v3/v4 unchanged. Exact audit:
`RecoverySprint/continuation_20260810/blackwell_v4_cpu_park_fresh_static_audit/attempt_01/CHECKPOINT.md`
(12,903 bytes; SHA-256
`454462a6be1b4300d2c184149c1723f19dbecbf6b4aa8759f874919da6f1e7df`).
Append-only v5 is static-only pending its own fresh independent audit.

Kira R25 AFES v3r5 is independently rejected for Blender execution despite
65/65 internal static/hostile tests and a clean `/W4 /WX` build. The exact PE
imports `python314.dll` normally before `wmain` and has no delay-import entry,
allowing Python DLL authority before manifest locking and runtime
verification. No executable, controller, bootstrap, wrapper, AFES, Blender,
mesh, output, or body operation ran. Preserve v3r4/v3r5 unchanged. Exact
audit:
`RecoverySprint/continuation_20260809/kira_r25_foundation_afes_locked_pair_execution_static_preparation/attempt_03r5/INDEPENDENT_AUDIT.md`
(6,306 bytes; SHA-256
`f1cf359b5338714cbd76237252d675903c1d1d3dcb97653c3b8642ccf4a7ca1b`).
Only an append-only delayed-import repair with a new exact-byte audit may
advance toward a bounded Blender command.

The no-model self-identity fallback no longer recites obsolete
`16GB/small/hollow` wording or substitutes a generic memory notice; expanded
conversation coverage passes 150/150 with 23/23 subtests. Registry-pointer
integrity coverage passes 6/6 with 5/5 subtests. The registry separately marks
adult-health prompt knowledge vs unimplemented lived/body systems, session
emotion wiring vs durable subjective experience, and promoted memories vs
draft backstory/reconstruction material.

<!-- END 2026-08-10 QWEN ATTEMPT 06 / TEMPORAL MEMORY / MEDIA AUDIT -->

<!-- BEGIN 2026-08-10 QWEN ATTEMPT 09 PRESENT-STATE REPAIR -->

Exact Qwen 3.5 present-state grounding now rejects invented "just finished" or
"wrapped up" causes and old media/project/class/club/collaborator drops when no
fresh daily-life or current-session fact exists. Memories and personality were
not rewritten; Qwen still supplies one exact public generation. Static coverage
passes 103 tests and 140 subtests. Exact checkpoint:
`RecoverySprint/continuation_20260810/qwen35_attempt08_present_state_temporal_repair/attempt_01/CHECKPOINT.md`
(4,192 bytes; SHA-256
`13836decf0b2b6a8220997e6363d8d6455702f441b8811a729088c3f05b30305`).

No-playback Attempt 09 passed its new content, exact-Qwen, approved Blackwell-v2
GPU, no-fallback, WAV, and cleanup gates. Text completed in 8.170095 and
5.642666 seconds; external voice calls took 7.502909 and 11.571091 seconds. No
audio was played, so this remains pending owner hearing and is not conversational
latency acceptance. Exact report SHA-256:
`ce8ce9682b652d5bd1b8323febe81884e77ddd437ebc63ca72f57c834ce3f886`.

R25 AFES v3r7 and resident-media v5 are frozen/static candidates awaiting fresh
independent audits. Blackwell CPU-park v6 remains static-only pending seal and
audit. None has live authorization.

<!-- END 2026-08-10 QWEN ATTEMPT 09 PRESENT-STATE REPAIR -->

<!-- BEGIN 2026-08-10 POST-ATTEMPT09 BODY MEDIA LATENCY AUDITS -->

R25 AFES v3r7 received exact-byte static acceptance for one read-only pair,
but the auditor-recorded command omitted all six mandatory bootstrap-seed
tokens after `--`. Root used the command exactly once; it failed closed in
under five seconds without an outcome, output root, Blender process, save,
render, or body change. The invocation is consumed and no rerun is authorized.
Accepted audit SHA-256:
`571c678f3db472c824a6ed1b4eb0508b93bb680b1da795dfb155e63513c14f10`.
Post-run rejection checkpoint SHA-256:
`6604cebf9650033c76d1b893189bbb1fba76201a4ee47f7cace448fff1f9d1be`.
Append-only v3r8 is static-only in authoring and needs a different fresh audit.

Resident-media v5 is independently rejected before live use. Exact audit
SHA-256:
`54d65343a7eca2c867d62b682cbffbccdc80508e788dae83c4f48f6ddb6be165`.
Append-only v6 is static-only in authoring; no media experience is accepted.

Blackwell CPU-park v6 is independently rejected before any adapter/live run.
Exact audit SHA-256:
`dcd260cd2e912db7d8018eb7cf781831b6d24c366d7edf8e162be1fa74894ed8`.
Approved production v2 remains unchanged. Append-only v7 is static-only in
authoring; no experimental synthesis, playback, or owner-hearing run is
authorized.

<!-- END 2026-08-10 POST-ATTEMPT09 BODY MEDIA LATENCY AUDITS -->

<!-- BEGIN 2026-08-10 R25 V3R8 SEAL AND MEDIA V6 REJECTION -->

R25 AFES v3r8 is sealed static-only after 89/89 authored tests. Its bootstrap
seed now derives internally from the exact locked contract/audit/manifest state
and external `--` seed arguments are rejected. No v3r8 executable or Blender
path ran. Checkpoint SHA-256:
`8541ebf17f4298abaa13df0908335224584e69027bd0328e6538553200c3f402`.
Fresh different-agent exact-byte audit remains mandatory before one bounded
read-only pair can be considered.

Resident-media v6 is independently rejected. Its normalizer deleted
non-ASCII semantic content and therefore accepted negative emoji/non-English
refusal mixtures as `YES`/`CONTINUE`. Independent probes reproduced 3/3.
Rejection checkpoint SHA-256:
`ba5ddf21a10044ae9304b1ef81961c52f6902c60548ed48a819b05082d12d785`.
Preserve v6; no live media session is authorized.

<!-- END 2026-08-10 R25 V3R8 SEAL AND MEDIA V6 REJECTION -->

<!-- BEGIN 2026-08-10 R25 V3R8 FRESH AUDIT REJECTION -->

Fresh exact-byte audit rejects v3r8: its contract adds
`locked_pair_v3r7_preservation`, but the exact child wrapper allowlist and
preservation loop stop at v3r6. The child would reject the contract before
AFES. Nothing executable or Blender-related ran. Rejection checkpoint SHA-256:
`a667b03f4a3de443609379cd3c7c368cfe1a1fd9dc9ca62e3593d4238cde10fe`.
Append-only v3r9 is the narrow static-only successor; no v3r8 command is
authorized.

<!-- END 2026-08-10 R25 V3R8 FRESH AUDIT REJECTION -->

<!-- BEGIN 2026-08-10 BLACKWELL V7 STATIC SEAL -->

Blackwell v7 is sealed static-only after 32/32 authored hostile tests and is
under different-agent audit. Checkpoint SHA-256:
`df3a5c6a62043fbcc4b890abbbd5d3a406bf66839f29b6edd116830864ddab33`.
Approved production v2 remains unchanged; no v7 live model, GPU, audio,
playback, or person-state operation is authorized.

<!-- END 2026-08-10 BLACKWELL V7 STATIC SEAL -->

<!-- BEGIN 2026-08-10 EXACT QWEN CURRENT-ROUTE REVALIDATION -->

Static current-route verification passed 24/24 with no model call. All normal
person routes require exact Qwen 3.5 name and digest; Llama 3.1 is dormant or
historical only. Checkpoint SHA-256:
`9e99ff0817dd726a5804ca0ef5027e6219c59f72e54b46ebb40d6326108cc314`.

<!-- END 2026-08-10 EXACT QWEN CURRENT-ROUTE REVALIDATION -->

<!-- BEGIN 2026-08-10 GENERATED-EXPERT CURRICULUM WIRING AND BLACKWELL V7 AUDIT -->

Five exact generated-expert confirmed adults now receive the pinned
source-backed adult curriculum on their normal Qwen shell request. Exact
identity is mandatory; Marinette, Peter, aliases, and unclassified people do
not inherit it. This is educational system context only, not anatomy, consent,
lesson completion, memory, sensation, action, or experience. Static/mocked
verification passed 34/34 plus 57 current shell regressions (one privilege
skip). Checkpoint SHA-256:
`5c5c147ed95a9ccaa1f4ae67e98dc0843fc46d82c1c11679b561681b05687e3e`.

Blackwell v7 passed fresh static audit (32/32 authored; 35/35 independent) but
remains `ACCEPT_STATIC_ONLY` because the live adapter and playback are absent.
Audit SHA-256:
`54ee6b70a58ac5a70f5de0e7713538a54cdb47fd1949f1624c5fabdb68474310`.
No v7 live run is authorized; v8 is append-only/static-only in authoring and
production v2 remains selected.

<!-- END 2026-08-10 GENERATED-EXPERT CURRICULUM WIRING AND BLACKWELL V7 AUDIT -->

<!-- BEGIN 2026-08-10 KIRA R22 BOUNDED REVIEW, R25 V3R9 CONSUMPTION, AND VOICE FORGE R6 AUDIT -->

Kira R22 external-anatomy Attempt 07 saved and rendered ten private views but
is rejected: the pelvic correction remains a raised narrow strip with straight
construction/colour lines, and the exact mesh audit reports 84 genuine
nonadjacent penetration pairs (55 patch-related, 29 outside the patch).
Attempt 05 is the first completed bounded visual repair; Attempt 06 is a
preserved pre-mutation helper failure; Attempt 07 is the second completed
bounded result. Nothing was activated, assigned, clothed, exported, or called
functional. Exact checkpoint SHA-256:
`443e5ed2d32d34a11a3eccd931a55fe0a03354da818ffe68f05341fca47c1e17`.

The normal Avatar Builder Kira Review Gallery now shows 107 exact hash-bound
images across eight sections and labels Attempts 05/07 rejected. Workspace
tests pass 18/18. HTML SHA-256:
`82f53aff6100dced0b6ebee4ed9be9c78cf6f7420326bbe8808ae309076f0eeb`;
manifest SHA-256:
`1a1ff163ff72a0d8ba11cc6a5a1e84842e1b77d6d032642257dfc0742fbcc740`.

R25 AFES v3r9's accepted one-shot read-only invocation was consumed by a
tool-boundary exit `1` with empty streams and no outcome/output/Blender/body
change. No retry is authorized. Final postmortem SHA-256:
`275fd7501a5d35ec6c5648a3935cafa56eb7854dfb80c173a2adc364738afed3`.

Voice Forge R6 is independently rejected despite its authored static passes.
It accepted an unparsed rejection audit, invalid evaluator ranges,
zero/arbitrary telemetry, ledger-selected later-use identity, and lacked R5's
held Windows final-file-identity commit. No voice was generated. Audit SHA-256:
`9094838509d115091da568dab55db8d6ab0a73c2642063f59f173da80cb56d10`.

Resident-media v7 is accepted for its static choice-gate core only after
104/104 preserved tests, 15/15 hostile tests, and 10/10 additional
mixed-language/emoji/refusal cases. Fresh audit checkpoint SHA-256:
`383d67fe8236fc3227b5ec3183436412bcc2e511b8cd8e977206e2ab14ac1f72`.
Its protected production clock/anchor backend and live source-time evidence
remain missing. Blackwell v8 is sealed static-only after 31/31 new and 32/32
inherited tests; its live adapter and playback exist but are unvalidated,
default-off, and pending a different fresh audit. Checkpoint SHA-256:
`094a79d7e99a4059471ad7e87a6faf8c98bb2776b976885b769ab5a1e94affa8`.
Voice Forge R7 remains static-only in progress. Production voice remains
approved Blackwell v2; no live media or experimental voice run is authorized
by this block.

<!-- END 2026-08-10 KIRA R22 BOUNDED REVIEW, R25 V3R9 CONSUMPTION, AND VOICE FORGE R6 AUDIT -->

<!-- BEGIN 2026-08-10 BLACKWELL V8 AUDIT, OWNER HEARING, AND REFLECTION REBIND -->

Blackwell v8 is accepted only as a static sealed source boundary. Fresh audit
SHA-256:
`934091af02deda78ec607e696c088d01848db7451f2f25036b14ab64b87f4458`.
No live adapter, model, GPU, synthesis, playback, person-state operation, or
production promotion is authorized; Blackwell v2 remains production.

Robert heard the content-correlated Attempt 06 output, liked the voice, and
heard no gap, but rejected its months-old fanfic/book-club content. Feedback
checkpoint SHA-256:
`b15b59e361f808b3522eb07483e78fd83175f91c57e714b658da50c722b69c8e`.
The corrected Attempt 09 WAV was not played because the later playback request
was rejected before sound began; boundary checkpoint SHA-256:
`e7dbc5c3345009d30a8b374ccd464b0c9c99b2b9de71ee58e5906c69a98604a3`.

The Kira/Lisa college-reflection runtime's two changed control-document hashes
were refreshed after a fail-closed test. Adult-curriculum wiring passed 27/27;
reflection/emotion wiring passed 21/21. This proves binding and prompt policy,
not private reconstruction display or lived bodily/emotional experience.
Checkpoint SHA-256:
`55388335001673f962b2c3eb2c2835c6a3c56a6eaa700c579cd8fdaf5afe6a93`.

<!-- END 2026-08-10 BLACKWELL V8 AUDIT, OWNER HEARING, AND REFLECTION REBIND -->

<!-- BEGIN 2026-08-10 VOICE FORGE R7 STATIC SEAL -->

Voice Forge R7 is sealed static-only with 18/18 focused, 9/9 hostile, and 24/24
R6-preservation checks passing. Its exact collision corpus has zero accepted
voices, so it fails closed before worker launch. No synthesis is authorized;
different-agent audit remains pending. Checkpoint SHA-256:
`7a347467864bb605913541b0dad260483b21a56006b3b89e62a7ed29e6a878c7`.

<!-- END 2026-08-10 VOICE FORGE R7 STATIC SEAL -->

<!-- BEGIN 2026-08-10 R25 V3R10 PRE-OUTCOME DIAGNOSTIC SEAL -->

R25 v3r10 is a sealed native diagnostic-only successor. It passed 22/22 static
hostile tests and cannot reach Python, AFES, Blender, body mutation, save, or
render. A different audit is mandatory before one diagnostic invocation.
Checkpoint SHA-256:
`36d759569f6819423e6daef950c11939e72adbabfbd188af492a168aab1c2dbf`.

<!-- END 2026-08-10 R25 V3R10 PRE-OUTCOME DIAGNOSTIC SEAL -->

<!-- BEGIN 2026-08-10 VOICE FORGE R7 AND R25 V3R10 FRESH REJECTIONS -->

Voice Forge R7 fresh audit verdict is `REJECT`. Four hostile states remained
accepted: excessive authorization lifetime, impossible CUDA accounting,
contradictory RSS timing, and a negative Job termination counter. No synthesis
or live resource ran. Report SHA-256:
`577fd3cf047fbaa0abddeea7dfb7f86602b6b94f97b9f43a724d77affc7ab966`.

R25 diagnostic v3r10 fresh audit verdict is `REJECTED_NO_EXECUTION_AUTHORITY`.
Its CRLF manifest cannot pass its LF-only magic verifier; additional binding,
child-reservation, and loader-boundary defects remain. No child, Python, AFES,
Blender, body, save, or render operation ran. Checkpoint SHA-256:
`211c571d0a82f4a94b3eb04c1213d95920da5738b52cae11c3277b879a36a511`.

<!-- END 2026-08-10 VOICE FORGE R7 AND R25 V3R10 FRESH REJECTIONS -->

<!-- BEGIN 2026-08-10 BLACKWELL V8 LIVE HARNESS AUDIT AND OUTER BOUNDARY -->

The Blackwell v8 bounded-live harness received fresh static acceptance for one
later bounded run; audit checkpoint SHA-256:
`dd76dda45f9c73855d6cc500649b7423f940449f87f6fbbd05c9836cb227a962`.
The one attempted tool request was rejected before shell start at the Codex
usage-limit boundary. No attempt was reserved and no model/GPU/audio/playback
operation ran. Boundary checkpoint SHA-256:
`ef88b5d11b5f7d82535138ac34b2a4c97415c7794294227a9db849732ab8204f`.

<!-- END 2026-08-10 BLACKWELL V8 LIVE HARNESS AUDIT AND OUTER BOUNDARY -->

<!-- BEGIN 2026-08-10 VOICE FORGE R8 STATIC DISCONNECTED ACCEPTANCE -->

Voice Forge R8 fresh verdict is `ACCEPT_STATIC_ONLY_DISCONNECTED`. All four R7
guard defects are closed in static tests, but no parent/worker/authorization or
accepted voice corpus exists, so synthesis remains impossible and unauthorized.
Candidate SHA-256:
`9f07b08e7f472a7981d4d981e26746e1981744a5323aa63f97a07c20c1144171`.
Audit SHA-256:
`941764a54f16ecafb2034c03cdfbb1060271a3c3eb539c2ff58aff603938c4aa`.

<!-- END 2026-08-10 VOICE FORGE R8 STATIC DISCONNECTED ACCEPTANCE -->

<!-- BEGIN 2026-08-10 R25 V3R11 INCOMPLETE BLOCKER -->

R25 v3r11 is incomplete, non-buildable, and has no execution authority. No
identity header, test, EXE, OBJ, compile, child, Python, AFES, Blender, body,
save, or render exists from this attempt. Blocker checkpoint SHA-256:
`7043923f02889ae9994a56af7a4cabaa74968dcc9902e74c2556bfcebc0fa83f`.

<!-- END 2026-08-10 R25 V3R11 INCOMPLETE BLOCKER -->
