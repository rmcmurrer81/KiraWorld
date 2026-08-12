# TemporaryAI Avatar Builder Bridge v1

Purpose: give TemporaryAIs a clean path from source/mind profile to visual avatar work.

## Folder Layout

```text
Avatar/temp_ai/<candidate_id>/
  avatar_profile.json
  avatar_request.json
  online_reference_queue.json
  references/
    downloaded/
    approved/
    rejected/
  outputs/
```

## What The Avatar Builder Can Use

- Approved local images.
- Future online reference downloads with recorded source URLs.
- Official references first where available.
- Secondary sources only with lower confidence labels.
- Style notes from the TemporaryAI profile.

## What It Must Not Do

- Do not claim a rendered avatar exists before one is built.
- Do not use private person images without permission.
- Do not treat reference images as memories.
- Do not use one AI's private body references for another AI.
- Do not make public exports without review.

## Future Online Search

The queue file prepares searches and the current helper can record online candidates:

```text
tools/search_temp_ai_avatar_references.py
Start_TempAI_Avatar_Reference_Search.bat
tools/create_temp_ai_avatar_build_brief.py
Start_TempAI_Avatar_Build_Brief.bat
```

The helper should:

1. Search official/reliable sources first.
2. Save images under `references/downloaded/`.
3. Record source URL, source type, and confidence.
4. Require Robert review before moving anything into `references/approved/`.
5. Only approved references can feed avatar generation.

Wikimedia Commons search is opt-in because broad character names can return unrelated public images. Rejected references should not count as usable review candidates in avatar build briefs.

Current Ladybug/Marinette smoke status:

```text
Avatar/temp_ai/ladybug_marinette_expanded_smoke/outputs/ladybug_marinette_expanded_smoke_avatar_build_brief_v1.md
status: ready_for_reference_review
approved: 0
online_candidates_need_review: 1
```

One old Wikimedia Commons insect result was marked `rejected_unrelated`; it is not a character reference.

## 2026-06-20 Desktop Intake And 3D Runtime

Robert's desktop staging folder is supported by a non-destructive intake tool:

```powershell
Start_Avatar_Reference_Intake.bat
py tools\intake_avatar_downloads.py
```

The tool reads `C:\Users\robmc\Desktop\Downloads For Avatars`, copies recognized images into candidate-specific `desktop_intake` folders, records provenance, and creates outfit catalogs. It never edits or deletes the desktop originals. The first intake copied 46 files with no unmatched folders:

- Cameron: 12
- Kara Zor-El (`My Adventures with Superman`): 19
- Kathryn Merteuil: 15

Desktop intake images are evidence for review. They are not automatically approved likenesses, isolated character cutouts, finished outfits, or memories. Group shots and backgrounds still need segmentation and human review before avatar generation.

The first Three.js runtime is under `Avatar/runtime3d/` and can be opened with:

```powershell
Start_TemporaryAI_3D_Avatar.bat
```

TemporaryAI Live Chat also exposes **Open Walking 3D Avatar**. The runtime provides a full-room 3D scene, camera framing, procedural walking, waving, sitting, reading a book or magazine, and computer-use actions. It is deliberately capable of loading a real rigged GLB/GLTF when one exists, while retaining a clearly labeled procedural fallback.

Rigged candidate models may be installed at one of these locations:

```text
Avatar/models/temp_ai/<candidate_id>/avatar.glb
Avatar/models/temp_ai/<candidate_id>/avatar.gltf
Avatar/temp_ai/<candidate_id>/models/avatar.glb
Avatar/temp_ai/<candidate_id>/generated_body/avatar.glb
```

See `Avatar/models/temp_ai/README.md` for the model, animation-clip, and outfit-mesh naming contract. Useful animation names include `idle`, `walk`, `wave`, `sit`, `read_book`, `read_magazine`, and `computer`/`type`. Outfit meshes can be tagged with names containing `civilian`, `hero`, `sleepwear`, `pajama`, or `pyjama` so the runtime can switch forms without rebuilding the whole model.

Current limitation: no likeness-matched rigged Kara, Marinette, or Ladybug GLB has been generated yet. The existing pose sheets are animated 2D frames and the current 3D figure is a procedural mannequin until a reviewed rigged model is installed. Reference images alone cannot provide a clean, articulated 3D body without segmentation, reconstruction/modeling, rigging, texture review, and animation retargeting.

Browser verification passed at desktop `1440x900` and mobile `390x844`. Playwright confirmed a nonblank full-viewport WebGL canvas, stable framing, walk and read actions, thousands of rendered triangles, and nonuniform canvas pixels. Screenshots are in `Data/avatar_runtime_tests/`.

Voice status is independent from the 3D body. Ladybug and Kara currently use slower Windows SAPI approximations (rate `-2`). Their mixed-speaker reference packs still require target-speaker review and an installed compatible neural voice backend before an exact reviewed voice can be enabled.
