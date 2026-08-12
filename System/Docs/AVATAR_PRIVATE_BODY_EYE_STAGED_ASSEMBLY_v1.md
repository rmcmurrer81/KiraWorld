# Private Body + Eye-Rig Staged Assembly v1

This pathway combines one exact body GLB and one separately authored eye-rig
GLB for private, inactive review. It does not grade the body's quality and does
not make either component approved, active, released, or safe for automatic
multi-profile work.

## Files

- Orchestrator: `Core/avatar_body_eye_staged_assembly.py`
- Blender worker: `tools/blender_assemble_avatar_body_eye_staged.py`
- CLI: `tools/assemble_avatar_body_eye_staged.py`
- Tests: `Testing/test_avatar_body_eye_staged_assembly.py`
- Append-only run root: `Avatar/avatar_builder/staged_assemblies/body_eye/`

## Fail-closed input contract

The caller supplies project-relative body and eye-rig paths plus each file's
expected SHA-256. Both files must be regular, non-symlink, self-contained GLB
2.0 files under the project root. Absolute paths, traversal, external GLB
buffers/images, reused run directories, malformed hashes, and hash mismatches
are rejected.

The body must have one uniquely recognized head joint in a skin. The eye rig
must retain separately named left/right controls and named morph targets on
both sides. The pathway does not add clothing, hair, anatomy, or likeness.

## Default dry run

The CLI is a no-write dry run unless `--execute` is explicitly present:

```powershell
py tools\assemble_avatar_body_eye_staged.py `
  --subject-id <subject_id> `
  --run-id <new_unique_run_id> `
  --body <project_relative_body.glb> `
  --body-sha256 <64_hex_characters> `
  --eyes <project_relative_eye_rig.glb> `
  --eyes-sha256 <64_hex_characters>
```

Dry-run validation creates no directory, queue, request, or artifact.

## Explicit private execution

Execution is appropriate only after the exact component revisions have passed
their own applicable review gates. Add:

```powershell
--execute --blender "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
```

Execution creates a brand-new directory containing:

- `assembly_request.json`
- `assembled_body_eyes.glb`
- `worker_result.json`
- `manifest.json`

The directory may not already exist. Existing contents are never overwritten.
A failed Blender run retains a `failure.json` instead of a manifest.

## Bone binding and coordinate proof

The worker imports each source independently, identifies the exact recognized
head bone, and bone-parents the eye-rig root while leaving the eye hierarchy,
separate gaze controls, and eyelid morphs intact.

Blender and glTF use different armature-origin conventions for bone children.
The worker compensates the imported armature-origin translation and then
calculates the source and assembled glTF world matrices for the eye-rig root
and each left/right control. Export fails if any rest-pose matrix changes by
more than `0.00002` in matrix-element magnitude. It also fails if the root is
not a descendant of the recognized head joint or if any exact control/morph is
missing from the exported GLB.

## Authority boundary

Every request, worker result, manifest, and returned result keeps these facts
explicit:

- private inactive staging only;
- no owner approval is inferred;
- no runtime activation;
- no live body replacement;
- no public export;
- no release.

The assembly manifest is evidence of exact mechanical composition only. It is
not evidence of body quality, eye realism, deformation quality, likeness,
owner acceptance, or readiness for automatic work on other bodies.

