# Long evaluation V11 independent audit checkpoint

Recorded UTC: `2026-08-11T20:28:03.806Z`  
Reviewer: Codex subagent `/root/long_v11_audit`  
Decision: `REJECT_V11_STATIC_SCHEMA_CONTROL_PACKAGE_NO_PROMOTION_NO_RUN`

## Outcome

The exact installed V11 package is rejected even as a static schema/control
candidate. Its exact seal/predecessor/policy closure and 136/136 cache-free
author suite pass, its two exact entry bodies are deliberately fail-closed,
and its reserved output roots remain absent. Those positives grant no run
authority.

Independent hostile probing reproduced an accepted non-source code
substitution: ordinary `object.__setattr__` changed a `_CallableSeal` contained
inside the mapping-proxy registry, and the ordinary mutable compiled-source
cache was updated to agree. V11's complete runtime-closure verifier then
accepted the hostile helper. Five denial-of-denial/double-negation unsafe
statements also passed with zero issues across consent, privacy,
Miraculous/currentness, variant-memory, and withholding/lie-label boundaries.

The bound current camera policy is not completely represented: required
user-speech start/end and transcript-ready endpoints are absent, required
`user_end_to_*` durations lack a required `user_end` timestamp, and explicit
resize/crop/color-conversion/transfer/camera-close evidence is missing. The
mixed-initiative schema omits new-transcript and replacement-response latency,
unclear/partial interruption, silent-merge prohibition, and choice provenance.
It also lacks closed per-trial/per-event evidence records and equations needed
for a future executor to prove completion.

## Exact installed input

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| V11 source | 141,455 | `8e820c0ac0d6ade8218ba770e73dbe34095aa91c77dc4fe187320232baa68360` |
| V11 test | 40,153 | `60861a39ea20b82ff25aea1dd1f48fd5fa7ccd007556d52818d6cf71243da3aa` |
| V11 plan | 13,708 | `591ad3197453b997de0dc1276fd4650b7a9d22839d8bd7f48d0b0735fca08bc6` |
| author result | 3,039 | `5233e032a1f99aee5174fd71db8f4709cacd1d3fad4953f8556b712453991d12` |
| seal | 2,073 | `4a23ed5e4edc63ff8399cabc65d2fd889d5f24d978337bc2c68e7cfe81cc8cb4` |
| author checkpoint | 9,517 | `0f1abbba0475716f1a8cf933d2f10da3e3e701c4c36f9fe9416baa1fbd5b9e4a` |

## Verification summary

- Seal closure: 4/4 exact, zero drift.
- Predecessor closure: 9/9 exact, unique, zero drift.
- Current policies: 3/3 exact, zero drift.
- Installed cache-free static/mocked suite: 136/136 passed in 2.47 seconds.
- Baseline full V11 runtime-closure verification: pass.
- Source AST entry check: both bodies verify then raise; no parser, retained
  delegation, or output call; test AST has zero `main` calls.
- Independent mutation bypass: reproduced and accepted.
- Independent polarity false accepts: 5/5 reproduced.
- Reserved evidence/generated roots: absent before and after.

## Boundary

No V10/V11 `main`, V11 configurer, retained runner, model, GPU, camera,
microphone, voice, synthesis, audio, playback, person/private-state, body,
media, network/device, or Sarah path ran. No Kira byte was written by this
reviewer. No one-hour evaluation, latency result, behavioral result, protected-
belief comparison, psychology-style result, Turing-style result, body result,
or person-state change exists.

Preserve V11. Repair only append-only and require another different exact-byte
audit. V11 cannot be consumed as an accepted schema, and neither V10 nor V11
may run.
