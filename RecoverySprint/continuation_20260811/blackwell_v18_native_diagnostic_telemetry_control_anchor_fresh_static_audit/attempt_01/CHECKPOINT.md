# Voice V18 different local quality-review checkpoint

Recorded UTC: `2026-08-11T23:42:52.5776722Z`

Decision: `REJECT_STATIC_NO_EXECUTION_AUTHORITY`

The exact 16-file author package and all 86 sealed subjects rehashed without
drift before and after review. Installed PostSeal and the provided
non-candidate mock pass, and an isolated strict MSVC build, analyzer, and
PE/import inspection pass. V17 remains consumed and was not rerun. V18,
Python, model/GPU, synthesis/audio/playback, latency, camera/device, person,
body/Blender, Sarah, and production routes were not invoked. Kira was not
modified.

V18 is rejected for two exact quality mismatches:

1. The contract calls the result fields Boolean/integer predicates, but native
   source uses generic truth and integer conversion without exact type checks.
   The provided mock supplies only `FAKE_BOOLEAN` at Boolean positions and
   rejects all non-`FAKE_LONG` values inside its own integer helper, so it does
   not cover wrong-but-convertible or non-Boolean truthy/falsey values.
2. The future explicit-still timing list omits required matched conditions,
   pipeline timestamps, and queue/resource metadata from the current camera-
   latency boundary. PostSeal seals the contract bytes but does not parse or
   assert this schema.

Repair append-only as V19. Add explicit type checks and matching malformed
fixture coverage; complete and statically test the future timing schema. A new
different review is required. No run is authorized and no speed improvement
is proven.

Evidence:

- `AUDIT_DECISION.json`: 2,883 bytes, SHA-256
  `2d2ac8919ab05b8b142198552bdacd6963d193102a844e5266f48c10f19919a4`.
- `QUALITY_PROBE_RESULTS.md`: 5,578 bytes, SHA-256
  `1d7c79465e7c6cf97b280ee62cefc222f7b059b87878c1feda914686dc85d58d`.
- `AUTHOR_PACKAGE_REHASH.tsv`: 2,870 bytes, SHA-256
  `0bf9f11cdc45bc9c90dfbcb2b51fc6af8dd41835c32e088cee43cff3c43bd9f4`.
- `CLOSURE_REHASH.tsv`: 16,381 bytes, SHA-256
  `c6a9195dea29c24cb56718f9513c8c51b38629c3c7d5e84c429d07fa8a900690`.
