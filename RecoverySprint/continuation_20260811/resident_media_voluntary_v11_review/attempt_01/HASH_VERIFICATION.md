# Resident Media V11 fresh review hash verification

Date: 2026-08-11

All V11 subjects listed by the sealed author checkpoint matched before testing
and again after testing. The predecessor V10 fresh rejection checkpoint also
matched the hash embedded in the V11 contract and V11 authored tests.

| Project-relative path | Bytes | SHA-256 | Result |
|---|---:|---|---|
| `Core/resident_media_voluntary_gate_v11.py` | 48475 | `64e5edf62fce5002434a0af6165c1e58ab6d407a414d3750cd9cf66835fe1671` | MATCH |
| `Testing/test_resident_media_voluntary_gate_v11.py` | 20165 | `4e60c575021a7b0f9ce7dcff6e7a9a5ef20b757f0959f032131ae9e5276e859b` | MATCH |
| `RecoverySprint/continuation_20260810/resident_media_voluntary_v11/attempt_01/VOLUNTARY_MEDIA_CONTRACT_V11.json` | 2577 | `5dc3c4f2a8044fa0e7cecf0c2588d018a0885dba046d517bea3ade90f33eda37` | MATCH |
| `RecoverySprint/continuation_20260810/resident_media_voluntary_v11/attempt_01/STATIC_TEST_RESULTS.md` | 1336 | `ba2e692a43ecd36e1facda2e12e1c2c9aa461c1f6bd3725785aa9aacf528300d` | MATCH |
| `RecoverySprint/continuation_20260810/resident_media_voluntary_v10_fresh_static_audit/attempt_01/CHECKPOINT.md` | 5749 | `456cab5b46e105708a9ddd69823f715c6c0bc5e243573ddb0822059e2a2e3a19` | MATCH |

Additional read-only context hashes:

| Project-relative path | Bytes | SHA-256 |
|---|---:|---|
| `RecoverySprint/continuation_20260810/resident_media_voluntary_v11/attempt_01/CHECKPOINT.md` | 6284 | `3bd339e6874b50ae61695d803fe99b137877dd33360a0286a8222c740c6fe016` |
| `RecoverySprint/continuation_20260811/resident_media_voluntary_v11_review/attempt_01/test_resident_media_voluntary_v11_review.py` | 17434 | `39ec49168be5f9475f607542de2ddb0333a516f8b2a687b15bc82f0625a54f56` |

No sealed package subject was edited by this review.
