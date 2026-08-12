# Blackwell voice V16 exact-manifest-row control anchor

Status: `AUTHOR_STATIC_ONLY_PENDING_BUILD_SEAL_AND_DIFFERENT_FRESH_AUDIT`

V15 was accepted for one bounded disconnected validation, invoked once, and
failed closed with exit code 4 before output. Its authority is permanently
consumed and V15 must not be rerun.

The exact cause was a native/seal serialization mismatch: V15 searched for
spaced JSON field fragments, while all 21 sealed subject rows were compact
JSON. V16 repairs only that native boundary. It binds each subject as one exact
complete compact row and requires exactly one occurrence, so whitespace
mutation, duplication, missing fields, field splicing, and path-only decoys
fail closed.

V16 retains the already accepted V15 Python source, private validator, config,
six V14 attestations, and immutable origin-bound control semantics byte for
byte. It creates no new Python or voice candidate.

This package contains no model, GPU, synthesis, audio, playback, latency,
network, process, person-state, body, Blender, or production route. Authoring,
building, sealing, and static tests grant no execution authority. A different
fresh V16 audit is mandatory before at most one no-argument disconnected
static-control validation; success or failure consumes it.
