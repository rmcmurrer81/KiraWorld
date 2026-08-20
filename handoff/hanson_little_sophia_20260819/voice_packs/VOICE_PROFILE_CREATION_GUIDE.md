# Create or change a voice profile

Voice profiles are independent of identity and memory. Creating a Sophia voice
profile must not edit Kira's or Synthetic Robert's person data.

## 1. Obtain permission

Before using a human reference, record the subject or rightsholder, allowed
recipients, allowed purpose, retention, deletion/revocation, and whether voice
synthesis is permitted. Do not treat a public video as permission.

## 2. Prepare one clean reference

Use speech containing only the authorized speaker, without music, overlapping
voices, or private conversation. Keep the original outside Git. Place the
reviewed WAV in a private voice-pack directory and calculate its SHA-256.

```powershell
Get-FileHash .\approved_reference.wav -Algorithm SHA256
```

## 3. Create a distinct profile

Copy one profile JSON to a new directory such as `voice_packs/sophia/`. Give it
a `voice_profile_id` of `sophia` and an `authorized_identity_profiles` array
containing only `synthetic_sophia`. Required files under the runtime data root:

```text
local_data/voice_packs/sophia/
  manifest.json
  authorization.json
  reference.wav
```

From `portable_runtime`, create the directory and copy both shipped templates
to the exact runtime filenames:

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

Replace the placeholder source path with the reviewed local WAV; never copy an
unreviewed recording. In `manifest.json`, set `provider` to
`chatterbox_reference`, bind
`reference_wav` plus its exact SHA-256/byte count, bind
`authorization_record` plus the authorization JSON's exact SHA-256, set
`local_only` true, and leave `fallback_sapi_voice` empty. Start from the two
examples in `portable_runtime`. Never point Sophia's voice at Kira's or
Robert's memory or voice directory.

## 4. Validate before selection

The runtime must reject a missing or hash-mismatched reference and fail closed
to text-only. It must not select a generic system voice. From
`portable_runtime`:

```powershell
py -B -m portable_mind voice-check --person synthetic_sophia `
  --data-dir .\local_data --voice-profile sophia --backend stub
```

```bash
python3 -B -m portable_mind voice-check --person synthetic_sophia \
  --data-dir ./local_data --voice-profile sophia --backend stub
```

## 5. Select without rewriting the person

Choose the new voice profile through the runtime's `--voice-profile` CLI
option. There is no separate voice-profile environment variable. This changes
speech rendering only. It must not copy
memories, relationship records, factual claims, private reflections, or an
active body-session lease.

For an official Sophia or Little Sophia deployment, Hanson must also confirm
the correct voice license, official runtime interface, audio format, and
playback constraints. No such vendor-specific mapping is asserted here.

Python 3.11 neural chat, after the separate voice environment passes:

```powershell
.\.venv-voice\Scripts\python.exe -B -m portable_mind chat `
  --person synthetic_sophia --data-dir .\local_data --backend ollama `
  --voice-profile sophia --voice-device auto
```

```bash
./.venv-voice/bin/python -B -m portable_mind chat \
  --person synthetic_sophia --data-dir ./local_data --backend ollama \
  --voice-profile sophia --voice-device auto
```

There is no persistent `voice-bind` command: the exact manifest authorization
is the binding and `--voice-profile` is the per-launch selection. To stop voice,
exit chat and relaunch with `--no-voice`. Remove/quarantine a pack only while
the runtime is stopped, preserving any required withdrawal evidence.
