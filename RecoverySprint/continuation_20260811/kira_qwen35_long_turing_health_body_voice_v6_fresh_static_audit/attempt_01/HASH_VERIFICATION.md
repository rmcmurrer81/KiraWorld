# Exact-byte closure verification

All hashes below were computed locally with SHA-256. The sealed candidate and
every bound V5 subject/audit were read only. The comparison was repeated after
the static test runs; every listed item remained byte-exact.

| Subject | Bytes | Expected and observed SHA-256 | Result |
|---|---:|---|---|
| V6 `EXECUTION_PLAN_V6.json` | 4443 | `fdc68423b05c562819846b53a94b867463c5a5376ef1752cdd7cc9ad22047a88` | MATCH |
| V6 controller | 44879 | `95ab9175ae6683803292af1478c82a6d7d3f28148e6a7b69855ff53a16d8e6f3` | MATCH |
| V6 author test | 22046 | `050f165cd6ea33fb77968a9105b0263385fbd102ac98d552d19bb138250a0174` | MATCH |
| V6 `AUTHOR_STATIC_TEST_RESULT.json` | 1149 | `702f3e3d1040f1908ae48136392e8e1fc9e881bd6bf756dca73a089d0d2d1d07` | MATCH |
| V6 `STATIC_SEAL_MANIFEST.json` | 1070 | `df2c712895529b4696492cc91c0569a1ea5b0a88227f7277c2b2a896a9d7c316` | MATCH |
| V6 `CHECKPOINT.md` | 4426 | `22bed8a96cd519d38aa6fbe47cad61c14e3bfca1f2469d7387a32158d1b2f3d1` | MATCH |
| Bound V5 plan | 8102 | `18f8015122ecdef85b5a2b2c68e440418b3b66a9d19c49807fa8300261fe6e5c` | MATCH |
| Bound V5 controller | 59358 | `319af9b9def7bcd6dd091494d315c54afe7aac20703b200ffdbfbaa4c99e56d2` | MATCH |
| Bound V5 author test | 22762 | `354359cdb6bbad6ca61ed3e0be262dc0a36ff717e1e5c0b3370c3ad44fdd35f4` | MATCH |
| Bound V5 checkpoint | 8510 | `22e93c92c645dc82d2354a0c9b20ec850f995828a81253bfba887f2530b0d855` | MATCH |
| Bound V5 fresh-audit checkpoint | 10855 | `b10508e7c22a1e5e9efc2be262c0c66c6dd3f374dcfc29988a19170007a8783a` | MATCH |
| Bound V5 hostile probes | 10772 | `2ebfa387a96f9e15e35e809d26ddcf3d8d4b5c5b4229ca08cd8579bf4c0a9439` | MATCH |

The V6 evidence root and V6 generated-audio root were absent before testing and
remained absent afterward. Integrity verification does not establish semantic
or schema correctness.
