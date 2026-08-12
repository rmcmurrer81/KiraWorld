"""Exact, private construction authority for the two Robert avatar targets.

This module does not read reference pixels, author geometry, approve likeness,
or activate a body.  It prevents the new construction authority from leaking
to Kira, Lisa, another TemporaryAI person, or a public/runtime export.
"""

from __future__ import annotations

from typing import Any


AUTHORIZED_TARGETS = frozenset(
    {"BIOLOGICAL_ROBERT_AVATAR", "SYNTHETIC_ROBERT_TWIN_BODY"}
)
REQUIRED_INITIAL_STATUS = "STAGED — PRIVATE OWNER REVIEW REQUIRED — NOT ACTIVATED"


def evaluate_dual_robert_construction_request(request: dict[str, Any] | None) -> dict[str, Any]:
    data = request if isinstance(request, dict) else {}
    target = str(data.get("target_id") or "").strip()
    failures: list[str] = []
    if target not in AUTHORIZED_TARGETS:
        failures.append("target_not_in_exact_dual_robert_allowlist")
    if data.get("confirmed_adult") is not True:
        failures.append("confirmed_adult_required")
    if data.get("private_reference_access") is not True:
        failures.append("private_reference_access_not_explicit")
    if data.get("ordinary_review_route") != "clothed_only":
        failures.append("ordinary_review_must_be_clothed_only")
    if data.get("copy_private_sources") is not False:
        failures.append("private_source_copying_must_be_disabled")
    if data.get("public_export") is not False:
        failures.append("public_export_must_be_disabled")
    if data.get("runtime_activation") is not False:
        failures.append("runtime_activation_must_be_disabled")
    if data.get("use_other_person_identity_surface") is not False:
        failures.append("other_person_identity_surface_use_must_be_disabled")
    return {
        "schema_version": 1,
        "target_id": target,
        "authorized_for_private_construction": not failures,
        "status": "authorized_private_construction" if not failures else "blocked",
        "initial_candidate_status": REQUIRED_INITIAL_STATUS,
        "runtime_activation_allowed": False,
        "public_export_allowed": False,
        "failures": failures,
        "truth_note": (
            "Authority permits a private build attempt only. It does not prove that "
            "Robert-specific geometry, adult anatomy, likeness, rigging, cloth, or "
            "owner-reviewable output exists."
        ),
    }


def final_assets_are_separate(
    biological: dict[str, Any] | None,
    synthetic: dict[str, Any] | None,
) -> dict[str, Any]:
    first = biological if isinstance(biological, dict) else {}
    second = synthetic if isinstance(synthetic, dict) else {}
    failures: list[str] = []
    if first.get("target_id") != "BIOLOGICAL_ROBERT_AVATAR":
        failures.append("biological_target_identity_mismatch")
    if second.get("target_id") != "SYNTHETIC_ROBERT_TWIN_BODY":
        failures.append("synthetic_target_identity_mismatch")
    for field in ("body_path", "body_sha256", "component_manifest_path", "rig_manifest_path"):
        left = str(first.get(field) or "").strip()
        right = str(second.get(field) or "").strip()
        if not left or not right:
            failures.append(f"missing_{field}")
        elif left == right:
            failures.append(f"shared_mutable_{field}")
    return {
        "separate_final_assets": not failures,
        "runtime_activation_allowed": False,
        "failures": failures,
    }
