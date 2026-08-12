from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.build_two_adult_body_quality_candidates_20260717 import (  # noqa: E402
    axis_preflight_sanity,
    generated_evidence_gate_truth,
    render_occupancy_sanity,
    validate_render_bindings,
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TwoBodyQualityReviewPreflightTests(unittest.TestCase):
    def test_bounded_z_up_neutral_axis_passes(self) -> None:
        result = axis_preflight_sanity(
            {
                "finite_coordinates": True,
                "extent": [0.53, 0.31, 1.72],
            }
        )

        self.assertTrue(result["passed"])

    def test_rejected_0539_orientation_shape_fails_closed(self) -> None:
        # Captures the known bad run's neutral aggregate proportions: height
        # was spread across Y/Z and nearly as wide as tall.  It must never be
        # accepted as a standing Z-up review assembly.
        result = axis_preflight_sanity(
            {
                "finite_coordinates": True,
                "extent": [1.525844, 1.728699, 1.509901],
            }
        )

        self.assertFalse(result["passed"])
        self.assertEqual(result["reason"], "rejected_orientation_or_unbounded_assembly")

    def test_missing_axis_evidence_fails_closed(self) -> None:
        self.assertFalse(axis_preflight_sanity({})["passed"])
        self.assertFalse(
            axis_preflight_sanity(
                {"finite_coordinates": False, "extent": [0.5, 0.3, 1.7]}
            )["passed"]
        )

    def test_full_body_crop_is_rejected_by_image_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "cropped.png"
            image = Image.new("RGB", (100, 100), (5, 8, 12))
            draw = ImageDraw.Draw(image)
            draw.rectangle((0, 0, 99, 89), fill=(220, 205, 190))
            image.save(path)

            result = render_occupancy_sanity(path, head_view=False)

        self.assertFalse(result["passed"])
        self.assertGreater(result["bbox_width_fraction"], 0.78)

    def test_centered_full_body_image_can_pass_image_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "centered.png"
            image = Image.new("RGB", (100, 100), (5, 8, 12))
            draw = ImageDraw.Draw(image)
            draw.rectangle((32, 4, 68, 88), fill=(220, 205, 190))
            image.save(path)

            result = render_occupancy_sanity(path, head_view=False)

        self.assertTrue(result["passed"])

    def test_render_binding_requires_hash_and_exact_run_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project_root = Path(temporary)
            run_dir = project_root / "private_review" / "run_1"
            run_dir.mkdir(parents=True)
            render = run_dir / "neutral_front.png"
            render.write_bytes(b"bound render")
            manifest = {
                "renders": {
                    "neutral_front": {
                        "path": render.relative_to(project_root).as_posix(),
                        "sha256": sha256_file(render),
                    }
                }
            }

            result = validate_render_bindings(
                manifest,
                run_dir=run_dir,
                project_root=project_root,
            )
            self.assertTrue(result["passed"])

            manifest["renders"]["neutral_front"]["sha256"] = "0" * 64
            with self.assertRaisesRegex(RuntimeError, "hash binding failed"):
                validate_render_bindings(
                    manifest,
                    run_dir=run_dir,
                    project_root=project_root,
                )

    def test_render_binding_rejects_output_from_a_different_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project_root = Path(temporary)
            run_dir = project_root / "private_review" / "run_1"
            other_run = project_root / "private_review" / "run_2"
            run_dir.mkdir(parents=True)
            other_run.mkdir(parents=True)
            render = other_run / "neutral_front.png"
            render.write_bytes(b"wrong run")
            manifest = {
                "renders": {
                    "neutral_front": {
                        "path": render.relative_to(project_root).as_posix(),
                        "sha256": sha256_file(render),
                    }
                }
            }

            with self.assertRaisesRegex(RuntimeError, "escapes exact run directory"):
                validate_render_bindings(
                    manifest,
                    run_dir=run_dir,
                    project_root=project_root,
                )

    def test_generated_evidence_cannot_self_create_owner_approval(self) -> None:
        truth = generated_evidence_gate_truth(2)

        self.assertEqual(truth["generated_subject_evidence_count"], 2)
        self.assertFalse(truth["owner_approval_may_be_inferred_from_generated_evidence"])
        self.assertFalse(truth["owner_approved"])
        self.assertFalse(truth["positive_proof_gate_released"])
        self.assertFalse(truth["two_subject_autobuild_released"])


if __name__ == "__main__":
    unittest.main()
