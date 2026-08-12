# Blackwell V11 typed-memory integration — different fresh static audit

Completed: `2026-08-11T05:28:54.231Z`

Auditor task: `/root/kira_long_turing_v4_fresh_audit`

Decision: `REJECT`

Verdict: `REJECT_V11_STATIC_INTEGRATION_CANDIDATE`

No live authority, future-harness-authoring authority, production promotion, or playback authority was issued. In particular, this audit did **not** create the candidate's expected `AUDIT_AUTHORIZATION.json`.

## Exact-byte closure

- All six V11 sealed subjects match `STATIC_SEAL_MANIFEST.json` by byte count and SHA-256.
- All fourteen sealed predecessor/routing dependencies match the canonical V11 config.
- The production routing file remains SHA-256 `a343572b25937926ea0181274976b53f57ca219ce1e4d3e1780343994aea7b81`.
- The V11 seal remains 1,410 bytes, SHA-256 `dfa12cb753721d5bb8553dd34509698f12b36ba846a049bc96cd182147b32b20`.
- The author checkpoint remains 4,168 bytes, SHA-256 `52601c5f8ca0a3e608570326a6621cc1796d3d862437133ee29da9471f073788`.
- The author result remains 994 bytes, SHA-256 `ec2ccfd709be0c39ec56192627acea1496ac2a3bbb6bf6f8312381b91d83dc19`.

No sealed candidate or predecessor byte was edited.

## Reproduced author tests

Both suites were run with `PYTHONDONTWRITEBYTECODE=1`, `PYTHONPYCACHEPREFIX=NUL`, and Python `-B`:

- V11 focused suite: 17/17 passed.
- Preserved V10 typed-memory suite: 12/12 passed, including the real x64 current-process regression.

These passes did not overcome the independent blocker below.

## Independent hostile probes

Corrected run: 14 tests, 12 passed, 2 failed, exit 1.

Passing areas included:

- strict config schemas, duplicate-key rejection, non-finite JSON rejection, and bool/numeric type separation;
- exact accepted V10 evidence with `static_only=true` and `live_authorized=false`;
- parent and direct-worker live refusal before process creation or typed integration preparation;
- exact pointer-width `HANDLE`, `DWORD`, structure, and Win32 return prototypes;
- stage-specific native memory failure and invalid-relation rejection;
- finite, nonnegative real current-process/system telemetry;
- changed adapter file rejection;
- exact V9 launcher/worker PID distinction, direct parentage, retained handles, executable identities, Job membership, unique request IDs, complete tree exit, stream/Job/child-handle cleanup, and zero cleanup errors.

The first probe invocation ran zero tests because direct script execution initially omitted the repository root from `sys.path`. Only the append-only audit probe was corrected. No candidate code or worker ran during that harness error.

## Blocking finding

`BLOCK_V11_EXACT_ADAPTER_MODULE_OBJECT_NOT_BOUND`

The exact-adapter installer checks the genuine file named by `module.__file__`, hashes that file, and checks only that the current callable is named `_windows_memory_mib`. It does not prove that the Python object supplied or imported is the canonical module object executed from those bytes.

Two static reproductions failed the required rejection:

1. A forged `SimpleNamespace` with `__file__` set to the exact sealed V8 adapter path and a same-named callable was accepted by `install_into_exact_v8_live_adapter`. The helper patched the forged object and returned `installed=true`.
2. A forged `ModuleType` inserted at the V8 adapter's package/`sys.modules` name was accepted through V11 `prepare_live_memory_integration`. Only the unavailable future-audit gate and replayable outer opt-in were stubbed, matching the sealed author's integration test. Real preserved-byte verification and real accepted-V10-audit verification ran. V11 nevertheless patched the forged object and returned affirmative evidence.

This is blocking because V11's central claim is installation into the exact sealed V8 adapter module. On-disk path/hash truth does not bind the imported module object after the check, so the evidence can identify genuine bytes while a different object receives the patch. Exact import identity and the relevant TOCTOU boundary remain open.

## Replay observation

The environment engineering opt-in accepts repeated checks and is not a one-shot capability. V11 currently refuses every live path and its documentation says a successor must add a new one-shot capability, so this audit records the replayability as an explicit boundary rather than a second blocker. No future harness may treat that string as live authority.

## Required repair

Build an append-only successor; do not edit V11. The successor should preferably use an exact sealed successor adapter rather than runtime monkeypatching. If patching remains, it must establish the canonical adapter module object in a clean child before substitutable import state, reject pre-existing/replaced module objects, validate module name/spec/origin/loader and the exact original callable identity, rehash immediately at patch time, retain the binding for later requests, add both reproduced hostile probes, and undergo another different fresh static audit.

## Evidence

- `INDEPENDENT_HOSTILE_PROBES.py` — 14,520 bytes — SHA-256 `638125fe75c688af939df8f7c815bf67eb8e62cb8d748d1e562bede01015111f`
- `HOSTILE_PROBE_RESULT.json` — 4,014 bytes — SHA-256 `af1688e8fd821a5e44b5927ada83d7c4ac906173184a2a01fea3d7b51f22568c`
- `STATIC_AUDIT_RESULT.json` — 8,770 bytes — SHA-256 `9e5c8372b814193bdb1b87c6ababe65ee017601d80aeaf8ad3a029ba3b2d565e`
- `AUDIT_DECISION.json` — 2,358 bytes — SHA-256 `9ab9a2ec9132e125ef5dead739f8108d8544f449f903e59658610c766ad0c90f`

## Scope truth

- No Ollama or Qwen request ran.
- No Torch, CUDA, or GPU operation ran.
- No Chatterbox model loaded; no synthesis, WAV, audio, or playback ran.
- No synthetic person, memory, body, media, or Blender operation ran.
- The only child process was the authorized sealed standard-library static fixture, and its exact process tree and handles closed cleanly.
- No production pointer or routing file changed.
