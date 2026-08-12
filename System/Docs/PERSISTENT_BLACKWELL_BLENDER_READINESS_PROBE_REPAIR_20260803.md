# Persistent Blackwell voice: Blender-readiness probe repair — 2026-08-03

Current status: **STATIC REPAIR VERIFIED; LIVE GPU ACCEPTANCE PENDING**

The persistent Blackwell candidate itself did not fail in Attempt 04. The
acceptance harness stopped before the candidate worker started because the
Windows `tasklist` readiness query returned `ERROR: Access denied`. That
failure remains preserved as Attempt 04; Attempts 01–03 also remain unchanged.

The acceptance harness now uses a narrow read-only, noninteractive PowerShell
`Get-Process -Name blender` query. It records only PID and process name. A
nonzero child result, invalid JSON, malformed process evidence, or probe
exception is not treated as absence: the query reports failure and the GPU
gate remains blocked. A detected Blender process also blocks the gate. The
probe cannot stop or modify a process and uses neither WMI nor CIM.

Focused mocked CPU/static verification covers:

- a successful zero-process result;
- one or more active Blender processes with exact PID/name evidence;
- nonzero exit, invalid JSON, and malformed schema;
- `require_no_active_blender()` success only for proven inactivity;
- fail-closed rejection of an active process or failed query;
- static exclusion of `tasklist`, WMI/CIM, and process-termination commands.

Results: 5/5 focused tests passed. The focused tests plus the existing
persistent candidate CPU/static suite passed 18/18. No real Blender query,
GPU/model operation, Ollama operation, synthesis, playback, Kira/person
operation, or process termination occurred during this repair.

The candidate config remains exactly
`54f219147d8b028c8488adf5ed60f883d5a528660bcec5e08b6b5fff3bc3a3d1`;
the sealed candidate worker remains
`5b36fc085ae5e536da27f079ec70cd2e26c842b266c3002079c56f875b5716a3`;
and the production routing manifest remains
`a343572b25937926ea0181274976b53f57ca219ce1e4d3e1780343994aea7b81`.
The one-shot Blackwell production preference and sealed CPU-only approved
fallback are unchanged.

Detailed evidence and rollback instructions are in:

`RecoverySprint/continuation_20260803/persistent_blackwell_blender_readiness_probe_repair/attempt_01/CHECKPOINT.md`

The next real attempt remains a serialized, operator-bound GPU gate. It must
not run alongside Blender or another heavy workload, and it will allocate a
new append-only attempt rather than alter Attempts 01–04.
