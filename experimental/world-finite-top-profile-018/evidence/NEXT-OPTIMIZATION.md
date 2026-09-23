# Proposed isolated019: equivalent primitive keys

Profile018 sampled the unchanged017 candidate and baseline for12 frames each.
All physical observations and certificate counters exactly match the earlier
unprofiled pilot. The helper accounts for49.28% of sampled self time across the
whole mixed run: observeVertex22.82%, clear12.85% and key12.83%. Sampling/inlining
limits mean this does not separately prove allocation cost. No optimization or
speedup has been implemented or demonstrated.

The safest first candidate is a helper-only fast path for key construction.
Today every clear call builds ids.slice().sort(...).join(','). There were about
4.99million queries in the12-frame pilot and468.87million in the1110-frame run.
All owned solver primitives contain one, two or three integer vertex IDs.

Proposed behavior: handle those lengths with scalar comparisons and exact string
assembly, preserving numeric order, duplicate IDs, negative zero formatting and
the length prefix. Keep the existing expression as the fallback for other
lengths or noninteger values. No certificate, mask, history, observation,
geometry, hold, solver order or finiteXYZ validation changes are needed.

Prepare019 separately and preserve017/018. Required checks are equivalence across
permutations, repeated/boundary/invalid IDs and fallback inputs; the20 focused
domain groups and33 tiny frames; and a bounded paired12-frame017/019 comparison
of every p/prev/v value and certificate counter, not only final contact metrics.
Measure a small fixed-order then reversed-order pair if the single run suggests
a benefit, so process warm-up/order is not mistaken for speedup. No broad1110
replay or installation follows automatically. Profile the larger observeVertex
work only after this isolated change is assessed.

Do not eliminate observation calls, cache moving masks, reduce iterations,
change EPS or permit running-history resets. Source inspection alone cannot
prove a performance improvement; the first implementation may fail to improve
runtime and must retain that outcome honestly.
