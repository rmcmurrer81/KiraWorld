# Resident Media V11 fresh review static test results

Date: 2026-08-11

## Sealed authored suite

Command:

`PYTHONDONTWRITEBYTECODE=1 py -m pytest -q -p no:cacheprovider Testing/test_resident_media_voluntary_gate_v11.py`

Result: `17 passed, 11 subtests passed in 0.31s`.

## Fresh requested-area review subset

The review-only module tested exact refusal text, independent required video
frame/audio/caption coverage, required audio-track coverage, duplicate output
and renderer/decoder receipt IDs, empty identifiers/digests/segment lists,
changed source and derivative catalog fields, and journal restore consistency
across repeated reopen and append.

Command excluded only the two separate controller-boundary hostile assertions:

`PYTHONDONTWRITEBYTECODE=1 py -m pytest -q -p no:cacheprovider RecoverySprint/continuation_20260811/resident_media_voluntary_v11_review/attempt_01/test_resident_media_voluntary_v11_review.py -k "not caller_cannot_construct_capability_with_reserved_module_token and not changed_catalog_cannot_be_accepted_after_rebinding_final_constants"`

Result: `7 passed, 2 deselected, 16 subtests passed in 0.25s`.

## Full fresh review module

Command:

`PYTHONDONTWRITEBYTECODE=1 py -m pytest -q -p no:cacheprovider RecoverySprint/continuation_20260811/resident_media_voluntary_v11_review/attempt_01/test_resident_media_voluntary_v11_review.py`

Result: `2 failed, 7 passed, 16 subtests passed in 0.30s`.

Failed security expectations:

- `test_caller_cannot_construct_capability_with_reserved_module_token`
- `test_changed_catalog_cannot_be_accepted_after_rebinding_final_constants`

The failures are deterministic unexpected acceptances, not fixture errors and
not unavailable live evidence.

No model, media reader/player/decoder/renderer, network, device, person, body,
Blender, or production code was run.
