from __future__ import annotations

from contextlib import redirect_stdout
import http.client
import io
import json
from pathlib import Path
import struct
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from Core import avatar_multiview_owner_review as owner_review
from Core.avatar_body_topology import inspect_glb_topology
from Core.avatar_multiview_authoring import sha256_file
from Core.avatar_multiview_owner_review import (
    AvatarOwnerReviewError,
    CANONICAL_GWEN_CANDIDATE_ID,
    SUPERSEDED_GWEN_CANDIDATE_ID,
    build_owner_review_report,
    load_owner_review_session,
    resolve_exact_source_image,
    save_base_owner_review,
    save_scale_owner_review,
    save_source_owner_review,
)
from tools import avatar_multiview_owner_review_server as review_server


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def write_png_header(
    path: Path, width: int = 640, height: int = 480, *, tag: bytes
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + struct.pack(">I", 13)
        + b"IHDR"
        + struct.pack(">II", width, height)
        + b"\x08\x02\x00\x00\x00"
        + tag
    )


def glb_bytes(document: dict) -> bytes:
    payload = json.dumps(document, separators=(",", ":")).encode("utf-8")
    payload += b" " * ((-len(payload)) % 4)
    total = 12 + 8 + len(payload)
    return struct.pack("<4sII", b"glTF", 2, total) + struct.pack(
        "<II", len(payload), 0x4E4F534A
    ) + payload


def complete_rig_document() -> dict:
    joint_names = [
        "Pelvis",
        "Spine",
        "Neck",
        "Head",
        "LeftUpperArm",
        "LeftForeArm",
        "LeftHand",
        "RightUpperArm",
        "RightForeArm",
        "RightHand",
        "LeftUpLeg",
        "LeftLeg",
        "LeftFoot",
        "RightUpLeg",
        "RightLeg",
        "RightFoot",
        "LeftThumb1",
        "RightThumb1",
    ]
    nodes = [{"name": name} for name in joint_names]
    nodes.append({"name": "PRIVATE_FIXTURE_MESH", "mesh": 0, "skin": 0})
    return {
        "asset": {"version": "2.0"},
        "accessors": [
            {"count": 300, "type": "VEC3", "componentType": 5126},
            {"count": 300, "type": "VEC4", "componentType": 5123},
            {"count": 300, "type": "VEC4", "componentType": 5126},
            {"count": 900, "type": "SCALAR", "componentType": 5123},
        ],
        "meshes": [
            {
                "primitives": [
                    {
                        "attributes": {
                            "POSITION": 0,
                            "JOINTS_0": 1,
                            "WEIGHTS_0": 2,
                        },
                        "indices": 3,
                    }
                ]
            }
        ],
        "nodes": nodes,
        "skins": [{"joints": list(range(len(joint_names)))}],
    }


class AvatarMultiviewOwnerReviewTests(unittest.TestCase):
    def make_manifest(
        self,
        *,
        candidate_id: str = "owner_review_fixture",
        subject_id: str = "owner_review_subject",
        version_id: str = "owner_review_version_v1",
        topology_lane: str = "confirmed_adult_topology",
        superseded: bool = False,
        canonical_candidate_id: str = "",
    ) -> tuple[tempfile.TemporaryDirectory, Path, Path, Path]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        evidence = root / "Avatar" / "avatar_builder" / "multiview_authoring"
        source_root = evidence / "private_sources" / candidate_id
        source_records = []
        for index in range(1, 4):
            source_path = source_root / f"source_{index:03d}.png"
            write_png_header(
                source_path, tag=f"private-fixture-{index}".encode("ascii")
            )
            source_records.append(
                {
                    "source_id": f"source_{index:03d}",
                    "source_path": source_path.relative_to(root).as_posix(),
                    "sha256": sha256_file(source_path),
                    "dimensions": {"width": 640, "height": 480},
                    "review_status": "pending_explicit_owner_review",
                }
            )
        maturity_lane = (
            "adult"
            if topology_lane == "confirmed_adult_topology"
            else "non_adult_doll_safe"
        )
        canonical_id = canonical_candidate_id or candidate_id
        candidate_root = root / "TemporaryAI" / "candidates" / canonical_id
        write_json(
            candidate_root / "temporary_ai_profile.json",
            {
                "candidate_id": canonical_id,
                "display_name": "Owner review fixture",
                "identity_selection": {
                    "version_id": version_id,
                    "maturity_lane": maturity_lane,
                },
            },
        )
        write_json(
            candidate_root / "creation_request.json",
            {"candidate_id": canonical_id},
        )
        write_json(
            root
            / "Avatar/avatar_builder/policies/candidate_identity_variant_registry.json",
            {
                "schema_version": 1,
                "candidates": [
                    {
                        "canonical_candidate_id": canonical_id,
                        "inventory_scope": "current_temporary_ai_profile",
                        "aliases": [candidate_id] if candidate_id != canonical_id else [],
                        "subject_id": subject_id,
                        "identity_class": "fictional_character",
                        "variant_kind": "fixture_locked",
                        "version_policy": {
                            "required": True,
                            "binding": {
                                "source": "temporary_ai_profile",
                                "path": ["identity_selection", "version_id"],
                                "expected": version_id,
                            },
                        },
                        "maturity_policy": {
                            "lane": maturity_lane,
                            "binding": {
                                "source": "temporary_ai_profile",
                                "path": ["identity_selection", "maturity_lane"],
                                "accepted_values": [maturity_lane],
                            },
                        },
                        "adult_variant_policy": {
                            "separate_variant_required": False,
                            "adult_variant_candidate_id": "",
                        },
                        "manual_review_notes": [],
                    }
                ],
            },
        )

        base_path = (
            root
            / "Avatar/avatar_builder/asset_library/base_body_reference/fixture_base.glb"
        )
        base_path.parent.mkdir(parents=True, exist_ok=True)
        base_path.write_bytes(glb_bytes(complete_rig_document()))
        base_sha = sha256_file(base_path)
        base_id = f"fixture_{maturity_lane}_base_v1"
        asset_record_id = f"base_body_reference:fixture:{base_sha[:12]}"
        adult_only = topology_lane == "confirmed_adult_topology"
        asset_manifest_path = root / "Avatar/avatar_builder/asset_library/manifest.json"
        write_json(
            asset_manifest_path,
            {
                "schema_version": 1,
                "records": [
                    {
                        "id": asset_record_id,
                        "category": "base_body_reference",
                        "local_file": base_path.relative_to(root).as_posix(),
                        "sha256": base_sha,
                        "adult_only": adult_only,
                        "allowed_for_non_adult": not adult_only,
                        "usage_policy": (
                            "adult fixture only"
                            if adult_only
                            else "doll-safe non-adult fixture only"
                        ),
                    }
                ],
            },
        )
        topology_report = inspect_glb_topology(base_path, artifact_id=base_id)
        metric_names = (
            "mesh_count",
            "primitive_count",
            "referenced_position_vertex_count",
            "indexed_or_sequential_triangle_count",
            "skin_count",
            "unique_joint_count",
            "maximum_joints_in_one_skin",
            "weighted_primitive_count",
            "weighted_skinned_primitive_count",
            "unweighted_skinned_primitive_count",
            "invalid_joint_reference_count",
            "invalid_accessor_reference_count",
            "invalid_attribute_layout_count",
            "triangle_element_remainder_count",
        )
        metrics = topology_report["topology_metrics"]
        write_json(
            evidence / "base_catalog/authority.json",
            {
                "schema_version": 1,
                "artifact_type": "avatar_multiview_base_authority_catalog",
                "catalog_status": "active_structural_and_maturity_audit",
                "asset_library_manifest": {
                    "path": "Avatar/avatar_builder/asset_library/manifest.json",
                    "sha256": sha256_file(asset_manifest_path),
                },
                "entries": [
                    {
                        "base_id": base_id,
                        "path": base_path.relative_to(root).as_posix(),
                        "sha256": base_sha,
                        "topology_lane": topology_lane,
                        "allowed_use": "cage_fit_source_new_surface_required",
                        "copy_as_candidate_body_allowed": False,
                        "asset_library_record_id": asset_record_id,
                        "maturity_authority": {
                            "adult_only": adult_only,
                            "allowed_for_non_adult": not adult_only,
                        },
                        "structural_audit": {
                            "method": "non_rendering_glb_structure_v1",
                            "minimum_gate": "weighted_skinned_cage_v1",
                            "valid_glb": True,
                            "metrics": {name: metrics[name] for name in metric_names},
                        },
                        "stable_working_rig_proven": False,
                        "anatomical_completeness_proven": False,
                    }
                ],
            },
        )
        manifest = {
            "schema_version": 1,
            "manifest_type": "avatar_multiview_likeness_evidence",
            "candidate_id": candidate_id,
            "subject_id": subject_id,
            "selected_version_id": version_id,
            "topology_lane": topology_lane,
            "visibility": "owner_only_private_build_evidence",
            "output_rule": "private_review_only_not_runtime",
            "runtime_activation_requested": False,
            "public_export_allowed": False,
            "source_images": source_records,
            "scale_review": {"status": "pending"},
            "base_body": {"status": "pending"},
            "reference_models": [],
        }
        if superseded:
            manifest["authoring_status"] = "superseded_audit_only"
            manifest["queue_eligible"] = False
        manifest_path = evidence / "manifests" / "private" / "fixture.json"
        write_json(manifest_path, manifest)
        return temporary, root, manifest_path, base_path

    @staticmethod
    def source_payload(session: dict, source_id: str = "source_001") -> dict:
        source = next(
            item for item in session["source_images"] if item["source_id"] == source_id
        )
        return {
            "source_id": source_id,
            "confirm_candidate_id": session["candidate_id"],
            "confirm_subject_id": session["subject_id"],
            "confirm_selected_version_id": session["selected_version_id"],
            "confirm_source_sha256": source["sha256"],
            "same_subject_confirmed": True,
            "selected_version_confirmed": True,
            "view_label": "head_front",
            "crop_pixels": {"x": 10, "y": 20, "width": 600, "height": 440},
            "confirm_crop": True,
            "calibration": {
                "camera_model": "perspective",
                "coordinate_frame_id": "owner_frame_001",
            },
            "confirm_calibration": True,
            "landmarks": [
                {
                    "name": "face_outline_left",
                    "region": "face_outline",
                    "x": 100.5,
                    "y": 120.5,
                    "reviewed": True,
                }
            ],
            "confirm_landmarks": True,
            "approve_source_review": True,
            "review_notes": "Owner checked exact enrolled image.",
        }

    @staticmethod
    def base_payload(session: dict) -> dict:
        catalog = session["base_authority_catalog"]
        option = catalog["options"][0]
        return {
            "confirm_candidate_id": session["candidate_id"],
            "confirm_subject_id": session["subject_id"],
            "confirm_selected_version_id": session["selected_version_id"],
            "confirm_topology_lane": session["topology_lane"],
            "confirm_identity_version_and_topology_lane": True,
            "base_authority_id": option["base_id"],
            "confirm_base_authority_catalog_sha256": catalog["catalog_sha256"],
            "confirm_base_sha256": option["sha256"],
            "confirm_exact_base_file": True,
            "rig_compatible_cage_source_confirmed": True,
            "new_candidate_surface_required": True,
            "confirm_surface_copy_forbidden": True,
            "copy_as_candidate_body_allowed": False,
            "approve_base_review": True,
        }

    def test_session_is_path_free_and_preserves_locked_route(self) -> None:
        temporary, root, manifest_path, _ = self.make_manifest()
        self.addCleanup(temporary.cleanup)

        session = load_owner_review_session(
            root, manifest_path, reviewer_id="robert_owner"
        )

        encoded = json.dumps(session)
        self.assertEqual("confirmed_adult_topology", session["topology_lane"])
        self.assertEqual(3, len(session["source_images"]))
        self.assertNotIn("source_path", encoded)
        self.assertNotIn(str(root), encoded)
        self.assertFalse(session["queue_operation_available"])
        self.assertFalse(session["mesh_operation_available"])
        self.assertFalse(session["runtime_activation_allowed"])
        self.assertEqual(
            session["candidate_id"],
            session["canonical_route"]["canonical_candidate_id"],
        )
        self.assertEqual(
            session["topology_lane"],
            session["canonical_route"]["canonical_topology_lane"],
        )
        self.assertEqual("ready", session["base_authority_catalog"]["status"])

    def test_registered_candidate_alias_resolves_to_one_canonical_profile(self) -> None:
        temporary, root, manifest_path, _ = self.make_manifest(
            candidate_id="owner_review_body_alias",
            canonical_candidate_id="owner_review_canonical_profile",
        )
        self.addCleanup(temporary.cleanup)
        session = load_owner_review_session(
            root, manifest_path, reviewer_id="robert_owner"
        )

        self.assertEqual("owner_review_body_alias", session["candidate_id"])
        self.assertEqual(
            "owner_review_canonical_profile",
            session["canonical_route"]["canonical_candidate_id"],
        )
        self.assertTrue(session["canonical_route"]["candidate_alias_used"])

    def test_superseded_gwen_is_blocked_and_canonical_gwen_is_reviewable(self) -> None:
        old_temp, old_root, old_manifest, _ = self.make_manifest(
            candidate_id=SUPERSEDED_GWEN_CANDIDATE_ID,
            subject_id="gwen_stacy_adult_project_variant",
            superseded=True,
        )
        self.addCleanup(old_temp.cleanup)
        with self.assertRaisesRegex(AvatarOwnerReviewError, "canonical Gwen"):
            load_owner_review_session(
                old_root, old_manifest, reviewer_id="robert_owner"
            )

        new_temp, new_root, new_manifest, _ = self.make_manifest(
            candidate_id=CANONICAL_GWEN_CANDIDATE_ID,
            subject_id="gwen_stacy_earth_65",
            version_id="earth_65_main_ghost_spider_young_adult_18_20_current_build_v1",
        )
        self.addCleanup(new_temp.cleanup)
        session = load_owner_review_session(
            new_root, new_manifest, reviewer_id="robert_owner"
        )
        self.assertEqual(CANONICAL_GWEN_CANDIDATE_ID, session["candidate_id"])
        self.assertEqual("confirmed_adult_topology", session["topology_lane"])

    def test_canonical_version_and_maturity_route_mismatches_fail_closed(self) -> None:
        temporary, root, manifest_path, _ = self.make_manifest(
            topology_lane="non_adult_doll_safe_topology"
        )
        self.addCleanup(temporary.cleanup)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["topology_lane"] = "confirmed_adult_topology"
        write_json(manifest_path, manifest)
        with self.assertRaisesRegex(AvatarOwnerReviewError, "canonical.*maturity"):
            load_owner_review_session(
                root, manifest_path, reviewer_id="robert_owner"
            )

        manifest["topology_lane"] = "non_adult_doll_safe_topology"
        manifest["selected_version_id"] = "wrong_canonical_version_v2"
        write_json(manifest_path, manifest)
        with self.assertRaisesRegex(AvatarOwnerReviewError, "canonical selected version"):
            load_owner_review_session(
                root, manifest_path, reviewer_id="robert_owner"
            )

    def test_registry_is_required_and_manifest_must_stay_in_private_root(self) -> None:
        temporary, root, manifest_path, _ = self.make_manifest()
        self.addCleanup(temporary.cleanup)
        outside = root / "owner_review_outside_private_root.json"
        write_json(outside, json.loads(manifest_path.read_text(encoding="utf-8")))
        with self.assertRaisesRegex(AvatarOwnerReviewError, "manifests/private"):
            load_owner_review_session(root, outside, reviewer_id="robert_owner")

        registry = (
            root
            / "Avatar/avatar_builder/policies/candidate_identity_variant_registry.json"
        )
        registry.unlink()
        with self.assertRaisesRegex(AvatarOwnerReviewError, "registry is unavailable"):
            load_owner_review_session(
                root, manifest_path, reviewer_id="robert_owner"
            )

    def test_manifest_symlink_is_rejected_even_inside_private_root(self) -> None:
        temporary, root, manifest_path, _ = self.make_manifest()
        self.addCleanup(temporary.cleanup)
        link = manifest_path.with_name("linked_fixture.json")
        try:
            link.symlink_to(manifest_path)
        except OSError as exc:
            self.skipTest(f"file symlinks are unavailable: {exc}")
        with self.assertRaisesRegex(AvatarOwnerReviewError, "manifests/private"):
            load_owner_review_session(root, link, reviewer_id="robert_owner")

    def test_source_review_never_auto_approves_and_writes_exact_binding(self) -> None:
        temporary, root, manifest_path, _ = self.make_manifest()
        self.addCleanup(temporary.cleanup)
        session = load_owner_review_session(
            root, manifest_path, reviewer_id="robert_owner"
        )
        original_manifest = manifest_path.read_bytes()
        payload = self.source_payload(session)
        payload["approve_source_review"] = False

        with self.assertRaisesRegex(AvatarOwnerReviewError, "explicit confirmation"):
            save_source_owner_review(
                root,
                manifest_path,
                reviewer_id="robert_owner",
                expected_manifest_sha256=session["manifest_sha256"],
                payload=payload,
            )
        self.assertEqual(original_manifest, manifest_path.read_bytes())
        self.assertFalse(
            (root / "Avatar/avatar_builder/multiview_authoring/private_reviews").exists()
        )

        payload["approve_source_review"] = True
        result = save_source_owner_review(
            root,
            manifest_path,
            reviewer_id="robert_owner",
            expected_manifest_sha256=session["manifest_sha256"],
            payload=payload,
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        binding = manifest["source_images"][0]["review_artifact"]
        artifact_path = root / binding["path"]
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        self.assertEqual(binding["sha256"], sha256_file(artifact_path))
        self.assertEqual(result["artifact_sha256"], binding["sha256"])
        self.assertEqual("manual_owner_entry", artifact["landmark_origin"])
        self.assertTrue(artifact["same_subject_confirmed"])
        self.assertTrue(artifact["selected_version_confirmed"])
        self.assertEqual(session["canonical_route"], artifact["canonical_route"])
        self.assertFalse(result["body_queued"])
        self.assertFalse(result["mesh_created"])
        self.assertFalse(result["runtime_activation_allowed"])

    def test_stale_manifest_and_changed_source_fail_closed(self) -> None:
        temporary, root, manifest_path, _ = self.make_manifest()
        self.addCleanup(temporary.cleanup)
        session = load_owner_review_session(
            root, manifest_path, reviewer_id="robert_owner"
        )
        source = session["source_images"][0]
        source_path, _, _ = resolve_exact_source_image(
            root,
            manifest_path,
            source_id=source["source_id"],
            expected_manifest_sha256=session["manifest_sha256"],
            expected_source_sha256=source["sha256"],
        )
        save_scale_owner_review(
            root,
            manifest_path,
            reviewer_id="robert_owner",
            expected_manifest_sha256=session["manifest_sha256"],
            payload={
                "confirm_candidate_id": session["candidate_id"],
                "confirm_subject_id": session["subject_id"],
                "confirm_selected_version_id": session["selected_version_id"],
                "confirm_identity_and_version": True,
                "scale_mode": "scale_unknown_review_only",
                "target_height_m": "",
                "confirm_no_height_inference": True,
                "approve_scale_review": True,
            },
        )
        with self.assertRaisesRegex(AvatarOwnerReviewError, "manifest changed"):
            save_source_owner_review(
                root,
                manifest_path,
                reviewer_id="robert_owner",
                expected_manifest_sha256=session["manifest_sha256"],
                payload=self.source_payload(session),
            )
        refreshed = load_owner_review_session(
            root, manifest_path, reviewer_id="robert_owner"
        )
        source_path.write_bytes(source_path.read_bytes() + b"tamper")
        with self.assertRaisesRegex(AvatarOwnerReviewError, "exact hash changed"):
            resolve_exact_source_image(
                root,
                manifest_path,
                source_id=source["source_id"],
                expected_manifest_sha256=refreshed["manifest_sha256"],
                expected_source_sha256=source["sha256"],
            )

    def test_scale_and_nonadult_base_reviews_preserve_topology_lane(self) -> None:
        temporary, root, manifest_path, _ = self.make_manifest(
            topology_lane="non_adult_doll_safe_topology"
        )
        self.addCleanup(temporary.cleanup)
        session = load_owner_review_session(
            root, manifest_path, reviewer_id="robert_owner"
        )
        scale_result = save_scale_owner_review(
            root,
            manifest_path,
            reviewer_id="robert_owner",
            expected_manifest_sha256=session["manifest_sha256"],
            payload={
                "confirm_candidate_id": session["candidate_id"],
                "confirm_subject_id": session["subject_id"],
                "confirm_selected_version_id": session["selected_version_id"],
                "confirm_identity_and_version": True,
                "scale_mode": "reviewed_metric",
                "target_height_m": 1.55,
                "confirm_metric_height": True,
                "approve_scale_review": True,
            },
        )
        refreshed = load_owner_review_session(
            root, manifest_path, reviewer_id="robert_owner"
        )
        base_payload = self.base_payload(refreshed)
        base_payload["confirm_topology_lane"] = "confirmed_adult_topology"
        with self.assertRaisesRegex(AvatarOwnerReviewError, "topology_lane"):
            save_base_owner_review(
                root,
                manifest_path,
                reviewer_id="robert_owner",
                expected_manifest_sha256=refreshed["manifest_sha256"],
                payload=base_payload,
            )
        base_payload["confirm_topology_lane"] = "non_adult_doll_safe_topology"
        base_result = save_base_owner_review(
            root,
            manifest_path,
            reviewer_id="robert_owner",
            expected_manifest_sha256=refreshed["manifest_sha256"],
            payload=base_payload,
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(
            "non_adult_doll_safe_topology", manifest["topology_lane"]
        )
        self.assertEqual(
            "non_adult_doll_safe_topology",
            manifest["base_body"]["topology_lane"],
        )
        review_path = root / manifest["base_body"]["review_artifact"]["path"]
        base_artifact = json.loads(review_path.read_text(encoding="utf-8"))
        self.assertTrue(
            base_artifact["base_authority"]["structural_proof"]["gate_passed"]
        )
        self.assertTrue(
            base_artifact["base_authority"]["maturity_authority"]["lane_match"]
        )
        self.assertFalse(
            base_artifact["base_authority"]["stable_working_rig_proven"]
        )
        self.assertFalse(scale_result["body_queued"])
        self.assertFalse(base_result["body_queued"])
        self.assertFalse((root / "Avatar/avatar_builder/multiview_authoring/queued").exists())

    def test_base_review_rejects_free_paths_and_changed_audited_bytes(self) -> None:
        temporary, root, manifest_path, base_path = self.make_manifest()
        self.addCleanup(temporary.cleanup)
        session = load_owner_review_session(
            root, manifest_path, reviewer_id="robert_owner"
        )
        payload = self.base_payload(session)
        payload["base_body_path"] = base_path.relative_to(root).as_posix()
        with self.assertRaisesRegex(AvatarOwnerReviewError, "free-form base paths"):
            save_base_owner_review(
                root,
                manifest_path,
                reviewer_id="robert_owner",
                expected_manifest_sha256=session["manifest_sha256"],
                payload=payload,
            )
        payload.pop("base_body_path")
        base_path.write_bytes(base_path.read_bytes() + b"tamper")
        with self.assertRaisesRegex(AvatarOwnerReviewError, "exact hash changed"):
            save_base_owner_review(
                root,
                manifest_path,
                reviewer_id="robert_owner",
                expected_manifest_sha256=session["manifest_sha256"],
                payload=payload,
            )

    def test_exactly_cataloged_malformed_glb_still_cannot_be_approved(self) -> None:
        temporary, root, manifest_path, base_path = self.make_manifest()
        self.addCleanup(temporary.cleanup)
        base_path.write_bytes(b"glTF-owner-review-base")
        malformed_sha = sha256_file(base_path)
        asset_manifest_path = root / "Avatar/avatar_builder/asset_library/manifest.json"
        asset_manifest = json.loads(
            asset_manifest_path.read_text(encoding="utf-8")
        )
        asset_manifest["records"][0]["sha256"] = malformed_sha
        write_json(asset_manifest_path, asset_manifest)
        catalog_path = (
            root
            / "Avatar/avatar_builder/multiview_authoring/base_catalog/authority.json"
        )
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        catalog["asset_library_manifest"]["sha256"] = sha256_file(
            asset_manifest_path
        )
        catalog["entries"][0]["sha256"] = malformed_sha
        write_json(catalog_path, catalog)

        session = load_owner_review_session(
            root, manifest_path, reviewer_id="robert_owner"
        )
        self.assertEqual("not_ready", session["base_authority_catalog"]["status"])
        self.assertIn(
            "not a valid audited GLB",
            session["base_authority_catalog"]["reason"],
        )
        self.assertEqual([], session["base_authority_catalog"]["options"])

    def test_catalog_maturity_lane_is_machine_enforced(self) -> None:
        temporary, root, manifest_path, _ = self.make_manifest(
            topology_lane="non_adult_doll_safe_topology"
        )
        self.addCleanup(temporary.cleanup)
        catalog_path = (
            root
            / "Avatar/avatar_builder/multiview_authoring/base_catalog/authority.json"
        )
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        catalog["entries"][0]["topology_lane"] = "confirmed_adult_topology"
        write_json(catalog_path, catalog)

        session = load_owner_review_session(
            root, manifest_path, reviewer_id="robert_owner"
        )
        self.assertEqual("not_ready", session["base_authority_catalog"]["status"])
        self.assertEqual([], session["base_authority_catalog"]["options"])
        self.assertIn("maturity", session["base_authority_catalog"]["reason"])

    def test_manifest_commit_lock_serializes_independent_writers(self) -> None:
        temporary, root, manifest_path, _ = self.make_manifest()
        self.addCleanup(temporary.cleanup)
        session = load_owner_review_session(
            root, manifest_path, reviewer_id="robert_owner"
        )
        scale_payload = {
            "confirm_candidate_id": session["candidate_id"],
            "confirm_subject_id": session["subject_id"],
            "confirm_selected_version_id": session["selected_version_id"],
            "confirm_identity_and_version": True,
            "scale_mode": "scale_unknown_review_only",
            "target_height_m": "",
            "confirm_no_height_inference": True,
            "approve_scale_review": True,
        }
        entered_replace = threading.Event()
        release_replace = threading.Event()
        second_done = threading.Event()
        results: list[object] = []
        calls = 0
        calls_lock = threading.Lock()
        real_replace = owner_review.os.replace

        def delayed_replace(source: Path, destination: Path) -> None:
            nonlocal calls
            with calls_lock:
                calls += 1
                current_call = calls
            if current_call == 1:
                entered_replace.set()
                if not release_replace.wait(3):
                    raise RuntimeError("test did not release first manifest replace")
            real_replace(source, destination)

        def first_writer() -> None:
            try:
                results.append(
                    save_scale_owner_review(
                        root,
                        manifest_path,
                        reviewer_id="robert_owner",
                        expected_manifest_sha256=session["manifest_sha256"],
                        payload=scale_payload,
                    )
                )
            except Exception as exc:  # captured for deterministic assertions
                results.append(exc)

        def second_writer() -> None:
            try:
                results.append(
                    save_source_owner_review(
                        root,
                        manifest_path,
                        reviewer_id="robert_owner",
                        expected_manifest_sha256=session["manifest_sha256"],
                        payload=self.source_payload(session),
                    )
                )
            except Exception as exc:  # captured for deterministic assertions
                results.append(exc)
            finally:
                second_done.set()

        with patch.object(owner_review.os, "replace", delayed_replace):
            first = threading.Thread(target=first_writer)
            first.start()
            self.assertTrue(entered_replace.wait(3))
            second = threading.Thread(target=second_writer)
            second.start()
            time.sleep(0.1)
            self.assertFalse(second_done.is_set())
            with calls_lock:
                self.assertEqual(1, calls)
            release_replace.set()
            first.join(3)
            second.join(3)
        self.assertFalse(first.is_alive())
        self.assertFalse(second.is_alive())
        self.assertEqual(2, len(results))
        self.assertEqual(1, sum(isinstance(item, dict) for item in results))
        errors = [item for item in results if isinstance(item, Exception)]
        self.assertEqual(1, len(errors))
        self.assertIn("manifest changed before commit", str(errors[0]))

    def test_report_is_owner_reviewable_and_contains_no_source_paths(self) -> None:
        temporary, root, manifest_path, _ = self.make_manifest()
        self.addCleanup(temporary.cleanup)
        report = build_owner_review_report(
            root, manifest_path, reviewer_id="robert_owner"
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertIn("Exact enrolled sources", report)
        self.assertIn("Queue/build/render/export/activation operations: unavailable", report)
        self.assertNotIn(str(root), report)
        for source in manifest["source_images"]:
            self.assertNotIn(source["source_path"], report)

    def test_application_uses_opaque_source_tokens_and_no_queue_api(self) -> None:
        temporary, root, manifest_path, _ = self.make_manifest()
        self.addCleanup(temporary.cleanup)
        app = review_server.OwnerReviewApplication(
            root,
            manifest_path,
            reviewer_id="robert_owner",
            csrf_token="fixture-csrf",
            source_token_key=b"fixture-key" * 4,
        )
        payload = app.session_payload()
        source = payload["source_images"][0]
        self.assertIn("/private/source/", source["image_url"])
        self.assertNotIn("source_path", json.dumps(payload))
        self.assertNotIn("queue", source["image_url"])
        ui = app.render_ui().decode("utf-8")
        self.assertIn("fixture-csrf", ui)
        self.assertNotIn("/api/queue", ui)
        self.assertNotIn("/api/activate", ui)
        self.assertNotIn('id="base-path"', ui)
        self.assertIn('id="base-authority"', ui)

    def test_loopback_http_boundaries_and_private_source_delivery(self) -> None:
        temporary, root, manifest_path, _ = self.make_manifest()
        self.addCleanup(temporary.cleanup)
        app = review_server.OwnerReviewApplication(
            root,
            manifest_path,
            reviewer_id="robert_owner",
            csrf_token="fixture-csrf",
            source_token_key=b"fixture-source-token-key-123456",
        )
        server = review_server.OwnerReviewHTTPServer(("127.0.0.1", 0), app)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        port = server.server_port

        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        connection.putrequest("GET", "/api/session", skip_host=True)
        connection.putheader("Host", f"127.0.0.1:{port}")
        connection.putheader("X-Owner-Review-CSRF", "fixture-csrf")
        connection.endheaders()
        response = connection.getresponse()
        session = json.loads(response.read())
        self.assertEqual(200, response.status)
        self.assertNotIn("source_path", json.dumps(session))

        image_url = session["source_images"][0]["image_url"]
        connection.putrequest("GET", image_url, skip_host=True)
        connection.putheader("Host", f"127.0.0.1:{port}")
        connection.putheader("Referer", f"http://127.0.0.1:{port}/")
        connection.endheaders()
        image_response = connection.getresponse()
        image_body = image_response.read()
        self.assertEqual(200, image_response.status)
        self.assertTrue(image_body.startswith(b"\x89PNG"))
        connection.close()

        hostile = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        hostile.putrequest("GET", "/api/session", skip_host=True)
        hostile.putheader("Host", "attacker.example")
        hostile.putheader("X-Owner-Review-CSRF", "fixture-csrf")
        hostile.endheaders()
        hostile_response = hostile.getresponse()
        hostile_response.read()
        self.assertEqual(403, hostile_response.status)
        hostile.close()

        no_origin = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        body = json.dumps(
            {
                "expected_manifest_sha256": session["manifest_sha256"],
                "payload": {},
            }
        )
        no_origin.putrequest("POST", "/api/review/source", skip_host=True)
        no_origin.putheader("Host", f"127.0.0.1:{port}")
        no_origin.putheader("X-Owner-Review-CSRF", "fixture-csrf")
        no_origin.putheader("Content-Type", "application/json")
        no_origin.putheader("Content-Length", str(len(body.encode("utf-8"))))
        no_origin.endheaders(body.encode("utf-8"))
        no_origin_response = no_origin.getresponse()
        no_origin_response.read()
        self.assertEqual(403, no_origin_response.status)
        no_origin.close()
        self.assertEqual(
            session["manifest_sha256"], sha256_file(manifest_path)
        )

        approved_scale = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        approved_body = json.dumps(
            {
                "expected_manifest_sha256": session["manifest_sha256"],
                "payload": {
                    "confirm_candidate_id": session["candidate_id"],
                    "confirm_subject_id": session["subject_id"],
                    "confirm_selected_version_id": session["selected_version_id"],
                    "confirm_identity_and_version": True,
                    "scale_mode": "scale_unknown_review_only",
                    "target_height_m": "",
                    "confirm_no_height_inference": True,
                    "approve_scale_review": True,
                },
            }
        ).encode("utf-8")
        approved_scale.putrequest("POST", "/api/review/scale", skip_host=True)
        approved_scale.putheader("Host", f"127.0.0.1:{port}")
        approved_scale.putheader("Origin", f"http://127.0.0.1:{port}")
        approved_scale.putheader("X-Owner-Review-CSRF", "fixture-csrf")
        approved_scale.putheader("Content-Type", "application/json")
        approved_scale.putheader("Content-Length", str(len(approved_body)))
        approved_scale.endheaders(approved_body)
        approved_response = approved_scale.getresponse()
        approved_result = json.loads(approved_response.read())
        self.assertEqual(200, approved_response.status)
        self.assertFalse(approved_result["body_queued"])
        self.assertFalse(approved_result["runtime_activation_allowed"])
        approved_scale.close()
        self.assertFalse(
            (root / "Avatar/avatar_builder/multiview_authoring/queued").exists()
        )

    def test_report_cli_writes_only_under_codex_reports(self) -> None:
        temporary, root, manifest_path, _ = self.make_manifest()
        self.addCleanup(temporary.cleanup)
        relative_manifest = manifest_path.relative_to(root).as_posix()
        output = "Data/codex_reports/owner_review_fixture.md"
        stdout = io.StringIO()
        with patch.object(review_server, "PROJECT_ROOT", root), redirect_stdout(stdout):
            exit_code = review_server.main(
                [
                    "report",
                    "--manifest",
                    relative_manifest,
                    "--reviewer-id",
                    "robert_owner",
                    "--output",
                    output,
                ]
            )
        self.assertEqual(0, exit_code)
        self.assertTrue((root / output).is_file())
        self.assertFalse((root / "Avatar/avatar_builder/multiview_authoring/queued").exists())


if __name__ == "__main__":
    unittest.main()
