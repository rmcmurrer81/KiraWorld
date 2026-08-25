# Kira Labs Local Voice Studio — Core Contract

This is an additive, privacy-first foundation for a local voice studio. Its
default backend remains a clearly marked silent-WAV contract mock. An optional
Kokoro subprocess adapter is now present but remains fail-closed. Exact runtime,
worker, dependency-lock, model, configuration, and voice-pack identities are
required, and a reviewed OS isolation provider is also required. No such
provider is enabled in this release, so the real adapter reports `ready: false`
even for an otherwise valid bundle. This change does not download or execute a
model and makes no general production-quality claim.

## What is real now

- A loopback-only HTTP/JSON API (`127.0.0.1`) with a per-install 256-bit bearer
  capability, DNS-rebinding-shaped Host-header rejection, bounded request
  threads, and no permissive CORS headers.
- Health and capability discovery that truthfully identifies the mock backend.
- Validated asynchronous synthesis requests, polling, cancellation, and terminal
  states.
- A backend protocol that keeps model/GPU dependencies outside the trusted API
  and storage core.
- An append-only voice registry with keyed integrity records and append-only
  deactivation tombstones. An existing `voice_id` cannot silently change
  identity, source, or permission basis. This detects accidental/casual record
  tampering; it is not protection from an administrator who controls both the
  data root and its integrity key.
- Two independent labels for every voice:
  - source basis: `source_recording_backed`, `designed`, or `generic_fallback`;
  - review status: `not_auditioned`, `auditioned`, or `owner_approved`.
- Immutable consent/provenance records, including scope, authority, timestamp,
  permissions, optional expiry, and optional evidence digest. Expired consent is
  rejected at synthesis time.
- Reference ingestion that validates PCM WAV metadata and computes SHA-256. It
  returns `copied: false`; it does not copy or enroll the recording.
- Output-path containment, cross-process name and storage-quota reservations,
  text/body/metadata limits, no overwrite, and atomic JSON receipts with output
  digests. Receipts retain text and metadata counts only—not plaintext,
  metadata keys/values, or hashes of private request content.

This directory does not read, migrate, modify, or route any existing Kira voice
profile, reference pack, authorization, generated audio, or sidecar. Integrating
those private assets requires a later explicit migration and owner review.

## Privacy and identity rules

1. The service refuses non-loopback bind addresses.
2. A source-recording-backed voice requires source-subject consent, consent
   evidence SHA-256, permission to use the reference, permission to generate
   audio, and at least one reference SHA-256.
3. Designed and generic voices cannot carry hidden reference hashes.
4. `auditioned` means a human listened to that particular registered profile. It
   never means identity was verified or consent was granted.
5. The current runnable backend is explicitly marked `mock_audio: true` in every receipt.
6. Reference paths are not persisted by the inspection API; only technical
   metadata and a content digest are returned to the caller.

## Run tests (Python 3.14, no third-party packages)

From this directory:

```powershell
py -3.14 -m unittest discover -v
```

If the Python launcher has only one interpreter, this also works:

```powershell
py -m unittest discover -v
```

For direct library imports without installing a package, point Python at `src`:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
```

## Run the local contract service

```powershell
py run_server.py --host 127.0.0.1 --port 8765 --data-root .local_voice_data
```

On first start the service creates `.local_voice_data/.api_capability_token`
with a random local capability. Every route, including health, requires
`Authorization: Bearer <token>`. The desktop host must read that file locally
and keep it out of browser URLs, logs, screenshots, and source control.

Available routes:

- `GET /v1/health`
- `GET /v1/capabilities`
- `GET /v1/voices`
- `POST /v1/synthesis-jobs`
- `GET /v1/jobs/{job_id}`
- `POST /v1/jobs/{job_id}/cancel`

Voice registration and reference inspection are presently Python service calls,
not public HTTP mutation routes. This intentionally keeps identity enrollment
out of the first remotely invocable surface.

## Example Python use

```python
from pathlib import Path
from kira_local_voice import LocalVoiceService, SynthesisRequest
from kira_local_voice.backends import contract_mock_profile

service = LocalVoiceService(Path(".local_voice_data"))
service.register_voice(contract_mock_profile())
job = service.submit(SynthesisRequest(text="Hello.", voice_id="calm-fallback"))
result = service.jobs.wait(job.job_id)
service.close()
```

## Optional Kokoro direct subprocess route

Use a dedicated Python 3.10-3.13 environment; upstream Kokoro/Misaki 0.9.4 do
not declare Python 3.14 support. Resolve and audit `requirements-kokoro.in.txt`
into a lock file inside that isolated environment. Do not patch Windows
Application Control or installed packages. The worker deliberately uses the
demonstrated direct route `KModel + misaki.espeak.EspeakG2P` and never imports
the blocked spaCy `gold_io` path.

The worker binds no socket. It receives one bounded JSON request on stdin,
forces offline and telemetry-disabled flags, reads only a fixed `sealed_bundle`
layout, writes only the assigned unique staging path, and emits one strict,
finite, bounded JSON result. The parent enforces timeout/cancellation and output
growth, checks exact model/voice/license provenance, validates the regular mono
PCM WAV itself, and publishes with a no-replace operation inside the same
cross-process guard used for deactivation. Model caches and weights are excluded
by `.gitignore`.

The runtime allowlist is only `af_heart` (calm female) and `am_fenrir` (warm male).
Both are upstream built-ins with no private Kira reference or identity claim.
The product owner audition-approved their perceived sound on 2026-08-25
America/New_York; this approval does not authorize cloning. See
`THIRD_PARTY_ATTRIBUTION.md` for pinned provenance, measured proof context, and
licenses.

The broader nine-voice design/audition catalog was measured at revision
`f3ff3571791e39611d31c381e3a41a3af07b4987`; that is evidence for design review,
not runtime authorization. This two-voice runtime bundle separately declares
revision `fbba31e67ad83eb66394c926627e99d35abeb087`. The seven additional catalog
voices must fail closed at runtime and are a later audited expansion.

Configure `KokoroConfig` with an absolute isolated interpreter and its explicit
SHA-256, the same staging root used by `LocalVoiceService`, the release runtime
lock, and a fixed `sealed_bundle`. A v2 marker must exactly repeat every release
hash and pin; installed distribution metadata must also exactly match the lock.
Even then capabilities remain unavailable until a reviewed
`IsolationProvider` supplies OS-enforced process-tree, network, and filesystem
containment. Environment variables are never treated as that isolation proof.
