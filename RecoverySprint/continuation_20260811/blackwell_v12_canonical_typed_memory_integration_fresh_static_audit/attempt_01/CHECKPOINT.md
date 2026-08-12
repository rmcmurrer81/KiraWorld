# Blackwell V12 canonical typed-memory integration — different fresh static audit

Date: `2026-08-11`

Decision: `REJECT`

`ACCEPT_STATIC_ONLY` is **not issued**.

Live authority: `false`

Promotion authority: `false`

Future-harness-authoring authority: `false`

Playback authority: `false`

The candidate-required `AUDIT_AUTHORIZATION.json` was not created.

## Outcome

V12 is rejected without live execution or candidate edits. Its seal manifest,
author checkpoint, seven sealed subjects, author result, and all 28 preserved
V8/V9/V10/V11/routing/audit boundaries remain exact before and after testing.
The production route remains SHA-256
`a343572b25937926ea0181274976b53f57ca219ce1e4d3e1780343994aea7b81`.

The authored V12/V11/V10 cache-free suites passed 56/56. Independent hostile
testing ran 15 tests: 12 passed and 3 failed. The failures reproduce one new
blocking trust-root defect:

`BLOCK_V12_CANONICAL_CONTROL_MODULE_NOT_BOUND`

V12 creates strongly sealed private V8 and V10 module objects, but the V12
canonical control module that creates, installs, and revalidates those objects
is imported through normal mutable package and `sys.modules` state. Its own
module object and validator globals are not included in the binding.

Three independent static reproductions were unexpectedly accepted:

1. After a genuine installed binding was created, replacing the V12 canonical
   module object in both `sys.modules` and its package attribute did not make
   `binding.revalidate()` fail.
2. Before integrated preparation, a forged V12 canonical module supplied
   replacement create/install/revalidate functions. It returned an arbitrary
   object and internally consistent affirmative evidence through every final
   preparation check.
3. Replacing the canonical module global `_ensure_import_slots_clean` with a
   no-op let a forged V8 `sys.modules` entry survive binding revalidation.

This means the V11 forged-adapter defect is repaired at the private V8/V10
layer, but the authority-conferring V12 control plane remains substitutable.
Exact source bytes on disk and internally consistent dictionaries do not bind
the Python module object and helper functions actually used by preparation.

## Positive findings that do not cure rejection

Independent controls confirmed rejection of forged adapter `__file__` and
callable names, exact-module subclasses, callable proxies, V8/V10 package and
`sys.modules` poisoning, altered private code/defaults/referenced globals and
closure contents, fake typed binding objects, and TOCTOU before and after
installation and after integrated preparation. Default-off parent and worker
live paths refuse, the exact typed-memory probe is installed only into the
private V8 object, and no candidate live/generated output root exists.

## Evidence

| File | Bytes | SHA-256 |
|---|---:|---|
| `INDEPENDENT_HOSTILE_PROBES.py` | 14,453 | `6a831f0695d9d6a911db379b07be0494ebc8e526892caba007678b3fcbd72627` |
| `HOSTILE_PROBE_RESULT.json` | 2,979 | `6c0c2fb02b1a0345aea208f41b598bf5c892831ca2df45b31795fccee8684833` |
| `AUDIT_DECISION.json` | 1,484 | `751939cf93fedfc323ecd7c32ee38c0606bf08f8fcc5ada6d8775b1eee58d41c` |
| `STATIC_AUDIT_RESULT.json` | 1,923 | `bc199169ca6b362788fd252a78df334db6e26e3662172b82a64f1ff80b9ef2a6` |
| `HASH_VERIFICATION.md` | 1,681 | `5b20b8a65d7e37dd8e5257875a44518fb5505d5682d3af6c97f3dc0f0a06b614` |
| `TEST_RESULTS.md` | 1,399 | `5e85ae2bb5c4409fb06edc012af3db28147a58f33f17cfe2bbef02e1f94bae43` |

## Scope truth

No V12/V11/V10 candidate, predecessor, earlier audit, production route, or main
documentation byte was edited. No Ollama or Qwen request, Torch or CUDA use,
Chatterbox load, synthesis, audio, playback, person, body, media, or Blender
operation occurred. No live harness ran and no promotion or authorization was
issued.

## Required next step

Preserve V12 and this rejection. Any repair must be an append-only successor
that binds the V12-equivalent control module object, its exact helper function
objects/code/globals, and the package/`sys.modules` identity before and after
creation, installation, revalidation, telemetry, and integrated preparation.
It then requires another different fresh exact-byte hostile static audit. This
rejection never enables live use or production promotion.
