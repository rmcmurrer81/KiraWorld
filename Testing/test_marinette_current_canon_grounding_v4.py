from __future__ import annotations

import copy
import contextlib
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Core import marinette_current_canon_contract_v4 as contract
from Core.avatar_asset_library import canonical_avatar_maturity_class
from tools import kira_world_shell_server as shell
from tools import temporary_ai_live_chat as live_chat


CANDIDATE_ID = "ladybug_marinette_expanded_smoke"
PRESERVED_HASHES = {
    # V1 draft and the complete V2 package/checkpoint/audit.
    "Data/temporary_ai_source_packs/temporary_ai_source_pack_ladybug_marinette_expanded_smoke.draft.json": "121c45fb18662f806c06d4a71b362e69ce3c8ceb931cd662fe8dc7c01813cbcd",
    "Data/temporary_ai_source_packs/temporary_ai_source_pack_ladybug_marinette_current_canon_v2.json": "3501a75e66b153e9a0827bf4e891bbd2b6e1bc8602d7e1debb52f8ba264b9588",
    "TemporaryAI/candidates/ladybug_marinette_expanded_smoke/temporary_ai_profile.json": "051683c3bf01a54127ddf41ccb332d9e82614930f9699603985f7130865ec9ae",
    "TemporaryAI/candidates/ladybug_marinette_expanded_smoke/source_grounding_review.json": "cf19f6e6f4a8daea59fe3138eaff244c6f4864b9c8a528bd5c3c3995672c3157",
    "Testing/test_marinette_current_canon_grounding_v2.py": "c1a2718260d9a0ba58030dd035a81885202994c503646549643cc6fd11f116d8",
    "System/Docs/MARINETTE_CURRENT_CANON_GROUNDING_V2_REPAIR_CHECKPOINT_20260809.md": "05b5881d92ebb209559e1ae606e8442b73359b3e0496d4ebf803fa86aa25e31e",
    "System/Docs/MARINETTE_CURRENT_CANON_GROUNDING_V2_INDEPENDENT_HOSTILE_AUDIT_20260809.md": "85daf6cb24120ac809ba079f631a228ec66d3c0a1a086ee21d2c7d6125f833b2",
    # Every versioned V3 member plus its test/checkpoint/rejection audit.
    **contract._EXPECTED_V3_HASHES,
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class MarinetteCurrentCanonGroundingV4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest, cls.artifacts = contract._load_contract()
        cls.candidate = live_chat.load_candidate(CANDIDATE_ID)

    def _semantic_rejection(self, mutate) -> str:
        manifest = copy.deepcopy(self.manifest)
        artifacts = copy.deepcopy(self.artifacts)
        mutate(manifest, artifacts)
        with self.assertRaises(contract.MarinetteCanonContractV4Error) as caught:
            contract._validate_semantics(manifest, artifacts)
        return str(caught.exception)

    def test_v1_v2_v3_packages_checkpoints_tests_and_audits_are_byte_preserved(self) -> None:
        for relative_path, expected in PRESERVED_HASHES.items():
            self.assertEqual(sha256(ROOT / relative_path), expected, relative_path)

    def test_pinned_manifest_and_every_exact_member_stable_open_cleanly(self) -> None:
        manifest_path = ROOT / contract.MANIFEST_RELATIVE_PATH
        self.assertEqual(sha256(manifest_path), contract.PINNED_MANIFEST_SHA256)
        self.assertEqual(contract.manifest_sha256(), contract.PINNED_MANIFEST_SHA256)
        self.assertEqual(contract.static_contract_readiness(), (True, []))
        rows = list(self.manifest["v4_contract_members"])
        rows += list(self.manifest["protected_v3_predecessors"])
        rows += list(self.manifest["local_no_claim_evidence"])
        rows.append(self.manifest["predecessor_rejection_audit"])
        for row in rows:
            self.assertEqual(sha256(ROOT / row["path"]), row["sha256"], row["path"])

    def test_loader_snapshot_is_v4_sanitized_and_execution_gate_is_closed(self) -> None:
        self.assertEqual(self.candidate["profile"]["profile_id"], "ladybug_marinette_current_canon_profile_v4")
        for field, empty in contract._EXCLUDED_TOP_LEVEL.items():
            self.assertEqual(self.candidate[field], empty, field)
        self.assertEqual(contract.static_contract_readiness(self.candidate), (True, []))
        self.assertEqual(
            live_chat.source_grounded_text_route_readiness(self.candidate),
            (False, ["different_agent_v4_audit_required"]),
        )
        diagnostic = contract.closed_gate_system_diagnostic(self.candidate)
        self.assertTrue(diagnostic["system_owned"])
        self.assertIsNone(diagnostic["person_reply"])
        self.assertFalse(diagnostic["writes_permitted"])

    def test_cli_closed_gate_returns_only_system_diagnostic_and_writes_nothing(self) -> None:
        output = io.StringIO()
        with patch.object(live_chat, "append") as append, patch.object(
            live_chat, "write_json"
        ) as write_json, patch.object(
            live_chat, "finalize_person_turn"
        ) as finalize_turn, patch.object(
            live_chat, "ask_model"
        ) as ask_model, patch.object(
            live_chat, "validate_and_repair_character_answer"
        ) as validate_answer, patch.object(
            live_chat, "finalize_model_artifacts"
        ) as finalize_artifacts, patch("builtins.input") as owner_input, contextlib.redirect_stdout(output):
            result = live_chat.run_chat(CANDIDATE_ID)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["person_reply"], "")
        self.assertIn("[System] Marinette owner text is unavailable", output.getvalue())
        self.assertNotIn("Marinette / Ladybug>", output.getvalue())
        append.assert_not_called()
        write_json.assert_not_called()
        finalize_turn.assert_not_called()
        ask_model.assert_not_called()
        validate_answer.assert_not_called()
        finalize_artifacts.assert_not_called()
        owner_input.assert_not_called()

    def test_shell_closed_gate_has_no_fallback_and_no_state_write(self) -> None:
        with patch.object(shell, "append_jsonl") as append_jsonl, patch.object(
            shell, "write_json"
        ) as write_json, patch.object(shell, "save_state") as save_state, patch.object(
            shell, "reply_for"
        ) as fallback, patch.object(shell, "ask_model") as ask_model:
            diagnostic = shell.marinette_v4_owner_text_gate(CANDIDATE_ID)
            with self.assertRaises(shell.MarinetteV4OwnerTextBlocked) as caught:
                shell.temporary_ai_reply(CANDIDATE_ID, "Marinette / Ladybug", "Hello", "")
        self.assertIsNone(diagnostic["person_reply"])
        self.assertTrue(caught.exception.diagnostic["system_owned"])
        append_jsonl.assert_not_called()
        write_json.assert_not_called()
        save_state.assert_not_called()
        fallback.assert_not_called()
        ask_model.assert_not_called()

    def test_direct_generic_reply_function_cannot_speak_as_marinette(self) -> None:
        with patch.object(shell, "append_jsonl") as append_jsonl, patch.object(
            shell, "write_json"
        ) as write_json, patch.object(shell, "save_state") as save_state:
            with self.assertRaises(shell.MarinetteV4OwnerTextBlocked) as caught:
                shell.reply_for(CANDIDATE_ID, "Marinette / Ladybug", "Hello", "Home World")
        self.assertIsNone(caught.exception.diagnostic["person_reply"])
        self.assertTrue(caught.exception.diagnostic["system_owned"])
        append_jsonl.assert_not_called()
        write_json.assert_not_called()
        save_state.assert_not_called()

    def test_shell_recovery_discovers_strict_candidate_without_repair_write(self) -> None:
        state = {
            "active_candidate": "",
            "last_active_candidate": CANDIDATE_ID,
            "last_activation_at": "2026-08-10T02:00:00+00:00",
            "last_deactivation_at": "2026-08-10T01:00:00+00:00",
        }
        before = copy.deepcopy(state)
        with patch.object(shell, "save_state") as save_state, patch.object(
            shell, "append_jsonl"
        ) as append_jsonl:
            recovered = shell.recover_active_candidate_for_chat(state)
        self.assertEqual(recovered, CANDIDATE_ID)
        self.assertEqual(state, before)
        save_state.assert_not_called()
        append_jsonl.assert_not_called()

    def test_http_chat_guard_precedes_activation_log_and_owner_turn_write(self) -> None:
        source = (ROOT / "tools" / "kira_world_shell_server.py").read_text(encoding="utf-8")
        route = source.index('if path == "/api/chat":')
        segment = source[route:route + 60000]
        gate = segment.index("strict_v4_diagnostic = marinette_v4_owner_text_gate")
        activation = segment.index("activation_block = candidate_activation_block")
        owner_write = segment.index("append_jsonl(\n                            CHAT_LOG")
        self.assertLess(gate, activation)
        self.assertLess(gate, owner_write)

    def test_actual_http_chat_handler_returns_system_409_with_zero_runtime_write(self) -> None:
        handler = object.__new__(shell.Handler)
        handler.path = "/api/chat"
        state = {
            "active_candidate": CANDIDATE_ID,
            "last_active_candidate": CANDIDATE_ID,
            "last_activation_at": "2026-08-10T02:00:00+00:00",
            "location": "home",
        }
        with patch.object(handler, "_body", return_value={"text": "Hello"}), patch.object(
            handler, "_shell_api_authorized", return_value=True
        ), patch.object(handler, "_json") as response, patch.object(
            shell, "load_state", return_value=copy.deepcopy(state)
        ), patch.object(shell, "append_jsonl") as append_jsonl, patch.object(
            shell, "write_json"
        ) as write_json, patch.object(shell, "save_state") as save_state, patch.object(
            shell, "update_candidate"
        ) as update_candidate, patch.object(
            shell, "safe_stop_active_ai"
        ) as safe_stop, patch.object(
            shell, "temporary_ai_reply"
        ) as person_reply:
            handler.do_POST()
        response.assert_called_once()
        status, payload = response.call_args.args
        self.assertEqual(status, 409)
        self.assertTrue(payload["system_owned"])
        self.assertEqual(payload["ai_line"], "")
        self.assertIsNone(payload["person_reply"])
        append_jsonl.assert_not_called()
        write_json.assert_not_called()
        save_state.assert_not_called()
        update_candidate.assert_not_called()
        safe_stop.assert_not_called()
        person_reply.assert_not_called()

    def test_model_preflight_never_reached_while_gate_closed(self) -> None:
        with patch.object(live_chat, "require_installed_exact_qwen35") as preflight, patch.object(
            live_chat.requests, "post"
        ) as post:
            with self.assertRaisesRegex(RuntimeError, "different_agent_v4_audit_required"):
                live_chat.ask_model(self.candidate, [{"role": "user", "content": "poison"}], "Hello")
        preflight.assert_not_called()
        post.assert_not_called()

    def test_future_request_is_exactly_two_messages_and_excludes_latent_context(self) -> None:
        owner_text = "Tell me about avatar body movement world project history."
        request = contract.build_owner_model_request(self.candidate, owner_text)
        self.assertEqual(len(request["messages"]), 2)
        self.assertEqual(request["messages"][1], {"role": "user", "content": owner_text})
        self.assertFalse(request["history_included"])
        system = request["messages"][0]["content"].lower()
        for poison in (
            "temporary_ai_character_context", "voluntary future-body expression",
            "current_project", "attached_workspaces", "recent_chat_records",
            "invented aunt", "separate house",
        ):
            self.assertNotIn(poison, system)

    def test_mocked_future_live_chat_payload_has_no_history_or_context_wrapper(self) -> None:
        class Response:
            status_code = 200

            @staticmethod
            def raise_for_status() -> None:
                return None

            @staticmethod
            def json() -> dict:
                return {"model": live_chat.MODEL_NAME, "message": {"content": "bounded reply"}}

        poisoned_history = [{"role": "assistant", "content": "invented aunt in a separate house"}]
        with patch.object(live_chat, "source_grounded_text_route_readiness", return_value=(True, [])), patch.object(
            live_chat, "require_installed_exact_qwen35"
        ), patch.object(live_chat, "require_exact_qwen35_response_model"), patch.object(
            live_chat.requests, "post", return_value=Response()
        ) as post:
            answer = live_chat.ask_model(self.candidate, poisoned_history, "Exact raw owner turn")
        self.assertEqual(answer, "bounded reply")
        payload = post.call_args.kwargs["json"]
        self.assertEqual(len(payload["messages"]), 2)
        self.assertEqual(payload["messages"][-1]["content"], "Exact raw owner turn")
        self.assertNotIn("invented aunt", json.dumps(payload))

    def test_mocked_future_shell_route_passes_raw_turn_and_empty_history(self) -> None:
        captured: dict[str, object] = {}

        def fake_ask(candidate, history, message, **_kwargs):
            captured.update(candidate=candidate, history=history, message=message)
            return "bounded reply"

        with patch.object(shell, "marinette_v4_owner_text_gate", return_value=None), patch.object(
            shell, "load_candidate", return_value=self.candidate
        ), patch.object(shell, "ask_model", side_effect=fake_ask):
            answer = shell.temporary_ai_reply(
                CANDIDATE_ID,
                "Marinette / Ladybug",
                "Exact raw owner turn",
                "Home World",
                {"avatar": "poison"},
            )
        self.assertEqual(answer, "bounded reply")
        self.assertEqual(captured["history"], [])
        self.assertEqual(captured["message"], "Exact raw owner turn")

    def test_semantic_status_identity_maturity_and_scope_drift_are_rejected(self) -> None:
        attacks = (
            lambda m, _a: m["v4_contract_members"][0].update(sha256="0" * 64),
            lambda m, _a: m["protected_v3_predecessors"][0].update(sha256="0" * 64),
            lambda m, _a: m["local_no_claim_evidence"][0].update(claim_policy="canon_claim"),
            lambda _m, a: a["v4_route_profile"].update(status="active"),
            lambda _m, a: a["v4_route_profile"]["conversation_style"].update(speak_in_first_person_after_future_audit_only=False),
            lambda _m, a: a["v4_route_profile"]["maturity_policy"].update(classification="confirmed_adult"),
            lambda _m, a: a["v4_source_review"].update(review_status="accepted"),
            lambda _m, a: a["v4_source_review"].update(review_id="replacement_review"),
            lambda _m, a: a["v4_source_review"]["voice_scope"].update(authorized_by_this_review=True),
            lambda _m, a: a["v4_runtime_policy"]["runtime_scope"].update(voice_allowed=True),
            lambda _m, a: a["v4_runtime_policy"]["runtime_scope"].update(hidden_override=True),
            lambda _m, a: a["v4_source_pack"].update(status="runtime_ready"),
            lambda _m, a: a["v4_source_pack"].update(source_pack_id="replacement_pack"),
            lambda _m, a: a["v4_official_content_evidence"].update(review_scope="self-asserted support"),
        )
        for attack in attacks:
            self.assertTrue(self._semantic_rejection(attack))

    def test_rank_url_claim_id_relevance_and_contradiction_attacks_are_rejected(self) -> None:
        attacks = (
            lambda _m, a: a["v4_source_registry"]["sources"][0].update(source_rank=99),
            lambda _m, a: a["v4_source_registry"]["sources"][0].update(url="https://fan.invalid/official"),
            lambda _m, a: a["v4_official_content_evidence"]["records"][0]["claim_support"][0].update(claim_id="season6_finale"),
            lambda _m, a: a["v4_official_content_evidence"]["records"][0]["claim_support"][0].update(supported_statement="Unrelated but nonempty support."),
            lambda _m, a: a["v4_official_content_evidence"]["records"][0].update(verbatim_excerpt="Different content"),
            lambda _m, a: a["v4_source_registry"]["sources"][-1].update(allowed_claim_ids=["season6_finale"]),
            lambda _m, a: a["v4_official_content_evidence"]["records"][-1].update(claim_policy="canon_claim"),
        )
        for attack in attacks:
            self.assertTrue(self._semantic_rejection(attack))

    def test_coordinated_unsupported_season6_claim_still_fails_exact_catalog(self) -> None:
        def coordinated(_manifest, artifacts):
            bogus = {
                "claim_id": "season6_finale",
                "classification": "official_primary_source_fact",
                "statement": "A fabricated finale and event order happened.",
                "source_ids": ["official_miraculous_s6_new_episodes_20260226"],
            }
            artifacts["v4_runtime_policy"]["claims"].append(copy.deepcopy(bogus))
            artifacts["v4_source_pack"]["source_bound_claims"].append(copy.deepcopy(bogus))
            artifacts["v4_source_review"]["canon_anchors"].append(copy.deepcopy(bogus))
            artifacts["v4_source_registry"]["sources"][3]["allowed_claim_ids"].append("season6_finale")
            artifacts["v4_official_content_evidence"]["records"][3]["claim_support"].append(
                {"claim_id": "season6_finale", "supported_statement": bogus["statement"]}
            )

        self.assertEqual(self._semantic_rejection(coordinated), "runtime_claim_catalog_mismatch")

    def test_post_load_secondary_old_project_avatar_and_body_injection_fails(self) -> None:
        for key, value in (
            ("reliable_source_pack", {"claims": ["fabricated finale"]}),
            ("recent_chat_records", [{"candidate": "invented aunt"}]),
            ("project_continuity", {"current_project": "separate house"}),
            ("activation_plan", {"body": "active"}),
        ):
            changed = copy.deepcopy(self.candidate)
            changed[key] = value
            with self.assertRaisesRegex(contract.MarinetteCanonContractV4Error, "candidate_snapshot_mismatch:" + key):
                contract.validate_candidate_snapshot(changed)

    def test_non_adult_doll_safe_private_inactive_and_all_surfaces_denied(self) -> None:
        self.assertEqual(canonical_avatar_maturity_class(CANDIDATE_ID), "non_adult_doll_safe")
        profile = self.artifacts["v4_route_profile"]
        self.assertEqual(profile["status"], "inactive_frozen_pending_different_agent_v4_audit")
        self.assertFalse(profile["maturity_policy"]["adult_anatomy_allowed"])
        self.assertFalse(profile["maturity_policy"]["adult_curriculum_allowed"])
        self.assertFalse(profile["maturity_policy"]["body_activation_authorized"])
        runtime = self.artifacts["v4_runtime_policy"]["runtime_scope"]
        for key, value in runtime.items():
            if key not in {"contract_integrity_static_audit_allowed", "fresh_independent_audit_required"}:
                self.assertFalse(value, key)
        with patch.object(shell, "TEXT_ONLY_CHAT_MODE", True):
            self.assertEqual(shell.candidate_activation_block(CANDIDATE_ID)["reason"], "strict_v4_different_agent_audit_required")
        with patch.object(shell, "TEXT_ONLY_CHAT_MODE", False):
            self.assertEqual(shell.candidate_activation_block(CANDIDATE_ID)["reason"], "strict_v4_text_only_world_denied")


class MarinetteV4StableOpenAdversarialTests(unittest.TestCase):
    def _write(self, root: Path, relative: str, data: bytes) -> str:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return hashlib.sha256(data).hexdigest()

    def test_plain_exact_file_passes_and_traversal_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            digest = self._write(root, "inside/value.bin", b"exact")
            self.assertEqual(
                contract._stable_read_hashed("inside/value.bin", digest, project_root=root),
                b"exact",
            )
            with self.assertRaisesRegex(contract.MarinetteCanonContractV4Error, "not_exact_project_relative"):
                contract._stable_read_hashed("../outside.bin", digest, project_root=root)

    def test_hardlink_alias_is_rejected_even_when_bytes_and_hash_match(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            digest = self._write(root, "outside.bin", b"same bytes")
            os.link(root / "outside.bin", root / "inside.bin")
            with self.assertRaisesRegex(contract.MarinetteCanonContractV4Error, "multiple_hardlinks"):
                contract._stable_read_hashed("inside.bin", digest, project_root=root)

    def test_file_symlink_or_reparse_is_rejected_when_platform_allows_creation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            digest = self._write(root, "outside.bin", b"same bytes")
            try:
                os.symlink(root / "outside.bin", root / "inside.bin")
            except (OSError, NotImplementedError) as exc:
                self.skipTest("file symlink creation unavailable: " + str(exc))
            with self.assertRaisesRegex(contract.MarinetteCanonContractV4Error, "reparse_or_not_regular"):
                contract._stable_read_hashed("inside.bin", digest, project_root=root)

    @unittest.skipUnless(os.name == "nt", "Windows junction probe")
    def test_internal_junction_to_outside_directory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outside = root / "outside"
            outside.mkdir()
            digest = self._write(outside, "value.bin", b"junction bytes")
            junction = root / "alias"
            result = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(junction), str(outside)],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                self.skipTest("junction creation unavailable: " + result.stderr)
            with self.assertRaisesRegex(contract.MarinetteCanonContractV4Error, "reparse_or_non_directory_component"):
                contract._stable_read_hashed("alias/value.bin", digest, project_root=root)

    @unittest.skipUnless(os.name == "nt", "Windows external-junction probe")
    def test_junction_to_directory_outside_root_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as root_directory, tempfile.TemporaryDirectory() as outside_directory:
            root = Path(root_directory)
            outside = Path(outside_directory)
            digest = self._write(outside, "value.bin", b"external junction bytes")
            junction = root / "alias"
            result = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(junction), str(outside)],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                self.skipTest("external junction creation unavailable: " + result.stderr)
            with self.assertRaisesRegex(contract.MarinetteCanonContractV4Error, "reparse_or_non_directory_component"):
                contract._stable_read_hashed("alias/value.bin", digest, project_root=root)

    def test_changed_path_snapshot_is_rejected_before_content_is_trusted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            digest = self._write(root, "value.bin", b"stable")
            real_lstat = contract.os.lstat
            calls = 0

            class ChangedStat:
                def __init__(self, wrapped):
                    self._wrapped = wrapped

                def __getattr__(self, name):
                    if name == "st_size":
                        return self._wrapped.st_size + 1
                    return getattr(self._wrapped, name)

            def changed_lstat(path):
                nonlocal calls
                value = real_lstat(path)
                if Path(path) == root / "value.bin":
                    calls += 1
                    if calls > 1:
                        return ChangedStat(value)
                return value

            with patch.object(contract.os, "lstat", side_effect=changed_lstat):
                with self.assertRaisesRegex(contract.MarinetteCanonContractV4Error, "changed_during_read"):
                    contract._stable_read_hashed("value.bin", digest, project_root=root)


if __name__ == "__main__":
    unittest.main()
