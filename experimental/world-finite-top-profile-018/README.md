# World018 CPU profile addon — isolated and uninstalled

This is a measurement of the unchanged World017 source. One12+12-frame mixed
candidate/baseline profile preserved all prior per-frame observations exactly.
The helper accounts for49.28% of whole-run sampled self time; no optimization or
speedup was implemented. See evidence/PROFILE-ANALYSIS.json and
evidence/NEXT-OPTIMIZATION.md. World015 remains installed.

Exact source modules and fixture are copied for provenance. Recorded receipts
and the CPU profile are under evidence with local identity paths redacted.
Their embedded hashes describe the original local files; BACKUP-MANIFEST.json
records original and packaged hashes. The profile addon does not modify017's
published portable003 package.

To reproduce in a fresh package, install Node.js on PATH and Python with psutil,
then run `python run_profile.py`. The portable runner retains384MiB heap,
512MiB RSS and30s limits. Existing output/profile files should be preserved.
The portable replay was not executed during packaging; paths, hashes and syntax
were checked statically. Results do not establish finished physics or visual
acceptance, and they do not authorize installation.
