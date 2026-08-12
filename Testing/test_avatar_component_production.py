from __future__ import annotations

import copy
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch


from Core.avatar_component_production import (
    ACTION,
    AvatarProductionError,
    canonical_json_bytes,
    plan_orchestration_request,
    process_job,
    process_queue,
    queue_production_request,
    sha256_file,
    validate_production_request_file,
)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def write_minimal_glb(path: Path, role: str) -> None:
    document = {
        "asset": {"version": "2.0", "generator": "avatar-component-production-test"},
        "scene": 0,
        "scenes": [{"nodes": [1]}],
        "nodes": [
            {"name": f"{role}_root", "translation": [0, 0, 0]},
            {"name": f"{role}_mesh", "mesh": 0, "skin": 0, "children": [0]},
        ],
        "meshes": [{"name": f"{role}_mesh", "primitives": [{"attributes": {}}]}],
        "skins": [{"name": f"{role}_rig", "joints": [0], "skeleton": 0}],
    }
    json_chunk = json.dumps(document, separators=(",", ":")).encode("utf-8")
    json_chunk += b" " * ((4 - len(json_chunk) % 4) % 4)
    total_length = 12 + 8 + len(json_chunk)
    payload = (
        struct.pack("<4sII", b"glTF", 2, total_length)
        + struct.pack("<II", len(json_chunk), 0x4E4F534A)
        + json_chunk
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


class AvatarComponentProductionTests(unittest.TestCase):
    def make_project(self, topology_lane: str) -> tuple[tempfile.TemporaryDirectory, Path, Path]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        candidate_id = "fixture_person_001"
        subject_id = "fixture_subject"
        component_root = root / "Avatar" / "temp_ai" / candidate_id / "generated_body"
        hashes: dict[str, str] = {}
        component_paths: dict[str, Path] = {}
        for role in ("body", "hair", "eyes", "clothes"):
            path = component_root / f"fixture_{role}.glb"
            write_minimal_glb(path, role)
            hashes[role] = sha256_file(path)
            component_paths[role] = path

        non_adult = topology_lane == "non_adult_doll_safe_topology"
        maturity_class = "non_adult_doll_safe" if non_adult else "adult"
        base_treatment = "non_adult_doll_safe" if non_adult else "neutral_adult_anatomy"
        orchestration = {
            "schema_version": 1,
            "candidate_id": candidate_id,
            "subject_id": subject_id,
            "owner_identity": {},
            "request_complete_adult_anatomy": not non_adult,
            "render_requested": False,
            "runtime_activation_requested": False,
            "maturity_policy": {
                "maturity_class": maturity_class,
                "evidence": {
                    "candidate_id": candidate_id,
                    "subject_id": subject_id,
                    "maturity_class": maturity_class,
                    "evidence_sha256": "1" * 64,
                    "exact_evidence_hash_verified": True,
                    "exact_subject_bound": True,
                    "review_status": "passed",
                },
            },
            "source_strategy": {
                "mode": "licensed_shape_preserving_derivative",
                "photo_only": {"selected": False},
                "licensed_derivative": {
                    "selected": True,
                    "candidate_id": candidate_id,
                    "subject_id": subject_id,
                    "source_sha256": "2" * 64,
                    "exact_source_hash_verified": True,
                    "license_evidence_sha256": "3" * 64,
                    "license_evidence_hash_verified": True,
                    "adaptation_allowed": True,
                    "attribution_bound": True,
                    "source_role_map_sha256": "4" * 64,
                    "source_role_map_hash_verified": True,
                    "licensed_source_surface_incorporated": True,
                    "source_surface_shape_preserved": True,
                    "new_body_surface_authored": False,
                    "source_artifact_byte_copied": False,
                    "source_materials_and_textures_exported": False,
                    "candidate_output_allowlist_enforced": True,
                    "candidate_body_sha256": hashes["body"],
                    "adult_only_source": not non_adult,
                },
            },
            "components": {
                role: {
                    "artifact_role": role,
                    "artifact_sha256": hashes[role],
                    "exact_artifact_hash_verified": True,
                    "separate_artifact": True,
                    **(
                        {
                            "contains_hair": False,
                            "contains_eyes": False,
                            "contains_clothes": False,
                        }
                        if role == "body"
                        else {}
                    ),
                }
                for role in hashes
            },
            "rig_binding": {
                "rig_sha256": "5" * 64,
                "exact_rig_hash_verified": True,
            },
            "readiness_evidence": {
                "topology": {
                    "artifact_sha256": hashes["body"],
                    "exact_artifact_hash_verified": True,
                    "review_status": "provisional",
                    "reviewed_by": "fixture",
                    "reviewed_at": "2026-07-16T00:00:00Z",
                    "body_treatment": base_treatment,
                    "adult_anatomy_present": False if non_adult else "unreviewed",
                    "test_results": {},
                }
            },
            "privacy": {
                "normal_review_route": "clothed_only",
                "intimate_render_retained": False,
                "private_source_paths_in_report": False,
                "public_export_allowed": False,
            },
        }
        orchestration_path = (
            root
            / "Avatar"
            / "avatar_builder"
            / "orchestration_requests"
            / f"{candidate_id}.json"
        )
        write_json(orchestration_path, orchestration)
        authority = {
            "schema_version": 1,
            "candidate_id": candidate_id,
            "subject_id": subject_id,
            "artifact_generation_succeeded": True,
            "runtime_activation_allowed": False,
            **{f"{role}_sha256": digest for role, digest in hashes.items()},
        }
        authority_path = root / "Avatar" / "temp_ai" / candidate_id / "status.json"
        write_json(authority_path, authority)
        production = {
            "schema_version": 1,
            "action": ACTION,
            "candidate_id": candidate_id,
            "subject_id": subject_id,
            "topology_lane": topology_lane,
            "source_lane": "licensed_shape_preserving_derivative",
            "adult_anatomy_requested": not non_adult,
            "runtime_activation_requested": False,
            "public_export_requested": False,
            "orchestration_binding": {
                "path": orchestration_path.relative_to(root).as_posix(),
                "sha256": sha256_file(orchestration_path),
            },
            "component_authority": {
                "path": authority_path.relative_to(root).as_posix(),
                "sha256": sha256_file(authority_path),
            },
            "source_components": {
                role: {
                    "artifact_role": role,
                    "path": path.relative_to(root).as_posix(),
                    "sha256": hashes[role],
                }
                for role, path in component_paths.items()
            },
        }
        production_path = (
            root
            / "Avatar"
            / "avatar_builder"
            / "component_production_requests"
            / f"{candidate_id}.json"
        )
        write_json(production_path, production)
        return temporary, root, production_path

    def test_adult_lane_queues_and_builds_real_separate_package(self) -> None:
        temporary, root, request_path = self.make_project("confirmed_adult_topology")
        self.addCleanup(temporary.cleanup)
        queued = queue_production_request(root, request_path)
        results = process_queue(root)
        self.assertEqual("queued", queued["status"])
        self.assertEqual(1, len(results))
        result = results[0]
        manifest_path = root / result["package_manifest"]
        manifest = json.loads(manifest_path.read_text())
        self.assertEqual("confirmed_adult_topology", manifest["topology_lane"])
        self.assertFalse(manifest["runtime_activation_allowed"])
        self.assertEqual(
            {"body", "hair", "eyes", "clothes", "rig"},
            set(manifest["artifacts"]),
        )
        artifact_hashes = set()
        for binding in manifest["artifacts"].values():
            artifact = manifest_path.parent / binding["filename"]
            self.assertTrue(artifact.is_file())
            self.assertEqual(binding["sha256"], sha256_file(artifact))
            artifact_hashes.add(binding["sha256"])
        self.assertEqual(5, len(artifact_hashes))

    def test_non_adult_lane_packages_only_explicit_doll_safe_route(self) -> None:
        temporary, root, request_path = self.make_project("non_adult_doll_safe_topology")
        self.addCleanup(temporary.cleanup)
        validated = validate_production_request_file(root, request_path)
        self.assertEqual("non_adult_doll_safe_topology", validated.topology_lane)
        queued = queue_production_request(root, request_path)
        job = root / queued["job_path"]
        result = process_job(root, job)
        manifest = json.loads((root / result["package_manifest"]).read_text())
        self.assertEqual("non_adult_doll_safe_topology", manifest["topology_lane"])
        self.assertFalse(manifest["runtime_activation_allowed"])

    def test_non_adult_lane_rejects_adult_anatomy_flag(self) -> None:
        temporary, root, request_path = self.make_project("non_adult_doll_safe_topology")
        self.addCleanup(temporary.cleanup)
        request = json.loads(request_path.read_text())
        request["adult_anatomy_requested"] = True
        write_json(request_path, request)
        with self.assertRaisesRegex(AvatarProductionError, "reject adult anatomy"):
            validate_production_request_file(root, request_path)

    def test_queue_is_idempotent_and_immutable(self) -> None:
        temporary, root, request_path = self.make_project("confirmed_adult_topology")
        self.addCleanup(temporary.cleanup)
        first = queue_production_request(root, request_path)
        second = queue_production_request(root, request_path)
        self.assertEqual(first["job_id"], second["job_id"])
        self.assertEqual("already_queued", second["status"])
        job = root / first["job_path"]
        first_result = process_job(root, job)
        second_result = process_job(root, job)
        self.assertEqual("processed_component_set_staged", first_result["status"])
        self.assertEqual("already_processed_verified", second_result["status"])

    def test_completed_job_survives_authoring_request_advancing(self) -> None:
        temporary, root, request_path = self.make_project("confirmed_adult_topology")
        self.addCleanup(temporary.cleanup)
        first = queue_production_request(root, request_path)
        first_result = process_job(root, root / first["job_path"])

        request = json.loads(request_path.read_text())
        request["truth_note"] = "A newer exact-hash authoring revision may follow."
        write_json(request_path, request)
        second = queue_production_request(root, request_path)

        self.assertNotEqual(first["job_id"], second["job_id"])
        self.assertEqual(
            "already_processed_verified",
            process_job(root, root / first["job_path"])["status"],
        )
        results = process_queue(root)
        self.assertEqual(1, len(results))
        self.assertEqual(second["job_id"], results[0]["job_id"])
        self.assertEqual("processed_component_set_staged", results[0]["status"])
        self.assertTrue((root / first_result["package_manifest"]).is_file())

    def test_unprocessed_job_rejects_changed_request(self) -> None:
        temporary, root, request_path = self.make_project("confirmed_adult_topology")
        self.addCleanup(temporary.cleanup)
        queued = queue_production_request(root, request_path)
        request = json.loads(request_path.read_text())
        request["truth_note"] = "Changed after queueing."
        write_json(request_path, request)
        with self.assertRaisesRegex(AvatarProductionError, "request changed"):
            process_job(root, root / queued["job_path"])

    def test_queue_revalidates_completed_package_instead_of_skipping_result_name(self) -> None:
        temporary, root, request_path = self.make_project("confirmed_adult_topology")
        self.addCleanup(temporary.cleanup)
        queued = queue_production_request(root, request_path)
        result = process_job(root, root / queued["job_path"])
        manifest_path = root / result["package_manifest"]
        manifest = json.loads(manifest_path.read_text())
        body_path = manifest_path.parent / manifest["artifacts"]["body"]["filename"]
        body_path.write_bytes(body_path.read_bytes() + b"tamper")

        with self.assertRaisesRegex(AvatarProductionError, "artifact changed"):
            process_queue(root)

    def test_source_change_after_queue_fails_closed(self) -> None:
        temporary, root, request_path = self.make_project("confirmed_adult_topology")
        self.addCleanup(temporary.cleanup)
        queued = queue_production_request(root, request_path)
        request = json.loads(request_path.read_text())
        body_path = root / request["source_components"]["body"]["path"]
        body_path.write_bytes(body_path.read_bytes() + b"changed")
        with self.assertRaisesRegex(AvatarProductionError, "request|hash|GLB"):
            process_job(root, root / queued["job_path"])

    def test_changed_queue_job_fails_content_hash(self) -> None:
        temporary, root, request_path = self.make_project("confirmed_adult_topology")
        self.addCleanup(temporary.cleanup)
        queued = queue_production_request(root, request_path)
        job_path = root / queued["job_path"]
        job = json.loads(job_path.read_text())
        job["candidate_id"] = "different_candidate"
        write_json(job_path, job)
        with self.assertRaisesRegex(AvatarProductionError, "content hash"):
            process_job(root, job_path)

    def test_photo_only_missing_multiview_manifest_stays_authoring_blocked(self) -> None:
        project = Path(__file__).resolve().parents[1]
        request = json.loads(
            (
                project
                / "Avatar"
                / "avatar_builder"
                / "orchestration_requests"
                / "robert_user_avatar_20260716.json"
            ).read_text()
        )
        plan = plan_orchestration_request(request)
        self.assertEqual(
            "blocked_multiview_evidence_manifest_missing", plan["production_state"]
        )
        self.assertEqual(
            "not_prepared", plan["multiview_authoring"]["status"]
        )
        self.assertIn(
            "multiview_evidence_manifest_missing", plan["body_blocking_reasons"]
        )
        self.assertFalse(plan["authored_component_set_present"])
        self.assertFalse(plan["activation_allowed"])

    def test_reviewed_source_counts_do_not_bypass_missing_landmarks_or_base(self) -> None:
        project = Path(__file__).resolve().parents[1]
        request = json.loads(
            (
                project
                / "Avatar"
                / "avatar_builder"
                / "orchestration_requests"
                / "robert_user_avatar_20260716.json"
            ).read_text()
        )
        evidence = {
            "status": "blocked_review_incomplete",
            "candidate_id": "robert_user_avatar_20260716",
            "subject_id": "robert_mcmurrer",
            "topology_lane": "confirmed_adult_topology",
            "manifest_sha256": "a" * 64,
            "manifest_exact_hash_verified": True,
            "source_count": 15,
            "exact_hash_source_count": 15,
            "reviewed_source_count": 0,
            "front_view_ready": False,
            "depth_view_ready": False,
            "full_body_view_ready": False,
            "single_calibration_frame_ready": False,
            "reviewed_landmark_count": 0,
            "missing_landmark_regions": ["face_outline", "feet"],
            "scale_review": {"ready": False, "mode": "pending"},
            "base_body_review": {"ready": False},
            "review_gaps": [
                "minimum_three_reviewed_sources_missing",
                "reviewed_front_identity_view_missing",
                "reviewed_profile_or_three_quarter_view_missing",
                "reviewed_full_body_view_missing",
                "required_landmark_region_coverage_incomplete",
                "scale_review_artifact_missing",
                "selected_base_body_and_review_missing",
            ],
            "integrity_failures": [],
            "authoring_queue_ready": False,
        }

        plan = plan_orchestration_request(request, multiview_evidence=evidence)

        self.assertEqual(
            "blocked_multiview_evidence_review_incomplete",
            plan["production_state"],
        )
        self.assertEqual(15, plan["multiview_authoring"]["exact_hash_source_count"])
        self.assertEqual(0, plan["multiview_authoring"]["reviewed_source_count"])
        self.assertIn(
            "multiview_landmark_coverage_incomplete", plan["body_blocking_reasons"]
        )
        self.assertIn(
            "multiview_base_body_review_incomplete", plan["body_blocking_reasons"]
        )

    def test_passing_evidence_still_stops_at_missing_likeness_author_backend(self) -> None:
        project = Path(__file__).resolve().parents[1]
        request = json.loads(
            (
                project
                / "Avatar"
                / "avatar_builder"
                / "orchestration_requests"
                / "robert_user_avatar_20260716.json"
            ).read_text()
        )
        evidence = {
            "status": "ready_for_likeness_authoring_queue",
            "candidate_id": "robert_user_avatar_20260716",
            "subject_id": "robert_mcmurrer",
            "topology_lane": "confirmed_adult_topology",
            "manifest_sha256": "a" * 64,
            "manifest_exact_hash_verified": True,
            "source_count": 3,
            "exact_hash_source_count": 3,
            "reviewed_source_count": 3,
            "front_view_ready": True,
            "depth_view_ready": True,
            "full_body_view_ready": True,
            "single_calibration_frame_ready": True,
            "reviewed_landmark_count": 36,
            "missing_landmark_regions": [],
            "scale_review": {"ready": True, "mode": "scale_unknown_review_only"},
            "base_body_review": {"ready": True},
            "review_gaps": [],
            "integrity_failures": [],
            "authoring_queue_ready": True,
        }

        plan = plan_orchestration_request(request, multiview_evidence=evidence)

        self.assertEqual(
            "blocked_multiview_likeness_author_backend_missing",
            plan["production_state"],
        )
        self.assertTrue(plan["multiview_authoring"]["authoring_queue_ready"])
        self.assertFalse(plan["multiview_authoring"]["author_backend_available"])
        self.assertIn(
            "multiview_likeness_author_backend_missing",
            plan["body_blocking_reasons"],
        )

    def test_photo_components_cannot_bypass_multiview_evidence_gate(self) -> None:
        decision = {
            "candidate_id": "fixture_person_001",
            "subject_id": "fixture_subject",
            "status": "capability_review_blocked",
            "blocking_reasons": [],
            "body_private_review_ready": False,
            "body_blocking_reasons": [],
            "advanced_garment_capability_ready": False,
            "garment_blocking_reasons": [],
            "identity_preflight": {"enforced": False, "status": "not_enforced"},
            "route": {
                "status": "selected_and_valid",
                "topology_lane": "confirmed_adult_topology",
                "reconstruction_source_lane": "photo_only_reconstruction",
            },
            "capability_gates": {"component_integrity": {"passed": True}},
        }
        request = {"candidate_id": "fixture_person_001"}
        with patch(
            "Core.avatar_component_production.evaluate_avatar_builder_orchestration",
            return_value=decision,
        ):
            blocked = plan_orchestration_request(request)
            ready = plan_orchestration_request(
                request,
                multiview_evidence={
                    "status": "ready_for_likeness_authoring_queue",
                    "candidate_id": "fixture_person_001",
                    "subject_id": "fixture_subject",
                    "topology_lane": "confirmed_adult_topology",
                    "authoring_queue_ready": True,
                    "review_gaps": [],
                    "integrity_failures": [],
                },
            )

        self.assertEqual(
            "blocked_multiview_evidence_manifest_missing",
            blocked["production_state"],
        )
        self.assertEqual(
            "component_set_authored_ready_for_immutable_adoption",
            ready["production_state"],
        )
        self.assertNotIn(
            "multiview_likeness_author_backend_missing",
            ready["body_blocking_reasons"],
        )

    def test_duplicate_component_bytes_are_rejected(self) -> None:
        temporary, root, request_path = self.make_project("confirmed_adult_topology")
        self.addCleanup(temporary.cleanup)
        request = json.loads(request_path.read_text())
        body = request["source_components"]["body"]
        request["source_components"]["hair"] = copy.deepcopy(body)
        request["source_components"]["hair"]["artifact_role"] = "hair"
        write_json(request_path, request)
        with self.assertRaises(AvatarProductionError):
            validate_production_request_file(root, request_path)

    def test_max_jobs_is_bounded(self) -> None:
        temporary, root, _ = self.make_project("confirmed_adult_topology")
        self.addCleanup(temporary.cleanup)
        with self.assertRaisesRegex(AvatarProductionError, "between 1 and 16"):
            process_queue(root, max_jobs=17)


if __name__ == "__main__":
    unittest.main()
