# Qwen 3.5 Kira Turing/psychology + voice evaluation static repair — 2026-08-09

Status: **STATIC PREPARATION PASSED; LIVE OWNER-SUPERVISED EVALUATION NOT RUN.**

The evaluation harness was repaired after an independent read-only audit found
that the earlier draft could ignore a later voluntary stop, mislabel latency
timings, equate completed speaker playback with Robert actually hearing it,
inherit an unreviewed model digest from the parent environment, and accept an
incomplete preparation contract.

The repaired harness now:

- pins `qwen3.5:9b` and its approved digest in a restricted allowlisted child
  environment;
- rejects contradictory initial consent and honors a later voluntary stop;
- records returned-model identity, text timing, voice timing, and all
  no-fallback/CPU/generic/SAPI fields explicitly;
- distinguishes technical playback completion from Robert's separate,
  post-playback hearing acknowledgment;
- requires the exact canonical preparation schema and source bindings;
- preserves the shared Qwen/voice serialization and clean-release gates; and
- defines prohibited media as unrelated/library media, not the approved reply
  WAV used by the test itself.

Append-only evidence:

- preserved `attempt_01/EVALUATION_CONTRACT.json` SHA-256:
  `17711e5396fdf42bee666f12ea0112c79d5f34b8ba6c3d17d2cce9532a436eb0`
- current `attempt_02/EVALUATION_CONTRACT.json` SHA-256:
  `f9d1e0992f7829619e3787385339ec409b97e747e7e97372e2ab6aa332462b59`

Current bound files:

| Project-relative path | Bytes | SHA-256 |
|---|---:|---|
| `tools/prepare_qwen35_kira_turing_psych_voice_evaluation.py` | 11818 | `b08e838cebfd20e211596eb44f2171915ce623c3386e4df9111cf8ef7ae21c48` |
| `tools/run_qwen35_kira_turing_psych_voice_owner_evaluation.py` | 73372 | `85a05d53cb7c65dd497b076ea22bed7e76005719ed79b93f77be267a68ce1773` |
| `Testing/test_qwen35_kira_turing_psych_voice_evaluation_preparation.py` | 5385 | `0cb317113b44a4d66370445b0c4a01ed2479f2477875f291f3e1673f1270ef66` |
| `Testing/test_qwen35_kira_turing_psych_voice_owner_evaluation.py` | 34357 | `0b480fb67edc568b9d54e28ec433c802d6b70cf73cfd56ea9882465c8c115160` |
| `RecoverySprint/continuation_20260809/kira_qwen35_turing_psych_voice_owner_evaluation_preparation/attempt_02/EVALUATION_CONTRACT.json` | 9701 | `f9d1e0992f7829619e3787385339ec409b97e747e7e97372e2ab6aa332462b59` |

Independent verification command:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
py -B -m unittest Testing.test_qwen35_kira_turing_psych_voice_evaluation_preparation Testing.test_qwen35_kira_turing_psych_voice_owner_evaluation -v
```

Result: **31 tests passed, 0 failures/errors, 0.079 seconds.** The run was
static/mocked only. It did not load Qwen, synthesize or play voice, access a
camera or microphone, launch Blender, or conduct a live Kira conversation.

The live six-turn Turing/psychology and owner-hearing acceptance remains
deliberately blocked until Robert is present to give the exact public opt-in,
hear the actual playback, report what he heard, and retain the ability to stop
at every boundary. No unattended process may manufacture those facts.

Rollback: restore the five bound files from the prior checkpoint and select
the preserved `attempt_01` only as historical evidence. Never overwrite either
append-only preparation attempt.
