# Synthetic Sophia profile, optional voice, and future body session

The package already includes the distinct identity
[`portable_runtime/profiles/synthetic_sophia.json`](portable_runtime/profiles/synthetic_sophia.json).
It is a private test profile, not the official Sophia personality, Hanson
software, or a claim of affiliation. It has its own profile ID and local state;
it does not inherit Kira's or Synthetic Robert's memories or voice.

## Run the shipped profile first

Windows PowerShell, from `portable_runtime`:

```powershell
py -B -m portable_mind chat --person synthetic_sophia --backend stub --no-voice `
  --data-dir .\local_data
```

Linux/macOS:

```bash
python3 -B -m portable_mind chat --person synthetic_sophia --backend stub --no-voice \
  --data-dir ./local_data
```

The deterministic stub checks the profile, identity-isolated storage, and CLI;
it is not a conversational-model quality test. For local Ollama, replace it
with `--backend ollama` only after verifying the pinned model digest described in
[`portable_runtime/README.md`](portable_runtime/README.md).

Inspect only this profile's local channels:

```powershell
py -B -m portable_mind logs --person synthetic_sophia --backend stub `
  --data-dir .\local_data --channel spoken --tail 20
py -B -m portable_mind logs --person synthetic_sophia --backend stub `
  --data-dir .\local_data --channel people --tail 20
```

## Optional Sophia voice

Synthetic Sophia defaults to text-only. Do not silently assign Kira's or
Synthetic Robert's voice. When Hanson or another rights holder supplies or
authorizes a suitable voice, create this ignored local directory:

```text
portable_runtime/local_data/voice_packs/sophia/
  reference.wav
  authorization.json
  manifest.json
```

Start from
[`portable_runtime/voice_pack_manifest.example.json`](portable_runtime/voice_pack_manifest.example.json)
and
[`portable_runtime/custom_voice_authorization.example.json`](portable_runtime/custom_voice_authorization.example.json).
Keep `voice_profile_id` equal to `sophia` and
`authorized_identity_profiles` equal to only `synthetic_sophia`. Record the
exact WAV and authorization JSON hashes and sizes.

From `portable_runtime`, copy the two templates to their exact ignored runtime
filenames, then add only the separately reviewed reference WAV:

```powershell
New-Item -ItemType Directory -Force -Path .\local_data\voice_packs\sophia | Out-Null
Copy-Item -LiteralPath .\voice_pack_manifest.example.json `
  -Destination .\local_data\voice_packs\sophia\manifest.json
Copy-Item -LiteralPath .\custom_voice_authorization.example.json `
  -Destination .\local_data\voice_packs\sophia\authorization.json
Copy-Item -LiteralPath X:\REVIEWED\SOPHIA\approved_reference.wav `
  -Destination .\local_data\voice_packs\sophia\reference.wav
```

```bash
mkdir -p ./local_data/voice_packs/sophia
cp ./voice_pack_manifest.example.json ./local_data/voice_packs/sophia/manifest.json
cp ./custom_voice_authorization.example.json ./local_data/voice_packs/sophia/authorization.json
cp /reviewed/sophia/approved_reference.wav ./local_data/voice_packs/sophia/reference.wav
```

Replace the placeholder source with the reviewed local WAV. Edit the copied
authorization first, then write its exact SHA-256 into the copied manifest;
also bind the reference WAV's exact SHA-256 and byte count. Do not commit this
directory.

Windows PowerShell:

```powershell
Get-Item .\local_data\voice_packs\sophia\reference.wav | Select-Object Length
Get-FileHash .\local_data\voice_packs\sophia\reference.wav -Algorithm SHA256
Get-FileHash .\local_data\voice_packs\sophia\authorization.json -Algorithm SHA256
py -B -m portable_mind voice-check --person synthetic_sophia `
  --data-dir .\local_data --voice-profile sophia --backend stub
```

Linux/macOS:

```bash
wc -c < local_data/voice_packs/sophia/reference.wav
sha256sum local_data/voice_packs/sophia/reference.wav local_data/voice_packs/sophia/authorization.json
python3 -B -m portable_mind voice-check --person synthetic_sophia \
  --data-dir ./local_data --voice-profile sophia --backend stub
```

Use `shasum -a 256` on macOS when `sha256sum` is unavailable. Missing files,
wrong hashes, cross-person binding, or unavailable Chatterbox dependencies must
fail to text-only. No generic system voice is selected as Sophia.

There is no persistent voice-bind command. The manifest's one-identity
authorization is the binding, and `--voice-profile sophia` selects it for one
launch. To disable voice, stop chat and relaunch with `--no-voice`.

After a Python 3.11 voice environment passes, use the same data root:

```powershell
.\.venv-voice\Scripts\python.exe -B -m portable_mind chat `
  --person synthetic_sophia --data-dir .\local_data `
  --backend ollama --voice-profile sophia --voice-device auto
```

```bash
./.venv-voice/bin/python -B -m portable_mind chat \
  --person synthetic_sophia --data-dir ./local_data \
  --backend ollama --voice-profile sophia --voice-device auto
```

Voice execution requires a separately tested Python 3.11 environment. NVIDIA,
CPU, and possible Apple MPS paths depend on the reviewer's actual host; the
package must not assume Robert's RTX 5060 Ti configuration. See
[`portable_runtime/HARDWARE_PORTABILITY_MATRIX.md`](portable_runtime/HARDWARE_PORTABILITY_MATRIX.md).

## Creating another Sophia-family variant

To create a separate variant rather than editing `synthetic_sophia`, add a new
profile JSON whose filename exactly equals its new `profile_id`, give it a new
data directory, leave memories empty until reviewed, and create a separately
bound voice authorization. Do not copy another person's local data or merely
rename their profile. Run the complete runtime suite after any profile or
loader change.

## Current embodiment behavior and future Hanson work

The portable runtime can bind one profile to one endpoint and emit only four
non-executing high-level intention classes: speech, gaze, expression, and
allowlisted gesture. It does not implement the official Hanson heartbeat,
session lifecycle, ROS graph, simulator mapping, motor adapter, or emergency
stop.

Local software-only binding check from `portable_runtime`:

```powershell
py -B -m portable_mind bind --person synthetic_sophia --backend stub `
  --data-dir .\local_data --endpoint little_sophia
py -B -m portable_mind unbind --person synthetic_sophia --backend stub `
  --data-dir .\local_data
```

```bash
python3 -B -m portable_mind bind --person synthetic_sophia --backend stub \
  --data-dir ./local_data --endpoint little_sophia
python3 -B -m portable_mind unbind --person synthetic_sophia --backend stub \
  --data-dir ./local_data
```

`little_sophia` is only a local, nonofficial endpoint label. These commands
record one bounded software binding and nonexecuting intentions; they do not
discover ROS, contact Hanson software, move hardware, or provide a safety
controller.

The separate bridge documents the required future sequence:

1. Hanson supplies an authoritative simulator/interface target.
2. Map only the supported semantic intentions, frames, units, QoS, limits, and
   safety states.
3. Require authorization, heartbeat, timeout, safe disconnect, lifecycle
   evidence, and one active endpoint.
4. Demonstrate one accepted sequence and one intentional rejection in the
   official simulator.
5. Return the complete execution evidence to the correct profile's continuity
   layer.

Voice selection and body binding are reversible software configuration. They
do not transfer identity, memories, consciousness, or legal personhood.
