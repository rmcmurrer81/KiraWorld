# Avatar Builder Blender 5.1 worker CLI compatibility boundary

Date: 2026-08-22
Status: `STATIC_CLI_REPAIR_TESTED_WORKERS_EXPLICITLY_NON_EXECUTABLE`

## Result

The inactive MakeHuman carrier builder and read-only pose auditor can now check the
Blender-reported launch binary through `bpy.app.binary_path`. They no longer mistake
Blender 5.1's bundled Python interpreter in `sys.executable` for the launched
Blender executable.

A read-only Blender 5.1.2 probe established:

```text
sys.executable       = <Blender installation>/5.1/python/bin/python.exe
bpy.app.binary_path  = <Blender installation>/blender.exe
sys.argv[0]          = <Blender installation>/blender.exe
background           = true
automatic script execution = false
```

The accepted Blender binary SHA-256 during the probe was
`1e6624af112b3c936f4b038b025ebd2bf00ae72c4b62881a6787166d71c58fa5`.
The executable hash remains checked by the exact one-run authorization. The
repair changes how the worker identifies the binary; it does not weaken or
replace the authorization hash.

## Shared worker gate

`Core/avatar_makehuman_rigged_carrier.py` provides the Blender-free
`validate_blender_worker_invocation` gate. Both carrier workers supply their
live Blender values to that shared gate.

The gate requires all of the following:

- exact background mode;
- one exact pre-worker argument grammar: `--background`, `--factory-startup`,
  `--disable-autoexec`, one `--python`, the canonical operation-specific worker,
  and one separator, in that order and with no extra script flags;
- exactly `--config <path> --authorization <path>` after the separator;
- automatic script execution reported as exactly disabled;
- `bpy.app.binary_path` resolving to a regular, singly linked, non-reparse
  file named `blender` or `blender.exe`;
- `sys.argv[0]` resolving to that same file;
- `sys.executable` resolving either to that Blender binary or to a
  version-shaped `python/bin` layout under the reported Blender installation;
  this is a compatibility check, not a hash or operating-system identity proof;
  and
- the unchanged downstream executable, config, source, controller, builder,
  auditor, and intersection-auditor hash bindings.

Ordinary Python, renamed binaries, an external or arbitrarily nested
interpreter, a substituted worker, extra `--python` or `--python-expr` flags,
reordered/missing/duplicate flags, altered worker arguments, a missing
separator, foreground mode, enabled automatic script execution, stale
configuration/code bindings, and executable hash drift all fail closed.

The output directory check is exact for each operation. A build preflight
permits only its bound configuration when colocated and its one authorization;
an audit additionally permits the exact carrier and build report. A preserved
rejection record, abandoned temporary item, prior output, or any other unbound
entry makes the attempt terminal and rejects a later use of that directory.

This is a static CLI parser and post-load drift-check repair, not a trusted
execution boundary. Python loads the named worker and its imported controller
and audit dependencies before any worker check. Ambient import-path shadowing
or already replaced code can therefore execute before a later hash mismatch.
The reported Blender path and bundled-Python-looking path are mutable process
state; ancestor junction integrity, the operating-system process image, the
bundled interpreter version, and the bundled interpreter hash are not proven.

The authorization is also not atomically claimed before Python import. A crash
before residue exists can leave the same authorization apparently reusable,
and concurrent starts can both pass the early static check. Directory residue
rejection is useful negative evidence, but it is not complete replay or
concurrency prevention.

For those reasons, `EXECUTION_TRUST_BOUNDARY_CLOSED` remains exactly false,
both workers call a fail-closed execution guard as their first `main` action,
and an authorization-present preflight reports
`PREFLIGHT_BINDINGS_VALID_STATIC_ONLY_EXECUTION_TRUST_BOUNDARY_OPEN`. Normal
source cannot build or audit a carrier through this package. A later version
needs a trusted pre-import launcher, operating-system process identity binding,
exact interpreter binding, and an atomic durable one-run claim with exclusive
concurrency and terminal completion/rejection records before a fresh audit may
consider one invocation.

## Test isolation repair

The carrier preflight tests now clone the tracked configuration into a fresh
temporary output root. They no longer assume that the real append-only carrier
workspace is empty and never remove preserved attempt evidence to make a test
pass.

## Avatar Builder lesson

Avatar Builder now has a reusable complete-body curriculum loader and an
idempotent synchronization command:

```text
py -B tools/sync_avatar_builder_complete_body_curriculum.py
```

The lesson is sourced from separate exact Kira and Synthetic Robert
complete-body matrices. The male user-avatar contract is bound only as a
private separation boundary and is never used as shared training material. It
preserves distinct Kira, Synthetic Robert, and Robert user-avatar lanes;
complete external/internal anatomy;
eating, drinking, digestion, bathroom and hygiene requirements; adult-only
private relationship and self-pleasure choice; conception, pregnancy,
recovery and family systems; physical skin/soft-tissue deformation; detachable
hair; separate clothing; and all truth boundaries. It keeps every current
implementation and acceptance claim false. The lesson carries a curriculum
digest, replaces a stale same-ID lesson, rejects corrupt existing memory, uses
an atomic same-directory replacement, and writes only to a final-explicitly
ignored resident memory path.

Kira's exact confirmed-adult evidence remains bound. Synthetic Robert has no
separate exact subject-bound adult classification in the current source set,
so his adult-male body requirements remain conditional design requirements;
adult curriculum delivery, private action, body construction, and activation
all remain blocked. Biological Robert's adulthood and similarity do not
transfer that classification.

## Scope boundary

This milestone did not create or approve a carrier, authorize another Blender
build, add Kira identity, add internal anatomy, add hair or clothing, activate
a body, perform a relationship or private action, control hardware, or permit
public body export. A future carrier run requires the missing trusted execution
boundary above, then a new run ID, new output directory, new exact
authorization, and the full build and pose-audit gates.
