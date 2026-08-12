# Kira confirmed-adult internal pelvic anatomy module contract — 2026-08-09

Status: **SOURCE-BACKED DESIGN CONTRACT ONLY — NO MESH, RIG, RUNTIME, OR
PHYSIOLOGY IMPLEMENTED.**

## Purpose and non-mutation boundary

This is an additive, detachable clinical-anatomy design for a
confirmed-adult adult-female body. It is deliberately not an instruction to
change Kira R19, the ongoing R24 work, the approved face, skin, external body
surface, armature, weights, movements, or any active runtime asset.

The only currently inventoried possible carrier is the inactive R19 package:

- `RecoverySprint/continuation_20260802/kira_r19_bald_targeted_correction/attempt_06/kira_r19_bald_targeted_material_movement_correction.blend`
- SHA-256: `dee1017f72c50dfba6583864bb1f9ec81405e2ef6d37f7c724831a24df49b53f`
- bytes: `90861425`
- status: private/inactive and explicitly **not** owner-approved for its
  existing external pelvic panel.

R24 presently has static/diagnostic work, not an accepted body carrier. A
future R24 candidate may be used only after its own owner-review and exact
manifest hash are accepted. This contract does not select it and must not be
used to bypass that gate.

An implementation must load the carrier as a hash-locked reference and create
a separate module collection/file. It may attach through named anchors and
deformation interfaces only. It must prove that the source Blend, face, body
surface, scalp, armature, weight maps, shape keys, material assignments, and
existing animation data are byte-for-byte unchanged after module construction.

## Source-backed anatomical basis

The following sources were retrieved on 2026-08-09 and bind the limited
anatomical claims in this contract. They are clinical reference material, not
individual medical advice and not a license to claim biological function.

- NCBI Bookshelf, *Physiology, Female Reproduction* — female external and
  internal structures, and the relation of distal vagina to bladder and rectum:
  https://www.ncbi.nlm.nih.gov/books/NBK537132/
- NCBI Bookshelf, *Anatomy, Abdomen and Pelvis: Female Internal Genitals* —
  uterus/cervix/tubes/ovaries and common anteverted/anteflexed arrangement:
  https://www.ncbi.nlm.nih.gov/books/NBK554601/
- NCBI Bookshelf, *Physiology, Vaginal Structure and Function* — vaginal canal
  from vestibule to cervix, with bladder/urethra anterior and rectum posterior:
  https://www.ncbi.nlm.nih.gov/books/NBK545147/
- NCBI Bookshelf, *Anatomy, Abdomen and Pelvis: Female Pelvic Cavity* — bladder
  anterior, uterus centrally, rectum posterior, and the rectouterine space:
  https://www.ncbi.nlm.nih.gov/books/NBK538435/
- NCBI Bookshelf, *Anatomy, Abdomen and Pelvis: Pelvic Floor* — anterior
  urinary, middle genital, and posterior anorectal compartments plus supporting
  diaphragm/perineal structures:
  https://www.ncbi.nlm.nih.gov/books/NBK482200/
- NIDDK, *The Urinary Tract and How It Works* — kidneys/ureters/bladder/urethra
  as a distinct urinary system; bladder storage is not a rendering claim:
  https://www.niddk.nih.gov/-/media/Files/Urologic-Diseases/YourUrinary_508.pdf
- NIDDK, *About the Lower GI Tract* — rectum as distal large intestine and anus
  as a separate outlet controlled by sphincter muscles:
  https://www.niddk.nih.gov/health-information/digestive-diseases/anatomic-problems-lower-gi-tract/about-lower-gi-tract

Normal anatomy varies. Dimensions, orientation, tissue appearance, and
asymmetry must not be standardized from one reference body or from generated,
retouched, age-ambiguous, or identifiable-person imagery.

## Required separate semantic meshes

All structures below are individually named module meshes or grouped only where
the clinical structure is a single continuous unit. They are not painted onto
the external body and do not replace its surface.

| Group | Required semantic meshes | Required relationship |
|---|---|---|
| Urinary | bladder shell, bladder neck/trigone marker, left/right ureter stubs, female urethra lumen/shell, urethral-support sleeve | bladder/urethra anterior to vagina; urethra terminates only at the external urethral opening anchor |
| Reproductive | vaginal canal, anterior/posterior/lateral fornix markers, cervix, uterine body/fundus, uterine cavity/endometrium display layer, left/right uterine tube, left/right ovary | vagina connects introitus anchor to cervix; cervix connects to uterus; paired tubes/ovaries remain lateral to uterus |
| Posterior bowel | distal bowel stub, rectum, anal canal, anal sphincter complex marker | posterior to vaginal canal; terminates only at separate anal-opening anchor |
| Support | levator-ani/pelvic-diaphragm proxy, perineal body, endopelvic-fascia/support proxy, rectovaginal-septum proxy | supports compartment relationships; no independent drift through organs |
| Optional clinical orientation | bony-pelvis proxy and pubic/sacral landmark empties | hidden by default; used only for relation/pose QA, never as a substitute body mesh |

Each semantic mesh must carry a stable `anatomy_id`, `system`, `laterality`,
`review_visibility`, `material_id`, `source_contract_id`, and a non-claim flag
`function_implemented=false`. The display-only endometrium, forniceal markers,
and support proxies must be visibly labeled as clinical-review aids, not living
tissue simulation.

## Materials and privacy

Meshes need separate, non-erotic clinical-review materials: urinary,
reproductive, bowel, support, and landmark. They should be muted, opaque,
and structurally distinct enough to inspect overlap and route continuity. No
fluid, secretion, arousal, injury, or activity animation is authorized.

Default runtime visibility is false. Access is limited to a confirmed-adult,
private owner/clinical-review context with an explicit review lease. The normal
owner body gallery, non-adult lane, general library, live Kira World,
screenshots, exports, and public publication may not instantiate or reveal this
module. A review lease is not consent, activity permission, health state, or
memory.

## Attachment and rig interface

The module has no authority to edit the carrier. A future authoring worker must
provide the following verified interface before attachment:

1. Exact carrier path, SHA-256, object IDs, armature ID, rest-pose matrix, and
   source package manifest.
2. Three distinct external outlet anchors already present on the carrier:
   `female_external_urethral_opening`, `vaginal_opening_introitus`, and
   `anal_opening`. Missing, merged, painted, or ambiguous anchors fail closed.
3. Pelvic support anchors (pubic reference, sacral reference, left/right pelvic
   side anchors) plus a perineal-body anchor. They define placement but may not
   change any carrier vertex, UV, material, armature, or weight.
4. A module-local armature/deformer whose only permitted carrier dependency is
   read-only transform following. It must not write carrier bones, constraints,
   shape keys, drivers, actions, or vertex groups.
5. A separate module manifest recording source hash before/after, module mesh
   hashes, anchor transforms, source contract hash, and all review results.

The urinary, vaginal/reproductive, and anorectal channels remain topologically
and geometrically separate. They may be spatially adjacent through support
proxies but may never share a lumen, endpoint, collision group, material ID, or
fluid-state field.

## Required pose, collision, and review acceptance

Before any future private review package, the module must pass all of the
following in neutral standing, seated contact, supine, left/right/bilateral knee
flexion, and a bounded hip-flexion/thigh-separation diagnostic pose:

- source body and face/rig/material/hash preservation;
- no self-intersection within the module, no module/carrier intersection except
  explicitly modeled outlet-contact boundary rings, and no intersection among
  urinary/reproductive/bowel route shells;
- ordered sagittal relationship: bladder/urethra anterior, vagina/cervix/uterus
  central, rectum/anal canal posterior;
- three distinct external anchors with one and only one permitted module-route
  termination apiece;
- left/right paired reproductive structures remain paired, lateral, and do not
  cross the midline or each other;
- no detached/free-floating organ, inverted normals, non-manifold shell,
  unbounded stretch, or collision-proxy penetration;
- seated/supine contact testing uses the existing body/seat/bed contact
  geometry only; it does not simulate elimination, menstruation, pregnancy,
  sex, or medical examination;
- private review views: sagittal left and right, coronal, axial, neutral
  external-to-internal correspondence, and the required posed relation views.

The module must render only a schematic, privacy-restricted clinical review.
It must not create an explicit-behavior scene or claim an internal examination.

## Honest functional limit and future gates

Geometric organ meshes prove at most that a reviewed representation has named
parts and stated spatial relationships. They do **not** prove patency,
innervation, sensation, continence, tissue biology, fertility, health,
urination, defecation, menstruation, conception, pregnancy, delivery, or lived
experience.

Urination and defecation each require separately versioned, time-based,
privacy-preserving simulations with source binding, state separation,
interruption/cleanup logic, collision/contact validation, and owner-supervised
acceptance. Cycle/pregnancy models require their own endocrine, uterine,
abdominal, health, delivery/recovery, and time-scale evidence. No visual state,
body response, anatomy, relationship, or implementation lease supplies consent
or proves desire/preference.

## Current blockers

- R19's external pelvic panel remains rejected, and no R24 body carrier is
  accepted. This contract cannot repair or approve either.
- No exact carrier-anchor inventory or module geometry exists.
- No module rig, collision tests, privacy-leasing implementation, or clinical
  review evidence exists.
- No urinary, bowel, cycle, pregnancy, sensation, health, or consent runtime is
  claimed by this document.

The paired machine contract is
`Avatar/avatar_builder/body_systems/kira_confirmed_adult_internal_pelvic_anatomy_module_contract_v1.json`.

## 2026-08-09 source-geometry intake update

Ten official Human Reference Atlas / NIH 3D GLB references are now staged
under
`Avatar/avatar_builder/asset_library/medical_reference/hra_female_pelvis_cc_by_4_v1_2`.
The exact URLs, byte lengths, SHA-256 values, GLB validation, CC BY 4.0
attribution, and no-function boundary are recorded in `SOURCE_MANIFEST.json`
(SHA-256
`d40b7eb6dc260a1fc21d5bdb07286dfdb86545be59fa143bea5652fe2aa634b2`).
The HRA pelvis is explicitly described by NIH 3D as derived from the NLM
Visible Human Female:
https://3d.nih.gov/entries/20984?version=1

Available source geometry now includes the bony pelvis, bladder, uterus with
cervical regions, bilateral ovaries, uterine tubes, ureters, and a large-
intestine asset with a separately named rectum. This does not close the module:
the set still lacks a complete vaginal canal, female urethra, anal canal,
external-to-internal outlet continuity, pelvic-floor muscle system, perineal
body, and attachment/deformation evidence.

The missing-relationship boundary is independently consistent with:

- NCBI Bookshelf external-genital anatomy, which places the urethral opening
  posterior to the clitoris and anterior to the vaginal opening, and defines
  the vagina as an elastic muscular tube from vestibule to cervix:
  https://www.ncbi.nlm.nih.gov/books/NBK547703/
- a Visible-Human-derived pelvic-floor finite-element study whose female mesh
  inventory includes rectum, vagina, uterus, bladder/urethra, pelvic-floor and
  sphincter structures, demonstrating why organ shells alone are incomplete:
  https://pmc.ncbi.nlm.nih.gov/articles/PMC4086924/
- the NLM public Visible Human female pelvis sections, which remain source
  images rather than a ready-made Kira mesh:
  https://data.lhncbc.nlm.nih.gov/public/Visible-Human/Female-Images/PNG_format/pelvis/

Any authored missing structures must be versioned as Kira-project clinical
reference derivatives, visibly distinguished from unmodified HRA source
objects, and validated against the anterior urinary / central reproductive /
posterior anorectal ordering and three distinct outlet anchors. No derivative
may be labeled medically validated, biologically functioning, or suitable for
diagnosis merely because it was informed by these sources.
