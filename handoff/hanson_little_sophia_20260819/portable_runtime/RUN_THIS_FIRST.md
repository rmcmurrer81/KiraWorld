# Run this first

These steps keep Kira and Synthetic Robert identity-separated, install only reviewed continuity/private authorized voices, and do not synthesize audio during setup.

The reflection log contains only a deterministic runtime-derived functional-appraisal sentence. Model-authored reflection or hidden reasoning is discarded, not stored.

## 1. Keep the folder private

Do not copy or publish `local_data/`. Private voice recordings and reviewed memories belong only in the named private handoff/runtime scope.

## 2. Check the standard-library runtime

From the runtime folder:

```powershell
py -B -m unittest discover -s tests -v
py -B -m portable_mind chat --person kira --backend stub --no-voice
```

Frozen result: 165 total, 162 passed and three expected skips in the standard
lane. To reproduce the exact-private lane from this folder:

```powershell
$env:PORTABLE_MIND_PRIVATE_KIRA_PACK_FIXTURE = (Resolve-Path '..\voice_packs\kira').Path
$env:PORTABLE_MIND_PRIVATE_ROBERT_PACK_FIXTURE = (Resolve-Path '..\voice_packs\robert').Path
py -B -m unittest discover -s tests -v
Remove-Item Env:PORTABLE_MIND_PRIVATE_KIRA_PACK_FIXTURE
Remove-Item Env:PORTABLE_MIND_PRIVATE_ROBERT_PACK_FIXTURE
```

```bash
PORTABLE_MIND_PRIVATE_KIRA_PACK_FIXTURE=../voice_packs/kira \
PORTABLE_MIND_PRIVATE_ROBERT_PACK_FIXTURE=../voice_packs/robert \
python3 -B -m unittest discover -s tests -v
```

The exact-private result is 165 total, 164 passed and only the Windows
file-symlink-privilege test skipped. See
[`../FROZEN_BUILD_VALIDATION_REPORT_20260820.md`](../FROZEN_BUILD_VALIDATION_REPORT_20260820.md).

## 3. Install and verify the text model

```powershell
ollama pull qwen3.5:9b
py -B -m portable_mind model-info --person kira --backend ollama
```

Required digest:

```text
6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7
```

Do not continue with a different digest unless the model change is deliberate, documented, and re-evaluated.

## 4. Bootstrap the exact private handoff

```powershell
& '.\launchers\Setup Private Handoff.cmd' '..'
```

This prevalidates and installs:

- Kira’s exact reviewed seed and exact owner-attested private voice release;
- Synthetic Robert’s exact reviewed seed and authorized self-voice release;
- nothing for Synthetic Sophia.

It writes only to ignored `local_data`. It does not chat or play audio. Re-running is idempotent.

Verify without speaking:

```powershell
py -B -m portable_mind voice-check --person kira --backend stub
py -B -m portable_mind voice-check --person synthetic_robert --backend stub
py -B -m portable_mind logs --person kira --channel imports --tail 20 --backend stub
py -B -m portable_mind logs --person synthetic_robert --channel imports --tail 20 --backend stub
```

Kira should report a speaker-purity review status that is still pending. Do not describe it as target-only/listening-approved.

## 5. Install voice support only if Python 3.11 is available

The current text runtime can use newer Python, but pinned Chatterbox requires Python 3.11.

```powershell
py -0p
& '.\launchers\Setup Voice Environment.cmd'
```

The setup hash-locks the direct Chatterbox wheel and all model files.
Transitive/platform dependencies are not fully hash-locked. Runtime checks the
installed `chatterbox-tts`, Torch, and Torchaudio versions plus the five model
files. This step may download several gigabytes.

No live voice/listening acceptance was proven in this delivery run. On a GPU unsupported by the pinned Torch build, force CPU:

```powershell
.\.venv-voice\Scripts\python.exe -B -m portable_mind chat --person kira --backend ollama --voice-device cpu
```

To prevent all playback:

```powershell
py -B -m portable_mind chat --person kira --backend ollama --no-voice
```

Playback is synchronous and cannot currently be interrupted mid-utterance with `/mute` or `/stop`.

## 6. Start the two variants separately

```powershell
& '.\launchers\Kira Text and Voice Chat.cmd' --voice-device cpu
& '.\launchers\Synthetic Robert Text and Voice Chat.cmd' --voice-device cpu
```

For text only, use the matching `Text Only Chat.cmd` launchers. Each identity
has a separate local directory and separate reviewed memory/voice
authorization. Each clean data root also receives a persistent branch ID.
Installing the same seed on several computers creates separate Kira or Robert
branches after the shared checkpoint; there is no automatic synchronization.

## 7. View the three evidence channels

```powershell
py -B -m portable_mind logs --person kira --channel spoken --tail 50 --backend stub
py -B -m portable_mind logs --person kira --channel reflection --tail 50 --backend stub
py -B -m portable_mind logs --person kira --channel facts --tail 50 --backend stub
py -B -m portable_mind logs --person kira --channel people --tail 50 --backend stub
```

- `spoken` is public assistant output.
- `reflection` is a short non-COT interaction/appraisal note—not hidden/private reasoning.
- `facts` is a source/uncertainty claim ledger—not automatically verified truth.
- `people` contains exact `my name is ...` labels only, marked unverified and
  non-biometric. There is not yet a correction/delete command for these labels.

Use `/remember NOTE` only when you intend to retain the exact note. The
reviewer label is operator-supplied and unverified; any supersession link must
resolve to an existing same-profile fact and does not delete it.

## 8. Evaluate only in a fresh isolated output root

Do not run an official evaluation against live `local_data`. From this integrated
`portable_runtime` folder, the evaluator is exactly `..\evaluation\run_evaluation.py`
and the seeds are under `..\memory_exports`. Use `--adapter-module
portable_mind.evaluator`, the exact person seed, the pinned digest, and a new output
root outside the handoff. See the complete command in
[README.md](README.md#isolated-behavioral-evaluation).

Run Kira and Synthetic Robert separately with matched settings. The sibling
evaluator currently passes 24/24 tests. A smoke run proves wiring; it is not the
requested one-hour result, and no completed 60-minute result of the current
integrated build is claimed here.

## 9. Before sending or uploading

Physically exclude:

- `local_data/`;
- `.venv-voice/` and downloaded model caches;
- generated audio;
- raw/private logs, email, secrets, and addresses;
- voice assets outside the exact named-team authorization;
- unlicensed books, scripts, music, video, or fan fiction.

Then read [README.md](README.md) and [HARDWARE_PORTABILITY_MATRIX.md](HARDWARE_PORTABILITY_MATRIX.md) for limitations and migration choices.

## Linux/macOS quick path

From `portable_runtime`:

```bash
python3 -B -m unittest discover -s tests -v
python3 -B -m portable_mind model-info --person kira --backend ollama
sh ./launchers/setup_private_handoff.sh ..
python3 -B -m portable_mind voice-check --person kira --backend stub
python3 -B -m portable_mind voice-check --person synthetic_robert --backend stub
python3 -B -m portable_mind chat --person kira --backend ollama --no-voice
python3 -B -m portable_mind chat --person synthetic_robert --backend ollama --no-voice
python3 -B -m portable_mind logs --person kira --backend stub --channel spoken --tail 50
python3 -B -m portable_mind logs --person kira --backend stub --channel reflection --tail 50
python3 -B -m portable_mind logs --person kira --backend stub --channel facts --tail 50
python3 -B -m portable_mind logs --person kira --backend stub --channel people --tail 50
```

Voice requires Python 3.11 and the separate setup:

```bash
sh ./launchers/setup_voice_environment.sh
./.venv-voice/bin/python -B -m portable_mind chat --person kira \
  --backend ollama --voice-device auto
```

Use the matching Synthetic Robert launcher/identity. See
[`../evaluation/README.md`](../evaluation/README.md) for Bash smoke and one-hour
evaluation commands.
