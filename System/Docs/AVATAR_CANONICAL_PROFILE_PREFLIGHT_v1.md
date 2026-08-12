# Avatar Canonical Profile Preflight v1

Date: 2026-07-16

## Purpose

Avatar Builder must know which exact person/character variant it is building
before it chooses an adult or doll-safe topology. Older TemporaryAI profiles use
several schemas, some body requests use an authorized alias, and some fictional
profiles still have blank version fields. The preflight layer normalizes those
boundaries without editing or silently “repairing” a canonical profile.

Implementation:

- `Core/avatar_profile_preflight.py`
- `Avatar/avatar_builder/policies/candidate_identity_variant_registry.json`
- `tools/preflight_avatar_candidate.py`
- `tools/preflight_all_avatar_candidates.py`

The registry covers all 22 current TemporaryAI profiles. The bounded batch tool
refuses more than 64 records, verifies exact 22-profile coverage, and excludes
only the two empty smoke directories recorded in the registry. Its result lists
canonical ID, selected-version status, maturity lane, topology lane, and exact
blockers for every profile.

## Three maturity states

The canonical preflight exposes three states:

1. `adult` selects `confirmed_adult_topology` when an explicit canonical
   profile/creation-request binding supports it.
2. `non_adult_doll_safe` selects `non_adult_doll_safe_topology` and rejects
   adult anatomy.
3. `unresolved_doll_safe` also reports the doll-safe topology as the safety
   fallback, but it is **not authoring authority**. Body authoring remains
   blocked until version and maturity are explicitly reviewed.

This prevents both unsafe directions: an unresolved/non-adult character cannot
receive adult topology, and a confirmed adult cannot be silently reduced to a
non-adult body merely because adult evidence is incomplete.

## Fictional version rule

A fictional character must have one machine-readable selected continuity,
timepoint, or version binding. Display names, filenames, actor names, costume
names, downloaded models, and prose handoffs do not replace the canonical
version field. A blank fictional version returns `fictional_version_blank` and
blocks authoring.

An actor's age never establishes the age of the character being portrayed.
Actor/reference models remain optional likeness or measurement evidence under
the separate reference-model rules.

## Age-progressed presentation variants

An age-progressed spa/project presentation version of an already selected
non-adult fictional candidate must have its own canonical candidate ID and
profile. Its presentation label is not a maturity classification; it remains
unresolved until a separate exact subject-bound confirmed-adult record exists.
Preflight returns
`adult_request_requires_separate_profiled_variant` when an orchestration request
tries to change the base candidate in place. The base profile is preserved.

A different case is an initially blank version that Robert explicitly resolves
as the same existing adult source version before body authoring. That resolution
may update the canonical profile when it is captured in a separate exact
evidence record and does not age up, overwrite, or merge identities. Earth-65
Gwen is the current example: Robert confirmed that the Gwen already used by the
project is the main-comics young-adult/college version, age 18-20. The prior
avatar-only workaround is retained only as a superseded inactive audit record.

The variant profile must independently bind:

- source candidate and continuity;
- adult timepoint/variant decision;
- reviewed maturity evidence;
- its own body, voice, clothes, approvals, and runtime state.

## Alias rule

Aliases are exact IDs in the registry, not fuzzy display-name matches. The
current Robert body request `robert_user_avatar_20260716` explicitly resolves to
the canonical `robert_mcmurrer_presence_ai` profile and subject
`robert_mcmurrer`. This fixes the ID drift without creating a second Robert or
renaming either existing artifact.

An unregistered alias or any alias collision fails closed.

Unresolved nonhuman/no-body candidates use `nonhuman_embodiment_unresolved` and
`blocked_nonhuman_embodiment`; they are not silently routed through either
humanoid topology. Once an exact nonhuman embodiment is selected, its visible
body may use an adult or doll-safe topology while the identity remains
nonhuman. Generated experts and original people remain unresolved unless their
canonical profile contains an explicit reviewed maturity/body binding.

## Current reviewed records

| Request/profile | Preflight result | Reason |
|---|---|---|
| Home Beth | passes canonical identity preflight | Profile binds `home_beth_through_s9e8_20260712`; creation request explicitly marks the avatar candidate adult. |
| Robert user avatar request | passes through explicit alias | Canonical profile is `robert_mcmurrer_presence_ai`; profile explicitly says `adult_male`. |
| Existing Spider-Gwen/Gwen TemporaryAI | passes canonical identity preflight | Robert explicitly selected the existing Earth-65 main-comics Ghost-Spider current build, young-adult/college age 18-20. It is adult topology, not a spa age-up or an animated-film/other-Gwen merge. |
| Older Gwen adult avatar project variant | superseded audit artifact; still inactive | Retained to preserve the earlier fail-closed decision. New authoring targets the now-resolved existing Gwen candidate. It still creates no mind/voice/runtime identity. |
| Base Kira TemporaryAI | unresolved for this profile-only batch | Canonical profile/runtime body are unchanged; adult avatar work uses a separate inactive build target. |
| Kira adult avatar build variant | passes canonical identity preflight | Adult topology only; no new mind/voice and no runtime replacement or activation. |
| Five generated experts | pass canonical identity preflight | Robert explicitly confirmed Emily, Jessica, Laura, Ryan, and Sarah are adults. This resolves topology only; no body or activation was created. |
| Kara / *My Adventures With Superman* | passes canonical identity preflight | Robert selected the adult-present end-of-season-2 portrayal; new-to-Earth behavior does not imply childhood. |
| Skynet / *Terminator Genisys* | passes canonical identity preflight | Selected Alex/Skynet physical embodiment played by Matt Smith; adult-presenting humanoid topology for a fictional nonhuman, with body/voice/motion still unproven. |
| Base Marinette TemporaryAI | non-adult but version anchor remains blank | Canonical profile/runtime body are unchanged. |
| Main-series Marinette avatar build variant | passes canonical identity preflight | Non-adult doll-safe topology; adult anatomy forbidden; no new mind/voice/runtime replacement. |
| Kathryn Merteuil | passes canonical identity preflight | User-directed adult continuation selects the 2016 NBC unaired-pilot period, approximately 17 years after the film. *Cruel Intentions 2* (Amy Adams) is backstory only; the 1999 film and 2016 pilot are the Sarah Michelle Gellar performance lane. Existing project chat is preserved by hash. |
| Ruby (*Supernatural*) | blocked | Vessel/performer/version and maturity are unresolved; the profile's `Male` field is reported for human repair and not auto-edited. |
| Peter Parker final-suit candidate | blocked | The name/files suggest *No Way Home*, but `canon_or_version_anchor` and maturity remain blank; an adult project variant must be separate. |

## Integration boundary

File-based orchestration and component production recompute this preflight from
the exact registry/profile/request files before planning or adopting component
artifacts. The result records SHA-256 hashes and refuses profile mutation.
In-memory contract unit tests may omit the external filesystem binding, but no
file-based project production job can use a registered project while bypassing
the preflight.

The preflight does not make a mesh, validate likeness, approve topology, assign
a voice, activate a TemporaryAI, or grant public export.

## Commands

Evaluate one canonical candidate:

```powershell
python tools\preflight_avatar_candidate.py --candidate-id kathryn_merteuil_kathryn_merteuil_20260605_213017
```

Evaluate the exact identity/maturity declarations in a body request:

```powershell
python tools\preflight_avatar_candidate.py --orchestration-request Avatar\avatar_builder\orchestration_requests\spider_gwen_spider_gwen_20260606_013325.json
```

Exit code `0` means canonical identity/version/maturity preflight passed. Exit
code `6` means it remains blocked; the JSON result contains every reason.
