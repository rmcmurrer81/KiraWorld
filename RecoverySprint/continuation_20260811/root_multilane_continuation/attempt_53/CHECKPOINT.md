# Root multilane continuation checkpoint — Qwen buffered-stream read optimization

Date: 2026-08-11
Status: `PASS_CODE_AND_MOCK_REGRESSION_LIVE_LATENCY_UNMEASURED`

## Change

The current exact Qwen 3.5 9B buffered stream no longer requests one transport
byte per Python iteration. `Core/conversation_loop.py` now uses the explicit
bounded constant `QWEN_BUFFERED_STREAM_READ_CHUNK_BYTES = 32`.

This keeps the early complete NDJSON event observable, preserves full-response
buffering and validation before any public display, and reduces Python read
iterations by up to 32 times for the same response byte volume compared with
the prior one-byte loop. It does not change `keep_alive=0`, exact model/digest
selection, one-generation semantics, protected truth rules, or voice routing.

## Exact identities

- `Core/conversation_loop.py`: 355,602 bytes, SHA-256
  `b460e2c99f48135812e506363938c68e15fb51325d89e60373ef9fb9079a681c`.
- `Testing/test_kira_qwen35_latency_current_route_v1.py`: 4,197 bytes,
  SHA-256
  `5d5880130dfe68b14ae1cc90db52fbc94ea121f71c928d9899a5664c558d49dd`.

## Verification

- current Qwen route, single-generation, and Blackwell resource-serialization
  suites: 26 tests plus 4 subtests PASS;
- current latency set with the obsolete Llama buffered fixture deselected:
  8/8 PASS, one intentionally deselected;
- the current-route fixture proves the response reader received chunk size 32,
  both content records were preserved, the final text remained exact, no
  partial response was displayed, and `keep_alive=0` remained exact.

No Qwen/model, GPU, voice synthesis, playback, camera, person, body/Blender,
Sarah, or production operation ran. Fewer read iterations are a code-level
improvement; wall-clock text latency and audible onset remain unmeasured and no
speedup percentage is claimed.
