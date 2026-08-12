# Louvre Solo Travel and Cell Streaming v1

Status: implementation scaffold; Louvre interior and Paris expansion are not complete.

## Refused-connection correction

`http://127.0.0.1:5183/` is a loopback address, not a permanent website. The
owner's screenshot showed `ERR_CONNECTION_REFUSED` because the previous test
server had been stopped. `Start_Louvre_Solo_Notebook_World_Test.bat` now runs
`tools/launch_louvre_solo_notebook_world_test.py`, which:

1. recognizes an already-running Louvre service only when `/healthz` returns
   the expected service ID, pinned build ID, `solo_review_only=true`, zero
   people, and zero minds;
2. otherwise starts only `tools/serve_louvre_solo_notebook_world_test.py` in a
   background process;
3. waits for the exact healthy response before opening the pinned bookmark;
4. leaves the browser closed and reports log paths on failure.

It does not start or stop Home World, TemporaryAI, voice, Ollama, or the Kira
World Shell.

## TARDIS owner-review destination

`Data/world_access/tardis_destinations/louvre_solo_owner_review.json` is listed
by the TARDIS gateway as an owner-review route, not as a completed location.
The route is Robert-only, forces `solo=1&bookmark=arrival_scale`, and keeps
activated-person travel disabled. The Kira World Shell's Louvre URL now also
forces the solo query. No person is activated by choosing or loading it.

The reviewable scope is still the Cour Napoleon exterior prototype. Entrance
doors are visible approximations but are not working doors. The exact descent,
stairs, escalators, elevators, reception, galleries, rooms, and artwork remain
unbuilt and cannot be claimed complete.

## Cell-streaming contract

`louvre_cell_streaming_contract.json` divides future work into:

- Cour Napoleon exterior;
- Pyramid entrance/door transition;
- under-Pyramid level -2 circulation;
- Richelieu, Sully, and Denon gallery zones.

The policy uses per-presence proximity interest sets, a union of those sets in
a shared notebook world, a smaller load radius than retain radius for unload
hysteresis, and a bounded number of active cells. Unbuilt cells have no bounds
and no runtime binding, which prevents a loader from treating guessed geometry
as a usable cell. Artwork must be a reviewed child inventory of a gallery room,
not a globally eager collection.

`Core/notebook_world_cell_streaming.py` validates these rules and produces
load/retain/unload plans. `src/louvre_cell_streaming.js` is the matching browser
scaffold. The existing exterior is truthfully labeled as a legacy eager cell
pending module extraction; therefore this pass establishes the contract and
failure gates but does not yet prove lower memory use.

## Promotion gates

An interior cell becomes loadable only after source review, geometry/scale
review, working collision and two-way portal tests, and owner approval. Vertical
transport needs motion, collision, arrival, and return tests. Gallery cells also
need a room-specific artwork inventory and rights/provenance review. A door
animation by itself never proves that the destination cell is ready.
