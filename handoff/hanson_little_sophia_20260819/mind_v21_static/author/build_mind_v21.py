from __future__ import annotations

import argparse
import hashlib
import json
import struct
import unicodedata
import zlib
from pathlib import Path


HERE = Path(__file__).resolve().parent
AUTHOR_DIR = HERE.parent / "kira_conversation_continuity_v21_singleton_genesis_unique_outputs_restored_content_hiding_data_only_author"
NAME = "MIND_CONTINUITY_V21_SINGLETON_GENESIS_UNIQUE_OUTPUTS_RESTORED_CONTENT_HIDING_DATA_ONLY.zip"
CEILING = "ACCEPT_STATIC_MIND_CONTINUITY_V21_SINGLETON_GENESIS_UNIQUE_OUTPUTS_RESTORED_CONTENT_HIDING_REQUIREMENTS_ONLY"
SUBJECTS = [
    "V20_FINAL_REJECT_BINDING_V21.json",
    "PRESERVED_SELF_DIRECTION_AND_LIFECYCLE_V21.json",
    "FIXED_PREAUDIT_PROTOCOL_BINDING_V21.json",
    "SINGLETON_GENESIS_UNIQUE_OUTPUTS_CONTENT_HIDING_SCHEMAS_V21.json",
    "ATTACKS_NULL_PINS_AND_AUTHORITY_V21.json",
]
ORDER = ["PAYLOAD_MANIFEST.json", *SUBJECTS]


def pairs(values):
    result = {}
    seen = set()
    for key, value in values:
        normalized = unicodedata.normalize("NFC", key)
        if key in result or normalized != key or normalized in seen:
            raise ValueError("key closure")
        seen.add(normalized)
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError(value)


def validate(value):
    if isinstance(value, str):
        if unicodedata.normalize("NFC", value) != value:
            raise ValueError("non-NFC string")
        if any(ord(character) < 32 or 0xD800 <= ord(character) <= 0xDFFF for character in value):
            raise ValueError("control or surrogate in string")
    elif isinstance(value, list):
        for member in value:
            validate(member)
    elif isinstance(value, dict):
        for key, member in value.items():
            validate(key)
            validate(member)
    elif isinstance(value, float):
        raise ValueError("float")


def load(path: Path):
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf") or b"\0" in raw:
        raise ValueError("raw closure")
    value = json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=pairs,
        parse_constant=reject_constant,
        parse_float=reject_constant,
    )
    validate(value)
    return value


def canonical(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def pretty(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n").encode("utf-8")


def identity(path: str, raw: bytes):
    return {"path": path, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def framed_root(rows):
    preimage = b"".join(
        row["path"].encode("utf-8")
        + b"\0"
        + str(row["bytes"]).encode("ascii")
        + b"\0"
        + row["sha256"].encode("ascii")
        + b"\n"
        for row in sorted(rows, key=lambda row: row["path"].encode("utf-8"))
    )
    return preimage, hashlib.sha256(preimage).hexdigest()


def deterministic_zip(members):
    local = bytearray()
    central = bytearray()
    offsets = {}
    for name, raw in members:
        encoded_name = name.encode("ascii")
        crc = zlib.crc32(raw) & 0xFFFFFFFF
        offsets[name] = len(local)
        local.extend(struct.pack("<IHHHHHIIIHH", 0x04034B50, 20, 0, 0, 0, 33, crc, len(raw), len(raw), len(encoded_name), 0))
        local.extend(encoded_name)
        local.extend(raw)
    central_start = len(local)
    for name, raw in members:
        encoded_name = name.encode("ascii")
        crc = zlib.crc32(raw) & 0xFFFFFFFF
        central.extend(struct.pack("<IHHHHHHIIIHHHHHII", 0x02014B50, 20, 20, 0, 0, 0, 33, crc, len(raw), len(raw), len(encoded_name), 0, 0, 0, 0, 0x01800000, offsets[name]))
        central.extend(encoded_name)
    return bytes(local + central + struct.pack("<IHHHHIIH", 0x06054B50, 0, 0, len(members), len(members), len(central), central_start, 0))


def build():
    members = [(name, canonical(load(HERE / name))) for name in SUBJECTS]
    rows = [identity(name, raw) for name, raw in members]
    root_preimage, root_sha256 = framed_root(rows)
    manifest = {
        "schema": "kira.mind.continuity.v21.singleton_genesis_unique_outputs_content_hiding.payload_manifest.v1",
        "status": "DATA_ONLY_SINGLETON_GENESIS_UNIQUE_OUTPUTS_CONTENT_HIDING_AUTHOR_CANDIDATE",
        "maximum_different_audit_ceiling": CEILING,
        "member_order": ORDER,
        "stored_json_member_count": len(ORDER),
        "code_native_executable_or_script_member_count": 0,
        "actual_journal_registry_beacon_generator_anchor_receipt_proof_key_store_launcher_runner_or_integration_member_count": 0,
        "subject_count": len(SUBJECTS),
        "root_algorithm": "unsigned ordinal UTF-8 path + actual NUL + ASCII decimal bytes + actual NUL + lowercase SHA-256 + actual LF",
        "subject_root_preimage_bytes": len(root_preimage),
        "subject_root_sha256": root_sha256,
        "subjects": rows,
        "v20_final_reject_bound_without_promotion": True,
        "fixed_preaudit_protocol_bound_without_execution": True,
        "authority": {
            "static_requirements_only": True,
            "runtime_live_production_private_log_global_pending": False,
            "root_go": None,
        },
    }
    payload_manifest = canonical(manifest)
    artifact = deterministic_zip([("PAYLOAD_MANIFEST.json", payload_manifest), *members])
    return {
        "artifact": {"bytes": len(artifact), "sha256": hashlib.sha256(artifact).hexdigest()},
        "payload_manifest": {"bytes": len(payload_manifest), "sha256": hashlib.sha256(payload_manifest).hexdigest()},
        "payload_subject_root": {
            "preimage_bytes": len(root_preimage),
            "actual_nul_count": root_preimage.count(b"\0"),
            "actual_lf_count": root_preimage.count(b"\n"),
            "sha256": root_sha256,
        },
        "member_order": ORDER,
        "raw": artifact,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-final", action="store_true")
    arguments = parser.parse_args()
    result = build()
    if arguments.write_final:
        AUTHOR_DIR.mkdir(exist_ok=True)
        (AUTHOR_DIR / NAME).write_bytes(result["raw"])
        public = {key: value for key, value in result.items() if key != "raw"}
        (HERE / "AUTHOR_BUILD_RESULT.json").write_bytes(
            pretty(
                {
                    "schema": "kira.mind.continuity.v21.author_build_result.v1",
                    "status": "AUTHOR_BUILD_COMPLETE_DATA_ONLY_REQUIREMENTS_ONLY",
                    **public,
                    "self_audit_performed": False,
                    "production_public_log_private_memory_or_launcher_accessed": False,
                }
            )
        )
    print(json.dumps({key: value for key, value in result.items() if key != "raw"}, sort_keys=True))


if __name__ == "__main__":
    main()
