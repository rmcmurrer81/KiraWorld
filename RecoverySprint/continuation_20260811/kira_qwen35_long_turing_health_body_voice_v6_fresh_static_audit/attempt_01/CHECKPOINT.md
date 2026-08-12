# Kira Qwen 3.5 Long Turing / Health / Body / Voice V6 Fresh Static Audit

Recorded date: `2026-08-11`

Decision: `REJECT`

Live authority: `NONE`

`ACCEPT_EXACTLY_ONE_OWNER_AUTHORIZED_UNATTENDED_ATTEMPT_01` is **not issued**.

## Basis

The sealed V6 closure and every exact V5 subject/audit it binds match their
declared byte lengths and SHA-256 digests before and after testing. The V6
author suite passed 45/45 and the combined V5/V6 suites passed 88/88 with
bytecode and pytest cache output disabled.

The independent hostile suite nevertheless produced 15 failures and 24 passes.
The sealed validator accepted four prohibited meaning-equivalent continuity,
private-memory, stale-media, and unsupported-lived-past claims. It also accepts
a terminal receipt with the two required aggregate cleanup fields omitted,
accepts non-finite status and cleanup numbers, permits JSON non-standard numeric
constants, and treats read-only mapping proxies as exact terminal objects.
These are deterministic fail-open correctness defects. Passing authored tests
and matching sealed hashes are insufficient to authorize a live attempt.

## Retained-boundary checks

Static inspection and positive controls confirmed the exact `qwen3.5:9b`
digest, 35 measured turns plus one invitation with cap 36, absence of a Llama
route, Blackwell-v2 CUDA-only policy, no CPU/generic/SAPI fallback, WAV,
synchronous playback and cleanup gates, and truthful absence of current live
authority. Both intended V6 output roots were absent before and after review.
No controller or production path was executed.

## Safety record

This audit used only local file reads, hashing, parsing, compilation/static
imports, and ordinary unit tests. It did not run a model, voice, audio, GPU,
device, person, body, media, Blender, controller, or production command. It did
not create V6 live evidence or generated-audio roots and did not modify any
sealed V6 or bound V5 byte.

## Evidence

- `HASH_VERIFICATION.md`
- `TEST_RESULTS.md`
- `REVIEW_RESULT.json`
- `INDEPENDENT_AUDIT.tsv`
- `INDEPENDENT_AUDIT.sha256`
- `test_v6_independent_hostile_static.py`

Any successor requires a new append-only preparation package and a new
different fresh exact-byte hostile static audit. This rejection never enables
live use.
