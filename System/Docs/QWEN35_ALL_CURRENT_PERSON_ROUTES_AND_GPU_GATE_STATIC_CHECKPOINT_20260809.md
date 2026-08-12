# Qwen 3.5 all-current-person routes and GPU gate static checkpoint

Date: `2026-08-09`

Status: `STATIC_ONLY_PASS_NO_MODEL_OR_DEVICE_EXECUTION`

This append-only checkpoint records the small current-route correction made
after the owner direction that all active synthetic-person runtime routes use
the approved Qwen model. It is not a live Qwen, voice, camera, microphone,
GPU, browser, animation, body, or owner-hearing acceptance.

## Current runtime identity

- Model: `qwen3.5:9b`
- Digest: `6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`
- Ordinary Qwen request mode remains non-thinking with bounded release.
- The formerly selected Llama 3.1 installation is retained only in
  `config/model_runtime.json` as a dormant rollback inventory record. It is
  not selected by an active route, tested by the reconciled policy suite, or
  available as an automatic fallback.

## Corrected current routes

The runtime manifest now makes exact Qwen the desktop and GPU-bridge default.
The following current owner-clickable person routes now explicitly pin the
exact model and digest and turn both legacy Llama candidate flags off:

- Kira main control, Creative Writing, Enhancement Roadmap, Memory Lanes,
  Relaxed Conversation, and weekly-meeting launchers.
- Lisa chat and Lisa supervised life-test launchers.
- TemporaryAI text chat, GUI chat, life-loop, and control-center launchers.

The corresponding class/evaluation runner defaults were also changed from
Llama to Qwen: Enhancement Roadmap, Memory Lanes, Memory Lanes follow-up,
Relaxed Conversation, weekly meeting, and Kira Turing/psychology evaluation.

`Start_Kira_Text_Voice_Chat.bat` formerly set both persistent Blackwell v2
selection and `KIRA_DISABLE_BLACKWELL_GPU_VOICE=1`. The latter is now `0` so
the selected Blackwell GPU route is not self-disabled. Its SAPI setting stays
off and this checkpoint does not add any generic-voice route.

## Static verification

No Ollama request or process was started.

```text
py -m unittest Testing.test_qwen35_owner_runnable_routes_static \
  Testing.test_model_request_policy \
  Testing.test_qwen35_production_singleton_launcher \
  Testing.test_current_authority_reconciliation

28 tests passed
```

`py -m py_compile` also passed for all six corrected Kira runner modules.

Targeted current-source scans found zero Llama 3.1 selections in root active
batch routes and zero Llama 3.1 defaults in active Kira/TemporaryAI runner
modules. RecoverySprint, backups, historical data, frozen Video Studio, and
the dormant installed rollback record were intentionally not changed.

## Changed-file SHA-256 manifest

| Path | SHA-256 |
|---|---|
| `config/model_runtime.json` | `7db3aa2d7f7af16fc2e7d7be819593ade8d5b073e8df9d15fcdde9da664da111` |
| `Start_Kira_Text_Voice_Chat.bat` | `debd10a48ece40389a78db62b710508fed0fdeeb4e9d3c4b7ad00f8bb7ea2a1c` |
| `Start_Kira_Main_Control_Center.bat` | `fba587cb314398b98eaef4e5a4cc862b11e1ab5a6a12c2d59fa6ac3c5a8863d6` |
| `Start_Kira_Creative_Writing_Class.bat` | `3b3579a643d488ddb69aaa4a87a48600b8b91666117bb733ae749a14966b6f9b` |
| `Start_Kira_Enhancement_Roadmap_Class.bat` | `b7546b021e6e037bb3db6195c8deceaf8d1a8d5ce253809c027ee701364f261b` |
| `Start_Kira_Memory_Lanes_Class_Then_Direct_Chat.bat` | `fb9120a3f375da09e10c83ab5f4209b40836636f7a7069b0e55c0c15f22711c2` |
| `Start_Kira_Relaxed_Conversation_Class.bat` | `498c1e7fcd2ba7e74317304dd1a4c11a57ca7dc1d6416bd896bd7b795686bd3d` |
| `Start_Kira_Robert_Weekly_Meeting_Audio.bat` | `3ffac2e287ab455f0005878e8f06977c8e610a2f13fe8b1cb002e9a25874f5a8` |
| `Start_Lisa_Chat.bat` | `fd62dec6cb9994a1fbe5e5462a23de59a77ebdb01159a8196223c37992d58eff` |
| `Start_Lisa_Supervised_6hour_Life_Test.bat` | `f79e02ae4ffa4614399522aa3d3985d5e62a021e12d01ec3b64ec80c850d05c9` |
| `Start_TemporaryAI_Live_Chat.bat` | `c9f5dcf12cae83d68a00cce0dba909048bd7d82ec80cae5f275c66a8c4704989` |
| `Start_TemporaryAI_Live_Chat_GUI.bat` | `94fa91f1c9ae4bd88bb05249ee9fab90ff83357a2c657643c44de615196f58a5` |
| `Start_TemporaryAI_Life_Loop.bat` | `d17a1f7a2d7d2692812125b9a15533680bdd2544842ff56458d593f4f30219be` |
| `Start_TemporaryAI_Control_Center.bat` | `0708ebedb90ea226f5c3ab6f4b8e4a0b121a5ccae794e873a18977a82da985f1` |
| `tools/run_kira_enhancement_roadmap_class.py` | `2b0a8352513a6fed3ec55dbb4e3f86c8d8149705bf341a8478787a3746890063` |
| `tools/run_kira_memory_lanes_class.py` | `43fb1fe0fd159aca33b1d92f92242d706efdf5893186d68b44a6be7b3d77edab` |
| `tools/run_kira_codex_memory_lanes_followup.py` | `213a54df1e0557c35e6d597788eda7346b162b99a37c95e2a43cbfed1941cda5` |
| `tools/run_kira_relaxed_conversation_class.py` | `d121eb552951fdb74a7fae0ade3a8dc9f9d53e5514b52160d2698a18fb6098ce` |
| `tools/run_kira_robert_weekly_meeting_audio_20260715.py` | `d771c4e4faa566b1c9c3c7138c41be41a598df6db5daf6eb9e1cf20caa4c1521` |
| `tools/run_kira_turing_psych_eval.py` | `6e0b65154f2bebe806b5950c5cc83673cb0c1a00babb1eac179189de0ad69803` |
| `Testing/test_qwen35_owner_runnable_routes_static.py` | `42ba4999f713133094b35113eb1a920742d649c71b19aff622858ec4b9f72021` |
| `Testing/test_qwen35_production_singleton_launcher.py` | `afe06939da739a68a61faea0cc559cb207eb800a8710007766dfad394301ef55` |
| `Testing/test_model_request_policy.py` | `fe72680af1491c142a58ffb05e2084c96ce3480485205e7b28f9c69bac41c0ff` |
| `Testing/test_current_authority_reconciliation.py` | `ab8748c3313294be9d472be63b494dc80ddbd123fa0098d9bb84f21d23b8a70f` |

## Rollback

Rollback is hunk-level only. Preserve this checkpoint and all existing
attempts. If a source rollback is ever required, restore only the exact Qwen
pinning lines or the Blackwell-disable correction that caused the issue, then
rerun the same static suite. Do not restore Llama as an active selection or
automatic fallback without a new explicit owner decision.
