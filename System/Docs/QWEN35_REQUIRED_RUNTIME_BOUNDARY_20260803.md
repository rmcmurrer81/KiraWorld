# Qwen 3.5 required runtime boundary — 2026-08-03

Status: **OWNER-CONTROLLING MODEL ROUTING DECISION**

## Required model

The required Kira Text + Voice model is the exact installed candidate:

- model: `qwen3.5:9b`;
- digest: `6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`;
- quantization: `Q4_K_M`;
- normal request mode: top-level `think: false`.

All new diagnosis, repair, integration, latency, launcher, and owner-acceptance
work must use this exact Qwen model. A harness, launcher, environment, or test
that pins or can silently select `llama3.1:8b` must not be executed as part of
the current work.

## Llama 3.1 boundary

`llama3.1:8b` remains installed only as a dormant rollback asset while Qwen
3.5 is being repaired and stabilized. Preserve its historical evidence, but
do not invoke it, test it, route a person to it, use it as an automatic
fallback, or use a Llama result to claim current acceptance.

Llama may be reconsidered only if bounded, evidence-preserving Qwen diagnosis
shows that the exact Qwen candidate is completely unusable. The existing
evidence does not show that: exact Qwen installation, non-thinking requests,
screening, and prior text/voice engineering acceptance have succeeded. The
owner-facing failure combined launcher evaluation mode, duplicate repair
calls, canned postprocessing, cold model lifecycle, and the old stateless
voice path; it was not proof that Qwen itself was unusable.

After Qwen passes the normal launcher, natural two-turn text behavior, exact
model/digest, approved GPU voice routing, cleanup, latency measurement, and a
stable owner-use period, remove Llama 3.1 from the computer. Removal is a
later destructive transition: first preserve the exact installed-model
identity, rollback record, and all historical evidence, then obtain a fresh
post-removal Qwen smoke result. Do not remove it early and do not allow its
mere installation to make it selectable during Qwen acceptance.

## Next bounded acceptance

Create a separate append-only Qwen-only acceptance path. It must:

1. reject any selected model or returned digest other than the exact Qwen
   identity above;
2. run with ordinary evaluation mode and `think: false`;
3. make one model generation per ordinary turn, with every permitted cleanup
   transformation recorded and no canned/static replacement;
4. explicitly unload Qwen and prove its absence before each approved
   Chatterbox GPU synthesis;
5. use one retained persistent-v2 Chatterbox worker and one continuous WAV per
   reply, with complete route, timing, coverage, playback, cleanup, RAM, and
   VRAM evidence;
6. forbid Llama, SAPI, generic voice, emergency/static text, and unproved
   fallback routes;
7. keep configuration promotion append-only and reversible until the run
   passes.

The historical Llama two-turn run remains evidence about the persistent voice
component only. It is not current text-model acceptance and must not be rerun.

## 2026-08-04 Attempt 01 diagnosis

The first exact-Qwen plus persistent-Blackwell-v2 no-playback attempt is
preserved as a failure. Its process ownership and cleanup gates worked, but it
prewarmed the GPU voice model before the first Qwen request. GPU use rose from
`1374 MiB` to `4989 MiB`, and the exact Qwen `/api/chat` call returned HTTP
`500` after `9.762975 s`. Voice was correctly not attempted, both model paths
were cleaned up, Ollama returned to empty residency, and normal person state
was unchanged.

A bounded Qwen-only isolation request after cleanup returned HTTP `200` with
exact content `OK` in `3.815 s`, then unloaded cleanly. This proves the exact
installed Qwen model is usable and means the Llama reconsideration boundary
has not been reached. It does not pass the complete Kira prompt or voice route.

Before Attempt 02, exact Qwen text and the persistent Blackwell voice model
must be serialized on the shared GPU: no Qwen-route activation prewarm, only
the owned voice model may be suspended before Qwen, one Qwen generation with
`keep_alive:0`, proved Qwen absence, then lazy approved GPU-voice load and
synthesis. A retained worker is permitted only when its owner, unload, race,
and cleanup boundaries are proved. Local HTTP failures must preserve bounded
status/body evidence without speaking diagnostic text.

Full evidence:

`RecoverySprint/continuation_20260803/qwen35_persistent_v2_two_turn_acceptance/no_playback/attempt_01/DIAGNOSIS_20260804.md`

## 2026-08-04 static shared-GPU serialization repair

The narrow Attempt 01 repair is now implemented and independently approved at
the static/mocks-only boundary. Exact Qwen text generation, direct or lazy
persistent-v2 voice prewarm, and persistent-v2 synthesis share one bounded
resource mutex. The host must suspend the exact owner-generation voice model
before Qwen, issue one `think:false`/`keep_alive:0` generation, strictly prove
Qwen absent from a schema-valid `/api/ps` response, and only then permit the
approved GPU voice path. Malformed residency records, a changed owner or
generation, lock timeout, HTTP failure, or absence-proof failure all block
speech and every CPU, generic, SAPI, and one-shot fallback.

Static verification passes 17/17 focused and 139/139 combined tests. No model,
voice worker, CUDA workload, audio device, Blender process, camera,
microphone, or Llama request was invoked. Independent review initially found
and then approved repairs for strict raw-residency parsing, owner-generation
ABA protection, and direct-prewarm mutex coverage.

Checkpoint:

`RecoverySprint/continuation_20260803/qwen35_persistent_v2_two_turn_acceptance/PREFLIGHT/RESOURCE_SERIALIZATION_REPAIR_STATIC_CHECKPOINT.md`

Checkpoint SHA-256:
`a53db66d47c92b9634dc799c56164af283c4ad8e821ad5fc4b902bd812188246`.

A fresh append-only no-playback live acceptance remains pending. Normal
launcher/default promotion remains forbidden until that acceptance passes;
the existing Llama-pinned launchers must not be run during the current Qwen
boundary.
