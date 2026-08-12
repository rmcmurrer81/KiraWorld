from __future__ import annotations

import ast
import copy
from datetime import datetime, timedelta, timezone
import importlib.util
import json
import math
import os
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools/kira_r24_intrinsic_curved_annulus_structured_retopology_static_r2.py"
PACKAGE = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "kira_r24_intrinsic_curved_annulus_structured_retopology_static_r2"
)
CONTRACT_PATH = PACKAGE / "INTRINSIC_CURVED_ANNULUS_STRUCTURED_RETOPOLOGY_R2_CONTRACT.json"
PARENT_PACKAGE = ROOT / (
    "RecoverySprint/continuation_20260808/"
    "kira_r24_intrinsic_curved_annulus_structured_retopology_static"
)


def load_module():
    spec = importlib.util.spec_from_file_location("kira_r24_r2_static", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load R2 static evaluator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class IntrinsicCurvedAnnulusR2StaticGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module()
        cls.contract = cls.module.load_contract(CONTRACT_PATH)
        cls.context = cls.module.static_context()
        cls.temp = tempfile.TemporaryDirectory(prefix="kira_r24_r2_static_")
        cls.artifact_root = Path(cls.temp.name)
        cls.synthetic_contract = copy.deepcopy(cls.contract)
        # The sealed source E* triangles are a complete synthetic schema fixture,
        # but the inherited source has a known 0.749-degree sliver. Lower only the
        # in-memory fixture threshold so every other gate can have a positive case.
        # The production 12-degree contract is tested separately and still rejects it.
        cls.synthetic_contract["metric_bounds"]["minimum_render_triangle_angle_degrees"] = 0.5
        cls.nominal = cls.build_nominal_evidence()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp.cleanup()

    @classmethod
    def binding(cls, relative_path: str) -> dict[str, object]:
        path = ROOT / relative_path
        return {
            "path": relative_path,
            "bytes": path.stat().st_size,
            "sha256": cls.module.sha256_file(path),
        }

    @classmethod
    def build_nominal_evidence(cls) -> dict[str, object]:
        module = cls.module
        contract = cls.synthetic_contract
        context = cls.context
        source = context["source_mesh"]
        domains = context["domains"]
        cycle = contract["exact_topology"]["outer_boundary_cycle"]
        cycle_set = set(cycle)
        interior_source = sorted(set(domains["estar_summary"]["vertices"]) - cycle_set)
        remap = {index: 1000 + offset for offset, index in enumerate(interior_source)}
        mapped = lambda index: index if index in cycle_set else remap[index]
        face_records = [
            {
                "face_id": order,
                "vertices": [mapped(index) for index in source["faces"][face_index]],
                "material_index": 5,
            }
            for order, face_index in enumerate(sorted(domains["estar"]))
        ]
        coordinate_records = [
            {"vertex_index": index, "coordinate_m": list(source["positions"][index])}
            for index in cycle
        ] + [
            {
                "vertex_index": remap[index],
                "coordinate_m": list(source["positions"][index]),
            }
            for index in interior_source
        ]
        coordinate_map = {
            row["vertex_index"]: row["coordinate_m"] for row in coordinate_records
        }
        schedule_records = [
            {
                "order": order,
                "operation": "emit_face",
                "face_id": face["face_id"],
                "vertices": list(face["vertices"]),
            }
            for order, face in enumerate(face_records)
        ]
        incident_face: dict[int, int] = {}
        for face_index in sorted(domains["estar"]):
            for vertex in source["faces"][face_index]:
                incident_face.setdefault(vertex, face_index)
        provenance_records = []
        for source_vertex in interior_source:
            face_index = incident_face[source_vertex]
            triangle = source["faces"][face_index]
            corner = triangle.index(source_vertex)
            barycentric = [0.0, 0.0, 0.0]
            barycentric[corner] = 1.0
            normal = list(source["normals"][source_vertex])
            normal_length = math.sqrt(sum(float(value) ** 2 for value in normal))
            normal = [float(value) / normal_length for value in normal]
            provenance_records.append(
                {
                    "vertex_index": remap[source_vertex],
                    "source_face_index": face_index,
                    "source_triangle": list(triangle),
                    "barycentric": barycentric,
                    "source_position_m": list(source["positions"][source_vertex]),
                    "displacement_m": [0.0, 0.0, 0.0],
                    "displacement_length_m": 0.0,
                    "final_position_m": list(source["positions"][source_vertex]),
                    "uv_records": [
                        {
                            "layer": "TEXCOORD_0",
                            "uv": list(source["texcoords"][source_vertex]),
                        }
                    ],
                    "normal": normal,
                    "native_weights": module._source_weight_map(
                        context, triangle, barycentric
                    ),
                    "material_index": 5,
                    "shape_key_records": [],
                }
            )

        consumed = [
            {
                "source_face_index": index,
                "vertices": list(source["faces"][index]),
            }
            for index in sorted(domains["estar"])
        ]
        collar = [
            {
                "source_face_index": index,
                "vertices": list(source["faces"][index]),
                "disposition": "consumed_by_complete_estar_structured_retopology",
            }
            for index in sorted(domains["collar"])
        ]
        materials = [{"material_index": 5, "name": "native_skin_material_slot_5"}]
        uv_layers = [{"name": "TEXCOORD_0", "domain": "CORNER", "components": 2}]
        bone_names = [f"native_bone_{index:03d}" for index in range(188)]
        armatures = [
            {
                "name": contract["rig_and_action_requirements"]["required_armature_name"],
                "bone_count": 188,
                "bone_names": bone_names,
                "bone_names_sha256": module.canonical_sha256(bone_names),
                "rest_structure_sha256": contract["rig_and_action_requirements"][
                    "required_armature_rest_structure_sha256"
                ],
            }
        ]
        actions = [
            {
                "name": name,
                "fcurve_data_sha256": module.canonical_sha256(
                    {"synthetic_exact_action_fixture": name}
                ),
            }
            for name in contract["rig_and_action_requirements"]["required_action_names"]
        ]
        inherited_pairs = [
            {
                "object_a": "preserved_body",
                "triangle_a": index,
                "object_b": "preserved_body",
                "triangle_b": 10000 + index,
                "measurement_sha256": module.canonical_sha256(
                    {"synthetic_inherited_pair": index}
                ),
            }
            for index in range(29)
        ]
        interface_records = [
            {
                "vertex_index": index,
                "coordinate_m": [float(index), float(index) / 10.0, -float(index) / 100.0],
            }
            for index in contract["intersection_and_interface_requirements"][
                "global_interface_vertex_indices"
            ]
        ]
        welds = [
            {"vertex_index": row["vertex_index"], "residual_m": 0.0}
            for row in interface_records
        ]
        truth_records = [
            {"property": "privacy", "value": "private"},
            {"property": "activation", "value": "inactive"},
            {"property": "assignment", "value": "unassigned"},
            {"property": "publication", "value": "unpublished"},
            {"property": "owner_approval", "value": "not_claimed"},
        ]

        run_id = "synthetic_gate_fixture_01"
        candidate_relative = (
            contract["authorized_implementation"]["candidate_path_prefix"]
            + run_id
            + "/candidate.blend"
        )
        candidate_path = cls.artifact_root / candidate_relative
        candidate_path.parent.mkdir(parents=True, exist_ok=True)
        candidate_bytes = b"BLENDER-v300\x00R2_STATIC_SYNTHETIC_EVIDENCE_FIXTURE" * 8
        candidate_path.write_bytes(candidate_bytes)
        now = datetime.now(timezone.utc)
        os.utime(candidate_path, (now.timestamp(), now.timestamp()))
        started = now - timedelta(seconds=2)
        ended = now + timedelta(seconds=2)
        source_binding = cls.binding(contract["exact_source"]["preserved_target_blend_path"])
        worker_binding = cls.binding(contract["authorized_implementation"]["worker_path"])
        config_binding = cls.binding(contract["authorized_implementation"]["config_path"])
        evidence = {
            "schema": contract["authorized_implementation"]["required_evidence_schema"],
            "record_sha256": "",
            "construction_run": {
                "run_id": run_id,
                "started_utc": started.isoformat().replace("+00:00", "Z"),
                "ended_utc": ended.isoformat().replace("+00:00", "Z"),
                "source": source_binding,
                "worker": worker_binding,
                "config": config_binding,
                "evidence_payload_sha256": "",
            },
            "artifact": {
                "kind": contract["authorized_implementation"]["required_artifact_kind"],
                "path": candidate_relative,
                "bytes": candidate_path.stat().st_size,
                "sha256": module.sha256_file(candidate_path),
                "created_utc": now.isoformat().replace("+00:00", "Z"),
                "construction_run_id": run_id,
                "source_sha256": source_binding["sha256"],
                "worker_sha256": worker_binding["sha256"],
                "config_sha256": config_binding["sha256"],
                "evidence_payload_sha256": "",
            },
            "topology": {
                "outer_boundary_cycle": list(cycle),
                "face_ledger": module.ledger(face_records),
                "vertex_coordinate_ledger": module.ledger(coordinate_records),
                "ordered_stitch_schedule": module.ledger(schedule_records),
            },
            "scope": {
                "consumed_estar_face_ledger": module.ledger(consumed),
                "collar_disposition_ledger": module.ledger(collar),
            },
            "provenance": {"new_vertex_ledger": module.ledger(provenance_records)},
            "attributes": {
                "material_inventory": module.paired_ledger(materials),
                "uv_layer_inventory": module.paired_ledger(uv_layers),
                "shape_key_inventory": module.paired_ledger([]),
                "shape_key_disposition": "source_has_no_shape_keys",
            },
            "rig": {
                "armature_inventory": module.paired_ledger(armatures),
                "action_inventory": module.paired_ledger(actions),
            },
            "protected_records": {
                "outside_estar": {
                    domain: module.paired_ledger(records)
                    for domain, records in module.expected_outside_records(context).items()
                },
                "outer_boundary": {
                    domain: module.paired_ledger(records)
                    for domain, records in module.expected_outer_boundary_records(context).items()
                },
            },
            "render": {
                "triangle_ledger": module.ledger(
                    module.render_triangle_records(face_records, coordinate_map)
                )
            },
            "intersections": {
                "standalone_patch_pairs": module.ledger([]),
                "post_graft_patch_pairs": module.ledger([]),
                "new_noninherited_pairs": module.ledger([]),
                "inherited_nonpatch_pairs": module.paired_ledger(inherited_pairs),
            },
            "global_interface": {
                "coordinate_ledger": module.paired_ledger(interface_records),
                "legacy_source_world_coordinate_sha256": contract[
                    "intersection_and_interface_requirements"
                ]["legacy_source_world_coordinate_sha256"],
                "weld_ledger": module.ledger(welds),
            },
            "truth": {"state_ledger": module.ledger(truth_records)},
        }
        return module.finalize_evidence_digest(evidence)

    def evaluate(self, evidence: dict[str, object], *, production: bool = False):
        return self.module.evaluate_measured_candidate_evidence(
            evidence,
            self.contract if production else self.synthetic_contract,
            binding_root=ROOT,
            artifact_root=self.artifact_root,
        )

    def finalized(self, evidence: dict[str, object]) -> dict[str, object]:
        return self.module.finalize_evidence_digest(evidence)

    def test_01_parent_package_and_audit_remain_byte_exact(self) -> None:
        resolved = self.module.validate_parent_bindings(self.contract)
        self.assertEqual(len(resolved), 6)
        self.assertEqual(
            self.module.sha256_file(PARENT_PACKAGE / "INDEPENDENT_STATIC_AUDIT.md"),
            "83c80abf975bcf1c5148b71c130bf2ffaa9a243c61d670c3805269340b1f16af",
        )

    def test_02_current_static_package_has_no_candidate_and_fails_closed(self) -> None:
        result = self.module.static_evaluation()
        self.assertEqual(
            result["status"],
            "STATIC_R2_GATE_IMPLEMENTED_FUTURE_EVIDENCE_ABSENT_INDEPENDENT_AUDIT_REQUIRED",
        )
        self.assertEqual(
            result["future_measured_candidate"]["failure_names"],
            ["measured_candidate_evidence_absent"],
        )
        self.assertFalse(result["blender_used"])
        self.assertFalse(result["mesh_mutated"])
        self.assertFalse(result["execution_authority_granted"])

    def test_03_complete_synthetic_fixture_passes_all_record_bound_gates(self) -> None:
        result = self.evaluate(copy.deepcopy(self.nominal))
        self.assertTrue(result["eligible"], result["failure_names"])
        self.assertEqual(result["failure_names"], [])
        self.assertEqual(result["derived"]["new_interior_vertex_record_count"], 61)

    def test_04_production_quality_bound_rejects_unrepaired_source_sliver(self) -> None:
        result = self.evaluate(copy.deepcopy(self.nominal), production=True)
        self.assertFalse(result["eligible"])
        self.assertIn("render:minimum_triangle_angle", result["failure_names"])

    def test_05_every_required_top_level_record_section_is_fail_closed(self) -> None:
        for section in (
            "construction_run",
            "artifact",
            "topology",
            "scope",
            "provenance",
            "attributes",
            "rig",
            "protected_records",
            "render",
            "intersections",
            "global_interface",
            "truth",
        ):
            with self.subTest(section=section):
                evidence = copy.deepcopy(self.nominal)
                evidence.pop(section)
                self.finalized(evidence)
                result = self.evaluate(evidence)
                self.assertFalse(result["eligible"], section)

    def test_06_real_per_vertex_displacement_and_provenance_are_required(self) -> None:
        mutations = (
            lambda row: row.pop("displacement_m"),
            lambda row: row.__setitem__("displacement_m", [0.0, float("inf"), 0.0]),
            lambda row: row.__setitem__("source_triangle", [0, 1, 2]),
            lambda row: row.__setitem__("barycentric", [0.2, 0.2, 0.2]),
            lambda row: row.__setitem__("final_position_m", [0.0, 0.0, 0.0]),
        )
        for mutate in mutations:
            evidence = copy.deepcopy(self.nominal)
            row = evidence["provenance"]["new_vertex_ledger"]["records"][0]
            mutate(row)
            if not any(
                isinstance(value, float) and not math.isfinite(value)
                for value in row.get("displacement_m", [])
            ):
                evidence["provenance"]["new_vertex_ledger"] = self.module.ledger(
                    evidence["provenance"]["new_vertex_ledger"]["records"]
                )
                self.finalized(evidence)
            result = self.evaluate(evidence)
            self.assertFalse(result["eligible"])

    def test_07_exact_outer_coordinates_and_all_domain_records_are_required(self) -> None:
        for scope_name in ("outside_estar", "outer_boundary"):
            for domain in ("POINT", "EDGE", "FACE", "CORNER"):
                with self.subTest(scope=scope_name, domain=domain):
                    evidence = copy.deepcopy(self.nominal)
                    pair = evidence["protected_records"][scope_name][domain]
                    pair["candidate"]["records"].pop()
                    pair["candidate"] = self.module.ledger(pair["candidate"]["records"])
                    self.finalized(evidence)
                    result = self.evaluate(evidence)
                    self.assertFalse(result["eligible"])
        evidence = copy.deepcopy(self.nominal)
        pair = evidence["protected_records"]["outer_boundary"]["POINT"]
        pair["candidate"]["records"][0]["coordinate_m"][0] += 0.01
        pair["candidate"] = self.module.ledger(pair["candidate"]["records"])
        self.finalized(evidence)
        self.assertFalse(self.evaluate(evidence)["eligible"])

    def test_08_uv_normal_material_shape_key_and_native_weight_records_are_required(self) -> None:
        paths = (
            ("uv_records", []),
            ("normal", [float("nan"), 0.0, 1.0]),
            ("material_index", 4),
            ("shape_key_records", [{"name": "unbound", "delta_m": [0.0, 0.0, 0.0]}]),
            ("native_weights", []),
        )
        for key, value in paths:
            with self.subTest(key=key):
                evidence = copy.deepcopy(self.nominal)
                evidence["provenance"]["new_vertex_ledger"]["records"][0][key] = value
                if key != "normal":
                    evidence["provenance"]["new_vertex_ledger"] = self.module.ledger(
                        evidence["provenance"]["new_vertex_ledger"]["records"]
                    )
                    self.finalized(evidence)
                result = self.evaluate(evidence)
                self.assertFalse(result["eligible"])

    def test_09_armature_and_exact_action_inventories_are_record_bound(self) -> None:
        for inventory in ("armature_inventory", "action_inventory"):
            evidence = copy.deepcopy(self.nominal)
            evidence["rig"][inventory]["candidate"]["records"].pop()
            evidence["rig"][inventory]["candidate"] = self.module.ledger(
                evidence["rig"][inventory]["candidate"]["records"]
            )
            self.finalized(evidence)
            self.assertFalse(self.evaluate(evidence)["eligible"])

    def test_10_actual_ordered_schedule_is_bound_to_topology(self) -> None:
        evidence = copy.deepcopy(self.nominal)
        evidence["topology"]["ordered_stitch_schedule"]["sha256"] = "x" * 64
        self.finalized(evidence)
        result = self.evaluate(evidence)
        self.assertFalse(result["eligible"])
        self.assertIn("topology:ordered_stitch_schedule:digest", result["failure_names"])

        evidence = copy.deepcopy(self.nominal)
        evidence["topology"]["ordered_stitch_schedule"]["records"][0]["vertices"].reverse()
        evidence["topology"]["ordered_stitch_schedule"] = self.module.ledger(
            evidence["topology"]["ordered_stitch_schedule"]["records"]
        )
        self.finalized(evidence)
        result = self.evaluate(evidence)
        self.assertIn("topology:schedule_bound_to_faces", result["failure_names"])

    def test_11_preexisting_preserved_blend_cannot_be_the_measured_candidate(self) -> None:
        evidence = copy.deepcopy(self.nominal)
        source = evidence["construction_run"]["source"]
        evidence["artifact"]["path"] = source["path"]
        evidence["artifact"]["bytes"] = source["bytes"]
        evidence["artifact"]["sha256"] = source["sha256"]
        self.finalized(evidence)
        result = self.module.evaluate_measured_candidate_evidence(
            evidence,
            self.synthetic_contract,
            binding_root=ROOT,
            artifact_root=ROOT,
        )
        self.assertFalse(result["eligible"])
        self.assertIn("artifact:not_preexisting_source", result["failure_names"])

    def test_12_negative_noninteger_nan_and_infinite_values_are_rejected(self) -> None:
        mutations = []
        first = copy.deepcopy(self.nominal)
        first["topology"]["face_ledger"]["record_count"] = -1
        mutations.append(first)
        second = copy.deepcopy(self.nominal)
        second["render"]["triangle_ledger"]["records"][0]["area_m2"] = float("inf")
        mutations.append(second)
        third = copy.deepcopy(self.nominal)
        third["provenance"]["new_vertex_ledger"]["record_count"] = 61.0
        mutations.append(third)
        fourth = copy.deepcopy(self.nominal)
        fourth["global_interface"]["weld_ledger"]["records"][0]["residual_m"] = -0.1
        mutations.append(fourth)
        for evidence in mutations:
            result = self.evaluate(evidence)
            self.assertFalse(result["eligible"])

    def test_13_scalar_quality_claim_cannot_replace_render_ledger(self) -> None:
        evidence = copy.deepcopy(self.nominal)
        evidence["render"] = {
            "minimum_triangle_angle_degrees": 180.0,
            "minimum_triangle_area_m2": 999.0,
            "degenerate_triangle_count": 0,
        }
        self.finalized(evidence)
        result = self.evaluate(evidence)
        self.assertFalse(result["eligible"])
        self.assertIn("render:triangle_ledger:missing_ledger", result["failure_names"])

    def test_14_asserted_booleans_cannot_substitute_for_records(self) -> None:
        evidence = copy.deepcopy(self.nominal)
        evidence["attributes"]["all_uv_records_bound"] = True
        self.finalized(evidence)
        result = self.evaluate(evidence)
        self.assertFalse(result["eligible"])
        self.assertIn("asserted_boolean_not_measurement", result["failure_names"])

    def test_15_collision_and_interface_counts_require_exact_records(self) -> None:
        evidence = copy.deepcopy(self.nominal)
        evidence["intersections"]["inherited_nonpatch_pairs"]["candidate"]["records"].pop()
        evidence["intersections"]["inherited_nonpatch_pairs"]["candidate"] = self.module.ledger(
            evidence["intersections"]["inherited_nonpatch_pairs"]["candidate"]["records"]
        )
        self.finalized(evidence)
        self.assertFalse(self.evaluate(evidence)["eligible"])

        evidence = copy.deepcopy(self.nominal)
        evidence["global_interface"]["coordinate_ledger"]["candidate"]["records"][0][
            "coordinate_m"
        ][1] += 1e-3
        evidence["global_interface"]["coordinate_ledger"]["candidate"] = self.module.ledger(
            evidence["global_interface"]["coordinate_ledger"]["candidate"]["records"]
        )
        self.finalized(evidence)
        self.assertFalse(self.evaluate(evidence)["eligible"])

    def test_16_fresh_run_source_worker_config_and_evidence_hashes_are_exact(self) -> None:
        for binding in ("source", "worker", "config"):
            with self.subTest(binding=binding):
                evidence = copy.deepcopy(self.nominal)
                evidence["construction_run"][binding]["sha256"] = "0" * 64
                self.finalized(evidence)
                self.assertFalse(self.evaluate(evidence)["eligible"])
        evidence = copy.deepcopy(self.nominal)
        evidence["artifact"]["evidence_payload_sha256"] = "0" * 64
        result = self.evaluate(evidence)
        self.assertFalse(result["eligible"])

    def test_17_static_evaluator_has_no_blender_subprocess_or_write_path(self) -> None:
        source = MODULE_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        } | {
            node.module or ""
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        }
        self.assertNotIn("bpy", imports)
        self.assertNotIn("bmesh", imports)
        self.assertNotIn("subprocess", imports)
        for forbidden in (
            "write_text(",
            "write_bytes(",
            "save_as_mainfile",
            "open_mainfile",
            "bpy.ops",
            "blender.exe",
        ):
            self.assertNotIn(forbidden, source)

    def test_18_r2_package_inventory_is_exact_and_contains_no_body_artifact(self) -> None:
        expected = {
            "INTRINSIC_CURVED_ANNULUS_STRUCTURED_RETOPOLOGY_R2_CONTRACT.json",
            "INTRINSIC_CURVED_ANNULUS_STRUCTURED_RETOPOLOGY_R2_PROPOSAL.md",
            "CHECKPOINT.md",
            "PACKAGE_MANIFEST.json",
        }
        actual = {path.name for path in PACKAGE.iterdir() if path.is_file()}
        self.assertEqual(actual, expected)
        self.assertFalse(any(path.suffix.lower() == ".blend" for path in PACKAGE.iterdir()))
        self.assertFalse(
            any(path.suffix.lower() in {".png", ".jpg", ".jpeg"} for path in PACKAGE.iterdir())
        )


if __name__ == "__main__":
    unittest.main()
