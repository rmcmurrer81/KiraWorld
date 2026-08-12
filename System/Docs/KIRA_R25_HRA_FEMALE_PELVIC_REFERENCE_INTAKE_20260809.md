# Kira R25 HRA female pelvic reference intake — 2026-08-09

Status: **VALIDATED SOURCE INTAKE ONLY — NO BODY OR FUNCTION IMPLEMENTED**

## Result

Ten GLB 2.0 reference objects were downloaded from the official Human
Reference Atlas v1.2 object endpoint into:

`Avatar/avatar_builder/asset_library/medical_reference/hra_female_pelvis_cc_by_4_v1_2/`

The package contains a female bony pelvis, uterus/cervix, urinary bladder,
left/right ovaries, left/right uterine tubes, left/right ureter/renal-pelvis
objects, and large intestine with a separately named rectum. Every file passed
binary GLB magic/version/declared-length and JSON-chunk parsing. Exact file
sizes, hashes, direct URLs, and attribution are sealed in `SOURCE_MANIFEST.json`.

Manifest:

- bytes: `4540`
- SHA-256: `d40b7eb6dc260a1fc21d5bdb07286dfdb86545be59fa143bea5652fe2aa634b2`

README:

- bytes: `1910`
- SHA-256: `b5231e520d0b7f045af5fc675ed886fd12be27008a3e76f5eddf5fd3116337f0`

## Authority and license

The [Human Reference Atlas 3D Reference Object Library](https://humanatlas.io/3d-reference-library)
describes its organ objects as anatomically correct reference organs developed
by a medical-illustration specialist and approved by organ experts. It releases
all HRA 3D reference objects under CC BY 4.0. The official [NIH 3D female
pelvis entry](https://3d.nih.gov/entries/20984?version=1.01) identifies the
Visible Human Dataset as its source and also displays CC BY licensing. The
[NLM Visible Human Project](https://www.nlm.nih.gov/research/visible/visible_human.html)
describes the female dataset as 5,189 axial anatomical images at 0.33 mm
intervals and states that a license has not been required since 2019.

Attribution remains mandatory for every derivative. The data are research and
reference material, not medical advice and not proof that one donor's anatomy
defines all normal bodies.

## R25 use boundary

This intake can materially improve a detachable, private clinical-review
module by preserving real compartment scale and relative orientation. The
objects share the HRA/Visible-Human reference basis and expose separately named
substructures such as cervix, bladder neck/trigone, rectum, and uterine-tube
segments.

The intake does **not** supply a complete vaginal canal, female urethra, anal
canal/sphincter, perineal body, full pelvic-floor support, or the three external
outlet interfaces. Those remain source-backed authored structures under
`KIRA_CONFIRMED_ADULT_INTERNAL_PELVIC_ANATOMY_MODULE_CONTRACT_20260809.md`.

No GLB may be copied blindly into Kira. A future module must:

1. retain source IDs, hashes, CC BY attribution, and original object names;
2. align to an accepted carrier through a separately audited transform;
3. use only the needed pelvic portions of long ureter/intestine objects;
4. retain urinary, reproductive, and anorectal routes as separate meshes;
5. validate manifoldness, normals, route ordering, distinct endpoints,
   collisions, and pose-space clearance;
6. remain private, inactive, detached, and hidden by default; and
7. keep `function_implemented=false` until distinct physiological simulation
   and supervised acceptance evidence exists.

No Kira source Blend, R19 package, qualified MakeHuman foundation, R25
candidate, rig, material, memory, runtime, or owner-facing asset was changed by
this source intake.
