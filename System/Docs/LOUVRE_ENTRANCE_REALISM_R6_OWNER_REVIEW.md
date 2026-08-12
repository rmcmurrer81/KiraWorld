# Louvre entrance realism R6 owner-review handoff

Date: 2026-07-16

R6 is the first isolated review that combines R5's supplied-model exterior
context with one R4-style transactional entrance/circulation transition. It
does not replace R4 or R5 and does not change Home World or TARDIS metadata.

## Runtime identity

- Build: `notebook_world_louvre_entrance_realism_r6_20260716_203000`
- Service: `louvre_entrance_realism_solo_owner_review`
- Protocol: `louvre_real_model_entrance_owner_review_r6`
- Port: `5196`
- Launcher: `Start_Louvre_Entrance_Realism_R6_Owner_Review.bat`
- URL: `http://127.0.0.1:5196/?solo=1&bookmark=arrival`

## Proven in this bounded review

- The two exact R5-derived GLB binaries load with their pinned hashes.
- Arrival keeps only the real-model exterior cell resident.
- Door approach loads the entrance but cannot load the lower cell by distance
  alone.
- Operating the entrance explicitly authorizes and validates the lower
  collision cell before the leaves can become passable.
- Closed threshold rejects crossing; validated/open threshold accepts it.
- Forty intervals plus both endpoints ground monotonically from 0 to -8 m and
  back on the approximate spiral.
- A non-door Pyramid boundary, the guarded opening, and lower-lobby scope wall
  remain solid/fail-closed.
- Far travel unloads entrance and lower cells, captures both states, expires
  portal authorization, and safely restores an open leaf as non-passable until
  the destination is validated again.

## Still explicitly unproven and locked

Entrance dimensions and placement, mechanism, lower-level elevation, stair
geometry, lobby geometry, materials, lights, and alignment are approximate.
There are no elevators, escalators, galleries, rooms, artwork, accessibility
routes, security/ticketing systems, people, minds, voice, or complete Louvre
interior. The smoke proves this review implementation, not the actual Louvre.

Do not auto-expand from R6 into galleries or transport. A future step needs a
separately sourced, rights-reviewed, eye-level interior/entrance asset or
measured plan for a named cell before replacing any approximation.

Full evidence:
`Data/codex_reports/20260716_louvre_entrance_realism_r6_owner_review.md`.
