# Kira R25 AFES execution-plan validation V3r24 — runtime control checkpoint

Date: 2026-08-11  
Attempt: `attempt_01`  
Status: `STATIC_AUTHOR_CANDIDATE_PENDING_DIFFERENT_FRESH_AUDIT_NO_EXECUTION_AUTHORITY`  
Execution authority: **NONE**

## Truth boundary

V3r24 is an append-only diagnostic candidate authored in a scratch preparation tree. No V3r24 executable, Python runtime, retained controller, plan callable, bootstrap, broker, process, AFES path, Blender path, body path, save, render, or export path has been invoked during authoring.

V3r23 was never invoked and is rejected with no execution authority. Its exact ten author artifacts and five independent-rejection artifacts are a frozen 15-row closure: 2,728 canonical bytes, SHA-256 `0b09c1f71154b4d56559f043f08076940bcc60e7919d6bcd8e9c3cde3b2a4ea0`.

V3r22 is a consumed bounded failure and is `DO_NOT_RERUN`. Its durable record proves only a terminal failure somewhere inside the former stage-40 validator boundary. The actual V3r22 stage-40 cause remains unknown. The V3r22 exact 20-row consumed-failure closure remains 3,779 canonical bytes, SHA-256 `7057deb657f5e235892180e5d694f139450d44897f9353ac3bdb1f15d730aec0`.

## Excluded annotation cause

The earlier V3r23 diagnosis attributing V3r22 stage 40 to unresolved annotation names is rejected. V3r22 and V3r23 both compile the retained controller with `flags=0x1000000`, `dont_inherit=True`, and `optimize=0`. The exact installed CPython 3.14 header is fixed at 14,708 bytes and SHA-256 `65fe295bd90aab0a5380c4b3c400713917af7f904fbb0ac86e76ffff2de1ab18`; it defines `0x1000000 == CO_FUTURE_ANNOTATIONS`. The exact retained standard-library zip is already held by the 137-row retained manifest, and its `__future__.py` declares that this flag makes annotations strings at runtime.

V3r24 therefore asserts the C header value at compile time, asserts the module and every retained controller function code object carry the exact flag, and requires every annotated retained function to have its generated `__annotate__` stringizer. The validator fingerprints each stringizer's type, globals, code bytes, identity, defaults, keyword defaults, closure identity/cells, module, name, and qualified name. It never reads `function.__annotations__` and never calls `function.__annotate__`. Thus the retained controller annotations stay stringized and non-evaluated, and unresolved global annotation names are an excluded cause rather than a proposed repair hypothesis.

## Bounded diagnostic

If, and only if, a different independent reviewer later authors an exact 29-line LF-only acceptance TSV plus one-line SHA-256 sidecar and explicitly accepts the frozen bytes, the native candidate permits at most one no-argument diagnostic invocation. That invocation may:

1. enforce exact current directory, executable path, x64 image identity, audit grammar, and append-only output absence;
2. bind all 136 fixed subjects, including all 15 V3r23 rejected artifacts, all 20 V3r22 consumed-failure artifacts, and the exact CPython code header;
3. parse, lock, read, and later recheck all 137 exact CRLF retained-manifest rows;
4. reserve a single `CREATE_NEW` write-through receipt and evidence file;
5. initialize only the exact isolated CPython runtime and exact retained standard-library zip;
6. compile two restricted controller copies with the exact future-annotations flag, without evaluating annotations;
7. call only `_build_execution_plan` once with six exact keyword arguments;
8. validate the returned data-only plan, destroy it, finalize Python, unload the DLL, prove module absence, and recheck every retained/fixed artifact;
9. commit bounded success-or-failure telemetry and consume all future authority.

The single call has exact attempt and return counters. The controller helper success bounds remain 222 SHA calls, 231 lower-hex checks, four strict JSON parses, zero forbidden blob/canonical helpers, and 223 total native SHA calls including the post-validation code root.

## Failure localization

The validator records `operation_enters` immediately before, and `operation_returns` immediately after, each of 21 named fallible operations. Success requires both counters to equal 21, plan attempts/returns to equal 1, and terminal checkpoint 230. A failure preserves the most recent checkpoint and unequal entered/returned counters when an entered operation does not return.

Checkpoint pairs are:

- `140/141`: left controller compile/exec/closure;
- `150/151`: right controller compile/exec/closure;
- `160/161`: pre-call controller seal;
- `170/171`: sole plan call;
- `180/181`: helper-count validation;
- `190/191`: plan shape;
- `200/201`: contract decode;
- `202/203`: retained binding lookup;
- `204/205`: V5 decode;
- `206/207`: V2 decode;
- `208/209`: plan identity;
- `210/211`: retained paths;
- `212/213`: output paths;
- `214/215`: projection equality;
- `216/217`: recursive data-only walk;
- `218/219`: post-call controller seal;
- `220/221`: post-call harness seal;
- `222/223`: module-origin recheck;
- `224/225`: native-helper recheck;
- `226/227`: controller code root;
- `228/229`: terminal marker.

Setup checkpoints `100`, `110`, `120`, and `130` distinguish validator entry, module snapshot, harness snapshot, and exact retained dictionary completion. Checkpoint `230` is terminal validator success.

On Python failure, only a sanitized ASCII exception type (63 bytes maximum) and message (191 bytes maximum) are recorded. Control characters, quotes, and backslashes are replaced; traceback and private exception state are not captured. Cleanup still decrements all held Python objects, zeroes copied bytes, finalizes/unloads the runtime, proves module absence, rechecks all 137 retained rows and all fixed subjects, and commits one terminal record. There is no retry.

## Downstream owner routing

The downstream owner for a genuinely accepted body-engineering result is the Avatar Builder reusable method/template layer. Routing is conditional: only a later independently accepted result with actual Blender, save, and render evidence may be integrated as a reusable method or template. A rejected result may contribute only a `DO_NOT_REPEAT` test. V3r24 is pending a different static audit, supplies no Blender/save/render evidence, integrates no body, and grants no owner-routing or body-claim authority.

## Stop-before boundary

No bootstrap, broker, process, AFES, Blender, body, save, render, or export authority exists here. Static author build and analysis do not establish a body result, acceptance, production authority, or permission to execute. A different audit must independently rehash the final seal and may reject the candidate. Until that exact-byte review accepts it, execution authority remains **NONE**.
