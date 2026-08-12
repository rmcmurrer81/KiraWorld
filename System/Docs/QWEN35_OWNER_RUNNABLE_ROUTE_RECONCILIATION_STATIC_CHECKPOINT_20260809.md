# Qwen 3.5 Owner-Runnable Route Reconciliation — Static Checkpoint

Date: 2026-08-09

Status: `STATIC_MOCK_PASS_NO_LIVE_ACCEPTANCE`

This append-only checkpoint records a bounded, static-only reconciliation of the current owner-runnable Kira entry points. It does not claim a live model, GPU, voice, camera, microphone, playback, browser, or owner-hearing acceptance.

## Controlling model identity

- Model: `qwen3.5:9b`
- Exact digest: `6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`
- Ordinary request policy: `think: false`
- Llama 3.1 is not selected or tested by the owner-runnable routes covered here.
- The Qwen buffered-stream timing candidate remains explicitly selected on the covered launcher routes.

## Scope changed

Owner-facing launchers:

- `Start_Kira_World_Shell.bat`
- `Start_Kira_Chat_Control_Center.bat`
- `Start_Kira_Voice_Chat.bat`

Owner-facing tools:

- `tools/kira_chat_control_center.py`
- `tools/gpu_readiness_check.py`

Static/mock tests reconciled or added:

- `Testing/test_current_authority_reconciliation.py`
- `Testing/test_kira_launcher_probe_isolation.py`
- `Testing/test_kira_world_shell_fresh_process_integration.py`
- `Testing/test_qwen_webcam_microphone_live_acceptance.py`
- `Testing/test_qwen35_owner_runnable_routes_static.py` (new)
- `Testing/test_kira_world_latest_session_repairs.py` (one approved stale launcher assertion)

The canonical `Start_Kira_Text_Voice_Chat.bat` was already governed by the current Qwen 3.5 production boundary and was enumerated by the new static route test; it did not require a source edit in this checkpoint.

## Implementation result

- Covered launchers now select the exact Qwen model and digest and disable both Llama candidate flags.
- Route activity flags now distinguish the World Shell route from Text + Voice routes.
- The Chat Control Center defaults to exact Qwen rather than Llama.
- GPU readiness now rejects non-Qwen model requests before any network operation.
- GPU readiness verifies the exact installed Ollama tag and digest before allowing a live probe.
- Its bounded probe path now uses local `/api/chat` request policy fields, including `think: false` and `keep_alive: 0`, rather than invoking `ollama run`.
- The new static test enumerates the current owner-runnable entry points and explicitly excludes archival, backup, RecoverySprint, school, and life-loop launch paths from current-route authority.
- The historical Qwen webcam/microphone harness remains preserved and unexecuted; its stale Llama assertions are classified as legacy/inert rather than current authority.

## Deliberately excluded

- No model was loaded, generated from, unloaded, downloaded, removed, or altered.
- No Ollama, GPU, voice, Chatterbox, camera, microphone, playback, browser, server, or owner conversation was started.
- No fresh-process integration test was run because it would start real local processes and violate this static-only boundary.
- No archival or protected evidence was rewritten.
- No school/life-loop launcher was promoted into the owner-runnable route list.
- No latency acceptance status was changed. The latest exact Qwen + Blackwell Attempt 04 measurements remain engineering evidence pending owner-hearing acceptance.

## Verification

Focused static/mock command:

```text
py -B -m pytest -q -p no:cacheprovider \
  Testing/test_qwen35_owner_runnable_routes_static.py \
  Testing/test_current_authority_reconciliation.py \
  Testing/test_kira_launcher_probe_isolation.py \
  Testing/test_qwen_webcam_microphone_live_acceptance.py \
  Testing/test_qwen35_production_singleton_launcher.py \
  Testing/test_kira_text_voice_device_capture.py \
  Testing/test_kira_world_latest_session_repairs.py::VoiceQueueAndLatencyPolicyTests::test_launcher_prewarms_and_uses_smaller_natural_chunks
```

Result: `60 passed, 66 subtests passed in 3.15s`.

An additional broad static/mock check produced `21 passed, 1 failed, 6 subtests passed`. The one non-gating failure is an existing expectation in `Testing/test_model_request_policy.py::ModelRequestPolicyTests::test_kira_chat_and_generate_fallback_apply_qwen_policy`: it expects a second `/api/generate` fallback after a 404, while the current exact-Qwen single-generation policy returns empty. Neither the production request policy nor that out-of-scope test was changed here. This is preserved as unresolved test debt, not hidden as a pass.

`Testing/test_kira_world_shell_fresh_process_integration.py` was statically reconciled but intentionally not executed.

## Post-change SHA-256 manifest

| Project-relative path | Bytes | SHA-256 |
|---|---:|---|
| `Start_Kira_World_Shell.bat` | 4304 | `3db4d0029a8f33758d19df0e29897f0577177850ab56fc850d9806d4ab77c21f` |
| `Start_Kira_Chat_Control_Center.bat` | 600 | `081cb40e82095fc1f9c1e582973d8aa83715a4b4672f240f686c45e23754f2b0` |
| `Start_Kira_Voice_Chat.bat` | 783 | `9a52177a455ca5d939e3db6dc5be233f13c3aed0b4c9949cfef7a85b8bd412f2` |
| `tools/kira_chat_control_center.py` | 65307 | `9459b0bcdc7a4903dd5b75a1a14fbb6fce2adf064f2c36fd073bc8fa4a97f127` |
| `tools/gpu_readiness_check.py` | 14882 | `dc2ad23a5c2175068bccb2a57399fa4c77bde2bca6fb07b87cdc70808453876f` |
| `Testing/test_current_authority_reconciliation.py` | 6635 | `0e8a42c3528a52182eb54c4300e77974ea408ed8d035d73bee8694fb345ab228` |
| `Testing/test_kira_launcher_probe_isolation.py` | 12948 | `5cc444a3e4463532d07bb1425e3c79bde3e3007a61898772ecb728821290ae79` |
| `Testing/test_kira_world_shell_fresh_process_integration.py` | 15092 | `ef355474462af19d5b5eb8249b4622abb7bf96f9830d9a52e152fe71723d096b` |
| `Testing/test_qwen_webcam_microphone_live_acceptance.py` | 12332 | `31ce56e7eca7130fe445206b54acde31b93811a52879312d3ea06614c7335628` |
| `Testing/test_qwen35_owner_runnable_routes_static.py` | 5660 | `d9ed3573912048520c0d3cec3fcef2a8996d3abcdcf1140f568046f6aa9e4b4e` |
| `Testing/test_kira_world_latest_session_repairs.py` | 30782 | `cd69b3104dfd108dd569e1aedec5918925a358246e4e08e383901702cc3a7b52` |

## Rollback boundary

Rollback must be hunk-level and must preserve later local work. Do not blindly overwrite whole files.

1. Preserve this checkpoint and the new static test as append-only evidence; if superseded, label them superseded rather than deleting them.
2. Reverse only the Qwen model/digest, timing-candidate, route-activity, readiness tag-verification, and `/api/chat` probe hunks recorded by this atomic change.
3. Reverse only the matching stale test expectations; do not replace entire test files.
4. A preserved comparison source for the five production files exists under `RecoverySprint/checkpoints/continuation/QWEN_TEXT_VOICE_PROMOTION_VALIDATED_20260801_034251_671/payload/`. It predates some later work and therefore must be used only to inspect affected hunks, never as a blind whole-file restore.
5. Restoring Llama selection would contradict the current owner decision. Treat that as an emergency code rollback only, requiring a new explicit authority decision before execution.
6. After any rollback, rerun the focused static/mock command above before attempting a live owner route.

No automatic deletion, process termination, cache cleanup, security weakening, or model mutation is part of this checkpoint.
