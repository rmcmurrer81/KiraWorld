# Root multilane continuation checkpoint — stale Llama latency-test contradiction

Date: 2026-08-11
Status: `CURRENT_LATENCY_TEST_7_OF_8_ONE_STALE_LLAMA_FIXTURE_REFUSED_BY_QWEN_ONLY_POLICY`

## Focused command

`python -B -m pytest -q Testing/test_kira_latency_integration_candidate.py`

Result: 7 passed, 1 failed.

## Exact failure classification

The failing test is
`test_buffered_stream_records_first_content_without_exposing_partial_text`.
It patches the current route to `MODEL_NAME='llama3.1:8b'`. The exact current
model-selection policy rejects that call before transport with:

`current person routes require exact qwen3.5:9b; alternate-model selection is disabled`

This is a stale Llama fixture/harness contradiction, not proof that the current
Qwen route failed and not a measured voice-latency regression. The other seven
deterministic candidate tests passed.

## Boundary

- Do not weaken the exact Qwen 3.5 9B selection rule to make the old Llama
  fixture pass.
- Do not rewrite a sealed historical test in place.
- A current append-only Qwen-only timing successor must replace or supersede
  the obsolete Llama predicate under its own review.
- No model, GPU, synthesis, audio, camera, person, body, Blender, or Sarah route
  ran in this test.
