# Resident-media voluntary gate V13 different fresh static audit

Recorded UTC: `2026-08-11T10:13:47.3992896Z`

Decision: `REJECT`

## Outcome

The different reviewer rehashed all 10 sealed V13 subjects before and after
review with zero drift. Strict compile passed 2/2, the focused V13 author suite
passed 15/15, and the preserved V3–V13 suite passed 191/191. The intended
missing-role, exact-type, numeric-digest, and completion checks work through
the untouched public path.

V13 is nevertheless rejected because three ordinary in-process bypasses reach
or alter the actual commit path:

1. the returned object exposes its rejected V12 ledger as `_inner`, and the
   inner V12 method commits incomplete evidence when called directly;
2. V13's runtime preflight and imported V4/V9/V12 code are not exact-identity
   bound, so rebinding the preflight commits incomplete audio;
3. rebinding the exact-type walker permits boolean identifiers and an integer
   decoder digest, reproducing the V12 alias failure.

The exact decision and reproductions are recorded in `AUDIT_DECISION.json` and
`HOSTILE_PROBES.md` in this directory.

## Current truth

- V13 is not accepted, promoted, live, or production-authorized.
- No evidence says that any synthetic person saw, heard, selected, enjoyed,
  learned from, preferred, or remembered media.
- No live media/model/device/person/audio/video/body/Blender/Sarah operation ran.
- The production opener remains default-off and refusing as written, and the
  reviewer found no production route to it.

## Required next step

Preserve all V13 bytes. V14 must be append-only; it must prevent access to the
rejected V12 commit surface, enforce completeness and exact types at the actual
commit point, externally bind exact V13/V12/V9/V4 execution identities and
state, and revalidate immediately before commit and after readback. V14 remains
disconnected/default-off and requires another different fresh audit. Static
acceptance would not be a live media experience.
