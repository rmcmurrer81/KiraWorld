# Body/avatar source review entry points

These are current source-only review entry points already present elsewhere in
the private KiraWorld repository. They are not copied into this directory, do
not include a 3D asset, and do not form a Hanson adapter. The repository has no
repository-wide license grant, so David's team should treat them as private
review material unless a specific license is added.

## World-reference evidence

Sources:

- `Core/world_reference_evidence.py`
- `tools/validate_world_reference_evidence.py`
- `Testing/test_world_reference_evidence.py`

Observed command and result on 2026-08-20:

```text
python -B -m unittest -v Testing.test_world_reference_evidence
9/9 passed
```

These tests enforce evidence, multiview, reference-only, and restricted-source
boundaries. They do not produce a world or open a portal in a runtime.

## Avatar orchestration, reconstruction, and garments

Sources:

- `Core/avatar_builder_orchestration.py`
- `Core/avatar_reusable_method_registry.py`
- `Core/avatar_reconstruction_contract.py`
- `Core/garment_capability.py`

Observed command and result:

```text
python -B -m unittest -v Testing.test_avatar_builder_orchestration Testing.test_avatar_reconstruction_contract Testing.test_garment_capability
28/28 passed
```

These tests cover source-lane isolation, owner-review bindings, reusable
component constraints, picture/model-reference boundaries, privacy, separate
clothing, and garment evidence. They explicitly do not grant runtime authority.

## Body eligibility and static anatomy quality

Sources:

- `Core/body_runtime_eligibility.py`
- `Core/avatar_static_anatomy_quality.py`

Observed command and result:

```text
python -B -m unittest -v Testing.test_body_runtime_eligibility Testing.test_avatar_static_anatomy_quality
19/19 passed
```

These tests are fail-closed eligibility and static-evidence checks. Passing a
technical fixture does not imply an approved Kira/Synthetic Robert avatar,
motion result, physical body, Blender execution, or GO.

## Known absent dependencies

The private repository does not currently track the required GLB/BLEND/world
assets and several local-only manifests. Broader runtime-body selection,
orchestration CLI, and notebook-world tests therefore are not portable from a
clean checkout. Do not “fix” those failures by inventing asset paths or
relabeling placeholder geometry as an accepted body.
