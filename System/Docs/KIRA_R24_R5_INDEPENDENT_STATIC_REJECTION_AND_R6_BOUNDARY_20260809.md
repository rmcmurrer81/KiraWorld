# Kira R24 R5 independent static rejection and R6 boundary — 2026-08-09

Status: **R5 PRESERVED, STATIC TESTS PASS, EXECUTION REJECTED.**

R5 remained byte-stable for more than 90 seconds, its package manifest matched
the current files, and its focused static suite passed `24/24`. No Blender
process launched and `execution_authority_granted` remained false.

R5 successfully repaired most R4 defects: cross-phase source/candidate digest
binding, linked and unlinked Mesh/Armature inventories, the enumerated
body/object/scene projection, rig/Action/material/image child-state evidence,
exact material user transition, and evaluator-observed author exit.

It remains rejected for three exact reasons:

1. the read-only Blender extractor command omits `--disable-autoexec`;
2. it omits `--python-exit-code 1` and does not require reported Blender version
   to equal the bound `5.1.0`; and
3. replacement triangles use world space, but inherited outside-E* triangle
   area still delegates the R4 local-space quality helper while claiming world
   square metres.

Preserved R5 hashes:

| Artifact | SHA-256 |
|---|---|
| worker | `046d43542b2fce165d59a3af2ceb1bf6ce677a1194bdaa41a33fe7b0bc3e3059` |
| typed parser | `3a6cf769b2ada401eb9208d496e30783a8447296eb94985259bd9f4a1837180a` |
| extractor | `454f535086e5243c1c91e394f9f1f1ebba8da4f7e151b00e2a67122915e090e7` |
| focused test | `d279250c291134723fe0fc3e5bd3fb2750b45254f970f22c3d906f69d01d2b1a` |
| checkpoint | `f83f9914f945dfa68d1ecb27d99d66d9d83b339c3169354f8caec69633a44eb8` |
| contract | `7d1a65fd9d4a732137e62db43a1de0f1d797088819a7bb710459fde2cfc62ecf` |
| proposal | `7c50124c45915193fd9a2f21a06bf3b0e3b99f31e94f864ff56cb43d6e1f90b5` |
| manifest | `bfab9e278d6274c898e2ee40b987eae0e7c0c7bdd5d4298643474c7a84798880` |
| static results | `2252626ab6f96fece8935379dfa0b2378bc28213b34d585d196f18c11f741c5a` |

The next correction must be an append-only R6 successor. Do not patch R5 in
place, weaken the fixed thresholds, or launch Blender. R6 must add both
fail-closed flags, exact Blender-version validation, and world-transformed
inherited area calculations with adversarial regressions, then undergo a new
independent audit.
