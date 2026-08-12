# Blackwell V12 canonical typed-memory integration - static preparation checkpoint

Date: 2026-08-11

Status: `SEALED_STATIC_CANDIDATE_PENDING_DIFFERENT_FRESH_INDEPENDENT_AUDIT`

## Outcome

V12 is the smallest append-only, default-off successor to the rejected V11
integration. It does not edit V2-V11, their consumed attempts or audits, or the
approved production route. It reads the exact accepted V8 adapter and V10
typed-memory helper bytes through file handles, compiles those bytes into
private `ModuleType` objects that are never registered in normal import state,
and retains the exact module, loader, spec, source identity, and callable
identities used by the operation.

The V8 original memory callable and V10 probe/installer are bound by exact
function type, globals mapping identity, code object identity, initial code
digest, defaults, keyword defaults, annotations, function metadata, builtins,
referenced globals/builtins, closure tuple/cells, and closure contents. The
binding rejects pre-existing or later `sys.modules` and package-attribute
poisoning, forged namespaces/modules/proxies/callables, module schema or loader
changes, callable changes, and exact-source identity or byte drift.

Every install, revalidation, and telemetry read validates immediately before
and after authority use. The future preparation helper also revalidates the
canonical config, all 28 preserved boundaries, accepted V10 audit, exact V11
rejection, future audit capability, outer opt-in, and binding after install and
before returning. Install failure proves exact private-module rollback or marks
the binding quarantined. Nothing in V12 authorizes live execution.

These are author/static claims only. They require a different fresh hostile
audit and are not production, live, latency, synthesis, or playback acceptance.

## Exact sealed subjects

| Path | Bytes | SHA-256 |
|---|---:|---|
| `Core/persistent_blackwell_voice_integration_v12.py` | 2,808 | `c64aee200d69bb69f091cd0cea561d2d78ef7fbdb909cc39afe2bbe76c49befe` |
| `Testing/test_blackwell_persistent_voice_candidate_v12_hostile_static.py` | 24,041 | `f8fe244f892b194a4b9ce1ca85b27376404f8a0177d06a982c804755976d688e` |
| `Voice/sidecars/chatterbox_blackwell_persistent_candidate_v12/README.md` | 1,132 | `094357c417286a52de14f8776e7a9be55259b01c6b2ecd5d8c787d081c0b7385` |
| `Voice/sidecars/chatterbox_blackwell_persistent_candidate_v12/candidate_config.json` | 9,202 | `9a6e96f6bae827437b301e4f4e9a1cb468fa44491b080e80956d33e3f3a52c59` |
| `Voice/sidecars/chatterbox_blackwell_persistent_candidate_v12/candidate_contract.py` | 18,691 | `e60dd2b127fb691467b43e6eeeb1becf3674bd29147c046d084a2271d37acf28` |
| `Voice/sidecars/chatterbox_blackwell_persistent_candidate_v12/canonical_typed_memory_binding.py` | 27,300 | `9d2ac1101b5b372aa7881e6c627960753b83ee711fd0db23eb059c216c92b187` |
| `Voice/sidecars/chatterbox_blackwell_persistent_candidate_v12/worker_entry.py` | 4,682 | `377bb6d83e5fad9e77f4b7791287205a3a031c299c511dd7320959aec463f1e0` |

Seal manifest:

- path: `Voice/sidecars/chatterbox_blackwell_persistent_candidate_v12/STATIC_SEAL_MANIFEST.json`
- bytes: 1,744
- SHA-256: `50cef220de1ccb30c3f86adc05d9b1561c87f137c69c0be21aaa7074d0c2db15`

## Static verification

- Final V12 focused hostile/static suite: 27/27 passed cache-free.
- Preserved V11 authored suite: 17/17 passed cache-free.
- Preserved V10 typed-memory suite: 12/12 passed cache-free.
- Total: 56/56 passed.
- Exact V11 blocker reproduction 1 (forged namespace naming the genuine V8
  file) is rejected.
- Exact V11 blocker reproduction 2 (package plus `sys.modules` replacement in
  integrated preparation) is rejected.
- Variants cover exact module/proxy/callable type, code/default/global/closure,
  spec/loader/schema, stored probe/installer, pre/post-install source TOCTOU,
  post-telemetry TOCTOU, and post-preparation dependency TOCTOU.
- Current-process typed Windows memory telemetry remained an exact four-float,
  finite, nonnegative, internally ordered tuple.
- The inherited standard-library static fixture used exact V9 root/direct-child
  topology and closed its process tree and handles.
- All V12 sources parsed, and the test process loaded no Ollama/Qwen, Torch,
  CUDA, or Chatterbox module.

Commands were run with `PYTHONDONTWRITEBYTECODE=1`,
`PYTHONPYCACHEPREFIX=NUL`, and `py -B`:

- `python -m unittest Testing.test_blackwell_persistent_voice_candidate_v12_hostile_static -v`
- `python -m unittest Testing.test_blackwell_persistent_voice_candidate_v11_hostile_static -v`
- `python -m unittest Testing.test_blackwell_persistent_voice_candidate_v10_hostile_static -v`

## Author engineering corrections retained as truth

Before sealing, three fail-closed dry-run defects were found and corrected:

1. Windows handle `fstat` and path `stat` exposed inconsistent creation-time
   semantics, so creation time was removed from the equality tuple while
   device, inode/file-index, size, modification time, and exact SHA-256 remain
   bound.
2. The controller-only `__new__` initially rejected legitimate keyword
   construction; it now accepts keywords while still requiring the private
   construction object.
3. Re-marshalling a code object after execution changed under Python 3.14
   adaptive specialization. Runtime integrity therefore binds the immutable
   exact code-object identity; the initial marshal digest remains sealed
   evidence and is not falsely treated as a stable post-execution byte image.

An initial 26/26 suite passed, but author review found that the future prepare
helper did not re-run every dependency/capability check after installation.
The helper was repaired, a hostile post-prepare TOCTOU test was added, and the
final 27/27 V12 suite passed before sealing.

## Authority and resource truth

- V12 future audit authorization is absent and the path fails closed.
- The exact V11 rejection and its hostile evidence remain preserved.
- All 28 declared predecessor, consumed-evidence, rejection-audit, and routing
  boundaries rehash correctly.
- Production routing remains exact at SHA-256
  `a343572b25937926ea0181274976b53f57ca219ce1e4d3e1780343994aea7b81`.
- V12 parent and direct worker live entries refuse before preparation or process
  creation.
- No Ollama/Qwen request, Torch/CUDA operation, Chatterbox load, synthesis,
  audio, playback, person state, body, media, or Blender operation occurred.

## Next gate

A different fresh agent must rehash this exact seal and all preserved closure,
rerun authored tests cache-free, and add independent hostile probes against the
canonical module/callable binding, normal import poisoning, TOCTOU, strict
telemetry, default-off/live refusal, and cleanup truth. An acceptance can be no
broader than
`ACCEPT_V12_STATIC_CANONICAL_INTEGRATION_FOR_FUTURE_HARNESS_AUTHORING_ONLY`
with `live_authorized=false`. It must not promote production or run a live
harness.

Do not edit the sealed V12 subjects after this checkpoint. Repair any audit
finding in an append-only successor.
