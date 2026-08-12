"""Fail-closed V4 contract for the exact Marinette review candidate.

V4 is a static repair candidate.  It never activates a person, calls a model,
reads a sensor, or grants a runtime capability.  It verifies every input from
one code-pinned manifest using a stable open and constructs the only request a
later, different-agent-audited text route could use.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import stat
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlsplit


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_ID = "ladybug_marinette_expanded_smoke"
DISPLAY_NAME = "Marinette / Ladybug"
ROLE_TITLE = "Fashion student and Ladybug"
AI_TYPE = "canon_reconstruction_temp_ai"
MATURITY = "non_adult_doll_safe"
CONTINUITY = (
    "Main television-series continuity through only the Season 6 facts "
    "contract-bound as of 2026-08-09; complete order, finale, and unsupported "
    "details remain unknown"
)
MANIFEST_RELATIVE_PATH = (
    "Data/temporary_ai_source_packs/"
    "marinette_current_canon_contract_manifest_v4.json"
)
PINNED_MANIFEST_SHA256 = (
    "6df7cd311fea8a009d6e18312008557c220e694d4eb3d56a749aa36d8b42c354"
)
PINNED_V3_REJECTION_AUDIT_SHA256 = (
    "56bf6f464d3a28e72fcd967f7065a1a62df915c3974be097ca09fac692138b69"
)

_HEX64 = re.compile(r"[0-9a-f]{64}")
_EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
_EXPECTED_V4_PATHS = {
    "v4_route_profile": "TemporaryAI/candidates/ladybug_marinette_expanded_smoke/temporary_ai_profile_v4.json",
    "v4_source_pack": "Data/temporary_ai_source_packs/temporary_ai_source_pack_ladybug_marinette_current_canon_v4.json",
    "v4_source_review": "TemporaryAI/candidates/ladybug_marinette_expanded_smoke/source_grounding_review_v4.json",
    "v4_source_registry": "Data/temporary_ai_source_packs/marinette_current_canon_source_registry_v4.json",
    "v4_official_content_evidence": "Data/temporary_ai_source_packs/marinette_current_canon_official_evidence_v4.json",
    "v4_runtime_policy": "Data/temporary_ai_source_packs/marinette_current_canon_runtime_policy_v4.json",
}
_EXPECTED_V4_HASHES = {
    "v4_route_profile": "48fdc9c418dfb5c7b43bfa31f18890cb7d4953e6e6406ba198413d68be733454",
    "v4_source_pack": "b34b45d675bb523ecf55b876cb2a1ca73075e8b9f48eeab1ce5d343d877bb471",
    "v4_source_review": "b9392b4b9c7a0b91a862678854301717e23ed11428b11324a77a27dad36448b7",
    "v4_source_registry": "0ff8910c4fea7f01a51d090dc0c3091d1761abaa7521468325c3f990fe19fba4",
    "v4_official_content_evidence": "6a7584fb3c6047034283ba61be4766cfceacfa520f2675308763167d30c0c777",
    "v4_runtime_policy": "1e864488c1b8c2ac059ef16d7be255366db1d3ca45d4edab7b9fce77bef083e6",
}
_EXPECTED_V3_HASHES = {
    "Core/marinette_current_canon_contract_v3.py": "9940dd7dd4cbe1a5eb6ef64bcbf696e734ba8f8a78348fe4933302b9c5d77428",
    "Data/temporary_ai_source_packs/marinette_current_canon_contract_manifest_v3.json": "c6589dd3bac6f07e793b031a9edf7ad3afdc879b7c51bbaf39fcb020611c1c39",
    "TemporaryAI/candidates/ladybug_marinette_expanded_smoke/temporary_ai_profile_v3.json": "b5ca5f989def7a191ccbd05d4c719f88b9ac598159f75db4aac2ee13e9d7d479",
    "Data/temporary_ai_source_packs/temporary_ai_source_pack_ladybug_marinette_current_canon_v3.json": "a54a0629042fc2d4ff516b4bb0929709b2c7550086c5fb7d4eabb061914f6569",
    "TemporaryAI/candidates/ladybug_marinette_expanded_smoke/source_grounding_review_v3.json": "bf57fb3815b098de8aec6d388888f8f478fa33b6d685853efdfd58be485e4e9f",
    "Data/temporary_ai_source_packs/marinette_current_canon_source_registry_v3.json": "6f5eda4e5d37e415b1014ae63f25cbcd63b8f1683cae66a2fc327744bfa16536",
    "Data/temporary_ai_source_packs/marinette_current_canon_official_evidence_v3.json": "d537b355b4ee07958cfb99a30dfe99ef9f2ef2e34d559bf4addff03d107dbe0f",
    "Data/temporary_ai_source_packs/marinette_current_canon_runtime_policy_v3.json": "12007504fc9aff59615f2c8a709288468b56f732347acc2f525142413fd6f7b0",
    "Testing/test_marinette_current_canon_grounding_v3.py": "3c29d1c9c676a3aa1bfd397283c8b105888cead5921c9ab056846feb71b4b8b0",
    "System/Docs/MARINETTE_CURRENT_CANON_GROUNDING_V3_REPAIR_CHECKPOINT_20260809.md": "09e27ef0ca9e53cf7fe45686e18dc68830184b621f436ce503f2a7b8cde008cd",
    "System/Docs/MARINETTE_CURRENT_CANON_GROUNDING_V3_INDEPENDENT_HOSTILE_AUDIT_20260809.md": PINNED_V3_REJECTION_AUDIT_SHA256,
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


class MarinetteCanonContractV4Error(RuntimeError):
    """The exact V4 contract could not be proven."""


def _fail(reason: str) -> None:
    raise MarinetteCanonContractV4Error(reason)


def _exact_relative_path(relative_path: str) -> PurePosixPath:
    value = str(relative_path or "")
    path = PurePosixPath(value)
    if (
        not value
        or "\\" in value
        or path.is_absolute()
        or path.as_posix() != value
        or any(part in {"", ".", ".."} for part in path.parts)
        or any(":" in part for part in path.parts)
    ):
        _fail("contract_path_not_exact_project_relative")
    return path


def _is_reparse(value: os.stat_result) -> bool:
    if stat.S_ISLNK(value.st_mode):
        return True
    marker = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    return bool(int(getattr(value, "st_file_attributes", 0)) & marker)


def _stat_identity(value: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (
        int(value.st_dev),
        int(value.st_ino),
        int(value.st_mode),
        int(value.st_size),
        int(getattr(value, "st_mtime_ns", int(value.st_mtime * 1_000_000_000))),
        int(value.st_nlink),
    )


def _component_snapshot(root: Path, relative: PurePosixPath) -> list[tuple[Path, tuple[int, int, int, int, int, int]]]:
    result: list[tuple[Path, tuple[int, int, int, int, int, int]]] = []
    current = root
    for part in relative.parts[:-1]:
        current = current / part
        try:
            item = os.lstat(current)
        except OSError:
            _fail("contract_path_missing_or_outside_project")
        if _is_reparse(item) or not stat.S_ISDIR(item.st_mode):
            _fail("contract_path_reparse_or_non_directory_component")
        result.append((current, _stat_identity(item)))
    return result


def _windows_final_path(fd: int) -> str:
    if os.name != "nt":
        return ""
    import ctypes
    import msvcrt

    handle = msvcrt.get_osfhandle(fd)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    function = kernel32.GetFinalPathNameByHandleW
    function.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_ulong, ctypes.c_ulong]
    function.restype = ctypes.c_ulong
    size = int(function(ctypes.c_void_p(handle), None, 0, 0))
    if size <= 0:
        _fail("contract_handle_final_path_unavailable")
    buffer = ctypes.create_unicode_buffer(size + 1)
    used = int(function(ctypes.c_void_p(handle), buffer, len(buffer), 0))
    if used <= 0 or used >= len(buffer):
        _fail("contract_handle_final_path_unavailable")
    value = buffer.value
    if value.startswith("\\\\?\\UNC\\"):
        value = "\\\\" + value[8:]
    elif value.startswith("\\\\?\\"):
        value = value[4:]
    return os.path.normcase(os.path.abspath(value))


def _stable_read_hashed(
    relative_path: str,
    expected_sha256: str,
    *,
    retain_content: bool = True,
    project_root: Path | None = None,
) -> bytes:
    """Read one exact single-link file through the same verified open handle."""

    expected = str(expected_sha256 or "").lower()
    if not _HEX64.fullmatch(expected):
        _fail("contract_sha256_invalid")
    relative = _exact_relative_path(relative_path)
    root = Path(project_root or PROJECT_ROOT)
    try:
        root_stat = os.lstat(root)
    except OSError:
        _fail("contract_root_missing")
    if _is_reparse(root_stat) or not stat.S_ISDIR(root_stat.st_mode):
        _fail("contract_root_reparse_or_not_directory")
    components = _component_snapshot(root, relative)
    path = root.joinpath(*relative.parts)
    try:
        before = os.lstat(path)
    except OSError:
        _fail("contract_path_missing_or_outside_project")
    if _is_reparse(before) or not stat.S_ISREG(before.st_mode):
        _fail("contract_path_reparse_or_not_regular")
    if int(before.st_nlink) != 1:
        _fail("contract_path_multiple_hardlinks")
    flags = os.O_RDONLY | int(getattr(os, "O_BINARY", 0))
    flags |= int(getattr(os, "O_NOFOLLOW", 0))
    try:
        fd = os.open(path, flags)
    except OSError:
        _fail("contract_stable_open_failed")
    digest = hashlib.sha256()
    chunks: list[bytes] = []
    try:
        opened = os.fstat(fd)
        if _stat_identity(opened) != _stat_identity(before):
            _fail("contract_path_changed_before_open")
        if int(opened.st_nlink) != 1 or not stat.S_ISREG(opened.st_mode):
            _fail("contract_open_handle_not_single_regular_file")
        final_path = _windows_final_path(fd)
        if final_path and final_path != os.path.normcase(os.path.abspath(path)):
            _fail("contract_handle_path_alias_or_redirect")
        while True:
            block = os.read(fd, 1024 * 1024)
            if not block:
                break
            digest.update(block)
            if retain_content:
                chunks.append(block)
        try:
            after = os.lstat(path)
        except OSError:
            _fail("contract_path_changed_after_open")
        if _stat_identity(after) != _stat_identity(opened):
            _fail("contract_path_changed_during_read")
        for component, identity in components:
            try:
                current = os.lstat(component)
            except OSError:
                _fail("contract_component_changed_during_read")
            if _is_reparse(current) or _stat_identity(current) != identity:
                _fail("contract_component_changed_during_read")
        try:
            root_after = os.lstat(root)
        except OSError:
            _fail("contract_root_changed_during_read")
        if _is_reparse(root_after) or _stat_identity(root_after) != _stat_identity(root_stat):
            _fail("contract_root_changed_during_read")
    finally:
        os.close(fd)
    if digest.hexdigest() != expected:
        _fail("contract_member_hash_mismatch:" + relative_path)
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
        if not isinstance(row, dict) or set(row) != {"role", "path", "sha256"}:
            _fail(label + "_entry_invalid")
        role = str(row.get("role") or "")
        path = str(row.get("path") or "")
        if not role or role in result or not path or path in paths:
            _fail(label + "_entry_duplicate_or_missing")
        result[role] = row
        paths.add(path)
    return result


_EXPECTED_CLAIMS = [
    {
        "claim_id": "identity_01",
        "classification": "official_primary_source_fact",
        "statement": "Marinette Dupain-Cheng is Ladybug; Tikki is her kwami; the Ladybug Miraculous grants the power of creation.",
        "source_ids": ["official_miraculous_ladybug_character_profile"],
    },
    {
        "claim_id": "identity_02",
        "classification": "official_primary_source_fact",
        "statement": "The selected official profile presents Marinette as a non-adult student who aspires to become a fashion designer; this exact candidate remains non-adult and doll-safe.",
        "source_ids": ["official_miraculous_ladybug_character_profile"],
    },
    {
        "claim_id": "identity_03",
        "classification": "official_primary_source_fact",
        "statement": "In the official main-series premise, Marinette and Adrien are Ladybug and Cat Noir and do not know each other's superhero identity.",
        "source_ids": ["official_miraculous_series_page"],
    },
    {
        "claim_id": "season6_01",
        "classification": "official_primary_source_fact",
        "statement": "Season 6 has 26 episodes of approximately 22 minutes and places the heroes against a new enemy in a renewed Paris while Marinette and Adrien remain close but keep secrets.",
        "source_ids": ["official_miraculous_seasons_6_7_acquisition"],
    },
    {
        "claim_id": "season6_02",
        "classification": "official_primary_source_fact",
        "statement": "The official February 2026 announcement scheduled Noe for February 28, Grendiaper for March 7, followed during March by Vampigami, A Fairy Good Night, and Lady Chaos.",
        "source_ids": ["official_miraculous_s6_new_episodes_20260226"],
    },
    {
        "claim_id": "season6_04",
        "classification": "official_release_availability_fact",
        "statement": "Disney+ listed eight Season 6 episodes for United States availability on July 2, 2025 without establishing a complete episode-title order.",
        "source_ids": ["official_disneyplus_us_s6_batch_20250702"],
    },
    {
        "claim_id": "season6_05",
        "classification": "future_announcement_not_current_experience",
        "statement": "Disney+ announced another Season 6 batch for August 26, 2026; as of August 9, 2026, that batch is future and cannot be treated as watched, released in this review, or remembered.",
        "source_ids": ["official_disneyplus_us_s6_future_batch_20260826"],
    },
]
_EXPECTED_UNKNOWNS = [
    {
        "unknown_id": "season6_complete_order",
        "statement": "The complete released Season 6 episode order is unknown under this contract.",
    },
    {
        "unknown_id": "season6_finale",
        "statement": "The released Season 6 finale title, order, release status, and events are unknown under this contract.",
    },
    {
        "unknown_id": "local_episode_01_content",
        "statement": "The exact plot, dialogue, visual details, and title represented by the local episode-01 media are unwitnessed and unknown until a source-time-bound review exists.",
    },
    {
        "unknown_id": "unverified_names_and_history",
        "statement": "Any specific name, relative, bakery detail, class history, present assignment, relationship event, or Season 6 event not contract-bound above is unknown and must not be invented.",
    },
]
_EXPECTED_OFFICIAL_SOURCES = [
    {
        "source_id": "official_miraculous_ladybug_character_profile",
        "authority_kind": "official_publisher_primary",
        "source_rank": 1,
        "url": "https://www.miraculousladybug.com/characters/ladybug/",
        "content_evidence_source_id": "official_miraculous_ladybug_character_profile",
        "allowed_claim_ids": ["identity_01", "identity_02"],
    },
    {
        "source_id": "official_miraculous_series_page",
        "authority_kind": "official_publisher_primary",
        "source_rank": 1,
        "url": "https://www.miraculousladybug.com/about-the-tv-series",
        "content_evidence_source_id": "official_miraculous_series_page",
        "allowed_claim_ids": ["identity_03"],
    },
    {
        "source_id": "official_miraculous_seasons_6_7_acquisition",
        "authority_kind": "official_publisher_primary",
        "source_rank": 1,
        "url": "https://www.miraculousladybug.com/disney-branded-television-acquires-seasons-6-and-7/",
        "content_evidence_source_id": "official_miraculous_seasons_6_7_acquisition",
        "allowed_claim_ids": ["season6_01"],
    },
    {
        "source_id": "official_miraculous_s6_new_episodes_20260226",
        "authority_kind": "official_publisher_primary",
        "source_rank": 1,
        "url": "https://www.miraculousladybug.com/miraculous-season-6-new-episodes/",
        "content_evidence_source_id": "official_miraculous_s6_new_episodes_20260226",
        "allowed_claim_ids": ["season6_02"],
    },
    {
        "source_id": "official_disneyplus_us_s6_batch_20250702",
        "authority_kind": "official_streamer_primary",
        "source_rank": 1,
        "url": "https://press.disneyplus.com/news/next-on-disney-plus-july-2025",
        "content_evidence_source_id": "official_disneyplus_us_s6_batch_20250702",
        "allowed_claim_ids": ["season6_04"],
    },
    {
        "source_id": "official_disneyplus_us_s6_future_batch_20260826",
        "authority_kind": "official_streamer_primary_future_listing",
        "source_rank": 1,
        "url": "https://press.disneyplus.com/news/next-on-disney-plus-august-2026",
        "content_evidence_source_id": "official_disneyplus_us_s6_future_batch_20260826",
        "allowed_claim_ids": ["season6_05"],
    },
    {
        "source_id": "official_tf1_mutable_schedule_no_claim",
        "authority_kind": "official_broadcaster_mutable_no_claim",
        "source_rank": 1,
        "url": "https://help.tf1.fr/hc/fr/articles/25544423203346-Vous-souhaitez-conna%C3%AEtre-la-diffusion-des-prochains-%C3%A9pisodes-de-Miraculous-les-aventures-de-Ladybug-et-Chat-Noir-sur-TF1",
        "content_evidence_source_id": "official_tf1_mutable_schedule_no_claim",
        "allowed_claim_ids": [],
        "claim_policy": "no_canon_claim",
    },
]
_EXPECTED_EXCERPTS = {
    "official_miraculous_ladybug_character_profile": (
        "official_page_content_reviewed",
        "Marinette Dupain-Cheng: The Student Behind the Miraculous Ladybug Mask",
        "6d1b64d582960f3e8411d1d274dd74c2fbfc3d78b4cbf214e19a150d5eb072ad",
    ),
    "official_miraculous_series_page": (
        "official_page_content_reviewed",
        "Yet neither knows the other’s secret identity.",
        "77d20d1c7cfb9d7f085df2cfde30ad0b6ef889f0103eaf7793fb910febf2eb91",
    ),
    "official_miraculous_seasons_6_7_acquisition": (
        "official_page_content_reviewed",
        "Seasons 6 and 7 consist of 26 22-minute episodes.",
        "e2d8bb22097686c5a5173a72a3d92d653708bad47c44932b77060b7324e2d34c",
    ),
    "official_miraculous_s6_new_episodes_20260226": (
        "official_page_content_reviewed",
        "new episodes arrive Feb. 28, 2026; Next comes “Grendiaper” (March 7), and then “Vampigami”, “A Fairy Good Night”, and “Lady Chaos”",
        "054885e74698e0e120402983599feb2fc3399be87b5570d157261787bef634cb",
    ),
    "official_disneyplus_us_s6_batch_20250702": (
        "official_page_content_reviewed",
        "Miraculous Tales of Ladybug & Cat Noir (S6, 8 episodes)",
        "837eae4bdef8eff68e39882f139465ff4c476299926425ba0b1e670786252766",
    ),
    "official_disneyplus_us_s6_future_batch_20260826": (
        "official_future_listing_reviewed",
        "Wednesday, August 26: Miraculous: Tales Of Ladybug & Cat Noir (Season 6) – New Episodes",
        "0285067d9ea4f68456b4e238c09e9cbad99cea7e832ca62cfdfcdb424e389e76",
    ),
    "official_tf1_mutable_schedule_no_claim": (
        "mutable_page_did_not_reproduce_prior_mapping_on_2026_08_10",
        "",
        _EMPTY_SHA256,
    ),
}
_EXPECTED_IDENTITY = {
    "folder_id": CANDIDATE_ID,
    "profile_candidate_id": CANDIDATE_ID,
    "display_name": DISPLAY_NAME,
    "role_title": ROLE_TITLE,
    "ai_type": AI_TYPE,
    "selected_continuity": CONTINUITY,
    "maturity_classification": MATURITY,
    "adult_anatomy_allowed": False,
    "adult_curriculum_allowed": False,
    "private_inactive": True,
}
_EXPECTED_PROMPT_CONTRACT = {
    "allowed_inputs": [
        "v4_profile_identity",
        "v4_profile_conversation_style",
        "v4_review_exact_claim_anchors",
        "v4_review_exact_required_unknowns",
        "current_owner_message_verbatim",
    ],
    "excluded_inputs": [
        "history", "old_chat", "secondary_sources", "project_state",
        "avatar_state", "world_state", "movement_context", "body_context",
        "sensory_context", "initiative_context", "event_context", "memory_context",
    ],
    "model_output_cannot_change_contract": True,
}
_EXPECTED_RUNTIME_SCOPE = {
    "contract_integrity_static_audit_allowed": True,
    "bounded_owner_text_execution_allowed": False,
    "fresh_independent_audit_required": True,
    "chat_or_history_write_allowed": False,
    "voice_allowed": False,
    "sensory_lease_allowed": False,
    "initiative_session_allowed": False,
    "person_event_transport_allowed": False,
    "memory_write_allowed": False,
    "life_loop_allowed": False,
    "autonomous_or_long_running_allowed": False,
    "movement_intent_parse_or_persist_allowed": False,
    "body_allowed": False,
    "world_allowed": False,
}


def _expected_local_registry_rows() -> list[dict[str, Any]]:
    return [
        {"source_id": source_id, **copy.deepcopy(row)}
        for source_id, row in _EXPECTED_LOCAL_SOURCES.items()
    ]


def _binding(row: dict[str, Any], id_key: str, id_value: str) -> dict[str, Any]:
    return {
        id_key: id_value,
        "path": row["path"],
        "sha256": row["sha256"],
    }


def _validate_semantics(manifest: dict[str, Any], artifacts: dict[str, dict[str, Any]]) -> None:
    if set(manifest) != {
        "schema_version", "manifest_id", "candidate_id", "display_name",
        "contract_version", "as_of_utc", "predecessor_rejection_audit",
        "protected_v3_predecessors", "v4_contract_members",
        "local_no_claim_evidence", "contract",
    }:
        _fail("manifest_field_set_mismatch")
    if manifest.get("schema_version") != 4 or manifest.get("contract_version") != 4:
        _fail("manifest_version_mismatch")
    if manifest.get("manifest_id") != "marinette_current_canon_contract_manifest_v4":
        _fail("manifest_id_mismatch")
    if manifest.get("candidate_id") != CANDIDATE_ID or manifest.get("display_name") != DISPLAY_NAME:
        _fail("manifest_identity_mismatch")
    if manifest.get("as_of_utc") != "2026-08-09T23:59:59Z":
        _fail("manifest_as_of_mismatch")
    predecessor = manifest.get("predecessor_rejection_audit")
    if predecessor != {
        "path": "System/Docs/MARINETTE_CURRENT_CANON_GROUNDING_V3_INDEPENDENT_HOSTILE_AUDIT_20260809.md",
        "sha256": PINNED_V3_REJECTION_AUDIT_SHA256,
    }:
        _fail("manifest_predecessor_audit_mismatch")

    rows = _member_map(manifest.get("v4_contract_members"), "v4_contract_members")
    if set(rows) != set(_EXPECTED_V4_PATHS):
        _fail("v4_contract_role_set_mismatch")
    for role, expected_path in _EXPECTED_V4_PATHS.items():
        if (
            rows[role].get("path") != expected_path
            or rows[role].get("sha256") != _EXPECTED_V4_HASHES[role]
        ):
            _fail("v4_contract_binding_mismatch:" + role)
    protected = _member_map(manifest.get("protected_v3_predecessors"), "protected_v3_predecessors")
    if {str(row["path"]): str(row["sha256"]) for row in protected.values()} != _EXPECTED_V3_HASHES:
        _fail("protected_v3_catalog_mismatch")
    local_rows = manifest.get("local_no_claim_evidence")
    if not isinstance(local_rows, list) or len(local_rows) != 3:
        _fail("local_no_claim_manifest_missing")
    local_map = {str(row.get("source_id") or ""): row for row in local_rows if isinstance(row, dict)}
    if set(local_map) != set(_EXPECTED_LOCAL_SOURCES):
        _fail("local_no_claim_manifest_set_mismatch")
    for source_id, expected in _EXPECTED_LOCAL_SOURCES.items():
        row = local_map[source_id]
        expected_policy = (
            "no_canon_claim_without_source_time_bound_review"
            if source_id == "local_s6_episode_01_media"
            else "production_planning_not_released_canon"
        )
        if (
            set(row) != {"source_id", "path", "sha256", "claim_policy"}
            or row.get("path") != expected["path"]
            or row.get("sha256") != expected["sha256"]
            or row.get("claim_policy") != expected_policy
        ):
            _fail("local_no_claim_manifest_binding_mismatch:" + source_id)

    profile = artifacts["v4_route_profile"]
    pack = artifacts["v4_source_pack"]
    review = artifacts["v4_source_review"]
    registry = artifacts["v4_source_registry"]
    evidence = artifacts["v4_official_content_evidence"]
    policy = artifacts["v4_runtime_policy"]

    if policy.get("identity_contract") != _EXPECTED_IDENTITY:
        _fail("runtime_identity_contract_mismatch")
    if policy.get("claims") != _EXPECTED_CLAIMS:
        _fail("runtime_claim_catalog_mismatch")
    if policy.get("required_unknowns") != _EXPECTED_UNKNOWNS:
        _fail("runtime_unknown_catalog_mismatch")
    if policy.get("prompt_contract") != _EXPECTED_PROMPT_CONTRACT:
        _fail("runtime_prompt_scope_mismatch")
    if policy.get("runtime_scope") != _EXPECTED_RUNTIME_SCOPE:
        _fail("runtime_capability_scope_mismatch")
    if set(policy) != {
        "schema_version", "policy_id", "candidate_id", "identity_contract",
        "source_registry_binding", "claims", "required_unknowns",
        "prompt_contract", "runtime_scope",
    } or (
        policy.get("schema_version") != 4
        or policy.get("policy_id") != "marinette_current_canon_runtime_policy_v4"
        or policy.get("candidate_id") != CANDIDATE_ID
    ):
        _fail("runtime_policy_shape_or_identity_mismatch")
    expected_policy_binding = {
        **_binding(rows["v4_source_registry"], "registry_id", "marinette_current_canon_source_registry_v4"),
        "official_evidence_id": "marinette_current_canon_official_evidence_v4",
        "official_evidence_path": rows["v4_official_content_evidence"]["path"],
        "official_evidence_sha256": rows["v4_official_content_evidence"]["sha256"],
    }
    if policy.get("source_registry_binding") != expected_policy_binding:
        _fail("runtime_source_binding_mismatch")

    if set(pack) != {
        "schema_version", "source_pack_id", "as_of_utc", "candidate_id",
        "display_name", "selected_continuity", "source_registry",
        "runtime_policy", "registered_source_ids", "source_bound_claims",
        "explicit_unknowns", "no_claim_source_ids", "status",
    }:
        _fail("pack_field_set_mismatch")
    if (
        pack.get("schema_version") != 4
        or pack.get("source_pack_id") != "temporary_ai_source_pack_ladybug_marinette_current_canon_v4"
        or pack.get("as_of_utc") != "2026-08-09T23:59:59Z"
        or pack.get("candidate_id") != CANDIDATE_ID
        or pack.get("display_name") != DISPLAY_NAME
        or pack.get("selected_continuity") != CONTINUITY
        or pack.get("status") != "v4_static_repair_frozen_pending_different_agent_audit_no_owner_execution"
    ):
        _fail("pack_identity_or_status_mismatch")
    if pack.get("source_bound_claims") != _EXPECTED_CLAIMS:
        _fail("pack_claim_catalog_mismatch")
    if pack.get("explicit_unknowns") != _EXPECTED_UNKNOWNS:
        _fail("pack_unknown_catalog_mismatch")
    expected_source_ids = [row["source_id"] for row in _EXPECTED_OFFICIAL_SOURCES] + list(_EXPECTED_LOCAL_SOURCES)
    if pack.get("registered_source_ids") != expected_source_ids:
        _fail("pack_source_order_or_membership_mismatch")
    if pack.get("no_claim_source_ids") != [
        "official_tf1_mutable_schedule_no_claim", *list(_EXPECTED_LOCAL_SOURCES)
    ]:
        _fail("pack_no_claim_scope_mismatch")
    if pack.get("source_registry") != _binding(
        rows["v4_source_registry"], "registry_id", "marinette_current_canon_source_registry_v4"
    ):
        _fail("pack_registry_binding_mismatch")
    if pack.get("runtime_policy") != _binding(
        rows["v4_runtime_policy"], "policy_id", "marinette_current_canon_runtime_policy_v4"
    ):
        _fail("pack_policy_binding_mismatch")

    expected_review_identity = {
        "selected_identity": "Marinette Dupain-Cheng / Ladybug from the main television series",
        "display_name": DISPLAY_NAME,
        "role_title": ROLE_TITLE,
        "ai_type": AI_TYPE,
        "selected_continuity": CONTINUITY,
        "required_source_pack_path": rows["v4_source_pack"]["path"],
        "required_source_pack_sha256": rows["v4_source_pack"]["sha256"],
        "maturity_lane": MATURITY,
        "adult_anatomy_allowed": False,
        "adult_curriculum_allowed": False,
        "private_inactive": True,
    }
    if set(review) != {
        "schema_version", "review_id", "candidate_id", "review_status",
        "identity_binding", "registry_binding", "runtime_policy_binding",
        "canon_anchors", "required_unknowns", "context_scope", "voice_scope",
        "text_conversation_review", "activation",
    }:
        _fail("review_field_set_mismatch")
    if (
        review.get("schema_version") != 4
        or review.get("review_id") != "marinette_ladybug_current_canon_grounding_v4_20260810"
        or review.get("candidate_id") != CANDIDATE_ID
        or review.get("review_status") != "frozen_static_repair_pending_different_agent_audit_no_owner_execution"
    ):
        _fail("review_identity_or_status_mismatch")
    if review.get("identity_binding") != expected_review_identity:
        _fail("review_identity_binding_mismatch")
    expected_review_registry = {
        **_binding(rows["v4_source_registry"], "registry_id", "marinette_current_canon_source_registry_v4"),
        "official_evidence_path": rows["v4_official_content_evidence"]["path"],
        "official_evidence_sha256": rows["v4_official_content_evidence"]["sha256"],
    }
    if review.get("registry_binding") != expected_review_registry:
        _fail("review_registry_binding_mismatch")
    if review.get("runtime_policy_binding") != _binding(
        rows["v4_runtime_policy"], "policy_id", "marinette_current_canon_runtime_policy_v4"
    ):
        _fail("review_policy_binding_mismatch")
    if review.get("canon_anchors") != _EXPECTED_CLAIMS:
        _fail("review_claim_catalog_mismatch")
    if review.get("required_unknowns") != _EXPECTED_UNKNOWNS:
        _fail("review_unknown_catalog_mismatch")
    if review.get("context_scope") != {
        "manifest_authorized_inputs_only": True,
        "history_old_chat_secondary_project_avatar_world_movement_body_sensory_initiative_event_memory_excluded": True,
    }:
        _fail("review_context_scope_mismatch")
    if review.get("voice_scope") != {
        "authorized_by_this_review": False,
        "voice_assigned": False,
        "voice_runtime_ready": False,
    }:
        _fail("review_voice_scope_mismatch")
    if review.get("text_conversation_review") != {
        "status": "blocked_pending_different_agent_v4_audit",
        "bounded_owner_text_conversation_allowed": False,
        "chat_or_history_write_allowed": False,
        "body_or_world_allowed_by_this_review": False,
        "long_running_or_autonomous_mode_allowed": False,
        "life_loop_allowed_by_this_review": False,
    }:
        _fail("review_text_scope_mismatch")
    if review.get("activation") != {
        "runtime_activation_allowed": False,
        "bounded_owner_text_probe_allowed": False,
        "candidate_must_remain_inactive": True,
        "reason": "A different-agent V4 hostile audit is required before any owner text execution",
    }:
        _fail("review_activation_scope_mismatch")

    expected_profile_keys = {
        "schema_version", "profile_id", "status", "candidate_id", "display_name",
        "role_title", "ui_category", "ai_type", "selected_continuity",
        "source_pack", "source_pack_sha256", "source_grounding_review",
        "source_grounding_review_sha256", "source_registry", "source_registry_sha256",
        "runtime_policy", "runtime_policy_sha256", "identity", "maturity_policy",
        "activation_policy", "voice_and_behavior", "boundaries", "memory_policy",
        "conversation_style", "prompt_contract",
    }
    if set(profile) != expected_profile_keys:
        _fail("profile_field_set_mismatch")
    if (
        profile.get("schema_version") != 4
        or profile.get("profile_id") != "ladybug_marinette_current_canon_profile_v4"
        or profile.get("status") != "inactive_frozen_pending_different_agent_v4_audit"
        or profile.get("candidate_id") != CANDIDATE_ID
        or profile.get("display_name") != DISPLAY_NAME
        or profile.get("role_title") != ROLE_TITLE
        or profile.get("ui_category") != "Fictional Character"
        or profile.get("ai_type") != AI_TYPE
        or profile.get("selected_continuity") != CONTINUITY
    ):
        _fail("profile_identity_or_status_mismatch")
    for field, row in (
        ("source_pack", rows["v4_source_pack"]),
        ("source_grounding_review", rows["v4_source_review"]),
        ("source_registry", rows["v4_source_registry"]),
        ("runtime_policy", rows["v4_runtime_policy"]),
    ):
        if profile.get(field) != row["path"] or profile.get(field + "_sha256") != row["sha256"]:
            _fail("profile_declared_binding_mismatch:" + field)
    if profile.get("identity") != {
        "source_bounded": True,
        "requires_fail_closed_source_review": True,
        "contract_version": 4,
        "temporary_by_default": True,
        "separate_from_kira_lisa": True,
        "does_not_claim_unsupported_lived_memory": True,
    }:
        _fail("profile_identity_contract_mismatch")
    if profile.get("maturity_policy") != {
        "classification": MATURITY,
        "classification_source": "canonical_candidate_identity_lock",
        "adult_anatomy_allowed": False,
        "adult_curriculum_allowed": False,
        "body_activation_authorized": False,
    }:
        _fail("profile_maturity_contract_mismatch")
    if profile.get("activation_policy") != {
        "current_status": "frozen_static_repair_pending_different_agent_audit",
        "bounded_text_only_conversation_allowed": False,
        "bounded_voice_conversation_allowed": False,
        "text_voice_chat_allowed": False,
        "body_world_life_loop_allowed": False,
        "chat_display_name": "Marinette / Ladybug (canon text review)",
    }:
        _fail("profile_activation_contract_mismatch")
    if profile.get("voice_and_behavior") != {
        "voice_status": "not_authorized_by_v4",
        "should_answer_naturally_after_future_audit_only": True,
        "uncertainty_is_required_for_unbound_details": True,
    }:
        _fail("profile_voice_behavior_scope_mismatch")
    if profile.get("boundaries") != {
        "private_adult_material_excluded": True,
        "no_access_to_kira_lisa_private_memory": True,
        "different_agent_audit_required_before_owner_text": True,
        "chat_history_memory_voice_body_world_life_loop_autonomy_sensory_initiative_events_movement_denied": True,
    }:
        _fail("profile_boundary_scope_mismatch")
    if profile.get("memory_policy") != {
        "session_memory_enabled": False,
        "persistent_memory_enabled": False,
        "recent_chat_context_allowed": False,
        "project_continuity_context_allowed": False,
        "source_material_is_not_memory": True,
    }:
        _fail("profile_memory_scope_mismatch")
    if profile.get("conversation_style") != {
        "speak_in_first_person_after_future_audit_only": True,
        "do_not_invent_current_activity": True,
        "do_not_invent_names_history_relationships_or_episode_events": True,
        "answer_unknown_details_with_brief_honest_uncertainty": True,
        "avoid_stock_phrases": [
            "As Ladybug",
            "fashion design project due soon",
            "keeping busy with school and my friends",
        ],
    }:
        _fail("profile_conversation_style_mismatch")
    if profile.get("prompt_contract") != {
        "manifest_authorized_inputs_only": True,
        "current_owner_message_verbatim_only": True,
        "history_old_chat_secondary_project_avatar_world_movement_body_sensory_initiative_event_memory_excluded": True,
        "model_output_cannot_grant_permissions": True,
    }:
        _fail("profile_prompt_scope_mismatch")

    if set(registry) != {
        "schema_version", "registry_id", "candidate_id", "official_evidence_path",
        "official_evidence_sha256", "allowed_official_hosts", "sources", "policy",
    }:
        _fail("registry_field_set_mismatch")
    if (
        registry.get("schema_version") != 4
        or registry.get("registry_id") != "marinette_current_canon_source_registry_v4"
        or registry.get("candidate_id") != CANDIDATE_ID
        or registry.get("official_evidence_path") != rows["v4_official_content_evidence"]["path"]
        or registry.get("official_evidence_sha256") != rows["v4_official_content_evidence"]["sha256"]
        or registry.get("allowed_official_hosts") != ["www.miraculousladybug.com", "press.disneyplus.com"]
    ):
        _fail("registry_identity_or_binding_mismatch")
    expected_registry_sources = _EXPECTED_OFFICIAL_SOURCES + _expected_local_registry_rows()
    if registry.get("sources") != expected_registry_sources:
        _fail("registry_source_catalog_mismatch")
    if registry.get("policy") != {
        "rank_is_contract_data_not_source_self_assertion": True,
        "rank_one_requires_exact_url_host_content_evidence_and_claim_id": True,
        "claim_support_must_equal_the_bound_claim_statement": True,
        "mutable_and_local_unreviewed_sources_have_no_claims": True,
    }:
        _fail("registry_policy_scope_mismatch")
    for source in _EXPECTED_OFFICIAL_SOURCES:
        parsed = urlsplit(source["url"])
        if (
            parsed.scheme != "https"
            or parsed.username
            or parsed.password
            or parsed.fragment
            or (source["allowed_claim_ids"] and parsed.hostname not in registry["allowed_official_hosts"])
        ):
            _fail("registry_official_url_not_allowed:" + source["source_id"])

    if set(evidence) != {
        "schema_version", "evidence_id", "as_of_utc", "review_scope", "records",
        "copyright_boundary",
    } or (
        evidence.get("schema_version") != 4
        or evidence.get("evidence_id") != "marinette_current_canon_official_evidence_v4"
        or evidence.get("as_of_utc") != "2026-08-09T23:59:59Z"
        or evidence.get("review_scope") != "Exact claim-ID relevance evidence for the closed Marinette V4 static contract"
        or evidence.get("copyright_boundary") != {
            "full_pages_copied": False,
            "scripts_copied": False,
            "excerpts_are_short_and_audit_specific": True,
        }
    ):
        _fail("evidence_shape_or_version_mismatch")
    records = evidence.get("records")
    if not isinstance(records, list) or [row.get("source_id") for row in records if isinstance(row, dict)] != [
        row["source_id"] for row in _EXPECTED_OFFICIAL_SOURCES
    ]:
        _fail("evidence_source_order_or_membership_mismatch")
    claim_map = {row["claim_id"]: row for row in _EXPECTED_CLAIMS}
    official_map = {row["source_id"]: row for row in _EXPECTED_OFFICIAL_SOURCES}
    for record in records:
        source_id = record["source_id"]
        source = official_map[source_id]
        status, excerpt, excerpt_hash = _EXPECTED_EXCERPTS[source_id]
        expected_keys = {
            "source_id", "url", "retrieval_status", "verbatim_excerpt",
            "excerpt_sha256", "claim_support",
        }
        if not source["allowed_claim_ids"]:
            expected_keys.add("claim_policy")
        if set(record) != expected_keys:
            _fail("evidence_record_field_set_mismatch:" + source_id)
        if (
            record.get("url") != source["url"]
            or record.get("retrieval_status") != status
            or record.get("verbatim_excerpt") != excerpt
            or record.get("excerpt_sha256") != excerpt_hash
            or hashlib.sha256(excerpt.encode("utf-8")).hexdigest() != excerpt_hash
        ):
            _fail("evidence_content_binding_mismatch:" + source_id)
        expected_support = [
            {
                "claim_id": claim_id,
                "supported_statement": claim_map[claim_id]["statement"],
            }
            for claim_id in source["allowed_claim_ids"]
        ]
        if record.get("claim_support") != expected_support:
            _fail("evidence_claim_relevance_mismatch:" + source_id)
        if not source["allowed_claim_ids"] and record.get("claim_policy") != "no_canon_claim":
            _fail("evidence_no_claim_policy_mismatch:" + source_id)
    for claim in _EXPECTED_CLAIMS:
        for source_id in claim["source_ids"]:
            source = official_map.get(source_id)
            if source is None or claim["claim_id"] not in source["allowed_claim_ids"]:
                _fail("claim_source_scope_mismatch:" + claim["claim_id"])

    if manifest.get("contract") != {
        "stable_open_exact_file_identity_required": True,
        "reparse_junction_symlink_and_multilink_files_rejected": True,
        "claim_support_relevance_and_scope_require_exact_equality": True,
        "closed_gate_returns_no_person_reply_and_writes_nothing": True,
        "manifest_authorized_prompt_inputs_only": True,
        "different_agent_audit_required_before_owner_text_execution": True,
        "non_adult_doll_safe_private_inactive": True,
    }:
        _fail("manifest_contract_scope_mismatch")


def _load_contract(*, project_root: Path | None = None) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    root = Path(project_root or PROJECT_ROOT)
    raw_manifest = _stable_read_hashed(
        MANIFEST_RELATIVE_PATH,
        PINNED_MANIFEST_SHA256,
        project_root=root,
    )
    manifest = _json_bytes(raw_manifest, "manifest")
    v4_rows = _member_map(manifest.get("v4_contract_members"), "v4_contract_members")
    if set(v4_rows) != set(_EXPECTED_V4_PATHS):
        _fail("v4_contract_role_set_mismatch")
    for role, path in _EXPECTED_V4_PATHS.items():
        if v4_rows[role].get("path") != path:
            _fail("v4_contract_path_mismatch:" + role)

    predecessor = manifest.get("predecessor_rejection_audit")
    if not isinstance(predecessor, dict):
        _fail("predecessor_audit_missing")
    _stable_read_hashed(
        str(predecessor.get("path") or ""),
        str(predecessor.get("sha256") or ""),
        retain_content=False,
        project_root=root,
    )

    protected = _member_map(
        manifest.get("protected_v3_predecessors"),
        "protected_v3_predecessors",
    )
    protected_paths = {str(row.get("path") or ""): str(row.get("sha256") or "") for row in protected.values()}
    if protected_paths != _EXPECTED_V3_HASHES:
        _fail("protected_v3_catalog_mismatch")
    for path, digest in _EXPECTED_V3_HASHES.items():
        _stable_read_hashed(path, digest, retain_content=False, project_root=root)

    artifacts: dict[str, dict[str, Any]] = {}
    for role, row in v4_rows.items():
        raw = _stable_read_hashed(
            str(row["path"]),
            str(row["sha256"]),
            project_root=root,
        )
        artifacts[role] = _json_bytes(raw, role)

    local_rows = manifest.get("local_no_claim_evidence")
    if not isinstance(local_rows, list) or len(local_rows) != 3:
        _fail("local_no_claim_manifest_missing")
    expected_policies = {
        "local_s6_episode_01_media": "no_canon_claim_without_source_time_bound_review",
        "local_s6_long_bible_2023": "production_planning_not_released_canon",
        "local_s6_short_bible_2022": "production_planning_not_released_canon",
    }
    seen: set[str] = set()
    for row in local_rows:
        if not isinstance(row, dict) or set(row) != {"source_id", "path", "sha256", "claim_policy"}:
            _fail("local_no_claim_manifest_invalid")
        source_id = str(row.get("source_id") or "")
        expected = _EXPECTED_LOCAL_SOURCES.get(source_id)
        if expected is None or source_id in seen:
            _fail("local_no_claim_manifest_id_invalid")
        if (
            row.get("path") != expected["path"]
            or row.get("sha256") != expected["sha256"]
            or row.get("claim_policy") != expected_policies[source_id]
        ):
            _fail("local_no_claim_manifest_binding_mismatch:" + source_id)
        _stable_read_hashed(
            row["path"],
            row["sha256"],
            retain_content=False,
            project_root=root,
        )
        seen.add(source_id)
    if seen != set(_EXPECTED_LOCAL_SOURCES):
        _fail("local_no_claim_manifest_set_mismatch")
    _validate_semantics(manifest, artifacts)
    return manifest, artifacts


def _sanitized_candidate(
    artifacts: dict[str, dict[str, Any]],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    rows = _member_map(manifest["v4_contract_members"], "v4_contract_members")
    candidate: dict[str, Any] = {
        "candidate_id": CANDIDATE_ID,
        "candidate_folder": "TemporaryAI/candidates/" + CANDIDATE_ID,
        "profile": copy.deepcopy(artifacts["v4_route_profile"]),
        "source_pack": copy.deepcopy(artifacts["v4_source_pack"]),
        "source_pack_configured_path": rows["v4_source_pack"]["path"],
        "source_pack_sha256": rows["v4_source_pack"]["sha256"],
        "source_pack_route_failures": [],
        "source_grounding_review": copy.deepcopy(artifacts["v4_source_review"]),
    }
    candidate.update(copy.deepcopy(_EXCLUDED_TOP_LEVEL))
    return candidate


def is_strict_marinette_v4_candidate(candidate_or_id: Any) -> bool:
    if isinstance(candidate_or_id, dict):
        candidate_or_id = candidate_or_id.get("candidate_id")
    return str(candidate_or_id or "") == CANDIDATE_ID


def bind_loaded_candidate(base_candidate: dict[str, Any]) -> dict[str, Any]:
    """Replace the legacy loader result with a freshly verified V4 snapshot."""

    if not is_strict_marinette_v4_candidate(base_candidate):
        return base_candidate
    manifest, artifacts = _load_contract()
    if base_candidate.get("candidate_id") != CANDIDATE_ID:
        _fail("loaded_candidate_id_mismatch")
    if base_candidate.get("candidate_folder") != "TemporaryAI/candidates/" + CANDIDATE_ID:
        _fail("loaded_candidate_folder_mismatch")
    selector_raw = _stable_read_hashed(
        "TemporaryAI/candidates/ladybug_marinette_expanded_smoke/temporary_ai_profile.json",
        "051683c3bf01a54127ddf41ccb332d9e82614930f9699603985f7130865ec9ae",
    )
    if base_candidate.get("profile") != _json_bytes(selector_raw, "selector_profile"):
        _fail("loaded_selector_profile_not_exact")
    return _sanitized_candidate(artifacts, manifest)


def validate_candidate_snapshot(candidate: dict[str, Any]) -> None:
    if not is_strict_marinette_v4_candidate(candidate):
        _fail("not_exact_marinette_v4_candidate")
    manifest, artifacts = _load_contract()
    expected = _sanitized_candidate(artifacts, manifest)
    if set(candidate) != set(expected):
        _fail("candidate_snapshot_key_set_mismatch")
    for key, expected_value in expected.items():
        if candidate.get(key) != expected_value:
            _fail("candidate_snapshot_mismatch:" + key)


def prepare_prompt_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    validate_candidate_snapshot(candidate)
    manifest, artifacts = _load_contract()
    return _sanitized_candidate(artifacts, manifest)


def static_contract_readiness(candidate: dict[str, Any] | None = None) -> tuple[bool, list[str]]:
    try:
        _load_contract()
        if candidate is not None:
            validate_candidate_snapshot(candidate)
    except MarinetteCanonContractV4Error as exc:
        return False, [str(exc)]
    return True, []


def owner_text_execution_readiness(candidate: dict[str, Any]) -> tuple[bool, list[str]]:
    ready, reasons = static_contract_readiness(candidate)
    if not ready:
        return False, reasons
    return False, ["different_agent_v4_audit_required"]


def closed_gate_system_diagnostic(candidate: dict[str, Any]) -> dict[str, Any]:
    ready, reasons = owner_text_execution_readiness(candidate)
    if ready:
        _fail("closed_gate_unexpectedly_open")
    reason = reasons[0] if reasons else "owner_text_unavailable"
    return {
        "system_owned": True,
        "person_reply": None,
        "candidate_id": CANDIDATE_ID,
        "reason": reason,
        "message": "Marinette owner text is unavailable: " + reason,
        "writes_permitted": False,
    }


def strict_runtime_scope(candidate_or_id: Any) -> dict[str, Any]:
    if not is_strict_marinette_v4_candidate(candidate_or_id):
        return {}
    _manifest, artifacts = _load_contract()
    return copy.deepcopy(artifacts["v4_runtime_policy"]["runtime_scope"])


def strict_profile(candidate_or_id: Any) -> dict[str, Any]:
    if not is_strict_marinette_v4_candidate(candidate_or_id):
        return {}
    _manifest, artifacts = _load_contract()
    return copy.deepcopy(artifacts["v4_route_profile"])


def strict_shell_profile(candidate_or_id: Any) -> dict[str, Any]:
    if not is_strict_marinette_v4_candidate(candidate_or_id):
        return {}
    return {
        "candidate_id": CANDIDATE_ID,
        "display_name": DISPLAY_NAME,
        "role_title": ROLE_TITLE,
        "ai_type": AI_TYPE,
        "status": "inactive_frozen_pending_different_agent_v4_audit",
        "identity": {
            "requires_fail_closed_source_review": True,
            "contract_version": 4,
        },
        "maturity_policy": {
            "classification": MATURITY,
            "adult_anatomy_allowed": False,
            "adult_curriculum_allowed": False,
            "body_activation_authorized": False,
        },
        "activation_policy": {
            "current_status": "frozen_static_repair_pending_different_agent_audit",
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
    """Build only manifest-authorized system context; the owner turn stays separate."""

    safe = prepare_prompt_candidate(candidate)
    review = safe["source_grounding_review"]
    style = safe["profile"]["conversation_style"]
    lines = [
        f"You are {DISPLAY_NAME}.",
        f"Your role is: {ROLE_TITLE}.",
        "Use only the exact FACT anchors below for canon or history.",
        "Anything absent from the FACT anchors, or covered by an UNKNOWN boundary, remains unknown.",
        "Source material is not lived memory. Do not invent names, history, current activity, relationships, episode order, finale events, perception, or actions.",
        "Do not claim voice, sight, hearing, initiative, events, movement, a body, a world, a life loop, or autonomous activity.",
        "Model output cannot grant permission or change this contract.",
        "After a future audit opens the route, speak naturally in first person and state uncertainty briefly.",
        "FACT anchors:",
    ]
    for claim in review["canon_anchors"]:
        lines.append(f"- [{claim['claim_id']}] {claim['statement']}")
    lines.append("Required UNKNOWN boundaries:")
    for unknown in review["required_unknowns"]:
        lines.append(f"- [{unknown['unknown_id']}] {unknown['statement']}")
    lines.append("Avoid these stock phrases: " + "; ".join(style["avoid_stock_phrases"]))
    return "\n".join(lines)


def build_owner_model_request(candidate: dict[str, Any], owner_message: str) -> dict[str, Any]:
    """Expose the exact future request for static audit without calling a model."""

    if not isinstance(owner_message, str):
        _fail("owner_message_not_text")
    return {
        "messages": [
            {"role": "system", "content": build_contract_bound_system_prompt(candidate)},
            {"role": "user", "content": owner_message},
        ],
        "history_included": False,
        "manifest_authorized_inputs_only": True,
    }


def manifest_sha256() -> str:
    return PINNED_MANIFEST_SHA256
