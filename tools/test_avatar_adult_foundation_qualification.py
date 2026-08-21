"""Focused tests for fail-closed adult-foundation qualification."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import Core.avatar_adult_foundation_qualification as qualification
from Core.avatar_adult_foundation_qualification import (
    POLICY_PATH,
    audit_registered_adult_foundations,
    evaluate_adult_foundation_qualification,
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def binding(root: Path, path: Path) -> dict[str, str]:
    return {
        "path": path.relative_to(root).as_posix(),
        "sha256": sha256(path),
    }


class AdultFoundationQualificationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="kira_adult_foundation_gate_"
        )
        self.root = Path(self.temporary.name)
        self.policy_path = Path("config/adult_foundation_policy.json")
        policy_target = self.root / self.policy_path
        policy_target.parent.mkdir(parents=True, exist_ok=True)
        policy_target.write_bytes((PROJECT_ROOT / POLICY_PATH).read_bytes())
        self.policy = json.loads(policy_target.read_text(encoding="utf-8"))
        self.registry_path = Path("config/adult_foundation_registry.json")

        self.source = self.root / "Avatar/sources/complete_adult_female.glb"
        self.source.parent.mkdir(parents=True, exist_ok=True)
        self.source.write_bytes(b"synthetic-complete-adult-female-fixture")
        self.license_evidence = self.root / "Avatar/licenses/source_license.json"
        write_json(
            self.license_evidence,
            {
                "license": "CC0-1.0",
                "foundation_use_allowed": True,
            },
        )
        self.entry = self.make_complete_entry()
        self.topology_path = self.root / "evidence/topology.json"
        self.relationship_path = self.root / "evidence/relationships.json"
        write_json(self.topology_path, self.make_topology_report())
        write_json(self.relationship_path, self.make_relationship_report())
        self.evidence = self.current_evidence()
        self.write_registry([self.entry])

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def make_complete_entry(self) -> dict:
        return {
            "foundation_id": "synthetic_complete_adult_female",
            "display_name": "Synthetic complete adult female fixture",
            "source_artifact": binding(self.root, self.source),
            "artifact_kind": "single_asset",
            "source_configuration_artifacts": [],
            "source_provenance": {
                "title": "Synthetic complete adult female fixture",
                "author": "fixture_author",
                "source_url": "https://example.test/source",
            },
            "maturity": {
                "status": "confirmed_adult",
                "body_class": "adult_female",
            },
            "foundation_role": "adaptable_foundation",
            "candidate_use": {
                "new_surface_derivative_allowed": True,
                "copy_as_candidate_body_allowed": False,
            },
            "license": {
                "id": "CC0-1.0",
                "url": "https://creativecommons.org/publicdomain/zero/1.0/",
                "adaptation_allowed": True,
                "foundation_use_allowed": True,
                "evidence": binding(self.root, self.license_evidence),
            },
            "known_blockers": [],
            "positive_independent_evidence": None,
            "qualified": False,
        }

    def make_topology_report(self) -> dict:
        return {
            "schema_version": 1,
            "artifact_type": "independent_adult_foundation_topology_audit",
            "status": "PASSED",
            "passed": True,
            "artifact_sha256": sha256(self.source),
            "body_class": "adult_female",
            "candidate_author_id": "fixture_builder",
            "independent_reviewer": {
                "id": "topology_auditor",
                "role": "independent_topology_auditor",
            },
            "reviewed_at": "2026-08-01T12:00:00Z",
            "exact_artifact_sha256_verified": True,
            "complete_scan": True,
            "metrics": deepcopy(self.policy["required_topology_metrics"]),
        }

    def make_relationship_report(self) -> dict:
        relationships = {
            name: {
                "geometry_present": True,
                "connected_to_primary_surface": True,
                "not_painted_only": True,
            }
            for name in self.policy["required_adult_female_relationships"]
        }
        return {
            "schema_version": 1,
            "artifact_type": "independent_adult_female_relationship_review",
            "status": "PASSED",
            "passed": True,
            "artifact_sha256": sha256(self.source),
            "body_class": "adult_female",
            "candidate_author_id": "fixture_builder",
            "independent_reviewer": {
                "id": "adult_anatomy_reviewer",
                "role": "independent_adult_anatomy_reviewer",
            },
            "reviewed_at": "2026-08-01T12:05:00Z",
            "exact_artifact_sha256_verified": True,
            "relationships": relationships,
            "negative_findings": deepcopy(
                self.policy["required_negative_findings"]
            ),
        }

    def current_evidence(self) -> dict[str, dict[str, str]]:
        return {
            "topology": binding(self.root, self.topology_path),
            "relationships": binding(self.root, self.relationship_path),
        }

    def write_registry(self, entries: list[dict]) -> None:
        write_json(
            self.root / self.registry_path,
            {
                "schema_version": 1,
                "registry_id": "avatar_builder_adult_foundation_registry_v1",
                "policy": self.policy_path.as_posix(),
                "status": "TEST_FIXTURE",
                "entries": entries,
                "invariants": {
                    "confirmed_adult_implies_complete_topology": False,
                    "runtime_mutation_allowed": False,
                },
            },
        )

    def evaluate(self, evidence: dict | None = None) -> dict:
        return evaluate_adult_foundation_qualification(
            self.root,
            self.entry["foundation_id"],
            independent_evidence=self.evidence if evidence is None else evidence,
            policy_path=self.policy_path,
            registry_path=self.registry_path,
        )

    def refresh_entry_and_evidence(self) -> None:
        self.evidence = self.current_evidence()
        self.write_registry([self.entry])

    def test_exact_independent_complete_source_qualifies(self) -> None:
        result = self.evaluate()
        self.assertTrue(result["adult_eligible"])
        self.assertTrue(result["foundation_authority"]["authorized"])
        self.assertTrue(result["complete_adult_topology_proven"])
        self.assertTrue(result["qualified_for_adult_foundation"])
        self.assertEqual([], result["blockers"])
        self.assertFalse(result["build_performed"])
        self.assertFalse(result["render_performed"])
        self.assertFalse(result["runtime_mutation_performed"])
        self.assertFalse(result["runtime_activation_allowed"])

    def test_confirmed_adult_does_not_imply_complete_topology(self) -> None:
        report = self.make_relationship_report()
        report["relationships"].pop("vestibule")
        write_json(self.relationship_path, report)
        self.evidence = self.current_evidence()
        result = self.evaluate()
        self.assertTrue(result["adult_eligible"])
        self.assertFalse(result["complete_adult_topology_proven"])
        self.assertFalse(result["qualified_for_adult_foundation"])
        self.assertIn(
            "relationship_record_missing:vestibule",
            result["blockers"],
        )

    def test_wrong_sex_helper_blocks(self) -> None:
        report = self.make_relationship_report()
        report["negative_findings"]["wrong_sex_helper_present"] = True
        write_json(self.relationship_path, report)
        self.evidence = self.current_evidence()
        result = self.evaluate()
        self.assertIn(
            "relationship_negative_finding_not_satisfied:wrong_sex_helper_present",
            result["blockers"],
        )
        self.assertFalse(result["qualified_for_adult_foundation"])

    def test_self_intersection_blocks(self) -> None:
        report = self.make_topology_report()
        report["metrics"]["nonadjacent_self_intersection_pairs"] = 1
        write_json(self.topology_path, report)
        self.evidence = self.current_evidence()
        result = self.evaluate()
        self.assertIn(
            "topology_metric_not_satisfied:nonadjacent_self_intersection_pairs",
            result["blockers"],
        )

    def test_exact_artifact_hash_mismatch_blocks(self) -> None:
        report = self.make_topology_report()
        report["artifact_sha256"] = "f" * 64
        write_json(self.topology_path, report)
        self.evidence = self.current_evidence()
        result = self.evaluate()
        self.assertIn(
            "topology_report_artifact_sha256_mismatch",
            result["blockers"],
        )

    def test_changed_evidence_bytes_block(self) -> None:
        stale = deepcopy(self.evidence)
        report = self.make_topology_report()
        report["extra_unbound_change"] = True
        write_json(self.topology_path, report)
        result = self.evaluate(stale)
        self.assertIn(
            "independent_topology_evidence_sha256_mismatch",
            result["blockers"],
        )

    def test_missing_source_hash_and_license_block(self) -> None:
        self.entry["source_artifact"].pop("sha256")
        self.entry["license"] = {}
        self.write_registry([self.entry])
        result = self.evaluate()
        self.assertIn("source_artifact_sha256_invalid", result["blockers"])
        self.assertIn("license_id_missing", result["blockers"])
        self.assertIn("license_evidence_binding_missing", result["blockers"])
        self.assertFalse(result["foundation_authority"]["authorized"])

    def test_parametric_source_requires_exact_configuration_binding(self) -> None:
        self.entry["artifact_kind"] = "parametric_source_set"
        self.write_registry([self.entry])
        result = self.evaluate()
        self.assertIn(
            "parametric_source_configuration_missing",
            result["blockers"],
        )
        self.assertFalse(result["foundation_authority"]["authorized"])

        configuration = self.root / "Avatar/sources/female_macro.target"
        configuration.write_bytes(b"synthetic-female-macro-configuration")
        self.entry["source_configuration_artifacts"] = [
            binding(self.root, configuration)
        ]
        self.write_registry([self.entry])
        result = self.evaluate()
        self.assertTrue(result["foundation_authority"]["authorized"])

    def test_reference_only_cannot_be_bypassed_by_passing_evidence(self) -> None:
        self.entry["foundation_role"] = "reference_only"
        self.write_registry([self.entry])
        result = self.evaluate()
        self.assertTrue(result["adult_eligible"])
        self.assertTrue(result["complete_adult_topology_proven"])
        self.assertFalse(result["foundation_authority"]["authorized"])
        self.assertFalse(result["qualified_for_adult_foundation"])
        self.assertIn(
            "foundation_role_not_allowed:reference_only",
            result["blockers"],
        )

    def test_known_registry_blocker_cannot_be_overridden(self) -> None:
        self.entry["known_blockers"] = [
            {
                "code": "doll_safe_or_incomplete",
                "evidence": binding(self.root, self.relationship_path),
            }
        ]
        self.write_registry([self.entry])
        result = self.evaluate()
        self.assertIn(
            "registry_known_blocker:doll_safe_or_incomplete",
            result["blockers"],
        )
        self.assertFalse(result["complete_adult_topology_proven"])

    def test_unconfirmed_maturity_stays_separate_from_topology(self) -> None:
        self.entry["maturity"]["status"] = "unresolved"
        self.write_registry([self.entry])
        result = self.evaluate()
        self.assertFalse(result["adult_eligible"])
        self.assertTrue(result["complete_adult_topology_proven"])
        self.assertFalse(result["qualified_for_adult_foundation"])
        self.assertIn("adult_maturity_not_confirmed", result["blockers"])

    def test_reviewer_must_be_independent(self) -> None:
        report = self.make_relationship_report()
        report["independent_reviewer"]["id"] = "fixture_builder"
        write_json(self.relationship_path, report)
        self.evidence = self.current_evidence()
        result = self.evaluate()
        self.assertIn(
            "relationship_report_reviewer_not_independent",
            result["blockers"],
        )

    def test_unknown_foundation_fails_closed(self) -> None:
        result = evaluate_adult_foundation_qualification(
            self.root,
            "unknown_foundation",
            independent_evidence=self.evidence,
            policy_path=self.policy_path,
            registry_path=self.registry_path,
        )
        self.assertIn("foundation_not_registered", result["blockers"])
        self.assertFalse(result["qualified_for_adult_foundation"])

    def test_multiply_linked_source_artifact_fails_closed(self) -> None:
        hardlink = self.root / "Avatar/sources/hardlinked_complete_adult_female.glb"
        try:
            os.link(self.source, hardlink)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"hardlink creation unavailable: {exc}")
        self.entry["source_artifact"] = binding(self.root, hardlink)
        self.write_registry([self.entry])

        result = self.evaluate()

        self.assertIn("source_artifact_path_invalid", result["blockers"])
        self.assertFalse(result["foundation_authority"]["authorized"])
        self.assertFalse(result["qualified_for_adult_foundation"])

    def test_reparse_inspection_error_fails_closed(self) -> None:
        with mock.patch.object(
            qualification,
            "_is_link_or_junction",
            side_effect=OSError("inspection denied"),
        ):
            result = self.evaluate()

        self.assertIn("adult_foundation_policy_path_invalid", result["blockers"])
        self.assertFalse(result["qualified_for_adult_foundation"])

    @unittest.skipUnless(os.name == "nt", "Windows path-prefix regression")
    def test_unc_and_long_local_paths_receive_correct_extended_prefixes(self) -> None:
        unc = qualification._io_path(Path(r"\\server\share\folder\source.glb"))
        self.assertEqual(
            str(unc),
            r"\\?\UNC\server\share\folder\source.glb",
        )

        long_relative = Path("long_path_fixture")
        for index in range(4):
            long_relative /= f"segment_{index}_" + "x" * 55
        long_relative /= "source.glb"
        normal_target = self.root / long_relative
        extended_target = qualification._io_path(normal_target)
        self.assertGreater(len(str(normal_target)), 260)
        self.assertTrue(str(extended_target).startswith("\\\\?\\"))
        long_root = qualification._io_path(self.root / "long_path_fixture")
        try:
            extended_target.parent.mkdir(parents=True, exist_ok=True)
            extended_target.write_bytes(b"long-path-foundation-fixture")
            observed = qualification._project_file(
                self.root,
                long_relative.as_posix(),
            )
            self.assertEqual(observed, extended_target)
        finally:
            if long_root.exists():
                shutil.rmtree(long_root)

    def test_known_sources_stay_blocked_and_derived_source_qualifies(self) -> None:
        audit = audit_registered_adult_foundations(PROJECT_ROOT)
        self.assertEqual(6, audit["registered_count"])
        self.assertEqual(1, audit["qualified_count"])
        self.assertEqual("qualified_sources_present", audit["status"])
        self.assertEqual([], audit["blockers"])
        by_id = {row["foundation_id"]: row for row in audit["results"]}

        makehuman = by_id["makehuman_hm08_female_macro_source"]
        self.assertTrue(makehuman["adult_eligible"])
        self.assertFalse(makehuman["complete_adult_topology_proven"])
        self.assertIn(
            "registry_known_blocker:doll_safe_or_incomplete",
            makehuman["blockers"],
        )

        blackproject = by_id[
            "blackproject_base_female_character_cc_by_4"
        ]
        self.assertFalse(blackproject["complete_adult_topology_proven"])
        if blackproject["foundation_authority"]["authorized"]:
            self.assertIn(
                "registry_known_blocker:self_intersections_present",
                blackproject["blockers"],
            )
        else:
            self.assertIn("source_artifact_path_invalid", blackproject["blockers"])
            self.assertFalse(blackproject["qualified_for_adult_foundation"])

        for cage_id in (
            "womenfemale_body_base_rigged_3ec62ba8d7",
            "base_female_game_ready_rigged_low_poly_471903a311",
        ):
            self.assertIn(
                "foundation_role_not_allowed:cage_fit_only",
                by_id[cage_id]["blockers"],
            )

        reference = by_id["female_anatomy_study_progress_2_b0577836d8"]
        self.assertIn(
            "foundation_role_not_allowed:reference_only",
            reference["blockers"],
        )
        self.assertFalse(audit["build_performed"])
        self.assertFalse(audit["render_performed"])
        self.assertFalse(audit["runtime_mutation_performed"])

        derived = by_id[
            "generic_makehuman_adult_female_foundation_v1_20260801"
        ]
        self.assertTrue(derived["adult_eligible"])
        self.assertTrue(derived["foundation_authority"]["authorized"])
        self.assertTrue(derived["complete_adult_topology_proven"])
        self.assertTrue(derived["qualified_for_adult_foundation"])
        self.assertEqual([], derived["blockers"])
        self.assertEqual(
            "3911419c44681d25f33892122e61206f1f4651bb78b3e403e377d1ed099cde2f",
            derived["foundation_authority"]["source_artifact_sha256"],
        )
        self.assertFalse(derived["runtime_activation_allowed"])
        self.assertFalse(derived["public_export_allowed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
