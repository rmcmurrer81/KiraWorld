# Focused Test Results

Run on 2026-07-22 without starting services or activating Kira.

## Runtime syntax and module tests

Command:

```text
node --check <preview>/src/main.js
node --check <preview>/src/existing_mouth_lipsync.js
node --test Testing/test_existing_mouth_lipsync.mjs Testing/test_ambient_micro_movements.mjs
```

Result:

```text
JavaScript syntax checks: PASS
Tests: 9
Passed: 9
Failed: 0
```

## Movement verifier

Command:

```text
node tools/verify_kira_movement_realism_r5.mjs
python -m unittest Testing.test_kira_movement_realism_r5
```

Result:

```text
Verifier: PASS
Evidence kind: deterministic_math_and_static_runtime_source_no_services_no_activation
Visually reviewed: false
Python tests: 9
Passed: 9
Failed: 0
```

The verifier reports zero sampled wall crossings for the centered doorway route, no ordinary runtime spawn-copy teleport, joint-limited relaxed arm samples, and no live doctor-harness mapping. These are deterministic/static assertions, not a live navigation observation.

## Dialogue, body-intent, audio, and playback tests

Command:

```text
python -m unittest \
  Testing.test_kira_world_dialogue_audio_continuity \
  Testing.test_kira_unified_body_intent \
  Testing.test_kira_world_shell_lipsync_playback \
  Testing.test_kira_world_latest_session_repairs \
  Testing.test_kira_chat_body_intent_bridge
```

Result:

```text
Tests: 85
Passed: 85
Failed: 0
```

## Aggregate focused result

```text
Python: 94/94 passed
JavaScript module tests: 9/9 passed
Syntax checks: passed
Kira activations: 0
Live audible claims: 0
Live visual claims: 0
```

