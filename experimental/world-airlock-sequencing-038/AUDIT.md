# Primary Airlock read-only audit

The actual saved Mars geometry has SHA256
`1af9ae1254356f0523f722d284b140b8e34eb6af3bf236ceef91ad5f145a9d75`.
Primary Airlock measures3×4×2.8m. `opening_1` links Equipment Vestibule to the
airlock at z=-4; `opening_2` links the airlock to circulation at z=0. Both portals
are1.2m wide and2.2m high. The moving leaves are1.16m wide,2.175m high and0.065m
thick, with clearance around the frame. These are navigation closures; the
authored scene contains no verified gasket/latch seal or pressure/leak model.
Both connections are interior. There is no exterior EVA portal.

With the installed controller and a walker at [1.5,0,-2], both opening requests
are accepted without advancing time. Eight0.05s steps bring both leaves to fully
open. This was reproduced in memory with the actual source, without writing it,
opening a preview or running a model. `ACTUAL-AIRLOCK-RESULT.json` records the
candidate's contrasting sequencing result without including private source files.

NASA's [Quest Airlock description](https://www.nasa.gov/international-space-station/quest-airlock/)
distinguishes an equipment lock and a crew lock that provides the exterior exit,
separated by a hatch. ESA's [22 November2019 spacewalk log](https://blogs.esa.int/luca-parmitano/2019/11/22/spacewalk-latest-updates/)
describes closing the inner hatch before depressurization and opening the outer
hatch, then closing the outer hatch and repressurizing before opening the inner.
These primary references support separating door sequencing from pressure work.
They do not establish that this procedural Mars layout reproduces Quest or
implements a qualified airlock.

The smallest bounded correction is mutual exclusion of the two authored doors.
Exterior access, pressure simulation, credible seals and emergency procedures
would require separate geometry, behavior and validation.038 implements only
the sequencing correction and labels that limit explicitly.
