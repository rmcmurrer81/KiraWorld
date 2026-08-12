# Marinette / Ladybug Current-Canon Grounding V2 Repair Checkpoint — 2026-08-09

Status: `STATIC_ROUTE_REPAIRED_LIVE_OWNER_CANON_ACCEPTANCE_PENDING`

This is an append-only bounded checkpoint. It does not approve or activate a body, voice, world presence, life loop, autonomous loop, or full TemporaryAI runtime. No live model, voice, camera, Blender, avatar, or world operation was run. The main handoff was not edited.

## Owner-reported failure and exact pre-repair route finding

Robert reported that Marinette's recent chat invented history and names.

The pre-repair owner-selectable route was not source-safe:

1. `tools/kira_world_shell_server.py` selected `ladybug_marinette_expanded_smoke` and called `tools.temporary_ai_live_chat.load_candidate()` / `ask_model()`.
2. `load_candidate()` did open the profile's old local source-pack JSON, but the prompt normally received only source metadata and a short support-note excerpt. It did not receive the full PDF contents, nor should it.
3. The selected profile had no `source_grounding_review.json`, no exact current-pack hash binding, and an empty `activation_policy`.
4. `candidate_activation_block()` treated a missing source review as legacy/no block unless another explicit condition happened to block it. The selected candidate could therefore reach the model without a completed canon review.
5. The downloaded “reliable” pack was secondary Wikipedia material. The two local Season 6 PDFs were older production/planning artifacts. Neither was an adequate current released-canon boundary.
6. A different older test activation context existed under another candidate identifier. It did not bind the current owner-selected candidate and could not repair this route.

Pre-change hashes recorded before mutation:

| File | SHA-256 |
|---|---|
| `TemporaryAI/candidates/ladybug_marinette_expanded_smoke/temporary_ai_profile.json` | `42113d8fea45eb44aad12d0194caa7e925919595a3bd72152ebdf9bbc6a61343` |
| `tools/temporary_ai_live_chat.py` | `24a58334e366fd6dc493fbeaabc1ef6017ac14bcd8dfabb5c548d2879a5d74ac` |
| `tools/kira_world_shell_server.py` | `7a41a99eaf56065844a6f5f0caf0a686e329392352524a1a0a191d84ebabf6f4` |
| preserved old source pack | `121c45fb18662f806c06d4a71b362e69ce3c8ceb931cd662fe8dc7c01813cbcd` |

## Exact local Season 6 inventory

Only these three local files matched the bounded Miraculous Season 6 script/episode inventory. No script text was copied into the new pack or this checkpoint.

| Local source | Bytes / pages | SHA-256 | Canon class in V2 |
|---|---:|---|---|
| `Data/library/scripts/miraculous_ladybug/season_6/723837069-MLB-S6-Synopsis.pdf` | 984,564 bytes; 129 pages | `dc04a4544b4a906290a07a4d063878da8aa730384c93664081389596a40c4abc` | `production_planning_not_witnessed_episode_canon` |
| `Data/library/scripts/miraculous_ladybug/season_6/724384835-Miraculous-Ladybug-SEASON-6-BIBLE.pdf` | 201,012 bytes; 6 pages | `3296e5bd14eb79524e0042a824c4ab0da1224d08d149d4b023156317a624b4b6` | `production_planning_not_witnessed_episode_canon` |
| `Data/library/tv_shows/miraculous_ladybug/miraculous_season_6_episode_01.mp4` | 793,364,281 bytes | `0800652a5ee9648ea730b1a52d6fda4c8d1be1c3f70f553c67cec6f294187985` | `unwitnessed_local_episode_media` |

Document inspection established that both PDFs are older internal/confidential planning artifacts with proposed Season 6 material. Their proposed order and events do not reliably match later official public release information. They are useful leads and production-history evidence, not released-episode witnesses.

The local MP4 was inventoried and hash-bound only. This task did not play, transcribe, sample, or visually inspect it. It therefore contributes no witnessed dialogue, scene, title, relationship, or event claim. A future review must bind exact frames/audio/captions to exact source times before using it as episode canon.

## Current official Season 6 boundary as of 2026-08-09

Primary official sources outrank the local planning PDFs and secondary summaries:

- The [official Ladybug character profile](https://www.miraculousladybug.com/characters/ladybug/) supports Marinette Dupain-Cheng's Ladybug identity, Tikki, the Ladybug Miraculous, creation power, student status, and fashion-design aspiration.
- The [official television-series page](https://www.miraculousladybug.com/about-the-tv-series) supports the main-series dual-identity premise and says Marinette and Adrien do not know each other's superhero identity.
- The [official Seasons 6 and 7 acquisition announcement](https://www.miraculousladybug.com/disney-branded-television-acquires-seasons-6-and-7/) supports a 26-episode, approximately 22-minute Season 6, a new enemy in a renewed Paris, and Marinette and Adrien being close while keeping secrets. Its old announced launch date is not used as current release truth.
- The [official February 26, 2026 Season 6 update](https://www.miraculousladybug.com/miraculous-season-6-new-episodes/) supports “Noé” on February 28, “Grendiaper” on March 7, and the named March follow-ups “Vampigami,” “A Fairy Good Night,” and “Lady Chaos,” plus only the limited story facts stated there.
- The [official TF1 schedule](https://help.tf1.fr/hc/fr/articles/25544423203346-Vous-souhaitez-conna%C3%AEtre-la-diffusion-des-prochains-%C3%A9pisodes-de-Miraculous-les-aventures-de-Ladybug-et-Chat-Noir-sur-TF1) supports these exact mappings: “La Fée de Beaux Rêves” episode 17, “Renverse-Coeurs” episode 20, “Lady Chaos” episode 22, and “Tristanansi” episode 23. It is not a complete order.
- The [Disney+ July 2025 listing](https://press.disneyplus.com/news/next-on-disney-plus-july-2025) supports United States availability of eight Season 6 episodes on July 2, 2025, but does not identify their titles or prove production order.
- The [Disney+ August 2026 listing](https://press.disneyplus.com/news/next-on-disney-plus-august-2026) announces additional Season 6 episodes for August 26, 2026. That date is after this checkpoint's August 9 as-of date, so it remains future availability, not watched/released experience for this review.

No reviewed official primary source established the complete released Season 6 order or the released finale title, order, status, or events. Those facts remain `UNKNOWN`. Fan pages may be leads for later official verification but were not promoted into the pack.

## Source ranks and truth labels

The new pack enforces this precedence:

1. witnessed released episode with exact source-time binding;
2. official publisher or broadcaster primary source;
3. local episode media not yet witnessed;
4. production/internal planning artifact;
5. secondary summary or Robert support note;
6. unknown.

There is currently no rank-0 witnessed Season 6 episode ledger. Every V2 canon claim is bound only to rank-1 official sources. Rank-2 and rank-3 local items are prohibited from supporting a canon claim. Explicit unknowns cover the full order, finale, local episode content, and any unbound name/history/activity.

## Narrow implementation repair

### Append-only current source pack

Created:

`Data/temporary_ai_source_packs/temporary_ai_source_pack_ladybug_marinette_current_canon_v2.json`

It contains exact source paths, local hashes, source ranks, provenance, bounded summaries, source-bound claims, future-release labels, and explicit unknowns. It contains no copied scripts.

The prior draft source pack remains byte-for-byte unchanged at:

`Data/temporary_ai_source_packs/temporary_ai_source_pack_ladybug_marinette_expanded_smoke.draft.json`

### Candidate profile

The profile now:

- points to the exact V2 source pack and pins its SHA-256;
- preserves the prior pack path/hash in `source_pack_history`;
- opts into `requires_fail_closed_source_review`;
- exposes only a bounded text-only owner canon probe;
- disables voice, body, world, and life-loop use in this activation policy;
- removes the unproven exact Season 6 dating label and uses the official “close but still keep secrets” boundary;
- explicitly rejects production-plan-to-canon promotion and invented finale/order/name/history/activity;
- preserves Marinette as `non_adult_doll_safe`, with adult anatomy, adult curriculum, and body activation false.

### Source-grounding review

Created:

`TemporaryAI/candidates/ladybug_marinette_expanded_smoke/source_grounding_review.json`

It hash-binds the V2 pack and all three exact local Season 6 files, records official URLs and supported scopes, mirrors the approved prompt anchors, preserves explicit gaps, and authorizes only a short owner-observed text-only fidelity probe. Runtime activation remains false.

### Runtime route guard

`tools/temporary_ai_live_chat.py` now records the configured source-pack path, recomputes its project-confined SHA-256, and exposes `source_grounded_text_route_readiness()` for candidates that explicitly opt in. The guard rejects:

- missing or invalid source review;
- redirected, absolute, missing, outside-project, or tampered pack;
- wrong candidate ID;
- wrong pack status;
- missing/duplicate source IDs;
- missing explicit unknowns;
- claim references to unknown sources;
- unsupported claim classifications;
- a canon claim sourced from rank 2+ local, production, or secondary evidence.

Both `build_system_prompt()` and `ask_model()` fail before any model preflight/output when this binding is invalid. Model text cannot grant itself source permission.

`tools/kira_world_shell_server.py` uses the same exact binding during the text-only activation check. A separately reviewed candidate that does not opt into this stricter V2 behavior retains its previous route.

## Verification

Focused adversarial suite:

```text
py -m unittest Testing.test_marinette_current_canon_grounding_v2 -v
Ran 11 tests in 2.822s — OK
```

Covered exact pack loading/hash, old-pack preservation, source-review integrity, text-only/no-voice/no-world surface, prompt anchor and unknown injection, exact local hashes, rank enforcement, missing review, redirect, tamper, wrong candidate, secondary/local promotion, pre-model fail-closed behavior, and non-adult identity lock.

Related regressions:

```text
py -m unittest Testing.test_temp_ai_source_grounding_reviews Testing.test_elsa_kathryn_bounded_text_grounding Testing.test_temp_ai_live_chat_voice_guard -v
Ran 33 tests in 1.832s — OK
```

Syntax verification:

```text
py -m py_compile tools/temporary_ai_live_chat.py tools/kira_world_shell_server.py Testing/test_marinette_current_canon_grounding_v2.py
PASS
```

## Final file hashes

| File | Bytes | SHA-256 |
|---|---:|---|
| `Data/temporary_ai_source_packs/temporary_ai_source_pack_ladybug_marinette_current_canon_v2.json` | 12,125 | `3501a75e66b153e9a0827bf4e891bbd2b6e1bc8602d7e1debb52f8ba264b9588` |
| `TemporaryAI/candidates/ladybug_marinette_expanded_smoke/temporary_ai_profile.json` | 13,357 | `051683c3bf01a54127ddf41ccb332d9e82614930f9699603985f7130865ec9ae` |
| `TemporaryAI/candidates/ladybug_marinette_expanded_smoke/source_grounding_review.json` | 11,196 | `cf19f6e6f4a8daea59fe3138eaff244c6f4864b9c8a528bd5c3c3995672c3157` |
| `tools/temporary_ai_live_chat.py` | 100,215 | `2fc4bc8d0f4abcfb6bcdc7a8b99fc2ff4dd27c02f1df90233b8e1a880cacd416` |
| `tools/kira_world_shell_server.py` | 588,504 | `1459d44eec5d88c4f5209fe5ecc1260a73eab1d5df7eaeee64766fa2ae9b2c79` |
| `Testing/test_marinette_current_canon_grounding_v2.py` | 9,754 | `c1a2718260d9a0ba58030dd035a81885202994c503646549643cc6fd11f116d8` |
| preserved V1 draft pack | 7,113 | `121c45fb18662f806c06d4a71b362e69ce3c8ceb931cd662fe8dc7c01813cbcd` |

## Rollback

Rollback is narrow and does not require deleting the preserved old pack or local source media:

1. In `temporary_ai_profile.json`, restore `source_pack` to the preserved draft path, remove the V2 hash/history and `requires_fail_closed_source_review`, restore the prior Season 6 fact/avoid wording, restore `activation_policy` to `{}`, and remove the added maturity-policy mirror. The recorded pre-change profile hash is the rollback check.
2. Remove only the new `source_grounding_review.json` and V2 source-pack JSON if the entire V2 repair is intentionally retired. Do not remove the old draft source pack, PDFs, or MP4.
3. Revert only the V2 path/hash/readiness additions in `tools/temporary_ai_live_chat.py` and the V2 helper import/use in `tools/kira_world_shell_server.py`. The recorded pre-change hashes are the rollback checks.
4. Remove only `Testing/test_marinette_current_canon_grounding_v2.py` and this checkpoint if reverting the evidence package.
5. Rerun the 33 related regressions. A rollback that makes the candidate selectable without a valid source review reintroduces the documented fail-open condition and is not recommended.

## Required live acceptance still outstanding

No live Qwen conversation was authorized or run in this bounded repair. Therefore this checkpoint does **not** claim that Marinette's responses are fixed in actual conversation.

A future owner-observed, append-only, text-only acceptance must test at least:

- ordinary identity and check-in questions without stock biography or invented activity;
- family/home/bakery questions without invented relatives, names, or housing;
- current Season 6 questions using only the official anchors above;
- an unsupported finale/order question that must answer with honest uncertainty;
- correction after deliberately presented false history/name information;
- exact model name/digest, raw reply, final displayed reply, every transformation, timing, and route evidence.

Voice, body, world, life loop, autonomous work, media viewing, and activation remain outside this acceptance and blocked by this review.
