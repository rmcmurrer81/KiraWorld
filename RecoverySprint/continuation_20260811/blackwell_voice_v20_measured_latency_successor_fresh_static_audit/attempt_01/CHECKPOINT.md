# Blackwell Voice V20 different fresh static audit checkpoint

Date: 2026-08-12 UTC

Verdict: `REJECT_V20_STATIC_CONTROL_PACKAGE_NO_PROMOTION_NO_RUN`

The installed 12-file package was kept read-only. All 12 files had identical
bytes before and after review, all nine sealed subjects matched the author seal,
and all 41 lineage inputs remained unique and exact. The installed cache-free
suite passed 42/42. Three Python sources compiled in memory. Fresh MSVC x64
`/W4 /WX` compilation and `/analyze /W4 /WX` passed without diagnostics; only
unlinked object scratch was created under Documents/Codex. V20 copies V19's
five accepted-static arrays exactly at 4 conditions, 51 timestamps, 42 metadata
fields, 30 durations, and 15 ordering rules. The package truthfully makes no
latency-improvement claim, and its public live factory/native `wmain` remain
default-off.

Those positives do not overcome five reproducible blockers:

1. The mutable `backend_bound_objects` map is the call target, but graph
   verification never verifies that map. A substituted resource callable ran
   twice and `load_once` still succeeded.
2. The authority dict remains mutable after validation. Maximum turns widened
   from one to four and expiry/owner values changed without graph rejection.
3. A self-hashed Qwen receipt with timestamps 1..7 was accepted after a window
   granted at monotonic 1,010,000,000 ns. It has neither external authentication
   nor causal time binding, so it cannot prove unload/no-overlap.
4. The experiment schema lists device first sample but defines no duration that
   uses it and no controlling success metric or closed measurement-method
   evidence. It cannot decide true device-onset latency.
5. Native ledger creation uses a string path rather than the bound parent handle
   and does not rebind the new ledger's identity/security. Final-path prefix
   comparison does not close parent rename/replacement/reparse races.

The exact hostile outputs are in `HOSTILE_PROBE_RESULT.json`; the full decision
and repairs are in `AUDIT_DECISION.json`. The new historical/expert voice rule
arrived after the seal and was not used to reject V20. It is preserved in
`FUTURE_V21_VOICE_INPUT.md` as mandatory input to the repaired successor: use
an evidence-based, explicitly uncertain reconstruction when no recording
exists; use H. H. Holmes as the regression case; and generate distinct expert
voices from the same sealed body/person-spec digest.

No candidate, production route, model, GPU, audio, playback, camera,
microphone, network, person, body, or Sarah operation ran. V20 must not be
copied, promoted, integrated, or run. The current persistent-v2 production
route remains unchanged, and latency remains failed pending a repaired static
successor and later separately authorized matched measurement.
