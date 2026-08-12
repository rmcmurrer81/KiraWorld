# Qwen 3.5 owner-route request-policy test-debt closure

Date: 2026-08-09

Status: `STATIC_MOCK_PASS_NO_LIVE_ACCEPTANCE`

This append-only addendum follows
`QWEN35_OWNER_RUNNABLE_ROUTE_RECONCILIATION_STATIC_CHECKPOINT_20260809.md`.
It closes the one stale test expectation that checkpoint reported; it does not
change the production request policy or claim a live model, voice, camera,
microphone, browser, server, or owner-hearing acceptance.

## Correction

`Testing/test_model_request_policy.py` no longer expects the normal
owner-runnable exact-Qwen route to retry a failed `/api/chat` request through
`/api/generate`. The test now activates the Text + Voice route boundary and
proves that a `404` fails closed after one Qwen request, preserving
`think: false` and `keep_alive: 0` without a compatibility generation retry.

This is a test-truth repair only. No Llama model was loaded, selected, called,
or tested.

## Verification

Focused static/mock reconciliation, including the repaired assertion:

```text
61 passed, 66 subtests passed in 3.18s
```

Changed file:

| Project-relative path | Bytes | SHA-256 |
|---|---:|---|
| `Testing/test_model_request_policy.py` | 6,916 | `590988ed9f944f52539b8357971059ffa7814a84d1d9609b1ceee1b914fb7282` |

## Rollback

Reverse only the renamed Qwen owner-route test, its `TEXT_VOICE_CHAT_ACTIVE`
patch, its request-mock keyword acceptance, and its one-request fail-closed
assertions. Do not overwrite the whole test file and do not restore the stale
two-endpoint expectation on a current owner route.
