# Avatar reference neutral-chart migration checkpoint — 2026-08-09

Status: `STAGED_PRIVATE_REFERENCE_LIBRARY_UNREVIEWED_NO_DELETION_AUTHORIZED`

Robert requested a gradual move away from general-reference photographs of real people toward neutral design charts and properly licensed medical illustrations. This checkpoint creates the first staged pack without deleting, moving, renaming, or rewriting any existing reference.

## Package

Path: `Avatar/library/neutral_generated_reference_charts_v1`

The package currently contains:

- a synthetic regional skin/material atlas;
- a synthetic eye/eyebrow/lip morphology atlas;
- a synthetic detachable hairstyle atlas with dry, wind-displaced, and wet/clumped targets;
- a synthetic opaque-garment torso/chest silhouette atlas;
- a synthetic hands/feet/nails/contact atlas;
- synthetic adult-female and adult-male head/ear/nose/jaw/profile atlases;
- a synthetic opaque-bodysuit pose/deformation/contact atlas covering major joints and everyday movement targets;
- synthetic opaque adult-female and adult-male front/side/rear full-body proportion and silhouette atlases;
- four NIDDK/NIH copyright-free medical diagrams with required credit (two
  female urinary/lower-abdomen references and two male urinary/reproductive
  overview references);
- one CC BY-SA 4.0 external-anatomy SVG with attribution;
- a linked, not stored, NCI public-domain breast illustration candidate.

Exact paths, byte sizes, SHA-256 values, source URLs, download URLs, licenses, attribution, and truth boundaries are in:

- `Avatar/library/neutral_generated_reference_charts_v1/REFERENCE_ASSET_MANIFEST.json`
- `Avatar/library/neutral_generated_reference_charts_v1/README.md`

Integrity verification: `Testing/test_neutral_reference_library_v1.py` — 6/6
passed after the 15 stored assets were rebound.

## Interpretation boundary

Generated charts are asset-design selectors, not medical sources, identity evidence, calibrated measurements, or proof of body function. Medical diagrams inform general structure but do not prove that a mesh, rig, simulation, or runtime function exists.

The skin atlas supports Robert's direction that a realistic body is not one flat color. Final skin must use controlled regional variation and owner review, including the possibility of darker/redder lips and areola/nipple regions, while avoiding one universal palette across all people.

Maturity classification never comes from appearance. Exact durable profile classification and Robert's latest exact-person correction control adult versus doll-safe lanes.

## Preservation truth

At package creation `Avatar/library/female` contained 38 files totaling 4,586,856 bytes. This task removed none of them. Deletion remains blocked until replacement coverage is mapped, provenance and consumption are tested, Robert approves an exact deletion list, and rollback is recorded.

## Known gaps

- no calibrated shader/color measurement;
- no medically reviewed external chest-variation chart;
- no calibrated full-body measurement or soft-tissue measurement atlas; the generated proportion atlases are selectors only;
- no medically calibrated joint/deformation atlas; the synthetic movement atlas is a review selector only;
- male head/body selector charts and two authoritative NIDDK male urinary and
  reproductive overview diagrams are now present, but broader male external
  anatomy and pelvic-floor coverage is still incomplete;
- no proof that every old photo's useful function has a replacement.

The first image-generation request for an explicit clinical torso morphology atlas was rejected by the generator's sexual-content safety boundary. It was not bypassed. The stored opaque-garment silhouette chart is explicitly labeled shape direction only, and reusable medical diagrams are used for anatomy.
