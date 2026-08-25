# Avatar Builder Blender Pre-Import Controller Boundary — 2026-08-25

Status: **STATIC CONTROLLER VERIFIED; NATIVE EXECUTION BOUNDARY OPEN; BLENDER MUST NOT START**

This record describes a reusable, fail-closed controller boundary. It does not
authorize Blender, build or accept a body, assign a carrier to a person, author
anatomy, save or render a Blend, activate a runtime person, or publish an asset.

## Authority relationship

The controller is subordinate to all current person, maturity, privacy, body,
carrier, and test-execution gates. In particular:

- Kira remains on the R25 foundation-first lane. The qualified continuous
  MakeHuman adult-female foundation is topology authority; R19 is
  non-pelvic appearance evidence only; AFES remains locked.
- The current MakeHuman rigged-carrier configuration remains
  `PREPARED_NO_BLENDER_AUTHORITY` and generic, bald, identity-neutral,
  internal-anatomy-free, inactive, and private.
- Synthetic Robert remains a distinct body lane with unresolved maturity.
  This controller creates no adult/private curriculum or body authority for
  that lane.
- The Robert user-avatar remains a third, private, distinct body artifact and
  is not shared training material.
- The current test-execution boundary still forbids Blender launch, body work,
  save/reload/render, activation, and promotion without a separate exact
  authorization.

## What is now verified without Blender

`Core/avatar_blender_preimport_controller.py` provides and tests:

1. strict typed run identifiers, artifact roles, JSON, and bounded sizes;
2. exact Blender, bundled-interpreter, worker, configuration, and per-run
   authorization SHA-256 bindings;
3. the fixed argument grammar
   `blender --background --factory-startup --disable-autoexec --python WORKER -- --config CONFIG --authorization AUTHORIZATION`;
4. a freshly constructed six-entry Windows environment containing only
   `SystemRoot`, `WINDIR`, `ComSpec`, `PATH`, `TEMP`, and `TMP`;
5. held single-open file hashing and stable file identity;
6. Windows read-only share mode that denies new write/delete opens while the
   held descriptor remains alive;
7. atomic create-new, file-flushed one-run claim records with claim-hash
   revalidation before terminalization;
8. atomic create-new terminal outcomes with stable reason codes and no
   absolute paths or raw exceptions;
9. replay denial across independent processes while the stable claim root and
   records remain untampered; and
10. a Windows OS process-image query and held-file identity comparison helper
    for a future native provider.

The exact local Blender 5.1 evidence is recorded without a private machine
path in
`Avatar/avatar_builder/tooling/blender_5_1_preimport_controller_boundary_v1.json`.

## Why execution remains blocked

The Python controller deliberately has:

- `EXECUTION_TRUST_BOUNDARY_CLOSED = False`; and
- an empty `REVIEWED_NATIVE_PROVIDER_IDS` set.

Even a valid preflight therefore ends as
`BLOCKED_NATIVE_BOUNDARY_REQUIRED`, with `process_started=false`.
An unreviewed provider object is never called.

Python can hold final files and produce a normal atomic ledger, but this does
not prove the entire Windows launch transaction. A pathname or ancestor may
still be exchanged around a Python path operation, and a file-only share hold
does not by itself close the real current-user hard-link and staging races.
The OS process-image helper compares the reported image to the still-held file
identity and digest, but it does not create or control a suspended child and is
therefore not alone a complete launch proof. It queries by PID; the reviewed
native provider must instead retain and verify the exact process handle it
created so PID reuse cannot substitute another process. The Python command uses
resolved current paths, but only the native provider can derive and retain the
final held-handle path and ancestor identity through launch.
The one-run ledger is file-flushed within a stable root, but Python does not
make the closed records immutable against deletion or rewrite by the same
account and does not prove the parent directory entry flush. It is not
execution authority until the root, records, and every ancestor are held and
protected by the native boundary.

## Exact native boundary still required

A separately reviewed Windows provider must, before this guard can change:

1. accept only the versioned provider interface and exact argument grammar;
2. open and hold Blender, bundled Python/runtime, bootstrap, workers,
   controller, config, authorization, source, and all build inputs without
   write/delete sharing;
3. open and hold every existing ancestor directory, reject UNC and reparse
   traversal, and bind final NT path, volume identity, file ID, regular-file
   type, link count, byte length, and SHA-256 from those handles;
4. create a share-zero, create-new, write-through pending claim and flush it
   before any child exists;
5. use `CreateProcessW` with exact `lpApplicationName`, a fresh Unicode
   environment, no shell, and `CREATE_SUSPENDED`;
6. place the process in a kill-on-close Job, verify the OS process-image
   identity against the held Blender file, and only then resume once;
7. keep all file, directory, process, job, claim, and output handles held
   through the build-and-audit transaction;
8. validate and hold new staging/output files before their names can be
   exchanged;
9. bound runtime and terminate the complete descendant tree on timeout; and
10. deny same-principal deletion or rewrite of claim and outcome records, and
    flush exactly one terminal result. A pending claim after abnormal death
    must remain permanently non-replayable.

The provider must pass real hostile two-process claim, pending-crash,
hard-link, junction, staging-name, environment-poisoning, argument-mutation,
process-image-mismatch, timeout, descendant-cleanup, and build-pass/audit-fail
tests. Static mocks are insufficient.

## Reusable Avatar Builder lesson

Avatar Builder may learn only the following verified rule:

> A worker's internal identity check is necessary but not sufficient. Before
> any Blender import or person/body work, bind exact files, sanitize arguments
> and environment, consume one durable run claim, hold identities through an
> OS-verified suspended launch, and write one terminal outcome. If a native
> link in that chain is unproven, record the block and start no process.

This lesson is a safety method. It is not evidence that a carrier or body was
built, accepted, assigned, functional, private-ready, or active.
