# Root multilane continuation checkpoint — current Qwen latency-route regression test

Date: 2026-08-11
Status: `QWEN35_CURRENT_ROUTE_DETERMINISTIC_TIMING_TEST_PASS_NO_LIVE_SPEEDUP_CLAIM`

## Append-only test

New file:

`Testing/test_kira_qwen35_latency_current_route_v1.py`

- bytes: 3,852;
- SHA-256:
  `efac83385e2fc24219fc4f437825b7ea54108c11e46fd95d8781a68360d868bd`.

## Results

- New Qwen-only focused test: 1/1 passed.
- Current deterministic latency set with the obsolete Llama buffered-stream
  case deselected: 8/8 passed; one stale case deselected.
- The test proves one exact Qwen 3.5 9B generation request, buffered streamed
  fragments withheld until completion, first-content timing recorded, and
  `keep_alive=0` retained for Qwen release before voice.

## Boundary

No production code or live route changed. No model, GPU, synthesis, audio,
playback, camera, person, body, Blender, or Sarah path ran. This does not prove
lower text latency, lower audio onset, or a camera improvement. It replaces an
obsolete Llama-specific deterministic predicate with current Qwen-only test
coverage; measured improvement still requires a separately authorized run.
