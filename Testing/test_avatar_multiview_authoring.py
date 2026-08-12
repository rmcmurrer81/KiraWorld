from __future__ import annotations

import json
import io
from pathlib import Path
import struct
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch


from Core.avatar_multiview_authoring import (
    AvatarMultiviewError,
    REQUIRED_LANDMARK_REGIONS,
    evaluate_multiview_manifest,
    queue_multiview_authoring_manifest,
    sha256_file,
)
from tools import avatar_multiview_authoring_queue as multiview_cli


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def write_png_header(
    path: Path, width: int = 640, height: int = 480, *, tag: bytes = b"fixture"
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


class AvatarMultiviewAuthoringTests(unittest.TestCase):
    def make_manifest(
        self, *, topology_lane: str = "confirmed_adult_topology"
    ) -> tuple[tempfile.TemporaryDirectory, Path, Path]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        candidate_id = "fixture_person_001"
        subject_id = "fixture_subject"
        version_id = "fixture_version_v1"
        evidence_root = root / "Avatar" / "avatar_builder" / "multiview_authoring"
        source_root = evidence_root / "private_sources" / candidate_id
        review_root = evidence_root / "private_reviews" / candidate_id
        views = ("head_front", "three_quarter_left", "full_body_front")
        region_groups = (
            (
                "face_outline",
                "brow",
                "eye_socket_rims",
                "nose",
                "lips",
                "chin",
                "ears",
                "neck",
            ),
            ("shoulders", "chest", "waist", "hips"),
            ("elbows", "wrists", "hands", "knees", "ankles", "feet"),
        )
        source_records = []
        for index, (view, regions) in enumerate(zip(views, region_groups), start=1):
            source_id = f"source_{index:03d}"
            source_path = source_root / f"{source_id}.png"
            write_png_header(source_path, tag=f"fixture-{index}".encode("ascii"))
            source_sha = sha256_file(source_path)
            review = {
                "schema_version": 1,
                "artifact_type": "avatar_multiview_source_review",
                "candidate_id": candidate_id,
                "subject_id": subject_id,
                "selected_version_id": version_id,
                "source_id": source_id,
                "source_sha256": source_sha,
                "review_status": "approved",
                "reviewed_by": "fixture_reviewer",
                "reviewed_at": "2026-07-16T12:00:00Z",
                "same_subject_and_version_confirmed": True,
                "view_label": view,
                "source_dimensions": {"width": 640, "height": 480},
                "crop_pixels": {"x": 0, "y": 0, "width": 640, "height": 480},
                "calibration": {
                    "status": "reviewed",
                    "camera_model": "perspective",
                    "coordinate_frame_id": "fixture_frame_v1",
                },
                "landmark_origin": "human_placed",
                "landmarks": [
                    {
                        "name": f"{region}_{point_index}",
                        "region": region,
                        "x": 100.0 + point_index,
                        "y": 100.0 + point_index,
                        "reviewed": True,
                    }
                    for point_index, region in enumerate(regions)
                ],
            }
            review_path = review_root / f"{source_id}_review.json"
            write_json(review_path, review)
            source_records.append(
                {
                    "source_id": source_id,
                    "source_path": source_path.relative_to(root).as_posix(),
                    "sha256": source_sha,
                    "dimensions": {"width": 640, "height": 480},
                    "review_artifact": {
                        "path": review_path.relative_to(root).as_posix(),
                        "sha256": sha256_file(review_path),
                    },
                }
            )

        scale_review = {
            "schema_version": 1,
            "artifact_type": "avatar_multiview_scale_review",
            "candidate_id": candidate_id,
            "subject_id": subject_id,
            "selected_version_id": version_id,
            "review_status": "approved",
            "reviewed_by": "fixture_reviewer",
            "reviewed_at": "2026-07-16T12:00:00Z",
            "scale_mode": "reviewed_metric",
            "target_height_m": 1.75,
        }
        scale_path = review_root / "scale_review.json"
        write_json(scale_path, scale_review)
        base_path = evidence_root / "bases" / "fixture_base.glb"
        base_path.parent.mkdir(parents=True, exist_ok=True)
        base_path.write_bytes(b"glTF-fixture-base")
        base_sha = sha256_file(base_path)
        base_review = {
            "schema_version": 1,
            "artifact_type": "avatar_multiview_base_review",
            "candidate_id": candidate_id,
            "subject_id": subject_id,
            "selected_version_id": version_id,
            "base_body_sha256": base_sha,
            "topology_lane": topology_lane,
            "review_status": "approved",
            "reviewed_by": "fixture_reviewer",
            "reviewed_at": "2026-07-16T12:00:00Z",
            "rig_compatible_cage_source_confirmed": True,
            "new_candidate_surface_required": True,
        }
        base_review_path = review_root / "base_review.json"
        write_json(base_review_path, base_review)
        manifest = {
            "schema_version": 1,
            "manifest_type": "avatar_multiview_likeness_evidence",
            "candidate_id": candidate_id,
            "subject_id": subject_id,
            "selected_version_id": version_id,
            "topology_lane": topology_lane,
            "output_rule": "private_review_only_not_runtime",
            "runtime_activation_requested": False,
            "public_export_allowed": False,
            "source_images": source_records,
            "scale_review_artifact": {
                "path": scale_path.relative_to(root).as_posix(),
                "sha256": sha256_file(scale_path),
            },
            "base_body": {
                "status": "reviewed",
                "path": base_path.relative_to(root).as_posix(),
                "sha256": base_sha,
                "topology_lane": topology_lane,
                "allowed_use": "cage_fit_source_new_surface_required",
                "copy_as_candidate_body_allowed": False,
                "review_artifact": {
                    "path": base_review_path.relative_to(root).as_posix(),
                    "sha256": sha256_file(base_review_path),
                },
            },
            "reference_models": [],
        }
        manifest_path = evidence_root / "manifests" / f"{candidate_id}.json"
        write_json(manifest_path, manifest)
        return temporary, root, manifest_path

    def test_complete_reviewed_manifest_is_ready_without_creating_a_mesh(self) -> None:
        temporary, root, manifest_path = self.make_manifest()
        self.addCleanup(temporary.cleanup)
        result = evaluate_multiview_manifest(
            root,
            manifest_path,
            expected_candidate_id="fixture_person_001",
            expected_subject_id="fixture_subject",
            expected_topology_lane="confirmed_adult_topology",
            expected_manifest_sha256=sha256_file(manifest_path),
        )

        self.assertEqual("ready_for_likeness_authoring_queue", result["status"])
        self.assertTrue(result["authoring_queue_ready"])
        self.assertEqual(3, result["exact_hash_source_count"])
        self.assertEqual(3, result["reviewed_source_count"])
        self.assertEqual(set(), set(result["missing_landmark_regions"]))
        self.assertEqual(
            set(REQUIRED_LANDMARK_REGIONS),
            set(result["covered_landmark_regions"]),
        )
        self.assertNotIn("source_path", json.dumps(result))
        self.assertFalse(result["runtime_activation_allowed"])

    def test_pending_draft_hashes_sources_but_refuses_authoring_queue(self) -> None:
        temporary, root, manifest_path = self.make_manifest()
        self.addCleanup(temporary.cleanup)
        manifest = json.loads(manifest_path.read_text())
        for source in manifest["source_images"]:
            source.pop("review_artifact")
            source["review_status"] = "pending_human_view_landmark_calibration_review"
        manifest.pop("scale_review_artifact")
        manifest["scale_review"] = {"status": "pending"}
        manifest["base_body"] = {"status": "pending"}
        write_json(manifest_path, manifest)

        result = evaluate_multiview_manifest(root, manifest_path)

        self.assertEqual("blocked_review_incomplete", result["status"])
        self.assertEqual(3, result["exact_hash_source_count"])
        self.assertEqual(0, result["reviewed_source_count"])
        self.assertIn("scale_review_artifact_missing", result["review_gaps"])
        self.assertIn(
            "selected_base_body_and_review_missing", result["review_gaps"]
        )
        with self.assertRaisesRegex(AvatarMultiviewError, "not ready"):
            queue_multiview_authoring_manifest(root, manifest_path)

    def test_changed_image_fails_exact_hash_binding(self) -> None:
        temporary, root, manifest_path = self.make_manifest()
        self.addCleanup(temporary.cleanup)
        manifest = json.loads(manifest_path.read_text())
        source_path = root / manifest["source_images"][0]["source_path"]
        source_path.write_bytes(source_path.read_bytes() + b"changed")

        result = evaluate_multiview_manifest(root, manifest_path)

        self.assertEqual("blocked_manifest_integrity_or_identity", result["status"])
        self.assertTrue(
            any("source image hash mismatch" in item for item in result["integrity_failures"])
        )

    def test_unconfirmed_automatic_landmarks_fail_closed(self) -> None:
        temporary, root, manifest_path = self.make_manifest()
        self.addCleanup(temporary.cleanup)
        manifest = json.loads(manifest_path.read_text())
        binding = manifest["source_images"][0]["review_artifact"]
        review_path = root / binding["path"]
        review = json.loads(review_path.read_text())
        review["landmark_origin"] = "automatic_suggestion"
        review["automatic_suggestions_confirmed_by_reviewer"] = False
        write_json(review_path, review)
        binding["sha256"] = sha256_file(review_path)
        write_json(manifest_path, manifest)

        result = evaluate_multiview_manifest(root, manifest_path)

        self.assertFalse(result["authoring_queue_ready"])
        self.assertTrue(
            any(
                "automatic landmark suggestions are not confirmed" in item
                for item in result["integrity_failures"]
            )
        )

    def test_non_adult_topology_lane_stays_exact(self) -> None:
        temporary, root, manifest_path = self.make_manifest(
            topology_lane="non_adult_doll_safe_topology"
        )
        self.addCleanup(temporary.cleanup)

        accepted = evaluate_multiview_manifest(
            root,
            manifest_path,
            expected_topology_lane="non_adult_doll_safe_topology",
        )
        mismatched = evaluate_multiview_manifest(
            root,
            manifest_path,
            expected_topology_lane="confirmed_adult_topology",
        )

        self.assertTrue(accepted["authoring_queue_ready"])
        self.assertFalse(mismatched["authoring_queue_ready"])
        self.assertIn(
            "manifest_topology_lane_mismatch", mismatched["integrity_failures"]
        )

    def test_superseded_audit_manifest_can_never_enter_queue(self) -> None:
        temporary, root, manifest_path = self.make_manifest()
        self.addCleanup(temporary.cleanup)
        manifest = json.loads(manifest_path.read_text())
        manifest["authoring_status"] = "superseded_audit_only"
        manifest["queue_eligible"] = False
        write_json(manifest_path, manifest)

        result = evaluate_multiview_manifest(root, manifest_path)

        self.assertFalse(result["authoring_queue_ready"])
        self.assertIn(
            "manifest_superseded_audit_only", result["integrity_failures"]
        )
        with self.assertRaisesRegex(AvatarMultiviewError, "not ready"):
            queue_multiview_authoring_manifest(root, manifest_path)

    def test_passing_evidence_queues_idempotently_but_backend_remains_absent(self) -> None:
        temporary, root, manifest_path = self.make_manifest()
        self.addCleanup(temporary.cleanup)

        first = queue_multiview_authoring_manifest(root, manifest_path)
        second = queue_multiview_authoring_manifest(root, manifest_path)

        self.assertEqual(first["job_id"], second["job_id"])
        self.assertEqual(
            "queued_waiting_for_likeness_author_backend", first["status"]
        )
        self.assertEqual(
            "already_queued_waiting_for_likeness_author_backend", second["status"]
        )
        self.assertFalse(first["author_backend_available"])
        self.assertFalse(first["runtime_activation_allowed"])

    def test_cli_evaluate_reports_ready_contract_without_queueing(self) -> None:
        temporary, root, manifest_path = self.make_manifest()
        self.addCleanup(temporary.cleanup)
        stdout = io.StringIO()
        stderr = io.StringIO()
        with (
            patch.object(multiview_cli, "PROJECT_ROOT", root),
            patch(
                "sys.argv",
                [
                    "avatar_multiview_authoring_queue.py",
                    "evaluate",
                    "--manifest",
                    str(manifest_path),
                    "--candidate-id",
                    "fixture_person_001",
                    "--subject-id",
                    "fixture_subject",
                    "--topology-lane",
                    "confirmed_adult_topology",
                ],
            ),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            exit_code = multiview_cli.main()

        payload = json.loads(stdout.getvalue())
        self.assertEqual(0, exit_code)
        self.assertEqual("ready_for_likeness_authoring_queue", payload["status"])
        self.assertEqual("", stderr.getvalue())
        self.assertFalse(
            (root / "Avatar" / "avatar_builder" / "multiview_authoring" / "queued").exists()
        )


if __name__ == "__main__":
    unittest.main()
