# Avatar neutral-reference medical male addendum — 2026-08-10

Status: `STAGED_PRIVATE_REFERENCE_LIBRARY_UNREVIEWED_NO_BODY_FUNCTION_CLAIM`

This addendum expands the neutral/open-medical reference library without
moving or deleting any existing female-library photograph and without running
Avatar Builder or Blender.

## Stored authoritative diagrams

Two copyright-free NIDDK/NIH media-library diagrams were downloaded from their
official asset URLs and bound into
`Avatar/library/neutral_generated_reference_charts_v1/REFERENCE_ASSET_MANIFEST.json`:

1. `medical_open_reference_v1/niddk_male_reproductive_tract_side_labeled.jpg`
   - bytes: `1120290`
   - SHA-256: `3488337919b8cc5163ef2f4fd9788a92f79737e855cd5ac6aa97e1551b0d62eb`
   - dimensions/mode: `2064 x 1611`, RGB JPEG
   - source page: `https://www.niddk.nih.gov/news/media-library/23070`
   - exact download: `https://www.niddk.nih.gov/media-assets/23070/Male-reproductive-tract-side-view_English-labels.jpg`

2. `medical_open_reference_v1/niddk_male_urinary_tract_front_labeled.jpg`
   - bytes: `499439`
   - SHA-256: `380e29f9dcfed5c62e9ccea8859e8d4e7fb5bb92185ca65ad4537f0d1c74a9ee`
   - dimensions/mode: `2075 x 2598`, grayscale JPEG
   - source page: `https://www.niddk.nih.gov/news/media-library/17544`
   - exact download: `https://www.niddk.nih.gov/media-assets/17544/N00124-H.jpg`

Both official pages state that NIDDK media-library images are available
copyright-free to the public at no cost and request this credit:
`National Institute of Diabetes and Digestive and Kidney Diseases, National
Institutes of Health`.

These diagrams provide general medical structure only. They are not Robert
likeness evidence and do not prove mesh correctness, continence, fertility,
elimination, sensation, physiology, rigging, or runtime function.

## Chest-reference result

The National Cancer Institute's `Breast Illustration` (image ID `2170`) was
verified on its official record as a schematic internal/external breast anatomy
illustration with no reuse restriction and public-domain reuse. Both NCI asset
hostnames failed DNS resolution from the local workstation, so it remains a
linked-not-stored candidate. No substitute copyrighted image was used.

## Verification

- manifest JSON strict parse: `PASS`;
- Pillow image readability/dimensions: `PASS` for both stored diagrams;
- `py -m unittest Testing.test_neutral_reference_library_v1 -v`:
  `6/6 PASS`;
- `git diff --check` for the manifest, README, checkpoint, and test: `PASS`.

Current bound files:

- manifest: 13,710 bytes, SHA-256
  `61a9912eade5d26766509318258640f532c98c9a370543f022bbb8f97f215ad2`;
- package README: 4,245 bytes, SHA-256
  `c4f5ddf0199d178c80eadd0e7de6efa240ac76b1c90a2a240204a13cce5a072e`;
- focused test: 3,209 bytes, SHA-256
  `e05c4752217bff490e5ced35e5ef16477710cf4d80e1099db91cbd9efff1df40`;
- migration checkpoint: 3,824 bytes, SHA-256
  `d1e0cb8b3819ee1ec5086c33c8b2d2cf009750e4fed099c57df4903598f1646e`.

## Remaining boundary

The neutral library now contains 15 stored generated/open-medical assets, but
it still does not prove replacement coverage for every file under
`Avatar/library/female`. No old reference is approved for deletion until exact
role mapping, Avatar Builder consumption parity, owner review, an exact
deletion list, and recoverable rollback evidence exist.
