# Root multilane continuation checkpoint - attempt 76

Date: 2026-08-12

## Long Evaluation V15 different-audit result

The exact seven-file V15 rejection bundle is installed append-only at:

`RecoverySprint/continuation_20260811/kira_qwen35_long_turing_health_body_voice_v15_fresh_static_audit/attempt_01/`

Exact installed identities:

- `AUDIT_ARTIFACT_MANIFEST.tsv`: 569 bytes, SHA-256 `2199e999fb8d5efa616adbf4ce0d2b79cfeb46850aacdfe5c9b49eb253c578a7`
- `AUDIT_DECISION.json`: 3,584 bytes, SHA-256 `9d224218f7dfafa280cbce62680b17fb0b3dfc29a9a7869af25a16d3601311ff`
- `AUTHOR_SUITE_RESULT.txt`: 595 bytes, SHA-256 `2c99ce6ecb1aba96252fad4123f26b2c03e9a4a02f9a44b3e3fb963c13fc5ab1`
- `CHECKPOINT.md`: 4,133 bytes, SHA-256 `fea1f02735e68c14ac0a4d0683f1aa10b45bf842fc4bf9e35bb36d6d1384282e`
- `HOSTILE_PROBE_RESULT.json`: 6,607 bytes, SHA-256 `9fa603430578f759c816d4379e1ff7ecc3602c45fd7d20ff6e8555ca2d713ceb`
- `INDEPENDENT_HOSTILE_PROBES.py`: 22,527 bytes, SHA-256 `026faae96f49c164927ed34d279b76085ae177fa9c4b6f22a06c12b6e7ab490d`
- `REVIEW_PROBES.md`: 7,083 bytes, SHA-256 `5b0a542123e21e40472f9280ea62feff11dea5335934c07795708a7aaa2b36f1`

Verdict: `REJECT_V15_STATIC_SCHEMA_CONTROL_PACKAGE_NO_PROMOTION_NO_RUN`.

The installed author package and its 72-test cache-free suite remain exact,
but the different review reproduced four blocking defects:

1. a Kira output event can be relabeled `PERSON_MESSAGE` and escape generation accounting;
2. truth/private-belief rows are not linked to exact public trace events/messages;
3. an identical belief/public digest can pass a deliberate-lie row because material conflict is caller-asserted; and
4. strict JSON containing an escaped lone surrogate can crash canonicalization instead of refusing safely.

V15 grants no entry, model, camera, voice, private-state, or one-hour run
authority. Preserve it as rejected evidence. Append-only V16 repair is active
in Documents/Codex scratch and must receive a different audit before any
successor boundary can advance.

No live route ran while installing this evidence.
