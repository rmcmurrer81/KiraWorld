"""Fail-closed V3 canon contract for the exact Marinette review candidate.

This module is deliberately narrow.  It does not activate a person, contact a
model, read sensors, or grant a runtime capability.  It binds one immutable
manifest to one exact candidate and constructs the only prompt context that a
future, separately audited text-only route may use.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_ID = "ladybug_marinette_expanded_smoke"
DISPLAY_NAME = "Marinette / Ladybug"
ROLE_TITLE = "Fashion student and Ladybug"
AI_TYPE = "canon_reconstruction_temp_ai"
MATURITY = "non_adult_doll_safe"
MANIFEST_RELATIVE_PATH = (
    "Data/temporary_ai_source_packs/"
    "marinette_current_canon_contract_manifest_v3.json"
)
PINNED_MANIFEST_SHA256 = (
    "c6589dd3bac6f07e793b031a9edf7ad3afdc879b7c51bbaf39fcb020611c1c39"
)
PINNED_V2_REJECTION_AUDIT_SHA256 = (
    "85daf6cb24120ac809ba079f631a228ec66d3c0a1a086ee21d2c7d6125f833b2"
)

_HEX64 = re.compile(r"[0-9a-f]{64}")
_EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
_EXPECTED_V3_PATHS = {
    "v3_route_profile": "TemporaryAI/candidates/ladybug_marinette_expanded_smoke/temporary_ai_profile_v3.json",
    "v3_source_pack": "Data/temporary_ai_source_packs/temporary_ai_source_pack_ladybug_marinette_current_canon_v3.json",
    "v3_source_review": "TemporaryAI/candidates/ladybug_marinette_expanded_smoke/source_grounding_review_v3.json",
    "v3_source_registry": "Data/temporary_ai_source_packs/marinette_current_canon_source_registry_v3.json",
    "v3_official_content_evidence": "Data/temporary_ai_source_packs/marinette_current_canon_official_evidence_v3.json",
    "v3_runtime_policy": "Data/temporary_ai_source_packs/marinette_current_canon_runtime_policy_v3.json",
}
_EXPECTED_SELECTOR_PATH = (
    "TemporaryAI/candidates/ladybug_marinette_expanded_smoke/temporary_ai_profile.json"
)
_EXPECTED_OFFICIAL_SOURCES = {
    "official_miraculous_ladybug_character_profile": {
        "authority_kind": "official_publisher_primary",
        "source_rank": 1,
        "url": "https://www.miraculousladybug.com/characters/ladybug/",
        "allowed_claim_ids": ["identity_01", "identity_02"],
    },
    "official_miraculous_series_page": {
        "authority_kind": "official_publisher_primary",
        "source_rank": 1,
        "url": "https://www.miraculousladybug.com/about-the-tv-series",
        "allowed_claim_ids": ["identity_03"],
    },
    "official_miraculous_seasons_6_7_acquisition": {
        "authority_kind": "official_publisher_primary",
        "source_rank": 1,
        "url": "https://www.miraculousladybug.com/disney-branded-television-acquires-seasons-6-and-7/",
        "allowed_claim_ids": ["season6_01"],
    },
    "official_miraculous_s6_new_episodes_20260226": {
        "authority_kind": "official_publisher_primary",
        "source_rank": 1,
        "url": "https://www.miraculousladybug.com/miraculous-season-6-new-episodes/",
        "allowed_claim_ids": ["season6_02"],
    },
    "official_disneyplus_us_s6_batch_20250702": {
        "authority_kind": "official_streamer_primary",
        "source_rank": 1,
        "url": "https://press.disneyplus.com/news/next-on-disney-plus-july-2025",
        "allowed_claim_ids": ["season6_04"],
    },
    "official_disneyplus_us_s6_future_batch_20260826": {
        "authority_kind": "official_streamer_primary_future_listing",
        "source_rank": 1,
        "url": "https://press.disneyplus.com/news/next-on-disney-plus-august-2026",
        "allowed_claim_ids": ["season6_05"],
    },
    "official_tf1_mutable_schedule_no_claim": {
        "authority_kind": "official_broadcaster_mutable_no_claim",
        "source_rank": 1,
        "url": "https://help.tf1.fr/hc/fr/articles/25544423203346-Vous-souhaitez-conna%C3%AEtre-la-diffusion-des-prochains-%C3%A9pisodes-de-Miraculous-les-aventures-de-Ladybug-et-Chat-Noir-sur-TF1",
        "allowed_claim_ids": [],
        "claim_policy": "no_canon_claim",
    },
}
_EXPECTED_LOCAL_SOURCES = {
    "local_s6_episode_01_media": {
        "authority_kind": "local_episode_media_unwitnessed",
        "source_rank": 2,
        "path": "Data/library/tv_shows/miraculous_ladybug/miraculous_season_6_episode_01.mp4",
        "sha256": "0800652a5ee9648ea730b1a52d6fda4c8d1be1c3f70f553c67cec6f294187985",
        "allowed_claim_ids": [],
    },
    "local_s6_long_bible_2023": {
        "authority_kind": "production_planning_not_released_canon",
        "source_rank": 3,
        "path": "Data/library/scripts/miraculous_ladybug/season_6/723837069-MLB-S6-Synopsis.pdf",
        "sha256": "dc04a4544b4a906290a07a4d063878da8aa730384c93664081389596a40c4abc",
        "allowed_claim_ids": [],
    },
    "local_s6_short_bible_2022": {
        "authority_kind": "production_planning_not_released_canon",
        "source_rank": 3,
        "path": "Data/library/scripts/miraculous_ladybug/season_6/724384835-Miraculous-Ladybug-SEASON-6-BIBLE.pdf",
        "sha256": "3296e5bd14eb79524e0042a824c4ab0da1224d08d149d4b023156317a624b4b6",
        "allowed_claim_ids": [],
    },
}
_EXCLUDED_TOP_LEVEL = {
    "creation_request": {},
    "activation_plan": {},
    "online_research_summary": {},
    "source_research_queue": {},
    "reliable_source_pack": {},
    "attached_workspaces": [],
    "recent_chat_records": [],
    "project_continuity": {},
    "canon_fact_sheet": {},
    "legacy_repair_notes_with_false_claim_text": [],
}
_FORBIDDEN_PROFILE_FIELDS = {
    "canon_fact_sheet",
    "attached_workspaces",
    "repair_notes",
    "recent_chat_records",
    "project_continuity",
}


class MarinetteCanonContractV3Error(RuntimeError):
    """Raised whenever the exact V3 contract cannot be proven."""


def _fail(reason: str) -> None:
    raise MarinetteCanonContractV3Error(reason)


def _confined_file(relative_path: str) -> Path:
    value = str(relative_path or "").replace("\\", "/")
    path = Path(value)
    if not value or path.is_absolute() or value != path.as_posix():
        _fail("contract_path_not_exact_project_relative")
    try:
        root = PROJECT_ROOT.resolve(strict=True)
        resolved = (PROJECT_ROOT / path).resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError):
        _fail("contract_path_missing_or_outside_project")
    if not resolved.is_file():
        _fail("contract_path_not_file")
    return resolved


def _read_hashed(
    relative_path: str,
    expected_sha256: str,
    *,
    retain_content: bool = True,
) -> bytes:
    expected = str(expected_sha256 or "").lower()
    if not _HEX64.fullmatch(expected):
        _fail("contract_sha256_invalid")
    path = _confined_file(relative_path)
    digest = hashlib.sha256()
    chunks: list[bytes] = []
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
            if retain_content:
                chunks.append(block)
    if digest.hexdigest() != expected:
        _fail("contract_member_hash_mismatch:" + str(relative_path))
    return b"".join(chunks)


def _json_bytes(raw: bytes, role: str) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        _fail("contract_json_invalid:" + role)
    if not isinstance(value, dict):
        _fail("contract_json_not_object:" + role)
    return value


def _member_map(rows: Any, label: str) -> dict[str, dict[str, Any]]:
    if not isinstance(rows, list) or not rows:
        _fail(label + "_missing")
    result: dict[str, dict[str, Any]] = {}
    paths: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            _fail(label + "_entry_invalid")
        role = str(row.get("role") or "")
        path = str(row.get("path") or "").replace("\\", "/")
        if not role or role in result or not path or path in paths:
            _fail(label + "_entry_duplicate_or_missing")
        result[role] = row
        paths.add(path)
    return result


def _core_claims(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list) or not rows:
        _fail("contract_claims_missing")
    result: list[dict[str, Any]] = []
    ids: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            _fail("contract_claim_invalid")
        claim_id = str(row.get("claim_id") or "")
        statement = str(row.get("statement") or "")
        classification = str(row.get("classification") or "")
        source_ids = row.get("source_ids")
        if (
            not claim_id
            or claim_id in ids
            or not statement
            or not classification
            or not isinstance(source_ids, list)
            or not source_ids
            or len(source_ids) != len(set(map(str, source_ids)))
        ):
            _fail("contract_claim_invalid_or_duplicate")
        ids.add(claim_id)
        result.append(
            {
                "claim_id": claim_id,
                "classification": classification,
                "statement": statement,
                "source_ids": list(map(str, source_ids)),
            }
        )
    return result


def _core_unknowns(rows: Any) -> list[dict[str, str]]:
    if not isinstance(rows, list) or not rows:
        _fail("contract_unknowns_missing")
    result: list[dict[str, str]] = []
    ids: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            _fail("contract_unknown_invalid")
        unknown_id = str(row.get("unknown_id") or "")
        statement = str(row.get("statement") or "")
        if not unknown_id or unknown_id in ids or not statement:
            _fail("contract_unknown_invalid_or_duplicate")
        ids.add(unknown_id)
        result.append({"unknown_id": unknown_id, "statement": statement})
    return result


def _validate_profile(
    selector: dict[str, Any],
    profile: dict[str, Any],
    pack_row: dict[str, Any],
    review_row: dict[str, Any],
    registry_row: dict[str, Any],
    policy_row: dict[str, Any],
) -> None:
    for source in (selector, profile):
        if source.get("candidate_id") != CANDIDATE_ID:
            _fail("profile_candidate_id_mismatch")
        if source.get("display_name") != DISPLAY_NAME:
            _fail("profile_display_name_mismatch")
        if source.get("role_title") != ROLE_TITLE:
            _fail("profile_role_title_mismatch")
        if source.get("ai_type") != AI_TYPE:
            _fail("profile_ai_type_mismatch")
        maturity = source.get("maturity_policy")
        if not isinstance(maturity, dict):
            _fail("profile_maturity_policy_missing")
        if maturity.get("classification") != MATURITY:
            _fail("profile_maturity_mismatch")
        if maturity.get("adult_anatomy_allowed") is not False:
            _fail("profile_adult_anatomy_not_denied")
        if maturity.get("adult_curriculum_allowed") is not False:
            _fail("profile_adult_curriculum_not_denied")
        if maturity.get("body_activation_authorized") is not False:
            _fail("profile_body_not_denied")
    expected_bindings = {
        "source_pack": (pack_row["path"], pack_row["sha256"]),
        "source_grounding_review": (review_row["path"], review_row["sha256"]),
        "source_registry": (registry_row["path"], registry_row["sha256"]),
        "runtime_policy": (policy_row["path"], policy_row["sha256"]),
    }
    for field, (path, digest) in expected_bindings.items():
        if profile.get(field) != path or profile.get(field + "_sha256") != digest:
            _fail("profile_declared_binding_mismatch:" + field)
    identity = profile.get("identity")
    if not isinstance(identity, dict) or identity.get("contract_version") != 3:
        _fail("profile_contract_version_mismatch")
    if identity.get("requires_fail_closed_source_review") is not True:
        _fail("profile_fail_closed_flag_missing")
    activation = profile.get("activation_policy")
    if not isinstance(activation, dict):
        _fail("profile_activation_policy_missing")
    if activation.get("bounded_text_only_conversation_allowed") is not False:
        _fail("profile_owner_text_not_blocked_pending_audit")
    if activation.get("bounded_voice_conversation_allowed") is not False:
        _fail("profile_voice_not_denied")
    if activation.get("body_world_life_loop_allowed") is not False:
        _fail("profile_world_not_denied")
    if any(field in profile for field in _FORBIDDEN_PROFILE_FIELDS):
        _fail("profile_contains_unbound_prompt_field")


def _validate_semantics(manifest: dict[str, Any], artifacts: dict[str, dict[str, Any]]) -> None:
    if manifest.get("schema_version") != 1:
        _fail("manifest_schema_mismatch")
    if manifest.get("manifest_id") != "marinette_current_canon_contract_manifest_v3":
        _fail("manifest_id_mismatch")
    if manifest.get("candidate_id") != CANDIDATE_ID or manifest.get("display_name") != DISPLAY_NAME:
        _fail("manifest_identity_mismatch")
    if manifest.get("contract_version") != 3:
        _fail("manifest_version_mismatch")
    predecessor = manifest.get("predecessor_rejection_audit")
    if not isinstance(predecessor, dict) or predecessor.get("sha256") != PINNED_V2_REJECTION_AUDIT_SHA256:
        _fail("manifest_predecessor_audit_mismatch")

    profile = artifacts["v3_route_profile"]
    pack = artifacts["v3_source_pack"]
    review = artifacts["v3_source_review"]
    registry = artifacts["v3_source_registry"]
    evidence = artifacts["v3_official_content_evidence"]
    policy = artifacts["v3_runtime_policy"]
    selector = artifacts["v2_selector_profile"]
    v3_rows = _member_map(manifest.get("v3_contract_members"), "v3_contract_members")
    _validate_profile(
        selector,
        profile,
        v3_rows["v3_source_pack"],
        v3_rows["v3_source_review"],
        v3_rows["v3_source_registry"],
        v3_rows["v3_runtime_policy"],
    )

    identity = policy.get("identity_contract")
    expected_identity = {
        "folder_id": CANDIDATE_ID,
        "profile_candidate_id": CANDIDATE_ID,
        "display_name": DISPLAY_NAME,
        "role_title": ROLE_TITLE,
        "ai_type": AI_TYPE,
        "selected_continuity": profile.get("selected_continuity"),
        "maturity_classification": MATURITY,
        "adult_anatomy_allowed": False,
        "adult_curriculum_allowed": False,
        "private_inactive": True,
    }
    if identity != expected_identity:
        _fail("runtime_identity_contract_mismatch")
    for source in (pack, review):
        if source.get("candidate_id") != CANDIDATE_ID:
            _fail("artifact_candidate_id_mismatch")
    if pack.get("display_name") != DISPLAY_NAME:
        _fail("pack_display_name_mismatch")
    binding = review.get("identity_binding")
    if not isinstance(binding, dict):
        _fail("review_identity_binding_missing")
    expected_review_identity = {
        "display_name": DISPLAY_NAME,
        "role_title": ROLE_TITLE,
        "ai_type": AI_TYPE,
        "selected_continuity": profile.get("selected_continuity"),
        "maturity_lane": MATURITY,
        "adult_anatomy_allowed": False,
        "adult_curriculum_allowed": False,
        "private_inactive": True,
    }
    for key, value in expected_review_identity.items():
        if binding.get(key) != value:
            _fail("review_identity_binding_mismatch:" + key)
    if binding.get("required_source_pack_path") != v3_rows["v3_source_pack"]["path"]:
        _fail("review_pack_path_mismatch")
    if binding.get("required_source_pack_sha256") != v3_rows["v3_source_pack"]["sha256"]:
        _fail("review_pack_hash_mismatch")

    policy_claims = _core_claims(policy.get("claims"))
    if _core_claims(pack.get("source_bound_claims")) != policy_claims:
        _fail("pack_policy_claim_mismatch")
    if _core_claims(review.get("canon_anchors")) != policy_claims:
        _fail("review_policy_claim_mismatch")
    policy_unknowns = _core_unknowns(policy.get("required_unknowns"))
    if _core_unknowns(pack.get("explicit_unknowns")) != policy_unknowns:
        _fail("pack_policy_unknown_mismatch")
    if _core_unknowns(review.get("required_unknowns")) != policy_unknowns:
        _fail("review_policy_unknown_mismatch")
    if {row["unknown_id"] for row in policy_unknowns} != {
        "season6_complete_order",
        "season6_finale",
        "local_episode_01_content",
        "unverified_names_and_history",
    }:
        _fail("required_unknown_set_mismatch")
    if any(row["claim_id"] == "season6_03" for row in policy_claims):
        _fail("mutable_tf1_claim_not_removed")

    if registry.get("candidate_id") != CANDIDATE_ID:
        _fail("registry_candidate_id_mismatch")
    if registry.get("allowed_official_hosts") != ["www.miraculousladybug.com", "press.disneyplus.com"]:
        _fail("registry_official_host_allowlist_mismatch")
    sources = registry.get("sources")
    if not isinstance(sources, list) or len(sources) != 10:
        _fail("registry_sources_missing")
    source_map: dict[str, dict[str, Any]] = {}
    for source in sources:
        if not isinstance(source, dict):
            _fail("registry_source_invalid")
        source_id = str(source.get("source_id") or "")
        if not source_id or source_id in source_map:
            _fail("registry_source_id_invalid_or_duplicate")
        source_map[source_id] = source
    expected_sources = {**_EXPECTED_OFFICIAL_SOURCES, **_EXPECTED_LOCAL_SOURCES}
    if set(source_map) != set(expected_sources):
        _fail("registry_source_set_mismatch")
    for source_id, expected in expected_sources.items():
        source = source_map[source_id]
        for key, value in expected.items():
            if source.get(key) != value:
                _fail("registry_source_binding_mismatch:" + source_id + ":" + key)
        if source_id in _EXPECTED_OFFICIAL_SOURCES:
            parsed = urlsplit(str(source.get("url") or ""))
            if parsed.scheme != "https":
                _fail("registry_source_url_not_allowed:" + source_id)
            if expected["allowed_claim_ids"] and parsed.hostname not in registry["allowed_official_hosts"]:
                _fail("registry_claim_source_host_not_allowed:" + source_id)
            if parsed.username or parsed.password or parsed.fragment:
                _fail("registry_source_url_ambiguous:" + source_id)

    records = evidence.get("records")
    if not isinstance(records, list):
        _fail("official_evidence_records_missing")
    evidence_map: dict[str, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict):
            _fail("official_evidence_record_invalid")
        source_id = str(record.get("source_id") or "")
        if not source_id or source_id in evidence_map:
            _fail("official_evidence_id_invalid_or_duplicate")
        evidence_map[source_id] = record
    if set(evidence_map) != set(_EXPECTED_OFFICIAL_SOURCES):
        _fail("official_evidence_source_set_mismatch")
    for source_id, expected in _EXPECTED_OFFICIAL_SOURCES.items():
        record = evidence_map[source_id]
        if record.get("url") != expected["url"]:
            _fail("official_evidence_url_mismatch:" + source_id)
        excerpt = str(record.get("verbatim_excerpt") or "")
        if hashlib.sha256(excerpt.encode("utf-8")).hexdigest() != record.get("excerpt_sha256"):
            _fail("official_evidence_excerpt_hash_mismatch:" + source_id)
        if expected["allowed_claim_ids"]:
            if not excerpt or not isinstance(record.get("bounded_support"), list) or not record["bounded_support"]:
                _fail("official_evidence_relevance_missing:" + source_id)
        else:
            if excerpt or record.get("excerpt_sha256") != _EMPTY_SHA256 or record.get("bounded_support") != []:
                _fail("mutable_tf1_not_honest_no_claim")
            if record.get("claim_policy") != "no_canon_claim":
                _fail("mutable_tf1_claim_policy_mismatch")
    for claim in policy_claims:
        for source_id in claim["source_ids"]:
            source = source_map.get(source_id)
            if source is None or claim["claim_id"] not in source.get("allowed_claim_ids", []):
                _fail("claim_not_relevant_to_registered_source:" + claim["claim_id"])
            if source.get("source_rank") != 1 or source_id not in _EXPECTED_OFFICIAL_SOURCES:
                _fail("claim_uses_non_primary_or_unregistered_source:" + claim["claim_id"])
            if not evidence_map[source_id].get("bounded_support"):
                _fail("claim_source_has_no_content_support:" + claim["claim_id"])
    if pack.get("registered_source_ids") != list(source_map):
        _fail("pack_registry_membership_mismatch")
    no_claim_ids = {
        str(row.get("source_id") or "")
        for row in pack.get("no_claim_sources", [])
        if isinstance(row, dict)
    }
    if no_claim_ids != {
        "official_tf1_mutable_schedule_no_claim",
        "local_s6_episode_01_media",
        "local_s6_long_bible_2023",
        "local_s6_short_bible_2022",
    }:
        _fail("pack_no_claim_source_set_mismatch")

    runtime_scope = policy.get("runtime_scope")
    if not isinstance(runtime_scope, dict):
        _fail("runtime_scope_missing")
    required_false = {
        "bounded_owner_text_execution_allowed",
        "voice_allowed",
        "sensory_lease_allowed",
        "initiative_session_allowed",
        "person_event_transport_allowed",
        "life_loop_allowed",
        "autonomous_or_long_running_allowed",
        "movement_intent_parse_or_persist_allowed",
        "body_allowed",
        "world_allowed",
    }
    if runtime_scope.get("contract_integrity_static_audit_allowed") is not True:
        _fail("static_audit_not_enabled")
    if runtime_scope.get("fresh_independent_audit_required") is not True:
        _fail("fresh_audit_requirement_missing")
    if any(runtime_scope.get(key) is not False for key in required_false):
        _fail("runtime_scope_capability_not_denied")
    text_review = review.get("text_conversation_review")
    activation = review.get("activation")
    if not isinstance(text_review, dict) or not isinstance(activation, dict):
        _fail("review_execution_scope_missing")
    if text_review.get("bounded_owner_text_conversation_allowed") is not False:
        _fail("review_owner_text_not_blocked")
    if activation.get("runtime_activation_allowed") is not False:
        _fail("review_runtime_not_blocked")
    if activation.get("bounded_owner_text_probe_allowed") is not False:
        _fail("review_probe_not_blocked")
    if activation.get("candidate_must_remain_inactive") is not True:
        _fail("review_inactive_requirement_missing")


def _load_contract() -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    raw_manifest = _read_hashed(MANIFEST_RELATIVE_PATH, PINNED_MANIFEST_SHA256)
    manifest = _json_bytes(raw_manifest, "manifest")
    v3_rows = _member_map(manifest.get("v3_contract_members"), "v3_contract_members")
    if set(v3_rows) != set(_EXPECTED_V3_PATHS):
        _fail("v3_contract_role_set_mismatch")
    for role, expected_path in _EXPECTED_V3_PATHS.items():
        if v3_rows[role].get("path") != expected_path:
            _fail("v3_contract_path_mismatch:" + role)
    v2_rows = _member_map(manifest.get("protected_v2_predecessors"), "protected_v2_predecessors")
    if v2_rows.get("v2_selector_profile", {}).get("path") != _EXPECTED_SELECTOR_PATH:
        _fail("v2_selector_path_mismatch")
    predecessor = manifest.get("predecessor_rejection_audit")
    if not isinstance(predecessor, dict):
        _fail("predecessor_audit_missing")
    _read_hashed(
        str(predecessor.get("path") or ""),
        str(predecessor.get("sha256") or ""),
        retain_content=False,
    )

    artifacts: dict[str, dict[str, Any]] = {}
    for role, row in {**v2_rows, **v3_rows}.items():
        is_json = str(row.get("path") or "").lower().endswith(".json")
        raw = _read_hashed(
            str(row.get("path") or ""),
            str(row.get("sha256") or ""),
            retain_content=is_json,
        )
        if is_json:
            artifacts[role] = _json_bytes(raw, role)
    local_rows = manifest.get("local_no_claim_evidence")
    if not isinstance(local_rows, list) or len(local_rows) != 3:
        _fail("local_no_claim_manifest_missing")
    local_ids: set[str] = set()
    for row in local_rows:
        if not isinstance(row, dict):
            _fail("local_no_claim_manifest_invalid")
        source_id = str(row.get("source_id") or "")
        if not source_id or source_id in local_ids or source_id not in _EXPECTED_LOCAL_SOURCES:
            _fail("local_no_claim_manifest_id_invalid")
        expected = _EXPECTED_LOCAL_SOURCES[source_id]
        if row.get("path") != expected["path"] or row.get("sha256") != expected["sha256"]:
            _fail("local_no_claim_manifest_binding_mismatch:" + source_id)
        _read_hashed(row["path"], row["sha256"], retain_content=False)
        local_ids.add(source_id)
    if local_ids != set(_EXPECTED_LOCAL_SOURCES):
        _fail("local_no_claim_manifest_set_mismatch")
    _validate_semantics(manifest, artifacts)
    return manifest, artifacts


def _sanitized_candidate(
    artifacts: dict[str, dict[str, Any]],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    rows = _member_map(manifest["v3_contract_members"], "v3_contract_members")
    candidate: dict[str, Any] = {
        "candidate_id": CANDIDATE_ID,
        "candidate_folder": "TemporaryAI/candidates/" + CANDIDATE_ID,
        "profile": copy.deepcopy(artifacts["v3_route_profile"]),
        "source_pack": copy.deepcopy(artifacts["v3_source_pack"]),
        "source_pack_configured_path": rows["v3_source_pack"]["path"],
        "source_pack_sha256": rows["v3_source_pack"]["sha256"],
        "source_pack_route_failures": [],
        "source_grounding_review": copy.deepcopy(artifacts["v3_source_review"]),
    }
    candidate.update(copy.deepcopy(_EXCLUDED_TOP_LEVEL))
    return candidate


def is_strict_marinette_v3_candidate(candidate_or_id: Any) -> bool:
    """Recognize the exact folder ID for deny-path handling, even before load."""

    if isinstance(candidate_or_id, dict):
        candidate_or_id = candidate_or_id.get("candidate_id")
    return str(candidate_or_id or "") == CANDIDATE_ID


def bind_loaded_candidate(base_candidate: dict[str, Any]) -> dict[str, Any]:
    """Replace the legacy loader result with a freshly verified V3 snapshot."""

    if not is_strict_marinette_v3_candidate(base_candidate):
        return base_candidate
    manifest, artifacts = _load_contract()
    if base_candidate.get("candidate_id") != CANDIDATE_ID:
        _fail("loaded_candidate_id_mismatch")
    if base_candidate.get("candidate_folder") != "TemporaryAI/candidates/" + CANDIDATE_ID:
        _fail("loaded_candidate_folder_mismatch")
    if base_candidate.get("profile") != artifacts["v2_selector_profile"]:
        _fail("loaded_selector_profile_not_exact")
    return _sanitized_candidate(artifacts, manifest)


def validate_candidate_snapshot(candidate: dict[str, Any]) -> None:
    """Reject post-load mutation and every excluded context channel."""

    if not is_strict_marinette_v3_candidate(candidate):
        _fail("not_exact_marinette_v3_candidate")
    manifest, artifacts = _load_contract()
    expected = _sanitized_candidate(artifacts, manifest)
    if set(candidate) != set(expected):
        _fail("candidate_snapshot_key_set_mismatch")
    for key, expected_value in expected.items():
        if candidate.get(key) != expected_value:
            _fail("candidate_snapshot_mismatch:" + key)


def prepare_prompt_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    """Return a fresh sanitized snapshot after rejecting in-memory drift."""

    validate_candidate_snapshot(candidate)
    manifest, artifacts = _load_contract()
    return _sanitized_candidate(artifacts, manifest)


def static_contract_readiness(candidate: dict[str, Any] | None = None) -> tuple[bool, list[str]]:
    try:
        _load_contract()
        if candidate is not None:
            validate_candidate_snapshot(candidate)
    except MarinetteCanonContractV3Error as exc:
        return False, [str(exc)]
    return True, []


def owner_text_execution_readiness(candidate: dict[str, Any]) -> tuple[bool, list[str]]:
    ready, reasons = static_contract_readiness(candidate)
    if not ready:
        return False, reasons
    return False, ["fresh_independent_v3_audit_required"]


def strict_runtime_scope(candidate_or_id: Any) -> dict[str, Any]:
    if not is_strict_marinette_v3_candidate(candidate_or_id):
        return {}
    _manifest, artifacts = _load_contract()
    return copy.deepcopy(artifacts["v3_runtime_policy"]["runtime_scope"])


def strict_profile(candidate_or_id: Any) -> dict[str, Any]:
    if not is_strict_marinette_v3_candidate(candidate_or_id):
        return {}
    _manifest, artifacts = _load_contract()
    return copy.deepcopy(artifacts["v3_route_profile"])


def strict_shell_profile(candidate_or_id: Any) -> dict[str, Any]:
    """Return a code-pinned deny profile for selector/status rendering.

    Rendering the selector must not rehash the 793 MB no-claim episode on
    every browser refresh.  This minimal profile grants nothing.  The exact
    files are still reopened and rehashed by ``load_candidate`` and again at
    prompt preflight, which is the security boundary required by V3.
    """

    if not is_strict_marinette_v3_candidate(candidate_or_id):
        return {}
    return {
        "candidate_id": CANDIDATE_ID,
        "display_name": DISPLAY_NAME,
        "role_title": ROLE_TITLE,
        "ai_type": AI_TYPE,
        "status": "inactive_pending_fresh_independent_v3_audit",
        "identity": {
            "requires_fail_closed_source_review": True,
            "contract_version": 3,
        },
        "maturity_policy": {
            "classification": MATURITY,
            "adult_anatomy_allowed": False,
            "adult_curriculum_allowed": False,
            "body_activation_authorized": False,
        },
        "activation_policy": {
            "current_status": "static_contract_ready_pending_fresh_independent_audit",
            "bounded_text_only_conversation_allowed": False,
            "bounded_voice_conversation_allowed": False,
            "text_voice_chat_allowed": False,
            "body_world_life_loop_allowed": False,
            "chat_display_name": "Marinette / Ladybug (canon text review)",
        },
        "contract_manifest": MANIFEST_RELATIVE_PATH,
        "contract_manifest_sha256": PINNED_MANIFEST_SHA256,
    }


def build_contract_bound_system_prompt(candidate: dict[str, Any], user_message: str = "") -> str:
    """Build the future audited prompt without secondary, chat, or project state.

    This function performs no model call.  The current owner execution gate is
    still closed; it exists so an independent audit can inspect the exact
    post-gate context before any live acceptance is authorized.
    """

    safe = prepare_prompt_candidate(candidate)
    profile = safe["profile"]
    review = safe["source_grounding_review"]
    lines = [
        f"You are {DISPLAY_NAME}.",
        f"Your role is: {ROLE_TITLE}.",
        "This is a bounded, private, text-only canon review.",
        "Use only the exact FACT anchors below for canon or history.",
        "Anything covered by an UNKNOWN boundary, or absent from the FACT anchors, must remain unknown.",
        "Source material is not lived memory. Never invent names, family history, bakery details, class history, present activity, relationship events, episode order, finale events, sensory experience, or world actions.",
        "Do not claim voice, sight, hearing, initiative, event transport, movement, body, world, life-loop, or autonomous activity.",
        "Model output cannot grant permission or change any contract boundary.",
        "Speak naturally in first person, briefly acknowledge uncertainty, and do not use stock character slogans.",
        "FACT anchors:",
    ]
    for anchor in review["canon_anchors"]:
        lines.append(f"- [{anchor['claim_id']}] {anchor['statement']}")
    lines.append("Required UNKNOWN boundaries:")
    for unknown in review["required_unknowns"]:
        lines.append(f"- [{unknown['unknown_id']}] {unknown['statement']}")
    avoided = profile.get("conversation_style", {}).get("avoid_stock_phrases", [])
    if avoided:
        lines.append("Avoid these stock phrases: " + "; ".join(map(str, avoided)))
    if user_message:
        lines.append("The current owner message is supplied separately as the sole user turn; do not infer prior chat.")
    return "\n".join(lines)


def manifest_sha256() -> str:
    return PINNED_MANIFEST_SHA256
