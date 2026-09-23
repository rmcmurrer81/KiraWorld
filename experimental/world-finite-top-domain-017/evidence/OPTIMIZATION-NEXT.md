# Proposed bounded profiling; no optimization implemented

The12-frame pilot measured2.58186s candidate stepping versus0.64187s baseline,
about4.02x. The1110-frame candidate made1,469,820,737 vertex observations and
468,866,463 domain queries: about1.324million observations and422,402 queries per
frame. It suppressed156,081,866 queries, about33.3%. These are actual counters;
they do not identify which functions consumed CPU time.

Source inspection suggests allocation and repeated book-keeping as the first
profiling targets. mask builds a three-element array and calls every for every
observation. observeVertex invokes reduce with a closure for every incident
primitive; clear allocates/sorts an ID key and bindings constructs a seven-value
array on every query. The40 constraint iterations and4 substeps legitimately
produce many calls. Counts alone do not justify removing observations.

After the active Studio run ends, propose one exact12+12 pilot under Node's CPU
sampling profiler, with original017 source unchanged, one process,384MiB heap,
512MiB RSS and a30-second hard ceiling. Retain the per-frame p/prev/v comparisons
and domain counts. This tests profiler neutrality and gives actual self/total
time before choosing an optimization. No baseline trajectory or broad suite
rerun is needed. Treat the profile's source paths as local-only until redacted
for backup. No profile has been launched.

If the profile confirms these hotspots, first consider allocation-free scalar
finiteness/binding checks and short explicit loops for the existing1/2/3-vertex
mask intersections. Keep finiteXYZ rejection, EPS, call order, permanent holds,
all observation boundaries, counters and primitive separation rules identical.
A successor must preserve017 and compare complete certificate outcomes/counters
plus p/prev/v on the focused cases and bounded pilot before wider evaluation.

Do not reduce iterations/substeps, remove checks based only on the current pose,
drop history after a failed certificate, reattach running history, change contact
response/damping or skip queries because adjacent vertices look exterior. A
no-op-observation fast path would need a separate proof covering signed zero,
NaN, other vertices' changes and unobserved aliases; it is not the first change.
