from __future__ import annotations

import hashlib
import json
import sys
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from Core.garment_contracts import GarmentState, build_robe_definition  # noqa: E402
from Core.garment_evidence import evaluate_garment_transition  # noqa: E402
from serve_kira_wardrobe_lab_notebook_world import (  # noqa: E402
    BUILD_MANIFEST,
    BUILD_MANIFEST_SHA256,
    allowed_asset_urls,
    bind_server,
    pinned_preview_relative_path,
    verify_pinned_build,
)
from validate_notebook_world_request import validate_notebook_world_request  # noqa: E402


BUILD = (
    ROOT
    / "Data"
    / "world_builds"
    / "notebook_worlds"
    / "kira_wardrobe_lab_notebook_world"
    / "builds"
    / "notebook_world_kira_wardrobe_lab_staged_20260715"
)
REGISTRATION = BUILD / "registration.json"
STATE_MACHINE = BUILD / "wardrobe_state_machine.json"
BRIDGE = BUILD / "core_garment_bridge.json"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class KiraWardrobeNotebookLabTests(unittest.TestCase):
    def test_code_pinned_manifest_binds_registration_all_metadata_and_index(self) -> None:
        verified = verify_pinned_build()
        self.assertEqual(verified.manifest_path, BUILD_MANIFEST)
        self.assertEqual(verified.manifest_sha256, BUILD_MANIFEST_SHA256)
        self.assertEqual(
            verified.registration_sha256,
            "9132fd24b54741d7f87896af4ff9b5d28d4d5ef57f9a221471b5de069251922c",
        )
        self.assertEqual(
            verified.index_anchor_sha256,
            "fc87ced00417eb5ea0f31fa857c35ca323c626ec3b0d86a1f925d86c9c2cb90b",
        )
        for role in (
            "state_machine_metadata",
            "builder_contract_metadata",
            "core_garment_bridge_metadata",
            "approval_gate_metadata",
        ):
            self.assertEqual(len(verified.role_paths[role]), 1, role)

    def test_integrity_failure_happens_before_socket_bind(self) -> None:
        with (
            patch(
                "serve_kira_wardrobe_lab_notebook_world.verify_pinned_build",
                side_effect=ValueError("simulated tamper"),
            ),
            patch("serve_kira_wardrobe_lab_notebook_world.ThreadingHTTPServer") as server_constructor,
        ):
            with self.assertRaisesRegex(ValueError, "simulated tamper"):
                bind_server(0)
        server_constructor.assert_not_called()

    def test_registered_as_separate_kira_only_notebook_world(self) -> None:
        index = read_json(ROOT / "Data/world_builds/notebook_world_index.json")
        worlds = index["notebook_worlds"]
        self.assertIn("kira_wardrobe_lab_notebook_world", worlds)
        anchors = worlds["kira_wardrobe_lab_notebook_world"]["anchors"]
        self.assertEqual(
            [item["request_id"] for item in anchors],
            ["notebook_world_kira_wardrobe_lab_staged_20260715"],
        )
        registration = read_json(REGISTRATION)
        self.assertTrue(registration["single_3d_person_only"])
        self.assertTrue(registration["loads_kira_body"])
        self.assertFalse(registration["loads_kira_mind"])
        self.assertFalse(registration["loads_voice"])
        self.assertFalse(registration["loads_ollama"])
        self.assertFalse(registration["loads_second_person"])
        self.assertFalse(registration["modifies_live_kira_body"])
        self.assertFalse(registration["modifies_home_world"])

    def test_registration_pins_exactly_current_body_and_static_robe(self) -> None:
        registration = read_json(REGISTRATION)
        self.assertEqual(len(registration["assets"]), 2)
        roles = {item["role"] for item in registration["assets"]}
        self.assertEqual(
            roles,
            {"read_only_current_body", "read_only_static_reference_not_wearable"},
        )
        for asset in registration["assets"]:
            path = ROOT / asset["source"]
            self.assertTrue(path.is_file())
            self.assertEqual(path.stat().st_size, asset["bytes"])
            self.assertEqual(sha256(path), asset["sha256"])
        body = next(item for item in registration["assets"] if item["id"] == "kira_current_body")
        self.assertEqual(
            body["sha256"],
            "3ec62ba8d70a2c8235ef2013ff8183b7b3e9c41ca40c33e8b31d758b4ca3339e",
        )

    def test_standard_notebook_request_is_valid_and_placement_isolated(self) -> None:
        request = read_json(BUILD / "notebook_world_request.json")
        self.assertEqual(validate_notebook_world_request(request), [])
        self.assertEqual(
            request["world_plan"]["notebook_world_id"],
            "kira_wardrobe_lab_notebook_world",
        )
        placement = read_json(BUILD / "placement.json")
        self.assertFalse(placement["home_world_import_requested"])
        self.assertFalse(placement["home_world_modified"])
        self.assertFalse(placement["live_kira_body_modified"])
        self.assertTrue(placement["world_contains_one_visual_body"])
        self.assertFalse(placement["world_loads_any_autonomous_person"])

    def test_state_graph_is_reachable_and_all_claims_fail_closed(self) -> None:
        machine = read_json(STATE_MACHINE)
        states = machine["states"]
        by_id = {state["id"]: state for state in states}
        self.assertEqual(len(by_id), len(states))
        self.assertIn(machine["initial_state"], by_id)
        for state in states:
            self.assertFalse(state["claim_allowed"], state["id"])
            self.assertEqual(state["verified_signals"], [], state["id"])
            self.assertTrue(state["required_signals"], state["id"])
            self.assertTrue(state["blockers"], state["id"])
            self.assertTrue(
                state["status"].startswith("blocked") or state["status"] == "staged_reference_only",
                state["id"],
            )
            for target in state["next"]:
                self.assertIn(target, by_id)

        reachable = set()
        pending = [machine["initial_state"]]
        while pending:
            state_id = pending.pop()
            if state_id in reachable:
                continue
            reachable.add(state_id)
            pending.extend(by_id[state_id]["next"])
        self.assertEqual(reachable, set(by_id))
        self.assertEqual(
            by_id["return_choice"]["next"],
            ["rehang_robe", "place_on_bed"],
        )
        self.assertFalse(machine["truth_policy"]["timers_are_evidence"])
        self.assertFalse(machine["truth_policy"]["button_clicks_are_evidence"])
        self.assertFalse(machine["truth_policy"]["posed_meshes_are_evidence"])

    def test_requested_vertical_slice_stages_are_present_in_order(self) -> None:
        ids = [state["id"] for state in read_json(STATE_MACHINE)["states"]]
        expected = [
            "hanging_on_hook",
            "grasp_contact",
            "detached_held",
            "right_sleeve_portal",
            "left_sleeve_portal",
            "settle_shoulders",
            "worn_open",
            "belt_left_grasp",
            "belt_right_grasp",
            "belt_cross",
            "belt_loop",
            "belt_tighten",
            "worn_tied",
            "walk_worn",
            "turn_worn",
            "sit_worn",
            "stand_worn",
            "untie_belt",
            "remove_shoulders",
            "right_arm_out",
            "left_arm_out",
            "return_choice",
            "rehang_robe",
            "place_on_bed",
            "round_trip_review",
        ]
        self.assertEqual(ids, expected)

    def test_shared_core_bridge_is_inactive_until_real_compatibility_exists(self) -> None:
        bridge = read_json(BRIDGE)
        activation = bridge["definition_activation"]
        self.assertFalse(activation["ready"])
        self.assertFalse(activation["ledger_registration_allowed"])
        self.assertIsNone(bridge["definition_inputs"]["compatible_rig_sha256"])
        self.assertFalse(bridge["truth_gate"]["preview_creates_transactions"])
        self.assertFalse(bridge["truth_gate"]["preview_commits_transactions"])
        self.assertFalse(bridge["truth_gate"]["preview_submits_evidence"])
        self.assertTrue(bridge["truth_gate"]["empty_or_timer_evidence_must_fail"])

        core_state_values = {state.value for state in GarmentState}
        definition = build_robe_definition(
            garment_type_id=bridge["definition_inputs"]["garment_type_id"],
            asset_sha256=bridge["definition_inputs"]["asset_sha256"],
            compatible_body_sha256=bridge["definition_inputs"]["compatible_body_sha256"],
            compatible_rig_sha256="0" * 64,
        )
        mapped_affordances = set()
        mapped_states = set()
        for mapping in bridge["lab_to_core_mapping"]:
            mapped_states.add(mapping["core_state"])
            if mapping.get("core_affordance_to_next"):
                mapped_affordances.add(mapping["core_affordance_to_next"])
            mapped_affordances.update(mapping.get("core_branch_affordances", []))
        self.assertTrue(mapped_states <= core_state_values)
        for affordance_id in mapped_affordances:
            affordance = definition.affordance(affordance_id)
            decision = evaluate_garment_transition(
                definition,
                affordance,
                {},
                transaction_id="wardrobe-lab-test-only",
                item_instance_id="kira_wardrobe_lab_shared_white_bath_robe_v1_instance_001",
            )
            self.assertFalse(decision.passed, affordance_id)
            self.assertTrue(decision.reasons, affordance_id)

    def test_builder_contract_preserves_one_item_and_optional_participation(self) -> None:
        contract = read_json(BUILD / "builder_contract.json")
        self.assertEqual(
            contract["item"]["persistent_instance_id"],
            "kira_wardrobe_lab_shared_white_bath_robe_v1_instance_001",
        )
        self.assertIn("Only one authoritative representation", contract["item"]["representation_rule"])
        self.assertTrue(contract["shared_runtime_contract"]["no_duplication"])
        self.assertTrue(contract["shared_runtime_contract"]["no_teleport"])
        self.assertTrue(contract["shared_runtime_contract"]["no_timer_only_completion"])
        self.assertTrue(contract["autonomy_contract"]["participation_is_optional"])
        self.assertTrue(contract["autonomy_contract"]["kira_can_refuse"])
        self.assertTrue(contract["autonomy_contract"]["kira_can_pause_or_stop"])
        self.assertTrue(contract["autonomy_contract"]["kira_can_choose_rehang_or_bed"])
        self.assertTrue(contract["autonomy_contract"]["refusal_is_not_a_mechanical_failure"])

    def test_approval_gate_forbids_live_activation_and_timer_proof(self) -> None:
        gate = read_json(BUILD / "approval_gate.json")
        self.assertFalse(gate["world_builder_may_commit_to_home_world"])
        self.assertFalse(gate["avatar_builder_may_activate_garment"])
        self.assertFalse(gate["live_kira_body_may_be_replaced"])
        self.assertFalse(gate["timers_may_count_as_physical_proof"])
        self.assertFalse(gate["manual_stage_buttons_may_count_as_physical_proof"])
        self.assertFalse(gate["staged_visuals_may_count_as_physical_proof"])
        self.assertGreaterEqual(len(gate["current_blockers"]), 4)

    def test_preview_navigation_has_no_timer_or_runtime_mutation_path(self) -> None:
        source = (BUILD / "preview/main.js").read_text(encoding="utf-8")
        self.assertNotIn("setTimeout(", source)
        self.assertNotIn("setInterval(", source)
        self.assertNotIn("AnimationMixer", source)
        self.assertNotIn("GarmentLedger", source)
        self.assertNotIn('method: "POST"', source)
        self.assertIn("requestAnimationFrame", source)
        self.assertIn("inspection_marker_not_evidence", source)
        self.assertIn("keepOneHangingRobeReference", source)
        self.assertIn('"robe_hanging_back_panel_soft_mesh"', source)
        self.assertNotIn('name.startsWith("robe_hanging_")', source)
        self.assertIn('stagedWorldAnchor("bathroom_wall_hook"', source)
        self.assertIn('stagedWorldAnchor("bed_soft_goods_place_anchor"', source)
        self.assertIn("stagedNotEvidence", source)

    def test_scoped_server_serves_preview_metadata_and_assets_but_not_workspace(self) -> None:
        registration = read_json(REGISTRATION)
        self.assertEqual(ROOT / pinned_preview_relative_path(), ROOT / registration["preview"])
        assets = allowed_asset_urls()
        self.assertEqual(set(assets), {"/assets/kira-current-body.glb", "/assets/robe-draft-proof.glb"})
        server, port = bind_server(0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/index.html", timeout=5) as response:
                self.assertEqual(response.status, 200)
                self.assertIn(b"Kira Wardrobe Lab", response.read())
                self.assertIn("default-src", response.headers["Content-Security-Policy"])

            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/data/wardrobe_state_machine.json",
                timeout=5,
            ) as response:
                self.assertEqual(response.status, 200)
                self.assertIn(b"staged_sequence_all_physical_claims_blocked", response.read())

            for metadata_path in (
                "/data/builder_contract.json",
                "/data/core_garment_bridge.json",
                "/data/approval_gate.json",
            ):
                with urllib.request.urlopen(f"http://127.0.0.1:{port}{metadata_path}", timeout=5) as response:
                    self.assertEqual(response.status, 200)
                    self.assertGreater(len(response.read()), 100)

            asset_url = next(iter(assets))
            request = urllib.request.Request(
                f"http://127.0.0.1:{port}{quote(asset_url, safe='/')}",
                method="HEAD",
            )
            with urllib.request.urlopen(request, timeout=5) as response:
                self.assertEqual(response.status, 200)
                self.assertGreater(int(response.headers["content-length"]), 100)

            with self.assertRaises(urllib.error.HTTPError) as blocked:
                urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/Data/identity/robert_presence_ai_variant_policy_20260712.json",
                    timeout=5,
                )
            self.assertEqual(blocked.exception.code, 404)
            blocked.exception.close()

            for path in ("/preview/README.md", "/%2e%2e/Data/launch/hardware_capability_profile.json"):
                with self.assertRaises(urllib.error.HTTPError) as divergent:
                    urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=5)
                self.assertEqual(divergent.exception.code, 404)
                divergent.exception.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
