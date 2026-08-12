# Avatar Builder Temporary-Body Conversational Acceptance

Status: implemented and executed as a private control-plane acceptance on 2026-08-02. No body geometry was generated and no visual approval is claimed.

The acceptance runner is `Tools/run_avatar_builder_temporary_body_conversational_acceptance.py`. It patches every Avatar Builder state/output root to a new append-only evidence sandbox. It cannot overwrite a populated attempt directory and does not invoke Blender, a GPU, camera, microphone, live avatar, activation, assignment, publication, or upload paths.

## Covered owner scenarios

- Two sandbox temporary candidates explicitly confirmed by Robert as adults, including offline, route to `adult_male` and `adult_female` respectively.
- Peter Parker starts with a deliberately wrong provisional non-adult classification. The exact correction beginning `No, this version is an adult; use an adult body` plus the post-*No Way Home* / pre-*Brand New Day* timepoint creates an append-only `adult_male` replacement route. The rejected fixture remains present and byte-identical.
- A later message mentioning high-school-era pictures only as contrast cannot change Peter's persisted adult classification or the requested later continuity.
- Robert's logged exact fictional-version correction is authoritative when Internet access is unavailable. Network lookup is not a prerequisite for that explicit owner correction.
- Normal Marinette remains `non_adult_doll_safe`; an attempted in-place adult conversion is rejected without changing either adjustment state or the preserved fixture.
- Hair correction rebuilds only the detachable `hair` component. Body, face, eyes, skin, rig, weights, and movement fixtures remain hash-identical.
- Spa Age Progression is two-stage. Stage 1 queues a separate older/taller private variant with adult anatomy forbidden. Stage 2 remains blocked until exact Stage 1 evidence, confirmed-adult classification, repeated-activation/promotion/spa eligibility, and the resident's separate anatomy choice are all present.

The Stage 1 artifact used by this automated acceptance is explicitly marked as a control-plane fixture. It proves gate behavior only; it is not a mesh, a completed age progression, or owner-reviewed evidence.

## Preservation and approval truth

Every successful next-build route is private, inactive, unassigned, unpublished, and unapproved. A classification correction does not approve a body. Superseded candidate deletion is forbidden, and the previous revision must remain preserved. Hair and maturity corrections may not silently regenerate accepted unrelated components.

## Remaining boundary

Actual temporary-body generation is intentionally not started by this acceptance. It must wait until the current Kira and Biological Robert private owner-review body work is complete. A later monitored Blender run must bind real input/output hashes, movement and contact evidence, private review renders, and Robert's visual decision without converting this control-plane pass into a claim of body approval.

## Verification

Run the isolated test with:

`py -B -m unittest -v Testing.test_avatar_builder_temporary_body_conversational_acceptance`

The preserved execution evidence is under:

`RecoverySprint/continuation_20260802/avatar_builder_temporary_body_conversational_acceptance/attempt_01`
