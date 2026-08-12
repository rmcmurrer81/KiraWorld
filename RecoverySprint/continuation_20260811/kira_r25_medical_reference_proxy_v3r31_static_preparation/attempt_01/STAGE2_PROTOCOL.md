# V3r31 two-stage authority and execution protocol

Status: `STAGE1_STATIC_ONLY_NO_EXECUTION_AUTHORITY`

V3r31 intentionally does not solve the audit-anchor cycle with another
replaceable TSV plus sibling digest. Stage 1 contains the complete worker,
proxy specification, normalized frame, materializer, and native anchor source,
but the compiled template is hard-disabled with `V3R31_MATERIALIZED=0`.

## Stage 1 and Audit A

A different reviewer rehashes the exact Stage 1 seal, all 34 direct V3r30
author/rejection rows, all 33 nested V3r29 rows, all 28 deep V3r28 rows, all
17 deepest V3r27 rows, the
exact Blender executable, and all static/build/hostile evidence. Audit A
may either reject or issue only:

`ACCEPT_STAGE1_FOR_STAGE2_MATERIALIZATION_ONLY_NO_BLENDER_AUTHORITY`

Audit A cannot authorize Blender or the worker. It must publish a canonical
artifact manifest that binds every Audit A file, exact auditor identity, exact
Stage 1 subject root, exact Stage 1 seal SHA-256, exact complete all-files
inventory root, and exact decision. Every JSON field uses an exact type;
Boolean/integer aliases, floats, numeric strings, and coercions refuse.

## Separate ProgramData install authority

Audit-A acceptance alone does not permit the ProgramData write. A different
reviewer, distinct from both author and Audit A, must publish a separately
manifested install-authority decision at the exact sealed Kira evidence path.
Root externally supplies its exact manifest SHA-256 and auditor ID. The
decision binds Audit A, the exact absent target
`C:\ProgramData\KiraV3r31AuthorityLedger`, the exact current ProgramData DACL,
the observed access-denied `FILE_DELETE_CHILD` probe, exact final read-only
file DACL, exact final append-only directory DACL, both canonical DACL
readbacks, mandatory `NtCreateFile`/`RootDirectory`-relative directory and file
operations, and ceilings of one directory creation and one materialization.
It grants no native-build or Blender authority and records that its auditor
created no ProgramData object. The materializer binds all four exact
install-authority files into the generated native header. Any absent, changed,
unbound, same-reviewer, wrong-type, or path/DACL-mismatched evidence refuses
before directory creation.

## Deterministic Stage 2 materialization

Only after Audit A and the separate install-authority decision may root run the
sealed materializer. Before any generated package write it attempts to open
`C:\ProgramData` with `FILE_DELETE_CHILD` and
requires access-denied; it also requires the exact sealed DACL SDDL. Access
success, an ambiguous failure, or a changed DACL refuses. It
then holds that exact non-reparse anchor without delete sharing. It calls
`NtCreateFile` with that held anchor as `RootDirectory` to atomically create
the exact top-level `KiraV3r31AuthorityLedger` directory with its final
append-only Owner-Rights DACL. It grants the owner read, traverse, and add-file
only, not add-subdirectory, delete, delete-child, or `WRITE_DAC`. A name
collision routes only to a handle-relative read/traverse open whose identity and canonical DACL must
match. It then calls `NtCreateFile` relative to the held directory to
atomically create a deterministic single-link non-reparse consumed-authority
record with its final read-only Owner-Rights DACL, flushes and reads it through
the same retained handle, and verifies both canonical DACL readbacks. The
creation handles retain their already-requested access even though later
materializer reopens request only read/traverse. The anchor parent does not grant same-user
delete-child and the protected ledger file grants only read after consumption,
so extra directory child creation cannot remove, replace, or reset the exact
deterministic ledger, and the fixed pathname cannot be reset merely by closing
handles. The held identities
also resist replacement, junction/directory swaps, and reset throughout the
transaction and are revalidated after atomic publish. Administrator
take-ownership and disk rollback remain outside the software boundary. It
accepts exactly the
new scratch destination
`C:\Users\robmc\Documents\Codex\2026-08-11\c\work\body_v3r31_stage2_materialized_attempt_01`;
an existing or alternate destination refuses. It stages privately, rechecks
both immutable inputs, and atomically publishes that directory. The generated
native header embeds:

- Audit A's exact manifest and decision hashes and exact auditor identity;
- the exact Stage 1 subject root, seal SHA-256, all-files root, and every exact
  Stage 1 file;
- the exact durable materialization-consumption record;
- every exact V3r30 author/rejection row, nested V3r29 row, deep V3r28 row,
  and deepest V3r27 row;
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

Before launching the child, native first creates and retains the exact
`outputs/worker_staging` directory without delete sharing and then exclusively
pre-reserves all seven staging files: the `.blend`, four renders, worker
result, and worker receipt. Each must be an empty, unique, regular,
single-link, non-reparse object at its exact final path. Native retains all
seven handles without delete sharing across Blender, finalization, durable
`SUCCESS_CONSUMED`, and terminal revalidation. The capability binds those
facts. Each file handle requests `GENERIC_READ|READ_CONTROL|WRITE_DAC`; the
directory handle requests
`FILE_ADD_FILE|FILE_ADD_SUBDIRECTORY|FILE_READ_ATTRIBUTES|READ_CONTROL|WRITE_DAC|SYNCHRONIZE`.
Before Blender, native applies the exact protected Owner-Rights transaction
DACL to all eight objects and reads back canonical SDDL
`D:PAI(A;;FA;;;SY)(A;;FA;;;BA)(A;;0x12019f;;;OW)` from all eight. The cache-free
hostile suite reproduces V3r30's status 5 for both old access masks, then proves
both V3r31 masks set and read back the canonical DACL. The DACL preserves owner
read/write needed by Blender while withholding target read-attributes access
required to add a current-user hard link; SYSTEM and Administrators retain
recovery rights. The worker refuses unless all seven exact identities already exist;
it writes each through the pre-reserved object and rechecks identity and link
count before and after save, reload, render, and receipt writes.

Native also pre-reserves the final `.blend`, four final render paths, worker
result, worker receipt, and native final manifest with stable file identities
and no write/delete sharing. After the child exits, native validates and hashes
the already-held staging objects without reopening their pathnames, copies them
through the already-held final handles, and keeps all seven worker plus all
eight final handles open through durable `SUCCESS_CONSUMED` and terminal
path/identity/single-link/size/hash revalidation.

The worker validates the factory-empty runtime, all eight normalized landmark
gates, each of nine proxies before save and after both reloads, six exact
materials, complete scene/data closure, exact camera matrices, decoded 640x640
PNG content, four distinct views, and final output hashes. A future successful
run would still prove only an isolated normalized clinical reference-proxy
scene, never Kira's completed or functional body.

## Preserved downstream owner requirements

V3r31 does not implement or weaken the later goal for medically realistic
adult external and internal anatomy. Later body stages also require
evidence-based regional tissue/material variation: skin is not one flat color,
and lips, nipples, and other tissues require their own supported materials. The
bald version remains the first activation candidate; a separate hair version
is retained inactive until the planned RAM upgrade. Nothing from V3r31 may be
given to Avatar Builder as a template unless both independent audits and actual
Blender/save/reload/render evidence accept the bounded result.
