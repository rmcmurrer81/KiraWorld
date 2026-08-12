import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from Core.avatar_static_anatomy_quality import REQUIRED_VIEWS
from Core.body_runtime_eligibility import evaluate_body_runtime_eligibility


class BodyRuntimeEligibilityTests(unittest.TestCase):
    def rendered_visual_evidence(
        self,
        root,
        body_hash,
        *,
        review_decision="APPROVED_BY_OWNER",
        pelvis_attachment_status="ACCEPTED_BY_OWNER",
        pelvis_gap=False,
        rejection_reasons=None,
    ):
        views = {}
        for view in sorted(REQUIRED_VIEWS):
            path = root / f"{view}.png"
            path.write_bytes(f"rendered:{view}".encode("utf-8"))
            views[view] = {
                "path": path.name,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "candidate_body_sha256": body_hash,
            }
        return {
            "candidate_body_sha256": body_hash,
            "review_decision": review_decision,
            "pelvis_attachment_status": pelvis_attachment_status,
            "pelvis_open_or_spatial_gap_detected": pelvis_gap,
            "rejection_reasons": rejection_reasons or [],
            "views": views,
        }

    def approval_manifest(self, root, body, **evidence_changes):
        body_hash = hashlib.sha256(body.read_bytes()).hexdigest()
        return {
            "status": "APPROVED FOR MANUAL RUNTIME ACTIVATION",
            "runtime_activation_allowed": True,
            "body_path": body.name,
            "body_sha256": body_hash,
            "review_state": {
                "owner_approved": True,
                "rendered_visual_review_passed": True,
                "runtime_quality_gate_passed": True,
                "rendered_visual_evidence": self.rendered_visual_evidence(
                    root, body_hash, **evidence_changes
                ),
            },
        }

    def test_file_or_has_body_alone_never_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "body.glb").write_bytes(b"glb")
            result = evaluate_body_runtime_eligibility(
                root,
                {
                    "has_body": True,
                    "model_url": "body.glb",
                    "model_status": "rigged_model_ready",
                },
            )
            self.assertFalse(result["eligible"])
            self.assertIn("body_approval_manifest_missing", result["reasons"])

    def test_hash_bound_reviewed_body_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            body = root / "body.glb"
            body.write_bytes(b"approved-body")
            manifest = self.approval_manifest(root, body)
            (root / "manifest.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )
            result = evaluate_body_runtime_eligibility(
                root, {"body_approval_manifest": "manifest.json"}
            )
            self.assertTrue(result["eligible"], result)

    def test_partial_candidate_is_blocked_even_if_boolean_true(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            body = root / "body.glb"
            body.write_bytes(b"body")
            manifest = self.approval_manifest(root, body)
            manifest["status"] = "PARTIAL — MOVEMENT INCOMPLETE"
            (root / "manifest.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )
            result = evaluate_body_runtime_eligibility(
                root, {"body_approval_manifest": "manifest.json"}
            )
            self.assertFalse(result["eligible"])
            self.assertIn("body_status_not_eligible", result["reasons"])

    def test_awaiting_static_review_never_passes_even_with_true_booleans(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            body = root / "body.glb"
            body.write_bytes(b"static-candidate")
            manifest = self.approval_manifest(root, body)
            manifest["status"] = "AWAITING ROBERT STATIC LIKENESS REVIEW"
            (root / "manifest.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )
            result = evaluate_body_runtime_eligibility(
                root, {"body_approval_manifest": "manifest.json"}
            )
            self.assertFalse(result["eligible"])
            self.assertIn("body_status_not_eligible", result["reasons"])
            self.assertIn("body_status_not_runtime_approved", result["reasons"])

    def test_visual_rejection_and_spatial_gap_override_approval_booleans(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            body = root / "body.glb"
            body.write_bytes(b"clean-topology-is-not-enough")
            manifest = self.approval_manifest(
                root,
                body,
                review_decision="REJECTED_BY_OWNER",
                pelvis_attachment_status="REJECTED",
                pelvis_gap=True,
                rejection_reasons=["visible hole above the attachment"],
            )
            (root / "manifest.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )
            result = evaluate_body_runtime_eligibility(
                root, {"body_approval_manifest": "manifest.json"}
            )
            self.assertFalse(result["eligible"])
            self.assertIn(
                "rendered_visual_review_not_owner_approved", result["reasons"]
            )
            self.assertIn(
                "pelvis_open_or_spatial_gap_not_cleared", result["reasons"]
            )
            self.assertIn(
                "pelvis_attachment_visual_acceptance_missing", result["reasons"]
            )

    def test_changed_render_file_breaks_hash_bound_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            body = root / "body.glb"
            body.write_bytes(b"approved-body")
            manifest = self.approval_manifest(root, body)
            (root / "front.png").write_bytes(b"changed after owner review")
            (root / "manifest.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )
            result = evaluate_body_runtime_eligibility(
                root, {"body_approval_manifest": "manifest.json"}
            )
            self.assertFalse(result["eligible"])
            self.assertIn(
                "rendered_visual_view_hash_mismatch:front", result["reasons"]
            )


if __name__ == "__main__":
    unittest.main()
