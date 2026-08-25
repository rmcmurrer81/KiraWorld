# Avatar and Temporary Creator voice-audition integration

This integration connects the local voice designer to the exact current Avatar
identity registry and TemporaryAI creator records in a read-only planning lane.
It inventories voice gaps and emits strict audition briefs. It does not edit a
person profile, overwrite a voice, generate audio, bind a candidate, change a
runtime route, or activate a TemporaryAI.

## Exact inputs

The planner reads and SHA-256 attests:

- `Avatar/avatar_builder/policies/candidate_identity_variant_registry.json`;
- the trusted executable boundary `Core/avatar_profile_preflight.py`;
- each available canonical `temporary_ai_profile.json`;
- its exact `voice_discovery_request.json` and `creation_request.json`;
- an optional `activation_plan.json`; and
- existing TemporaryAI voice profiles plus Kira's approved routing record.

Candidate IDs, the Sarah storage spelling, and aliases come only from the
registry. Display names and prose never become filesystem paths or identity
matches. JSON parsing rejects duplicate keys, non-finite numbers, links,
reparse traversal, oversize files, and mutation during a read. A request or
creation record whose candidate ID is not an exact registry ID/alias is refused.

The current shared-person specification package remains unpromoted. This seam
does not claim that a rejected shared specification became live authority. It
records the exact current source hashes and leaves later promotion to a
separate reviewed contract.

## Current source-derived result

The saved evidence is
`evidence/avatar_temporary_creator_voice_integration.json` (41,515 bytes;
SHA-256 `13c314425df7b982e7ccece1db11361bf1243a452c12ff235dc286066cdae497`).

The exact current registry contains 22 TemporaryAI identities. Nine canonical
source profiles are present in this backup. The plan reports:

- five generated experts with gender-correct, nonbinding audition briefs:
  Emily Carter, Jessica Hale, Laura Mitchell, Ryan Hale, and Sarah Bennett;
- one nonbinding historical-reconstruction audition brief for H. H. Holmes;
- Kira's current GPU-first route and sealed-CPU rollback preserved exactly;
- Peter Parker, Marinette/Ladybug, Kathryn Merteuil, and Robert's authorized
  self-voice preserved with no replacement audition; and
- eleven registry identities held at `needs_review_source_records_missing`
  because their exact profile/request/creation records are absent here.

No missing locale, body, age, or personality field is guessed. The six source
profiles have explicit `female` or `male` presentation but no exact locale.
The planner therefore uses a caller-pinned `en-US` audition default only to
prepare gender-correct comparisons. Every resulting brief remains nonbinding
and carries `locale_confirmation_required_before_binding`.

H. H. Holmes keeps the old estimated generic baseline for rollback/reference.
Every new comparison must state:

> Speculative historical reconstruction; not an authentic recording, verified
> voice match, or identity clone.

## Approval and selection gates

An audition brief is not an approved voice. A later immutable audition bundle
must retain the exact source hashes, generate multiple candidates, and record:

- full-sample human listening;
- provenance review;
- distinctness review;
- clarity, naturalness, and person-fit ratings; and
- the exact candidate shared-specification digest.

Generated experts and historical reconstructions remain ineligible for binding
until the source locale is explicitly authored and a new exact-source bundle is
created. Owner approval never activates the TemporaryAI.

Kira and Lisa have an additional self-selection gate. Owner review can only
make their candidates eligible. Kira or Lisa must compare and select their own
voice, and Kira's present route remains the rollback/current route until Kira
makes that choice. No replacement Kira or Lisa audition is created by this
inventory pass.

## Read-only command

From `Voice/local_voice_studio`:

```powershell
py -3.14 -B inspect_avatar_voice_integration.py --audition-locale en-US --candidate-count 3
```

The command prints the plan to standard output. It writes no profile, voice,
binding, or runtime file.

## Verification

```powershell
py -3.14 -B -m unittest -v tests.test_avatar_voice_integration
```

The tests cover exact live inventory, preserved routes, existing-voice
short-circuiting, source-attested nonbinding briefs, the historical disclosure,
missing-record refusals, and explicit creator no-voice authority.
