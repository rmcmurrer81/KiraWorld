# Blackwell voice V19 exact-type and camera-schema author checkpoint

Recorded UTC: `2026-08-12T00:06:41.7330550Z`

Status: `AUTHOR_SEALED_STATIC_ONLY_PENDING_DIFFERENT_FRESH_AUDIT`

Execution authority: `NONE`

## Exact repair

V17 remains `CONSUMED_FAILURE_DO_NOT_RERUN`. V18 remains rejected and
uninvoked; its exact rejection decision is
`2d2ac8919ab05b8b142198552bdacd6963d193102a844e5266f48c10f19919a4`.

V19 replaces permissive truth/conversion checks with exact built-in type gates.
It requires an exact tuple of ten, exact Unicode schema, exact Boolean types
and singleton identities, and exact integers before signed-64-bit conversion,
range/error checking, and value checking. Codes 10 through 34 distinguish all
25 failures. Wrong-but-convertible types cannot reach conversion.

The retained validator remains 21,931 bytes,
`2bf232b07b0b7b93de8776f5210bd2d89068ad76cb4ee46555b861ad2818d16a`;
module `_kira_blackwell_v15_private_native_validator`; callable
`validate_static_control_graph_v15`; result schema
`kira.blackwell.v15.native_validator_result.v1`.

## Complete non-executable timing schema

The contract statically binds four matched conditions, 51 monotonic
timestamps, 42 metadata fields, 30 durations, and 15 ordering requirements.
The explicit-one-still condition covers local permission/open/capture/draw/
JPEG/handoff; vision lock/load/infer/unload; chat queue/text load/first token/
display; voice queue/load/first sample/audio-ready/playback; and camera close.
It binds prompt/state/history/limits/order, exact Qwen identity/digest,
residency, queue depth, GPU/VRAM/CPU samples, in-flight work, and cue/frame
handling. It records no live values and authorizes no later run.

## Exact closure and static evidence

The canonical 110-row seal is 23,616 bytes,
`1247fce7561f9d47ab0f013b6b98ef0a12ff33eb627bd874c28caa9c94d66713`.
It binds the V19 source/header/executable/config/contract/readme, the complete
86-row V18 seal closure, ten remaining V18 author artifacts, six V18 rejection
review artifacts, and root attempts 44 and 51.

- Compiled hostile mock: `100/100`, with all 25 stages/codes exact; candidate
  entrypoint unreachable and Python not invoked.
- Source mutation gate: `18/18` exact-type/schema removals refused.
- PreSeal and PostSeal actual-layout suites: pass.
- Strict x64 `/W4 /WX /O2 /MT /guard:cf /std:c17`: pass, zero diagnostics.
- Candidate and hostile `/analyze /W4 /WX`: pass, zero unsuppressed diagnostics.
- PE: x64 PE32+, high-entropy VA, ASLR, NX, CFG/CF instrumentation and FID
  table; imports exactly `bcrypt.dll` and `KERNEL32.dll`.

Core identities:

- source: 106,649 bytes,
  `f0e06bc9242f3585d79788e666c6481c6055b7a974d683c430377940201c1104`;
- identity header: 13,662 bytes,
  `6f5a8e10bc4b0c51f9c6458934faf06f34d50a51a515c91877abbfaa0682f903`;
- object: 181,247 bytes,
  `8092f0be64f6aaefce6365aabb83f3be9fb4987885bd98911ab4c82205418c48`;
- executable: 177,152 bytes,
  `b6b7d2c6ee838ec8cb168f9c93301f9f0f1f0861a1d2d145a7ffc021c2243f19`;
- hostile source: 13,912 bytes,
  `ce209890eff3c647797a1061806d14d9bbc1504962c0f303df53b8083edc3ed2`;
- hostile executable: 188,416 bytes,
  `9f39efc2d156fc61fc0f778199edb72a9868d420faee4dc7e9facdf1fc8711ee`.

## Boundary and next step

V17, V18, V19, Python, model, GPU, synthesis, audio, playback, latency,
camera/device, network, person state, body, Blender, Sarah, and production
routes were not invoked. This proves no voice or latency improvement.

Root may transplant the exact 16 author artifacts into previously absent V19
paths, rehash them, run only the non-candidate PostSeal static suite, and obtain
a different fresh static review. Author sealing grants no run.
