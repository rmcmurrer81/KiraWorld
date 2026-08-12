from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import Core.embodiment_evidence as embodiment_evidence_module
from Core.embodiment_evidence import (
    CAPABILITIES,
    embodiment_binding_sha256,
    evaluate_capability,
    evaluate_capability_series,
    redact_private_snapshot,
    transition_trace_sha256,
)
from tools.run_kira_embodiment_staged_tests_20260715 import evaluate_snapshot_for_report


def grounded_held(kind: str) -> dict:
    return {
        "kind": kind,
        "grounded": True,
        "syntheticPreview": False,
        "sourcePropId": f"world_{kind}_001",
        "sourceRemovedOrHidden": True,
        "handContact": {"touching": True, "distance": 0.08, "node": "hand.R"},
    }


def build_approval_fixture(root: Path) -> tuple[dict, Path, str, dict]:
    body_relative = "artifacts/kira_body.glb"
    rig_relative = "artifacts/kira_rig.json"
    approval_relative = "approvals/kira_body_approval.json"
    registry_relative = "policies/body_registry.json"
    body_path = root / body_relative
    rig_path = root / rig_relative
    approval_path = root / approval_relative
    registry_path = root / registry_relative
    for path in (body_path, rig_path, approval_path, registry_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    body_path.write_bytes(b"test-only-skinned-body-bytes")
    rig_path.write_bytes(b'{"rig":"test-only-kira-rig-v1"}\n')
    body_sha = hashlib.sha256(body_path.read_bytes()).hexdigest()
    rig_sha = hashlib.sha256(rig_path.read_bytes()).hexdigest()
    approval = {
        "schemaVersion": 1,
        "approvalType": "embodiment_body_runtime_approval",
        "approvalId": "test_only_kira_body_approval",
        "status": "approved",
        "reviewerId": "robert_mcmurrer",
        "approvedAt": "2026-07-15T00:00:00Z",
        "actorId": "kira",
        "subjectId": "kira",
        "maturityClass": "adult",
        "bodyAssetPath": body_relative,
        "bodyAssetSha256": body_sha,
        "rigArtifactPath": rig_relative,
        "rigSha256": rig_sha,
    }
    approval_path.write_text(json.dumps(approval, indent=2) + "\n", encoding="utf-8")
    approval_sha = hashlib.sha256(approval_path.read_bytes()).hexdigest()
    entry = {
        "status": "approved",
        "ownerApproved": True,
        "reviewerId": "robert_mcmurrer",
        "approvalId": approval["approvalId"],
        "approvedAt": approval["approvedAt"],
        "approvalArtifactPath": approval_relative,
        "approvalArtifactSha256": approval_sha,
        "actorId": "kira",
        "subjectId": "kira",
        "maturityClass": "adult",
        "bodyAssetPath": body_relative,
        "bodyAssetSha256": body_sha,
        "rigArtifactPath": rig_relative,
        "rigSha256": rig_sha,
    }
    registry = {
        "schemaVersion": 1,
        "registryType": "owner_controlled_embodiment_body_runtime_approval_registry",
        "ownerId": "robert_mcmurrer",
        "status": "active_fail_closed",
        "entries": [entry],
        "policy": {
            "default": "deny",
            "callerSuppliedHashesAreAuthority": False,
            "requireConcreteArtifactBytes": True,
            "requireExactApprovalArtifactSha256": True,
            "requireExactBodyRigIdentityMaturityBindings": True,
            "currentApprovedBodies": 1,
        },
    }
    registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
    registry_sha = hashlib.sha256(registry_path.read_bytes()).hexdigest()
    body_evidence = {
        "actorId": "kira",
        "subjectId": "kira",
        "maturityClass": "adult",
        "bodyAssetPath": body_relative,
        "bodyAssetSha256": body_sha,
        "rigArtifactPath": rig_relative,
        "rigSha256": rig_sha,
        "approvalArtifactPath": approval_relative,
        "approvalArtifactSha256": approval_sha,
        "approved": True,
    }
    return body_evidence, registry_path, registry_sha, registry


def base_snapshot(body_evidence: dict, action: str = "idle") -> dict:
    transition = {
        "actorId": "kira",
        "observerId": "runtime_scene_observer",
        "captureBasis": "scene_observer_trace",
        "mode": "walk",
        "teleported": False,
        "distanceMeters": 2.4,
        "pathSampleCount": 3,
        "collisionBlocked": False,
        "startedAt": 10.0,
        "endedAt": 12.0,
        "startPosition": {"x": 0.0, "y": 0.0, "z": 0.0},
        "endPosition": {"x": 2.4, "y": 0.0, "z": 0.0},
        "path": [
            {"x": 0.0, "y": 0.0, "z": 0.0, "t": 10.0},
            {"x": 1.2, "y": 0.0, "z": 0.0, "t": 11.0},
            {"x": 2.4, "y": 0.0, "z": 0.0, "t": 12.0},
        ],
    }
    transition["traceSha256"] = transition_trace_sha256(transition)
    binding = {
        "actorId": "kira",
        "observerId": "runtime_scene_observer",
        "transitionTraceSha256": transition["traceSha256"],
        "subjectId": body_evidence["subjectId"],
        "maturityClass": body_evidence["maturityClass"],
        "bodyAssetPath": body_evidence["bodyAssetPath"],
        "bodyAssetSha256": body_evidence["bodyAssetSha256"],
        "rigArtifactPath": body_evidence["rigArtifactPath"],
        "rigSha256": body_evidence["rigSha256"],
        "approvalArtifactPath": body_evidence["approvalArtifactPath"],
        "approvalArtifactSha256": body_evidence["approvalArtifactSha256"],
    }
    binding["bindingSha256"] = embodiment_binding_sha256(binding)
    return {
        "activeModelLoaded": True,
        "action": action,
        "bodyEvidence": deepcopy(body_evidence),
        "transitionEvidence": transition,
        "evidenceBinding": binding,
        "activityTruthByAction": {
            "use_phone": {"grounded": True},
            "read_book": {"grounded": True},
            "drink": {"grounded": True},
            "drink_coffee": {"grounded": True},
            "eat_food": {"grounded": True},
        },
    }


def rebind_transition(snapshot: dict) -> None:
    transition = snapshot["transitionEvidence"]
    transition["traceSha256"] = transition_trace_sha256(transition)
    snapshot["evidenceBinding"]["transitionTraceSha256"] = transition["traceSha256"]
    snapshot["evidenceBinding"]["bindingSha256"] = embodiment_binding_sha256(
        snapshot["evidenceBinding"]
    )


class EmbodimentEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.project_root = Path(self._temp.name)
        (
            self.body_evidence,
            self.registry_path,
            self.registry_sha,
            self.registry_payload,
        ) = build_approval_fixture(self.project_root)
        self._patchers = [
            patch.object(
                embodiment_evidence_module,
                "EMBODIMENT_PROJECT_ROOT",
                self.project_root,
            ),
            patch.object(
                embodiment_evidence_module,
                "EMBODIMENT_APPROVAL_REGISTRY_PATH",
                self.registry_path,
            ),
            patch.object(
                embodiment_evidence_module,
                "EMBODIMENT_APPROVAL_REGISTRY_PINNED_SHA256",
                self.registry_sha,
            ),
        ]
        for patcher in self._patchers:
            patcher.start()

    def tearDown(self) -> None:
        for patcher in reversed(self._patchers):
            patcher.stop()
        self._temp.cleanup()

    def snapshot(self, action: str = "idle") -> dict:
        return base_snapshot(self.body_evidence, action)

    def rewrite_registry(self, entries: list[dict]) -> str:
        payload = deepcopy(self.registry_payload)
        payload["entries"] = entries
        payload["policy"]["currentApprovedBodies"] = len(entries)
        self.registry_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return hashlib.sha256(self.registry_path.read_bytes()).hexdigest()

    def test_synthetic_prop_cannot_pass_tablet_pickup(self) -> None:
        snapshot = self.snapshot("pick_up_tablet")
        snapshot["activeHeldProp"] = {
            "kind": "tablet",
            "grounded": False,
            "syntheticPreview": True,
        }
        result = evaluate_capability("tablet_pickup", snapshot)
        self.assertEqual(result["status"], "blocked")
        self.assertTrue(any("generated preview" in reason for reason in result["reasons"]))
        self.assertTrue(any("hand/finger" in reason for reason in result["reasons"]))

    def test_direct_position_copy_blocks_posture_claim(self) -> None:
        snapshot = self.snapshot("sit")
        snapshot["postureState"] = {"posture": "sit", "surface": "one_bedroom_couch"}
        snapshot["supportState"] = {"id": "one_bedroom_couch", "supported": True, "falling": False}
        snapshot["transitionEvidence"] = {"mode": "direct_position_copy", "teleported": True}
        result = evaluate_capability("sit_couch", snapshot)
        self.assertEqual(result["status"], "blocked")
        self.assertTrue(any("teleport" in reason for reason in result["reasons"]))

    def test_zero_meter_two_sample_walk_is_not_movement_evidence(self) -> None:
        snapshot = self.snapshot("pick_up_tablet")
        snapshot["activeHeldProp"] = grounded_held("tablet")
        transition = snapshot["transitionEvidence"]
        transition.update({
            "mode": "walk",
            "distanceMeters": 0.0,
            "pathSampleCount": 2,
            "startedAt": 20.0,
            "endedAt": 21.0,
            "startPosition": {"x": 1.0, "y": 0.0, "z": 1.0},
            "endPosition": {"x": 1.0, "y": 0.0, "z": 1.0},
            "path": [
                {"x": 1.0, "y": 0.0, "z": 1.0, "t": 20.0},
                {"x": 1.0, "y": 0.0, "z": 1.0, "t": 21.0},
            ],
        })
        rebind_transition(snapshot)

        result = evaluate_capability("tablet_pickup", snapshot)

        self.assertFalse(result["passed"])
        self.assertTrue(any("meaningful nonzero" in reason for reason in result["reasons"]))

    def test_small_but_measured_reach_path_can_pass(self) -> None:
        snapshot = self.snapshot("pick_up_tablet")
        snapshot["activeHeldProp"] = grounded_held("tablet")
        transition = snapshot["transitionEvidence"]
        transition.update({
            "mode": "reach",
            "distanceMeters": 0.01,
            "pathSampleCount": 2,
            "startedAt": 20.0,
            "endedAt": 20.5,
            "startPosition": {"x": 1.0, "y": 1.0, "z": 1.0},
            "endPosition": {"x": 1.01, "y": 1.0, "z": 1.0},
            "path": [
                {"x": 1.0, "y": 1.0, "z": 1.0, "t": 20.0},
                {"x": 1.01, "y": 1.0, "z": 1.0, "t": 20.5},
            ],
        })
        rebind_transition(snapshot)

        self.assertTrue(evaluate_capability("tablet_pickup", snapshot)["passed"])

    def test_syntactic_hashes_without_concrete_artifact_paths_are_denied(self) -> None:
        snapshot = self.snapshot("pick_up_tablet")
        snapshot["activeHeldProp"] = grounded_held("tablet")
        snapshot["bodyEvidence"] = {
            "actorId": "kira",
            "subjectId": "kira",
            "maturityClass": "adult",
            "bodyAssetSha256": "a" * 64,
            "rigSha256": "b" * 64,
            "approvalArtifactSha256": "c" * 64,
            "approved": True,
        }

        result = evaluate_capability("tablet_pickup", snapshot)

        self.assertFalse(result["passed"])
        self.assertTrue(any("path is missing" in reason for reason in result["reasons"]))

    def test_absolute_or_out_of_root_artifact_path_is_denied(self) -> None:
        snapshot = self.snapshot("pick_up_tablet")
        snapshot["activeHeldProp"] = grounded_held("tablet")
        absolute_body = str((self.project_root / self.body_evidence["bodyAssetPath"]).resolve())
        snapshot["bodyEvidence"]["bodyAssetPath"] = absolute_body

        result = evaluate_capability("tablet_pickup", snapshot)

        self.assertFalse(result["passed"])
        self.assertTrue(any("project-relative" in reason for reason in result["reasons"]))

    def test_tampered_body_or_rig_bytes_are_denied(self) -> None:
        for relative, expected_reason in (
            (self.body_evidence["bodyAssetPath"], "body asset SHA-256"),
            (self.body_evidence["rigArtifactPath"], "rig SHA-256"),
        ):
            with self.subTest(relative=relative):
                snapshot = self.snapshot("pick_up_tablet")
                snapshot["activeHeldProp"] = grounded_held("tablet")
                path = self.project_root / relative
                original = path.read_bytes()
                path.write_bytes(original + b"tampered")
                try:
                    result = evaluate_capability("tablet_pickup", snapshot)
                finally:
                    path.write_bytes(original)
                self.assertFalse(result["passed"])
                self.assertTrue(any(expected_reason in reason for reason in result["reasons"]))

    def test_tampered_or_missing_owner_registry_is_denied(self) -> None:
        snapshot = self.snapshot("pick_up_tablet")
        snapshot["activeHeldProp"] = grounded_held("tablet")
        self.registry_path.write_bytes(self.registry_path.read_bytes() + b" \n")
        tampered = evaluate_capability("tablet_pickup", snapshot)
        self.assertFalse(tampered["passed"])
        self.assertTrue(any("code-pinned hash" in reason for reason in tampered["reasons"]))

        with patch.object(
            embodiment_evidence_module,
            "EMBODIMENT_APPROVAL_REGISTRY_PATH",
            self.project_root / "policies" / "missing.json",
        ):
            missing = evaluate_capability("tablet_pickup", snapshot)
        self.assertFalse(missing["passed"])
        self.assertTrue(any("registry is missing" in reason for reason in missing["reasons"]))

    def test_valid_empty_registry_still_denies_unlisted_approval(self) -> None:
        snapshot = self.snapshot("pick_up_tablet")
        snapshot["activeHeldProp"] = grounded_held("tablet")
        empty_registry_sha = self.rewrite_registry([])
        with patch.object(
            embodiment_evidence_module,
            "EMBODIMENT_APPROVAL_REGISTRY_PINNED_SHA256",
            empty_registry_sha,
        ):
            result = evaluate_capability("tablet_pickup", snapshot)

        self.assertFalse(result["passed"])
        self.assertTrue(any("not listed" in reason for reason in result["reasons"]))

    def test_hash_pinned_but_schema_empty_registry_is_invalid(self) -> None:
        self.registry_path.write_text("{}\n", encoding="utf-8")
        empty_object_sha = hashlib.sha256(self.registry_path.read_bytes()).hexdigest()
        with patch.object(
            embodiment_evidence_module,
            "EMBODIMENT_APPROVAL_REGISTRY_PINNED_SHA256",
            empty_object_sha,
        ):
            registry = embodiment_evidence_module.load_embodiment_approval_registry()

        self.assertFalse(registry["valid"])
        self.assertEqual(registry["entries"], [])
        self.assertTrue(any("schema version" in reason for reason in registry["failures"]))

    def test_approval_status_and_identity_maturity_bindings_are_exact(self) -> None:
        approval_path = self.project_root / self.body_evidence["approvalArtifactPath"]
        original = json.loads(approval_path.read_text(encoding="utf-8"))
        cases = (
            ("status", "draft", "status"),
            ("reviewerId", "caller", "reviewerId"),
            ("actorId", "other_actor", "actorId"),
            ("subjectId", "other_subject", "subjectId"),
            ("maturityClass", "unknown", "maturityClass"),
            ("bodyAssetSha256", "0" * 64, "bodyAssetSha256"),
            ("rigSha256", "1" * 64, "rigSha256"),
        )
        for key, forged_value, expected_reason in cases:
            with self.subTest(key=key):
                forged = deepcopy(original)
                forged[key] = forged_value
                approval_path.write_text(json.dumps(forged, indent=2) + "\n", encoding="utf-8")
                snapshot = self.snapshot("pick_up_tablet")
                snapshot["activeHeldProp"] = grounded_held("tablet")
                new_sha = hashlib.sha256(approval_path.read_bytes()).hexdigest()
                snapshot["bodyEvidence"]["approvalArtifactSha256"] = new_sha
                snapshot["evidenceBinding"]["approvalArtifactSha256"] = new_sha
                snapshot["evidenceBinding"]["bindingSha256"] = embodiment_binding_sha256(
                    snapshot["evidenceBinding"]
                )
                result = evaluate_capability("tablet_pickup", snapshot)
                self.assertFalse(result["passed"])
                self.assertTrue(any(expected_reason in reason for reason in result["reasons"]))
        approval_path.write_text(json.dumps(original, indent=2) + "\n", encoding="utf-8")

    def test_missing_transition_blocks_self_asserted_posture_and_restroom(self) -> None:
        couch = {
            "bodyPresent": True,
            "postureState": {"posture": "sit", "surface": "couch"},
            "supportState": {"id": "couch", "supported": True, "falling": False},
        }
        self.assertFalse(evaluate_capability("sit_couch", couch)["passed"])

        restroom = {
            "bodyPresent": True,
            "action": "use_bathroom",
            "place": {"label": "bathroom", "inside": True},
            "fixtureEvidence": {"kind": "toilet", "distanceMeters": 0.4},
            "privacyState": {"active": True, "observersAllowed": False, "logScope": "none"},
            "anatomyAnimationSupported": True,
        }
        result = evaluate_capability("restroom_private_use", restroom)
        self.assertFalse(result["passed"])
        self.assertTrue(any("transition evidence is missing" in reason for reason in result["reasons"]))

    def test_negative_contact_distance_is_never_touching(self) -> None:
        pickup = self.snapshot("pick_up_tablet")
        pickup["activeHeldProp"] = grounded_held("tablet")
        pickup["activeHeldProp"]["handContact"]["distance"] = -999
        result = evaluate_capability("tablet_pickup", pickup)
        self.assertFalse(result["passed"])
        self.assertTrue(any("hand/finger" in reason for reason in result["reasons"]))

    def test_grounded_couch_and_bed_postures_can_pass(self) -> None:
        sit = self.snapshot("sit")
        sit["postureState"] = {"posture": "sit", "surface": "one_bedroom_couch"}
        sit["supportState"] = {"id": "one_bedroom_couch", "supported": True, "falling": False}
        self.assertTrue(evaluate_capability("sit_couch", sit)["passed"])

        lie = self.snapshot("lie_down")
        lie["postureState"] = {"posture": "lie", "surface": "one_bedroom_bed"}
        lie["supportState"] = {"id": "one_bedroom_bed", "supported": True, "falling": False}
        self.assertTrue(evaluate_capability("lie_bed", lie)["passed"])

    def test_restroom_requires_private_metadata_only_boundary(self) -> None:
        snapshot = self.snapshot("use_bathroom")
        snapshot.update({
            "place": {"label": "Kira one-bedroom bathroom", "inside": True},
            "fixtureEvidence": {"kind": "toilet", "distanceMeters": 0.55},
            "privacyState": {"active": True, "observersAllowed": False, "logScope": "metadata_only"},
            "anatomyAnimationSupported": True,
        })
        self.assertTrue(evaluate_capability("restroom_private_use", snapshot)["passed"])
        snapshot["privacyState"]["observersAllowed"] = True
        result = evaluate_capability("restroom_private_use", snapshot)
        self.assertFalse(result["passed"])
        self.assertTrue(any("observers" in reason for reason in result["reasons"]))

    def test_restroom_without_approved_anatomy_animation_is_blocked(self) -> None:
        snapshot = self.snapshot("use_bathroom")
        snapshot.update({
            "place": {"label": "bathroom", "inside": True},
            "fixtureEvidence": {"kind": "toilet", "distanceMeters": 0.4},
            "privacyState": {"active": True, "observersAllowed": False, "logScope": "none"},
            "anatomyAnimationSupported": False,
        })
        result = evaluate_capability("restroom_private_use", snapshot)
        self.assertFalse(result["passed"])
        self.assertTrue(any("anatomy/animation" in reason for reason in result["reasons"]))

    def test_private_redaction_drops_coordinates_and_content(self) -> None:
        redacted = redact_private_snapshot({
            "activeModelLoaded": True,
            "action": "use_bathroom",
            "place": {"label": "exact bathroom", "inside": True, "position": {"x": 1, "z": 2}},
            "privacyState": {"active": True, "observersAllowed": False, "logScope": "metadata_only"},
            "fixtureEvidence": {"kind": "toilet", "distanceMeters": 0.4},
            "privateContent": "must never be retained",
        })
        self.assertTrue(redacted["detailsRedacted"])
        self.assertEqual(redacted["place"], {"category": "private_room", "inside": True})
        self.assertNotIn("privateContent", redacted)
        self.assertNotIn("position", redacted["place"])

    def test_restroom_is_evaluated_before_private_evidence_is_redacted(self) -> None:
        snapshot = self.snapshot("use_bathroom")
        snapshot.update({
            "place": {
                "label": "Kira one-bedroom bathroom",
                "inside": True,
                "position": {"x": -29.1, "z": -1.2},
            },
            "fixtureEvidence": {"kind": "toilet", "distanceMeters": 0.45},
            "privacyState": {
                "active": True,
                "observersAllowed": False,
                "logScope": "metadata_only",
            },
            "anatomyAnimationSupported": True,
            "privateContent": "must not be persisted",
        })

        result, saved = evaluate_snapshot_for_report("restroom_private_use", snapshot)

        self.assertTrue(result["passed"])
        self.assertTrue(saved["detailsRedacted"])
        self.assertEqual(saved["place"], {"category": "private_room", "inside": True})
        self.assertEqual(saved["fixtureEvidence"]["distanceBand"], "within_interaction_zone")
        self.assertNotIn("privateContent", saved)
        self.assertNotIn("distanceMeters", saved["fixtureEvidence"])

    def test_eating_and_drinking_require_contact_and_anatomy(self) -> None:
        eat = self.snapshot("eat_snack")
        eat["activeHeldProp"] = grounded_held("food")
        eat["consumptionEvidence"] = {"mouthContact": True}
        eat["anatomyAnimationSupported"] = True
        self.assertTrue(evaluate_capability("eat_food", eat)["passed"])

        drink = self.snapshot("drink_water")
        drink["activeHeldProp"] = grounded_held("cup")
        drink["consumptionEvidence"] = {"mouthContact": False}
        drink["anatomyAnimationSupported"] = True
        result = evaluate_capability("drink", drink)
        self.assertFalse(result["passed"])
        self.assertTrue(any("mouth" in reason for reason in result["reasons"]))

    def test_tablet_pickup_and_putdown_need_same_object_continuity(self) -> None:
        pickup = self.snapshot("pick_up_tablet")
        pickup["activeHeldProp"] = grounded_held("tablet")
        self.assertTrue(evaluate_capability("tablet_pickup", pickup)["passed"])

        putdown = self.snapshot("put_down_tablet")
        putdown["activeHeldProp"] = None
        putdown["putdownEvidence"] = {
            "kind": "tablet",
            "sourcePropId": "world_tablet_001",
            "surface": "one_bedroom_coffee_table",
            "objectVisibleAtSurface": True,
            "handContact": {"touching": True, "distance": 0.09},
        }
        self.assertTrue(evaluate_capability("tablet_putdown", putdown)["passed"])
        del putdown["putdownEvidence"]["sourcePropId"]
        self.assertFalse(evaluate_capability("tablet_putdown", putdown)["passed"])

    def test_tablet_content_actions_require_real_artifacts(self) -> None:
        read = self.snapshot("read_ebook")
        read["activeHeldProp"] = grounded_held("tablet")
        read["contentEvidence"] = {
            "kind": "local_book",
            "sourcePath": "Data/library/novels/example.pdf",
            "page": 4,
        }
        self.assertTrue(evaluate_capability("tablet_read", read)["passed"])

        lookup = self.snapshot("research_online")
        lookup["activeHeldProp"] = grounded_held("tablet")
        lookup["contentEvidence"] = {
            "kind": "online_research",
            "sourcesChecked": ["https://example.invalid/reference"],
            "researchNoteId": "research_001",
        }
        self.assertTrue(evaluate_capability("tablet_online_lookup", lookup)["passed"])

        notes = self.snapshot("write_notes")
        notes["activeHeldProp"] = grounded_held("tablet")
        notes["contentEvidence"] = {
            "kind": "creative_writing",
            "noteId": "note_001",
            "saved": True,
        }
        self.assertTrue(evaluate_capability("tablet_note_writing", notes)["passed"])

    def test_empty_runtime_series_blocks_every_capability(self) -> None:
        report = evaluate_capability_series({})
        self.assertEqual(report["blocked_count"], len(CAPABILITIES))
        self.assertEqual(report["passed_count"], 0)


class ProductionEmbodimentRegistryTests(unittest.TestCase):
    def test_code_pinned_production_registry_is_valid_empty_default_deny(self) -> None:
        registry = embodiment_evidence_module.load_embodiment_approval_registry()

        self.assertTrue(registry["valid"])
        self.assertEqual(registry["default"], "deny")
        self.assertEqual(registry["entries"], [])
        self.assertEqual(registry["sha256"], registry["pinnedSha256"])


if __name__ == "__main__":
    unittest.main()
