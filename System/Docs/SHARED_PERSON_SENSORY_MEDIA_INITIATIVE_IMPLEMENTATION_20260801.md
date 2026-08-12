# Shared-Person Sensory, Resident Media, and Initiative Foundation

Date: 2026-08-01  
Status: **BOUNDED FOUNDATION IMPLEMENTED; SUPERVISED OWNER ACCEPTANCE PENDING**

## Controlling result

The first bounded shared-person foundation is connected to the existing Kira
Text + Voice / Kira World Shell runtime. It is not a second persona, alarm
utility, or command mode. The exact selected person owns the temporary sensory,
media, and initiative session, and switching or deactivating the person purges
that session.

This result does **not** mean that continuous natural person behavior is
complete. In particular, there is not yet an accepted model-driven private
attention/initiative generator, meaningful visual understanding, or an
accepted full-duplex echo-cancellation path. Those limitations are recorded
below so a tested transport is not mistaken for a synthetic-person acceptance.

The following boundaries remain controlling:

- Video Studio is frozen and was not opened, run, redesigned, moved, or edited.
- `llama3.1:8b` remains the normal text model and Qwen remains an inactive
  candidate. Qwen image/webcam/video understanding remains disabled.
- R18 remains preflight-only. No Blender, Kira mesh, Robert body, TemporaryAI
  body, clothing, activation, assignment, export, publication, or upload work
  occurred in this stage.
- No unsupervised overnight or 24-hour person operation is authorized on the
  current 32 GB system.

## Exact person and sensory boundary

Implemented foundations:

- A short-lived signed browser sensory lease is bound to the exact active
  `person_id` and activation revision.
- A separate memory-only sensory buffer is bound to an exact person,
  activation revision, and cryptographically random nonce.
- Switching or deactivating a person invalidates the old lease and purges the
  old person's temporary cues. A cue cannot cross into the next person.
- Raw frames, raw audio, PCM, pixels, binary data, paths, data URLs, and encoded
  raw payloads are rejected from the derived-cue buffer.
- Factual cues, private-attention placeholders, and explicit public `SPOKEN`
  releases remain separate lanes. No cue automatically becomes speech, action,
  memory, consent, canon, or relationship state.
- Camera and microphone start off. Physical camera-off and microphone-mute
  controls remain immediate.
- The camera path currently produces only bounded non-identifying local cues
  such as brightness and motion. It does not identify Robert, recognize what
  Robert is doing, or prove attention, intent, dishonesty, or motive.
- Local ASR can create a temporary transcript/cue without automatically
  submitting it as Robert's chat turn. Push-to-talk remains available.
- ASR and visual helpers receive narrowly constructed child environments and
  separate per-process secrets rather than a copy of the complete parent
  environment.
- Recorder fragments are discarded while Kira's synthesized voice or local
  media output is active. This is a bounded loop-prevention measure, not an
  accepted acoustic echo-cancellation or speaker-attribution result.

## Shared resident library truth

Everything Robert deliberately placed under `Data/library` is resident library
material. A branch named for Robert or another person is not treated as
owner-private merely because of the branch name. Files outside the library
retain their existing privacy boundaries.

The access layer uses three different outcomes:

1. `GENERAL_LIBRARY_MEDIA`
   - compatible residents may discover and open it independently;
   - indexing, opening, or permission never means it was watched, read, heard,
     enjoyed, remembered, or completed.
2. `MATURE_MAINSTREAM_REQUIRES_ADULT_COVIEW`
   - confirmed adults may use it independently;
   - a non-adult may discover it and sees `adult co-viewing required`;
   - playback for a non-adult requires a fresh exact-item, exact-person,
     exact-activation decision by a confirmed participating adult;
   - Robert is the supported adult participant in the current one-synthetic-
     person interface;
   - refusing is represented by not granting the decision; stopping media,
     changing the item/person, ending the activation, participant departure in
     the lease manager, or expiry revokes the decision;
   - while an item is presented, an exact three-second heartbeat revalidates
     the person, source-file identity, media grant, and adult decision. If any
     check ends, local playback pauses and closes and an in-world screen is
     switched off; no unreported interval is credited as experienced;
   - a decision is memory-only and never becomes a permanent classification or
     universal unlock.
3. `EXPLICIT_ADULT_FOLDER_REQUIRES_CONFIRMED_ADULT`
   - confirmed adults may discover and open it;
   - non-adult and unresolved people cannot discover or directly open it;
   - this retains the owner's separate restriction on explicit adult folders
     and does not collapse them into mainstream R/TV-MA co-viewing.

Media is not classified from filename words. An explicit adult-folder boundary
remains adult-only. For everything outside that separate boundary, the policy
uses existing index rating/category metadata first, then an exact durable
Robert-provided classification. A separately verified local title-metadata
catalog is not present today; when one is added, it must be the next source and
must not fall back to filename words. Broad words such as `adult`, `sex`, or a
character name do not classify a file. This prevents false positives such as
Adult Swim titles or academic documents about adult life stages.

The present media index has no general rating field populated for the current
catalog, and the curated mainstream-mature exact lists are presently empty.
Consequently, mainstream co-viewing enforcement is connected and tested but
only becomes active for an item after reliable rating/category metadata or an
exact durable Robert classification exists. Robert can now supply that exact
classification through the normal chat or the simple owner correction action
described below. The code does not guess from a title to make the feature
appear more complete than it is.

## Natural-language exact-item rating correction

Implemented and connected:

- The shared-library owner controls expose one `Correct rating/classification`
  action. It fixes the correction target to the exact selected or open item,
  then accepts Robert's correction in the normal chat input. Robert does not
  edit JSON or move the file.
- A clear correction typed directly in ordinary chat uses the exact selected
  or open library item. Ordinary discussion such as liking an R-rated movie is
  conservatively left as conversation and does not mutate policy. Negated
  instructions such as `do not change the rating` and rejected categories do
  not invert into an accidental durable correction.
- If a different item is open while another search result is selected, natural
  chat refuses to guess which `this` means. The owner action fixes one target;
  it changes to a visible cancel action while clarification is pending, and
  normal owner-surface open is disabled until Robert resolves or cancels it.
- Switching people clears prior search results, correction target, and co-view
  state so an adult-visible title cannot remain displayed for a non-adult.
- A determinate correction records the opaque media ID, current file SHA-256,
  canonical project-relative `Data/library` path, title/version when present,
  previous rating/category/source, Robert's exact text, UTC timestamp, and the
  resulting rating/category.
- Records append to
  `Data/owner_corrections/media_classification_corrections.jsonl`. Older
  records are never rewritten or removed. The latest record for the same exact
  media ID and exact file hash is current authority over automatic metadata,
  folder policy, and title-word guesses. No correction is propagated to a
  similarly named title or another file version.
- On startup, only a record whose path and current source-file hash still
  match is reapplied. While the shell remains running, search, co-view, and
  open revalidate cached source identity; any identity change forces a new
  full hash, and grant creation independently returns its full current hash.
  A mismatch removes only the live override, revokes that exact item's media
  and co-view capabilities, and preserves the append-only history. A moved,
  missing, or replaced file therefore never inherits the old correction.
  Correction, search, co-view, and open use one atomic service boundary so an
  old authorization cannot race past a correction. A malformed or redirected
  ledger fails search/open/correction closed rather than silently bypassing
  owner history.
- Search and direct-open authorization use the same in-memory effective
  classification. Home World screens open through that same grant path. An
  exact item already open when its classification changes is revoked and must
  be reopened under the new decision; the media heartbeat also prevents a
  buffered or resumed presentation from surviving the change.
- Reclassifying explicit material as mainstream mature permits non-adult
  discovery but does not grant playback. A fresh adult co-view decision is
  still required for that exact person, item, activation, and session.
- Unknown, unclear, conflicting, or `ask me before opening` wording asks for a
  clarification and writes no ledger record.
- Correction changes metadata/access only. It creates no watched, read,
  listened, liked, disliked, attention, enjoyment, or memory claim.

Recent-item lists, playlists, and saved-session entry points are not currently
implemented. When they are added, they must resolve the opaque item through
this same effective policy at use time; they must not cache an earlier access
decision or create their own classification copy.

## Grounded media presentation

Implemented foundations:

- Search returns opaque media IDs rather than filesystem paths.
- Open authorization repeats the exact access check; a direct indexed-path
  request goes through the same policy and is not a bypass.
- A short-lived grant is bound to the exact person activation, exact indexed
  file, file identity, and hash. Person switch, media switch, stop, expiry, or
  file change invalidates it.
- A bounded heartbeat covers already-buffered media and page display, so a
  browser cannot continue merely because it no longer needs another range
  request. The heartbeat creates no presentation, attention, or memory record.
- Local streaming supports bounded single HTTP ranges, `HEAD`, exact MIME,
  exact CORS origins, a per-response byte cap, and revocation checks between
  streamed chunks.
- Timed playback events require monotonically exact integer sequence numbers.
  Seek accounting records only the interval actually presented and never
  counts skipped time as watched/listened time.
- Page media records bounded visible time without pretending a whole document
  was read.
- The shell can present local image, video, audio, and PDF media without
  autoplay. Media audio ducks Kira's voice output and restores the owner's
  previous volume rather than forcing a new volume.
- Local library image/video/audio can be prepared for an exact Home World TV,
  monitor, tablet, or phone. The trusted Home World parent supplies the grant,
  but a direct owner click in the world is still required to start it.
- Home World presentation events are accepted only from the exact trusted
  parent/window/origin binding. Replacement, screen off, person switch, end,
  and unload finalize bounded truth before teardown.

No permission, index result, open, playback event, or co-view decision creates
a claim of attention, enjoyment, preference, memory, relationship change, or
complete viewing/reading/listening. Those require a later separate grounded
person decision.

## Person initiative and natural turn-taking foundation

Implemented foundations:

- A bounded memory-only opportunity evaluator can consider factual cue
  references, current activity, unfinished threads, an explicit emotion
  signal, boredom, urgency, recent bids/turns, and advisory Robert-busy
  evidence.
- Per-person pacing profiles are bound to the exact activation. Camera-derived
  busy evidence is never a command and cannot prove Robert's attention, motive,
  lying, or intentional ignoring.
- Anger, annoyance, hurt, or disappointment may be supplied as an explicit
  private emotion signal, but the foundation does not manufacture accusations
  from camera motion and does not automatically speak, act, write memory, or
  alter a relationship.
- Turn state distinguishes Robert interrupting a person, a person seeking the
  floor, and a person holding the floor.
- Previously approved private decisions can publish public speech, action
  intent, leave intent, or an ignore disposition through an exact-person
  queue. Private thought, hidden reasoning, activation nonces, and raw sensory
  material are rejected from the public event.
- The shared UI polls this public queue. Approved person-initiated speech can
  display and enter the approved voice queue without Robert pressing Send.
  Action and leave events remain visible intents; this foundation does not
  execute world actions on its own.

Not implemented or accepted:

- no autonomous private model/decision generator is connected;
- no claim that each person's default pacing profile is a finished personality;
- no accepted overlap speech, barge-in, full-duplex AEC, or reliable speaker
  attribution;
- no automatic inference that camera motion means Robert is busy with another
  activity or deliberately ignoring someone;
- no autonomous world action executor;
- no automatic emotion, relationship, consent, or memory mutation.

Hard-coded angry replies or generic chatbot scripts were deliberately not
added. Natural person behavior requires a separately reviewed private
generation/decision connection and real supervised evidence.

### 2026-08-02 default-off decision-bridge addendum

A bounded adapter contract now exists in
`Core/supervised_person_decision.py`. It accepts one exact existing
`DecisionOpportunity`, exact active-person lease, exact per-person profile,
and exact ephemeral context; makes at most one supplied adapter call; validates
one strict speak/action/continue/ignore/leave selection; and exposes only a
compatible chosen public speech/action/leave event through the existing
`PersonInitiatedEventQueue`. Continue and ignore remain quiet choices.

The bridge is now imported by the shell behind three exact default-off gates
and has a caller-supplied one-shot fake/later-adapter hook. It still has no live
model adapter, timer, or recurring scheduler. Normal activation does not enable
it. Its fake tests and inert ten-case live-acceptance plan do not change the
status above: autonomous/continuous person behavior and owner acceptance remain
pending. Exact contracts, completed shell wiring, remaining limitations, and
rollback are recorded in
`System/Docs/SUPERVISED_CONTINUOUS_PERSON_PRIVATE_DECISION_LAYER_20260802.md`.

## Known connection gaps

- Meaningful visual understanding is unavailable. Webcam-to-Home-World-screen
  perception is not connected; only approved local library media uses the
  embodied-screen bridge.
- PDFs remain shell-local because the current Home World has no reviewed PDF
  renderer.
- Recent items, playlists, and saved-session entry points do not yet exist in
  this owner surface. Their required correction/policy behavior is documented
  above, but cannot be called connected or tested until those entry points
  exist.
- The system can record presentation intervals, but it does not yet decide that
  a resident attended, enjoyed, disliked, or voluntarily remembered them.
- Physical adult presence/departure is not inferred from the camera. In the
  current interface Robert explicitly agrees and explicitly stops media; the
  lease manager also revokes on participant-departure events when a future
  trusted presence controller supplies one.
- Supervised real-device/person acceptance remains pending. Component tests did
  not turn on a camera or microphone, play media, call a model, or run an owner
  conversation.

## Verification completed

On 2026-08-01, isolated verification completed without launching a browser,
model, camera, microphone, media player, Video Studio, or Blender:

- 14 Python source files compiled in an isolated temporary bytecode directory;
- both JavaScript files passed `node --check`;
- 187 focused tests passed, covering exact person leases, sensory expiry and
  raw-payload rejection, restricted helpers, media access, direct-path parity,
  exact natural-language owner corrections, append-only history, file-hash
  version binding during startup and the live process, negation safety,
  correction/open atomicity, exact co-view purge, person-switch UI clearing,
  immediate runtime revocation, grants, file-integrity checks, byte ranges,
  exact playback truth, mature co-view leases, Home World screen trust,
  initiative decisions, public event transport, identity switching, and
  existing grounding behavior.

These are engineering tests, not owner real-use acceptance.

## Required supervised acceptance before normal enablement

Use one active person first, then repeat identity-isolation checks with other
people. Do not run unattended.

- prove camera/microphone off, on, immediate off, person switch, cue expiry,
  and raw-media non-persistence;
- measure local ASR segmentation, dropped speech, self-voice/media suppression,
  latency, RAM, VRAM, and clean shutdown;
- prove an approved person-initiated greeting/follow-up can occur without Send,
  while silence, refusal, ignore, and leave remain valid choices;
- test Robert interruption and person interruption without false duplicate
  speech;
- test a busy-camera cue as uncertain evidence and confirm it does not produce
  a motive/lying/attention claim;
- open general library image/video/audio/PDF items, pause/resume/seek/stop, and
  confirm exact intervals rather than whole-title claims;
- test a reliably classified mainstream-mature item with Robert agree, refuse,
  stop, timeout, media switch, and person switch;
- use the owner action and ordinary chat to correct one exact item through
  general, mature-mainstream, and explicit categories; confirm older records
  remain, a similarly named item does not change, and an already-open item is
  revoked;
- correct an explicit item to mature-mainstream as a non-adult and confirm it
  becomes discoverable but still requires a fresh co-view decision;
- confirm explicit adult folders remain invisible and inaccessible to a
  non-adult/unresolved person and remain available to a confirmed adult;
- confirm the same person/media truth when using a Home World embodied screen;
- verify no test writes memory, changes a relationship, publishes, uploads, or
  activates Qwen vision.

## Rollback boundary

Disable active camera, microphone, media, and person-initiative sessions first.
Restore only files named in the append-only post-implementation checkpoint,
and only after verifying that their current hashes have not acquired a later
unrelated change. Newly added foundation modules may then be removed as a
file-scoped rollback. Never restore an entire tree and never delete library
media, person memories, approved voices, model installations, avatar review
packages, or Video Studio evidence.
