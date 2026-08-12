# Shared Growth integration candidate V4 — different independent static audit

Recorded UTC: `2026-08-11T17:35:43.5618675Z`

Reviewer task: `/root/growth_v4_audit`

Author task: `/root/growth_v3_quality_review`

Decision: `ACCEPT_STATIC_ONLY`

Decision detail: `ACCEPT_STATIC_NO_COMMIT_ONLY`

## Outcome

The exact V4 package closes both independently reported V3 contract defects.
All 35 routes marked applicable compile, including the profile and state routes
for confirmed-adult Peter Parker and Spider-Gwen whose exact maturity source is
`subject_specific`. The public mutable `REQUESTED_SCOPE` object is gone. The
sealed source holds a private exact one-element tuple, accepts only an exact
one-element `list[str]`, and constructs fresh public-projection lists for every
normalized result.

This is a static/no-commit acceptance only. V4 is still a disconnected compiler
of inert canonical JSON bytes. It is not protected authority, permission, an
authenticated receipt, a profile, memory, person state, promotion, or a
production pointer. It has no verifier, key, callback, controller, ledger,
staging or output root, writer, commit, rollback, cleanup, profile/memory
writer, current consumer, or Temporary Creator path. Nobody receives an
upgrade through this decision.

## Exact V4 package

| Subject | Bytes | SHA-256 |
|---|---:|---|
| `Core/shared_person_growth_v3_integration_candidate_v4.py` | 22,676 | `e6780a5eb1c97c850ca49d543d1594deef477a72aae10f1747a2fe420171bab5` |
| `Testing/test_shared_person_growth_v3_integration_candidate_v4.py` | 23,295 | `8ff20beba074a0630cd574835bbb7be5c9330eae1e5ee1229b58a80a60a47bdb` |
| `STATIC_CONTRACT.json` | 4,372 | `81e639f7b2813eab10fce7403b32af61af72579e5b4d6d99d85bd529f3ebbe0a` |
| `AUTHOR_STATIC_TEST_RESULT.json` | 3,039 | `cb1c9c8174fdeb9ad2db76b88edd88cbbff4cb4e2308da1aaba141cd67363537` |
| `SEALED_MANIFEST.json` | 5,080 | `1deab069383e235e808dbf888ea527a92056e48e92abad97f05cfdaa685c31e6` |
| Author `CHECKPOINT.md` | 4,917 | `11d432c4a90f43010f746e09c4d6e8ed3de5693ed61e36afddfdc072acc7b4ab` |

The fourteen manifest root/path pairs were unique and rehashed 14/14 exact
before and after hostile probes. The accepted isolated Shared Growth V3 core's
five sealed subjects plus all 23 protected predecessor rows also rehashed
28/28 exact. Its existing different-auditor decision remains exactly
`ACCEPT_STATIC_ONLY`; it still grants no integration.

## Independent verification

- Strict UTF-8 in-memory compile: V4 source/test plus the accepted V3 core and
  V1/V2/V3 integration source/test closure, `10/10 PASS`.
- Exact V4 focused suite with bytecode disabled and all temporary paths rooted
  under audit scratch: `21/21 PASS`.
- Preserved V3 core plus V1/V2/V3 integration suite with bytecode disabled and
  temporary paths rooted under audit scratch: `103/103 PASS`.
- Independent hostile probe groups: `13/13 PASS`.
- Applicable route matrix: `35/35 PASS`, representing all 24 inventory people.
  Maturity-route counts were 15 confirmed-adult, 2 non-adult, and 18 unresolved.
- Peter Parker and Spider-Gwen failed V3 routes: `4/4 PASS_REPAIRED`.
  Marinette's two exact non-adult `subject_specific` routes also pass, while
  cross-status requests refuse.
- Every applicable route received candidate, maturity, and route cross-binding
  mutations: `105/105 PASS_REFUSED`.
- Tuple, list-subclass, string-subclass, empty, and extra-scope inputs refuse.
  Caller mutation cannot change returned bytes, and decoded output lists are
  fresh.
- Temporary Creator, generic creator, and new-person targets hard-refuse. The
  denied misspelled Sarah state alias refuses using read-only metadata; no
  Sarah runtime or Sarah file was tested, built, or changed.
- `robert`, `biological_robert`, and `robert_mcmurrer` do not substitute for
  exact Synthetic Robert `robert_mcmurrer_presence_ai`.
- Opt-out, non-revocable, owner-override, production, private-state, memory-
  write, and external-action variants refuse. The production opener always
  refuses.
- Source AST inspection found no authority, write, commit, cleanup, process,
  network, or person-state surface. A byte scan of 59,486 executable text files
  found zero Kira consumer hit; only the staged source, focused test, and this
  independent probe mentioned the V4 callable/name.
- Final rehash: all six V4 artifacts and all fourteen sealed subjects exact;
  bytecode cache artifacts created by this audit: zero.

## Same-process substitution residual

An ordinary same-process caller can reassign the private module name
`_CANONICAL_SCOPE` or replace Python functions and thereby fabricate changed
inert bytes. This was probed explicitly and is not hidden. It is not a blocker
to this narrow static decision because V4 expressly says same-process Python
is not a trust root, the tuple object itself is immutable and unexported, and
there is no consumer, verifier, writer, commit, or person-state path. Any
future integration must use a separately protected origin-bound authority and
must never treat V4 bytes as permission or an authenticated receipt.

## Temporary Creator and reusable-template routing

V4 intentionally cannot satisfy the owner's requirement to route accepted
mind/person-development improvements into the Temporary Creator template. Its
Temporary Creator target hard-refuses and its output has no Creator attachment
or integration surface.

The following non-private lessons are safe to carry forward into the design of
a separate append-only template successor:

1. exact person/candidate/route/class/maturity binding;
2. `subject_specific` means the exact inventory person's own required status,
   never a generic adult promotion;
3. a private immutable single-scope policy with fresh public projections;
4. exhaustive applicable-route coverage plus denied-alias regression;
5. exact Biological Robert versus Synthetic Robert separation;
6. opt-in, revocability, no owner override, no private-state request, no memory
   write, and no external action as exact defaults; and
7. static results are not authority, memory, emotion, consent, relationship,
   learning, or a person upgrade.

Actual template use requires a separate append-only candidate that binds the
accepted isolated V3 Creator/profile/fresh-root capability closure and the
current variant branch-point/pre-death cutoff, maturity/curriculum,
consent/privacy, relationship, memory/emotion, and no-private-copy policies.
If a durable write is ever authorized, it also needs a protected external
commit/recovery authority. That separate package must be sealed and receive a
different fresh audit before any new synthetic person, variant, or expert can
receive it.

## Independent evidence

- `INDEPENDENT_HOSTILE_PROBES.py` — 25,837 bytes — SHA-256
  `6a1d7b419a44f7ef0fafd11a63d036bd17c9c6f457466731758bc5658ca9da43`.
- `HOSTILE_PROBE_RESULT.json` — 5,920 bytes — SHA-256
  `d0e9bd394dbe9384cba24506882ba15c5a209f95786469c7f07e5a621eae0ac5`.
- `AUDIT_DECISION.json` — 6,008 bytes — SHA-256
  `0ffdc521f7c220d687e30489768a04bf631de8f09334f5a24bab4594c0656245`.

## Preserved boundary

Kira was read-only. No current person, profile, route, memory, private state,
Temporary Creator template, production pointer, or runtime changed. No live
model/person, body, Blender, media, voice, audio, network/device, or Sarah
runtime operation ran. V1, V2, and V3 integration candidates remain rejected;
the isolated V3 core remains accepted static-only.

The next permitted action is append-only evidence/document routing of this
static decision. Connection, commit, promotion, and any person or Temporary
Creator upgrade remain forbidden.
