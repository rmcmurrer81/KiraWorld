# Battleground Capture-Flag Notebook World

## 2026-07-06 Repair Status After Live Test

The first playable prototype exposed the battlefield in Home World and had unsafe Stormtrooper scale. The current runtime repair keeps the CTF battlefield isolated and hidden until the CTF notebook world is active.

- Home World entry is still the billboard wall by the strip-mall parking lot.
- The Home World road was extended near the strip mall, and parking/road surfaces are grass-avoid zones.
- The parked car now uses Robert's supplied `back_to_the_future_time_machine_reference.glb` when it loads; the block fallback hides afterward.
- The battlefield bounds are much larger, with additional streets, alleys, ruins, cover walls, and far random flag spawns.
- Current enemy count is 11: six Stormtrooper patrols/guards and five Daleks.
- The Dalek GLB is usable. The Stormtrooper GLB currently reports giant unsafe bounds and is suppressed at runtime, with a life-size rounded fallback Stormtrooper shown instead.
- NPCs block the player and only tag from a real close chase check. Observe/Follow mode is ignored by enemies so Robert can watch without being tagged.
- The Observe / Follow UI button and `tools/observe_kira_life_loop_report.py` support long evidence reports with screenshots and JSONL samples.

Latest verification:

```text
node --check preview/src/main.js passed.
python -m py_compile tools/observe_kira_life_loop_report.py tools/kira_world_shell_server.py passed.
npm.cmd run build passed; existing Vite large-chunk warning remains.
CDP smoke confirmed Home World idle hides the battlefield, CTF entry starts seeking_flag, flag spawn randomizes, npcCount=11, imported car is visible, Dalek GLB attaches, and Stormtrooper GLB is suppressed for unsafe scale.
```

## 2026-07-06 Playable Home World Prototype

Implemented in the Home World preview runtime:

- Home World entry is a small parking lot beside the strip mall on the far side of the public library.
- The lot includes parking stripes, Robert's supplied time-machine reference car when the GLB loads, and a wall billboard that says "Play Capture The Flag."
- Walking into the billboard wall teleports the player to the capture-flag battlefield notebook-world zone.
- The battlefield has base camp, streets, perimeter walls, ruined/torn buildings, rubble, cover walls, a random glowing flag spawn, and a Kira World return billboard.
- The return billboard near base camp sends the player back to Home World.
- Stormtrooper and Dalek smart NPCs patrol, chase within sight range, and tag the player/active body back to base.
- Peter/Gwen/Marinette active bodies can start `capture_flag_game` through `window.kiraBodyPractice.startSkill("capture_flag_game")`.
- The active-body run uses jog, run, dodge, flag pickup, and base return phases.

Current staged runtime assets:

```text
Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/public/models/capture_flag/back_to_the_future_time_machine_reference.glb
Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/public/models/capture_flag/stormtrooper_rigged_game_ready.glb
Data/world_builds/notebook_worlds/home_world/builds/home_world_main_house_20260630_223000/preview/public/models/capture_flag/bronze_new_series_dalek_-_rigged.glb
```

Verification:

```text
Headless Edge monitor confirmed:
  portal billboard=1, return billboard=1, parked car=1, first prototype enemy roster observed
  current repaired runtime verifies npcCount=11
  home billboard teleported to the battlefield
  Kira World return billboard teleported back home
  Peter loaded and completed capture_flag_game
  observed actions: jog, run, dodge, idle
  final phase=won, captures=1, tags=0, dodges=1
```

## Purpose

Create a large optional game notebook world where Robert and invited AIs can practice movement, evasion, teamwork, and route planning without affecting home-world autonomy.

## Core Loop

- A flag spawns at a random far-side objective point.
- The player or allied AI must reach the flag and return it to the home base.
- Stormtroopers and Daleks patrol the arena and try to tag players.
- A tag resets the tagged player or AI to the starting area after a short cooldown. No harm, death, or injury state is used.
- Successful capture logs route time, near misses, recovery behavior, and cooperation events.

## Staged Assets

- Stormtrooper prototype: `Assets/third_party/intake/3d_models_kira_world/characters/stormtrooper/stormtrooper_rigged_game_ready.glb`
- Dalek prototype: `Assets/third_party/intake/3d_models_kira_world/props/dalek/bronze_new_series_dalek_-_rigged.glb`

## Temporary Access

- Use a home-world billboard portal until the TARDIS call and console workflow is reliable.
- The billboard should show the battleground theme and clearly promise the capture-the-flag game.
- A return billboard must exist at the safe base so Robert and invited AIs can leave without needing the TARDIS.
- Each billboard trip logs a travel-training example for later TARDIS learning.

## Build Requirements

- Wide terrain with clear base zones, cover, paths, and visible boundaries.
- Navmesh-safe spawn points so no one starts inside geometry.
- Collision capsules for every moving character.
- Patrol behaviors that use path waypoints first, then line-of-sight chase only inside a fair range.
- Scoreboard for captures, tags, elapsed time, and best run.
- Difficulty gates for patrol count, speed, tag radius, and flag distance.
- Run locomotion for Robert, allied AIs, and any character invited to play.
- No root sliding: Spider-Man, Spider-Gwen, and other rigged bodies must either use authored run/walk clips or the generic procedural fallback before joining the game.

## NPC Rules

- Stormtroopers and Daleks are smart NPCs unless promoted to full AIs later.
- Guard NPCs stay near the flag until they see a player or allied AI.
- Patrol NPCs follow waypoint loops and alert nearby NPCs when they see a player.
- A sighting sends nearby NPCs to the last seen position, not directly to an unfair perfect chase.
- A tag sends the player or allied AI back to the safe start point after a short cooldown.

## AI Learning Signals

- Reward forward progress toward flag and base.
- Reward obstacle avoidance and successful route replanning.
- Penalize stuck states, repeated collisions, teleport recovery, and path loops.
- Compare the AI's declared intention with actual body position and held object state before crediting a successful action.

## Notes

This world should stay separate from the home world until the avatar controller and object-level collision are stable. It is a training/game notebook, not the main life-session environment.
