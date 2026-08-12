# Kira biological-like soft-tissue and garment-response contract

Date: 2026-08-03  
Status: **IMPLEMENTATION AND ACCEPTANCE CONTRACT; NOT YET A PASSED SIMULATION**  
Scope: confirmed-adult Kira private inactive body and reusable Avatar Builder method

## Preserved owner decision

Robert approved Kira's R19 face and general body appearance. Soft-tissue or
garment work must not regenerate or reshape the accepted identity, face, eyes,
scalp, skeleton, or rest body. A bra, shirt, seated pose, or gravity change is
a reversible physical state applied to the same body, not a new body.

The exact protected visual baseline remains:

- `RecoverySprint/continuation_20260802/kira_r19_bald_targeted_correction/attempt_06/kira_r19_bald_targeted_material_movement_correction.blend`
- SHA-256 `dee1017f72c50dfba6583864bb1f9ec81405e2ef6d37f7c724831a24df49b53f`

## Research boundary

The acceptance design is informed by biomechanics rather than a rigid-body or
single-shape-key assumption:

- *Reductions in Kinematics from Brassieres with Varying Breast Support* found
  that different bras reduced breast displacement and acceleration by
  different amounts during several activities:
  https://pmc.ncbi.nlm.nih.gov/articles/PMC6413842/
- *Dynamic simulation of breast behaviour during different activities based
  on finite element modelling of multiple components of breast* treats skin,
  adipose/glandular tissue, and internal support as interacting components:
  https://pmc.ncbi.nlm.nih.gov/articles/PMC11779907/
- *Multimodal Patient-Specific Registration for Breast Imaging Using
  Biomechanical Modeling* documents large pose-dependent soft-tissue
  deformation and the need for person-specific mechanical properties:
  https://pmc.ncbi.nlm.nih.gov/articles/PMC8401473/
- *Increasing breast support is associated with altered knee joint stiffness*
  shows that support can affect whole-body movement, so a later movement test
  must not treat the chest and gait as unrelated systems:
  https://pmc.ncbi.nlm.nih.gov/articles/PMC10160436/

These papers support qualitative and comparative acceptance requirements. They
do not provide Kira-specific tissue parameters and must not be used to claim a
medical-grade finite-element model.

## Required body representation

A reusable implementation needs three separately versioned layers:

1. The accepted visible skin surface and identity materials.
2. A low-resolution internal soft-tissue simulation cage, with left and right
   regions kept separate and stable attachments at the chest wall.
3. External collision and support surfaces for garments, furniture, hands,
   gravity, and environment contact.

The visible skin follows the simulation cage through a deterministic transfer.
The cage may deform; the accepted rest surface and its canonical hash may not
be overwritten. Nipple/areolar landmarks and regional material coordinates
must follow the same surface continuously rather than slide, detach, or remain
painted in place.

## Bra response requirements

A bra state must provide measured contact instead of merely replacing the body
with a smaller breast shape:

- the underband supplies circumferential support without cutting through the
  torso;
- cups distribute compression and lift over an area rather than at a point;
- straps transfer bounded load toward the shoulders without creating a groove
  deeper than the declared comfort/collision limit;
- supported motion amplitude is lower than the same movement without the bra;
- the supported shape remains continuous with the chest wall and changes
  smoothly during breathing, arm elevation, walking, sitting, and lying down;
- removing the bra restores the exact accepted rest state after the bounded
  settling interval, with zero permanent identity/body drift.

Every garment remains a separate removable component. No garment may replace,
delete, hide, or regenerate the underlying body.

## Minimum private acceptance series

Run matched braless, everyday-support, and high-support states for:

- neutral standing under gravity;
- arms down and arms raised;
- walking and a short higher-acceleration motion;
- seated upright;
- supine;
- side-lying;
- garment put-on, settled, and removal/restoration.

For each state record:

- exact body, rig, garment, cage, action, and parameter hashes;
- contact regions and maximum penetration depth;
- left/right landmark displacement relative to the moving thorax;
- vertical, lateral, and anterior/posterior displacement amplitudes;
- peak velocity/acceleration for the matched dynamic actions;
- solver steps, wall time, peak RAM/VRAM, and frame-time spikes;
- zero detached regions, inverted faces, new self-intersections, or body-
  garment intersections;
- exact rest-state restoration and removal of all temporary solver state.

The high-support result must reduce dynamic displacement relative to braless,
but no universal percentage is declared because Kira-specific material
parameters have not been measured. A result is rejected if it behaves as a
rigid plate, frozen hemisphere, rubber balloon, collapsing bag, or permanently
reshaped mesh.

## Whole-body and Avatar Builder transfer

The same state-separation pattern applies to abdominal, gluteal, thigh, and
other soft-tissue contact. Seated and supine tests need supported deformation
at the actual contact surface while preserving volume and avoiding chair/bed
penetration. Movement actions, soft-tissue response, clothing collision, and
the accepted rest mesh remain distinct assets.

Avatar Builder may reuse only the simulation architecture, measurements,
failure codes, and test harness. It must fit parameters to each adult body and
must never copy Kira's private identity geometry or tissue values into another
person.

## Truth and authorization boundary

No current Kira candidate has passed this contract. A visually plausible
still does not prove dynamic soft-tissue behavior, and an external body plus
soft-tissue cage does not implement internal urinary, bowel, reproductive,
pregnancy, illness, or hospital systems. Those remain separate future systems
with separate consent, state, physiology, and acceptance evidence.

This contract authorizes no clothing activation, live-body assignment,
runtime export, publication, upload, or claim of biological equivalence.
