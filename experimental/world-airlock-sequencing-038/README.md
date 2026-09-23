# Experimental paired airlock door sequencing038

This isolated candidate prevents the two doors of an explicitly authored airlock
from opening together. It changes only `walk_controller.mjs`; the existing viewer
already displays the returned reason, including the adjacent destination. It is
not installed and no saved preview has been refreshed.

The authored `functional_program` must mark the room as `airlock`. Names and room
IDs do not opt a room in. The room must have exactly two supported moving doors.
An open, moving, pending or occupancy-held peer blocks an opening request, even
before its first animation frame. Closing keeps the existing reach, movement and
occupied-swing rules. A shared door observes every authored pair it belongs to.
Door state stays local to this preview session.

Validation:16 sequencing checks,33 generic door/navigation checks, and3 read-only
checks of the actual saved Mars source pass. The installed baseline opened both
actual airlock doors together; the candidate blocks that case and permits the
other door after closing. Geometry bytes, all116 protected original files and the
installed frontend remain unchanged. The existing viewer callback/message code
was exercised headlessly; no native/browser visual review was performed.

Run `node test_airlock.mjs` and `node test_generic_doors.mjs` for CPU fixtures.
`check_saved_airlock.mjs` takes an explicit geometry path and SHA256; original
saved geometry is deliberately not bundled. The generic test inherited a stale
2m reach assertion: both installed and candidate controllers use2.25m. Only that
test's out-of-reach point was corrected to2.3m; see the correction receipt.

## Limits and upgrade implications

This is door sequencing, not a pressure seal, leak check, pressure cycle, emergency
procedure or working exterior EVA access. The saved Mars airlock has two interior
connections and no exterior portal. Furnishings and visual realism are unchanged.
The contract is `preview_hinged_doors_v2`, with pairing policy
`paired_airlock_door_sequence_v1` exposed through the read-only `interlocks()` API.

An installed upgrade would create a new immutable preview build through the
existing refresh path. Old saved previews must retain their original controller.
Frozen036/037 mesh export evidence uses the earlier controller.037 correctly
rejects a preview with this new controller pin. Before exporting the new behavior,
a successor exporter must carry the pair policy and validate door ownership and
roundtrip behavior; merely changing its accepted digest would be insufficient.

`INSTALL-PLAN.json` is a proposed exact one-file change for root review. Installation,
new preview creation, visual review and an export successor remain separate work.
