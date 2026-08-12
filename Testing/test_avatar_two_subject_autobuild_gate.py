from __future__ import annotations

import contextlib
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from Core.avatar_positive_proof_gate import (  # noqa: E402
    build_downstream_release_plan,
    evaluate_positive_proof,
)
from Core.avatar_two_subject_autobuild_gate import (  # noqa: E402
    build_two_subject_autobuild_dry_run_plan,
    evaluate_two_subject_autobuild_gate,
)
import tools.evaluate_avatar_positive_proof_gate as legacy_cli  # noqa: E402


COMPONENTS = ["body", "eyes", "hair", "clothing", "rig"]
DOMAINS = [
    "topology",
    "rig_and_deformation",
    "skin_integrity",
    "ground_contact",
    "object_contact",
    "clothed_visual_quality",
]
GATES_BY_DOMAIN = {
    "topology": ["topology_lane_correct"],
    "rig_and_deformation": [
        "stable_rig",
        "walk_sit_reach_deformation",
        "face_controls",
        "walk_stop_turn",
        "sit_stand_lie_rise",
    ],
    "skin_integrity": ["skin_material_and_deformation_integrity"],
    "ground_contact": ["feet_and_ground_contact"],
    "object_contact": ["prop_contact"],
    "clothed_visual_quality": [
        "visual_likeness_reviewed",
        "clothed_visual_integrity",
        "visible_realistic_eyes",
        "separate_clothing_integrity",
        "privacy_review",
        "owner_visual_approval",
    ],
}
ALL_GATES = [name for names in GATES_BY_DOMAIN.values() for name in names]
OWNER_FLAGS = [
    "reviewed_clothed",
    "reviewed_in_motion",
    "reviewed_full_body",
    "reviewed_face_and_eyes",
    "reviewed_skin_and_deformation",
    "reviewed_ground_contact",
    "reviewed_object_contact",
    "counts_toward_two_subject_gate",
    "allow_batch_authoring_after_two_distinct_qualified_subjects",
]


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def content_addressed_json(root: Path, relative_dir: str, payload: object) -> tuple[Path, str]:
    directory = root / relative_dir
    draft = directory / "draft.json"
    write_json(draft, payload)
    sha256 = digest(draft)
    target = directory / f"{sha256}.json"
    draft.replace(target)
    return target, sha256


def relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


class TwoSubjectFixture:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.registry_path = root / "Avatar/avatar_builder/policies/candidate_identity_variant_registry.json"
        self.backlog_path = root / "Avatar/avatar_builder/authoring_backlogs/body_authoring_backlog_after_positive_proof_20260716.json"
        self.v1_policy_path = root / "Avatar/avatar_builder/policies/positive_proof_autobuild_gate_v1.json"
        self.v2_policy_path = root / "Avatar/avatar_builder/policies/two_subject_autobuild_gate_v2.json"
        self.proof_root = "Avatar/avatar_builder/autobuild_two_subject/immutable/subject_proofs"
        self.review_root = "Avatar/avatar_builder/autobuild_two_subject/immutable/owner_reviews"
        self.domain_root = "Avatar/avatar_builder/autobuild_two_subject/immutable/domain_evidence"
        for path in (self.proof_root, self.review_root, self.domain_root):
            (root / path).mkdir(parents=True, exist_ok=True)

        self.candidates = [
            {"canonical_candidate_id": "candidate_a", "subject_id": "subject_a"},
            {"canonical_candidate_id": "candidate_b", "subject_id": "subject_b"},
            {"canonical_candidate_id": "candidate_a_variant", "subject_id": "subject_a"},
            {"canonical_candidate_id": "candidate_next", "subject_id": "subject_next"},
        ]
        self.write_registry_and_backlog()
        write_json(
            self.v1_policy_path,
            {
                "schema_version": 1,
                "owner_authority_id": "real_robert",
                "maximum_concurrent_downstream_builds": 1,
                "required_component_artifacts": COMPONENTS,
                "required_gates": ALL_GATES,
                "required_owner_decision": "approve_body_for_two_subject_autobuild_qualification",
                "runtime_activation_allowed": False,
                "current_proof_path": "",
            },
        )
        self.write_v2_policy([])

    def write_registry_and_backlog(self) -> None:
        write_json(self.registry_path, {"schema_version": 1, "candidates": self.candidates})
        write_json(
            self.backlog_path,
            {
                "candidate_identity_registry_sha256": digest(self.registry_path),
                "next_owner_reviewed_likeness_builds": [
                    {"candidate_id": "candidate_a"},
                    {"candidate_id": "candidate_b"},
                    {"candidate_id": "candidate_next"},
                ],
            },
        )

    def write_v2_policy(self, qualifications: list[dict[str, str]]) -> None:
        write_json(
            self.v2_policy_path,
            {
                "schema_version": 2,
                "policy_id": "avatar_two_distinct_subject_autobuild_gate_v2",
                "minimum_distinct_canonical_subjects": 2,
                "maximum_enrolled_qualifications": 8,
                "maximum_concurrent_downstream_builds": 1,
                "owner_authority_id": "real_robert",
                "required_owner_decision": "approve_body_for_two_subject_autobuild_qualification",
                "required_component_artifacts": COMPONENTS,
                "required_evidence_domains": DOMAINS,
                "required_legacy_gates_by_domain": GATES_BY_DOMAIN,
                "required_owner_review_flags": OWNER_FLAGS,
                "immutable_roots": {
                    "subject_proofs": self.proof_root,
                    "owner_reviews": self.review_root,
                    "domain_evidence": self.domain_root,
                },
                "qualification_bindings": qualifications,
                "runtime_activation_allowed": False,
                "live_body_replacement_allowed": False,
                "public_export_allowed": False,
                "queue_creation_allowed_by_evaluator": False,
            },
        )

    def make_qualification(
        self,
        candidate_id: str,
        subject_id: str,
        *,
        skin_gate: bool = True,
        body_payload: str = "",
    ) -> dict[str, str]:
        build_id = f"{candidate_id}_build"
        component_bindings: dict[str, dict[str, str]] = {}
        component_hashes: dict[str, str] = {}
        for component in COMPONENTS:
            path = self.root / f"artifacts/{candidate_id}/{component}.bin"
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = body_payload if component == "body" and body_payload else f"{candidate_id}-{component}"
            path.write_bytes(payload.encode())
            component_hashes[component] = digest(path)
            component_bindings[component] = {
                "path": relative(self.root, path),
                "sha256": component_hashes[component],
            }

        evidence_bindings: dict[str, dict[str, str]] = {}
        domain_hashes: dict[str, str] = {}
        for domain in DOMAINS:
            raw = self.root / f"evidence/raw/{candidate_id}/{domain}.dat"
            raw.parent.mkdir(parents=True, exist_ok=True)
            raw.write_bytes(f"observed-{candidate_id}-{domain}".encode())
            domain_payload = {
                "schema_version": 1,
                "artifact_type": "avatar_body_domain_proof",
                "domain": domain,
                "candidate_id": candidate_id,
                "subject_id": subject_id,
                "build_id": build_id,
                "decision": "pass",
                "exact_build_observed": True,
                "review_complete": True,
                "component_sha256": component_hashes,
                "retained_evidence": [
                    {"path": relative(self.root, raw), "sha256": digest(raw)}
                ],
                "runtime_activation_allowed": False,
                "public_export_allowed": False,
            }
            domain_path, domain_sha = content_addressed_json(
                self.root, self.domain_root, domain_payload
            )
            domain_hashes[domain] = domain_sha
            evidence_bindings[domain] = {
                "path": relative(self.root, domain_path),
                "sha256": domain_sha,
            }

        review = {
            "schema_version": 2,
            "artifact_type": "immutable_owner_body_review",
            "owner_authority_id": "real_robert",
            "decision": "approve_body_for_two_subject_autobuild_qualification",
            "candidate_id": candidate_id,
            "subject_id": subject_id,
            "build_id": build_id,
            **{flag: True for flag in OWNER_FLAGS},
            "release_downstream_autobuild": False,
            "release_downstream_autobuild_by_itself": False,
            "component_sha256": component_hashes,
            "domain_evidence_sha256": domain_hashes,
            "runtime_activation_allowed": False,
            "public_export_allowed": False,
        }
        review_path, review_sha = content_addressed_json(self.root, self.review_root, review)
        gates = {gate: True for gate in ALL_GATES}
        gates["skin_material_and_deformation_integrity"] = skin_gate
        proof = {
            "schema_version": 1,
            "status": "owner_approved_positive_proof",
            "candidate_id": candidate_id,
            "subject_id": subject_id,
            "build_id": build_id,
            "candidate_identity_registry_sha256": digest(self.registry_path),
            "components": component_bindings,
            "gates": gates,
            "evidence": evidence_bindings,
            "owner_approval": {
                "path": relative(self.root, review_path),
                "sha256": review_sha,
            },
            "runtime_activation_allowed": False,
            "public_export_allowed": False,
        }
        proof_path, proof_sha = content_addressed_json(self.root, self.proof_root, proof)
        return {"path": relative(self.root, proof_path), "sha256": proof_sha}


class AvatarTwoSubjectAutobuildGateTests(unittest.TestCase):
    def test_current_project_stays_locked_and_creates_nothing(self) -> None:
        result = evaluate_two_subject_autobuild_gate(PROJECT_ROOT)
        self.assertFalse(result["batch_auto_authoring_allowed"])
        self.assertEqual(result["qualified_body_count"], 0)
        self.assertEqual(result["distinct_canonical_subject_count"], 0)
        self.assertFalse(result["queue_created"])
        self.assertFalse(result["body_created"])
        self.assertFalse(result["runtime_activation_allowed"])

    def test_one_perfect_body_is_only_a_subject_qualification(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            fixture = TwoSubjectFixture(Path(temp))
            first = fixture.make_qualification("candidate_a", "subject_a")
            fixture.write_v2_policy([first])
            legacy = evaluate_positive_proof(fixture.root, fixture.root / first["path"])
            self.assertTrue(legacy["subject_qualification_ready"])
            self.assertFalse(legacy["release_allowed"])
            with self.assertRaisesRegex(ValueError, "one-subject positive proof"):
                build_downstream_release_plan(fixture.root, legacy)
            result = evaluate_two_subject_autobuild_gate(fixture.root)
            self.assertFalse(result["batch_auto_authoring_allowed"])
            self.assertEqual(result["qualified_body_count"], 1)
            self.assertIn("insufficient_distinct_qualified_subjects:1/2", result["failures"])

    def test_two_variants_of_one_person_count_as_one_subject(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            fixture = TwoSubjectFixture(Path(temp))
            first = fixture.make_qualification("candidate_a", "subject_a")
            variant = fixture.make_qualification("candidate_a_variant", "subject_a")
            fixture.write_v2_policy([first, variant])
            result = evaluate_two_subject_autobuild_gate(fixture.root)
            self.assertFalse(result["batch_auto_authoring_allowed"])
            self.assertEqual(result["qualified_body_count"], 2)
            self.assertEqual(result["distinct_canonical_subject_count"], 1)

    def test_two_distinct_complete_subjects_enable_dry_run_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            fixture = TwoSubjectFixture(Path(temp))
            first = fixture.make_qualification("candidate_a", "subject_a")
            second = fixture.make_qualification("candidate_b", "subject_b")
            fixture.write_v2_policy([first, second])
            result = evaluate_two_subject_autobuild_gate(fixture.root)
            self.assertTrue(result["batch_auto_authoring_allowed"])
            self.assertEqual(result["distinct_canonical_subject_count"], 2)
            self.assertFalse(result["queue_created"])
            plan = build_two_subject_autobuild_dry_run_plan(fixture.root, result)
            self.assertEqual(plan["candidate_order"], ["candidate_next"])
            self.assertEqual(plan["maximum_concurrent_body_builds"], 1)
            self.assertFalse(plan["queue_created"])
            self.assertFalse(plan["runtime_activation_allowed"])
            self.assertFalse(plan["live_body_replacement_allowed"])

    def test_two_subject_names_cannot_reuse_one_body_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            fixture = TwoSubjectFixture(Path(temp))
            first = fixture.make_qualification(
                "candidate_a", "subject_a", body_payload="same-body-bytes"
            )
            second = fixture.make_qualification(
                "candidate_b", "subject_b", body_payload="same-body-bytes"
            )
            fixture.write_v2_policy([first, second])
            result = evaluate_two_subject_autobuild_gate(fixture.root)
            self.assertFalse(result["batch_auto_authoring_allowed"])
            self.assertIn("qualified_subjects_share_same_body_artifact", result["failures"])

    def test_missing_skin_gate_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            fixture = TwoSubjectFixture(Path(temp))
            first = fixture.make_qualification("candidate_a", "subject_a", skin_gate=False)
            second = fixture.make_qualification("candidate_b", "subject_b")
            fixture.write_v2_policy([first, second])
            result = evaluate_two_subject_autobuild_gate(fixture.root)
            self.assertFalse(result["batch_auto_authoring_allowed"])
            self.assertTrue(
                any("skin_material_and_deformation_integrity" in item for item in result["failures"])
            )

    def test_policy_cannot_remove_skin_or_visual_domains(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            fixture = TwoSubjectFixture(Path(temp))
            first = fixture.make_qualification("candidate_a", "subject_a")
            second = fixture.make_qualification("candidate_b", "subject_b")
            fixture.write_v2_policy([first, second])
            policy = json.loads(fixture.v2_policy_path.read_text(encoding="utf-8"))
            policy["required_evidence_domains"] = ["topology", "rig_and_deformation"]
            policy["required_legacy_gates_by_domain"] = {
                "topology": ["topology_lane_correct"],
                "rig_and_deformation": ["stable_rig"],
            }
            write_json(fixture.v2_policy_path, policy)
            result = evaluate_two_subject_autobuild_gate(fixture.root)
            self.assertFalse(result["batch_auto_authoring_allowed"])
            self.assertIn(
                "required_evidence_domains_do_not_match_code_authority",
                result["failures"],
            )

    def test_tampered_domain_evidence_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            fixture = TwoSubjectFixture(Path(temp))
            first = fixture.make_qualification("candidate_a", "subject_a")
            second = fixture.make_qualification("candidate_b", "subject_b")
            fixture.write_v2_policy([first, second])
            proof = json.loads((fixture.root / first["path"]).read_text(encoding="utf-8"))
            evidence_path = fixture.root / proof["evidence"]["ground_contact"]["path"]
            evidence_path.write_text("{}\n", encoding="utf-8")
            result = evaluate_two_subject_autobuild_gate(fixture.root)
            self.assertFalse(result["batch_auto_authoring_allowed"])
            self.assertTrue(any("ground_contact_sha256_mismatch" in x for x in result["failures"]))

    def test_owner_review_must_be_content_addressed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            fixture = TwoSubjectFixture(Path(temp))
            first = fixture.make_qualification("candidate_a", "subject_a")
            second = fixture.make_qualification("candidate_b", "subject_b")
            proof_path = fixture.root / first["path"]
            proof = json.loads(proof_path.read_text(encoding="utf-8"))
            review_path = fixture.root / proof["owner_approval"]["path"]
            renamed = review_path.with_name("owner_review_not_content_addressed.json")
            review_path.replace(renamed)
            proof["owner_approval"] = {
                "path": relative(fixture.root, renamed),
                "sha256": digest(renamed),
            }
            proof_path.unlink()
            new_proof_path, new_proof_sha = content_addressed_json(
                fixture.root, fixture.proof_root, proof
            )
            first = {"path": relative(fixture.root, new_proof_path), "sha256": new_proof_sha}
            fixture.write_v2_policy([first, second])
            result = evaluate_two_subject_autobuild_gate(fixture.root)
            self.assertFalse(result["batch_auto_authoring_allowed"])
            self.assertTrue(any("owner_review_not_content_addressed" in x for x in result["failures"]))

    def test_legacy_cli_never_returns_batch_release_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            fixture = TwoSubjectFixture(Path(temp))
            first = fixture.make_qualification("candidate_a", "subject_a")
            output = io.StringIO()
            with (
                mock.patch.object(legacy_cli, "PROJECT_ROOT", fixture.root),
                mock.patch.object(sys, "argv", ["legacy", "--proof", first["path"]]),
                contextlib.redirect_stdout(output),
            ):
                exit_code = legacy_cli.main()
            payload = json.loads(output.getvalue())
            self.assertEqual(exit_code, 3)
            self.assertTrue(payload["subject_qualification_ready"])
            self.assertFalse(payload["release_allowed"])
            self.assertEqual(
                payload["batch_gate_required"],
                "avatar_two_distinct_subject_autobuild_gate_v2",
            )


if __name__ == "__main__":
    unittest.main()
