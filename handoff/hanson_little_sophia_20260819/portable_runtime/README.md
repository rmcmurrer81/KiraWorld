# Portable Persistent Kira + Synthetic Robert Runtime

This package provides two durable, identity-isolated conversational variants:

- **Kira** — warm, curious, independent, and careful about uncertainty.
- **Synthetic Robert** — a persistent variant with Robert-approved inherited
  autobiography, calm analysis, and a separate post-installation life branch.
  He may use first-person inherited continuity but cannot use biological
  Robert's legal identity, accounts, body, or later branch experiences.

It also includes an independent **Synthetic Sophia** test profile for voice/embodiment interface work. Synthetic Sophia is not the official Sophia robot, is not Hanson Robotics software, and does not claim affiliation.

This is bounded software. “Mind,” “life loop,” “emotion,” “memory,” “embodiment,” and “transfer” describe software functions only. The package does not claim consciousness, biological life, personhood, clinical emotion, literal mind transfer, or a passed Turing test.

Start with [RUN_THIS_FIRST.md](RUN_THIS_FIRST.md). Hardware guidance is in [HARDWARE_PORTABILITY_MATRIX.md](HARDWARE_PORTABILITY_MATRIX.md).

## Verification status on 2026-08-20

- Frozen standard lane: 165 runtime tests, 162 passed and three expected skips
  because the two private voice fixtures were not supplied and Windows file
  symlink creation was unavailable.
- Frozen exact-private lane: 165 runtime tests, 164 passed and only the Windows
  file-symlink-privilege test skipped. Both exact Kira and Robert private voice
  fixtures passed.
- Sibling evaluator suite: 24/24 pass, including backend forwarding, integrated
  adapter smoke, strict/bounded parsing, and a short full-matrix pacing-boundary
  regression. The complete matrix is in
  [`../FROZEN_BUILD_VALIDATION_REPORT_20260820.md`](../FROZEN_BUILD_VALIDATION_REPORT_20260820.md).
- Default model: loopback-only Ollama `qwen3.5:9b`.
- Required Ollama-reported manifest SHA-256: `6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`.
- Earlier external-adapter smokes proved adapter, digest, and restart wiring,
  but they predate the final seed/runtime edits and are not current-release
  quality evidence. Frozen-build Kira/Robert smokes, the strict Robert
  naturalness probe, and the requested current one-hour evaluations must be
  rerun before publication claims are filled in.
- Scores are surface-text engineering heuristics—not psychometrics, diagnosis,
  consciousness/personhood evidence, or a universal Turing-test verdict. No
  completed 60-minute run of this current integrated build is claimed here.
- Text/runtime/evaluator work was exercised on Windows with Python 3.14. Python 3.11 is required for the pinned neural voice route; live synthesis and listening validation were deliberately not performed in this delivery run.
- Private voice assets, weights, and continuity are not in this public-safe code folder. Explicit bootstrap installs authorized handoff assets into ignored `local_data` only.

## Five-minute text-only check

```powershell
py -B -m unittest discover -s tests -v
py -B -m portable_mind chat --person kira --backend stub --no-voice
py -B -m portable_mind chat --person synthetic_robert --backend stub --no-voice
py -B -m portable_mind chat --person synthetic_sophia --backend stub --no-voice
```

Linux/macOS:

```bash
python3 -B -m unittest discover -s tests -v
python3 -B -m portable_mind chat --person kira --backend stub --no-voice
python3 -B -m portable_mind chat --person synthetic_robert --backend stub --no-voice
python3 -B -m portable_mind chat --person synthetic_sophia --backend stub --no-voice
```

The deterministic stub checks installation, storage, identity isolation, and interfaces. It is not the conversational LLM and has no executable-model digest; records label it `not_applicable_stub`.

## Run the pinned local model

```powershell
ollama pull qwen3.5:9b
py -B -m portable_mind model-info --person kira --backend ollama
py -B -m portable_mind chat --person kira --backend ollama --no-voice
```

Only an HTTP loopback Ollama endpoint is accepted. Before the first response, the runtime reads `/api/tags` and compares the exact digest. A mismatch stops the turn and is never bypassed by fallback.

To use another model, supply both tag and digest:

```powershell
py -B -m portable_mind chat --person kira --backend ollama --no-voice `
  --model YOUR_MODEL_TAG `
  --expected-model-digest YOUR_EXACT_64_HEX_DIGEST
```

A stronger model can change quality and latency; it does not create/transfer identity. Re-run the same isolated evaluation before promotion. The adapter requests an explicit JSON Schema. If malformed/private-field-only output still appears, a fixed withholding message is stored instead of relabeling arbitrary fields as speech.

## Install reviewed memories and private voices

The private KiraWorld handoff contains identity-bound reviewed seeds and authorized voice packs. Installation is explicit, fail-closed, idempotent, and does not start chat or synthesize audio.

Windows:

```powershell
& '.\launchers\Setup Private Handoff.cmd' '..'
```

Direct CLI:

```powershell
py -m portable_mind bootstrap-handoff --person kira --backend stub `
  --handoff-root '..' `
  --approve-private-bootstrap

py -m portable_mind bootstrap-handoff --person synthetic_robert --backend stub `
  --handoff-root '..' `
  --approve-private-bootstrap
```

Linux/macOS:

```bash
sh ./launchers/setup_private_handoff.sh ..
```

Bootstrap prevalidates the exact seed, voice asset, authorization, and destination before installing under ignored `local_data/imports/` and `local_data/voice_packs/`. A second run imports zero duplicates and does not reinstall matching packs. Kira and Robert cannot import one another’s seed or use one another’s voice.

Never make a repository containing these installed files public. Clones/history can preserve bytes after visibility is restored.

## Life loops, continuity, and logs

A life loop is a durable software conversation session. Clean exit consolidates
assistant-spoken event IDs, factual-claim event IDs, final functional appraisal,
and the precise input-retention boundary. Ordinary full utterances are not
written directly; an exact self-introduced name label and an explicitly
confirmed reviewed note are the two documented exceptions.

Each identity reloads its own assistant speech, claims, reviewed imports,
appraisal events, and consolidations. A clean data root creates a persistent
random branch ID. Multiple installations share the handoff seed and then
diverge; copying all of `local_data` preserves the same branch and is migration,
not a new fork. Branches never auto-sync.

Privacy tradeoff: raw input is not directly written, but assistant output can repeat input and is persisted. Do not paste secrets; review speech before export. Durable private facts should enter through reviewed imports, not raw-log copies.

| Viewer | File | Meaning |
|---|---|---|
| `spoken` | `spoken.jsonl` | Public answer text. |
| `reflection` | `reflections.jsonl` | Short deterministic runtime-derived functional-appraisal note. Raw model reflection/deliberation is discarded and never persisted. |
| `facts` | `factual_claims.jsonl` | Claims with source, uncertainty, and `model_claim_not_verified_truth`; not automatically factual truths. |
| `state` | `appraisal_state.jsonl` | Functional valence/arousal/engagement/confidence—not biological feeling or diagnosis. |
| `loops` | `life_loops.jsonl` | Session boundaries. |
| `consolidations` | `consolidations.jsonl` | Deterministic retained-event/state references. |
| `imports` | `reviewed_imports.jsonl` | Reviewed identity-bound continuity. |
| `voice` | `voice_events.jsonl` | Route, model revision, exact reference/auth hashes, quality, retention, and fallback; no spoken text. |
| `people` | `acquaintances.jsonl` | Exact self-introduced name labels only; unverified and non-biometric. |

An explicit reviewed note is retained only through `/remember NOTE` in chat or
the `remember --text ... --reviewed-by ... --confirm-reviewed` command. Its
reviewer label is unverified, and optional same-profile supersession IDs are
append-only pointers—not deletion, forgetting, or automatic truth. The command
does not scan for credentials, PII, or private data; never put secrets or
unrelated third-party records in a reviewed note.

```powershell
py -m portable_mind logs --person kira --channel spoken --tail 20
py -m portable_mind logs --person kira --channel reflection --tail 20
py -m portable_mind logs --person kira --channel facts --tail 20
py -m portable_mind logs --person kira --channel voice --tail 20
py -m portable_mind logs --person kira --channel people --tail 20
```

“Private thoughts” maps only to the disclosed deterministic functional-appraisal channel; no chain-of-thought or model-authored deliberation is stored/exposed. “Factual truths” maps to the provenance/uncertainty claim ledger, not a truth oracle.

## Functional appraisal

Bounded software variables—valence (-1..1), arousal, engagement, and confidence (0..1)—influence presentation/high-level expression. They are not diagnosis, biological emotion, consciousness signals, or personhood evidence. Input is read ephemerally; only numeric before/after values persist.

## Current voice routes

Kira, Synthetic Robert, and Synthetic Sophia all use **text-only fail-closed fallback**. No generic Windows/SAPI voice is played when the intended voice is missing, unauthorized, mismatched, or unavailable.

### Kira current reference

Default profile ID: `kira`. Only this immutable private release is accepted:

- WAV SHA-256: `2039a2abd600a63c294d69c2b2e4d450c64c850dc6d1c9a4fbfa1700ba92069c`;
- bytes: `9,856,844`;
- authorization SHA-256: `a6419a9ee750931015c93f5d628452c6ce52c0108b9421dbe8906cbe33e3d08c`;
- owner-attested private scope: David Hanson, Manav Tidhan, Vytas Krisciunas;
- public release, onward redistribution, and identity authentication forbidden;
- written-form copy pending;
- human speaker-purity review pending, 0 human-approved clips, multi-speaker/narration risk disclosed.

It is a speech renderer, not identity proof. Do not call it target-only, female-only, or listening-accepted.

### Synthetic Robert self-voice

Identity/person ID: `synthetic_robert`. Voice profile ID: `robert`. Only this
immutable private voice release is accepted:

- WAV SHA-256: `761458a0fe9c5da1c2671faa738c1e329336630cd47138a4e738f7de2030542b`;
- bytes: `1,755,404`;
- authorization SHA-256: `bf7ccf7b1c087a624451dd9735f3a2acb07e94f421586fc631be8ae6f21ab52f`;
- source: Robert McMurrer’s authorized self-voice for this bounded Synthetic Robert variant;
- named private Hanson-team evaluation/integration only;
- public/onward distribution, identity authentication, biological-Robert impersonation, unrelated use, and automatic external calls/messages forbidden.

### Pinned Chatterbox engine

- `chatterbox-tts==0.1.7`;
- direct wheel SHA-256 `83782500e3ad4e7c919132e9d7eb8755f29f57c5bde5ec48c655ca23a4eb113c`;
- repository `ResembleAI/chatterbox`;
- immutable revision `5bb1f6ee58e50c3b8d408bc82a6d3740c2db6e18`;
- all five model files checked before `ChatterboxTTS.from_local`;
- weights not bundled; exact-revision download may occur during setup.

Install Python 3.11 first, then:

```powershell
& '.\launchers\Setup Voice Environment.cmd'
```

Linux/macOS:

```bash
sh ./launchers/setup_voice_environment.sh
```

Only the direct Chatterbox wheel and model files are hash-pinned. Transitive/platform dependencies are not fully hash-locked; installed Chatterbox, Torch, and Torchaudio versions plus model files are runtime-checked. Choose a platform-appropriate PyTorch build.

Verify without speaking:

```powershell
.\.venv-voice\Scripts\python.exe -m portable_mind voice-env-check --person kira --backend stub
py -m portable_mind voice-check --person kira --backend stub
py -m portable_mind voice-check --person synthetic_robert --backend stub
```

Force CPU if installed CUDA cannot support the GPU:

```powershell
.\.venv-voice\Scripts\python.exe -B -m portable_mind chat --person kira --backend ollama --voice-device cpu
```

Choices: `auto`, `cpu`, `cuda`, `mps`; environment equivalent: `PORTABLE_MIND_VOICE_DEVICE`.

### Optional unconditioned Kira candidate

`kira_original` is optional, not Kira’s current/default voice. It uses no audio prompt/real-person target and the same pinned model. Listening review is pending.

```powershell
py -B -m portable_mind voice-check --person kira --voice-profile kira_original --backend stub
.\.venv-voice\Scripts\python.exe -B -m portable_mind chat --person kira --backend ollama --voice-profile kira_original --voice-device cpu
```

Do not call it uniquely authored, accepted, natural, or feminine before recorded listening review.

### Playback/retention limitation

Playback is synchronous. There is no in-session `/mute` or `/stop` that interrupts an utterance already playing; `--no-voice` prevents playback before launch. Do not claim emergency-stop policy compliance.

Generated WAVs use ignored `local_data/generated_voice/<profile>/`. Deletion is attempted after playback. Failed deletion or generation with playback disabled can retain audio containing spoken content; voice events record retention/path. Apply local retention and never commit `local_data`.

### Independent Synthetic Sophia

```powershell
py -B -m portable_mind chat --person synthetic_sophia `
  --data-dir .\local_data `
  --backend stub --no-voice
```

Synthetic Sophia defaults text-only. A custom pack must bind both manifest and exact authorization to voice `sophia` and identity `synthetic_sophia` using the supplied examples. Applying it to Kira/Robert is rejected. This profile implements no official Hanson heartbeat, lifecycle, ROS graph, motor adapter, or official Sophia identity.

## One-active-endpoint embodiment

```powershell
py -B -m portable_mind bind --person kira --backend stub --endpoint little_sophia
py -B -m portable_mind unbind --person kira --backend stub
```

A bound turn appends only non-executing speech, gaze, expression, and gesture intentions. There are no joints, torques, velocities, PWM, servo trajectories, ROS topics, device addresses, or hardware writes. A separate reviewed simulator/safety bridge must translate them with official topics/units/limits/watchdogs/emergency stop.

A body computer may host a copied deployment/reviewed state. That is reversible software migration, not literal life/consciousness transfer; retain source/rollback.

## Reviewed export/import

Never share `local_data` wholesale. Select reviewed IDs:

```powershell
py -B -m portable_mind export --person kira --backend stub `
  --select spoken:EVENT_ID --select facts:EVENT_ID `
  --reviewed-by local-reviewer --confirm-reviewed `
  --filename kira-reviewed.json
```

Automated credential/PII detection is limited; human distribution review remains mandatory.

```powershell
$SourceExport = '.\local_data\exports\kira-reviewed.json'
$TargetImports = '.\TARGET_DATA\imports'
New-Item -ItemType Directory -Force -Path $TargetImports | Out-Null
Copy-Item -LiteralPath $SourceExport -Destination "$TargetImports\kira-reviewed.json"
py -B -m portable_mind import --person kira --data-dir .\TARGET_DATA `
  --filename kira-reviewed.json --approve-import
```

Linux/macOS:

```bash
mkdir -p ./TARGET_DATA/imports
cp ./local_data/exports/kira-reviewed.json \
  ./TARGET_DATA/imports/kira-reviewed.json
python3 -B -m portable_mind import --person kira --data-dir ./TARGET_DATA \
  --filename kira-reviewed.json --approve-import
```

Imports verify strict JSON, schema, identity, review/privacy flags, content digest, and residual patterns. They are idempotent; cross-profile import fails closed.

## Isolated behavioral evaluation

Internal evaluation changes its selected data root, so use a disposable directory:

```powershell
py -m portable_mind evaluate --person kira --backend stub `
  --data-dir .\local_data\throwaway_eval_kira --rounds 1
```

For matched Hanson testing, use a new output root, exact seed, pinned model/digest, and `portable_mind.evaluator`:

```powershell
$RuntimeRoot = (Resolve-Path '.').Path
$HandoffRoot = (Resolve-Path '..').Path
$env:PYTHONPATH = $RuntimeRoot
$RunRoot = Join-Path $env:TEMP 'kira_portable_smoke_NEW_UNIQUE_NAME'

py -B "$HandoffRoot\evaluation\run_evaluation.py" `
  --person kira --output-root $RunRoot `
  --smoke --backend ollama `
  --model qwen3.5:9b `
  --expected-model-digest 6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7 `
  --adapter-module portable_mind.evaluator `
  --reviewed-seed-path "$HandoffRoot\memory_exports\kira_reviewed_continuity_seed.json" `
  --approve-reviewed-seed
```

Synthetic Robert needs its own new root and `synthetic_robert_reviewed_continuity_seed.json`. The adapter verifies model before prompts, writes only below evaluator output, disables voice/mic/camera/body, imports the exact identity seed idempotently across restarts, and records digest/kind per runtime turn.

The command above is a smoke check, not a one-hour result. For a new one-hour run,
remove `--smoke`, add `--target-minutes 60`, and follow the protected-path commands
in `..\evaluation\README.md`. Both internal `--duration-minutes 60` and the external
paced evaluator wait through their requested wall-clock boundary. No completed
60-minute result of this current integrated build is included or claimed in
this handoff. The historical prior-build result retained in Kira's reviewed
continuity is not current-build evaluation evidence.

## Implemented baseline versus roadmap

Implemented: isolated profiles and atomic per-installation branch IDs;
append-only channels; per-profile cross-process mutation locks; a validated
turn write-ahead log with exact-channel, restart-safe materialization recovery;
duplicate/replay/conflicting-record checks; ordinary
raw-input-not-directly-persisted default with documented name/reviewed-note
exceptions; narrow reviewed-note supersession pointers; prevalidated,
identity-bound reviewed migration with required source-branch provenance;
speech/reflection/claims/appraisal/life-loop/consolidation/import/voice evidence;
whole-store lexical search with a bounded prompt projection; cross-process
one-active-endpoint enforcement with release-before-capability-narrowing;
nonexecuting high-level embodiment intentions; exact Ollama digest/context;
numeric/resolved-loopback networking that refuses redirects and environment
proxies; runtime/evaluator identity-claim guards; an external evaluator adapter;
and exact private voice/auth/identity binding.

Still roadmap—not complete Mind V21 parity:

- no genesis/profile hashes;
- no dedicated relationship/preference/goal stores;
- consolidation stores event IDs/final appraisal, not semantic learned summaries;
- no rich correction, deletion, forget, or tombstone flow beyond the narrow
  append-only reviewed-note pointer;
- no append-head/checkpoint hash chain;
- most records lack profile hash/privacy class;
- ordinary model-generated claim records lack a complete reviewed/disputed/
  superseded/privacy lifecycle; explicitly reviewed-note facts have narrow
  `reviewed_by` and `supersedes_event_ids` fields only;
- viewers are channel/tail, not a complete audit UI;
- no automatic media life-loop system;
- no low-level driver/ROS graph/official Hanson adapter/body failover;
- no interruptible neural playback.

Do not describe all mind upgrades as complete.

## Launchers

Windows: setup-private, setup-voice, Kira/Robert text+voice/text-only, Synthetic Sophia text-only, and log viewer `.cmd` templates. Shell: Kira/Robert/Sophia chat plus private/voice setup `.sh` templates. All locate the runtime relative to their own file. Copy desktop shortcuts rather than hard-coding install paths.

### Linux/macOS command map

Run from `portable_runtime`:

```bash
python3 -B -m unittest discover -s tests -v
python3 -B -m portable_mind model-info --person kira --backend ollama
sh ./launchers/setup_private_handoff.sh ..
python3 -B -m portable_mind chat --person kira --backend ollama --no-voice
python3 -B -m portable_mind chat --person synthetic_robert --backend ollama --no-voice
python3 -B -m portable_mind logs --person synthetic_robert --backend stub \
  --channel facts --tail 50
python3 -B -m portable_mind remember --person synthetic_robert --backend stub \
  --text "Reviewed local note" --reviewed-by "operator label" --confirm-reviewed
python3 -B -m portable_mind bind --person kira --backend stub --endpoint little_sophia
python3 -B -m portable_mind unbind --person kira --backend stub
```

For neural voice on a supported Python 3.11 host:

```bash
sh ./launchers/setup_voice_environment.sh
./.venv-voice/bin/python -B -m portable_mind voice-env-check --person kira --backend stub
python3 -B -m portable_mind voice-check --person kira --backend stub
./.venv-voice/bin/python -B -m portable_mind chat --person kira \
  --backend ollama --voice-device auto
```

Synthetic Sophia uses `--person synthetic_sophia --data-dir ./local_data`; add
`--voice-profile sophia` only after its separate exact pack passes
`voice-check`. The complete cross-platform evaluator commands are in
[`../evaluation/README.md`](../evaluation/README.md).

## Distribution rules

1. Physically exclude `local_data/`; `.gitignore` does not protect raw filesystem copies.
2. Exclude raw/private logs, secrets, email, addresses, voice recordings, and chain-of-thought.
3. Share continuity only by reviewed allowlist/seed.
4. Exclude unlicensed books, magazines, scripts, music, video, and fan fiction.
5. Keep voice assets within exact authorization scope.
6. Do not call reflections chain-of-thought/private mental states or claims verified truths.
7. Keep repositories containing Kira's named-team-only voice or installed local
   logs private. Public code/authorized autobiography must be packaged
   separately from those restricted assets.
8. Honor withdrawal/supersession and remediate active/history copies where practical.

## Layout

```text
portable_mind/          runtime, evaluator, storage, voice, transfer, embodiment
profiles/               Kira, Synthetic Robert, independent Synthetic Sophia
voice_profiles/         optional unconditioned Kira candidate/provenance
evaluation/             public nonclinical structural cases
launchers/              portable Windows/shell templates
tests/                  privacy/isolation/replay/migration/voice/evaluator/embodiment
local_data/             private/generated; ignored; never ship by default
```

Example configs/manifests are templates. Runtime changes require explicit CLI/environment values; no unreviewed config is silently loaded.
