# Blackwell persistent voice candidate v5

This is an append-only, inactive, static-only repair candidate. It does not
replace v2, rejected v3, or rejected v4, and it is not connected to production.

V5 adds an immutable internal policy, a mandatory killable-child boundary for
every potentially blocking adapter call, exclusive-lease-bound Qwen residency
evidence, pre/post CUDA-transition absence gates, fail-closed policy-drift
cleanup, closed real-stream validation, independent WAV verification, and
generation-bound CUDA evidence.

`PLAYBACK_IMPLEMENTED` remains false. Passing the local fake/static tests does
not authorize CUDA/model/audio execution, playback, owner hearing, production
routing, or promotion. A fresh independent exact-byte hostile audit is the next
gate.
