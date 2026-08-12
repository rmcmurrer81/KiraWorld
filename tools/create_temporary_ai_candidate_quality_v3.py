"""Create one inert TemporaryAI quality-V3 static evidence package.

The normal entry accepts only a parent-authorized request ID. The authority
root SHA-256 and trusted UTC clock must come from launcher-owned environment
values; records, sources, identities, domains, and output paths are never taken
from free-form CLI arguments. No model/body/voice/avatar/live lane exists here.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.temporary_ai_creator_quality_v3 import (
    HEAD_KIND,
    SCHEMA_VERSION,
    ParentAuthorityV3,
    canonical_json_bytes,
    canonical_sha256,
    exclusive_write,
    open_parent_authority,
    prepare_quality_v3,
    private_lifecycle,
    safe_make_directory,
    validate_head_chain,
)


AUTHORITY_ROOT_RELATIVE = "TemporaryAI/quality_v3_parent_authority"
AUTHORITY_HASH_ENV = "KIRA_TEMP_AI_V3_AUTHORITY_ROOT_SHA256"
TRUSTED_NOW_ENV = "KIRA_TEMP_AI_V3_TRUSTED_NOW_UTC"


def _join(relative_directory: str, name: str) -> str:
    return f"{relative_directory.rstrip('/')}/{name}"


def create_candidate_v3(authority: ParentAuthorityV3, request_id: str) -> dict[str, Any]:
    """Write only the parent-derived inert source pack, record, summary, and head."""
    prepared = prepare_quality_v3(authority, request_id)
    index = prepared.index
    output_dir = str(index["output_directory"])
    head_dir = str(index["head_directory"])
    if not head_dir.startswith(output_dir.rstrip("/") + "/"):
        raise ValueError("head directory must be inside the exact parent-owned output directory")

    # Validate all inputs before the first output mutation. A new directory is
    # the commit namespace; any existing final directory is refused.
    safe_make_directory(authority.root, output_dir)
    safe_make_directory(authority.root, head_dir)

    source_pack_path = _join(output_dir, "source_pack_v3.json")
    quality_path = _join(output_dir, "creator_quality_v3_revision_000001.json")
    summary_path = _join(output_dir, "creation_summary_v3.json")
    head_path = _join(head_dir, "head_000001.json")

    source_pack_bytes = canonical_json_bytes(prepared.source_pack)
    quality_bytes = canonical_json_bytes(prepared.quality_record)
    source_pack_sha = exclusive_write(authority.root, source_pack_path, source_pack_bytes)
    quality_sha = exclusive_write(authority.root, quality_path, quality_bytes)
    if source_pack_sha != prepared.quality_record["source_pack_sha256"]:
        raise RuntimeError("parent-derived source pack changed before exclusive write")

    summary = {
        "schema_version": SCHEMA_VERSION,
        "record_kind": "temporary_ai_creator_quality_v3_static_summary",
        "request_id": prepared.request["request_id"],
        "candidate_id": prepared.request["candidate_id"],
        "display_name": prepared.request["display_name"],
        "quality_record_path": quality_path,
        "quality_record_sha256": quality_sha,
        "source_pack_path": source_pack_path,
        "source_pack_sha256": source_pack_sha,
        "status": prepared.quality_record["quality_status"],
        "model_loaded_or_called": False,
        "model_body_voice_avatar_or_live_queue_created": False,
        "lifecycle": private_lifecycle(),
    }
    summary_sha = exclusive_write(authority.root, summary_path, canonical_json_bytes(summary))
    head = {
        "schema_version": SCHEMA_VERSION,
        "record_kind": HEAD_KIND,
        "generation": 1,
        "request_id": prepared.request["request_id"],
        "candidate_id": prepared.request["candidate_id"],
        "revision": 1,
        "record_path": quality_path,
        "record_sha256": quality_sha,
        "previous_head_sha256": "",
        "consumed_parent_record_sha256": "",
        "request_sha256": prepared.quality_record["request_sha256"],
        "registry_sha256": prepared.quality_record["registry_sha256"],
        "created_at_utc": authority.trusted_now_utc,
        "lifecycle": private_lifecycle(),
    }
    head_sha = exclusive_write(authority.root, head_path, canonical_json_bytes(head))
    heads = validate_head_chain(authority, request_id)
    if len(heads) != 1 or canonical_sha256(heads[0]) != head_sha:
        raise RuntimeError("initial parent head readback failed")
    return {
        "request_id": prepared.request["request_id"],
        "candidate_id": prepared.request["candidate_id"],
        "files": {
            "quality_record": quality_path,
            "source_pack": source_pack_path,
            "summary": summary_path,
            "head": head_path,
        },
        "hashes": {
            "quality_record": quality_sha,
            "source_pack": source_pack_sha,
            "summary": summary_sha,
            "head": head_sha,
        },
        "status": prepared.quality_record["quality_status"],
        "model_body_voice_avatar_or_live_queue_created": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create an inert TemporaryAI quality-V3 package from one parent-issued request ID."
    )
    parser.add_argument("--request-id", required=True)
    args = parser.parse_args()
    root_hash = os.environ.get(AUTHORITY_HASH_ENV, "")
    trusted_now = os.environ.get(TRUSTED_NOW_ENV, "")
    if not root_hash or not trusted_now:
        raise SystemExit(
            f"parent launcher must set {AUTHORITY_HASH_ENV} and {TRUSTED_NOW_ENV}"
        )
    authority = open_parent_authority(
        PROJECT_ROOT / AUTHORITY_ROOT_RELATIVE,
        expected_root_sha256=root_hash,
        trusted_now_utc=trusted_now,
    )
    result = create_candidate_v3(authority, args.request_id)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
