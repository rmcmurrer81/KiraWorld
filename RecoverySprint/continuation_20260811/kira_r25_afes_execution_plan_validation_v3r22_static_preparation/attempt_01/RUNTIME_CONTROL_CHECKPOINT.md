# Kira R25 AFES execution-plan validation V3r22 runtime control

Status: STATIC_AUTHOR_CANDIDATE_PENDING_DIFFERENT_FRESH_AUDIT_NO_EXECUTION_AUTHORITY

Author: `codex_r25_afes_v3r22_static_author`

This append-only candidate closes the consumed V3r21 success and the retained V3r9/V3r10/V3r11 history. V3r21 already consumed its one bounded invocation and must never be replayed. V3r10 was rejected without execution. V3r11 is incomplete, unbuildable, and frozen.

The V3r22 source is a deterministic transformation of exact V3r21 source bytes `84245`, SHA-256 `7e78c480643fb7735b1d6738e565c06d169cbd50410e040c8f1f8c7416a0f6f6`. Static preparation, compilation, analysis, PE inspection, sealing, and fresh review are not candidate execution.

The only operation that a later different fresh reviewer may authorize is one native invocation that:

1. validates the no-argument/current-directory/exact-executable boundary;
2. creates fresh write-through evidence and receipt reservations;
3. locks and parses the exact CRLF retained manifest, locks all 137 unique rows, reads them only through those handles, and rechecks all 137 identities;
4. verifies the exact 19-row consumed V3r21 closure and exact 27-row retained history closure;
5. loads only the exact retained Python DLL with only the exact retained standard-library ZIP in the isolated search path;
6. evaluates the exact retained V3r9 controller twice in separate restricted globals;
7. binds both copies' function identities, globals, code identities, marshal-v4 code bytes, defaults, keyword defaults, closures, and annotations, plus every injected helper and the direct imported-module identities/origins, before and after the call;
8. calls `_build_execution_plan` exactly once with the exact retained contract, accepted V3r9 audit, manifest row, and 137-row retained dictionary;
9. validates a data-only 13-key result, destroys that result, finalizes Python, releases the DLL, proves its old module base and exact path absent, rechecks all held subjects, and writes the terminal receipt.

STOP_BEFORE_BOOTSTRAP_BROKER_PROCESS_AFES_BLENDER_BODY_SAVE_RENDER_EXPORT

The source contains no process-creation path and grants no authority to bootstrap, broker, create a child process, execute AFES, open Blender, inspect or modify a body, save a Blend, render, or export. Failure after fresh reservation consumes the bounded authority. Success also consumes it. There is no automatic retry.

Required author workflow:

- transplant source, contract, anchor, static test, and this checkpoint through append-only edits;
- strict x64 build using `/W4 /WX /O2 /MT /guard:cf /std:c17` and an independent MSVC `/analyze` run with zero unsuppressed warnings;
- inspect PE architecture, CFG, imports, and absence of process-launch imports;
- run the authored static test in `PreSeal`, create a deterministic 237-unique-subject seal covering the eight current artifacts, all 100 runtime fixed bindings, and all 137 retained manifest rows, then run `PostSeal` once;
- freeze the author package and request a different fresh static review.

Neither the author nor this checkpoint authorizes invocation. A different reviewer must independently rehash the full seal, reproduce every hostile static mutation, rebuild/analyze/inspect independently, create a fresh LF-only audit and sidecar, and explicitly accept exactly one bounded pure-plan invocation. Until then `execution_authority` is `NONE`.

Truth boundary: no V3r22 candidate has been invoked; no Python/controller/AFES/Blender/body/save/render/export operation was performed while authoring; no body or anatomy result is claimed.
