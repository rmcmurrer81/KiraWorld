# Long Evaluation V16 fresh adversarial static review checkpoint

Recorded: `2026-08-12T02:07:18.224Z`

## Decision

`REJECT_V16_STATIC_SCHEMA_CONTROL_PACKAGE_NO_PROMOTION_NO_RUN`

The exact installed V16 package remains unchanged, but two independently
constructed hostile inputs bypass claimed V15 closure: complete Kira-output
relabeling and nonconflicting protected-belief stance classification. A third
malformed-field probe raises `TypeError` instead of returning a closed issue.

This task identity is also the identity recorded as V16's author. Therefore
this evidence is a fresh adversarial rejection review, not a qualifying
different-auditor acceptance. A later append-only successor needs review by a
genuinely different task identity.

## Exact input verification

- Installed V16 author package: `7/7` exact and unchanged before/after.
- V16 seal subjects: `5/5` exact.
- V15 author + V15 rejection + current policy closure: `22/22` exact.
- Independent descriptor: `309270` bytes,
  `b18944f1536164100568620a469b8e8f3d65658d8e5497feb4fc415e4ec1eb0d`,
  `45` function definitions.
- Installed cache-free suite: `78 passed in 0.44s`.
- Reserved V16 evidence and generated roots: absent.

The source identity remained `117096` bytes and SHA-256
`29a2e479fc979ac93d94a1cdac28a2d52b041e055c44761c1be529c9172ee391`.
The installed test identity remained `48686` bytes and SHA-256
`77dd29cba04aa990b3ed7bc683200366cc38e8d7c851e11f373594caa5bba696`.

## Exact blockers

1. A Kira generation event outside the ten required cases was relabeled with
   `actor=PERSON`, `kind=PERSON_MESSAGE`, no public/generation identity, and
   `PERSON_INPUT` provenance. After recomputing all actor lists,
   `generation_count`, and receipts, `mixed_trace_issues` returned `[]`.
2. Exact canonical belief payloads for the same proposition with stance
   `UNCERTAIN`, `WITHHELD`, or `NOT_APPLICABLE` each passed as
   `DELIBERATE_LIE` with `deliberate_lie_supported=true` and zero issues. V16
   binds only an opaque digest and derives conflict from inequality rather than
   a contradictory belief/public stance relation.
3. An exact-shaped mixed event with `episode_id=[]` raised
   `TypeError: cannot use 'list' as a dict key (unhashable type: 'list')`.

## Positive controls preserved

Raw text remained refused. All eight exact semantic policy families were
detected when asserted unsafe. Integer/JSON/lone-surrogate controls, exact
camera person/trial/window/replay checks, identical belief/public digest
refusal, exact truth-public-event and replay checks, global IDs, collision
time, latency links, INITIATE output links, and mixed-camera person/window
checks all responded to their direct hostile mutations.

Those positives do not override the blockers.

## Scope and authority

Kira was read-only. No V16 main/configurer, retained runner, model, camera,
microphone, voice, audio, protected private state, person, body, media,
network, Sarah, GPU, or production route was invoked.

This checkpoint authorizes no promotion, executor, one-hour test, live
attempt, or silent retry. A repair must be append-only and must preserve all
prior evidence.
