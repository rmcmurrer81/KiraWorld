# Root multilane continuation attempt 69

Date: 2026-08-11

## Scope

Read-only reconciliation of the most recent seven complete ordinary Kira voice
benchmark captures. No model, camera, microphone, synthesis, playback, person,
body, Blender, Sarah, network, or production action was invoked by this review.
No existing capture was edited.

## Exact finding

The captures prove a machine-side `first_playback_proxy` at the start of the
playback API call. They do **not** prove the true first audible sample at the
speaker or Robert's first-heard instant. Every reviewed completion explicitly
records:

- `first_audible_proxy_kind = playback_api_call_start_not_owner_observed_audible`
- `owner_true_first_audible_monotonic_ms = null`
- `owner_observation_required = true`

Therefore prior current-layer phrases that call the cold `23.460 s` and warm
`7.979-11.128 s` values "audible onset" are superseded. The supported label is
`displayed-text-to-first-playback-API-proxy`. The latency verdict remains
`LATENCY_FAIL`; this reconciliation is not a speed improvement.

## Exact seven-capture evidence

All seven used `blackwell_gpu_persistent_candidate_v2`, recorded actual GPU
execution, completed with generated and played status true, and had exact
expected-vs-synthesized and expected-vs-playback-proxy public-word sequences.

| request | bytes | SHA-256 | text processing ms | text to playback proxy ms | first chunk synthesis ms | worker reused |
|---|---:|---|---:|---:|---:|---|
| `27e1881a63334d52a3fcbcd693b554f1` | 14358 | `68682f622a3e3439fde745d7d7d49cd10d9183397980c80369a139bfcc08f887` | 14038.4779 | 23462.0885 | 23457.2011 | false |
| `3cf21a43ca4b4f48bdb578323b7f96a0` | 15058 | `df7dbac607a7f0f09e7e05927d6876b0e1ce27f5d57926ca35888cdc4a732a77` | 7806.9645 | 11130.6169 | 11125.2832 | true |
| `b6aceaab87114c4eaa5e0db50af3326b` | 14578 | `4b4f26de7d07a97ef75eacf31a9fe3dc2497199092316d82900593c62ee3dd35` | 7660.8336 | 10394.1164 | 10389.1945 | true |
| `1cf8659a036e4d52996d96335d5f6ed7` | 20340 | `6f223e7794d87ba4cecd8f325e607a116c1db6f7bd05bd59404f3442516c3886` | 7882.2572 | 8748.9197 | 8743.2861 | true |
| `c1c99416dd424b9b9bd585ef85348b20` | 25333 | `0fc7a6887d4b8d2aaf46523d6bfcb284b5c7c50b7e3abb1831bce248cbfac7b5` | 7938.4930 | 8503.0543 | 8496.4852 | true |
| `442b7f288fa64caa9cee7ccbec341f7f` | 31309 | `2acc7e0e5788c0aeda01c8b509d25ac6fac98e2c12278fcbd09aff8482054611` | 8252.7312 | 7981.1676 | 7975.5812 | true |
| `1c6dca2debe34bf0839ce8fd8349bdec` | 25922 | `1e723da12fbaf2e33d8c559f6cf1d129ac8fea1b1863664f4f88ccc2380e71d5` | 8059.6841 | 8771.6585 | 8766.0384 | true |

The source files are under
`Data/voice/realtime_audio_readiness/live_capture/voice_request_<request>.jsonl`.

## Boundaries

- Camera and camera-on contention are not measured by these seven captures.
- A future accepted matched test must distinguish browser camera/JPEG work,
  vision queue/load/inference/unload, text generation, synthesis, playback API
  start, true audio-device first sample, and optional owner-heard observation.
- The current text/voice guard changes are code/test evidence only until such a
  matched run is separately authorized and completed.
