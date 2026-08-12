# Blackwell voice V15 consumed-failure checkpoint

Date: 2026-08-11

Status: `CONSUMED_FAILED_PRE_OUTPUT_DO_NOT_RERUN_V15_V16_REQUIRED`

V15 passed its different fresh static review, but the one authorized
no-argument disconnected static-control invocation returned exit code `4`.
Neither fixed evidence/output file was created. The one-shot authority is
consumed and V15 must not be invoked again.

Read-only source/manifest diagnosis proves the exact pre-output defect: all 21
sealed subject rows use compact JSON tokens such as `"path":"..."`, while the
native verifier requires whitespace-sensitive strings such as
`"path": "..."`. The two sentinel row paths also have spaced count 0 and
compact count 1. `seal_contract_exact` therefore fails in native stage 10,
before output reservation and before private Python loading.

Exact diagnosis artifact:

- `STATIC_FAILURE_DIAGNOSIS.md` - 4,001 bytes - SHA-256
  `2ec653382ba9d915cac53e525419829ac53e314782a91d7de77cdf7e8ab1275f`.

Preserve the valid V15 static-review conclusion separately: V15 closes the
four V14 control-plane defects, but its bounded check did not complete and no
voice, synthesis, playback, audio, or latency result exists.

Continue append-only as V16 with structural/canonical, duplicate-rejecting
manifest validation and hostile compact/pretty/duplicate/scalar-alias tests.
V16 must be resealed and receive a different fresh review before any bounded
invocation. No V15 rerun is authorized.

No model, GPU, Torch, CUDA, Chatterbox, synthesis, audio, playback, latency,
person-state, network/device, body/Blender, or Sarah operation occurred.
