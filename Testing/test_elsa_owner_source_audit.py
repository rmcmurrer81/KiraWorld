from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "Data/codex_reports/20260716_elsa_frozen_adventures_owner_source_audit.json"
REFERENCE_MANIFEST = ROOT / "Avatar/avatar_builder/reference_models/elsa_frozen_reference/reference_model_manifest.json"
RENDER_MANIFEST = ROOT / "Avatar/avatar_builder/reference_models/elsa_frozen_reference/private_source_audit_20260716_primary/source_quality_audit_manifest.json"


class ElsaOwnerSourceAuditTests(unittest.TestCase):
    def test_incomplete_source_cannot_release_positive_proof(self) -> None:
        audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
        self.assertFalse(audit["candidate_created"])
        self.assertFalse(audit["candidate_enrolled"])
        self.assertFalse(audit["runtime_activation_allowed"])
        self.assertFalse(audit["positive_proof_autobuild_released"])
        self.assertFalse(audit["mesh_evidence"]["skin"]["complete_body_under_outfit"])
        self.assertFalse(audit["decision"]["may_be_called_complete_adult_body"])
        self.assertFalse(audit["decision"]["may_be_enrolled_as_positive_proof_candidate_now"])
        self.assertFalse(audit["decision"]["may_release_auto_build"])

    def test_exact_source_remains_reference_only(self) -> None:
        audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
        manifest = json.loads(REFERENCE_MANIFEST.read_text(encoding="utf-8"))
        expected = audit["selected_owner_source"]["sha256"].lower()
        matching = [item for item in manifest["models"] if item["sha256"].lower() == expected]
        self.assertEqual(len(matching), 1)
        self.assertTrue(matching[0]["reference_only"])
        self.assertFalse(matching[0]["copy_as_avatar_body_allowed"])
        self.assertEqual(matching[0]["maturity_class"], "adult")

    def test_private_render_pack_is_diagnostic_only(self) -> None:
        manifest = json.loads(RENDER_MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["artifact_type"], "private_clothed_owner_source_quality_audit")
        self.assertTrue(manifest["source_not_modified"])
        self.assertFalse(manifest["candidate_created"])
        self.assertFalse(manifest["runtime_activation_allowed"])
        self.assertEqual(len(manifest["renders"]), 10)
        for render in manifest["renders"]:
            path = Path(render["path"])
            self.assertTrue(path.is_file(), render["path"])
            self.assertEqual(path.suffix.lower(), ".png")


if __name__ == "__main__":
    unittest.main()
