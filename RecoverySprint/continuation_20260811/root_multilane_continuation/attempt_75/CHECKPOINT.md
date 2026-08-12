# Root multilane continuation checkpoint — exact seven-reply offline voice replay

Recorded UTC: `2026-08-12T01:38:49.962Z`

The persistent-v2 first-waveform refinement was replayed offline against the
exact latest seven public `voice_output` events. No model, GPU, synthesis,
playback, camera, microphone, or person route ran.

Result: `3/7` formerly single-waveform replies change, from first-waveform
sizes `123`, `166`, and `132` characters to `65`, `71`, and `67` characters.
The other `4/7` replies were already naturally split and remain unchanged.
All seven preserve the exact public spoken-word sequence.

This supports the engineering expectation that those three first waveforms
can finish earlier. It is not a measured timing or quality result; no seconds
are inferred. The per-turn model reload remains the dominant fixed delay and
requires a separately audited resource-residency successor.

Machine-readable evidence: `OFFLINE_REPLAY.json`. Status remains
`LATENCY_FAIL_PENDING_MATCHED_MEASUREMENT`.
