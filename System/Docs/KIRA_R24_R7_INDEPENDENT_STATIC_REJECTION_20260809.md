# Kira R24 R7 independent static rejection — 2026-08-09

Status: **R7 STATIC TESTS PASS; INDEPENDENT AUDIT REJECTS EXECUTION.**

R7 was internally sealed, reported `PRE_AUDIT_EXACT`, and passed `37/37`
focused static tests. It also retained false execution authority and did not
launch Blender or create a candidate. A separate read-only audit nevertheless
found integrity gaps that prevent using it as an artifact-acceptance gate.

R7 hashes:

| Artifact | SHA-256 |
|---|---|
| worker | `391eac6d01782f75524546600067e441809b706dfd5d9bc8ddfad5c7513bc5e6` |
| extractor | `df25d4aaabcee0da0333633b2498402433a468c816aef77861850565f3a99b87` |
| semantic helper | `e50052017866fcca945ae141ac4227e33a3164de8356ae29e5a5a9e41b1b623f` |
| inert author | `6f99e5667ebe97cc23c1fe556a602d0fba63d667c56bc9915c67718b3e2aa8e0` |
| fresh evaluator | `abd171a1eb73089c7906a213db28c6da5dcb2a847f1ff62ee23535607c8fdc74` |
| focused test | `ab81ad4326f9307f5ff3e4a43118a30acdbc9e237b857a563fb97b35a7fed164` |
| contract | `c228fc29b3f2028734a47dd74bdc074216d04b62dd10cf8f3399c419343e9992` |
| checkpoint | `66cd145a39bba136bac53669aa2b0bccd876601fa12fdd1640f4b5b551afcceb` |
| proposal | `015571fb70b805dd5a20c2797de6a5b6b56a1f13ba9c6e98f1a84e4d17660cbd` |
| package manifest | `78194b2f42dfd6d3bc96bc771ef389ac40bb9b600c82895362825970b22337a9` |
| static results | `066fea226a76c669fb4371d8077b416b3463bec1babd0c184e09768f189e94dd` |

Independent blockers:

1. After the fresh evaluator exits, the parent validates the previously
   reported candidate digest and current size but does not re-hash the named
   candidate or retain an immutable lease through the final eligibility
   decision. The accepted report can therefore cease to identify the bytes at
   the path.
2. The fresh evaluator output is an ordinary closed temporary file. Its exact
   identity is not held immutably from child completion through parent read and
   final decision.
3. R7 claims complete R6 preservation but does not bind the current R6
   `PACKAGE_MANIFEST.json` or `STATIC_TEST_RESULTS.json` as parents.
4. Candidate/runtime-prefix and temporary-snapshot path components do not all
   carry the same raw reparse-component rejection and locked-directory identity
   proof as the sealed artifact paths.
5. The evaluator envelope's artifact body is primarily schema-checked; final
   eligibility relies too heavily on child-authored/echoed fields rather than
   parent-recomputed evidence.

The audit re-ran the focused suite (`37/37` pass) and confirmed no Blender
process. Passing fixtures do not cure these gaps. Preserve R7 unchanged and do
not run it. The same cross-phase identity class has now survived multiple
bounded evaluator successors, so do not start a minor R8 automatically. A
genuinely different immutable artifact/receipt mechanism or Robert's review of
a narrower accepted threat boundary is required.
