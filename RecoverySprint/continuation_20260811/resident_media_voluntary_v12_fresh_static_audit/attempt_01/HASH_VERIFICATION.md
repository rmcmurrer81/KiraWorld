# Resident Media V12 different fresh exact-byte verification

Recorded UTC: `2026-08-11T07:38:16.3160182Z`

Result: `PASS`

The V12 author package was treated as read-only. Every sealed subject and the
seal-bound V11 rejection checkpoint matched its recorded byte count and
SHA-256.

| Subject | Bytes | SHA-256 | Result |
|---|---:|---|---|
| `Core/resident_media_voluntary_gate_v12.py` | 50,849 | `2cc9e588affde3c0dd1e127baef31fd2183cc2d188d61afdf2899df06bd6bf5c` | PASS |
| `Testing/test_resident_media_voluntary_gate_v12.py` | 32,717 | `9e9441564eaf6415b19c100b678430f425b0b29003a003b2954af093693291b8` | PASS |
| `RecoverySprint/continuation_20260811/resident_media_voluntary_v12/attempt_01/STATIC_TEST_RESULTS.md` | 2,127 | `e3d87c7e09384582145d69d955f3b9f5c525264b02344aca22b02fb4bfec5542` | PASS |
| `RecoverySprint/continuation_20260811/resident_media_voluntary_v12/attempt_01/VOLUNTARY_MEDIA_CONTRACT_V12.json` | 3,600 | `362a9a833d324ab53b8eebf90cc4a05308fde2ff3e70fbd989c6ec8ad14f81f8` | PASS |
| V11 fresh rejection `CHECKPOINT.md` | 3,165 | `bfe12c090c45e09b83fed2ad51f1258c1da882f2941f910e0d3f8033b26a0e1e` | PASS |

Seal manifest:

- path: `RecoverySprint/continuation_20260811/resident_media_voluntary_v12/attempt_01/SEALED_MANIFEST.json`
- bytes: 1,411
- SHA-256: `7c6d2da7319e163dc0e2a1be0be1af06bbbfe89173f5a8b5f21e93e2a94e2a66`
- result: PASS

The unsealed author checkpoint was also preserved as observed:

- bytes: 6,026
- SHA-256: `4c61fced59fa3131bf12c6f4d9daaaadcff6db3200fd2ba70a7388ed47cc34db`

The independent probe also rehashed the exact V10 core/test/fresh-audit
checkpoint and the V11 core/test/contract/checkpoint/review result. All nine
matched the identities hard-bound by the sealed V12 test.
