# Kira text/voice fast-end static repair — attempt 01

Date: 2026-08-11

Status: `STATIC_REPAIR_VERIFIED_NO_LIVE_UI_RUN`

## Owner-observed problem

Robert reported that the Kira text/voice session was difficult to end and that he ultimately closed the text/voice window.  The prior read-only session audit independently showed that `Close Safely` later completed and released the voice worker, but the interaction still felt unresponsive.

## Bounded repair

- The primary control is now labelled `End conversation now` for bounded text/voice sessions and retains the existing pointer-up primary path plus click fallback.
- The button changes to `Ending conversation...` while the request is in flight.
- Text/voice launchers have no world or active body.  Their end/close path therefore skips the irrelevant avatar-snapshot wait and proceeds directly to the existing deactivate or safe-close API.
- Embodied/world sessions retain the avatar snapshot gate.  The skip is narrowly guarded by `state.text_voice_mode` and `state.active_has_body`; body and wardrobe persistence behavior was not removed.
- Existing duplicate-deactivation protection remains in place.

## Exact subjects

| Path | Bytes | SHA-256 |
|---|---:|---|
| `tools/kira_world_shell_server.py` | 606696 | `72e4fc403e00a2c4e7ac84e7a87a3c925fc9ce475a8afc90e17ac9e0b6b19fb4` |
| `Testing/test_kira_text_voice_fast_end_static.py` | 1108 | `b74e2dd3144f825095fbe71570afca7a7e6e2872062cbf70c7e0d456a50797c9` |

## Verification

Command:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
py -m py_compile tools\kira_world_shell_server.py Testing\test_kira_text_voice_fast_end_static.py
py -m pytest -q -p no:cacheprovider Testing\test_kira_text_voice_fast_end_static.py Testing\test_elsa_kathryn_bounded_text_grounding.py
```

Result: `19 passed, 12 subtests passed in 1.33s`.

`git diff --check` for the two bounded subjects passed.

A broader historical avatar-resume/wardrobe source-string suite was also sampled during diagnosis and retained two unrelated stale expectations in the separate Home World source.  They were not caused by this text/voice repair, and no unrelated Home World file or historical test was changed to conceal them.

## Runtime truth

No browser, model, voice, audio, body, media, Blender, or person-state runtime was invoked for this repair.  This is a static UI/source repair pending the owner's next ordinary use; it does not claim an owner-observed usability acceptance yet.
