# Habitat design references for the reusable World Builder

Reviewed September 23, 2026. Research notes and original implementation proposals;
no layout, renderer, saved source, game adapter or VR runtime was changed.

## What the production sources actually establish

Daniel Jennings, the set designer responsible for Jamestown, documents separate
plans for walls, floors, ceilings, hatch surrounds, the hatch and galley. His
captions identify working hatch levers and dogs, and distinguish the airlock
atrium, galley, bunks and docking connection. This is useful evidence that credible
set design includes construction and interaction detail, not only room labels.
Only his written page and captions were inspected in this pass; the underlying
drawings and photographs have not been independently measured or imported.
[Designer portfolio](https://drjennings7.artstation.com/projects/obQ4GJ)

In his 2021 interview, co-creator Ronald D. Moore describes developing Jamestown
from a habitat into modular additions. Operations, crew living, laboratories,
power, waste, mining access and landing locations informed the arrangement.
These are the creator's account of a fictional design process, not engineering
approval of a real lunar or Martian facility.
[Moore interview](https://sixcolors.com/post/2021/02/interview-ron-moore-on-for-all-mankind-season-2-alt-history-space-tech-and-the-road-to-star-trek/)

Cinematographer Stephen McNutt describes using a consistent lighting scheme for
the base and changing it during a story emergency. The useful design lesson is
that lighting conveys location and state. World Builder must not display an
atmosphere or pressure condition that its simulation does not actually track.
[McNutt interview](https://www.motionpictures.org/2021/05/cinematographer-stephen-mcnutt-on-lighting-the-moon-in-for-all-mankind/)

NASA's discussion of life-support technology associated with The Martian covers
habitat temperature control and insulation, agriculture, water and air. Our
inference is that these functions deserve identifiable equipment and service
space in an original science-fiction base. The article does not provide a
validated layout or certify any generated equipment.
[NASA life-support article](https://www.nasa.gov/technology/tech-transfer-spinoffs/the-real-martian-spinoffs-part-1-stayin-alive-with-life-support-spinoffs/)

## Concrete next design work

The following are our proposed requirements, not statements copied from a film
or claims that the installed preview already satisfies them.

| Area | Recognizable construction | Interaction to implement | Honest present limit |
| --- | --- | --- | --- |
| Airlock | Recessed hatch surround, visible gasket channel, latch and hinge assembly, suit/tool storage | Door handle and paired-door sequencing tied to the same real door state | 038 tests sequencing only; no pressure seal or exterior exit |
| Laboratory | Work surface, instrument enclosure, sample storage, protected service routing | Open a cabinet or inspect a sample with an explicit object target | Decorative equipment currently produces no scientific measurements |
| Crew space | Bunk/privacy elements, personal storage, recognizable eating area | Cabinet/seat interactions with collision and reachable controls | Walking and some generic doors exist; a complete daily-life simulation does not |
| Operations | Workstations oriented toward a shared information surface, equipment access | Real saved-world/task information, not arbitrary animated telemetry | Generated display graphics are not operational readings |
| Utility zone | Distinct ventilation, water and power service housings | Inspect component role and its connections | No validated life-support or electrical simulation |

For each room, require at least one silhouette/function that remains recognizable
when its sign is hidden. Door frames, trim and controls must follow the opening
orientation and stay out of the walker's path. Clearance, navigation and moving
door tests must run against the same geometry that is drawn and exported.
Visual approval still requires actually viewing the room and motion.

Keep original geometry and materials; do not bundle a show's production drawings,
logos, screenshots or scene assets as product content. References inform function,
construction detail and staging. The reusable engine should retain stable room,
door, collider and interaction identities; a game or VR adapter can map those
identities to its own controller/input system. Exporting the identities alone does
not make the exported door interactive in another engine.

038 and 039 are the immediate bounded work. More detailed hatch construction,
distinct utility/crew furnishings and an exterior transition need separately
reviewed geometry changes, fresh source pins and new visual/export checks. Do not
silently reinterpret the existing two-interior-door room as an operational EVA lock.
