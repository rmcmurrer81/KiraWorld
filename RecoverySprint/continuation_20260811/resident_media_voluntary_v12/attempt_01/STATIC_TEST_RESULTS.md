# Resident Media Voluntary Gate V12 - Static Test Results

Date: 2026-08-11

Live execution: `NONE`

## Strict compile

Command:

`$env:PYTHONDONTWRITEBYTECODE='1'; py -m py_compile Core\resident_media_voluntary_gate_v12.py Testing\test_resident_media_voluntary_gate_v12.py`

Result: `PASS`

## Focused V12 static/hostile suite

Command:

`$env:PYTHONDONTWRITEBYTECODE='1'; py -m unittest Testing.test_resident_media_voluntary_gate_v12 -q`

Result: `PASS - 14 tests`

The focused suite covers the unconditional disconnected production opener;
absence of a V12 module issuer secret, issuer factory, or trusted owner-catalog
global; same-process invented token/global rebinding; refusal of caller catalog
input; exact externally returned catalog/selection/source-time/derivative
snapshot binding; page/video/audio/caption per-role completeness; incomplete
role refusal; authority receipt replay within and across adapters; global
output/decoder receipt replay across sessions and reopen; stale concurrent
CAS, rollback, exact-readback TOCTOU, zero sentinels, bool/integer confusion,
unknown fields, and exact V10/V11/rejection-evidence preservation.

## Preserved V3-V12 static regression suite

Command:

`$env:PYTHONDONTWRITEBYTECODE='1'; py -m unittest Testing.test_resident_media_voluntary_gate_v3 Testing.test_resident_media_voluntary_gate_v4 Testing.test_resident_media_voluntary_gate_v5 Testing.test_resident_media_voluntary_gate_v6 Testing.test_resident_media_voluntary_gate_v7 Testing.test_resident_media_voluntary_gate_v8 Testing.test_resident_media_voluntary_gate_v9 Testing.test_resident_media_voluntary_gate_v10 Testing.test_resident_media_voluntary_gate_v11 Testing.test_resident_media_voluntary_gate_v12 -q`

Result: `PASS - 176 tests`

## Static execution scan

The V12 core contains no subprocess, media decoder/renderer, camera,
microphone, network, model, GPU, audio playback, body, or Blender execution
path. The sole occurrence of `Blender` is in the module truth-boundary
documentation.

No media was opened, decoded, rendered, played, or claimed as experienced.
No production pointer or route was changed.
