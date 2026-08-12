# Sarah durable device authentication implementation specification — 2026-08-09

Status: **DESIGN ONLY — NOT IMPLEMENTED, NOT DEPLOYED, NOT OWNER-ACCEPTED**

This is an append-only implementation specification for the later full Sarah
Android and Windows release. It does not change, extend, relabel, publish, or
retire the separate 72-hour event candidate. No workflow was dispatched and no
credential value is recorded here.

## Objective and non-negotiable boundary

Sarah must remain able to renew online model, current-source, and protected
voice access beyond 72 hours without placing an indefinitely reusable bearer in
an APK, EXE, source file, artifact, manifest, log, or handoff.

The current event design must not be made "full" by removing
`SARAH_EVENT_AUTH_EXPIRES_UTC`. The existing Worker accepts one global
`SARAH_BACKEND_TOKEN`, and absence of the event expiry makes that bearer
unbounded. An extractable global bearer with no expiry is expressly rejected.

The full release instead uses:

- one stable HTTPS Worker origin containing no client secret;
- one P-256 signing key generated independently by each installation;
- owner-approved, ten-minute, single-use device enrollment;
- one-use server challenges signed by the device key;
- ten-minute access JWTs held only in memory;
- a rolling 90-day device inactivity lease renewed by fresh key proof;
- immediate per-device revocation and an `auth_epoch` check on every protected
  route; and
- Cloudflare D1 as the sole security-state database.

There is no long-lived refresh bearer. The long-lived credential is a private
signing key that is created on the device, never compiled or transmitted, and
can be independently rotated or revoked.

## Audited starting point

The design was derived from read-only inspection of
`RecoverySprint/continuation_20260807/sarah_pr21_audit/android-app`:

- Android `SecureStore` encrypts a backend URL and static bearer with
  Android Keystore AES-GCM. The normal lane compiles an empty bearer; only the
  `.eventcandidate` application can fall back to its bounded bundled bearer.
- Windows `runtime-config.json` protects configured secret fields with
  current-user DPAPI, with resolution order environment, per-user config, then
  bundled event defaults.
- Existing X25519/SAS pairing requires two explicit matching-code approvals and
  produces a separate encrypted LAN-sync credential. It is suitable for local
  continuity but must never be reused as cloud authentication.
- The current Worker has one global bearer, optional event expiry, no device
  registry, and route-rate-limit keys shared by all clients.

## Full-version protocol

### Client key contract

- Algorithm: ECDSA P-256 with SHA-256.
- Public wire form: JWK containing only `kty`, `crv`, `x`, and `y`.
- Thumbprint: RFC 7638 SHA-256 JWK thumbprint.
- Signature wire form: 64-byte IEEE-P1363 `r || s`, base64url without padding.
- Android private key: non-exportable `AndroidKeyStore` EC key, versioned alias,
  no per-use biometric requirement so background renewal remains possible.
- Windows private key: PKCS#8 encrypted through the existing current-user DPAPI
  boundary in a new `device-auth-v1` vault. Non-exportable Windows CNG is a
  compatible later hardening step, not a prerequisite for the first full gate.
- Access JWT: memory only; never written to preferences, SQLite, runtime config,
  backups, logs, or crash reports.

### Device-first enrollment

1. The client generates its P-256 key before network enrollment.
2. `POST /v1/enrollments` submits public key and bounded device/build metadata.
3. The Worker stores only hashed codes and returns a 256-bit `device_code`, an
   eight-character human `user_code`, a server challenge, verification URL,
   ten-minute expiry, and poll interval.
4. The owner opens the verification URL on a separate Cloudflare
   Access-protected owner host, reviews exact platform/name/version/fingerprint,
   and explicitly approves or denies.
5. `POST /v1/enrollments/{id}/complete` presents the device code plus a key
   signature bound to enrollment ID, server challenge, API origin, and key
   thumbprint.
6. Valid approval and proof create one device row and return only a random
   `device_id`; no renewable bearer is returned.

Enrollment states are `pending_owner`, `approved`, `consumed`, `denied`, and
`expired`. Approval and consumption use conditional D1 updates and are
single-use.

### Renewable sessions

1. `POST /v1/auth/challenges` creates a random two-minute challenge for an
   active `device_id`.
2. The client signs the following exact UTF-8 payload:

```text
SARAH-AUTH-V1
device_id
challenge_id
nonce
api_origin
key_version
```

3. `POST /v1/auth/token` verifies the key, atomically consumes the challenge,
   renews the rolling lease, and issues a ten-minute HS256 access JWT.
4. Protected middleware verifies JWT signature/`kid`, issuer, audience, time,
   JTI, and then reads current D1 device status, lease, key version, and
   `auth_epoch` before any provider call.

JWTs contain random owner/device IDs, scopes, key version, auth epoch, and
times—never email, profile data, prompts, replies, or credential material.

### Endpoint and status contract

| Endpoint | Authentication | Required result |
|---|---|---|
| `GET /health` | public | minimal service and contract health only |
| `POST /v1/enrollments` | public, IP-rate-limited | create bounded pending enrollment |
| `POST /v1/enrollments/{id}/complete` | device code + key proof | pending, deny/expire, or consume once |
| `POST /v1/auth/challenges` | device ID, rate-limited | one-use two-minute challenge |
| `POST /v1/auth/token` | P-256 proof | ten-minute memory-only access JWT |
| `GET /v1/capabilities` | access JWT | exact service/device/provider/model truth |
| `POST /v1/chat` | access JWT | protected conversation |
| `POST /v1/search` | access JWT | protected current-source search |
| `POST /v1/voice` | access JWT | protected voice |
| `GET /v1/devices/me` | access JWT | current lease/key/state |
| `POST /v1/devices/me/key-rotations` | JWT + old/new proofs | idempotent key rotation |
| `POST /v1/devices/me/revoke` | JWT + fresh key proof | self-revoke |
| `GET /owner/devices` | validated Access JWT | owner device inventory |
| `POST /owner/enrollments/{id}/approve` | Access JWT + CSRF | approve exact request |
| `POST /owner/enrollments/{id}/deny` | Access JWT + CSRF | deny exact request |
| `POST /owner/devices/{id}/revoke` | Access JWT + CSRF | immediate device revoke |

Error truth is fixed: `401` invalid/expired token or proof; `403` revoked,
lease-expired, or stale epoch; `409` replay/stale rotation/already consumed;
`410` expired challenge or enrollment; `429` bounded retry; `503` unavailable
auth store/configuration. D1/auth failure must occur before Workers AI,
Tavily, ElevenLabs, OpenAI, or another provider is called.

`/v1/capabilities` is authenticated and reports stable service ID, compatible
contract major, device state, lease expiry, actual server-selected
provider/model, current-source readiness, voice readiness, rate-limit readiness,
and server time. Full clients bind their five-minute capability cache to service
ID, contract major, device ID, key version, and auth epoch—not an event token
fingerprint or exact per-run Worker hash.

## Cloudflare state and secrets

Use a single D1 binding with tables equivalent to:

- `owners(owner_id, access_subject_hash, status, created_at)`;
- `enrollments(enrollment_id, device_code_hash, user_code_hash,
  challenge_hash, public_jwk, key_thumbprint, platform, app_id, app_version,
  state, owner_id, created_at, expires_at, approved_at, consumed_at)`;
- `devices(device_id, owner_id, public_jwk, key_thumbprint, platform,
  display_name, app_id, key_version, auth_epoch, status, lease_expires_at,
  created_at, last_seen_at, revoked_at, revoke_reason, last_rotation_id)`;
- `auth_challenges(challenge_id, device_id, purpose, nonce_hash, created_at,
  expires_at, consumed_at)`; and
- `audit_events(event_id, owner_id, device_id, event_type, created_at,
  bounded_metadata_json)`.

Apply unique constraints to code hashes, challenge nonces, rotation IDs, and
active key thumbprints. Security reads use D1 primary/sequential consistency.
A scheduled cleanup removes expired requests/challenges and aged bounded audit
metadata. Audit rows never contain tokens, codes, signatures, content, or keys.

Workers KV is forbidden for enrollment, challenge replay, lease, rotation, or
revocation truth because it is eventually consistent and lacks the necessary
atomic security transition. A SQLite-backed Durable Object is optional only if
a later per-request DPoP replay ledger becomes necessary; it is not part of the
minimum design.

Server-only Worker secrets include current/previous access-JWT signing keys and
provider/search/voice credentials. Their values never enter D1 or a client.
Cloudflare Access issuer and application audience are configuration identifiers,
and the Worker must cryptographically validate every
`Cf-Access-Jwt-Assertion`, not merely trust that a header exists.

Rate-limit keys become `device_id + route` after authentication and a
non-reversible network-source bucket before enrollment. The current one-global-
key-per-route pattern must not be carried into the full Worker.

## Key and server rotation

Device rotation keeps the old key until the new path is proven:

1. Generate the new local key.
2. Obtain a server rotation nonce.
3. Old and new keys sign the same payload containing device ID, idempotent
   rotation ID, nonce, current version, and both thumbprints.
4. One conditional D1 update installs the new public key and increments
   `key_version` and `auth_epoch`.
5. Old access JWTs fail immediately.
6. Obtain one session with the new key, then delete the old local key.
7. A lost response is recovered by replaying the same rotation ID or testing
   the new key; it must not create a third identity.

Default automatic key-rotation target is 180 days, plus manual rotation after
suspected exposure or secure-storage migration.

JWT signing-key rotation uses `current` and `previous` keys selected by `kid`.
Retain the prior verification key only beyond the ten-minute maximum access
token lifetime. Provider-secret rotation is independent of device enrollment.

## Offline and recovery behavior

- Offline Sarah retains the local mind, database, trips, memories, and local
  phone/Windows voice fallback.
- Access-token expiry while offline is normal. On validated connectivity Sarah
  requests a new challenge/session automatically with bounded exponential
  backoff and jitter.
- Do not durably queue sensitive chat/search/voice requests for automatic replay
  days later. Background work waits; foreground requests use truthful local
  fallback or ask for retry.
- Missing Android Keystore or unreadable Windows DPAPI material becomes
  `KEY_MISSING`; never generate a replacement under the old `device_id`.
- Preserve local data, perform fresh owner-approved enrollment, then revoke the
  old device from the owner portal.
- Configure an owner-controlled backup Cloudflare Access identity. No reusable
  recovery secret is embedded in either app.
- Existing X25519/SAS pairing may transfer only an owner-reviewed local
  continuity preview. It must exclude cloud auth keys/state, backend tokens,
  provider credentials, Gmail tokens, and pairing credential namespaces.
- Current pairing does not bind a cloud P-256 thumbprint or enrollment ID, so it
  must not approve cloud enrollment in the minimum implementation.

## Phased implementation order and gates

### Phase 0 — freeze boundaries and fixtures

- Preserve the 72-hour event build, labels, workflows, Worker, and app ID.
- Add protocol schema, canonical P-256 vectors, D1 migration, and threat-model
  fixtures on a separate full-version branch.
- Define a stable full API origin and owner-portal origin.

Gate: no Sarah artifact/source credential regression; event tests unchanged;
cross-language vector design independently reviewed.

Rollback: remove only new full-version fixtures/configuration. No event or local
owner data changes exist in this phase.

### Phase 1 — Worker auth foundation

- Add D1 schema, Access owner middleware, enrollment, challenge/token,
  per-device middleware, owner device inventory/revocation, rotation, cleanup,
  and per-device rate limits.
- Version protected routes under `/v1` and require a server-selected provider
  and model.
- Keep staging provider quota bounded until auth gates pass.

Gate: Worker unit/integration/concurrency tests; forged Access assertion,
replay, double consume, stale epoch, revoke, missing D1, and absent signing key
all fail closed before provider calls.

Rollback: undeploy the separate full staging Worker and remove its isolated D1
binding. Do not point any existing artifact at it.

### Phase 2 — Android full client

- Implement Keystore P-256 credential manager, enrollment UI/deep link,
  in-memory session manager, automatic renewal, capability identity update,
  key rotation, revoke/recovery UI, and event-token exclusion.
- Canonical full package remains `com.kiraworld.sarahtravel` with established R1
  signing continuity; `.eventcandidate` remains side-by-side.

Gate: Android source/unit tests, Java/Worker signature interoperability,
Keystore non-exportability, APK/DEX credential scan, upgrade/data-preservation
test, and physical Galaxy A17 enrollment/reboot/renew/revoke/offline recovery.

Rollback: install the prior canonical signed build or disable the separate full
endpoint. Never copy an event bearer into the canonical app.

### Phase 3 — Windows full client

- Add a distinct DPAPI `device-auth-v1` vault and in-memory session manager.
- Full resolution ignores legacy `SARAH_MODEL_BACKEND_TOKEN` for authentication;
  only non-secret route/provider/model settings may migrate.
- Preserve local data independently from cloud credential state.

Gate: Windows unit/package tests, P-256 Worker interoperability, DPAPI
cross-account rejection, EXE/bundled-JSON credential scan, reboot/renew/revoke,
8 GB/no-GPU physical use, and vault-damage recovery without local data loss.

Rollback: restore the prior executable and data snapshot. The new credential
vault is isolated and may be ignored; legacy bearer fallback remains forbidden
in the full executable.

### Phase 4 — owner-reviewed continuity migration

- Add explicit Android-event/full and Android/Windows continuity previews using
  the existing X25519/SAS trust boundary.
- Maintain an allowlist of transferable profile/trip/memory/message data and an
  explicit denylist of every auth/Gmail/provider/pairing-secret namespace.

Gate: tamper/replay/deny/timeout tests; preview-before-import; no credential
field in transfer; duplicate-safe merge; append-only import receipt.

Rollback: decline or discard the preview. Source data and existing destination
records remain unchanged.

### Phase 5 — staging soak and physical owner acceptance

- Enroll one Android and one Windows installation independently.
- Use accelerated token/lease tests plus a real run beyond 72 hours.
- Revoke each device separately, rotate each key, test key loss/re-enrollment,
  and prove exact model/search/voice capability receipts.

Gate: 73-hour renewal, per-device quota/revocation, offline/online recovery,
actual provider/model, protected current-source, protected voice, and owner
hearing/UI acceptance all pass. No claim is allowed from source tests alone.

Rollback: revoke staging devices and disable the full staging Worker. The event
candidate continues only until its own recorded expiry.

### Phase 6 — full release and later event retirement

- Build and sign clearly named full APK/Windows artifacts with no bundled auth
  secret and publish adjacent hashes/manifests.
- Owner enrolls every accepted installation through the one-time portal.
- Retire the exact event Worker only after the owner confirms the full devices
  and any desired local continuity migration.

Gate: independent artifact scan, signer/hash verification, physical install,
capability truth, device inventory, revoke/recovery rehearsal, and explicit
owner acceptance.

Rollback: revoke full devices/route and return to the last accepted locally
functional build. Never extend the event bearer or convert it into a full
credential.

## Required test matrix

The implementation is not complete until all of these pass:

- no backend/provider bearer in full BuildConfig, APK/DEX, EXE, bundled JSON,
  manifests, logs, or crash fixtures;
- Android, Windows, and Worker P-256 deterministic interoperability;
- enrollment approve, deny, expire, poll throttling, CSRF, single consume, and
  concurrent consume;
- Access JWT missing/forged/wrong issuer/wrong audience rejection;
- challenge tamper, wrong key/device, replay, expiry, and concurrent use;
- access JWT wrong signature/issuer/audience/time/key version/auth epoch;
- immediate per-device revoke and independent per-device rate limits;
- D1/signing-key outage fails closed before provider calls;
- idempotent key rotation, lost-response recovery, old-key rejection, and
  server signing-key overlap/removal;
- Android Keystore loss and Windows DPAPI loss/cross-account failure;
- offline expiry, bounded reconnect, no delayed sensitive replay;
- pairing migration denylist and owner-reviewed merge; and
- physical Galaxy A17 plus 8 GB Windows install, reboot, 73-hour soak,
  conversation, exact server-selected model, search, voice, revoke, rotation,
  and recovery.

## Required owner setup

1. Select stable full API and owner-portal hostnames.
2. Create/bind D1 and apply the reviewed schema.
3. Put only the owner portal behind Cloudflare Access; allow primary and backup
   owner identities.
4. Configure the Worker to validate Access issuer/audience and set server-only
   current JWT-signing and provider/search/voice credentials.
5. Configure authenticated per-device and unauthenticated enrollment rate
   limits.
6. Deploy staging, then verify health, owner portal, D1 failure behavior, and
   authenticated capabilities.
7. Build/sign the canonical Android full lane with signing continuity and the
   separately named Windows full installer, both with empty bundled credential
   fields.
8. Approve each physical device through its one-time enrollment code and test
   inventory/revoke/recovery before accepting release.
9. Retire the event Worker only after the full migration and explicit owner
   acceptance.

## Current truth

This document is the implementation target only. As of 2026-08-09, none of the
D1 schema, owner portal, device keys, enrollment routes, renewable sessions,
per-device revocation, full client changes, staged deployment, 73-hour soak, or
physical owner acceptance described above has been implemented or claimed.

