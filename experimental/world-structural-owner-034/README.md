# Structural collider ownership successor034

The earlier030 exporter left actual Mars ceilings and walls unowned because it
looked only for a node named `collider_id + "_mesh"`. Those structural primitives
use the exact collider ID. This isolated successor links exact names and the
compiler's floor-mesh alias, and requires exactly one structural box with matching
bounds. Missing or ambiguous names and incompatible boxes are rejected; another
object at similar coordinates is never guessed as the owner.

The031 writer/CLI is copied under `package/`, with pins for the corrected core in
`core/`. Original030/031 code, packages, installed World Builder and owner worlds
remain untouched. This is a reusable metadata prototype, not a mesh/game/VR export
feature or an installed desktop control.

## Evidence

- Ten ownership regression groups pass on the synthetic fixture and the actual
  saved Mars geometry, including the floor alias and rejection cases.
- The inherited11 metadata groups and15 package tests pass. A separate package
  check proves three hash-valid but semantically invalid ownership inputs fail
  before creating an output directory.
- `actual-mars-001/` contains a corrected derived metadata package. All59 source
  structural colliders now have intended owners and equivalent bounds. The other
  scene fields are exactly unchanged from031. Counts remain7 rooms,141 nodes,
  134 colliders and6 doors.
- All116 protected owner source files,12 historical code files and the three
  historical031 package files were verified unchanged. No original geometry,
  research document, personal memory, media or absolute local path is bundled
  in the derived package.

Owner bounds are compared with the existing exporter's absolute1e-7m tolerance
to allow roundoff when center/size reconstruct source min/max. Collision response,
equipment meshes/materials, visual realism, engine adapters and VR remain outside
this change. The stored ownership link is not a physics-certification claim.

## Use the isolated CLI

Create a package from an explicitly supplied saved-preview binding manifest:

```text
python package/package_writer.py build --bindings PATH --bindings-sha256 SHA256 --scene-id ORIGINAL_SCENE_ID --output NEW_FOLDER
python package/package_writer.py verify --package NEW_FOLDER
```

The default core is this successor's sibling `core/`; `--core-root` can select a
copy only if its exact producer pins match. Existing outputs are refused. The
writer verifies actual source bytes and the geometry/blueprint/research/cache
digest chain; those checks do not establish source truth or visual approval.

The CPU tests are `test_ownership.mjs`, `core/test_metadata.mjs`,
`package/test_package.py` and `package/test_owner_package.py`. Their receipts are
preserved; replay in a disposable copy using `run_portable.py` when supplied with
the public backup. `check_actual.py` requires explicit original saved bindings,
the preserved prior package and the116-file protection plan; it never downloads
or copies the original source documents into the output.
