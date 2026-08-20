# Voice packs, consent, and fail-closed fallback

The target is for Kira and Synthetic Robert to have distinct, persistent voice
configurations that travel with their authorized variant packages. A voice is
part of presentation and identity continuity, but a convincing voice must not
be obtained or redistributed by bypassing the speaker's rights.

## Current handoff status

- Synthetic Robert uses Robert's self-voice under a named-recipient private
  review grant recorded on 2026-08-19.
- Kira uses the current exact reference WAV under the owner's direct
  attestation that the speaker's permission covers synthetic voice use,
  private disclosure of this exact recording to the named Hanson review team,
  and private Little Sophia integration research. The original written form
  has not yet been attached, and this package does not claim independent legal
  verification.
- Kira's WAV is the owner-selected current reference. Its historical source
  manifest did not record a completed human speaker-purity review, so the
  package does not claim the recording contains only the intended woman.
  Listening and contamination review remain required before promotion.
- No trained voice model, embedding, raw source session, or private transcript
  is included. A reviewer installs a compatible local backend.
- Neither profile permits a silent generic voice fallback. If its selected
  neural backend cannot run, the portable runtime continues text-only and
  reports the unavailable voice route.
- Neither pack permits public release, identity authentication, or onward
  redistribution. Both are restricted to the named private review group.

## Required manifest for a custom voice pack

A distributable voice pack should include a machine-readable and human-readable
manifest containing:

- variant identifier and public display name;
- speaker/performer identity or an approved pseudonymous rights-holder record;
- affirmative consent covering voice synthesis or transformation;
- allowed recipients, uses, territories, and redistribution scope;
- whether robot, public demonstration, research, commercial, and derivative
  use are allowed;
- consent date, expiration/review date, and revocation process;
- source-recording provenance and hashes;
- synthesis engine/model name, exact version/digest, and its license;
- generated model/embedding hashes;
- disclosure text required when the voice is used;
- security and deletion requirements; and
- approver and approval date.

If any required permission is absent or ambiguous, the pack stays local and is
not committed or sent. For this private handoff the owner attestation is the
recorded authorization basis; the pending form attachment is not hidden.

## Packaging boundary

Keep these outside Git even when licensed unless the manifest explicitly
authorizes Git-based distribution. The two exact, hash-bound reference WAVs in
this access-controlled handoff are the only current exceptions:

- raw recording sessions and transcripts with personal information;
- access tokens, API keys, service credentials, or speaker account IDs;
- biometric embeddings and intermediate training checkpoints;
- generated audio containing private conversations; and
- third-party music, movie, television, or game audio used as a reference.

The repository can contain an adapter, configuration template, checksums, and a
license/consent manifest. The actual pack should use an access-controlled,
encrypted delivery channel appropriate to its license.

## Runtime behavior: current and required

- Bind a voice configuration to exactly one variant ID unless the license
  explicitly allows sharing.
- Record the voice-engine and pack hash with spoken-output evidence.
- Never fall back silently. If the selected custom voice is unavailable,
  report it and continue text-only unless the reviewer explicitly chooses and
  labels a different profile.
- Do not alter the spoken text in the voice layer except for documented
  pronunciation/markup normalization.
- **Current:** playback is synchronous. `--no-voice` prevents playback before
  launch, but there is no tested in-session `/mute` or `/stop` that interrupts
  an utterance already playing. Interruptible playback and embodiment-session
  stop integration are release requirements, not current claims.
- **Current:** generated WAV deletion is attempted after playback and the voice
  event records retention/path. A failed deletion or playback-disabled run can
  retain a generated WAV under ignored `local_data`; operators must inspect and
  apply the pack's retention policy.
- Prevent one variant from selecting another variant's restricted voice pack.

## Review tests

Before a custom pack is promoted, test authorization-manifest validation,
identity binding, pack-hash verification, missing-pack text-only fallback,
offline behavior, retention/deletion, and log redaction. Mute/interruption is a
known missing test/capability and must not be marked passed. Perform content and
impersonation review with the same exact pack that will be distributed.
