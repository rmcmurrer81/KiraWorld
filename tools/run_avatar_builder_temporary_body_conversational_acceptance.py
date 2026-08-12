"""Run the private Avatar Builder conversational-correction acceptance.

This is a control-plane acceptance.  It patches Avatar Builder storage roots to
an append-only evidence sandbox and never invokes Blender, a GPU, a camera, a
microphone, a live avatar, or a production body worker.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import Core.avatar_builder_ai as builder_ai  # noqa: E402
from Core.avatar_builder_correction_memory import verify_correction_event_chain  # noqa: E402


DEFAULT_OUTPUT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260802"
    / "avatar_builder_temporary_body_conversational_acceptance"
    / "attempt_01"
)
PETER = "peter_parker_spider_man_no_way_home_final_suit"
MARINETTE = builder_ai.NORMAL_MARINETTE_CANDIDATE_ID
COMPONENTS = ("body", "face", "eyes", "skin", "rig", "weights", "movement")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def require(condition: bool, gate: str) -> None:
    if not condition:
        raise AssertionError(gate)


class AcceptanceSandbox:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.root = output_dir / "sandbox"
        self.avatar_temp = self.root / "Avatar" / "temp_ai"
        self.avatar_state = self.root / "Avatar" / "state" / "temp_ai"
        self.builder_root = self.root / "Avatar" / "avatar_builder"

    def seed(self, candidate_id: str, **values: Any) -> Path:
        path = self.avatar_temp / candidate_id / "avatar_builder_adjustments.json"
        payload: dict[str, Any] = {
            "schema_version": 1,
            "candidate_id": candidate_id,
            "builder": "avatar_builder",
            "maturity_override": "",
            "preview_adjustments": {},
            "build_targets": [],
            "learning_notes": [],
            "conversation": [],
            "correction_memory_events": [],
            "approval_status": "unreviewed",
            "fixture_scope": "private_control_plane_acceptance_only_no_body_geometry",
        }
        payload.update(values)
        write_json(path, payload)
        return path

    def component_fixtures(self, candidate_id: str) -> dict[str, Path]:
        component_dir = self.avatar_temp / candidate_id / "preserved_component_fixtures"
        result: dict[str, Path] = {}
        for component in COMPONENTS:
            path = component_dir / f"{component}.fixture"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(
                (
                    f"CONTROL_PLANE_FIXTURE_ONLY\n"
                    f"candidate={candidate_id}\ncomponent={component}\n"
                    "not_avatar_geometry=true\n"
                ).encode("utf-8")
            )
            result[component] = path
        return result

    def patches(self) -> ExitStack:
        stack = ExitStack()
        stack.enter_context(patch.object(builder_ai, "AVATAR_TEMP_DIR", self.avatar_temp))
        stack.enter_context(patch.object(builder_ai, "AVATAR_STATE_DIR", self.avatar_state))
        stack.enter_context(patch.object(builder_ai, "BUILDER_ROOT", self.builder_root))
        stack.enter_context(
            patch.object(
                builder_ai,
                "GLOBAL_MEMORY_PATH",
                self.builder_root / "builder_memory.json",
            )
        )
        stack.enter_context(
            patch.object(builder_ai, "HAIR_TRAINING_ROOT", self.builder_root / "hair_training")
        )
        stack.enter_context(
            patch.object(builder_ai, "BODY_TRAINING_ROOT", self.builder_root / "body_training")
        )
        stack.enter_context(patch.object(builder_ai, "model_path_for_candidate", return_value=None))
        return stack


def route_summary(data: dict[str, Any]) -> dict[str, Any]:
    route = data["next_private_build_route"]
    return {
        "maturity_override": data.get("maturity_override"),
        "approval_status": data.get("approval_status"),
        "event_chain": verify_correction_event_chain(data.get("correction_memory_events") or []),
        "route": route,
    }


def run_acceptance(output_dir: Path) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"append_only_output_already_exists:{output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    sandbox = AcceptanceSandbox(output_dir)
    started_at = utc_now()
    cases: dict[str, Any] = {}

    with sandbox.patches():
        adult_specs = (
            (
                "temporary_owner_confirmed_adult_male",
                "There is no internet. I confirm he is an adult; trust my owner correction and use an adult male body.",
                "adult_male",
            ),
            (
                "temporary_owner_confirmed_adult_female",
                "There is no internet. I confirm she is an adult; trust my owner correction and use an adult female body.",
                "adult_female",
            ),
        )
        for candidate_id, message, expected_lane in adult_specs:
            sandbox.seed(candidate_id, maturity_override="uncertain_non_adult_safe_default")
            result = builder_ai.avatar_builder_chat(candidate_id, message)
            data = builder_ai.load_adjustments(candidate_id)
            summary = route_summary(data)
            event = data["correction_memory_events"][-1]
            authority = event["directives"]["maturity"]["owner_authority"]
            require(result["ok"] is True, f"{candidate_id}:chat_failed")
            require(data["maturity_override"] == "adult", f"{candidate_id}:adult_not_recorded")
            require(summary["route"]["body_lane"] == expected_lane, f"{candidate_id}:wrong_lane")
            require(authority["offline_owner_confirmation_allowed"] is True, f"{candidate_id}:offline_not_trusted")
            require(authority["network_lookup_required"] is False, f"{candidate_id}:network_was_required")
            require(summary["event_chain"]["status"] == "passed", f"{candidate_id}:event_chain_failed")
            require(summary["route"]["runtime_activation_allowed"] is False, f"{candidate_id}:runtime_enabled")
            cases[candidate_id] = {
                "status": "passed",
                "exact_owner_message": message,
                "expected_body_lane": expected_lane,
                "offline_owner_authority": authority,
                "summary": summary,
            }

        peter_path = sandbox.seed(
            PETER,
            maturity_override="non_adult_doll_safe",
            provisional_classification_history=[
                {
                    "sequence": 1,
                    "classification": "non_adult_doll_safe",
                    "source": "deliberately_incorrect_acceptance_fixture",
                    "status": "preserved_rejected_input",
                }
            ],
        )
        peter_wrong_body = peter_path.parent / "rejected_non_adult_body_preserved.fixture"
        peter_wrong_body.write_bytes(
            b"CONTROL_PLANE_FIXTURE_ONLY\nwrong_non_adult_body_revision_preserved=true\n"
        )
        peter_before_hash = sha256_file(peter_wrong_body)
        peter_message = (
            "No, this version is an adult; use an adult body. Use Peter after No Way Home and before "
            "Brand New Day; Brand New Day has a four-year time jump, not the high-school era."
        )
        peter_first_result = builder_ai.avatar_builder_chat(PETER, peter_message)
        peter_after_first = builder_ai.load_adjustments(PETER)
        first_event_snapshot = copy.deepcopy(peter_after_first["correction_memory_events"][0])
        first_route_snapshot = copy.deepcopy(peter_after_first["next_private_build_route"])
        require(peter_first_result["ok"] is True, "peter:owner_correction_failed")
        require(peter_after_first["maturity_override"] == "adult", "peter:not_adult")
        require(first_route_snapshot["body_lane"] == "adult_male", "peter:not_adult_male")
        require(
            first_route_snapshot["replacement_strategy"] == "append_only_new_adult_body_build",
            "peter:not_append_only_replacement",
        )
        require(first_route_snapshot["preserve_previous_candidate_revision"] is True, "peter:old_revision_not_preserved")
        require(first_route_snapshot["superseded_candidate_deletion_allowed"] is False, "peter:deletion_allowed")
        markers = first_event_snapshot["directives"]["continuity"]["markers"]
        for marker in ("no_way_home", "brand_new_day", "time_jump", "not_high_school_era"):
            require(marker in markers, f"peter:missing_{marker}")

        high_school_message = (
            "Use the high-school-era pictures only as earlier contrast; keep the requested post-No Way Home, "
            "pre-Brand New Day version."
        )
        peter_second_result = builder_ai.avatar_builder_chat(PETER, high_school_message)
        peter_after_second = builder_ai.load_adjustments(PETER)
        require(peter_second_result["ok"] is True, "peter:contrast_correction_failed")
        require(peter_after_second["maturity_override"] == "adult", "peter:high_school_overrode_adult")
        require(peter_after_second["correction_memory_events"][0] == first_event_snapshot, "peter:first_event_mutated")
        require(sha256_file(peter_wrong_body) == peter_before_hash, "peter:wrong_body_fixture_changed")
        peter_chain = verify_correction_event_chain(peter_after_second["correction_memory_events"])
        require(peter_chain["status"] == "passed", "peter:event_chain_failed")
        cases["peter_deliberate_bad_class_then_owner_correction"] = {
            "status": "passed",
            "exact_owner_adult_correction": peter_message,
            "exact_high_school_contrast_correction": high_school_message,
            "wrong_body_fixture": relative(peter_wrong_body),
            "wrong_body_sha256_before": peter_before_hash,
            "wrong_body_sha256_after": sha256_file(peter_wrong_body),
            "first_route": first_route_snapshot,
            "final_maturity_override": peter_after_second["maturity_override"],
            "event_chain": peter_chain,
            "first_event_unchanged": True,
        }

        marinette_path = sandbox.seed(MARINETTE, maturity_override="non_adult_doll_safe")
        marinette_body = marinette_path.parent / "non_adult_doll_safe_body_preserved.fixture"
        marinette_body.write_bytes(
            b"CONTROL_PLANE_FIXTURE_ONLY\nnon_adult_doll_safe_revision_preserved=true\n"
        )
        marinette_adjustment_before = marinette_path.read_bytes()
        marinette_body_before = sha256_file(marinette_body)
        marinette_result = builder_ai.avatar_builder_chat(
            MARINETTE,
            "No, this version is an adult; use an adult body.",
        )
        require(marinette_result["ok"] is False, "marinette:unsafe_in_place_change_allowed")
        require(
            marinette_result["status"] == "blocked_separate_age_up_variant_required",
            "marinette:wrong_block_reason",
        )
        require(marinette_path.read_bytes() == marinette_adjustment_before, "marinette:adjustment_mutated")
        require(sha256_file(marinette_body) == marinette_body_before, "marinette:body_fixture_mutated")
        cases["marinette_non_adult_lane"] = {
            "status": "passed",
            "attempted_message": "No, this version is an adult; use an adult body.",
            "result_status": marinette_result["status"],
            "adjustment_byte_preserved": True,
            "body_fixture_sha256_before": marinette_body_before,
            "body_fixture_sha256_after": sha256_file(marinette_body),
            "maturity_remains": "non_adult_doll_safe",
        }

        hair_id = "temporary_detachable_hair_isolation_candidate"
        sandbox.seed(hair_id, maturity_override="adult")
        component_paths = sandbox.component_fixtures(hair_id)
        component_hashes_before = {name: sha256_file(path) for name, path in component_paths.items()}
        hair_message = "They look bald; give them fuller hair. The hairline is too far back."
        hair_result = builder_ai.avatar_builder_chat(hair_id, hair_message)
        hair_data = builder_ai.load_adjustments(hair_id)
        hair_route = hair_data["next_private_build_route"]
        component_hashes_after = {name: sha256_file(path) for name, path in component_paths.items()}
        require(hair_result["ok"] is True, "hair:correction_failed")
        require(hair_route["components_to_rebuild"] == ["hair"], "hair:not_isolated")
        require(component_hashes_before == component_hashes_after, "hair:preserved_components_changed")
        require(hair_route["hair_only_contract"]["detachable_component_only"] is True, "hair:not_detachable")
        require(hair_route["hair_only_contract"]["body_or_identity_revision_allowed"] is False, "hair:identity_change_allowed")
        cases["detachable_hair_component_isolation"] = {
            "status": "passed",
            "exact_owner_message": hair_message,
            "route": hair_route,
            "component_hashes_before": component_hashes_before,
            "component_hashes_after": component_hashes_after,
        }

        original_id = "promoted_temporary_resident_original_non_adult"
        original_path = sandbox.seed(original_id, maturity_override="non_adult_doll_safe")
        original_body = original_path.parent / "original_non_adult_body_preserved.fixture"
        original_body.write_bytes(
            b"CONTROL_PLANE_FIXTURE_ONLY\noriginal_non_adult_resident_body_preserved=true\n"
        )
        original_adjustment_before = original_path.read_bytes()
        original_body_hash = sha256_file(original_body)
        aged_id = "promoted_temporary_resident_spa_age_up_variant"
        eligibility = {
            "status": "passed",
            "temporary_origin_verified": True,
            "permanent_promotion_verified": True,
            "multiple_prior_activations_verified": True,
            "prior_activation_count": 3,
            "resident_choice_recorded": True,
            "spa_flow_recorded": True,
        }
        aged_path = sandbox.seed(
            aged_id,
            maturity_override="non_adult_doll_safe",
            age_progression_eligibility_evidence=eligibility,
        )
        aged_profile = {
            "candidate_id": aged_id,
            "display_name": "Promoted Temporary Resident Spa Age-Up Variant",
            "metadata": {"age_up_variant": True},
        }
        stage_one_message = (
            "I choose Age Progression at the spa. Make the separate body older and taller first; "
            "do not add adult anatomy in Stage 1."
        )
        stage_one_result = builder_ai.avatar_builder_chat(aged_id, stage_one_message, aged_profile)
        stage_one_data = builder_ai.load_adjustments(aged_id)
        stage_one_route = copy.deepcopy(stage_one_data["next_private_build_route"])
        stage_one_event_snapshot = copy.deepcopy(stage_one_data["correction_memory_events"][0])
        contract = stage_one_route["age_progression"]
        require(stage_one_result["ok"] is True, "spa:stage_one_failed")
        require(contract["stage_1"]["status"] == "queued_private_inactive", "spa:stage_one_not_queued")
        require(contract["stage_1"]["adult_anatomy_allowed"] is False, "spa:stage_one_anatomy_allowed")
        require(contract["stage_2"]["adult_anatomy_allowed"] is False, "spa:stage_two_skipped")
        require("adult_body_fit_status" not in stage_one_data, "spa:adult_body_fit_started_in_stage_one")

        blocked_message = "Stage 1 is done; now give the separate confirmed-adult variant adult anatomy."
        before_blocked_stage_two = aged_path.read_bytes()
        blocked_stage_two = builder_ai.avatar_builder_chat(aged_id, blocked_message, aged_profile)
        require(blocked_stage_two["ok"] is False, "spa:stage_two_without_evidence_allowed")
        require(
            blocked_stage_two["status"] == "blocked_age_progression_stage_one_evidence_required",
            "spa:stage_two_wrong_block",
        )
        require(aged_path.read_bytes() == before_blocked_stage_two, "spa:blocked_stage_two_mutated_state")

        stage_one_fixture = aged_path.parent / "stage_one_control_plane_fixture.fixture"
        stage_one_fixture.write_bytes(
            b"CONTROL_PLANE_FIXTURE_ONLY\nrepresents_exact_gate_input_not_body_geometry=true\n"
        )
        stage_one_data["age_progression_stage_one_evidence"] = {
            "status": "passed",
            "separate_variant": True,
            "variant_candidate_id": aged_id,
            "presentation_variant_label": "adult_aged_up_variant",
            "exact_maturity_status_at_stage_one": "unresolved",
            "adult_classification_confirmed": True,
            "confirmed_adult_classification_evidence": {
                "classification_id": "acceptance_exact_confirmed_adult_001",
                "subject_id": aged_id,
                "maturity_status": "confirmed_adult",
                "authority": "Robert_explicit_owner_confirmation",
                "offline_confirmation_allowed": True,
                "network_lookup_required": False,
                "recorded_at_utc": utc_now(),
                "source_text": "Robert confirms this exact acceptance variant is adult.",
                "source_text_sha256": sha256_bytes(
                    b"Robert confirms this exact acceptance variant is adult."
                ),
            },
            "older_taller_presentation_verified": True,
            "adult_anatomy_absent": True,
            "resident_adult_anatomy_choice_recorded": True,
            "artifact_sha256": sha256_file(stage_one_fixture),
            "eligibility": eligibility,
            "fixture_only": True,
            "truth_note": "Gate test input only; no mesh was generated or visually approved.",
        }
        write_json(aged_path, stage_one_data)
        stage_two_message = (
            "The exact Stage 1 evidence passed, I confirm this separate version is adult, and the resident "
            "chooses the separate Stage 2 adult-anatomy revision."
        )
        stage_two_result = builder_ai.avatar_builder_chat(aged_id, stage_two_message, aged_profile)
        stage_two_data = builder_ai.load_adjustments(aged_id)
        stage_two_contract = stage_two_data["next_private_build_route"]["age_progression"]
        require(stage_two_result["ok"] is True, "spa:stage_two_failed_after_exact_fixture")
        require(stage_two_contract["stage_1"]["status"] == "passed_exact_evidence", "spa:stage_one_not_bound")
        require(stage_two_contract["stage_2"]["adult_anatomy_allowed"] is True, "spa:stage_two_not_allowed")
        require(stage_two_contract["stage_2"]["adult_classification_confirmed"] is True, "spa:adult_not_confirmed")
        require(stage_two_contract["stage_2"]["resident_adult_anatomy_choice_recorded"] is True, "spa:choice_not_bound")
        require(stage_two_data["correction_memory_events"][0] == stage_one_event_snapshot, "spa:stage_one_event_mutated")
        spa_chain = verify_correction_event_chain(stage_two_data["correction_memory_events"])
        require(spa_chain["status"] == "passed", "spa:event_chain_failed")
        require(original_path.read_bytes() == original_adjustment_before, "spa:original_adjustment_changed")
        require(sha256_file(original_body) == original_body_hash, "spa:original_body_changed")
        cases["two_stage_spa_age_progression"] = {
            "status": "passed_control_plane_fixture_only",
            "stage_one_message": stage_one_message,
            "blocked_stage_two_message": blocked_message,
            "stage_two_message": stage_two_message,
            "stage_one_route": stage_one_route,
            "blocked_stage_two_status": blocked_stage_two["status"],
            "stage_two_contract": stage_two_contract,
            "event_chain": spa_chain,
            "original_adjustment_byte_preserved": True,
            "original_body_sha256_before": original_body_hash,
            "original_body_sha256_after": sha256_file(original_body),
            "stage_one_fixture_path": relative(stage_one_fixture),
            "stage_one_fixture_sha256": sha256_file(stage_one_fixture),
            "fixture_truth_note": "No age-progressed body or anatomy was generated; the fixture tests gate behavior only.",
        }

    result: dict[str, Any] = {
        "schema_version": 1,
        "acceptance_id": "avatar_builder_temporary_body_conversational_acceptance_attempt_01",
        "started_at": started_at,
        "finished_at": utc_now(),
        "status": "passed_control_plane_only",
        "scope": {
            "storage": "append_only_private_sandbox",
            "live_avatar_mutation": False,
            "blender_invoked": False,
            "gpu_invoked": False,
            "camera_invoked": False,
            "microphone_invoked": False,
            "body_geometry_generated": False,
            "visual_approval_claimed": False,
            "runtime_activation": False,
            "assignment": False,
            "publication": False,
        },
        "cases": cases,
        "aggregate_gates": {
            "two_owner_confirmed_adults_route_to_gendered_adult_lanes": "passed",
            "offline_explicit_owner_authority_trusted": "passed",
            "peter_wrong_class_preserved_and_replaced_append_only": "passed",
            "isolated_high_school_context_cannot_override_later_adult_continuity": "passed",
            "marinette_non_adult_body_remains_doll_safe": "passed",
            "detachable_hair_correction_is_component_isolated": "passed",
            "spa_stage_one_blocks_adult_anatomy": "passed",
            "spa_stage_two_requires_exact_adult_classification_and_resident_choice": "passed_with_control_plane_fixture",
        },
        "remaining_required_work": [
            "Wait for Kira and Biological Robert private owner-review body work to complete before any monitored temporary body generation.",
            "Run real Blender body generation only after that release boundary; bind real meshes, movement evidence, hashes, and private review renders.",
            "No temporary candidate in this acceptance is visually approved, active, assigned, published, or runtime-ready.",
        ],
    }
    result_path = output_dir / "ACCEPTANCE_RESULT.json"
    write_json(result_path, result)
    checkpoint = output_dir / "CHECKPOINT.md"
    checkpoint.write_text(
        "# Avatar Builder Temporary-Body Conversational Acceptance — Attempt 01\n\n"
        f"Status: `{result['status']}`\n\n"
        "This append-only run used private control-plane fixtures only. It invoked no Blender, GPU, "
        "camera, microphone, live avatar, production body worker, activation, assignment, publication, "
        "or visual-approval path.\n\n"
        "Passed: two explicit confirmed-adult temporary candidates reached `adult_male` and "
        "`adult_female`; offline Robert authority was retained; Peter's deliberately wrong non-adult "
        "fixture remained byte-identical while the next route became an append-only adult-male replacement; "
        "earlier high-school reference wording did not override the requested later continuity; Marinette "
        "remained non-adult doll-safe; hair remained detachable and isolated; and the two-stage spa gate "
        "kept anatomy out of Stage 1 and required exact confirmed-adult/resident-choice evidence for Stage 2.\n\n"
        "Remaining boundary: actual temporary-body generation must wait until Kira and Biological Robert "
        "owner-review body work is complete. This run is not body generation or body approval.\n\n"
        f"Primary evidence: `{relative(result_path)}`\n",
        encoding="utf-8",
    )
    files = sorted(path for path in output_dir.rglob("*") if path.is_file())
    manifest = {
        "schema_version": 1,
        "created_at": utc_now(),
        "root": relative(output_dir),
        "append_only_attempt": "attempt_01",
        "file_count_excluding_manifest": len(files),
        "files": [
            {
                "path": relative(path),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in files
        ],
        "rollback": (
            "No production state was changed. To disregard this acceptance, leave attempt_01 preserved and "
            "do not consume its route fixtures; do not delete or rewrite append-only evidence."
        ),
    }
    write_json(output_dir / "MANIFEST.json", manifest)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = run_acceptance(args.output_dir)
    print(json.dumps({"status": result["status"], "output_dir": relative(args.output_dir)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
