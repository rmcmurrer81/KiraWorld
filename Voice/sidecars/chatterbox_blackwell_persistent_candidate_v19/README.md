# Blackwell voice V19 exact-type and camera-schema candidate

V17 remains terminal consumed failure evidence and must never be rerun. V18
was rejected by its different fresh static review and has no execution
authority. V19 is an append-only static repair for the two exact blockers in
that rejection.

The result gate now requires exact Python runtime types before conversion:
an exact tuple of size ten, an exact Unicode schema field, exact Boolean
objects with the required `True` or `False` singleton identity, and exact
integer objects whose conversions are in the signed 64-bit range and whose
values meet the retained V15 result contract. Convertible or truthy/falsey
objects of any other type are refused before their conversion hooks can run.
The 25 individual refusal predicates have distinct result codes 10 through 34.

The retained validator remains exact: 21,931 bytes, SHA-256
`2bf232b07b0b7b93de8776f5210bd2d89068ad76cb4ee46555b861ad2818d16a`,
private module `_kira_blackwell_v15_private_native_validator`, callable
`validate_static_control_graph_v15`, and result schema
`kira.blackwell.v15.native_validator_result.v1`.

The contract also binds a non-executable future matched camera OFF/ON timing
schema. It defines four conditions, 51 monotonic timestamps, 42 metadata
fields, 30 derived durations, and 15 ordering requirements. The explicit-still
condition records local permission/open/capture/draw/JPEG and upload-or-local
handoff, vision lock/load/infer/unload, chat queue/text load/first token/display,
voice queue/load/first sample/audio-ready/playback, and camera close. Matched
prompt, state, queue order, exact Qwen identity and digest, residency, in-flight
state, GPU/VRAM/CPU samples, and frame/cue handling are required. This is a
schema only; it contains no live measurement or speed claim.

This frozen author package is static-only. It grants no V19 invocation, Python
run, model/GPU use, synthesis, audio/playback, latency test, camera/device
access, person state, body/Blender work, Sarah access, or production routing.
A different fresh exact-byte review is mandatory before any later decision.
