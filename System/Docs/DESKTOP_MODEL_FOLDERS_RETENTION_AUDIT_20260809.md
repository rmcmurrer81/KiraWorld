# Desktop model folders retention audit — 2026-08-09

Status: `PRESERVE_PENDING_SOURCE_TO_STAGED_RECONCILIATION`

This is a bounded read-only inventory made after Robert asked whether the
model folders on the Desktop were still needed. Nothing was opened in Blender,
copied, moved, renamed, placed in the Recycle Bin, or deleted.

## Bounded inventory

The scan covered 28 top-level folders that appeared to contain avatar,
environment, movement, or reference-model material. It deliberately excluded
Robert's private `Desktop/reference` photographs and unrelated application,
video, interview, and legal folders.

- total files: `1258`;
- total bytes: `24382581077` (`22.71 GiB`);
- model/archive files (`.glb`, `.usdz`, `.zip`, and related model formats):
  `979`;
- files whose names looked like license/readme/terms/copyright/attribution/
  source documents: `0`.

The absence of a filename match is not proof that no license metadata exists
inside an archive. It means the Desktop folders are not yet safe to discard
without archive-level provenance reconciliation.

## Why deletion is blocked

Current project records still reference multiple Desktop roots and exact
assets, including:

- Avatar Builder teaching/source roots: `Desktop/1model`, `Desktop/21`,
  `Desktop/40`, `Desktop/45`, and `Desktop/91`;
- world/structure/furniture sources: `Desktop/3d models`,
  `Desktop/3d models 2`, and `Desktop/3d model 3`, `4`, and `5`;
- alternate world assets under `Desktop/some more`;
- rigged character sources under `Desktop/no way home`;
- Voyager/reference-world material under `Desktop/voyager details`.

Some folders may contain duplicate `.glb`, `.usdz`, and source archives, but
duplicate-looking names are not sufficient evidence that topology, armatures,
textures, morphs, external/internal anatomy, animation, license material, and
source provenance are byte-identical. Some are world assets rather than body
assets, so a successful Kira body would not make them unnecessary.

## Required recoverable-removal gate

A folder or exact file may be moved to the Windows Recycle Bin only after:

1. every project reference to it is enumerated;
2. each useful source is matched to an exact project-staged path and SHA-256;
3. archive-only meshes, textures, rigs, morphs, anatomy, animations, and
   license/provenance files are accounted for;
4. the staged replacement opens and passes its applicable Avatar Builder or
   World Builder validation;
5. any sole full-anatomy or deformation teaching source remains preserved
   until accepted neutral/medical/template replacements exist;
6. an exact removal manifest records original path, size, hash, replacement,
   reason, Recycle Bin date, and restoration procedure; and
7. Robert is shown the exact proposed list before the recoverable move.

Current decision: `NO_DESKTOP_MODEL_DELETION_AUTHORIZED`.

