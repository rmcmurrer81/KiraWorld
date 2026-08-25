# Kira Labs Local Voice Studio — Core Contract

The Avatar/Temporary Creator read-only voice-gap planner is documented in
`AVATAR_TEMPORARY_CREATOR_VOICE_INTEGRATION.md`. It preserves established
voices and Kira's current route while producing source-attested, nonbinding
audition briefs for exact profiles that still lack a voice.

The approved-only product route resolver is documented in
`../../System/Docs/APPROVED_STARTER_VOICE_RELEASE_AND_ASSIGNMENT_20260825.md`.
It exposes only the owner-approved calm female and warm male generic starter
voices to exact hackathon-app or nonbinding creator-preview selectors. Its
release inventory excludes unapproved auditions, reference audio, resident
audio, weights, and caches; Kira, Lisa, and H. H. Holmes remain unassigned.

This is an additive, privacy-first foundation for a local voice studio. Its
default backend remains a clearly marked silent-WAV contract mock. An optional
Kokoro subprocess adapter is now present but remains fail-closed. Exact runtime,
worker, dependency-lock, model, configuration, voice-pack, and audition-bridge
identities are required, and a reviewed OS isolation provider is also required.
A pinned Microsoft MXC ProcessContainer provider candidate is implemented, but
no isolation provider is release reviewed in this build. Its positive launch
canary does not yet prove denied network access, denied writes outside staging,
or descendant cleanup, and hash-to-launch TOCTOU is not closed. On the inspected
Windows 25H2 host the capability probe succeeded but even the launch canary
returned `E_NOTIMPL`. The real adapter therefore reports `ready: false` under
every configuration. This change does not download or execute a model and makes
no general production-quality claim.

The privacy-minimized machine-readable observation is preserved in
`evidence/windows_mxc_attestation_20260825.json`. It records no user path and
explicitly confirms that no synthesis, model/GPU execution, network use, or
host-security change occurred during the readiness check.

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
`f3ff3571791e39611d31c381e3a41a3af07b4987`. The exact configuration, model,
`af_heart`, and `am_fenrir` hashes in that report match this two-voice bundle.
The product-owner approval record and those exact public-generic assets are now
sealed together in `evidence/kokoro_starter_runtime_bridge_v1.json`. The bridge
grants only those two voice IDs at that exact revision; the previous `fbba...`
runtime label had no evidence binding and is superseded. The other seven catalog
voices still fail closed and require a separate audited expansion.

Configure `KokoroConfig` with an absolute isolated interpreter and its explicit
SHA-256, its explicit base-Python runtime root, the same staging root used by
`LocalVoiceService`, the release runtime lock, runtime bridge, and a fixed
`sealed_bundle`. A v3 marker must exactly
repeat every release hash and pin. The lock binds the reviewed venv launcher, a
no-exclusions digest over all 36,060 files in its 3.23 GiB venv tree, and a
second no-exclusions digest over all 6,265 files in the 148.1 MiB base-Python
tree that supplies its standard library and DLLs. Any added module, `.pth`,
bytecode, DLL, or changed package changes one of those digests. The worker is
launched with `-I -S`, verifies `sys.base_prefix` and every initial `sys.path`
entry against the attested base tree, then adds only the attested venv
`site-packages` directory. This prevents automatic `sitecustomize`,
`usercustomize`, and `.pth` execution. These checks still occur before
path-based launch, so they do not close TOCTOU and do not enable the adapter.

The experimental `MxcIsolationProvider` accepts only a release-pinned
`wxc-exec.exe` hash, prohibits DACL fallback, requests deny-by-default networking
with no capabilities, disables UI, and reruns its launch canary before work.
However, the release-reviewed provider set is intentionally empty until hostile
network/filesystem/descendant canaries and a launch-time identity seal exist.
Environment variables, policy shape, and `--probe` are never isolation proof.

Kokoro is only a bounded generic audition/bootstrap lane. It does not replace
Kira's accepted Chatterbox routing and is not the original-voice forge. The
long-term designed-original route remains the separately governed Qwen3-TTS
VoiceDesign + Base architecture described by KiraWorld's current authority.
