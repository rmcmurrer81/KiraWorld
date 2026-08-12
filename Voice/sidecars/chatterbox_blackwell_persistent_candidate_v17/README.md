# Blackwell voice V17 whole-document manifest control anchor

Status: `AUTHOR_STATIC_ONLY_PENDING_DIFFERENT_FRESH_AUDIT`

Execution authority: `NONE`

V15 is a consumed failure and must not be rerun. V16 is rejected, was never
invoked, and must not be run. V17 preserves both predecessor histories and
repairs only V16's native manifest-verification boundary.

V17 parses one canonical compact JSON document through exact EOF. It parses
actual subject objects, requires exactly 55 unique canonical paths, and
requires an ordered bijection with all 55 locked Bindings. It rejects all
whitespace variants, trailing bytes, missing/extra/duplicate/reordered fields
or rows, all `.` and `..` path segments, noncanonical or overflowing byte
counts, and non-exact digests. The only absolute manifest path it permits is
the exact locked `C:/Python314/python314.dll` binding.

The hostile suite compiles the exact V17 parser into a non-candidate harness.
The harness makes candidate `wmain` unreachable, uses only in-memory fixtures,
and reproduces every V16 bypass as an expected refusal. Authoring, building,
testing, and sealing do not invoke V15, V16, V17, Python, a model, GPU, voice,
audio, playback, network, camera, microphone, speaker, person state, body,
Blender, or Sarah.

This package is not a latency improvement or live voice result. A different
fresh exact-byte hostile audit is mandatory before any later decision about at
most one disconnected no-argument static-control validation.
