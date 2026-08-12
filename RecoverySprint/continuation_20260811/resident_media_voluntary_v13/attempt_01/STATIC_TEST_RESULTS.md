# Resident Media Voluntary Gate V13 - Static Test Results

Date: 2026-08-11

Live execution: `NONE`

## Strict compile/read check

Command:

`$env:PYTHONDONTWRITEBYTECODE='1'; py -B -c "from pathlib import Path; files=['Core/resident_media_voluntary_gate_v13.py','Testing/test_resident_media_voluntary_gate_v13.py']; [compile(Path(f).read_bytes(),f,'exec') for f in files]; print('STRICT_COMPILE_PASS',len(files))"`

Result: `PASS - 2/2 exact source files`

## Focused V13 hostile/static suite

Command:

`$env:PYTHONDONTWRITEBYTECODE='1'; py -B -m unittest Testing.test_resident_media_voluntary_gate_v13 -v`

Result: `PASS - 15 tests in 0.118s`

The suite proves that complete page, video-frame, synchronized-audio, caption,
and audio-track controls still commit; missing caption coverage and a one-ms
audio gap fail before any external receipt/history/anchor state changes;
completion booleans and the exact authoritative role map must all be true;
and bool/integer/coerced identifiers are rejected across descriptor, snapshot,
nested catalog, receipt, verification, person, session, output, surface,
manifest, record, anchor, evidence, and segment locations.

SHA-256 probes reject non-string digests, uppercase-normalized aliases, a
64-digit JSON integer, and a numeric-only 64-character decoder-digest string.
Output/decoder receipt replay across sessions/reopen, stale anchors, snapshot
mutation, and the V12 external-authority/catalog/receipt boundaries remain
fail-closed.

## Preserved V3-V13 regression suite

Command:

`$env:PYTHONDONTWRITEBYTECODE='1'; py -B -m unittest Testing.test_resident_media_voluntary_gate_v3 Testing.test_resident_media_voluntary_gate_v4 Testing.test_resident_media_voluntary_gate_v5 Testing.test_resident_media_voluntary_gate_v6 Testing.test_resident_media_voluntary_gate_v7 Testing.test_resident_media_voluntary_gate_v8 Testing.test_resident_media_voluntary_gate_v9 Testing.test_resident_media_voluntary_gate_v10 Testing.test_resident_media_voluntary_gate_v11 Testing.test_resident_media_voluntary_gate_v12 Testing.test_resident_media_voluntary_gate_v13 -q`

Result: `PASS - 191 tests in 1.567s`

This preserved suite retains the accepted V7 choice-normalization core and the
catalog, consent, privacy, maturity/co-viewing, current choice, receipt,
external-authority, and fail-closed production regressions carried by V3-V12.
It does not promote or connect any predecessor.

## Static execution scan

The V13 core imports only standard-library data/locking helpers and the exact
preserved V4/V9/V12 static contracts. It contains no subprocess, network,
model, media decoder/renderer, camera, microphone, GPU, audio playback, body,
or Blender execution path.

No media was opened, decoded, rendered, played, or presented. No model or
device was called, no person/memory/preference state changed, and no claim of
seeing, hearing, attention, enjoyment, dislike, learning, or recall was made.
