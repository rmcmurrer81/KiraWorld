# V3r31 independent Audit-A rejection

Recorded UTC: `2026-08-12T03:50:00Z`

Verdict: `REJECT_AUDIT_A_NO_STAGE2_MATERIALIZATION_OR_BUILD_AUTHORITY`

The exact installed V3r31 package rehashed `26/26` and its installed
cache-free `PostSeal` suite passed. Its exact upstream chain reports `112/112`.
Those positive results do not cure the independent blocking reproduction.

V3r31 applies worker transaction DACL
`D:P(A;;FA;;;SY)(A;;FA;;;BA)(A;;GRGW;;;OW)` and claims that it withholds the
target right required for a current-user hard link. A test-owned Windows probe
applied that exact DACL and independently observed:

- an inside-directory hard link was created;
- an outside-directory hard link was created while the source file remained
  open with `FileShare.Read` and therefore without delete sharing;
- the outside alias was deleted while that source handle remained open; and
- the source returned to an observed hard-link count of exactly `1`.

This is a transient-alias gap. A same-user process can create an alias outside
the protected directory, use it to modify the held staging object, delete the
alias, and restore the point-in-time link-count invariant before the native
code rechecks it. No Stage-2 materialization, ProgramData authority creation,
native product run, Blender, `bpy`, worker, body, save, reload, render,
activation, audio, camera, model, or Sarah route was invoked.

V3r31 is rejected and must not run. Append-only V3r32 may proceed only in
scratch/static work and must not treat no-delete-share plus link-count polling
as sufficient proof against transient external aliases.
