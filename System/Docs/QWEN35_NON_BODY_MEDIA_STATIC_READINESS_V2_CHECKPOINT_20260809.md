# Qwen 3.5 non-body and resident-media static readiness v2 — 2026-08-09

Status: `STATIC_V2_BINDINGS_PASS_PENDING_INDEPENDENT_AUDIT`

## Outcome

An append-only v2 static binding now preserves the historical resident-media
harness digest as provenance while separately binding the current exact
Qwen-3.5 resident-media harness. The validator does not import either harness.
It reads each exact file once, verifies its bytes and SHA-256, parses the
current harness as inert Python syntax, and rehashes the four exact resident
library sources.

This closes only the stale-hash preparation blocker. It does not authorize a
live model call, media decoding, playback, speaker output, camera, microphone,
person activation, memory promotion, or body/Blender operation.

## Preserved and current bindings

- Historical harness provenance SHA-256:
  `d7b527397c8c630dfda01834191b8839c4fc4300c372c6517e5926cb03267773`.
- Current Qwen-repinned harness SHA-256:
  `f56927167a92eadf88f2ea9b61ef5a6ece9d8e96bc53f3d696331188e2279e23`.
- Exact model: `qwen3.5:9b`.
- Exact digest:
  `6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`.
- Media-question digest:
  `3da59a2279f70b573887661c26c492603eb2a15fda3763406a0a09dbd3c3b4e2`.
- Separate behavior-question digest:
  `75244e80adc2c3ec541bd56c5c2e8bee16858f5e81360b14fce8768201f468d3`.

The four exact source records remain one illustrated PDF page, one unfamiliar
PDF crop, one eight-second video interval, and one ten-second music interval.
Every source stays under `Data/library`, and its current bytes match the exact
source hash recorded by the preserved readiness configuration.

## New append-only files

| Project-relative path | Bytes | SHA-256 |
|---|---:|---|
| `tools/prepare_qwen35_non_body_media_acceptance_v2.py` | 11,429 | `6f953073a91c05c4b0632d05961bd70ab5c6b4790cb3256eb70a40897eda765c` |
| `Testing/test_qwen35_non_body_media_acceptance_v2.py` | 2,893 | `f62a75aa6fc15f960877866f561db0d4688e49c131f25937a764dab87a386d50` |
| `RecoverySprint/continuation_20260809/qwen35_non_body_media_static_readiness_v2/attempt_01/READINESS_CONFIG_V2.json` | 2,904 | `a009876a89ac580577a9ea8ad42ba73993346efc6099d8f3ea5e4da0df126881` |

## Verification

- v2 focused static tests: 8/8 passed.
- v2 plus current resident-media/source/session/person-receipt regression:
  48/48 passed.
- Python compilation passed.
- `git diff --check` passed for the three v2 files.
- The preserved v1 overlay still fails closed in its four historical-hash tests;
  those failures are expected evidence of the old binding and were not hidden
  or rewritten.

## Truth boundary and next gate

No person has been shown, heard, read, watched, enjoyed, learned, preferred, or
remembered any media because of this static work. Prepared sources are not
experiences, frames are not a whole viewing, metadata or lyrics are not
hearing, and a model reply cannot establish consciousness or biological
humanity.

A fresh independent hostile audit must review these exact bytes before a live
v2 runner may be authored. Any later live run still requires Robert present,
exact source confirmation, exact Qwen identity, serialized model unloads,
speaker/capture truth, voluntary participation, and append-only receipts.
