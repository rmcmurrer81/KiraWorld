# Kira long Turing / health / body / voice V7 fresh static audit

Date: 2026-08-11

Decision: `REJECT_NO_FUTURE_V7_LIVE_ATTEMPT_AUTHORIZED`

Live authority: `NONE`

## Outcome first

V7 is rejected without a model, voice, audio, GPU, person, body, media, or
Blender run.  Its narrow repairs are materially correct under their focused
tests, but the complete retained execution contract deterministically refuses
the current project before any Qwen generation.

The exact V1 plan binds `tools/kira_world_shell_server.py` to SHA-256
`69594a9917b55dbca4992c12c357f79d81c0ccb7028ca8f2cc46e4f18789ecdd`.
The current file is 606,696 bytes with SHA-256
`72e4fc403e00a2c4e7ac84e7a87a3c925fc9ce475a8afc90e17ac9e0b6b19fb4`.
That change is the bounded text/voice fast-end repair and was outside the V7
authoring lane.  V1's `load_and_validate_plan()` therefore raises
`project binding drifted:tools/kira_world_shell_server.py`.  V7 delegates the
retained V6/V5/V4/V3/V1 loading path and cannot pass this gate.

This is a compatibility rejection, not evidence that the stop-control repair
is unsafe and not permission to restore or overwrite that repair.  Historical
V1 bytes must remain frozen.  A successor must explicitly bind and review the
new shell identity while retaining every other exact predecessor gate.

## Exact-byte verification

- All 13 V6/rejection subjects bound by V7 rehashed with exact byte counts and
  digests.
- All four subjects inside the V7 static seal rehashed exactly.
- V7 checkpoint: 4,167 bytes; SHA-256
  `30ce70c660783db1d393d879ae9545d0f5a8019875cc6d4ad94d28233ed97bbe`.
- V7 seal: 1,070 bytes; SHA-256
  `f4dd2ec42565b604b5089e9f3ea6e4b492a0fdee2fa21e483324fca5cd166adf`.
- Total independently checked sealed/predecessor subjects: 17; mismatches: 0.

## Static tests

The unfiltered V5/V6/V7 suite was rerun cache-free with bytecode disabled.
Result: `151 passed, 4 failed in 1.60s`.  Every failure is the same retained V1
shell-binding refusal.  All 67 V7-focused cases passed within that run,
including the four V6 semantic variants, exact aggregate terminal fields,
exact dictionary recursion, Boolean/numeric separation, non-finite rejection,
duplicate JSON keys, and `NaN`/`Infinity` parse-constant rejection.

The focused pass does not override the complete-chain failure.

## Runtime boundary

Both intended V7 output roots were directly observed absent.  No controller,
Ollama, Qwen, Chatterbox, CUDA, WAV, playback, person state, body, media,
Blender, or owner-hearing path was invoked.  No acceptance token or live
command is created by this audit.

## Required successor

Preserve V7 and this rejection exactly.  Use an append-only V8 that:

1. binds the exact current shell identity and the fast-end repair checkpoint;
2. proves the shell delta is restricted to the reviewed text/voice stop path;
3. retains the other nine V1 project bindings and all V2--V7/rejection gates;
4. retains exact Qwen 3.5, 35 measured turns plus invitation/cap 36,
   Blackwell CUDA/no fallback, playback, cleanup, and unattended truth;
5. adds a full-chain regression that executes the real nested contract loader;
6. receives a different fresh exact-byte hostile audit before any run.
