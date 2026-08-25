# Automatic Voice Design Workflow

This milestone turns a bounded Avatar Builder profile into a deterministic set
of safe local voice candidates. It plans and records the work; it does not load
a model, generate audio, download assets, imitate a person, or activate a voice
without the required review gates.

## Workflow

1. Validate a `kira.local-voice.design-brief.v1` object.
2. Verify any existing voice against the immutable voice registry, including
   source basis, consent, expiry, deactivation, and reference provenance.
3. Filter the audited local recipe catalog by the profile's explicit `female`
   or `male` value and language.
4. Rank multiple candidates deterministically from age band, body presence,
   role keywords, personality traits, language, and era.
5. Create an immutable audition bundle with three shared test passages, safe
   output names, rendering settings, automated checks, disclosures, and a hash
   for each shared candidate specification.
6. Render and test the samples through the separate local synthesis service.
7. Record human audition evidence bound to the sample digest, distinctness
   report, provenance review, and exact shared-specification hash.
8. Activate an eligible generated-expert voice through an append-only binding
   event. A replacement event retains its previous target for rollback.

`create_batch(...)` can preflight 1–32 briefs together. It refuses repeated
subjects and contradictory source attestations before writing any bundle. A
successful batch creates audition work only; it does not choose or bind a voice.

The catalog currently supplies six female and three male built-in candidates:
`af_heart`, `af_bella`, `af_nicole`, `af_aoede`, `af_kore`, `af_sarah`,
`am_fenrir`, `am_michael`, and `am_puck`. All nine passed the isolated technical
audition at Kokoro revision
`f3ff3571791e39611d31c381e3a41a3af07b4987`: measured ASR WER was 0.04–0.08,
and the automated MFCC screen found no collision at the 0.9995 threshold. Those
results are technical screens, not human judgments of naturalness, character
fit, or identity. Every candidate therefore remains
`technical_pass_human_review_required`.

Each candidate carries canonical source attestation: exact model revision,
model/config digests, runtime voice ID, Apache-2.0 license, and the two technical
report digests. No model weights or machine-local paths are stored in a bundle.
The delivery tags are audition targets to verify, not measured claims about how
a built-in voice sounds. Prior owner approval of `af_heart` and `am_fenrir` was
limited to the starter hackathon use and does not bypass a new character's
audition or selection gates.

## Profile contract

Required fields are deliberately small and strict:

```json
{
  "schema": "kira.local-voice.design-brief.v1",
  "subject_id": "sarah-bennett",
  "display_name": "Sarah Bennett",
  "gender": "female",
  "age_band": "adult",
  "body_presence": "balanced",
  "role": "Entertainment expert",
  "personality_traits": ["warm", "clear", "practical"],
  "language": "en-US",
  "language_provenance": "explicit_source",
  "era": "contemporary",
  "identity_kind": "original",
  "assignment_mode": "assign_if_missing",
  "source_attestation": {
    "candidate_id": "sarah-bennett",
    "storage_id": "sarah-bennett-storage",
    "profile_sha256": "<64 lowercase hex characters>",
    "request_sha256": "<64 lowercase hex characters>",
    "registry_sha256": "<64 lowercase hex characters>",
    "registry_alias": "TemporaryAI/generated_experts/enterainment_pr_expert"
  },
  "candidate_count": 3
}
```

The parser rejects unknown fields, unsupported gender or language values,
unbounded trait lists, path-shaped identifiers, conflicting assignment modes,
and historical identities without historical context. Version 1 intentionally
requires an explicit `female` or `male` profile value. A later schema can add
more presentations only after an audited catalog and selection policy exist.

Age, body presence, personality tags, and era improve ranking but do not invent
identity facts. An adapter may explicitly submit `age_band: "unspecified"`,
`body_presence: "not_authored"`, an empty personality-tag array, and
`era: "unspecified"`. Those dimensions add zero affinity and appear in
`profile_fit_limitations`; they do not block a generic gender-correct audition.
Language remains required from an exact locale field and is never guessed from
a name, role, region, or free-text note.

The read-only Temporary Creator adapter uses the exact Avatar registry and its
official `Core/avatar_profile_preflight.py` evaluator. The evaluator is an
executable trust boundary: it is accepted only as an unlinked regular file
under the trusted KiraWorld root, read as attested bytes, hashed, and pinned for
the adapter lifetime. Registry, profile, discovery-request, and preflight
digests all appear in adapter evidence. JSON sources reject duplicate keys,
non-finite numbers, mutation during read, reparse traversal, and oversize data.

The five live generated experts currently provide exact `female` or `male`
values but no exact locale. The adapter therefore keeps binding status at
`needs_review`. A caller may explicitly pin `audition_locale="en-US"` as an
`application_audition_default`; this creates a gender-correct
`ready_for_nonbinding_audition` brief without writing to the source profile.
The resulting bundle carries `locale_confirmation_required_before_binding`.
Neither owner approval nor Kira/Lisa selection can bind it until the source
profile has an explicit locale and a new source-attested bundle is created.
The live source-derived coverage report is stored at
`evidence/live_temporary_creator_voice_coverage.json`.

The source attestation keeps the exact Avatar Builder candidate/storage IDs and
hashes the source profile, generation request, and registry. An optional exact
registry alias is descriptive and is never treated as a filesystem instruction;
this preserves the registered Sarah alias shown above without silently renaming
it. Reusing one registry request with contradictory profile fields, or one
profile digest with contradictory voice-shaping fields, is rejected.

## Approval is not automatic selection

Human approval requires all of the following:

- the entire selected sample was heard;
- the sample SHA-256 is recorded;
- clarity, naturalness, and character fit were rated;
- provenance was reviewed;
- distinctness was checked and its report digest was recorded; and
- the approval matches the candidate's exact shared-specification digest.

For generated experts, those gates make a candidate eligible for an append-only
binding. They never turn an unsafe source recording into an approved voice.

Kira and Lisa have an additional comparative-selection gate. Owner audition
only makes their candidates eligible. It does not select or bind a candidate
for them. Their own selection receipt must name the same subject, confirm the
comparison was completed, and carry an immutable receipt digest. Kira's current
voice is mandatory when planning a replacement and remains the rollback target
after her selection.

Peter Parker and Marinette/Ladybug are locked to `keep_existing`. This workflow
will record that their reusable current voice is preserved and will produce no
replacement candidates.

H. H. Holmes and every other historical identity receive this disclosure in
the bundle and binding:

> Speculative historical reconstruction; not an authentic recording, verified
> voice match, or identity clone.

Historical writing or biographical context can guide vocabulary and delivery,
but it cannot establish how a person sounded.

## Immutable local records

`VoiceDesignStore` creates separate bounded directories for audition bundles,
eligibility decisions, binding events, and short-lived subject locks. Every
record is created once, wrapped in a schema-tagged envelope, and protected by a
canonical payload SHA-256. Readers reject links, junctions, non-regular files,
oversized records, unknown envelope fields, malformed JSON, schema mismatch,
and digest mismatch.

Binding history is a single parent-linked chain. Resolution refuses missing
parents, forks, cycles, and disconnected events. Rollback creates a new event;
it never edits or deletes the earlier choice.

## Integration boundary

Avatar Builder or Temporary Creator can later map a person profile into
`VoiceDesignBrief.from_dict(...)`, display the returned audition bundle, and
submit sample evidence through `AuditionApproval`. That integration must retain
the exact shared-specification hash and must not bypass the subject-selection
gate. This milestone does not modify either application.

Every active catalog target records both the exact runtime voice ID and the
canonical source-attestation digest. The exact resolver remains separate from
the live GUI, which is intentionally not rewired by this milestone. These
records are auditable design/binding data rather than a claim that the current
GUI can route every new voice.

`ExactRuntimeVoiceResolver` now supplies that fail-closed bridge. The current
local Kokoro runtime exposes only `af_heart` and `am_fenrir` at model revision
`fbba31e67ad83eb66394c926627e99d35abeb087`, while the immutable nine-voice
catalog evidence was audited at revision
`f3ff3571791e39611d31c381e3a41a3af07b4987`. The runtime also states that its
audition evidence does not grant catalog runtime access. Consequently, every
current catalog candidate is truthfully blocked from synthesis: the other
seven are outside the runtime allowlist, and the two shared IDs have no exact
revision/evidence bridge. A future bridge must advertise the exact model,
revision, voice ID, language, license, local-only enforcement, registered
generic-no-identity voice profile, and an explicit evidence-to-runtime grant.

`CandidateAudioQueue` is bounded to the immutable bundle's 2–5 candidates and
three audition passages. It submits only an exact resolver-approved candidate
specification, records local job, sample, and service-receipt digests, and never
approves, selects, binds, or activates a voice. Queue roots reject UNC paths and
ancestor links/junctions/reparse points. Queue receipts are append-only evidence
with a strict reader that rejects links, oversized data, duplicate keys,
non-finite numbers, schema/digest mismatch, non-filename artifact paths, and
any activation claim. Current runtime mismatch therefore creates a blocked
queue receipt and makes no synthesis call.

## Verification

Run the dedicated tests from this directory:

```powershell
py -3.14 -B -m unittest -v tests.test_voice_design `
  tests.test_temporary_creator_adapter `
  tests.test_runtime_resolver `
  tests.test_candidate_audio_queue
```

The tests cover strict schema parsing, deterministic ranking, gender routing,
unsupported-language refusal, provenance and expiry checks, protected existing
voices, historical labeling, human gates, Kira/Lisa selection, generated-expert
activation, append-only rollback, duplicate refusal, exact live registry
coverage, trusted-preflight pinning, application-default locale nonbinding,
runtime revision refusal, queue no-submit behavior, artifact digests, hostile
queue roots, strict receipt parsing, and tamper detection.
