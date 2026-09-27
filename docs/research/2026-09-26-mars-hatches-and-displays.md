# Mars habitat: pressure hatches, outside views and useful displays

Research and design revision, 26 September 2026. Robert accepts the current ordinary doors for most rooms, but requests airlocks that visibly seal and research from real systems and film/television. He also asks why the base does not show planetary information or the exterior. This document is an implementation brief, not evidence that these changes are installed.

## What the existing preview actually establishes

Root opened the exact immutable World063 preview in the permitted in-app browser after the original Computer Use tool recovered. Browser traversal demonstrated the first door opening, passage into the airlock, refusal to open the inner door while the outer door remained open, outer closure from inside, the near-swing obstruction guard, and subsequent inner opening. These are real browser observations, separate from the earlier CPU export and collision checks. The chamber still uses ordinary blue-panel doors and pull handles. It has no pressure or latch simulation. Robert's assessment is improved but unfinished, not visual approval.

The saved layout is equipment vestibule → airlock → circulation, with other rooms off circulation. Do not silently equate the equipment vestibule with the Martian outdoors: it is a modeled interior room. An outside pressure zone and an exterior connection must be explicitly designed before claiming an exterior EVA cycle. No saved room program or owner world is to be rewritten automatically.

## Real systems: principles to adapt

NASA's human-system architecture requirements distinguish positioning a hatch closed from securing its latches. They call for separate deliberate unlatching actions, operation from either side, pressure equalization, visible differential pressure and closure/latch indications, and suitable passage for suited crew and equipment. A closed mesh plus a green light does not establish those functions. Our proposed interface should expose clear, separate states and keep the opening clear. [NASA, section 8.4](https://www.nasa.gov/reference/8-0-architecture-vol-2/)

Quest separates equipment support from the crew lock used for EVA. This is a useful functional distinction: the equipment area needs storage and suit preparation; the changing-pressure compartment needs pressure equipment and controlled hatches. It is not merely a corridor given an airlock label. [NASA Quest](https://www.nasa.gov/international-space-station/quest-airlock/)

NASA's historical hatch survey describes pressure seals, mechanisms that compress them, manual actuation from both sides and different inward/outward opening arrangements. The chosen swing depends on the design and operating conditions; not every real hatch is round or inward opening. The report's Shuttle examples include separate seal barriers and inspection/test provisions. We will borrow the visible relationship between a seat, gasket and positive latch, without copying spacecraft dimensions or representing a game asset as engineered hardware. PDF text was retrieved; the web screenshot service failed, so its diagrams were not visually reviewed. [Historical hatch survey, sections 1.7–1.8](https://ntrs.nasa.gov/api/citations/20100027421/downloads/20100027421.pdf)

ESA's ATV account describes checking the inter-hatch area, closing hatches, controlled depressurization and checking for leakage. It supports an explicit sequence and inspection step, not instant pressure changes. It is a docking example, not a universal Mars EVA procedure. [ESA hatch closure](https://blogs.esa.int/orion/2011/06/19/hatch-closure-details-on-current-operation/)

Mars dust can compromise sealing surfaces. NASA's self-cleaning-seal work identifies increased leakage when dust accumulates. Show a cleanable gasket seat, protective lip and dust-control equipment; do not put decorative grime directly across the sealing face. [NASA seal research](https://technology.nasa.gov/patent/KSC-TOPS-101)

## Film and television: visual references, not mechanical proof

**The Martian:** Marc Homes' production portfolio was opened in a real browser. The exterior airlock set photograph shows a substantial layered circular opening, surrounding structural fittings and a distinct cylindrical chamber. Its suit-room and other airlock images are identified in the portfolio, but not all were visually inspected. This supports giving the chamber a recognizable structural identity. Do not copy the set or include its images in the shipped world. [Marc Homes portfolio](https://www.marchomes.org/the-martian)

**The Expanse:** Khanh Quach's season-four interior-airlock render was viewed in the browser. It uses a heavy shaped aperture, reinforced wall faces, recessed equipment and integrated lighting. These make the space look different from an office passage. The render does not prove a working seal or pressure sequence. [Khanh Quach portfolio](https://www.khanhquach.com/emily-london)

**Dark Matter / Stargate production experience:** SYFY's gallery quotes the production team explaining the move toward sideways-sliding airlocks, partly because vertical doors bounced during filming. It also documents the move from narrow circular concepts toward broader, heavier forms. This is a useful reminder to distinguish cinematic styling and set practicality from real engineering. [SYFY production sketches](https://www.syfy.com/dark-matter/photos/dark-matter-season-1-concept-sketches)

These sources supply reference and analysis only. No third-party design image, franchise branding or model has been copied into product assets.

## Original hatch design for this base

Keep ordinary interior doors for living spaces. Introduce a separate pressure-hatch recipe selected by the explicit airlock role, not by searching a displayed room name.

- A substantial rounded-rectangle structural frame, recessed seating flange and continuous dark gasket path. The hatch overlaps its seat when closed; there must be no visible through-gap at the seal.
- A reinforced leaf with beveled edges, hinges appropriate to its apparent mass, and distributed locking dogs engaging matching keepers. Include a readable latch mechanism on both sides. A grab bar is separate from the locking control.
- A small recessed observation port with modeled depth and a real view through the leaf, if the current geometry permits it. A blue rectangle painted on an opaque door is not a window.
- Clearly readable CLOSED / LATCHED / EQUALIZING / READY states, with text and symbols as well as color. Include a differential-pressure display and adjacent manual equalization control as an original visual design.
- Threshold, gasket, latch housing and door hardware participate in collision and clearance tests. Hardware moves with the correct leaf; the user's capsule must not clip it. Do not shrink the suited passage merely to fit more decoration.
- A chamber-specific finish: service panels, restrained piping, filters and protected lighting, with purposeful surface variation. Keep the gasket seat clean and use scuffs on exposed handles/floor edges rather than uniform noise everywhere.

The first deliverable should be one isolated hatch assembly inspected closed, partly open and fully open from both sides. Check its visual seal, latch contact, sill, window and actual passage before cloning it around the world. Reuse shared recipe geometry for preview and export so the two cannot silently diverge. This replaces neither the owner world nor the currently installed056 source until reviewed.

## Proposed behavior, separated from current capability

First model visible closed/unlatched/latched states and a deliberate latch action. The current physical obstruction guard must remain. Closing must not instantly label the hatch sealed; engagement must complete. An interrupted operation must retain a truthful state.

Pressure cycling is a later explicit fictional simulation: confirm both hatches closed and latched, choose a defined adjacent zone, equalize the chamber toward that zone, then permit deliberate unlatching and opening. Cancel, fault, loss of power and blocked motion need deterministic behavior. Do not allow simultaneous conflicting cycles or let a rejected button press mutate the pressure state. No fixed NASA threshold or timing is proposed here; gameplay values need an authored simulation contract and must not masquerade as hardware certification.

The current saved layout has no established exterior pressure-zone model. Until it does, displays must say pressure simulation unavailable rather than animate invented readings as though an exterior cycle had occurred. Hinge direction alone is not a seal, and a sliding design would still require seating/latching motion rather than merely sliding through the frame.

## Make Mars visible and understandable

The current entrance does not convey Mars. Review the existing observation recipe before adding duplicate windows; preserve its original Mars presentation binding and any already-authored exterior geometry.

Place a compact exterior-status display at the entry/airlock and a larger map/weather display in operations. Keep the observation room a destination with a clearly framed view and a sign visible from the corridor. The viewport should look through a genuine wall opening toward coherent terrain, sky and sunlight, not at a flat decorative image stuck on a wall. Frame depth and protective shutters are possible design additions; their strength/radiation performance is not simulated.

Use one shared fictional-base record for the displays: base name and site, local sol/time, outside pressure/temperature, dust/visibility, power/storage and hatch state. Clearly label authored scenario readings as simulated; do not call them live NASA weather. Show stale/unavailable for any future disconnected telemetry. A local terrain map can be original and labeled fictional; an actual Martian map would need exact location, projection and source attribution.

NASA describes a thin, cold Martian atmosphere and weather/temperature variation. Its fact sheet reports reference values, not current measurements at our invented base. Use these to establish plausible ranges and visual context, not to invent a real-time feed. [NASA Mars facts](https://science.nasa.gov/mars/facts/) · [NASA Mars fact sheet](https://nssdc.gsfc.nasa.gov/planetary/factsheet/marsfact.html)

Readable measurements and real outside views matter more than dense random graphs. Door-state displays should bind the actual controller; planet scenario data should have explicit provenance. Never use owner twin memories, private location or personal telemetry for a habitat display.

## Acceptance and remaining work

Real-browser evidence must cover: useful view with controls collapsed; clear distinction between ordinary and pressure doors; gasket/seat/latch appearance from both sides; truthful status while moving; no hardware or frame penetration; clear doorway for travel; observation glass looking onto Mars; readable and consistent displays from human distance. Then compare the exported scene and test native import. CPU bounds tests and a valid GLB do not certify appearance, pressure containment, physics, comfort or VR readiness.

This research is complete enough to begin the original hatch/telemetry candidate. No new pressure hatch, planetary display, exterior opening or pressure simulation is installed by this document.
