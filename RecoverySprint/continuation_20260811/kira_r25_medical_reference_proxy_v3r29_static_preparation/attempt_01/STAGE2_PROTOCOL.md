# V3r29 two-stage authority and execution protocol

Status: `STAGE1_STATIC_ONLY_NO_EXECUTION_AUTHORITY`

V3r29 intentionally does not solve the audit-anchor cycle with another
replaceable TSV plus sibling digest. Stage 1 contains the complete worker,
proxy specification, normalized frame, materializer, and native anchor source,
but the compiled template is hard-disabled with `V3R29_MATERIALIZED=0`.

## Stage 1 and Audit A

A different reviewer rehashes the exact Stage 1 seal, all 28 direct V3r28
author/rejection rows, all 17 transitive V3r27 rows,
the exact Blender executable, and all static/build/hostile evidence. Audit A
may either reject or issue only:

`ACCEPT_STAGE1_FOR_STAGE2_MATERIALIZATION_ONLY_NO_BLENDER_AUTHORITY`

Audit A cannot authorize Blender or the worker. It must publish a canonical
artifact manifest that binds every Audit A file, exact auditor identity, exact
Stage 1 subject root, exact Stage 1 seal SHA-256, exact complete all-files
inventory root, and exact decision. Every JSON field uses an exact type;
Boolean/integer aliases, floats, numeric strings, and coercions refuse.

## Deterministic Stage 2 materialization

Only after Audit A may root run the sealed materializer. Before any generated
package write it exclusively creates, flushes, and reads back a deterministic
consumed-authority record under
`C:\Users\robmc\Documents\Codex\kira_authority_ledgers\body_v3r29`. That
record is outside the removable generated package, so deleting or recreating
the generated destination cannot restore the authority. It accepts exactly the
new scratch destination
`C:\Users\robmc\Documents\Codex\2026-08-11\c\work\body_v3r29_stage2_materialized_attempt_01`;
an existing or alternate destination refuses. It stages privately, rechecks
both immutable inputs, and atomically publishes that directory. The generated
native header embeds:

- Audit A's exact manifest and decision hashes and exact auditor identity;
- the exact Stage 1 subject root, seal SHA-256, all-files root, and every exact
  Stage 1 file;
- the exact durable materialization-consumption record;
- every exact V3r28 author/rejection row and transitive V3r27 row;
- the exact worker, proxy spec, normalized frame, Blender executable, and
  runtime version expectations.

The materialized native launcher therefore cannot accept a newly recomputed
audit/package pair. Changing any embedded subject requires a different native
binary.

## Audit B and external executable anchor

A second different reviewer independently builds/analyzes and inspects the
materialized Stage 2 package, its PE imports/mitigations, stable-handle logic,
worker, and hostile suite. Audit B records the exact final executable bytes and
SHA-256 outside the executable; the executable does not parse a replaceable
Audit B decision pair.

Root must open the Audit-B-pinned executable with read access and read sharing
only (denying write/delete sharing), resolve and verify that handle's exact
final path/file identity/bytes/SHA-256, and keep that same handle open across
the sole `CreateProcess` call. Root also confirms every output is absent and
invokes once with no arguments from `C:\Users\robmc\Kira`. This handle-held
comparison closes replacement between preflight and process-image creation and
is the external trust anchor. The native launcher then opens and retains its
own image and all bound inputs without write/delete sharing before reservation.

Any mismatch, failure, interruption, timeout, torn ledger, partial output, or
ambiguity consumes that sole authority. Stage 1, Audit A, or materialization
alone never grants an invocation.

## Bounded Stage 2 operation

The native launcher alone owns reservation, the Job-contained suspended child,
timeout, capability, final output rehash, and the single fixed-size
`CREATE_NEW` outcome/receipt ledger. It launches only exact Blender 5.1.2 from
its sealed path/hash with:

`--background --factory-startup --disable-autoexec --python-exit-code 91 --python <exact worker> -- <exact capability>`

No input `.blend`, source asset, import, export, rig, weight, animation, live
avatar, activation, production promotion, network, voice, external camera
capture/device, general model service, or Sarah path is permitted. The four
sealed Blender evidence-camera views are the only camera use in Stage 2.

Before launching the child, native exclusively pre-reserves the final `.blend`,
four final render paths, worker result, worker receipt, and native final
manifest with stable file identities and no write/delete sharing. The worker
writes only into the separately held `outputs/worker_staging` directory. After
the child exits, native opens every staging object without write/delete sharing,
validates it, copies it through the already-held final handle, and keeps all
eight final handles open through durable `SUCCESS_CONSUMED` and terminal
path/identity/size/hash revalidation.

The worker validates the factory-empty runtime, all eight normalized landmark
gates, each of nine proxies before save and after both reloads, six exact
materials, complete scene/data closure, exact camera matrices, decoded 640x640
PNG content, four distinct views, and final output hashes. A future successful
run would still prove only an isolated normalized clinical reference-proxy
scene, never Kira's completed or functional body.

## Preserved downstream owner requirements

V3r29 does not implement or weaken the later goal for medically realistic
adult external and internal anatomy. Later body stages also require
evidence-based regional tissue/material variation: skin is not one flat color,
and lips, nipples, and other tissues require their own supported materials. The
bald version remains the first activation candidate; a separate hair version
is retained inactive until the planned RAM upgrade. Nothing from V3r29 may be
given to Avatar Builder as a template unless both independent audits and actual
Blender/save/reload/render evidence accept the bounded result.
