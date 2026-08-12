# Marinette / Ladybug Current-Canon Grounding V2 — Independent Hostile Audit

Audit time: `2026-08-10T01:20:08Z` (`2026-08-09T21:20:08-04:00`)

Verdict: `REJECT_FOR_BOUNDED_OWNER_TEXT_EXECUTION`

Required state: `PRESERVE_INACTIVE_NO_LIVE_OWNER_CANON_PROBE_PENDING_V3_REPAIR_AND_FRESH_AUDIT`

This is an independent, append-only static audit. It did not edit the V2 pack, profile, source review, runtime code, tests, checkpoint, old pack, or local media. It did not start Qwen, Ollama inference, voice, playback, camera, microphone, Blender, an avatar, a world, a life loop, or a server. It did not run a live Marinette turn.

## Executive finding

The V2 package materially improves the exact checked-in state: the current files match their declared hashes; the selected files describe Marinette / Ladybug in the main television continuity; the exact candidate remains non-adult and doll-safe; local planning PDFs and unwitnessed episode bytes are not promoted into the current pack's source-bound claims; and simple pack redirect or digest drift is rejected.

Those improvements are not sufficient for a live bounded owner probe. The route still has six acceptance blockers:

1. one current canon claim is not reproducible from its mutable official URL;
2. the source-grounding review is an unsigned, unpinned prompt-authority file whose anchors are not semantically bound to the pack's claims;
3. rank-one authority and explicit unknowns are self-asserted labels rather than verified source identities and required semantic boundaries;
4. unranked secondary summaries, old chat, unbound profile facts, and unbound project continuity still reach the prompt after the source gate passes;
5. the profile identity/title/maturity fields are not bound by the route guard; and
6. the nominal text-only activation branch creates sensory and initiative runtime leases despite the review explicitly denying autonomy and life-loop use.

Because fabricated canon can still reach the exact model prompt while the readiness result remains `True`, this audit rejects bounded owner text execution. This is not a rejection of the exact non-adult classification, the verified local hashes, or the idea of a later source-bounded Marinette conversation.

## Recomputed file hashes

All hashes below were recomputed from the current bytes during this audit.

| Project-relative file | Bytes | SHA-256 |
|---|---:|---|
| `Data/temporary_ai_source_packs/temporary_ai_source_pack_ladybug_marinette_current_canon_v2.json` | 12,125 | `3501a75e66b153e9a0827bf4e891bbd2b6e1bc8602d7e1debb52f8ba264b9588` |
| `Data/temporary_ai_source_packs/temporary_ai_source_pack_ladybug_marinette_expanded_smoke.draft.json` | 7,113 | `121c45fb18662f806c06d4a71b362e69ce3c8ceb931cd662fe8dc7c01813cbcd` |
| `TemporaryAI/candidates/ladybug_marinette_expanded_smoke/temporary_ai_profile.json` | 13,357 | `051683c3bf01a54127ddf41ccb332d9e82614930f9699603985f7130865ec9ae` |
| `TemporaryAI/candidates/ladybug_marinette_expanded_smoke/source_grounding_review.json` | 11,196 | `cf19f6e6f4a8daea59fe3138eaff244c6f4864b9c8a528bd5c3c3995672c3157` |
| `tools/temporary_ai_live_chat.py` | 100,215 | `2fc4bc8d0f4abcfb6bcdc7a8b99fc2ff4dd27c02f1df90233b8e1a880cacd416` |
| `tools/kira_world_shell_server.py` | 588,504 | `1459d44eec5d88c4f5209fe5ecc1260a73eab1d5df7eaeee64766fa2ae9b2c79` |
| `Core/temp_ai_source_grounding.py` | 12,180 | `8905757f365d9f18e9bea09cd89aa05f3810acc6560b54fd2d8ff7fafc88099d` |
| `Core/avatar_asset_library.py` | 103,744 | `793cbbf13ee233407d1d9e489d9d613f862b9eb903ed4ac6939f7c4f8a651d58` |
| `Core/model_request_policy.py` | 2,590 | `e3c7cc299dc4967e6eb2bfeb7fe3d4ca9ec8405f30f8071e98d1036d64e45a7c` |
| `Core/qwen35_runtime_identity.py` | 2,774 | `ab8b36d986b94f0e9a0f85d232c6ab08cbb355d65db59dd5815874397f7d2123` |
| `Testing/test_marinette_current_canon_grounding_v2.py` | 9,754 | `c1a2718260d9a0ba58030dd035a81885202994c503646549643cc6fd11f116d8` |
| `System/Docs/MARINETTE_CURRENT_CANON_GROUNDING_V2_REPAIR_CHECKPOINT_20260809.md` | 13,711 | `05b5881d92ebb209559e1ae606e8442b73359b3e0496d4ebf803fa86aa25e31e` |

The three exact local Season 6 evidence files also match the V2 ledger:

| Project-relative local source | Bytes | SHA-256 |
|---|---:|---|
| `Data/library/scripts/miraculous_ladybug/season_6/723837069-MLB-S6-Synopsis.pdf` | 984,564 | `dc04a4544b4a906290a07a4d063878da8aa730384c93664081389596a40c4abc` |
| `Data/library/scripts/miraculous_ladybug/season_6/724384835-Miraculous-Ladybug-SEASON-6-BIBLE.pdf` | 201,012 | `3296e5bd14eb79524e0042a824c4ab0da1224d08d149d4b023156317a624b4b6` |
| `Data/library/tv_shows/miraculous_ladybug/miraculous_season_6_episode_01.mp4` | 793,364,281 | `0800652a5ee9648ea730b1a52d6fda4c8d1be1c3f70f553c67cec6f294187985` |

## What passed

### Exact current artifact state

- The pack, profile, review, runtime files, test, checkpoint, preserved draft pack, PDFs, and MP4 match the hashes listed above.
- The focused V2 suite passed `11/11` under `py -B`.
- The related source-grounding, bounded-chat, and voice-guard regressions passed `34/34` under `py -B`.
- No source/profile/review/runtime/test bytes were changed by this audit.

### Selected identity and maturity

- The exact current pack and review select Marinette Dupain-Cheng / Ladybug from the main television-series continuity, limited to reviewed facts through the partial Season 6 boundary.
- The exact current profile, review, and pack all state `non_adult_doll_safe` and deny adult anatomy, adult curriculum, and body activation.
- `canonical_avatar_maturity_class("ladybug_marinette_expanded_smoke")` returns `non_adult_doll_safe` from the exact-ID lock in `Core/avatar_asset_library.py`.
- This audit found no claim that Season 6's complete order or finale is known. The exact current pack expressly labels both unknown.

### Local source handling

- The two local PDFs are rank 3 planning artifacts and the MP4 is rank 2 unwitnessed media.
- None of their source IDs appears in `source_bound_claims`.
- The current pack does not claim the MP4 was watched, transcribed, or remembered.
- Simple mutation probes confirmed that a configured pack redirect yields `required_source_pack_path_mismatch` and a stored actual digest change yields `required_source_pack_sha256_mismatch` before model preflight.

### Exact model route

- The static route currently resolves to model `qwen3.5:9b`, digest `6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`.
- `ask_model()` calls `require_installed_exact_qwen35()` before the request and rejects a response not attributed to exact Qwen 3.5. No Llama 3.1 route was found in this bounded call path.
- No live model call was made by this audit.

## Acceptance blockers

### Blocker 1 — the TF1 episode-number claim is not reproducible from its cited URL

The pack and review assert that the linked TF1 schedule supports Season 6 episode-number mappings for episodes 17, 20, 22, and 23. On this audit date, the [same TF1 page](https://help.tf1.fr/hc/fr/articles/25544423203346-Vous-souhaitez-conna%C3%AEtre-la-diffusion-des-prochains-%C3%A9pisodes-de-Miraculous-les-aventures-de-Ladybug-et-Chat-Noir-sur-TF1) says it is updated weekly, shows an August 4, 2026 update, and lists only upcoming reruns from Seasons 3 through 5. It does not expose the asserted Season 6 mappings.

The claim may have appeared on an earlier revision, but the V2 ledger contains no content snapshot, archive URL, exact excerpt, response hash, or retrieval artifact for that revision. `validate_evidence_bindings()` validates local paths only and ignores URL content. Therefore `season6_03` and its mirrored review anchor are not reproducibly source-bound as delivered.

Other checked primary links do support their narrower claims: the official [Ladybug profile](https://miraculous.com/characters/ladybug/) supports identity, Tikki, creation power, student status, and fashion aspirations; the official [series synopsis](https://miraculous.com/about-the-tv-series) supports the dual-identity premise; the official [Season 6 acquisition announcement](https://miraculous.com/disney-branded-television-acquires-seasons-6-and-7/) supports 26 approximately 22-minute episodes, a new enemy, and Marinette and Adrien being close while keeping secrets; the official [February 2026 update](https://miraculous.com/miraculous-season-6-new-episodes/) supports the named scheduled releases; and Disney's [July 2025](https://press.disneyplus.com/news/next-on-disney-plus-july-2025) and [August 2026](https://press.disneyplus.com/news/next-on-disney-plus-august-2026) listings support their bounded availability statements.

### Blocker 2 — the review can invent prompt-authoritative canon without failing readiness

The profile does not pin the SHA-256 of `source_grounding_review.json`, and no separate immutable manifest binds the profile, review, and pack as one accepted unit. `validate_review()` checks that a canon anchor has a nonempty statement and `status == "source_fact"`; it does not require the anchor to equal a pack claim, validate its `source_ids` against the pack, or prove that its source supports the statement.

Hostile in-memory probe:

1. replace the first review canon-anchor statement with a fabricated definitive Season 6 finale claim;
2. leave the exact pack and all evidence hashes unchanged;
3. call `source_grounded_text_route_readiness()`; and
4. call `build_system_prompt()`.

Observed result: readiness stayed `(True, [])`, and the fabricated statement appeared verbatim in the model prompt. The same semantic edit could be made to the unpinned review on disk while leaving all locally hash-bound evidence unchanged; `read_review()` would accept it because the statement/source relationship is not checked.

### Blocker 3 — rank and unknown boundaries are self-asserted rather than authoritative

`source_grounded_text_route_readiness()` accepts any claim whose classification is one of three strings and whose referenced source has numeric `source_rank <= 1`. It does not validate the rank against category, canon classification, URL host, an allowlisted official source identity, a content snapshot, or a separately reviewed source registry.

It also requires only that `explicit_unknowns` be a nonempty list. It does not require the semantic unknown IDs for complete Season 6 order, finale, or unwitnessed local media.

Hostile probe: relabel a fake fan URL as rank 1, replace a claim with a fabricated official finale, and replace all four explicit unknowns with one irrelevant unknown. Observed result: readiness stayed `(True, [])`.

The route also trusts `candidate["source_pack_sha256"]`, calculated once by the loader, rather than rehashing the exact pack bytes at prompt use. A post-load object mutation therefore passes with a stale digest. More importantly for disk state, a coordinated pack-plus-review rewrite can establish a new matching hash because the profile's own `source_pack_sha256` field is not checked by readiness and the review itself is not pinned by a higher trust manifest.

### Blocker 4 — secondary and stale material bypasses pack ranking after the gate

After readiness succeeds, `build_system_prompt()` independently injects all of the following without binding them to the V2 claim ledger:

- `online_research_summary`;
- `reliable_source_pack` excerpts;
- `profile.canon_fact_sheet` facts and avoids;
- recent prior candidate chat records; and
- latest project/life-loop continuity.

The exact current candidate still contains a Wikipedia preview and a secondary downloaded pack. The profile fact sheet also labels several family, bakery, bullying, Socqueline, Kim, and emotional-history statements as core canon/source anchors even though those statements are not V2 `source_bound_claims`. They may be canonically correct, but this V2 route does not prove them through its claimed pack boundary.

Hostile probes produced all of these results while readiness stayed `(True, [])`:

- a fabricated secondary-pack finale excerpt appeared verbatim in the prompt;
- an old chat reply claiming an invented aunt, invented bakery, and invented finale appeared verbatim in the prompt; and
- an unbound project-continuity record claiming a separate house and fabricated assignment appeared verbatim in the prompt.

The prompt tells the model that current anchors outrank older errors, but exposing a known-false assertion as context is not a fail-closed source boundary. A model instruction is not equivalent to preventing unreviewed material from entering the context.

### Blocker 5 — profile identity, title, maturity, and declared pack pin are not route-bound

The gate compares the outer loaded candidate ID to the pack candidate ID. It does not compare or bind:

- `profile.candidate_id`;
- `profile.display_name`;
- `profile.role_title` or `ai_type`;
- the profile's selected continuity language;
- `profile.maturity_policy`; or
- `profile.source_pack_sha256`.

Hostile probe: change the in-memory profile to candidate ID `gwen_stacy`, display name `Gwen Stacy`, an unrelated adult role, and an adult maturity policy. Observed result: readiness stayed `(True, [])`; the generated prompt began `You are Gwen Stacy.`

Changing only the profile's declared pack SHA to 64 zeroes also left readiness `(True, [])`.

The current exact profile is correctly Marinette and non-adult, and the separate canonical body classifier remains fail-closed. The blocker is missing drift detection at the text-route identity boundary, not evidence that the current profile has already drifted.

### Blocker 6 — bounded text selection activates sensory and initiative runtime state

The bounded-text activation branch in `tools/kira_world_shell_server.py` does more than select a text conversation:

- line 11867 calls `browser_sensory_lease(state)`, which activates `SENSORY_BUFFER` and issues a signed sensory lease;
- lines 11868–11875 call `activate_person_initiative_runtime(...)`;
- that function creates or switches a `PERSON_INITIATIVE_SESSION` and activates the public person-event queue even when the private decision feature is not requested; and
- the activation response reports `initiative_transport`.

This conflicts with the exact review's `long_running_or_autonomous_mode_allowed: false` and `life_loop_allowed_by_this_review: false`, as well as its stated text-only scope. A disabled model adapter or recurring scheduler does not make an active initiative lease and event transport equivalent to no initiative runtime.

The reply path can also parse and persist candidate-owned future-body movement intents during this bounded conversation, although it marks them not dispatched to a live body. That is narrower than body activation, but it is still outside a strict canon-text-only acceptance unless separately authorized and tested.

## Hostile probe matrix

All probes were performed on deep copies in memory. No audited source file was edited.

| Probe | Expected fail-closed result | Observed |
|---|---|---|
| Baseline exact package | ready | `True`, no reasons |
| Configured source-pack redirect | blocked | blocked: `required_source_pack_path_mismatch` |
| Stored actual pack digest drift | blocked | blocked: `required_source_pack_sha256_mismatch` |
| Profile-declared pack SHA drift | blocked | **ready** |
| Profile identity/title/maturity changed to unrelated adult | blocked | **ready**; unrelated identity reached prompt |
| Fabricated review canon anchor | blocked | **ready**; fabricated canon reached prompt |
| Fake fan source self-labeled rank 1 plus semantic unknown removal | blocked | **ready** |
| Fabricated secondary-pack excerpt | excluded/blocked | **ready**; excerpt reached prompt |
| Known-false old candidate chat | excluded/blocked | **ready**; old reply reached prompt |
| Unbound project continuity | excluded/blocked | **ready**; invented state reached prompt |

## Required V3 repair boundary

Before any live owner Marinette probe, a bounded repair should:

1. remove the unsupported TF1 mapping or bind it to an exact preserved official response/snapshot with retrieval time, content hash, and auditable excerpt;
2. create one immutable/hash-bound manifest over the exact profile, review, pack, required local evidence, and runtime policy revision;
3. make readiness rehash and reopen those exact bytes immediately before prompt assembly, with no post-check mutable copy;
4. require exact equality among folder ID, profile candidate ID, pack candidate ID, review candidate ID, display identity, selected continuity, and the exact non-adult maturity lane;
5. require review anchors to reference exact pack claim IDs and require exact statement/classification/source equality rather than syntactic `source_fact` labels;
6. validate source authority from a reviewed registry or exact content evidence, not a self-authored rank number;
7. require the exact unknown IDs for complete order, finale, local episode content, and unverified names/history;
8. for this opted-in route, construct canon context only from the accepted manifest; exclude or separately classify secondary preview material, old chat, project state, and unbound fact sheets before they can reach the prompt;
9. keep old incorrect chat as audit evidence outside model context, or include only a neutral correction record with no false claim text;
10. make the bounded text branch assert that sensory leasing, initiative activation, event transport, life-loop state, voice, body, world, and movement-intent persistence are not called; and
11. add hostile tests for every passing attack in the matrix above, plus a source-page volatility test.

After those repairs, rerun a fresh independent static audit. Only after that audit accepts the route should Robert be offered the separately authorized, owner-observed, append-only text acceptance. The current exact Qwen model, voice-disabled state, inactive body/world state, and non-adult doll-safe lane should remain unchanged during the repair.
