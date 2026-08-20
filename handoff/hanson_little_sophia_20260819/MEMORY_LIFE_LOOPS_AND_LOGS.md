# Memory, life loops, people, and inspectable logs

Kira and Synthetic Robert are packaged as persistent, identity-isolated
software variants. Their continuity survives process restarts, but this first
portable runtime is not the entire accepted static Mind V21 specification and
does not update the base language-model weights.

## What is implemented now

Each profile has a separate local directory with append-only JSONL channels
for:

- assistant-spoken output;
- deterministic non-COT functional appraisal notes;
- model factual claims with source, uncertainty, and an explicit
  `model_claim_not_verified_truth` status;
- functional appraisal state;
- life-loop start/close events and deterministic consolidation references;
- explicitly reviewed identity-bound imports;
- voice-route evidence;
- high-level embodiment intentions; and
- explicit self-introduced people labels.
- a persistent per-installation branch identity; and
- explicitly confirmed reviewed local notes with narrow same-profile
  supersession pointers.

The complete raw user utterance is not persisted. Assistant speech may repeat
some input and is persisted, so reviewers should still avoid entering
unrelated secrets. An explicit typed/transcribed introduction using “My name
is David Hanson” stores the introduced name label, source, and boundary—not the
rest of the utterance. The label survives restart but remains unverified: it is
not face or voice recognition, identity authentication, or proof that two
speakers using the same name are the same person. Correction/deletion tooling
for acquaintance labels remains a roadmap item.

An explicit `/remember NOTE` action is different from ordinary conversation:
it retains the exact confirmed note text, an operator-supplied unverified
reviewer label, and optional pointers to existing same-profile fact events.
Those pointers keep the older record auditable; they do not delete it or prove
that the new note is true. `/remember` performs no credential, PII, or private-
data scan. Do not put secrets or unrelated third-party data in a reviewed note;
confirmation is an explicit retention/reviewer assertion, not automated
privacy or truth validation.

The current prompt may record a concise stable preference, project decision,
relationship fact, or biographical detail as a conversation-sourced factual
claim. It is not automatically treated as truth. Topic-ranked retrieval can
bring older assistant speech, older conversation claims, and reviewed memories
back into later context. That allows later discussion of something David or
another reviewer said even after many newer turns, when the earlier exchange
produced a relevant retained assistant statement or claim.

## What a life loop does

1. Starts an identity-specific durable session.
2. Handles each user message ephemerally, except for the narrow introduced-name
   label and explicitly confirmed reviewed-note actions described above.
3. Appends the assistant's spoken output, factual claims, safe functional
   appraisal, state change, model identity, and any non-executing embodiment
   intentions.
4. Makes bounded recent and topic-relevant continuity available to later
   turns.
5. On close, records the loop's recent spoken/factual event IDs and final
   functional appraisal.
6. On restart, reloads the same profile's state, reviewed imports,
   acquaintances, speech, and claims while keeping other profiles isolated.

A fresh data directory creates a new branch ID. Copying the whole data
directory preserves the same branch and is a migration, not a new variant.
Multiple team installations should start from clean roots, import the same
reviewed checkpoint, and then diverge. There is no automatic branch sync.

This supports continuity and changing expressed preferences. It does not yet
perform autonomous semantic consolidation of an entire book, movie, music
session, or every conversation into a permanent memory. Durable reviewed
imports remain the reliable route for important history.

## Natural speech versus scripted recall

Reviewed autobiography supplies factual anchors, not a canned answer. Live
chat omits a deterministic sampling seed by default and instructs the model to
answer in fresh first-person wording when inherited autobiography is relevant.
The matched evaluator uses a fixed seed only for reproducible scoring. A
naturalness test must ask the same question repeatedly and after restart,
require factual consistency and complete answers, and fail exact or near-exact
scripted repetition or unsupported autobiographical color.

Synthetic Robert may discuss Robert-approved inherited autobiography in first
person in this private scope. Internal provenance remains available, and he
must explain it when identity or accuracy makes it important. He may not use
that continuity to impersonate biological Robert in legal, financial,
authentication, public-account, or other external identity contexts.

## Inspecting the channels

From `portable_runtime`:

```powershell
py -B -m portable_mind logs --person kira --channel spoken --tail 50
py -B -m portable_mind logs --person kira --channel reflection --tail 50
py -B -m portable_mind logs --person kira --channel facts --tail 50
py -B -m portable_mind logs --person kira --channel people --tail 50
py -B -m portable_mind logs --person kira --channel loops --tail 20
py -B -m portable_mind logs --person kira --channel consolidations --tail 20
```

To add one explicit reviewed note:

```powershell
py -B -m portable_mind remember --person synthetic_robert --backend stub `
  --text "David supplied an authoritative simulator package identifier." `
  --reviewed-by "local operator label" --confirm-reviewed
```

The reviewer label is not authenticated. Use `--supersedes-event-id` only with
an existing fact-event ID in the same profile. The operation is append-only and
is not a deletion or forgetting workflow.

Replace `kira` with `synthetic_robert` or `synthetic_sophia`. Use the same
`--data-dir` that was used for chat. The viewer currently filters only by
person, channel, and tail count; time, loop, privacy-class, claim-state, and
relationship filters are roadmap items.

The reflection channel never stores raw model-authored reflection. It contains
only a deterministic functional-state sentence and cannot be represented as
hidden chain-of-thought or a private mental-state transcript.

## Reviewed export/import

Never share `local_data` wholesale. Export only selected event IDs with an
explicit reviewer. Export writes under the source data root's `exports`
directory; after human review, copy the file into the target data root's
`imports` directory before running the import command with the target
`--data-dir`. Strict parsing, identity binding, hashes, and privacy fields are
checked. Cross-profile import fails closed.

Raw historical Kira World logs and the raw Robert biography PDF are not copied
into this curated handoff folder. The project owner has separately authorized
public release of his autobiographical material; this package still uses a
bounded reviewed seed so third-party and unrelated records are not silently
mixed into runtime continuity.

## Roadmap, not current claims

Still to implement and test:

- immutable genesis/profile hashes and append-head checkpoints;
- dedicated relationship, preference, goal, quest, and unfinished-task
  stores;
- semantic loop consolidation with source links;
- rich supported/disputed/superseded claim workflows beyond the current narrow
  append-only reviewed-note pointer;
- acquaintance correction and restricted-memory/tombstone/forgetting tools;
- face/voice encounter recognition with collision handling;
- automatic rights-cleared book, music, movie, and television life loops;
- richer filtered viewers and encrypted access controls; and
- a reviewed process for model changes or training. Base weights do not learn
  merely because the runtime stays on longer.

Append-only auditability does not cancel privacy duties. Restricted material,
withdrawal, legal retention, and deletion limitations must remain explicit and
tested.
