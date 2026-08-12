# Kira R25 AFES execution-plan validation V3r26 runtime-control checkpoint

Status: `STATIC_AUTHOR_CANDIDATE_PENDING_DIFFERENT_FRESH_AUDIT_NO_EXECUTION_AUTHORITY`

V3r26 is append-only. It has not been invoked. This checkpoint does not authorize Python initialization, controller compilation, `_build_execution_plan`, AFES, Blender, body, save, render, export, model, camera, voice, or Sarah work.

## Consumed predecessor

V3r25 was invoked exactly once after its independent authorization and exact preflight. Its plan callable attempted once and returned once. The diagnostic then failed at checkpoint 218 with:

`RuntimeError: controller_function_code_or_deferred_annotate_metadata:_build_execution_plan`

Exact terminal counters were plan attempts/returns 1/1, operation enters/returns 16/15, marker 0, and native SHA calls 222. Python finalization, DLL release, module absence, retained-file rechecks, and all fifteen contract gates passed.

V3r25 is `CONSUMED_FAILURE_DO_NOT_RERUN`. Its complete 20-row author/audit/run closure is bound by the canonical root:

- bytes: 3,781
- SHA-256: `d9cde96c013b40451d673dc96a64f60729c7dd52050fc854a26177dbf2906bd6`
- author artifacts: 10
- independent-audit artifacts: 6
- run/post-run artifacts: 4

The initially supplied aggregate metadata (`3,821` bytes / `727d4d66429bbbcf961b905685d35822c8f75f9ff213696c048b60e14e982c58`) is superseded. No authoritative material with that identity was found, and it is not reproducible from the 20 exact rows under the declared UTF-8/LF/sorted-path/tab grammar. Two independent recalculations produce the 3,781-byte root above; every individual row still rehashes exactly.

## Exact diagnosis

The V3r25 plan returned before the failure. The exact failing statement was the checkpoint-218 post-call `_v3_validate_controller(left,right,snapshot)` call. The exception came from its earlier broad left/right `code_or_deferred_annotate_metadata` predicate for `_build_execution_plan`, not from the later generic snapshot-drift predicate.

Before the call, the left and right retained controllers were separately compiled but structurally equal. During the diagnostic only the left `_build_execution_plan` function was invoked. Reapplying the pre-call twin serialization comparison after that asymmetric execution was not a valid immutable-source postcondition: it mixed interpreter-managed execution state with source/code replacement detection.

This diagnosis does not claim the retained plan source mutated. Function call/return 1/1, the data-only plan shape/projections, and checkpoints through 217 all passed. No annotation evaluation route was requested by the diagnostic.

## Bounded V3r26 repair

V3r26 preserves the exact sealed retained source and the existing locked Python 3.14.4 `marshal.version == 5` gate.

Pre-call validation remains strict:

- separately compiled twin function code must have exact format-5 marshal equality;
- deferred-annotation thunk code/default/keyword-default/closure shape and stable metadata must be structurally equal;
- function globals, module, qualname, future-annotations flag, defaults, keyword defaults, and closures must be exact;
- the pre-call code bytes remain the only bytes used to derive the final controller code root.

Post-call validation changes only the false predicate:

- it does not remarshal executed controller or harness code;
- it requires the same function objects and the same code objects by identity;
- it requires identical defaults, keyword defaults, closures, globals, module, name, and qualname;
- it requires the same deferred-annotation function/code/default/keyword-default/closure/cell objects and immutable metadata;
- it retains exact global-key closure, restricted-builtins identity, native-helper identity, constants, exception-class shape, helper identity, module-origin/marshal-version, native SHA helper, data-only plan, and counter gates.

Code objects and function objects are retained strongly by the live controller dictionaries. Under the restricted builtins and sealed source they cannot be replaced without the identity checks failing. Interpreter-managed execution state is deliberately excluded from the post-call byte-serialization comparison.

## Preserved execution ceiling

- no arguments;
- maximum plan attempts: 1;
- maximum plan returns: 1;
- checkpoints: exact existing sequence through terminal success 230;
- operation enter/return maximum: 21/21;
- exact helper counts: SHA 222, lower-hex 231, strict JSON 4, forbidden 0;
- receipt/evidence files use `CREATE_NEW` and consume any terminal attempt;
- Python finalization, DLL unload, process-module absence proof, retained rechecks, contract same-handle rechecks, and terminal evidence remain mandatory;
- stop before bootstrap, broker, child process, AFES, Blender, body, save, render, and export.

## Static-only truth boundary

This repair is a diagnostic validator repair only. It proves no body, internal or external anatomy, skin material, regional pigmentation, hair, Blender scene, save, render, export, camera behavior, voice behavior, mind improvement, or Sarah result. The bald/hair/RAM and material rules remain downstream policy only.

V3r26 must receive strict static tests, hostile mutation tests, x64 `/W4 /WX /O2 /MT /guard:cf /std:c17` build, zero-unsuppressed `/analyze`, PE/import inspection, a complete frozen seal, and a different fresh independent audit before any bounded diagnostic run can be considered.
