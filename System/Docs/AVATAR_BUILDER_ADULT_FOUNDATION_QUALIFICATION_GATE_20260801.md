# Avatar Builder Adult-Foundation Qualification Gate

Date: 2026-08-01  
Status: **CURRENT FAIL-CLOSED PIPELINE AUTHORITY - NOT BODY APPROVAL**  
Scope: reusable, private adult-avatar foundation selection

## Outcome

Avatar Builder now treats adult eligibility, source authority, and complete
topology proof as three separate decisions. A confirmed-adult female request
must enter the adult-female lane, but the words `adult`, `female`, `rigged`, or
`watertight` never prove that the exact source is a complete adult foundation.

The read-only evaluator is
`Core/avatar_adult_foundation_qualification.py`. Its versioned policy and
source registry are:

- `Avatar/avatar_builder/policies/adult_foundation_qualification_v1.json`;
- `Avatar/avatar_builder/policies/adult_foundation_registry_v1.json`.

The gate performs no build, render, copy, selection, activation, or runtime
mutation.

## Required exact-candidate proof

Qualification requires all of the following at the same exact artifact hash:

- confirmed-adult maturity and `adult_female` body class;
- an adaptation/foundation role authorized by the enrolled license and source
  provenance;
- one primary body-surface component;
- zero boundary edges, nonmanifold edges, degenerate faces, coincident
  duplicate triangle pairs, and nonadjacent self-intersection pairs;
- independent topology review separated from the candidate author;
- independent adult-anatomy relationship review separated from the candidate
  author;
- connected geometric proof, not painted labels, for mons pubis, paired labia
  majora, paired labia minora, clitoral hood and clitoris, vestibule, urethral
  opening anterior to the vaginal opening, vaginal opening, posterior
  commissure/fourchette, and the perineal transition to anus/pelvic floor;
- explicit negative findings for doll-safe/incomplete anatomy, floating or
  separate anatomy, intersection, wrong-sex helper geometry, and visible open
  seams/bridge patches.

A caller cannot override a registered blocker by supplying a more favorable
status string. Evidence files are themselves hash-bound, and changing either
the candidate or review bytes invalidates qualification.

## Current source audit

The aggregate audit registers five local source lanes and truthfully qualifies
zero:

- MakeHuman hm08 plus female macro targets: source/license role is usable for
  a newly authored derivative, but the existing female surface is doll-safe or
  incomplete and its male helper is excluded. It is a body/rig substrate, not
  finished adult topology.
- BlackProject base female: source/license role permits adaptation, but the
  prior adult patch has proven nonadjacent self-intersections and remains
  blocked.
- `womenfemale_body_base_rigged_3ec62ba8d7`: cage-fit evidence only; complete
  adult topology is unproven and copying it as a candidate body is not
  authorized.
- `base_female_game_ready_rigged_low_poly_471903a311`: cage-fit evidence only;
  complete adult topology is unproven and copying it as a candidate body is
  not authorized.
- `female_anatomy_study_progress_2_b0577836d8`: structural reference only;
  never copy it as an AI body or treat it as a licensed foundation.

This is intentional. The next legitimate path is to author a new continuous
generic external adult-female surface on the CC0 MakeHuman body/rig substrate,
then audit that derivative independently. Kira styling may begin only after
the generic exact artifact passes this gate.

## Tests

Run:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
py -m unittest tools.test_avatar_adult_foundation_qualification -v
```

Current result: **14/14 PASS**. The suite covers a genuinely complete synthetic
fixture, changed evidence bytes, exact candidate hash mismatch, missing
license/hash authority, wrong-sex helper, self-intersection, reviewer
independence, reference-only bypass attempts, immutable registered blockers,
unknown foundations, and all five known local entries.

## Privacy and promotion boundary

Generic method work must not contain Robert's photographs, measurements,
likeness targets, morph deltas, vertex selections, intimate observations, or
private candidate geometry. Kira-specific styling and body preferences also
remain outside the generic method.

A method is not selectable in the reusable-method registry merely because the
first Kira build works. It still requires the separate reusable-method
promotion gate, owner approval where required, and two non-private synthetic
fixture proofs. No result from this qualification gate authorizes activation,
assignment, clothing, publication, upload, or runtime replacement.
