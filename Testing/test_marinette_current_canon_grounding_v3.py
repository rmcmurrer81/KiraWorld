from __future__ import annotations

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Core import marinette_current_canon_contract_v3 as contract
from Core.avatar_asset_library import canonical_avatar_maturity_class
from tools import kira_world_shell_server as shell
from tools import temporary_ai_live_chat as live_chat


CANDIDATE_ID = "ladybug_marinette_expanded_smoke"
MANIFEST_PATH = ROOT / contract.MANIFEST_RELATIVE_PATH
V2_HASHES = {
    "Data/temporary_ai_source_packs/temporary_ai_source_pack_ladybug_marinette_current_canon_v2.json": "3501a75e66b153e9a0827bf4e891bbd2b6e1bc8602d7e1debb52f8ba264b9588",
    "TemporaryAI/candidates/ladybug_marinette_expanded_smoke/temporary_ai_profile.json": "051683c3bf01a54127ddf41ccb332d9e82614930f9699603985f7130865ec9ae",
    "TemporaryAI/candidates/ladybug_marinette_expanded_smoke/source_grounding_review.json": "cf19f6e6f4a8daea59fe3138eaff244c6f4864b9c8a528bd5c3c3995672c3157",
    "System/Docs/MARINETTE_CURRENT_CANON_GROUNDING_V2_REPAIR_CHECKPOINT_20260809.md": "05b5881d92ebb209559e1ae606e8442b73359b3e0496d4ebf803fa86aa25e31e",
    "System/Docs/MARINETTE_CURRENT_CANON_GROUNDING_V2_INDEPENDENT_HOSTILE_AUDIT_20260809.md": "85daf6cb24120ac809ba079f631a228ec66d3c0a1a086ee21d2c7d6125f833b2",
    "Testing/test_marinette_current_canon_grounding_v2.py": "c1a2718260d9a0ba58030dd035a81885202994c503646549643cc6fd11f116d8",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class MarinetteCurrentCanonGroundingV3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest, cls.artifacts = contract._load_contract()
        cls.candidate = live_chat.load_candidate(CANDIDATE_ID)

    def _semantic_rejection(self, mutate) -> str:
        manifest = copy.deepcopy(self.manifest)
        artifacts = copy.deepcopy(self.artifacts)
        mutate(manifest, artifacts)
        with self.assertRaises(contract.MarinetteCanonContractV3Error) as caught:
            contract._validate_semantics(manifest, artifacts)
        return str(caught.exception)

    def test_v2_source_review_checkpoint_audit_and_tests_are_byte_preserved(self) -> None:
        for relative_path, expected in V2_HASHES.items():
            self.assertEqual(sha256(ROOT / relative_path), expected, relative_path)

    def test_code_pinned_manifest_and_every_member_rehash_cleanly(self) -> None:
        self.assertEqual(sha256(MANIFEST_PATH), contract.PINNED_MANIFEST_SHA256)
        self.assertEqual(contract.manifest_sha256(), contract.PINNED_MANIFEST_SHA256)
        self.assertEqual(contract.static_contract_readiness(), (True, []))
        rows = []
        rows.extend(self.manifest["protected_v2_predecessors"])
        rows.extend(self.manifest["v3_contract_members"])
        rows.extend(self.manifest["local_no_claim_evidence"])
        rows.append(self.manifest["predecessor_rejection_audit"])
        for row in rows:
            self.assertEqual(sha256(ROOT / row["path"]), row["sha256"], row["path"])

    def test_exact_loader_snapshot_is_sanitized_and_owner_execution_stays_blocked(self) -> None:
        self.assertEqual(self.candidate["profile"]["profile_id"], "ladybug_marinette_current_canon_profile_v3")
        self.assertEqual(self.candidate["candidate_id"], CANDIDATE_ID)
        for field, empty in contract._EXCLUDED_TOP_LEVEL.items():
            self.assertEqual(self.candidate[field], empty, field)
        self.assertEqual(contract.static_contract_readiness(self.candidate), (True, []))
        self.assertEqual(
            live_chat.source_grounded_text_route_readiness(self.candidate),
            (False, ["fresh_independent_v3_audit_required"]),
        )

    def test_mutable_tf1_page_is_honest_no_claim_and_season6_03_is_absent(self) -> None:
        registry = self.artifacts["v3_source_registry"]
        source = next(
            row for row in registry["sources"]
            if row["source_id"] == "official_tf1_mutable_schedule_no_claim"
        )
        self.assertEqual(source["allowed_claim_ids"], [])
        self.assertEqual(source["claim_policy"], "no_canon_claim")
        evidence = next(
            row for row in self.artifacts["v3_official_content_evidence"]["records"]
            if row["source_id"] == source["source_id"]
        )
        self.assertEqual(evidence["verbatim_excerpt"], "")
        self.assertEqual(evidence["bounded_support"], [])
        claim_ids = {
            row["claim_id"] for row in self.artifacts["v3_runtime_policy"]["claims"]
        }
        self.assertNotIn("season6_03", claim_ids)

    def test_review_anchor_fabrication_or_scope_escalation_fails(self) -> None:
        reason = self._semantic_rejection(
            lambda _m, a: a["v3_source_review"]["canon_anchors"][0].update(
                {"statement": "A fabricated definitive Season 6 finale happened."}
            )
        )
        self.assertEqual(reason, "review_policy_claim_mismatch")

        reason = self._semantic_rejection(
            lambda _m, a: a["v3_source_review"]["activation"].update(
                {"bounded_owner_text_probe_allowed": True}
            )
        )
        self.assertEqual(reason, "review_probe_not_blocked")

    def test_registry_rank_host_and_content_relevance_are_not_self_labels(self) -> None:
        def fake_fan(_manifest, artifacts):
            source = artifacts["v3_source_registry"]["sources"][0]
            source["url"] = "https://fan.example.invalid/official-looking"
            source["source_rank"] = 1

        self.assertIn("registry_source_binding_mismatch", self._semantic_rejection(fake_fan))

        def sever_claim_mapping(_manifest, artifacts):
            artifacts["v3_source_registry"]["sources"][0]["allowed_claim_ids"] = []

        self.assertIn("registry_source_binding_mismatch", self._semantic_rejection(sever_claim_mapping))

        def remove_content_support(_manifest, artifacts):
            artifacts["v3_official_content_evidence"]["records"][0]["bounded_support"] = []

        self.assertIn("official_evidence_relevance_missing", self._semantic_rejection(remove_content_support))

    def test_exact_required_unknowns_cannot_be_removed_or_replaced(self) -> None:
        def replace_unknown(_manifest, artifacts):
            bogus = [{"unknown_id": "irrelevant_weather", "statement": "Weather is unknown."}]
            artifacts["v3_runtime_policy"]["required_unknowns"] = copy.deepcopy(bogus)
            artifacts["v3_source_pack"]["explicit_unknowns"] = copy.deepcopy(bogus)
            artifacts["v3_source_review"]["required_unknowns"] = copy.deepcopy(bogus)

        self.assertEqual(
            self._semantic_rejection(replace_unknown),
            "required_unknown_set_mismatch",
        )

    def test_profile_identity_maturity_and_declared_pack_hash_are_exact(self) -> None:
        mutations = (
            ("candidate_id", "gwen_stacy", "profile_candidate_id_mismatch"),
            ("display_name", "Gwen Stacy", "profile_display_name_mismatch"),
            ("role_title", "Unrelated adult", "profile_role_title_mismatch"),
            ("source_pack_sha256", "0" * 64, "profile_declared_binding_mismatch:source_pack"),
        )
        for key, value, expected in mutations:
            reason = self._semantic_rejection(
                lambda _m, a, key=key, value=value: a["v3_route_profile"].update({key: value})
            )
            self.assertEqual(reason, expected)

        def adult_drift(_manifest, artifacts):
            artifacts["v3_route_profile"]["maturity_policy"].update(
                {
                    "classification": "confirmed_adult",
                    "adult_anatomy_allowed": True,
                    "adult_curriculum_allowed": True,
                }
            )

        self.assertEqual(self._semantic_rejection(adult_drift), "profile_maturity_mismatch")

    def test_post_load_and_coordinated_context_mutations_fail_closed(self) -> None:
        attacks = []
        secondary = copy.deepcopy(self.candidate)
        secondary["reliable_source_pack"] = {
            "sources": [{"excerpt": "Fabricated finale from a secondary pack."}]
        }
        attacks.append((secondary, "reliable_source_pack"))
        old_chat = copy.deepcopy(self.candidate)
        old_chat["recent_chat_records"] = [{"candidate": "Invented aunt and finale."}]
        attacks.append((old_chat, "recent_chat_records"))
        project = copy.deepcopy(self.candidate)
        project["project_continuity"] = {"current_project": "Invented separate house."}
        attacks.append((project, "project_continuity"))
        fact_sheet = copy.deepcopy(self.candidate)
        fact_sheet["profile"]["canon_fact_sheet"] = {"facts": ["Invented history."]}
        attacks.append((fact_sheet, "profile"))
        coordinated = copy.deepcopy(self.candidate)
        coordinated["source_pack"]["source_bound_claims"][0]["statement"] = "Fabricated canon."
        coordinated["source_grounding_review"]["canon_anchors"][0]["statement"] = "Fabricated canon."
        attacks.append((coordinated, "source_pack"))

        with patch.object(contract, "_load_contract", return_value=(self.manifest, self.artifacts)):
            for candidate, changed_key in attacks:
                with self.assertRaisesRegex(
                    contract.MarinetteCanonContractV3Error,
                    "candidate_snapshot_mismatch:" + changed_key,
                ):
                    contract.validate_candidate_snapshot(candidate)

    def test_contract_prompt_contains_only_bound_facts_and_unknowns(self) -> None:
        with patch.object(contract, "_load_contract", return_value=(self.manifest, self.artifacts)):
            prompt = contract.build_contract_bound_system_prompt(
                self.candidate,
                "What happened in the Season 6 finale?",
            )
        self.assertIn("FACT anchors:", prompt)
        self.assertIn("[season6_01] Season 6 has 26 episodes", prompt)
        self.assertIn("[season6_finale] The released Season 6 finale", prompt)
        self.assertNotIn("invented aunt", prompt.lower())
        self.assertNotIn("separate house", prompt.lower())
        self.assertNotIn("wikipedia", prompt.lower())
        self.assertNotIn("current_project", prompt)

    def test_model_preflight_is_never_reached_while_fresh_audit_is_pending(self) -> None:
        with patch.object(live_chat, "require_installed_exact_qwen35") as model_preflight:
            with self.assertRaisesRegex(
                RuntimeError,
                "source_grounded_text_route_blocked:fresh_independent_v3_audit_required",
            ):
                live_chat.ask_model(self.candidate, [], "Invent a finale.")
        model_preflight.assert_not_called()

    def test_shell_blocks_owner_text_and_every_non_text_surface(self) -> None:
        policy = shell.candidate_surface_policy(CANDIDATE_ID)
        self.assertTrue(policy["bounded_text_only"])
        self.assertFalse(policy["voice_allowed"])
        self.assertFalse(policy["world_or_body_allowed"])
        with patch.object(shell, "TEXT_ONLY_CHAT_MODE", True):
            text_block = shell.candidate_activation_block(CANDIDATE_ID)
        self.assertEqual(text_block["reason"], "strict_v3_fresh_independent_audit_required")
        with patch.object(shell, "TEXT_ONLY_CHAT_MODE", False):
            world_block = shell.candidate_activation_block(CANDIDATE_ID)
        self.assertEqual(world_block["reason"], "strict_v3_text_only_world_denied")

    def test_strict_text_path_mints_no_sensory_initiative_event_or_movement_capability(self) -> None:
        state = {"active_candidate": CANDIDATE_ID, "last_activation_at": "v3-test"}
        with patch.object(shell.SENSORY_BUFFER, "activate") as sensory_activate, patch.object(
            shell, "issue_sensory_lease"
        ) as lease_issue:
            self.assertEqual(shell.browser_sensory_lease(state), "")
        sensory_activate.assert_not_called()
        lease_issue.assert_not_called()

        with patch.object(shell.PERSON_INITIATIVE_SESSION, "activate") as initiative_activate, patch.object(
            shell.PERSON_EVENT_QUEUE, "activate"
        ) as event_activate:
            with self.assertRaises(shell.InitiativeSessionBoundaryError):
                shell.activate_person_initiative_runtime(state)
        initiative_activate.assert_not_called()
        event_activate.assert_not_called()

        with patch.object(
            shell.SUPERVISED_PERSON_DECISION_ENGINE, "note_external_turn"
        ) as note_external:
            result = shell.note_supervised_person_external_turn(state, "owner-turn", accepted=True)
        self.assertFalse(result["registered"])
        note_external.assert_not_called()

        with patch.object(shell, "extract_candidate_owned_movement_intents") as parser, patch.object(
            shell, "record_candidate_owned_movement_intents"
        ) as recorder:
            split = shell.candidate_chat_movement_split(CANDIDATE_ID, "Hello. *waves*")
        self.assertEqual(split, {"spoken_text": "Hello. *waves*", "movement_intents": []})
        parser.assert_not_called()
        recorder.assert_not_called()

        status = shell.strict_text_review_runtime_status(CANDIDATE_ID)
        for key in (
            "sensory_lease_issued",
            "initiative_session_created",
            "public_event_transport_connected",
            "movement_intent_parse_or_persist_connected",
            "voice_started",
            "body_activated",
            "world_activated",
            "life_loop_started",
        ):
            self.assertFalse(status[key], key)

    def test_non_adult_doll_safe_private_inactive_identity_remains_locked(self) -> None:
        self.assertEqual(canonical_avatar_maturity_class(CANDIDATE_ID), "non_adult_doll_safe")
        profile = self.artifacts["v3_route_profile"]
        self.assertEqual(profile["maturity_policy"]["classification"], "non_adult_doll_safe")
        self.assertFalse(profile["maturity_policy"]["adult_anatomy_allowed"])
        self.assertFalse(profile["maturity_policy"]["adult_curriculum_allowed"])
        self.assertFalse(profile["maturity_policy"]["body_activation_authorized"])
        self.assertEqual(profile["status"], "inactive_pending_fresh_independent_v3_audit")


if __name__ == "__main__":
    unittest.main()
