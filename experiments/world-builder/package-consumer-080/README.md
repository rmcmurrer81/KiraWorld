# Portable World consumer080 — experimental source backup

This additive snapshot preserves the reviewed desktop package consumer, including visible step, turn and look buttons, a nearby-door button that names its destination, and corrected animation timing. Click movement uses the existing collision and floor checks in short bounded slices. Door animation remains separate from walking, uses the same validated door runtime and can be interrupted. Nothing here teleports the viewer or relaxes package admission.

The first walking animation frame now establishes a frame timestamp baseline. Later invalid or reversed timestamps pause walking with an explicit Resume action. The preceding door fix similarly accepts a first frame whose timestamp precedes the click-time sample, while retaining its two-second and 120-frame bounds. Cancelled callbacks cannot rejoin a new walking session.

## Included source and package limits

`candidate/` contains exact frozen consumer080 source, six original Mars-history transcripts and the necessary vendored Three.js subset and MIT license. The loader retains its two exact reviewed package digests and the source, geometry, image-budget, door, interlock and navigation checks. **The private sample package and all exported scene data are excluded.** This source backup alone therefore provides no world to import or walk through. An arbitrary GLB is not admitted. Public usability has not been obtained by weakening the integrity gates.

The optional `serve.py` is an explicit local development utility; preparing this backup does not run it. No installed World Builder or Video Studio file is promoted by this snapshot. Original saved worlds and the older experiment folders remain separate.

## What was checked

The native desktop checks are recorded by revision, because they exercised different parts of the interface:

- **078:** ordinary visible controls traversed both pressure hatches and an ordinary door into the crew quarters. The habitat-only history entry appeared there and disappeared on return to the corridor. Four of the six chapters were individually opened and read. Close/Escape paused the interface; reopening retained the selected chapter. Two usability findings in door timing and target naming led to 079.
- **079:** a focused check confirmed that the button named the selected hatch destination and that single Open and Close requests animated to completion. A separately reproduced walking-clock error remained and led to 080.
- **080:** exact package import rendered the actual meshes and PNG textures. Start, Escape, Resume and Pause states worked. Two short click steps reached the named outer hatch, whose single Open and Close requests completed without a Continue retry. No warning or error was captured in this focused check.

The 080 browser check did not force animation timestamps or establish sustained physical-key walking. Those clock edge cases were tested with actual application modules and inert adapters. The unchanged quarters/history behavior has the separate 078 walkthrough, not a claimed repeat in 080. These checks are not owner visual acceptance, installation approval or a headset test.

## History and greenhouse boundaries

The library contains six written chapters with official NASA/JPL/ESA/JAXA links. Their content review is dated **September 26, 2026**; future mission schedules are plans, not guarantees or a live news feed. All six narration entries remain `null`. There is no generated narration, recorded audio, listening approval or completed audio experience. The original chapter drafts and source notes are preserved in the earlier [Mars history source snapshot](../mars-history-077/research/).

Opening the history library pauses walking and clears held input. It is available only in an admitted habitat room. Hidden pages, room exit, package changes and disposal suspend or remove it. Greenhouse louvers and readings remain session-local illustrative controls; mounted exported textures are saved snapshots. Door state shown by the controller is local state, not pressure, leak, seal or safety simulation.

`TESTS.md` describes the portable inert checks and what they omit. `SOURCE-INVENTORY.json` pins included files; `REVIEW-SUMMARY.json` separates independent source review from native observations. No private world package, owner or visitor data, local machine receipts, credentials, model weights or binary media is included. Finished XR interaction, headset approval and real audio remain outside this snapshot.
