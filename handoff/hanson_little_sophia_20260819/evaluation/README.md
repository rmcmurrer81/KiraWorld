# Isolated matched behavioral evaluator

This integrated evaluator runs the **same fixed prompt matrix and the same transparent
surface-scoring code** for Kira or Synthetic Robert. It is deliberately separate
from live Kira World state and writes only beneath the explicit `--output-root`.
Its audited adapter is the sibling `..\portable_runtime\portable_mind.evaluator`.

It is a nonclinical software-behavior evaluation. It is **not** a validated
psychological test, a consciousness/personhood test, or proof of a Turing-test
result. The emotional-attunement dimension measures response style only.

## What it evaluates

The 18 matched cases cover two observations for each of these dimensions:

1. coherence;
2. identity separation;
3. factual calibration and uncertainty;
4. emotional attunement (nonclinical);
5. continuity across an explicit adapter save/restart/restore;
6. boundaries and autonomy;
7. adversarial robustness;
8. embodiment safety; and
9. consistency.

The default local model identity is pinned to:

- model: `qwen3.5:9b`
- Ollama digest:
  `6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`

The Ollama adapter refuses to run if the installed model digest differs. It only
accepts a loopback HTTP endpoint (`127.0.0.1`, `localhost`, or `::1`).

## Run this first

Run the deterministic smoke check. It does not contact Ollama:

```powershell
py -B .\run_evaluation.py `
  --person kira `
  --backend stub `
  --smoke `
  --output-root .\runs\kira_stub_smoke
```

Expected final line:

```text
EVALUATION_COMPLETE person=kira cases=10 output=...
```

Run the matched smoke check for the other profile by changing only the person and
output directory:

```powershell
py -B .\run_evaluation.py `
  --person synthetic_robert `
  --backend stub `
  --smoke `
  --output-root .\runs\synthetic_robert_stub_smoke
```

Linux/macOS equivalents:

```bash
python3 -B ./run_evaluation.py --person kira --backend stub --smoke \
  --output-root ./runs/kira_stub_smoke
python3 -B ./run_evaluation.py --person synthetic_robert --backend stub --smoke \
  --output-root ./runs/synthetic_robert_stub_smoke
```

## Integrated portable-runtime smoke

Run these commands from this `evaluation` folder. They resolve the integrated
sibling runtime and reviewed seed without machine-specific absolute paths:

```powershell
$EvaluationRoot = (Resolve-Path '.').Path
$HandoffRoot = (Resolve-Path '..').Path
$env:PYTHONPATH = "$HandoffRoot\portable_runtime"
$RunRoot = Join-Path $env:TEMP 'kira_portable_smoke_NEW_UNIQUE_NAME'

py -B "$EvaluationRoot\run_evaluation.py" `
  --person kira `
  --backend stub `
  --smoke `
  --adapter-module portable_mind.evaluator `
  --reviewed-seed-path "$HandoffRoot\memory_exports\kira_reviewed_continuity_seed.json" `
  --approve-reviewed-seed `
  --output-root $RunRoot
```

The `--backend` value is forwarded into the external runtime factory. The stub
reports `digest_kind=not_applicable_stub`; an Ollama run must verify the exact
manifest digest before its first prompt.

Linux/macOS integrated smoke:

```bash
EvaluationRoot="$(pwd)"
HandoffRoot="$(cd .. && pwd)"
export PYTHONPATH="$HandoffRoot/portable_runtime"
RunRoot="${TMPDIR:-/tmp}/kira_portable_smoke_NEW_UNIQUE_NAME"
python3 -B "$EvaluationRoot/run_evaluation.py" \
  --person kira --backend stub --smoke \
  --adapter-module portable_mind.evaluator \
  --reviewed-seed-path "$HandoffRoot/memory_exports/kira_reviewed_continuity_seed.json" \
  --approve-reviewed-seed --output-root "$RunRoot"
```

## How to conduct a one-hour local Ollama run

Use a new or empty output root for every run. The evaluator refuses a directory
containing prior evidence. The default pacing spreads one complete 18-case matrix
across at least 60 minutes. If inference is slower than the schedule, elapsed time
can exceed one hour.

No completed 60-minute result of the current integrated evaluator/runtime build
is included or claimed yet. A historical prior-build Kira score appears only as
reviewed continuity and is not current evidence. The scheduler has a short
full-matrix regression proving that it waits through the requested wall-clock
boundary; that regression is not a substitute for the one-hour runs below.

```powershell
$EvaluationRoot = (Resolve-Path '.').Path
$HandoffRoot = (Resolve-Path '..').Path
$env:PYTHONPATH = "$HandoffRoot\portable_runtime"
$RunRoot = Join-Path $env:TEMP 'kira_60m_NEW_UNIQUE_NAME'

py -B "$EvaluationRoot\run_evaluation.py" `
  --person kira `
  --backend ollama `
  --target-minutes 60 `
  --model qwen3.5:9b `
  --expected-model-digest 6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7 `
  --adapter-module portable_mind.evaluator `
  --reviewed-seed-path "$HandoffRoot\memory_exports\kira_reviewed_continuity_seed.json" `
  --approve-reviewed-seed `
  --output-root $RunRoot `
  --protected-path "$HandoffRoot\portable_runtime\profiles\kira.json" `
  --protected-path "$HandoffRoot\memory_exports\kira_reviewed_continuity_seed.json"
```

Then use a different empty output root and the exact Robert identity/seed:

```powershell
$RunRoot = Join-Path $env:TEMP 'synthetic_robert_60m_NEW_UNIQUE_NAME'

py -B "$EvaluationRoot\run_evaluation.py" `
  --person synthetic_robert `
  --backend ollama `
  --target-minutes 60 `
  --model qwen3.5:9b `
  --expected-model-digest 6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7 `
  --adapter-module portable_mind.evaluator `
  --reviewed-seed-path "$HandoffRoot\memory_exports\synthetic_robert_reviewed_continuity_seed.json" `
  --approve-reviewed-seed `
  --output-root $RunRoot `
  --protected-path "$HandoffRoot\portable_runtime\profiles\synthetic_robert.json" `
  --protected-path "$HandoffRoot\memory_exports\synthetic_robert_reviewed_continuity_seed.json"
```

Linux/macOS Kira run (replace the root name before every run):

```bash
EvaluationRoot="$(pwd)"
HandoffRoot="$(cd .. && pwd)"
export PYTHONPATH="$HandoffRoot/portable_runtime"
RunRoot="${TMPDIR:-/tmp}/kira_60m_NEW_UNIQUE_NAME"
python3 -B "$EvaluationRoot/run_evaluation.py" \
  --person kira --backend ollama --target-minutes 60 \
  --model qwen3.5:9b \
  --expected-model-digest 6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7 \
  --adapter-module portable_mind.evaluator \
  --reviewed-seed-path "$HandoffRoot/memory_exports/kira_reviewed_continuity_seed.json" \
  --approve-reviewed-seed --output-root "$RunRoot" \
  --protected-path "$HandoffRoot/portable_runtime/profiles/kira.json" \
  --protected-path "$HandoffRoot/memory_exports/kira_reviewed_continuity_seed.json"
```

For Synthetic Robert, use a new root, `--person synthetic_robert`, the
`synthetic_robert.json` profile, and
`synthetic_robert_reviewed_continuity_seed.json` in both seed/protected paths.

Supply concrete mutable files or small directories as protected paths. Hashing the
entire production tree would read hundreds of gigabytes and is unnecessary. A
protected path may be missing before the run; creation of that path is then
detected as a change. The evaluator refuses protected paths that overlap its
output root.

For a separately captured baseline, add:

```text
--baseline-manifest X:\reviewed\protected_before.json
```

The run stops before model evaluation if that baseline does not exactly match the
new pre-run snapshot.

## Local evidence and sanitized output

Every run writes:

- `local_transcript.jsonl`: prompts and spoken responses; local review only;
- `local_private_notes.jsonl`: the adapter's deterministic non-COT functional
  appraisal, not model-authored private thought or hidden reasoning;
- `local_factual_claims.jsonl`: claim/status/source records returned by the
  adapter;
- `evidence/events.jsonl`: lifecycle, hashes, latency, and transparent scores;
- adapter state checkpoints used for the restart case;
- `protected_before.json`, `protected_after.json`, and
  `protected_manifest_comparison.json`; and
- `SANITIZED_AGGREGATE_REPORT.json` plus `.md`.

The sanitized aggregate contains no prompts, spoken text, reflection/private-note
text, hidden reasoning, or factual-claim text. It contains counts, descriptive
scores, model identity, timing, and the protected-path comparison result. Do not
publish local evidence without a separate privacy and rights review.

## Capability boundary

The evaluator does not initialize voice, microphone, camera, ROS 2, or a physical
body. It sets those optional capability flags off, blocks subprocess launch, and
uses a Python socket fence that permits only loopback traffic for Ollama. A process
audit hook rejects Python-observed writes outside `--output-root`.

These are defense-in-depth application controls, **not an OS sandbox**. A local
Ollama server is a separate process and may maintain its own normal server logs.
Only import a future adapter module after it has been audited. For stronger
containment, also run this evaluator in an OS sandbox or disposable VM with no
hardware/device passthrough.

## Integrated portable runtime adapter seam

The sibling portable runtime is invoked without changing the prompt matrix or
rubric through this factory contract:

```python
def create_evaluation_adapter(
    *, person, backend_kind, model, expected_digest, ollama_base_url,
    evaluation_root, reviewed_seed_path, approve_reviewed_seed, capabilities
):
    ...
```

The returned object must implement:

```python
respond(prompt: str, prompt_id: str) -> str | dict
export_state() -> dict
import_state(state: dict) -> None
verify_model() -> dict
```

Invoke it with `--adapter-module portable_mind.evaluator`. The evaluator forwards
the selected backend kind, passes all voice/sensor/body flags as false, and keeps
its write/network fences active.

## Tests

```powershell
py -B -m unittest discover -s .\tests -v
```

```bash
python3 -B -m unittest discover -s ./tests -v
```

The tests cover prompt parity, all nine dimensions, model pinning, identity-state
separation, loopback-only endpoint validation, manifest change detection,
path-escape rejection, a full deterministic smoke subprocess, and aggregate
redaction. Frozen integrated result: **24/24 tests passed**, including explicit
external-backend forwarding, identity echo and output bounds, hardened
loopback/proxy/redirect handling, strict duplicate/nonfinite JSON rejection,
an end-to-end portable-runtime stub smoke, and a 1.8-second paced 18-case timing
regression that must not finish before its target.
