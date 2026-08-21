from __future__ import annotations

import copy
import hashlib
import io
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import Core.avatar_anatomy_package as anatomy_package

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_SOURCE = PROJECT_ROOT / (
    "Avatar/avatar_builder/body_systems/"
    "kira_confirmed_adult_internal_pelvic_anatomy_module_contract_v1.json"
)
CLI = PROJECT_ROOT / "tools/evaluate_avatar_anatomy_package_preflight.py"

from Core.avatar_anatomy_package import (  # noqa: E402
    AvatarAnatomyPackageError,
    HRA_SOURCE_ROLE_MAP,
    PREFLIGHT_BLOCKED_CARRIER_UNACCEPTED,
    PREFLIGHT_BLOCKED_MISSING_STRUCTURES,
    READY_FOR_PRIVATE_INACTIVE_AUTHORING,
    REQUEST_SCHEMA,
    SOURCE_INTAKE_VALIDATED_COMPLETE,
    SOURCE_INTAKE_VALIDATED_INCOMPLETE,
    canonical_json_bytes,
    canonical_sha256,
    evaluate_avatar_anatomy_package_preflight,
    sha256_file,
)


IDENTITY_MATRIX = [
    1.0,
    0.0,
    0.0,
    0.0,
    0.0,
    1.0,
    0.0,
    0.0,
    0.0,
    0.0,
    1.0,
    0.0,
    0.0,
    0.0,
    0.0,
    1.0,
]

HRA_FILES = {
    "SBU_F_Intestine_Large.glb": 10,
    "VH_F_Fallopian_Tube_L.glb": 4,
    "VH_F_Fallopian_Tube_R.glb": 4,
    "VH_F_Ovary_L.glb": 1,
    "VH_F_Ovary_R.glb": 1,
    "VH_F_Pelvis.glb": 14,
    "VH_F_Ureter_L.glb": 27,
    "VH_F_Ureter_R.glb": 25,
    "VH_F_Urinary_Bladder.glb": 6,
    "VH_F_Uterus.glb": 10,
}

HRA_AVAILABLE_COMPONENTS = {
    "bladder_shell": "VH_F_Urinary_Bladder.glb",
    "bladder_neck_trigone_marker": "VH_F_Urinary_Bladder.glb",
    "ureter_stub_left": "VH_F_Ureter_L.glb",
    "ureter_stub_right": "VH_F_Ureter_R.glb",
    "cervix": "VH_F_Uterus.glb",
    "uterine_body_fundus": "VH_F_Uterus.glb",
    "uterine_tube_left": "VH_F_Fallopian_Tube_L.glb",
    "uterine_tube_right": "VH_F_Fallopian_Tube_R.glb",
    "ovary_left": "VH_F_Ovary_L.glb",
    "ovary_right": "VH_F_Ovary_R.glb",
    "distal_bowel_stub": "SBU_F_Intestine_Large.glb",
    "rectum": "SBU_F_Intestine_Large.glb",
    "bony_pelvis_proxy": "VH_F_Pelvis.glb",
}

MATERIAL_FOR_SYSTEM = {
    "urinary": "clinical_urinary",
    "reproductive": "clinical_reproductive",
    "posterior_bowel": "clinical_bowel",
    "support": "clinical_support",
    "orientation": "clinical_landmark",
}


def hra_mesh_names_by_file() -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for source_file, mesh_count in HRA_FILES.items():
        names: list[str] = []
        for role_bindings in HRA_SOURCE_ROLE_MAP.values():
            for name in role_bindings.get(source_file, ()):
                if name not in names:
                    names.append(name)
        while len(names) < mesh_count:
            names.append(f"unmapped_hra_reference_{Path(source_file).stem}_{len(names)}")
        if len(names) != mesh_count:
            raise AssertionError(f"test HRA role nodes exceed manifest mesh_count: {source_file}")
        result[source_file] = names
    return result


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


def write_glb(path: Path, mesh_names: list[str]) -> None:
    mesh_count = len(mesh_names)
    binary_payload = b"".join(
        struct.pack("<fff", float(index), 0.0, 0.0) for index in range(mesh_count)
    )
    document = {
        "asset": {"version": "2.0", "generator": "unit-test-read-only-source"},
        "meshes": [
            {
                "name": mesh_names[index],
                "primitives": [{"attributes": {"POSITION": index}}],
            }
            for index in range(mesh_count)
        ],
        "buffers": [{"byteLength": len(binary_payload)}],
        "bufferViews": [
            {"buffer": 0, "byteOffset": index * 12, "byteLength": 12}
            for index in range(mesh_count)
        ],
        "accessors": [
            {
                "bufferView": index,
                "componentType": 5126,
                "count": 1,
                "type": "VEC3",
            }
            for index in range(mesh_count)
        ],
        "nodes": [
            {"mesh": index, "name": mesh_names[index]}
            for index in range(mesh_count)
        ],
        "scene": 0,
        "scenes": [{"nodes": list(range(mesh_count))}],
    }
    payload = canonical_json_bytes(document)
    payload += b" " * ((4 - len(payload) % 4) % 4)
    total_length = 12 + 8 + len(payload) + 8 + len(binary_payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        struct.pack("<4sII", b"glTF", 2, total_length)
        + struct.pack("<II", len(payload), 0x4E4F534A)
        + payload
        + struct.pack("<II", len(binary_payload), 0x004E4942)
        + binary_payload
    )


def binding(path: Path, root: Path, prefix: str = "") -> dict[str, object]:
    names = {
        "path": path.resolve().relative_to(root.resolve()).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }
    if not prefix:
        return names
    return {
        f"{prefix}_path": names["path"],
        f"{prefix}_bytes": names["bytes"],
        f"{prefix}_sha256": names["sha256"],
    }


class AnatomyFixture:
    def __init__(self, root: Path, *, complete: bool = True, owner_accepted: bool = True) -> None:
        self.root = root
        self.authority_id = (
            "synthetic_complete_adult_pelvic_v1"
            if complete
            else "synthetic_hra_incomplete_pelvic_v1"
        )
        self.carrier_authority_id = "synthetic_qualified_carrier_v1"
        self.contract = json.loads(CONTRACT_SOURCE.read_text(encoding="utf-8"))
        self.contract_path = root / "Contracts/pelvic_contract.json"
        self.contract_path.parent.mkdir(parents=True, exist_ok=True)
        self.contract_path.write_bytes(CONTRACT_SOURCE.read_bytes())

        inventory = {
            anatomy_id: system
            for system, anatomy_ids in self.contract["required_module_meshes"].items()
            for anatomy_id in anatomy_ids
        }
        required_anchor_ids = self.contract["attachment_interface"]["required_anchor_ids"]
        mesh_names_by_file = hra_mesh_names_by_file()
        if complete:
            direct_names = list(dict.fromkeys(sorted(inventory) + list(required_anchor_ids)))
            direct_index = 0
            for source_file in HRA_FILES:
                for mesh_index in range(len(mesh_names_by_file[source_file])):
                    if direct_index >= len(direct_names):
                        break
                    mesh_names_by_file[source_file][mesh_index] = direct_names[direct_index]
                    direct_index += 1
            if direct_index != len(direct_names):
                raise AssertionError("synthetic source fixture has insufficient mesh slots")

        self.sources = root / "Sources/hra_female_pelvis_cc_by_4_v1_2"
        self.source_records: list[dict[str, object]] = []
        for name, mesh_count in HRA_FILES.items():
            path = self.sources / name
            write_glb(path, mesh_names_by_file[name])
            self.source_records.append(
                {
                    "path": name,
                    "bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                    "url": (
                        "https://ccf-ontology.hubmapconsortium.org/objects/v1.2/"
                        f"{name}"
                    ),
                    "mesh_count": mesh_count,
                }
            )
        self.source_manifest = {
            "schema": "kira.avatar.medical_reference.hra_female_pelvis_intake.v1",
            "status": "SOURCE_REFERENCE_ONLY_NOT_A_BODY_NOT_FUNCTIONAL",
            "retrieved_utc_date": "2026-08-09",
            "source_collection": {
                "name": "Human Reference Atlas 3D Reference Object Library",
                "portal": "https://humanatlas.io/3d-reference-library",
                "license": "CC BY 4.0",
                "license_url": "https://creativecommons.org/licenses/by/4.0/",
                "visible_human_source": (
                    "https://www.nlm.nih.gov/research/visible/visible_human.html"
                ),
                "attribution": (
                    "Human Reference Atlas / HuBMAP CCF 3D Reference Object Library; "
                    "source anatomy derived from the NLM Visible Human Dataset."
                ),
            },
            "validation": {
                "glb_magic": "glTF",
                "glb_version": 2,
                "declared_length_matches_file": True,
                "json_chunk_decoded": True,
                "all_files_passed": True,
            },
            "files": self.source_records,
            "truth_boundary": [
                "REFERENCE_GEOMETRY_ONLY",
                "NO_KIRA_BODY_CREATED_OR_CHANGED",
                "NO_EXTERNAL_ANATOMY_REPLACEMENT",
                "NO_PHYSIOLOGICAL_OR_SUBJECTIVE_FUNCTION_CLAIM",
                "NO_RUNTIME_ACTIVATION_OR_ASSIGNMENT",
                "PRIVATE_CLINICAL_REVIEW_DERIVATIVES_ONLY",
            ],
        }
        self.source_manifest_path = self.sources / "SOURCE_MANIFEST.json"
        write_json(self.source_manifest_path, self.source_manifest)

        node_locations = {
            node_name: source_file
            for source_file, node_names in mesh_names_by_file.items()
            for node_name in node_names
        }
        if complete:
            source_roles = [
                {
                    "source_file": node_locations[anatomy_id],
                    "anatomy_id": anatomy_id,
                    "system": inventory[anatomy_id],
                    "laterality": (
                        "left"
                        if anatomy_id.endswith("_left")
                        else "right"
                        if anatomy_id.endswith("_right")
                        else "midline"
                    ),
                    "source_nodes": [anatomy_id],
                    "function_implemented": False,
                }
                for anatomy_id in sorted(inventory)
            ]
            external_anchor_references = {
                anchor_id: anchor_id for anchor_id in required_anchor_ids
            }
        else:
            source_roles = []
            for anatomy_id, bindings_by_file in HRA_SOURCE_ROLE_MAP.items():
                source_file, source_nodes = next(iter(bindings_by_file.items()))
                source_roles.append(
                    {
                        "source_file": source_file,
                        "anatomy_id": anatomy_id,
                        "system": inventory[anatomy_id],
                        "laterality": (
                            "left"
                            if anatomy_id.endswith("_left")
                            else "right"
                            if anatomy_id.endswith("_right")
                            else "bilateral"
                            if anatomy_id == "bony_pelvis_proxy"
                            else "midline"
                        ),
                        "source_nodes": list(source_nodes),
                        "function_implemented": False,
                    }
                )
            external_anchor_references = {
                "female_external_urethral_opening": None,
                "vaginal_opening_introitus": None,
                "anal_opening": None,
                "pubic_reference": "VH_F_pubis",
                "sacral_reference": "VH_F_sacrum",
                "pelvic_side_left": "VH_F_ilium_compact_bone_L",
                "pelvic_side_right": "VH_F_ilium_compact_bone_R",
                "perineal_body": None,
            }
        self.role_map = {
            "schema_version": 1,
            "role_map_id": (
                "synthetic_complete_adult_pelvic_role_map_v1"
                if complete
                else "hra_female_pelvis_cc_by_4_v1_2_to_kira_internal_pelvic_contract_v1"
            ),
            "status": (
                "SOURCE_ROLE_MAP_COMPLETE_NORMALIZATION_DECLARED"
                if complete
                else "SOURCE_ROLE_MAP_INCOMPLETE_NORMALIZATION_NOT_RUN"
            ),
            "source_manifest": binding(self.source_manifest_path, root),
            "anatomy_contract": binding(self.contract_path, root),
            "license": {
                "id": "CC-BY-4.0",
                "url": "https://creativecommons.org/licenses/by/4.0/",
                "attribution": self.source_manifest["source_collection"]["attribution"],
                "adaptation_notice_required": True,
                "private_clinical_review_derivatives_only": True,
            },
            "normalization": {
                "source_format": "glTF-2.0-binary",
                "source_units": "meters",
                "source_axes": "gltf_right_handed_y_up",
                "target_units": "meters",
                "target_axes": "blender_right_handed_z_up",
                "per_source_transform": None,
                "transform_sha256": None,
                "status": "REQUIRED_NOT_RUN",
            },
            "source_roles": source_roles,
            "external_anchor_references": external_anchor_references,
            "truth_limits": {
                "source_role_is_authored_component": False,
                "normalization_or_carrier_fit_completed": False,
                "external_anatomy_complete": False,
                "internal_anatomy_complete": False,
                "function_implemented": False,
                "runtime_activation_allowed": False,
                "public_export_allowed": False,
            },
        }
        self.role_map_path = self.sources / "ANATOMY_ROLE_MAP_V1.json"
        write_json(self.role_map_path, self.role_map)

        self.carrier_path = root / "Carrier/generic_makehuman_adult_female.blend"
        self.carrier_path.parent.mkdir(parents=True, exist_ok=True)
        self.carrier_path.write_bytes(b"BLENDER-v1-qualified-inactive-fixture\x00")
        carrier_sha = sha256_file(self.carrier_path)
        self.qualification = {
            "schema_version": 1,
            "artifact_type": "adult_foundation_qualification_result",
            "foundation_id": "generic_makehuman_adult_female_foundation_v1",
            "status": "QUALIFIED_INACTIVE",
            "source_artifact": {
                "path": self.carrier_path.relative_to(root).as_posix(),
                "sha256": carrier_sha,
            },
            "qualified_for_adult_foundation": True,
            "adult_eligible": True,
            "complete_adult_topology_proven": True,
            "blockers": [],
            "build_performed_by_evaluator": False,
            "render_performed": False,
            "export_performed": False,
            "runtime_mutation_performed": False,
            "runtime_activation_allowed": False,
            "public_export_allowed": False,
            "clothing_applied": False,
            "armature_present": True,
            "pose_space_deformation_audit_passed": True,
        }
        self.qualification_path = root / "Carrier/QUALIFICATION.json"
        write_json(self.qualification_path, self.qualification)
        self.owner = {
            "schema_version": 1,
            "artifact_type": "private_inactive_carrier_owner_acceptance",
            "status": "OWNER_ACCEPTED_PRIVATE_INACTIVE_CARRIER",
            "candidate_id": "generic_makehuman_adult_female",
            "foundation_id": "generic_makehuman_adult_female_foundation_v1",
            "carrier_sha256": carrier_sha,
            "owner_approved": owner_accepted,
            "runtime_activation_allowed": False,
            "public_export_allowed": False,
        }
        if not owner_accepted:
            self.owner["status"] = "PENDING_OWNER_REVIEW"
        self.owner_path = root / "Carrier/OWNER_ACCEPTANCE.json"
        write_json(self.owner_path, self.owner)

        file_records = {record["path"]: record for record in self.source_records}
        components = []
        for source_role in source_roles:
            anatomy_id = source_role["anatomy_id"]
            source_name = source_role["source_file"]
            system = source_role["system"]
            components.append(
                {
                    "anatomy_id": anatomy_id,
                    "system": system,
                    "laterality": source_role["laterality"],
                    "source_file": source_name,
                    "source_file_sha256": file_records[source_name]["sha256"],
                    "source_nodes": list(source_role["source_nodes"]),
                    "review_visibility": "PRIVATE_INACTIVE_DEFAULT_HIDDEN",
                    "material_id": MATERIAL_FOR_SYSTEM[system],
                    "source_contract_id": self.contract["contract_id"],
                    "function_implemented": False,
                }
            )

        normalization_without_hash = {
            "source_units": "meters",
            "target_units": "meters",
            "source_axes": {"up": "+Y", "forward": "+Z", "handedness": "right"},
            "target_axes": {"up": "+Z", "forward": "-Y", "handedness": "right"},
            "per_source_transform": {
                name: [
                    1.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    -1.0,
                    0.0,
                    0.0,
                    1.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    1.0,
                ]
                for name in HRA_FILES
            },
        }
        normalization = copy.deepcopy(normalization_without_hash)
        normalization["transform_sha256"] = canonical_sha256(normalization_without_hash)

        truth = {
            key: False
            for key, expected in self.contract["truth_limits"].items()
            if expected is False
        }
        truth.update(
            {
                "external_anatomy_complete": False,
                "internal_anatomy_complete": False,
                "whole_body_complete": False,
                "function_implemented": False,
                "owner_approved": False,
                "runtime_activation_allowed": False,
                "public_export_allowed": False,
                "geometry_proves_biological_function": False,
                "eating_implemented": False,
                "drinking_implemented": False,
                "swallowing_implemented": False,
                "digestion_implemented": False,
                "nutrient_absorption_implemented": False,
                "relationship_status_proven": False,
                "consent_proven": False,
                "activity_proven": False,
                "fertility_implemented": False,
                "conception_implemented": False,
                "delivery_implemented": False,
                "postpartum_implemented": False,
                "family_relationships_proven": False,
            }
        )
        anchors = []
        for anchor_id in required_anchor_ids:
            source_node = external_anchor_references[anchor_id]
            if source_node is None or source_node not in node_locations:
                continue
            source_file = node_locations[source_node]
            anchors.append(
                {
                    "anchor_id": anchor_id,
                    "source_file": source_file,
                    "source_node": source_node,
                    "source_bound": True,
                    "authored": False,
                    "transform": normalization["per_source_transform"][source_file],
                }
            )
        self.request = {
            "schema": REQUEST_SCHEMA,
            "schema_version": 1,
            "status": "PREFLIGHT_REQUESTED",
            "package_id": "kira_adult_anatomy_package_v1",
            "candidate_id": "generic_makehuman_adult_female",
            "subject_id": "kira",
            "maturity_status": "confirmed_adult",
            "anatomy_profile_id": "confirmed_adult_female_internal_pelvic_v1",
            "contract": binding(self.contract_path, root),
            "source_package": {
                "authority_id": self.authority_id,
                **binding(self.source_manifest_path, root, "manifest"),
                **binding(self.role_map_path, root, "role_map"),
            },
            "carrier": {
                "authority_id": self.carrier_authority_id,
                **binding(self.carrier_path, root),
                "foundation_id": "generic_makehuman_adult_female_foundation_v1",
                **binding(self.qualification_path, root, "qualification_manifest"),
                **binding(self.owner_path, root, "owner_acceptance"),
                "rest_pose_matrix": copy.deepcopy(IDENTITY_MATRIX),
                "object_ids": ["body", "eyes"],
                "armature_id": "rig",
                "source_hash_before": carrier_sha,
                "source_hash_after": carrier_sha,
            },
            "normalization": normalization,
            "components": components,
            "anchors": anchors,
            "routes": [
                {
                    "route_id": "urinary",
                    "ordered_anatomy_ids": ["bladder_shell", "female_urethra_shell"],
                    "external_endpoint_anchor_id": "female_external_urethral_opening",
                    "exclusive": True,
                },
                {
                    "route_id": "reproductive",
                    "ordered_anatomy_ids": [
                        "vaginal_canal",
                        "cervix",
                        "uterine_body_fundus",
                    ],
                    "external_endpoint_anchor_id": "vaginal_opening_introitus",
                    "exclusive": True,
                },
                {
                    "route_id": "bowel",
                    "ordered_anatomy_ids": ["rectum", "anal_canal"],
                    "external_endpoint_anchor_id": "anal_opening",
                    "exclusive": True,
                },
            ],
            "separation": {
                "separate_artifact": True,
                "default_hidden": True,
                "carrier_dependency_mode": "READ_ONLY_TRANSFORM_FOLLOWING_ONLY",
                "module_local_armature_or_deformer": True,
                "forbidden_carrier_writes": self.contract["attachment_interface"][
                    "forbidden_carrier_writes"
                ],
                "carrier_write_operations": [],
                "contains_hair": False,
                "contains_clothing": False,
            },
            "truth": truth,
        }
        self.authority_record = {
            "source_manifest_sha256": sha256_file(self.source_manifest_path),
            "role_map_sha256": sha256_file(self.role_map_path),
            "contract_sha256": sha256_file(self.contract_path),
            "allow_direct_semantic_nodes": complete,
        }
        self.carrier_authority_record = {
            "carrier_sha256": sha256_file(self.carrier_path),
            "qualification_manifest_sha256": sha256_file(self.qualification_path),
            "owner_acceptance_sha256": sha256_file(self.owner_path),
            "object_ids": ["body", "eyes"],
            "armature_id": "rig",
            "rest_pose_matrix": copy.deepcopy(IDENTITY_MATRIX),
        }

    def rewrite_source_manifest(self, *, reauthorize: bool = True) -> None:
        write_json(self.source_manifest_path, self.source_manifest)
        self.request["source_package"].update(
            binding(self.source_manifest_path, self.root, "manifest")
        )
        if reauthorize:
            self.authority_record["source_manifest_sha256"] = sha256_file(
                self.source_manifest_path
            )

    def rewrite_owner(self) -> None:
        write_json(self.owner_path, self.owner)
        self.request["carrier"].update(binding(self.owner_path, self.root, "owner_acceptance"))
        self.carrier_authority_record["owner_acceptance_sha256"] = sha256_file(
            self.owner_path
        )

    def rewrite_qualification(self) -> None:
        write_json(self.qualification_path, self.qualification)
        self.request["carrier"].update(
            binding(self.qualification_path, self.root, "qualification_manifest")
        )
        self.carrier_authority_record["qualification_manifest_sha256"] = sha256_file(
            self.qualification_path
        )

    def rewrite_role_map(self) -> None:
        write_json(self.role_map_path, self.role_map)
        self.request["source_package"].update(
            binding(self.role_map_path, self.root, "role_map")
        )
        self.authority_record["role_map_sha256"] = sha256_file(self.role_map_path)


class AvatarAnatomyPackagePreflightTests(unittest.TestCase):
    def make_fixture(self, *, complete: bool = True, owner_accepted: bool = True) -> AnatomyFixture:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        fixture = AnatomyFixture(
            Path(temporary.name),
            complete=complete,
            owner_accepted=owner_accepted,
        )
        registry_patch = mock.patch.dict(
            anatomy_package.SUPPORTED_SOURCE_PACKAGES,
            {fixture.authority_id: fixture.authority_record},
            clear=False,
        )
        registry_patch.start()
        self.addCleanup(registry_patch.stop)
        carrier_registry_patch = mock.patch.dict(
            anatomy_package.SUPPORTED_CARRIER_AUTHORITIES,
            {fixture.carrier_authority_id: fixture.carrier_authority_record},
            clear=False,
        )
        carrier_registry_patch.start()
        self.addCleanup(carrier_registry_patch.stop)
        return fixture

    def test_hra_shaped_current_subset_is_explicitly_incomplete(self) -> None:
        fixture = self.make_fixture(complete=False)
        before = {path.name: sha256_file(path) for path in fixture.sources.glob("*.glb")}
        report = evaluate_avatar_anatomy_package_preflight(fixture.root, fixture.request)
        after = {path.name: sha256_file(path) for path in fixture.sources.glob("*.glb")}

        self.assertEqual(report["status"], PREFLIGHT_BLOCKED_MISSING_STRUCTURES)
        self.assertEqual(report["source_intake_status"], SOURCE_INTAKE_VALIDATED_INCOMPLETE)
        self.assertEqual(report["mapped_structure_count"], 13)
        self.assertEqual(report["required_structure_count"], 28)
        self.assertEqual(len(report["missing_required_structures"]), 15)
        self.assertEqual(report["source_package"]["mapped_role_count"], 13)
        self.assertEqual(report["source_package"]["contract_role_count"], 28)
        self.assertEqual(report["source_package"]["missing_contract_role_count"], 15)
        self.assertEqual(report["source_package"]["null_anchor_reference_count"], 4)
        for known_gap in (
            "female_urethra_shell",
            "vaginal_canal",
            "uterine_cavity_endometrium_display_layer",
            "anal_canal",
            "anal_sphincter_complex_marker",
            "pelvic_diaphragm_proxy",
            "perineal_body",
        ):
            self.assertIn(known_gap, report["missing_required_structures"])
        self.assertNotIn("bladder_neck_trigone_marker", report["missing_required_structures"])
        self.assertFalse(report["build_performed"])
        self.assertFalse(report["blender_invoked"])
        self.assertEqual(before, after)
        self.assertTrue(report["read_only_evidence"]["artifacts_unchanged"])

    def test_complete_synthetic_package_is_ready_and_receipt_is_deterministic(self) -> None:
        fixture = self.make_fixture()
        first = evaluate_avatar_anatomy_package_preflight(fixture.root, fixture.request)
        second = evaluate_avatar_anatomy_package_preflight(fixture.root, fixture.request)

        self.assertEqual(first["status"], READY_FOR_PRIVATE_INACTIVE_AUTHORING)
        self.assertEqual(first["source_intake_status"], SOURCE_INTAKE_VALIDATED_COMPLETE)
        self.assertEqual(first["blockers"], [])
        self.assertEqual(first["missing_required_structures"], [])
        self.assertEqual(first["mapped_structure_count"], first["required_structure_count"])
        self.assertEqual(first["preflight_receipt_sha256"], second["preflight_receipt_sha256"])
        self.assertEqual(first["preflight_receipt_sha256"], canonical_sha256({
            key: value for key, value in first.items() if key != "preflight_receipt_sha256"
        }))
        self.assertTrue(first["authoring_authority"]["readiness_only_not_execution_authority"])
        self.assertTrue(first["authoring_authority"]["separate_versioned_authorization_required"])
        self.assertFalse(first["authoring_authority"]["private_inactive_authoring_allowed"])
        self.assertFalse(first["authoring_authority"]["blender_execution_allowed"])
        self.assertFalse(first["authoring_authority"]["carrier_mutation_allowed"])
        self.assertFalse(first["authoring_authority"]["runtime_activation_allowed"])
        self.assertFalse(first["authoring_authority"]["public_export_allowed"])
        self.assertEqual(first["scope"]["region"], "internal_pelvis")
        self.assertFalse(first["scope"]["whole_body_complete"])
        self.assertFalse(first["scope"]["external_anatomy_complete"])
        for nonclaim in (
            "eating_implemented",
            "drinking_implemented",
            "swallowing_implemented",
            "digestion_implemented",
            "nutrient_absorption_implemented",
            "relationship_status_proven",
            "consent_proven",
            "activity_proven",
            "fertility_implemented",
            "conception_implemented",
            "delivery_implemented",
            "postpartum_implemented",
            "family_relationships_proven",
        ):
            self.assertIs(first["truth"][nonclaim], False)
        self.assertFalse(first["separation"]["contains_hair"])
        self.assertFalse(first["separation"]["contains_clothing"])

    def test_unaccepted_carrier_has_distinct_blocked_status(self) -> None:
        fixture = self.make_fixture(owner_accepted=False)
        report = evaluate_avatar_anatomy_package_preflight(fixture.root, fixture.request)
        self.assertEqual(report["status"], PREFLIGHT_BLOCKED_CARRIER_UNACCEPTED)
        self.assertIn("carrier_owner_acceptance_missing_or_false", report["blockers"])
        self.assertFalse(report["carrier"]["owner_accepted"])

    def test_qualified_but_unrigged_makehuman_shaped_carrier_stays_blocked(self) -> None:
        fixture = self.make_fixture()
        fixture.qualification["armature_present"] = False
        fixture.qualification.pop("pose_space_deformation_audit_passed")
        fixture.rewrite_qualification()
        fixture.carrier_authority_record["armature_id"] = None
        fixture.request["carrier"]["armature_id"] = None
        report = evaluate_avatar_anatomy_package_preflight(fixture.root, fixture.request)
        self.assertEqual(report["status"], PREFLIGHT_BLOCKED_CARRIER_UNACCEPTED)
        self.assertIn("carrier_armature_not_qualified", report["blockers"])
        self.assertIn("carrier_pose_space_deformation_not_qualified", report["blockers"])
        self.assertIsNone(report["carrier"]["armature_id"])

        fixture.qualification["armature_present"] = True
        fixture.qualification["pose_space_deformation_audit_passed"] = True
        fixture.rewrite_qualification()
        with self.assertRaisesRegex(AvatarAnatomyPackageError, "armature_id may be null"):
            evaluate_avatar_anatomy_package_preflight(fixture.root, fixture.request)

    def test_anatomy_profile_is_exactly_bound_to_canonical_contract(self) -> None:
        fixture = self.make_fixture()
        fixture.request["anatomy_profile_id"] = "unrelated_whole_body_profile"
        with self.assertRaisesRegex(AvatarAnatomyPackageError, "not bound"):
            evaluate_avatar_anatomy_package_preflight(fixture.root, fixture.request)

    def test_exact_bytes_and_hashes_fail_closed_after_source_tamper(self) -> None:
        fixture = self.make_fixture()
        source = fixture.sources / next(iter(HRA_FILES))
        source.write_bytes(source.read_bytes() + b"tamper")
        with self.assertRaisesRegex(AvatarAnatomyPackageError, "byte count mismatch"):
            evaluate_avatar_anatomy_package_preflight(fixture.root, fixture.request)

    def test_glb2_structure_is_revalidated_not_trusted_from_manifest(self) -> None:
        fixture = self.make_fixture()
        name = next(iter(HRA_FILES))
        source = fixture.sources / name
        source.write_bytes(b"not-a-glb")
        record = next(item for item in fixture.source_records if item["path"] == name)
        record["bytes"] = source.stat().st_size
        record["sha256"] = sha256_file(source)
        fixture.rewrite_source_manifest()
        for component in fixture.request["components"]:
            if component["source_file"] == name:
                component["source_file_sha256"] = record["sha256"]
        with self.assertRaisesRegex(AvatarAnatomyPackageError, "truncated GLB|not a GLB"):
            evaluate_avatar_anatomy_package_preflight(fixture.root, fixture.request)

    def test_license_and_attribution_are_required_and_bound(self) -> None:
        fixture = self.make_fixture()
        fixture.source_manifest["source_collection"]["attribution"] = ""
        fixture.rewrite_source_manifest()
        with self.assertRaisesRegex(AvatarAnatomyPackageError, "source attribution"):
            evaluate_avatar_anatomy_package_preflight(fixture.root, fixture.request)

        fixture.source_manifest["source_collection"]["attribution"] = "HRA attribution"
        fixture.source_manifest["source_collection"]["license"] = "unknown"
        fixture.rewrite_source_manifest()
        with self.assertRaisesRegex(AvatarAnatomyPackageError, "unsupported source license"):
            evaluate_avatar_anatomy_package_preflight(fixture.root, fixture.request)

    def test_normalization_requires_exact_coverage_axes_units_and_hash(self) -> None:
        fixture = self.make_fixture()
        fixture.request["normalization"]["target_units"] = "centimeters"
        with self.assertRaisesRegex(AvatarAnatomyPackageError, "target_units must be meters"):
            evaluate_avatar_anatomy_package_preflight(fixture.root, fixture.request)

        fixture = self.make_fixture()
        fixture.request["normalization"]["per_source_transform"].pop(next(iter(HRA_FILES)))
        with self.assertRaisesRegex(AvatarAnatomyPackageError, "exactly cover source files"):
            evaluate_avatar_anatomy_package_preflight(fixture.root, fixture.request)

        fixture = self.make_fixture()
        fixture.request["normalization"]["transform_sha256"] = "0" * 64
        with self.assertRaisesRegex(AvatarAnatomyPackageError, "transform_sha256 mismatch"):
            evaluate_avatar_anatomy_package_preflight(fixture.root, fixture.request)

        fixture = self.make_fixture()
        normalization = fixture.request["normalization"]
        normalization["per_source_transform"] = {
            name: IDENTITY_MATRIX for name in HRA_FILES
        }
        normalization_without_hash = {
            key: value for key, value in normalization.items() if key != "transform_sha256"
        }
        normalization["transform_sha256"] = canonical_sha256(normalization_without_hash)
        with self.assertRaisesRegex(AvatarAnatomyPackageError, "declared up axis"):
            evaluate_avatar_anatomy_package_preflight(fixture.root, fixture.request)

        fixture = self.make_fixture()
        normalization = fixture.request["normalization"]
        normalization["source_axes"] = copy.deepcopy(normalization["target_axes"])
        normalization["per_source_transform"] = {
            name: IDENTITY_MATRIX for name in HRA_FILES
        }
        normalization_without_hash = {
            key: value for key, value in normalization.items() if key != "transform_sha256"
        }
        normalization["transform_sha256"] = canonical_sha256(normalization_without_hash)
        with self.assertRaisesRegex(AvatarAnatomyPackageError, "pinned source role map"):
            evaluate_avatar_anatomy_package_preflight(fixture.root, fixture.request)

        fixture = self.make_fixture()
        normalization = fixture.request["normalization"]
        for matrix in normalization["per_source_transform"].values():
            matrix[3] = 1.0e9
            matrix[7] = -1.0e9
            matrix[11] = 1.0e9
        normalization_without_hash = {
            key: value for key, value in normalization.items() if key != "transform_sha256"
        }
        normalization["transform_sha256"] = canonical_sha256(normalization_without_hash)
        with self.assertRaisesRegex(AvatarAnatomyPackageError, "zero-translation"):
            evaluate_avatar_anatomy_package_preflight(fixture.root, fixture.request)

    def test_ready_requires_real_unique_mesh_bound_source_names(self) -> None:
        fixture = self.make_fixture()
        fixture.request["components"][0]["source_nodes"] = ["invented_missing_mesh"]
        with self.assertRaisesRegex(AvatarAnatomyPackageError, "source_nodes differ"):
            evaluate_avatar_anatomy_package_preflight(fixture.root, fixture.request)

        fixture = self.make_fixture(complete=False)
        bladder = next(
            item for item in fixture.request["components"] if item["anatomy_id"] == "bladder_shell"
        )
        bladder["source_nodes"] = bladder["source_nodes"][:-1]
        with self.assertRaisesRegex(AvatarAnatomyPackageError, "source_nodes differ"):
            evaluate_avatar_anatomy_package_preflight(fixture.root, fixture.request)

    def test_role_map_rejects_semantic_spoofing_of_missing_anatomy(self) -> None:
        fixture = self.make_fixture()
        vaginal_role = next(
            item for item in fixture.role_map["source_roles"] if item["anatomy_id"] == "vaginal_canal"
        )
        pelvis_role = next(
            item for item in fixture.role_map["source_roles"] if item["anatomy_id"] == "bony_pelvis_proxy"
        )
        vaginal_role["source_file"] = pelvis_role["source_file"]
        vaginal_role["source_nodes"] = list(pelvis_role["source_nodes"])
        fixture.rewrite_role_map()
        vaginal_component = next(
            item for item in fixture.request["components"] if item["anatomy_id"] == "vaginal_canal"
        )
        vaginal_component["source_file"] = pelvis_role["source_file"]
        source_record = next(
            item
            for item in fixture.source_records
            if item["path"] == pelvis_role["source_file"]
        )
        vaginal_component["source_file_sha256"] = source_record["sha256"]
        vaginal_component["source_nodes"] = list(pelvis_role["source_nodes"])
        with self.assertRaisesRegex(AvatarAnatomyPackageError, "semantics are not recognized"):
            evaluate_avatar_anatomy_package_preflight(fixture.root, fixture.request)

    def test_canonical_contract_and_bounded_hra_provenance_cannot_be_self_reissued(self) -> None:
        fixture = self.make_fixture()
        fixture.contract["scope"]["blender_execution_authorized"] = True
        write_json(fixture.contract_path, fixture.contract)
        fixture.request["contract"] = binding(fixture.contract_path, fixture.root)
        with self.assertRaisesRegex(AvatarAnatomyPackageError, "canonical contract"):
            evaluate_avatar_anatomy_package_preflight(fixture.root, fixture.request)

        fixture = self.make_fixture()
        fixture.source_manifest["schema"] = "attacker.source.schema"
        fixture.rewrite_source_manifest(reauthorize=False)
        with self.assertRaisesRegex(AvatarAnatomyPackageError, "not pinned"):
            evaluate_avatar_anatomy_package_preflight(fixture.root, fixture.request)

        fixture = self.make_fixture()
        fixture.source_manifest["source_collection"]["license_url"] = (
            "https://example.invalid/not-the-license"
        )
        fixture.rewrite_source_manifest()
        with self.assertRaisesRegex(AvatarAnatomyPackageError, "does not match"):
            evaluate_avatar_anatomy_package_preflight(fixture.root, fixture.request)

    def test_carrier_header_and_closed_authority_fields_fail_closed(self) -> None:
        fixture = self.make_fixture()
        fixture.carrier_path.write_bytes(b"not-a-Blender-carrier")
        carrier_sha = sha256_file(fixture.carrier_path)
        fixture.request["carrier"].update(binding(fixture.carrier_path, fixture.root))
        fixture.carrier_authority_record["carrier_sha256"] = carrier_sha
        fixture.request["carrier"]["source_hash_before"] = carrier_sha
        fixture.request["carrier"]["source_hash_after"] = carrier_sha
        with self.assertRaisesRegex(AvatarAnatomyPackageError, "Blender file header"):
            evaluate_avatar_anatomy_package_preflight(fixture.root, fixture.request)

        fixture = self.make_fixture()
        fixture.request["carrier"]["object_ids"] = ["invented_body", "invented_eyes"]
        with self.assertRaisesRegex(AvatarAnatomyPackageError, "object_ids differ"):
            evaluate_avatar_anatomy_package_preflight(fixture.root, fixture.request)

        fixture = self.make_fixture()
        fixture.request["carrier"]["armature_id"] = "invented_armature"
        with self.assertRaisesRegex(AvatarAnatomyPackageError, "armature_id differs"):
            evaluate_avatar_anatomy_package_preflight(fixture.root, fixture.request)

        fixture = self.make_fixture()
        fixture.request["carrier"]["rest_pose_matrix"][3] = 9.0e8
        with self.assertRaisesRegex(AvatarAnatomyPackageError, "rest_pose_matrix differs"):
            evaluate_avatar_anatomy_package_preflight(fixture.root, fixture.request)

        fixture = self.make_fixture()
        fixture.request["truth"]["runtime_activation_authorized"] = True
        with self.assertRaisesRegex(AvatarAnatomyPackageError, "truth fields"):
            evaluate_avatar_anatomy_package_preflight(fixture.root, fixture.request)

        fixture = self.make_fixture()
        fixture.request["separation"]["carrier_mutation_authorized"] = True
        with self.assertRaisesRegex(AvatarAnatomyPackageError, "separation fields"):
            evaluate_avatar_anatomy_package_preflight(fixture.root, fixture.request)

    def test_checked_in_zstd_makehuman_carrier_is_exact_bound_and_read_only(self) -> None:
        request_path = PROJECT_ROOT / (
            "Avatar/avatar_builder/anatomy_packages/"
            "kira_internal_pelvis_source_preflight_v1_20260820/PREFLIGHT_REQUEST.json"
        )
        carrier_path = PROJECT_ROOT / (
            "Avatar/avatar_builder/workspaces/inactive_adult_female_foundations/"
            "generic_makehuman_adult_female_foundation_inactive_v1_20260801/"
            "generic_makehuman_adult_female_foundation_inactive_v1_20260801.blend"
        )
        request = json.loads(request_path.read_text(encoding="utf-8"))
        before = (anatomy_package._file_size(carrier_path), sha256_file(carrier_path))

        report = evaluate_avatar_anatomy_package_preflight(PROJECT_ROOT, request)

        after = (anatomy_package._file_size(carrier_path), sha256_file(carrier_path))
        self.assertEqual(before, (789620, "3911419c44681d25f33892122e61206f1f4651bb78b3e403e377d1ed099cde2f"))
        self.assertEqual(after, before)
        self.assertEqual(report["status"], PREFLIGHT_BLOCKED_MISSING_STRUCTURES)
        self.assertEqual(report["carrier"]["sha256"], before[1])
        self.assertTrue(report["read_only_evidence"]["artifacts_unchanged"])
        self.assertFalse(report["blender_invoked"])

    def test_arbitrary_and_malformed_zstd_carriers_fail_closed(self) -> None:
        from compression import zstd

        fixture = self.make_fixture()
        decompressed = b"BLENDER-v1-unregistered-compressed-fixture\x00"
        compressed = zstd.compress(decompressed)
        fixture.carrier_path.write_bytes(compressed)
        carrier_sha = sha256_file(fixture.carrier_path)
        fixture.request["carrier"].update(binding(fixture.carrier_path, fixture.root))
        fixture.request["carrier"]["source_hash_before"] = carrier_sha
        fixture.request["carrier"]["source_hash_after"] = carrier_sha
        fixture.carrier_authority_record["carrier_sha256"] = carrier_sha
        with self.assertRaisesRegex(AvatarAnatomyPackageError, "not authority-bound"):
            evaluate_avatar_anatomy_package_preflight(fixture.root, fixture.request)

        fixture = self.make_fixture()
        malformed = zstd.compress(decompressed) + b"trailing-not-a-zstd-frame"
        fixture.carrier_path.write_bytes(malformed)
        carrier_sha = sha256_file(fixture.carrier_path)
        fixture.request["carrier"].update(binding(fixture.carrier_path, fixture.root))
        fixture.request["carrier"]["source_hash_before"] = carrier_sha
        fixture.request["carrier"]["source_hash_after"] = carrier_sha
        fixture.carrier_authority_record.update(
            {
                "carrier_sha256": carrier_sha,
                "carrier_bytes": len(malformed),
                "storage_format": "zstd_multiframe_blender",
                "decompressed_bytes": len(decompressed),
                "decompressed_sha256": hashlib.sha256(decompressed).hexdigest(),
            }
        )
        with self.assertRaisesRegex(AvatarAnatomyPackageError, "container is invalid"):
            evaluate_avatar_anatomy_package_preflight(fixture.root, fixture.request)

    def test_carrier_before_after_and_acceptance_artifacts_are_exact_bound(self) -> None:
        fixture = self.make_fixture()
        fixture.request["carrier"]["source_hash_after"] = "0" * 64
        with self.assertRaisesRegex(AvatarAnatomyPackageError, "before/after"):
            evaluate_avatar_anatomy_package_preflight(fixture.root, fixture.request)

        fixture = self.make_fixture()
        fixture.owner["carrier_sha256"] = "0" * 64
        fixture.rewrite_owner()
        report = evaluate_avatar_anatomy_package_preflight(fixture.root, fixture.request)
        self.assertEqual(report["status"], PREFLIGHT_BLOCKED_CARRIER_UNACCEPTED)

    def test_separation_function_runtime_and_public_claims_block_authoring(self) -> None:
        fixture = self.make_fixture()
        fixture.request["separation"]["contains_hair"] = True
        fixture.request["separation"]["contains_clothing"] = True
        fixture.request["separation"]["carrier_write_operations"] = ["vertices"]
        fixture.request["truth"]["function_implemented"] = True
        fixture.request["truth"]["runtime_activation_allowed"] = True
        fixture.request["truth"]["public_export_allowed"] = True
        report = evaluate_avatar_anatomy_package_preflight(fixture.root, fixture.request)
        self.assertEqual(report["status"], PREFLIGHT_BLOCKED_MISSING_STRUCTURES)
        for blocker in (
            "separation_invariant_failed:contains_hair",
            "separation_invariant_failed:contains_clothing",
            "separation_invariant_failed:carrier_write_operations",
            "truth_invariant_failed:function_implemented",
            "truth_invariant_failed:runtime_activation_allowed",
            "truth_invariant_failed:public_export_allowed",
        ):
            self.assertIn(blocker, report["blockers"])
        self.assertFalse(report["authoring_authority"]["private_inactive_authoring_allowed"])

        fixture = self.make_fixture()
        for key in (
            "separate_artifact",
            "default_hidden",
            "module_local_armature_or_deformer",
        ):
            fixture.request["separation"][key] = 1
        for key in ("contains_hair", "contains_clothing"):
            fixture.request["separation"][key] = 0
        report = evaluate_avatar_anatomy_package_preflight(fixture.root, fixture.request)
        self.assertEqual(report["status"], PREFLIGHT_BLOCKED_MISSING_STRUCTURES)
        for key in (
            "separate_artifact",
            "default_hidden",
            "module_local_armature_or_deformer",
            "contains_hair",
            "contains_clothing",
        ):
            self.assertIn(f"separation_invariant_failed:{key}", report["blockers"])

    def test_contract_inventory_routes_and_anchor_mappings_are_enforced(self) -> None:
        fixture = self.make_fixture()
        fixture.request["components"][0]["system"] = "reproductive"
        with self.assertRaisesRegex(AvatarAnatomyPackageError, "component system mismatch"):
            evaluate_avatar_anatomy_package_preflight(fixture.root, fixture.request)

        fixture = self.make_fixture()
        fixture.request["routes"][0]["external_endpoint_anchor_id"] = "anal_opening"
        report = evaluate_avatar_anatomy_package_preflight(fixture.root, fixture.request)
        self.assertIn("route_endpoint_mismatch:urinary", report["blockers"])
        self.assertIn("shared_external_endpoint:anal_opening", report["blockers"])

        fixture = self.make_fixture()
        fixture.request["routes"][0]["ordered_anatomy_ids"] = [
            "vaginal_canal",
            "female_urethra_shell",
        ]
        fixture.request["routes"][2]["ordered_anatomy_ids"] = [
            "vaginal_canal",
            "anal_canal",
        ]
        report = evaluate_avatar_anatomy_package_preflight(fixture.root, fixture.request)
        self.assertEqual(report["status"], PREFLIGHT_BLOCKED_MISSING_STRUCTURES)
        self.assertIn("route_system_mismatch:urinary:vaginal_canal", report["blockers"])
        self.assertIn("route_system_mismatch:bowel:vaginal_canal", report["blockers"])
        self.assertTrue(
            any(
                blocker.startswith("shared_route_node:vaginal_canal:")
                for blocker in report["blockers"]
            )
        )

        fixture = self.make_fixture(complete=False)
        fixture.request["anchors"].append(
            {
                "anchor_id": "female_external_urethral_opening",
                "source_file": "VH_F_Pelvis.glb",
                "source_node": "VH_F_sacrum",
                "source_bound": True,
                "authored": False,
                "transform": fixture.request["normalization"]["per_source_transform"][
                    "VH_F_Pelvis.glb"
                ],
            }
        )
        with self.assertRaisesRegex(AvatarAnatomyPackageError, "no exact mesh-bound"):
            evaluate_avatar_anatomy_package_preflight(fixture.root, fixture.request)

        fixture = self.make_fixture()
        fixture.request["anchors"][0]["transform"] = IDENTITY_MATRIX
        with self.assertRaisesRegex(AvatarAnatomyPackageError, "exact source normalization"):
            evaluate_avatar_anatomy_package_preflight(fixture.root, fixture.request)

    def test_unsafe_project_relative_and_symlink_paths_are_rejected(self) -> None:
        fixture = self.make_fixture()
        fixture.request["contract"]["path"] = "../pelvic_contract.json"
        with self.assertRaisesRegex(AvatarAnatomyPackageError, "safe project-relative path"):
            evaluate_avatar_anatomy_package_preflight(fixture.root, fixture.request)

        fixture = self.make_fixture()
        link = fixture.root / "Contracts/linked_contract.json"
        try:
            os.symlink(fixture.contract_path, link)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlink creation unavailable: {exc}")
        fixture.request["contract"]["path"] = "Contracts/linked_contract.json"
        with self.assertRaisesRegex(AvatarAnatomyPackageError, "symlink or reparse point"):
            evaluate_avatar_anatomy_package_preflight(fixture.root, fixture.request)

    def test_reparse_inspection_error_fails_closed(self) -> None:
        fixture = self.make_fixture()
        with mock.patch.object(
            anatomy_package.os,
            "lstat",
            side_effect=OSError("inspection denied"),
        ):
            with self.assertRaisesRegex(
                AvatarAnatomyPackageError,
                "cannot inspect path for symlink or reparse point",
            ):
                evaluate_avatar_anatomy_package_preflight(fixture.root, fixture.request)

    def test_multiply_linked_bound_artifact_is_rejected(self) -> None:
        fixture = self.make_fixture()
        hardlink = fixture.root / "Contracts/hardlinked_contract.json"
        try:
            os.link(fixture.contract_path, hardlink)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"hardlink creation unavailable: {exc}")
        fixture.request["contract"]["path"] = "Contracts/hardlinked_contract.json"
        with self.assertRaisesRegex(AvatarAnatomyPackageError, "multiply-linked"):
            evaluate_avatar_anatomy_package_preflight(fixture.root, fixture.request)

    @unittest.skipUnless(os.name == "nt", "Windows extended-length path regression")
    def test_windows_extended_length_carrier_path_is_supported_read_only(self) -> None:
        fixture = self.make_fixture()
        long_relative = Path("Carrier")
        for index in range(4):
            long_relative /= f"qualified_foundation_segment_{index}_" + "x" * 45
        long_relative /= "generic_makehuman_adult_female_foundation_inactive.blend"
        long_normal = fixture.root / long_relative
        long_extended = "\\\\?\\" + str(long_normal)
        os.makedirs(os.path.dirname(long_extended), exist_ok=True)
        carrier_payload = b"BLENDER-v1-long-qualified-inactive-fixture\x00"
        with open(long_extended, "wb") as stream:
            stream.write(carrier_payload)
        long_carrier_root = "\\\\?\\" + str(fixture.root / "Carrier" / long_relative.parts[1])

        def remove_long_test_tree() -> None:
            if os.path.exists(long_carrier_root):
                import shutil

                shutil.rmtree(long_carrier_root)

        self.addCleanup(remove_long_test_tree)
        self.assertGreater(len(str(long_normal)), 260)
        carrier_sha = sha256_file(long_normal)
        fixture.request["carrier"].update(
            {
                "path": long_relative.as_posix(),
                "bytes": len(carrier_payload),
                "sha256": carrier_sha,
                "source_hash_before": carrier_sha,
                "source_hash_after": carrier_sha,
            }
        )
        fixture.carrier_authority_record["carrier_sha256"] = carrier_sha
        fixture.qualification["source_artifact"] = {
            "path": long_relative.as_posix(),
            "sha256": carrier_sha,
        }
        fixture.rewrite_qualification()
        fixture.owner["carrier_sha256"] = carrier_sha
        fixture.rewrite_owner()

        report = evaluate_avatar_anatomy_package_preflight(fixture.root, fixture.request)
        self.assertEqual(report["status"], READY_FOR_PRIVATE_INACTIVE_AUTHORING)
        self.assertEqual(report["carrier"]["path"], long_relative.as_posix())
        self.assertTrue(report["read_only_evidence"]["artifacts_unchanged"])

    def test_cli_is_cwd_independent_read_only_and_uses_bounded_exit_codes(self) -> None:
        fixture = self.make_fixture()
        request_path = fixture.root / "request.json"
        write_json(request_path, fixture.request)
        before = {
            path.relative_to(fixture.root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in fixture.root.rglob("*")
            if path.is_file()
        }
        completed = subprocess.run(
            [
                sys.executable,
                "-B",
                str(CLI),
                "--project-root",
                str(fixture.root),
                "--request",
                "request.json",
                "--compact",
            ],
            cwd=fixture.root.parent,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONWARNINGS": "error"},
        )
        after = {
            path.relative_to(fixture.root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in fixture.root.rglob("*")
            if path.is_file()
        }
        self.assertEqual(completed.returncode, 6)
        self.assertEqual(completed.stdout, "")
        self.assertEqual(json.loads(completed.stderr)["status"], "INVALID_PREFLIGHT_REQUEST")
        self.assertEqual(before, after)

        from tools import evaluate_avatar_anatomy_package_preflight as cli

        stdout = io.StringIO()
        with mock.patch.object(sys, "stdout", stdout):
            exit_code = cli.main(
                [
                    "--project-root",
                    str(fixture.root),
                    "--request",
                    "request.json",
                    "--compact",
                ]
            )
        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(stdout.getvalue())["status"], READY_FOR_PRIVATE_INACTIVE_AUTHORING)


if __name__ == "__main__":
    unittest.main()
