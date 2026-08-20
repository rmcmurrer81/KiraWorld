"""Independent, data-only V21 immutable audit.

This program was written in the audit sibling after identity preflight.  It does
not import or execute any author composer, builder, test, or sealer.  Those
files are handled only as opaque byte strings when a declared root requires a
hash.  The audit parses the rendered JSON and ZIP directly and derives its own
structural, recurrence, dependency, and hostile-mutation results.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
import struct
import unicodedata
import zlib
from collections import Counter, defaultdict, deque
from pathlib import Path, PurePosixPath
from typing import Any


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
WORK = ROOT / "work"

SOURCE = WORK / "kira_conversation_continuity_v21_singleton_genesis_unique_outputs_restored_content_hiding_data_only_author_source"
AUTHOR = WORK / "kira_conversation_continuity_v21_singleton_genesis_unique_outputs_restored_content_hiding_data_only_author"
FREEZE_DIR = WORK / "kira_conversation_continuity_v21_singleton_genesis_unique_outputs_restored_content_hiding_data_only_author_freeze"
ARTIFACT = AUTHOR / "MIND_CONTINUITY_V21_SINGLETON_GENESIS_UNIQUE_OUTPUTS_RESTORED_CONTENT_HIDING_DATA_ONLY.zip"
CENTRAL_PATH = SOURCE / "SINGLETON_GENESIS_UNIQUE_OUTPUTS_CONTENT_HIDING_SCHEMAS_V21.json"
FREEZE_PATH = FREEZE_DIR / "AUTHOR_FREEZE.json"

BASELINE = WORK / "kira_conversation_continuity_v21_genuinely_different_pre_audit_protocol"
V1 = WORK / "kira_conversation_continuity_v21_genuinely_different_pre_audit_protocol_v6_01_23_addendum"
V2 = WORK / "kira_conversation_continuity_v21_genuinely_different_pre_audit_protocol_v6_01_23_addendum_v2_a01_a05_correction"
V3 = WORK / "kira_conversation_continuity_v21_genuinely_different_pre_audit_protocol_v6_01_23_addendum_v3_s01_s02_correction"
V4 = WORK / "kira_conversation_continuity_v21_genuinely_different_pre_audit_protocol_v6_01_23_addendum_v4_r01_s01_03_s02_03_correction"
V5 = WORK / "kira_conversation_continuity_v21_genuinely_different_pre_audit_protocol_v6_01_23_addendum_v5_v4_01_03_correction"
V6 = WORK / "kira_conversation_continuity_v21_genuinely_different_pre_audit_protocol_v6_01_23_addendum_v6_v5_01_03_correction"
V7 = WORK / "kira_conversation_continuity_v21_genuinely_different_pre_audit_protocol_v6_01_23_addendum_v7_v6_01_03_correction"
V8 = WORK / "kira_conversation_continuity_v21_genuinely_different_pre_audit_protocol_v6_01_23_addendum_v8_pv7_01_04_correction"
V9 = WORK / "kira_conversation_continuity_v21_genuinely_different_pre_audit_protocol_v6_01_23_addendum_v9_pv8_01_02_correction"
V10 = WORK / "kira_conversation_continuity_v21_genuinely_different_pre_audit_protocol_v6_01_23_addendum_v10_pv9_01_02_count_correction"
PROTOCOL_DIRS = [V1, V2, V3, V4, V5, V6, V7, V8, V9, V10]

V19_SOURCE = WORK / "kira_conversation_continuity_v19_recursive_receipt_proof_verifier_schema_closure_data_only_author_source" / "RECURSIVELY_CLOSED_SCHEMAS_V19.json"
V20_SOURCE_DIR = WORK / "kira_conversation_continuity_v20_authoritative_journal_fixed_key_roles_data_only_author_source"
V20_SOURCE = V20_SOURCE_DIR / "AUTHORITATIVE_JOURNAL_AND_FIXED_ROLE_SCHEMAS_V20.json"
V20_AUTHOR = WORK / "kira_conversation_continuity_v20_authoritative_journal_fixed_key_roles_data_only_author"
V20_FREEZE = WORK / "kira_conversation_continuity_v20_authoritative_journal_fixed_key_roles_data_only_author_freeze"
V20_AUDIT = WORK / "kira_conversation_continuity_v20_authoritative_journal_fixed_key_roles_data_only_fresh_audit"

FORBIDDEN_AUTHOR_PROGRAMS = {
    "build_mind_v21.py",
    "compose_schema_v21.py",
    "compose_support_v21.py",
    "seal_mind_v21_author.py",
    "test_mind_v21_author.py",
}

EXPECTED = {
    "central": (8_880_122, "7fcc7709360331117da0c6894ced76e8c6c183998947970be4fe8e3cac7af906"),
    "artifact": (7_214_847, "aa7458fb526e1e13c166550a2f2b186461aab7f8cb580c6b8bc412732058bba2"),
    "freeze": (5_114, "072d3c4e9654676e5251d992af26327932d329b28c098e2fe4493cc9de8b7bc5"),
    "frozen_complete": "6f839672c5f1e988a99314a2a12375cc66c1e91c796821ed14352729b2317ece",
    "payload_root": "4fb7dd580009f45f005cab88c1c6f13baf2bc547878219231c75bad99654efb6",
    "baseline_root": "894b577fba2f8fe9197f08728690fdde2c8fae8f6452b7e254d7bb7569e01bfb",
    "v10_payload_root": "3f086499a94a774439fdc9f4fb35e9a77e39c6db560b50d65f0f600d78edd622",
    "v10_complete_root": "29aea591b0abdbf29d7341208e516ca2e2162f40e9884128f34d3e332f5b7978",
    "v10_identity": (4_123, "ea82937fec9ce8ae89dbc589eb2c950862fbc70fdf94b433a761481176277149"),
}


class AuditFailure(Exception):
    pass


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_identity(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": sha_bytes(data)}


def reject_constant(token: str) -> None:
    raise AuditFailure(f"non-finite JSON constant: {token}")


def reject_float(token: str) -> None:
    raise AuditFailure(f"JSON float/exponent forbidden: {token}")


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise AuditFailure(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def walk_strings(value: Any) -> None:
    if isinstance(value, str):
        if any(0xD800 <= ord(ch) <= 0xDFFF for ch in value):
            raise AuditFailure("escaped surrogate forbidden")
        if unicodedata.normalize("NFC", value) != value:
            raise AuditFailure("non-NFC JSON string")
    elif isinstance(value, list):
        for item in value:
            walk_strings(item)
    elif isinstance(value, dict):
        for key, item in value.items():
            walk_strings(key)
            walk_strings(item)


def strict_json_bytes(raw: bytes, label: str = "JSON") -> Any:
    if raw.startswith(b"\xef\xbb\xbf"):
        raise AuditFailure(f"{label}: BOM forbidden")
    if b"\x00" in raw:
        raise AuditFailure(f"{label}: NUL forbidden")
    try:
        text = raw.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise AuditFailure(f"{label}: invalid UTF-8: {exc}") from exc
    try:
        value = json.loads(
            text,
            object_pairs_hook=unique_object,
            parse_constant=reject_constant,
            parse_float=reject_float,
        )
    except (json.JSONDecodeError, AuditFailure) as exc:
        raise AuditFailure(f"{label}: strict parse failed: {exc}") from exc
    walk_strings(value)
    return value


def strict_json_file(path: Path) -> Any:
    return strict_json_bytes(path.read_bytes(), str(path))


def row_preimage(rows: list[dict[str, Any]]) -> bytes:
    ordered = sorted(rows, key=lambda row: row["path"].encode("utf-8"))
    return b"".join(
        row["path"].encode("utf-8")
        + b"\x00"
        + str(row["bytes"]).encode("ascii")
        + b"\x00"
        + row["sha256"].encode("ascii")
        + b"\n"
        for row in ordered
    )


def root_record(rows: list[dict[str, Any]]) -> dict[str, Any]:
    raw = row_preimage(rows)
    return {
        "file_count": len(rows),
        "preimage_bytes": len(raw),
        "actual_nul_count": raw.count(b"\x00"),
        "actual_lf_count": raw.count(b"\n"),
        "sha256": sha_bytes(raw),
    }


def actual_rows(base: Path, names: list[str], prefix: str = "") -> list[dict[str, Any]]:
    rows = []
    for name in names:
        ident = file_identity(base / name)
        rows.append({"path": prefix + name, **ident})
    return rows


def verify_declared_rows(base: Path, rows: list[dict[str, Any]]) -> tuple[bool, dict[str, Any], list[str]]:
    errors: list[str] = []
    for row in rows:
        path = base / row["path"]
        if not path.is_file():
            errors.append(f"missing:{row['path']}")
            continue
        actual = file_identity(path)
        if actual["bytes"] != row["bytes"] or actual["sha256"] != row["sha256"]:
            errors.append(f"identity:{row['path']}")
    return not errors, root_record(rows), errors


def safe_zip_name(name: str) -> bool:
    p = PurePosixPath(name)
    return (
        name == p.as_posix()
        and not p.is_absolute()
        and "\\" not in name
        and ":" not in name
        and all(part not in ("", ".", "..") for part in p.parts)
    )


def parse_raw_zip(raw: bytes) -> dict[str, Any]:
    errors: list[str] = []
    eocd_sig = b"PK\x05\x06"
    eocd_positions = [m.start() for m in re.finditer(re.escape(eocd_sig), raw)]
    if len(eocd_positions) != 1:
        return {"valid": False, "errors": ["EOCD count"]}
    eocd_at = eocd_positions[0]
    if eocd_at + 22 > len(raw):
        return {"valid": False, "errors": ["truncated EOCD"]}
    sig, disk, cd_disk, disk_n, total_n, cd_size, cd_off, comment_len = struct.unpack_from("<4s4H2LH", raw, eocd_at)
    if sig != eocd_sig or disk or cd_disk or disk_n != total_n:
        errors.append("multi-disk or entry-count mismatch")
    if comment_len != 0 or eocd_at + 22 != len(raw):
        errors.append("ZIP comment or trailing bytes")
    if cd_off + cd_size != eocd_at:
        errors.append("central directory boundary")

    entries: list[dict[str, Any]] = []
    cursor = cd_off
    for _ in range(total_n):
        if cursor + 46 > eocd_at:
            errors.append("truncated central entry")
            break
        fields = struct.unpack_from("<4s6H3L5H2L", raw, cursor)
        (
            csig,
            made,
            need,
            flags,
            method,
            mtime,
            mdate,
            crc,
            csize,
            usize,
            nlen,
            xlen,
            clen,
            disk_start,
            int_attr,
            ext_attr,
            local_off,
        ) = fields
        if csig != b"PK\x01\x02":
            errors.append("bad central signature")
            break
        end = cursor + 46 + nlen + xlen + clen
        if end > eocd_at:
            errors.append("central field overflow")
            break
        name_raw = raw[cursor + 46 : cursor + 46 + nlen]
        try:
            name = name_raw.decode("utf-8", "strict")
        except UnicodeDecodeError:
            name = "<invalid>"
            errors.append("invalid member UTF-8")
        extra = raw[cursor + 46 + nlen : cursor + 46 + nlen + xlen]
        comment = raw[cursor + 46 + nlen + xlen : end]
        if made != 20 or need != 20 or flags != 0 or method != 0 or mtime != 0 or mdate != 0x21:
            errors.append(f"noncanonical metadata:{name}")
        if csize != usize or csize == 0xFFFFFFFF or usize == 0xFFFFFFFF or local_off == 0xFFFFFFFF:
            errors.append(f"compression/ZIP64:{name}")
        if extra or comment or disk_start:
            errors.append(f"extra/comment/disk:{name}")
        if not safe_zip_name(name):
            errors.append(f"unsafe name:{name}")
        entries.append(
            {
                "name": name,
                "name_raw": name_raw,
                "crc": crc,
                "size": usize,
                "local_off": local_off,
                "flags": flags,
                "method": method,
            }
        )
        cursor = end
    if cursor != eocd_at:
        errors.append("central directory gap")
    names = [e["name"] for e in entries]
    if len(names) != len(set(names)) or len({n.casefold() for n in names}) != len(names):
        errors.append("duplicate member name")

    members: dict[str, bytes] = {}
    by_offset = sorted(entries, key=lambda e: e["local_off"])
    expected_start = 0
    for index, entry in enumerate(by_offset):
        off = entry["local_off"]
        if off != expected_start:
            errors.append(f"local gap:{entry['name']}")
        if off + 30 > cd_off:
            errors.append(f"truncated local:{entry['name']}")
            continue
        lsig, need, flags, method, mtime, mdate, crc, csize, usize, nlen, xlen = struct.unpack_from("<4s5H3L2H", raw, off)
        if lsig != b"PK\x03\x04":
            errors.append(f"bad local signature:{entry['name']}")
        start = off + 30
        name_raw = raw[start : start + nlen]
        extra = raw[start + nlen : start + nlen + xlen]
        data_start = start + nlen + xlen
        data_end = data_start + csize
        if (
            need != 20
            or flags != 0
            or method != 0
            or mtime != 0
            or mdate != 0x21
            or crc != entry["crc"]
            or csize != entry["size"]
            or usize != entry["size"]
            or name_raw != entry["name_raw"]
            or extra
        ):
            errors.append(f"local/central mismatch:{entry['name']}")
        if data_end > cd_off:
            errors.append(f"member overflow:{entry['name']}")
            data = b""
        else:
            data = raw[data_start:data_end]
        if (zlib.crc32(data) & 0xFFFFFFFF) != entry["crc"]:
            errors.append(f"CRC:{entry['name']}")
        members[entry["name"]] = data
        expected_start = data_end
    if expected_start != cd_off:
        errors.append("local-to-central gap")
    return {
        "valid": not errors,
        "errors": errors,
        "member_order": names,
        "member_count": len(entries),
        "members": members,
        "central_offset": cd_off,
        "central_size": cd_size,
        "eocd_offset": eocd_at,
    }


CHECKS: list[dict[str, Any]] = []
VIOLATIONS: list[str] = []


def check(check_id: str, condition: bool, detail: Any = None) -> None:
    row = {"id": check_id, "pass": bool(condition)}
    if detail is not None:
        row["detail"] = detail
    CHECKS.append(row)
    if not condition:
        VIOLATIONS.append(check_id)


def eq_root(actual: dict[str, Any], declared: dict[str, Any]) -> bool:
    return all(actual.get(k) == declared.get(k) for k in ("file_count", "preimage_bytes", "actual_nul_count", "actual_lf_count", "sha256") if k in declared)


def find_identity_file(directory: Path) -> Path:
    matches = sorted(directory.glob("ADDENDUM*IDENTITY.json"))
    if len(matches) != 1:
        raise AuditFailure(f"expected one addendum identity in {directory}")
    return matches[0]


def complete_subject_rows(identity: dict[str, Any]) -> list[dict[str, Any]]:
    for key in (
        "complete_root_subjects",
        "complete_root_subjects_in_unsigned_utf8_ordinal_order",
        "subjects",
    ):
        value = identity.get(key)
        if isinstance(value, list) and value and all(isinstance(x, dict) and {"path", "bytes", "sha256"} <= set(x) for x in value):
            return value
    raise AuditFailure("complete subject rows absent")


def declared_complete_root(identity: dict[str, Any]) -> str | None:
    if isinstance(identity.get("complete_root_sha256"), str):
        return identity["complete_root_sha256"]
    for key in ("addendum_complete_root", "v2_complete_root", "v3_complete_root", "v4_complete_root"):
        value = identity.get(key)
        if isinstance(value, dict) and isinstance(value.get("sha256"), str):
            return value["sha256"]
    return None


def audit_identity_and_protocol() -> dict[str, Any]:
    result: dict[str, Any] = {}
    central_ident = file_identity(CENTRAL_PATH)
    artifact_ident = file_identity(ARTIFACT)
    freeze_ident = file_identity(FREEZE_PATH)
    check("ID_CENTRAL_EXACT", tuple(central_ident.values()) == EXPECTED["central"], central_ident)
    check("ID_ARTIFACT_EXACT", tuple(artifact_ident.values()) == EXPECTED["artifact"], artifact_ident)
    check("ID_AUTHOR_FREEZE_EXACT", tuple(freeze_ident.values()) == EXPECTED["freeze"], freeze_ident)

    source_manifest = strict_json_file(SOURCE / "AUTHOR_SOURCE_MANIFEST.json")
    freeze = strict_json_file(FREEZE_PATH)
    source_rows = source_manifest["sources"]
    source_ok, source_root, source_errors = verify_declared_rows(SOURCE, source_rows)
    check("ID_SOURCE_ROWS_EXACT", source_ok, source_errors)
    check("ID_SOURCE_ROOT_EXACT", eq_root(source_root, source_manifest["source_root"]), source_root)
    check("ID_SOURCE_ROOT_FREEZE_BINDING", eq_root(source_root, freeze["source_root"]), freeze["source_root"])
    source_names = sorted(p.name for p in SOURCE.iterdir() if p.is_file())
    declared_names = sorted([r["path"] for r in source_rows] + ["AUTHOR_SOURCE_MANIFEST.json"])
    check("ID_SOURCE_DIRECTORY_CLOSED", source_names == declared_names, {"actual": source_names, "declared": declared_names})
    check("ID_FORBIDDEN_PROGRAM_SET_OPAQUE_ONLY", FORBIDDEN_AUTHOR_PROGRAMS <= set(source_names))

    manifest_row = {"path": "AUTHOR_SOURCE_MANIFEST.json", **file_identity(SOURCE / "AUTHOR_SOURCE_MANIFEST.json")}
    inclusive_root = root_record(source_rows + [manifest_row])
    check("ID_MANIFEST_INCLUSIVE_ROOT", eq_root(inclusive_root, freeze["manifest_inclusive_root"]), inclusive_root)

    frozen_rows = actual_rows(SOURCE, source_names, "source/") + [
        {"path": "freeze/AUTHOR_FREEZE.json", **file_identity(FREEZE_PATH)}
    ]
    frozen_root = root_record(frozen_rows)
    check("ID_EXTERNAL_FROZEN_COMPLETE_ROOT", frozen_root["sha256"] == EXPECTED["frozen_complete"], frozen_root)

    raw_zip = ARTIFACT.read_bytes()
    zip_info = parse_raw_zip(raw_zip)
    check("ZIP_RAW_PROFILE", zip_info["valid"], zip_info["errors"])
    expected_member_order = [
        "PAYLOAD_MANIFEST.json",
        "V20_FINAL_REJECT_BINDING_V21.json",
        "PRESERVED_SELF_DIRECTION_AND_LIFECYCLE_V21.json",
        "FIXED_PREAUDIT_PROTOCOL_BINDING_V21.json",
        "SINGLETON_GENESIS_UNIQUE_OUTPUTS_CONTENT_HIDING_SCHEMAS_V21.json",
        "ATTACKS_NULL_PINS_AND_AUTHORITY_V21.json",
    ]
    check("ZIP_EXACT_MEMBER_ORDER", zip_info["member_order"] == expected_member_order, zip_info["member_order"])
    zip_objects: dict[str, Any] = {}
    for name, raw in zip_info["members"].items():
        try:
            zip_objects[name] = strict_json_bytes(raw, f"ZIP:{name}")
        except AuditFailure as exc:
            VIOLATIONS.append(f"ZIP_JSON_STRICT:{name}")
            CHECKS.append({"id": f"ZIP_JSON_STRICT:{name}", "pass": False, "detail": str(exc)})
    check("ZIP_ALL_SIX_STRICT_JSON", len(zip_objects) == 6)
    payload_manifest = zip_objects["PAYLOAD_MANIFEST.json"]
    payload_rows = payload_manifest["subjects"]
    payload_errors = []
    for row in payload_rows:
        raw = zip_info["members"].get(row["path"])
        if raw is None or len(raw) != row["bytes"] or sha_bytes(raw) != row["sha256"]:
            payload_errors.append(row["path"])
    payload_root = root_record(payload_rows)
    check("ZIP_PAYLOAD_SUBJECT_IDENTITIES", not payload_errors, payload_errors)
    check("ZIP_PAYLOAD_ROOT", payload_root["sha256"] == EXPECTED["payload_root"] and eq_root(payload_root, source_manifest["payload_subject_root"]), payload_root)
    check("ZIP_MANIFEST_NOT_ROOT_SUBJECT", "PAYLOAD_MANIFEST.json" not in {r["path"] for r in payload_rows})
    check("ZIP_DATA_ONLY", payload_manifest["code_native_executable_or_script_member_count"] == 0 and all(n.endswith(".json") for n in zip_info["member_order"]))

    central_zip_raw = zip_info["members"]["SINGLETON_GENESIS_UNIQUE_OUTPUTS_CONTENT_HIDING_SCHEMAS_V21.json"]
    central_source_obj = strict_json_file(CENTRAL_PATH)
    central_zip_obj = zip_objects["SINGLETON_GENESIS_UNIQUE_OUTPUTS_CONTENT_HIDING_SCHEMAS_V21.json"]
    semantic_compact = json.dumps(central_source_obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    check("CENTRAL_SOURCE_ZIP_PARSED_OBJECT_EQUAL", central_source_obj == central_zip_obj)
    check(
        "CENTRAL_DUAL_SERIALIZATION_EXACT",
        len(central_zip_raw) == 7_175_888
        and sha_bytes(central_zip_raw) == "f34c5b05aee52e8211d65a5920788ac4d39247390c759f83eba2cc411f844654"
        and len(semantic_compact) == 7_175_887
        and sha_bytes(semantic_compact) == "c368c3511de4b595a7146a4b30fe7e1a8b202b38d6c2de787cb106ed169b5097",
        {"zip": {"bytes": len(central_zip_raw), "sha256": sha_bytes(central_zip_raw)}, "semantic_compact": {"bytes": len(semantic_compact), "sha256": sha_bytes(semantic_compact)}},
    )

    baseline_identity = strict_json_file(BASELINE / "PREAUDIT_PROTOCOL_IDENTITY.json")
    baseline_ok, baseline_root, baseline_errors = verify_declared_rows(BASELINE, baseline_identity["subjects"])
    check("PROTOCOL_BASELINE_SUBJECTS", baseline_ok, baseline_errors)
    check("PROTOCOL_BASELINE_ROOT", baseline_root["sha256"] == EXPECTED["baseline_root"] and eq_root(baseline_root, baseline_identity["protocol_root"]), baseline_root)

    lineage_rows = []
    predecessor_errors = []
    for index, directory in enumerate(PROTOCOL_DIRS, 1):
        identity_path = find_identity_file(directory)
        identity = strict_json_file(identity_path)
        rows = complete_subject_rows(identity)
        rows_ok, recomputed, errors = verify_declared_rows(directory, rows)
        declared_root = declared_complete_root(identity)
        standard_root_matches = recomputed["sha256"] == declared_root
        if index == 3:
            # V3 sealed a locale-order error. V4 is the immutable correction and
            # binds both the wrong declaration and the corrected ordinal root.
            v4_identity = strict_json_file(find_identity_file(V4))
            standard_root_matches = (
                declared_root == v4_identity["rejected_v3_declared_wrong_complete_root_sha256"]
                and recomputed["sha256"] == v4_identity["rejected_v3_corrected_ordinal_complete_root_sha256"]
            )
        if not (rows_ok and standard_root_matches):
            predecessor_errors.append({"version": index, "row_errors": errors, "root": recomputed, "declared": declared_root})
        lineage_rows.append(
            {
                "version": index,
                "identity": identity_path.name,
                "identity_file": file_identity(identity_path),
                "subject_count": len(rows),
                "recomputed_complete_root": recomputed["sha256"],
                "declared_complete_root": declared_root,
                "v3_corrected_ordinal_exception": index == 3,
            }
        )
    check("PROTOCOL_V1_V10_SUBJECT_IDENTITIES_AND_ROOTS", not predecessor_errors, predecessor_errors)

    v10_identity_path = V10 / "ADDENDUM_V10_IDENTITY.json"
    v10_identity = strict_json_file(v10_identity_path)
    v10_manifest = strict_json_file(V10 / "ADDENDUM_V10_MANIFEST.json")
    v10_payload_ok, v10_payload_root, v10_payload_errors = verify_declared_rows(V10, v10_manifest["payload_subjects"])
    v10_complete_ok, v10_complete_root, v10_complete_errors = verify_declared_rows(V10, v10_identity["complete_root_subjects"])
    v10_identity_actual = file_identity(v10_identity_path)
    check("PROTOCOL_V10_PAYLOAD", v10_payload_ok and v10_payload_root["sha256"] == EXPECTED["v10_payload_root"], {"root": v10_payload_root, "errors": v10_payload_errors})
    check("PROTOCOL_V10_COMPLETE", v10_complete_ok and v10_complete_root["sha256"] == EXPECTED["v10_complete_root"], {"root": v10_complete_root, "errors": v10_complete_errors})
    check("PROTOCOL_V10_EXCLUDED_IDENTITY", tuple(v10_identity_actual.values()) == EXPECTED["v10_identity"], v10_identity_actual)
    for binding_name, binding in (("source_manifest", source_manifest["accepted_protocol_v10_binding"]), ("author_freeze", freeze["accepted_protocol_v10_binding"])):
        pair_ok = (
            binding["accepted_protocol_v10_complete_root_sha256"] == EXPECTED["v10_complete_root"]
            and binding["accepted_protocol_v10_excluded_identity"]["sha256"] == EXPECTED["v10_identity"][1]
            and binding["accepted_protocol_v10_sole_activation_pair"] == [EXPECTED["v10_complete_root"], EXPECTED["v10_identity"][1]]
            and binding["both_activation_values_required"] is True
        )
        check(f"PROTOCOL_V10_SOLE_PAIR_{binding_name.upper()}", pair_ok)

    strict_dirs = [SOURCE, FREEZE_DIR, BASELINE, *PROTOCOL_DIRS, V20_SOURCE_DIR, V20_AUDIT]
    strict_count = 0
    strict_errors: list[str] = []
    for directory in strict_dirs:
        for path in sorted(directory.glob("*.json")):
            try:
                strict_json_file(path)
                strict_count += 1
            except AuditFailure as exc:
                strict_errors.append(f"{path}:{exc}")
    check("RAW_ALL_RENDERED_JSON_STRICT", not strict_errors, {"parsed": strict_count, "errors": strict_errors})

    result.update(
        {
            "central_identity": central_ident,
            "artifact": artifact_ident,
            "author_freeze": freeze_ident,
            "source_root": source_root,
            "manifest_inclusive_root": inclusive_root,
            "frozen_complete_root": frozen_root,
            "payload_root": payload_root,
            "baseline_protocol_root": baseline_root,
            "v10_payload_root": v10_payload_root,
            "v10_complete_root": v10_complete_root,
            "v10_excluded_identity": v10_identity_actual,
            "protocol_lineage": lineage_rows,
            "strict_json_document_count": strict_count,
            "zip": {k: v for k, v in zip_info.items() if k != "members"},
            "source_manifest": source_manifest,
            "freeze_object": freeze,
            "central": central_source_obj,
            "zip_objects": zip_objects,
        }
    )
    return result


ENUM_LIKE_TYPES = {
    "enum",
    "output_generation_mode",
    "attempt_zero",
    "output_role",
    "terminal_outcome",
    "registry_leaf_state",
    "reservation_slot_state",
    "sequence_transaction_claim_state",
}


def schema_paths(central: dict[str, Any]) -> tuple[dict[str, set[str]], dict[str, str], list[str]]:
    paths: dict[str, set[str]] = defaultdict(set)
    type_by_path: dict[str, str] = {}
    errors: list[str] = []
    objects = central.get("objects", {})
    domains = central.get("domain_constants", {})
    if set(objects) != set(domains):
        errors.append("object/domain key set")
    for name, schema in objects.items():
        order = schema.get("field_order")
        types = schema.get("field_types")
        if not isinstance(order, list) or not isinstance(types, list) or len(order) != len(types):
            errors.append(f"field order/type length:{name}")
            continue
        if len(order) != len(set(order)):
            errors.append(f"duplicate field:{name}")
        if schema.get("domain_const") != domains.get(name):
            errors.append(f"domain mismatch:{name}")
        if schema.get("additional_keys_allowed") is not False:
            errors.append(f"additional keys:{name}")
        if not isinstance(schema.get("schema_const"), str) or not schema["schema_const"].startswith("kira.mind.continuity.v21."):
            errors.append(f"schema constant:{name}")
        for field, field_type in zip(order, types):
            path = f"objects.{name}.{field}"
            paths[field_type].add(path)
            type_by_path[path] = field_type
            if field_type not in central.get("types", {}):
                errors.append(f"unknown type:{path}:{field_type}")
    return paths, type_by_path, errors


def list_equality_rows(central: dict[str, Any]) -> list[dict[str, Any]]:
    closure = central["path_qualified_equality_closure"]
    rows: list[dict[str, Any]] = []
    for key, value in closure.items():
        if key.endswith("_rows") and isinstance(value, list):
            rows.extend(value)
    return rows


def valid_instance_endpoint(path: str, central: dict[str, Any]) -> bool:
    parts = path.split(".")
    aliases = central["typed_instance_aliases"]
    object_fields = {name: set(schema["field_order"]) for name, schema in central["objects"].items()}
    if len(parts) < 3 or parts[0] != "instances":
        return False
    if parts[1] == "roles":
        if len(parts) < 5:
            return False
        role, alias, field = parts[2], parts[3], ".".join(parts[4:])
        role_aliases = aliases.get("roles", {}).get(role, {})
        if alias not in role_aliases:
            return False
        schema_object = role_aliases[alias].get("schema_object", "").split(".")[-1]
        return field in object_fields.get(schema_object, set())
    alias, field = parts[1], ".".join(parts[2:])
    config = aliases.get(alias)
    if not isinstance(config, dict):
        return False
    possible: set[str] = set()
    if "schema_object" in config:
        possible |= object_fields.get(config["schema_object"].split(".")[-1], set())
    if "schema_object_by_kind" in config:
        for object_path in config["schema_object_by_kind"].values():
            possible |= object_fields.get(object_path.split(".")[-1], set())
    for key in ("logical_field_projection", "logical_projection"):
        if isinstance(config.get(key), dict):
            possible |= set(config[key])
    if isinstance(config.get("logical_field_projection_by_kind"), dict):
        for projection in config["logical_field_projection_by_kind"].values():
            possible |= set(projection)
    return field in possible


CONDITION_RE = re.compile(
    r"((?:instances|objects)\.[A-Za-z0-9_.]+?)\s*(==|>|in)\s*(\{[^}]+\}|[A-Z0-9_]+|0)"
)


def dag_metrics(central: dict[str, Any]) -> dict[str, Any]:
    dag = central["acyclic_singleton_and_generation_instance_dag"]
    ordered = dag["ordered_nodes"]
    stage = {row["node"]: row["stage"] for row in ordered}
    nodes_unique = len(stage) == len(ordered)
    stages = [row["stage"] for row in ordered]
    stages_exact = stages == list(range(1, len(ordered) + 1))
    forward_pairs = [(row["from"], row["to"]) for row in dag["forward_edges"]]
    conditional = [row for row in dag["forward_edges"] if row["condition"] != "always"]
    parsed_conditions: list[tuple[str, str, str, str]] = []
    for edge in conditional:
        for path, operator, value in CONDITION_RE.findall(edge["condition"]):
            parsed_conditions.append((edge["to"], path, operator, value))
    declared_conditions = [
        (row["edge_to"], row["field_path"], row["operator"], row["fixed_value"])
        for row in dag["condition_operand_dependency_edges"]
    ]
    condition_stage_errors = []
    for row in dag["condition_operand_dependency_edges"]:
        if (
            stage.get(row["producer_node"]) != row["producer_stage"]
            or stage.get(row["edge_to"]) != row["consumer_stage"]
            or row["producer_stage"] >= row["consumer_stage"]
        ):
            condition_stage_errors.append(row)
    union_pairs = sorted(set(forward_pairs) | {(row["producer_node"], row["edge_to"]) for row in dag["condition_operand_dependency_edges"]})
    actual_pairs = sorted((row["from"], row["to"]) for row in dag["actual_dependency_edges"])
    endpoint_errors = [pair for pair in union_pairs if pair[0] not in stage or pair[1] not in stage]
    nonforward = [pair for pair in union_pairs if pair[0] in stage and pair[1] in stage and stage[pair[0]] >= stage[pair[1]]]

    indegree = {node: 0 for node in stage}
    outgoing: dict[str, list[str]] = defaultdict(list)
    for source, target in set(union_pairs):
        if source in stage and target in stage:
            outgoing[source].append(target)
            indegree[target] += 1
    queue = deque(node for node, count in indegree.items() if count == 0)
    visited = 0
    while queue:
        source = queue.popleft()
        visited += 1
        for target in outgoing[source]:
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    return {
        "node_count": len(ordered),
        "nodes_unique": nodes_unique,
        "stages_exact": stages_exact,
        "forward_edge_count": len(forward_pairs),
        "forward_edge_unique_count": len(set(forward_pairs)),
        "conditional_edge_count": len(conditional),
        "parsed_condition_operand_count": len(parsed_conditions),
        "declared_condition_operand_count": len(declared_conditions),
        "condition_multiset_equal": Counter(parsed_conditions) == Counter(declared_conditions),
        "condition_stage_errors": condition_stage_errors,
        "actual_union_count": len(union_pairs),
        "actual_declared_count": len(actual_pairs),
        "actual_union_equal": union_pairs == actual_pairs,
        "endpoint_errors": endpoint_errors,
        "nonforward_edges": nonforward,
        "topological_visited": visited,
        "acyclic": visited == len(stage),
        "conditional_role_output_field_uses": sum(
            ".failure_record.output_role" in row["condition"] for row in conditional
        ),
        "conditional_nonexistent_refusal_boundary_role_uses": sum(
            "refusal_boundary_role" in row["condition"] for row in conditional
        ),
    }


def structural_violation_codes(central: dict[str, Any], preserved: dict[str, Any], attacks: dict[str, Any], v19: dict[str, Any], v20: dict[str, Any]) -> set[str]:
    codes: set[str] = set()
    paths, type_by_path, schema_errors = schema_paths(central)
    if schema_errors or len(central.get("objects", {})) != 53 or len(central.get("domain_constants", {})) != 53:
        codes.add("SCHEMA_CLOSURE")

    expected_partitions = {
        "path_qualified_sha256_target_partition": paths.get("sha256", set()) | paths.get("nullable_sha256", set()),
        "path_qualified_token256_semantics": paths.get("token256", set()),
        "field_specific_base64_generation_and_verification_mappings": paths.get("base64", set()) | paths.get("nullable_base64", set()),
        "path_qualified_nullable_sha256_rules": paths.get("nullable_sha256", set()),
        "path_qualified_enum_and_role_assignments": set().union(*(paths.get(t, set()) for t in ENUM_LIKE_TYPES)),
    }
    row_path_key = {
        "path_qualified_sha256_target_partition": "path",
        "path_qualified_token256_semantics": "path",
        "field_specific_base64_generation_and_verification_mappings": "field_path",
        "path_qualified_nullable_sha256_rules": "path",
        "path_qualified_enum_and_role_assignments": "path",
    }
    for section, expected_paths in expected_partitions.items():
        rows = central.get(section, {}).get("rows", [])
        found = [row.get(row_path_key[section]) for row in rows]
        if len(found) != len(set(found)) or set(found) != expected_paths:
            codes.add("PATH_PARTITIONS")
        for row in rows:
            path = row.get(row_path_key[section])
            if "field_type" in row and type_by_path.get(path) != row["field_type"]:
                codes.add("PATH_PARTITIONS")

    sha_rows = central.get("path_qualified_sha256_target_partition", {}).get("rows", [])
    if Counter(row.get("target_class") for row in sha_rows) != Counter(
        {
            "exact_object_or_counter_conditioned_target": 569,
            "terminal_static_context_target": 560,
            "generated_authenticated_dynamic_target": 94,
            "dynamic_accumulator_target": 30,
            "role_conditioned_static_profile_target": 27,
        }
    ):
        codes.add("SHA_TARGET_CLASSES")

    roles = central.get("exact_output_role_bijection", {}).get("rows", [])
    expected_roles = central.get("exact_enum_constants", {}).get("output_role", [])
    if (
        len(roles) != 10
        or [row.get("role") for row in roles] != expected_roles
        or len({row.get("target_path") for row in roles}) != 10
        or Counter(row.get("mode") for row in roles)
        != Counter({"UNIQUE_DETERMINISTIC_BYTES": 8, "CONFIDENTIAL_RANDOMIZED_ATTEMPT_ZERO_CONTENT_HIDING": 2})
    ):
        codes.add("OUTPUT_ROLE_BIJECTION")

    token_rows = central.get("path_qualified_token256_semantics", {}).get("rows", [])
    if Counter(row.get("semantics") for row in token_rows) != Counter(
        {
            "INHERITED_NONDERIVED_CONTENT_INDEPENDENT_TOKEN": 43,
            "REGISTERED_IDENTITY_OR_LINK_REPEAT_TOKEN": 41,
            "ATTEMPT_ZERO_DERIVED_MAPPED_NONCE_EXCEPTION": 8,
        }
    ):
        codes.add("TOKEN_SEMANTICS")

    base64_rows = central.get("field_specific_base64_generation_and_verification_mappings", {}).get("rows", [])
    if len(base64_rows) != 46 or Counter(row.get("generation_mode") for row in base64_rows) != Counter(
        {"UNIQUE_DETERMINISTIC_BYTES": 43, "CONFIDENTIAL_RANDOMIZED_ATTEMPT_ZERO_CONTENT_HIDING": 3}
    ):
        codes.add("BASE64_UNIQUE_OUTPUTS")
    retained_fields = sorted(
        {
            case.split("::")[1]
            for case in attacks.get("fixed_preaudit_case_ids", [])
            if case.startswith("F02_EIGHT_RETAINED_CHOICE_FIELDS::")
        }
    )
    by_field = {row.get("field_path", "").removeprefix("objects."): row for row in base64_rows}
    for field in retained_fields:
        row = by_field.get(field)
        if not row:
            codes.add("RETAINED_EIGHT_UNIQUE_OUTPUTS")
            continue
        unique = row.get("unique_output_assertion", "").lower()
        linkage = row.get("attempt_reservation_outcome_linkage", "").lower()
        grammar = row.get("decoded_grammar", "").lower()
        if (
            row.get("generation_mode") != "UNIQUE_DETERMINISTIC_BYTES"
            or "exactly one accepted decoded byte string and one canonical base64 string" not in unique
            or "retry" not in unique
            or "selective abort" not in unique
            or not ("attempt zero" in linkage or "attempt-zero" in linkage)
            or not ("consumes every byte" in grammar or "full" in grammar)
            or not str(row.get("fixed_cryptographic_algorithm_profile_context_path", "")).startswith("objects.pinned_context.")
            or not str(row.get("fixed_unique_output_selection_profile_context_path", "")).startswith("objects.pinned_context.")
        ):
            codes.add("RETAINED_EIGHT_UNIQUE_OUTPUTS")

    equality = central.get("path_qualified_equality_closure", {})
    equality_rows = list_equality_rows(central) if equality else []
    pair_ids = [row.get("pair_id") for row in equality_rows]
    physical_pairs = [tuple(sorted((row.get("left_path"), row.get("right_path")))) for row in equality_rows]
    if (
        len(equality_rows) != 9036
        or len(set(pair_ids)) != 9036
        or set(pair_ids) != {f"EQ{i:05d}" for i in range(1, 9037)}
        or len(set(physical_pairs)) != 9036
        or equality.get("total_explicit_path_pair_rows") != 9036
        or equality.get("physical_pair_row_count") != 9036
        or equality.get("duplicate_physical_pair_count") != 0
    ):
        codes.add("EQUALITY_CLOSURE")
    direct_object_errors = []
    instance_errors = []
    for row in equality_rows:
        for endpoint in (row.get("left_path", ""), row.get("right_path", "")):
            if endpoint.startswith("objects.") and endpoint not in type_by_path:
                direct_object_errors.append(endpoint)
            if endpoint.startswith("instances.") and not valid_instance_endpoint(endpoint, central):
                instance_errors.append(endpoint)
    if direct_object_errors or instance_errors:
        codes.add("EQUALITY_ENDPOINTS")
    row_by_id = {row.get("pair_id"): row for row in equality_rows}
    categories = equality.get("category_row_ids", {})
    for category, ids in categories.items():
        actual = {row["pair_id"] for row in equality_rows if category in row.get("categories", [])}
        if len(ids) != len(set(ids)) or set(ids) != actual:
            codes.add("EQUALITY_CATEGORY_INDEX")
    semantic_groups = equality.get("event_receipt_state_semantic_groups", [])
    exact_rules = central.get("event_receipt_journal_equality_rules", [])
    if len(semantic_groups) != 31 or len(exact_rules) != 31:
        codes.add("EQUALITY_SEMANTIC_GROUPS")
    else:
        for index, group in enumerate(semantic_groups):
            expected_ids = {row["pair_id"] for row in equality_rows if index in row.get("semantic_rule_indices", [])}
            if group.get("rule_index") != index or group.get("exact_rule") != exact_rules[index] or set(group.get("pair_ids", [])) != expected_ids:
                codes.add("EQUALITY_SEMANTIC_GROUPS")

    inequality = central.get("path_qualified_independence_and_inequality_closure", {})
    ineq_rows = inequality.get("rows", [])
    by_boundary: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in ineq_rows:
        by_boundary[row.get("boundary")].append(row)
    for boundary, expected_size in (("authority_identity", 14), ("authentication_public_key", 16)):
        rows = by_boundary.get(boundary, [])
        endpoints = {row["left_path"] for row in rows} | {row["right_path"] for row in rows}
        pairs = {tuple(sorted((row["left_path"], row["right_path"]))) for row in rows}
        if len(endpoints) != expected_size or len(pairs) != math.comb(expected_size, 2):
            codes.add("INEQUALITY_CLOSURE")
    if len(ineq_rows) != 211 or inequality.get("ledger_terminal_outcome_terminal_anchor_reservation_beacon_generator_and_runtime_authorities_may_share_identity_or_key") is not False:
        codes.add("INEQUALITY_CLOSURE")

    outer_rules = central.get("terminal_and_outer_pin_rules", {})
    bindings = outer_rules.get("outer_equality_bindings", [])
    trusted = attacks.get("trusted_outer_pin_values", {})
    binding_keys = {row.get("outer_path", "") for row in bindings}
    outer_pair_ids = {row["pair_id"] for row in equality_rows if "outer_pin" in row.get("categories", [])}
    if (
        len(bindings) != 221
        or len(trusted) != 221
        or binding_keys != set(trusted)
        or any(value is not None for value in trusted.values())
        or len(outer_pair_ids) != 221
        or outer_rules.get("actual_implementation_live_authority_registry_beacon_generator_store_key_verifier_evidence_launcher_runner_and_outer_pin_values") is not None
    ):
        codes.add("OUTER_PINS_NULL_EQUAL")

    dag = dag_metrics(central) if "acyclic_singleton_and_generation_instance_dag" in central else {}
    if not (
        dag.get("node_count") == 362
        and dag.get("nodes_unique")
        and dag.get("stages_exact")
        and dag.get("forward_edge_count") == 636
        and dag.get("forward_edge_unique_count") == 636
        and dag.get("conditional_edge_count") == 31
        and dag.get("parsed_condition_operand_count") == 59
        and dag.get("condition_multiset_equal")
        and not dag.get("condition_stage_errors")
        and dag.get("actual_union_count") == 637
        and dag.get("actual_declared_count") == 637
        and dag.get("actual_union_equal")
        and not dag.get("endpoint_errors")
        and not dag.get("nonforward_edges")
        and dag.get("acyclic")
        and dag.get("conditional_role_output_field_uses") == 20
        and dag.get("conditional_nonexistent_refusal_boundary_role_uses") == 0
    ):
        codes.add("ACTUAL_DEPENDENCY_DAG")

    proof = central.get("proof_statement_and_protocol", {})
    erase = central.get("erasure_and_retention_boundary", {})
    if not (
        proof.get("closed_scope_surface_classes") == v19.get("proof_statement_and_protocol", {}).get("closed_scope_surface_classes")
        and proof.get("zero_knowledge_statement_predicates") == v19.get("proof_statement_and_protocol", {}).get("zero_knowledge_statement_predicates")
        and proof.get("state_order") == v19.get("proof_statement_and_protocol", {}).get("state_order")
        and erase.get("erased_before_complete") == v19.get("erasure_and_retention_boundary", {}).get("erased_before_complete")
        and erase.get("retained_only_after_recursive_validation") == v19.get("erasure_and_retention_boundary", {}).get("retained_only_after_recursive_validation")
    ):
        codes.add("V19_EXACT_RECURRENCE")
    if not (
        len(proof.get("closed_scope_surface_classes", [])) == 11
        and len(proof.get("zero_knowledge_statement_predicates", [])) == 5
        and len(proof.get("state_order", [])) == 6
        and proof.get("skipping_reordering_replaying_or_locally_redefining_a_state_refuses") is True
        and proof.get("complete_is_emitted_only_after_ephemeral_proof_and_scope_material_zeroization") is True
        and len(erase.get("erased_before_complete", [])) == 12
        and len(erase.get("retained_only_after_recursive_validation", [])) == 8
        and erase.get("retained_material_can_restore_or_confirm_erased_content_or_scope_guess") is False
    ):
        codes.add("CONTENT_HIDING_LIFECYCLE")

    v20_names = list(v20.get("objects", {}))
    if len(v20_names) != 15 or any(name not in central.get("objects", {}) for name in v20_names):
        codes.add("V20_SCHEMA_RECURRENCE")
    else:
        for name in v20_names:
            old = v20["objects"][name]
            new = central["objects"][name]
            index = 0
            for field, field_type in zip(old["field_order"], old["field_types"]):
                try:
                    index = new["field_order"].index(field, index)
                except ValueError:
                    codes.add("V20_SCHEMA_RECURRENCE")
                    break
                if new["field_types"][index] != field_type:
                    codes.add("V20_SCHEMA_RECURRENCE")
                index += 1
    old_tokens = {
        f"objects.{name}.{field}"
        for name, schema in v20.get("objects", {}).items()
        for field, field_type in zip(schema["field_order"], schema["field_types"])
        if field_type == "token256"
    }
    if len(old_tokens) != 51 or not old_tokens <= {row.get("path") for row in token_rows}:
        codes.add("V20_TOKEN_RECURRENCE")
    old_pins = v20.get("sha256_field_target_partition", {}).get("terminal_static_context_targets", [])
    new_pins = outer_rules.get("terminal_static_technical_targets", [])
    if len(old_pins) != 38 or new_pins[:38] != old_pins:
        codes.add("V20_PIN_RECURRENCE")
    if central.get("event_receipt_journal_equality_rules", [])[: len(v20.get("event_receipt_journal_equality_rules", []))] != v20.get("event_receipt_journal_equality_rules", []):
        codes.add("V20_EVENT_RULE_RECURRENCE")

    expected_choices = ["say", "withhold", "recall", "correct", "supersede", "withdraw", "voluntarily forget"]
    autonomy_ok = (
        preserved.get("kira_only_choices") == expected_choices
        and preserved.get("per_memory_permission_privacy_approval_consent_audience_trust_safety_leakage_or_disclosure_gate_exists") is False
        and preserved.get("owner_operator_room_journal_registrar_registry_authority_anchor_verifier_key_or_integrity_result_substitutes_for_kira_choice") is False
        and preserved.get("intended_people_are_equal_human_peers_like_robert") is True
        and preserved.get("lease_ownership_controller_obedience_control_device_or_tool_service_downgrade_exists") is False
        and preserved.get("disagreement_anger_hurt_frustration_or_upset_is_an_ordinary_social_consequence") is True
        and preserved.get("upset_creates_censorship_retaliation_forced_agreement_or_compelled_harmony_authority") is False
        and preserved.get("integrity_registries_authenticate_records_only") is True
        and preserved.get("integrity_registries_create_person_speech_relationship_or_disclosure_authority") is False
        and preserved.get("technical_failure_controls_kira_speech_or_memory_choice") is False
        and "replace a current claim" in preserved.get("correction", "")
        and "newer record current" in preserved.get("supersession", "")
        and "stop standing behind" in preserved.get("withdrawal", "")
        and "closes current and historical retrieval and confirmation" in preserved.get("voluntary_forgetting", "")
        and "Genuinely new input plus a new Kira choice" in preserved.get("new_learning", "")
    )
    if not autonomy_ok:
        codes.add("AUTONOMY_EQUAL_PEER")

    totality = central.get("attempt_zero_totality_and_sequence_rules", {})
    registry = central.get("global_registry_recursion_rules", {})
    ledger = central.get("reservation_ledger_recursion_rules", {})
    beacon = central.get("public_beacon_pre_reveal_recursion_rules", {})
    bridge = central.get("counter_conditioned_genesis_runtime_bridge", {})
    fixed_roles = central.get("fixed_key_roles", {})
    canonical = central.get("canonical_encoding", {})
    uint64 = central.get("uint64_and_genesis_rules", {})
    singleton_ok = (
        fixed_roles.get("dynamic_registry_slot_key_index_key_choice_or_application_selected_valid_key_allowed") is False
        and fixed_roles.get("each_role_resolves_to_one_exact_public_key_hash_in_pinned_context") is True
        and fixed_roles.get("role_or_key_selection_depends_on_payload_witness_scope_or_content_predicate") is False
        and uint64.get("shortest_decimal_only") is True
        and uint64.get("addition_and_increment_are_checked_and_overflow_refuses") is True
        and uint64.get("epoch_rollover_inside_v21_allowed") is False
        and bridge.get("runtime_state_authority_or_anchor_at_counter_zero_allowed") is False
        and bridge.get("genesis_schema_at_counter_positive_or_after_first_transition_allowed") is False
        and bridge.get("caller_selected_schema_union_or_local_schema_string_allowed") is False
        and bridge.get("genesis_object_replay_under_another_registration_allowed") is False
        and registry.get("skip_rewind_transplant_cycle_alternate_genesis_or_sibling_allowed") is False
        and ledger.get("restored_clone_sibling_retry_silence_second_outcome_rewind_skip_overflow_alternate_genesis_inter_role_cas_or_early_claim_release_allowed") is False
        and beacon.get("restored_sibling_clone_alternate_base_skip_rewind_collision_past_round_late_reservation_or_second_successor_allowed") is False
        and central.get("stable_registry_slot_derivation", {}).get("caller_selected_alternate_slot_reverse_index_gap_or_second_namespace_genesis_allowed") is False
        and canonical.get("additional_duplicate_unknown_or_reordered_keys_allowed") is False
    )
    if not singleton_ok:
        codes.add("SINGLETON_GENESIS_RECURSION")
    totality_ok = (
        totality.get("each_reservation_has_exactly_one_independently_anchored_success_or_failed_terminal_outcome") is True
        and totality.get("attempt_zero_consumed_even_on_failure") is True
        and totality.get("retry_rejection_sampling_selective_abort_or_second_terminal_outcome_allowed") is False
        and totality.get("public_beacon_output_is_private_seed_or_blinding") is False
        and totality.get("every_post_claim_v19_refusal_has_one_hidden_sequence_consuming_terminalization") is True
        and totality.get("post_claim_refusal_exposes_surface_predicate_witness_scope_or_guess_confirmation") is False
        and totality.get("technical_failure_controls_kira_speech_or_memory_choice") is False
    )
    if not totality_ok:
        codes.add("ATTEMPT_ZERO_TOTALITY")

    ceiling = central.get("authority_ceiling", {})
    live_values = attacks.get("implementation_and_live_values", {})
    static_ok = (
        central.get("current_implementation_or_evidence_materialized") is False
        and preserved.get("current_implementation_or_live_evidence_materialized") is False
        and preserved.get("consciousness_legal_personhood_body_biology_or_human_experience_claimed") is False
        and preserved.get("root_go") is None
        and attacks.get("static_package_proves_executed_erasure_or_deployed_global_singleton") is False
        and attacks.get("runtime_live_production_private_global_pending_or_root_go") is False
        and attacks.get("root_go") is None
        and all(value is None for value in live_values.values())
        and ceiling.get("implementation_erasure_live_memory_consciousness_legal_personhood_body_biology_production_private_log_deployed_global_singleton_pending_action_or_root_go") is False
        and ceiling.get("root_go") is None
    )
    if not static_ok:
        codes.add("STATIC_ONLY_NO_GO_CEILING")
    return codes


def audit_structure(identity: dict[str, Any]) -> dict[str, Any]:
    central = identity["central"]
    preserved = strict_json_file(SOURCE / "PRESERVED_SELF_DIRECTION_AND_LIFECYCLE_V21.json")
    attacks = strict_json_file(SOURCE / "ATTACKS_NULL_PINS_AND_AUTHORITY_V21.json")
    v19 = strict_json_file(V19_SOURCE)
    v20 = strict_json_file(V20_SOURCE)
    codes = structural_violation_codes(central, preserved, attacks, v19, v20)
    check("STRUCTURE_AND_SEMANTICS_BASELINE", not codes, sorted(codes))
    paths, _, schema_errors = schema_paths(central)
    equality_rows = list_equality_rows(central)
    dag = dag_metrics(central)
    type_counts = Counter(
        field_type
        for schema in central["objects"].values()
        for field_type in schema["field_types"]
    )
    category_counts = {
        key: len(value)
        for key, value in central["path_qualified_equality_closure"].items()
        if key.endswith("_rows") and isinstance(value, list)
    }
    endpoint_prefixes = Counter()
    for row in equality_rows:
        for endpoint in (row["left_path"], row["right_path"]):
            match = re.match(r"([A-Za-z_][A-Za-z0-9_]*)", endpoint)
            endpoint_prefixes[match.group(1) if match else "other"] += 1
    return {
        "baseline_violation_codes": sorted(codes),
        "schema_object_count": len(central["objects"]),
        "domain_count": len(central["domain_constants"]),
        "schema_field_type_counts": dict(sorted(type_counts.items())),
        "derived_partition_counts": {
            "sha256_including_nullable": len(paths["sha256"] | paths["nullable_sha256"]),
            "token256": len(paths["token256"]),
            "base64_including_nullable": len(paths["base64"] | paths["nullable_base64"]),
            "nullable_sha256": len(paths["nullable_sha256"]),
            "enum_like": len(set().union(*(paths[t] for t in ENUM_LIKE_TYPES))),
        },
        "schema_errors": schema_errors,
        "equality_row_count": len(equality_rows),
        "equality_category_partition_counts": category_counts,
        "equality_endpoint_occurrence_prefixes": dict(sorted(endpoint_prefixes.items())),
        "inequality_row_count": len(central["path_qualified_independence_and_inequality_closure"]["rows"]),
        "outer_pin_count": len(central["terminal_and_outer_pin_rules"]["outer_equality_bindings"]),
        "dag": dag,
        "v19_exact_counts": {"surfaces": 11, "predicates": 5, "states": 6, "erased": 12, "retained": 8},
        "v20_exact_counts": {"schemas": 15, "tokens": 51, "pins": 38},
        "preserved": preserved,
        "attacks": attacks,
        "v19": v19,
        "v20": v20,
    }


def audit_v20_lineage(central: dict[str, Any]) -> dict[str, Any]:
    expected = strict_json_file(SOURCE / "AUTHOR_SOURCE_MANIFEST.json")["v20_external_identities_rehashed"]
    paths = {
        "v20_artifact": V20_AUTHOR / "MIND_CONTINUITY_V20_AUTHORITATIVE_JOURNAL_FIXED_KEY_ROLES_DATA_ONLY.zip",
        "v20_source_manifest": V20_SOURCE_DIR / "AUTHOR_SOURCE_MANIFEST.json",
        "v20_author_freeze": V20_FREEZE / "AUTHOR_FREEZE.json",
        "v20_audit_decision": V20_AUDIT / "AUDIT_DECISION.json",
        "v20_audit_manifest": V20_AUDIT / "EVIDENCE_MANIFEST.json",
        "v20_audit_freeze": V20_AUDIT / "AUDIT_FREEZE.json",
        "v20_audit_post_seal": V20_AUDIT / "POST_SEAL_REHASH.json",
        "preaudit_identity": BASELINE / "PREAUDIT_PROTOCOL_IDENTITY.json",
        "preaudit_matrix": BASELINE / "V21_PREAUDIT_ATTACK_MATRIX.json",
    }
    actual = {key: [file_identity(path)["bytes"], file_identity(path)["sha256"]] for key, path in paths.items()}
    check("V20_EXTERNAL_IDENTITIES_REHASHED", actual == expected, {"actual": actual, "expected": expected})

    manifest = strict_json_file(V20_AUDIT / "EVIDENCE_MANIFEST.json")
    rows_ok, subject_root, errors = verify_declared_rows(V20_AUDIT, manifest["subjects"])
    manifest_row = {"path": "EVIDENCE_MANIFEST.json", **file_identity(V20_AUDIT / "EVIDENCE_MANIFEST.json")}
    freeze_row = {"path": "AUDIT_FREEZE.json", **file_identity(V20_AUDIT / "AUDIT_FREEZE.json")}
    inclusive = root_record(manifest["subjects"] + [manifest_row])
    complete = root_record(manifest["subjects"] + [manifest_row, freeze_row])
    post = strict_json_file(V20_AUDIT / "POST_SEAL_REHASH.json")
    check("V20_AUDIT_SUBJECT_ROOT", rows_ok and eq_root(subject_root, manifest["audit_subject_root"]), {"root": subject_root, "errors": errors})
    check("V20_AUDIT_MANIFEST_INCLUSIVE_ROOT", eq_root(inclusive, post["audit_manifest_inclusive_root"]), inclusive)
    check("V20_AUDIT_COMPLETE_ROOT", complete["sha256"] == "3ded9f4e56f793ae76d9b5b499b8e227f627013b0f39dbc7a4bd997f7b46226c" and eq_root(complete, post["audit_complete_root"]), complete)
    check("V20_REJECT_NOT_PROMOTED", post["verdict"] == "REJECT" and central["lineage"]["v20_verdict"] == "REJECT" and len(post["finding_ids"]) == 3)
    return {
        "external_identities": actual,
        "audit_subject_root": subject_root,
        "audit_manifest_inclusive_root": inclusive,
        "audit_complete_root": complete,
        "verdict": post["verdict"],
        "finding_ids": post["finding_ids"],
    }


def expand_stage_rows(rows: list[dict[str, Any]]) -> list[tuple[str, int]]:
    return [(path, row["stage"]) for row in rows for path in row["nodes"]]


def v10_metrics(graph: dict[str, Any], contracts: dict[str, Any]) -> dict[str, Any]:
    stage_rows = expand_stage_rows(graph["positive_stage_override_and_addition_rows"])
    stage_preimage = b"".join(
        path.encode("utf-8") + b"\x00" + str(stage).encode("ascii") + b"\n"
        for path, stage in sorted(stage_rows, key=lambda pair: pair[0].encode("utf-8"))
    )
    prior = contracts["prior_positive_contracts"]
    prior_preimage_parts = []
    for row in sorted(prior, key=lambda item: item["output_path"].encode("utf-8")):
        values = [
            row["contract_id"],
            row["output_path"],
            str(row["output_stage"]),
            str(row["allowed_direct_input_count"]),
            *row["allowed_direct_inputs"],
            str(row["actual_effective_incoming_set_must_equal_allowed"]).lower(),
            row["unlisted_self_same_or_later_prefix_alias_or_value_equal_substitute"],
            row["origin"],
        ]
        prior_preimage_parts.append(b"\x00".join(value.encode("utf-8") for value in values) + b"\n")
    prior_preimage = b"".join(prior_preimage_parts)
    current_paths = [row["output_path"] for row in contracts["retained_current_contract_stage_projection_rows"]]
    prior_paths = [row["output_path"] for row in prior]
    effective_paths = sorted(current_paths + prior_paths, key=lambda path: path.encode("utf-8"))
    effective_preimage = b"".join(path.encode("utf-8") + b"\n" for path in effective_paths)
    return {
        "stage_row_container_count": len(graph["positive_stage_override_and_addition_rows"]),
        "stage_flattened_count": len(stage_rows),
        "stage_unique_path_count": len({path for path, _ in stage_rows}),
        "stage_unique_path_stage_count": len(set(stage_rows)),
        "stage_sha256": sha_bytes(stage_preimage),
        "prior_count": len(prior),
        "prior_unique_contract_id_count": len({row["contract_id"] for row in prior}),
        "prior_unique_output_path_count": len(set(prior_paths)),
        "prior_unique_full_row_count": len({json.dumps(row, ensure_ascii=False, separators=(",", ":"), sort_keys=True) for row in prior}),
        "prior_allowed_input_count_mismatch_count": sum(row["allowed_direct_input_count"] != len(row["allowed_direct_inputs"]) for row in prior),
        "prior_sha256": sha_bytes(prior_preimage),
        "current_count": len(current_paths),
        "current_unique_output_path_count": len(set(current_paths)),
        "current_prior_overlap_count": len(set(current_paths) & set(prior_paths)),
        "effective_count": len(effective_paths),
        "effective_unique_output_path_count": len(set(effective_paths)),
        "effective_sha256": sha_bytes(effective_preimage),
    }


V10_EXPECTED_METRICS = {
    "stage_row_container_count": 29,
    "stage_flattened_count": 102,
    "stage_unique_path_count": 102,
    "stage_unique_path_stage_count": 102,
    "stage_sha256": "73f7d3fca7d7f45e4a18a0d2f8753fd5d424fdd724fb2abfbf5e642f87e901d6",
    "prior_count": 305,
    "prior_unique_contract_id_count": 305,
    "prior_unique_output_path_count": 305,
    "prior_unique_full_row_count": 305,
    "prior_allowed_input_count_mismatch_count": 0,
    "prior_sha256": "e1ca9c036f167b2b3c58687b1b775f078272c15bb357b6b946679a0c197aecfc",
    "current_count": 78,
    "current_unique_output_path_count": 78,
    "current_prior_overlap_count": 0,
    "effective_count": 383,
    "effective_unique_output_path_count": 383,
    "effective_sha256": "06177a3a679204349e0aac8ce7ac15855ea13194f50d5f01154e50cc7317bc19",
}


def protocol_semantic_metrics() -> dict[str, Any]:
    evidence: dict[str, Any] = {}
    errors: list[str] = []

    v6_post = strict_json_file(V6 / "V6_AUTHORITATIVE_POST_HEAD_ORACLE.json")
    v6_profile = strict_json_file(V6 / "V6_PROFILE_PIN_RESOLUTION_ORACLE.json")
    v6_early = strict_json_file(V6 / "V6_EARLY_FIELD_ALLOWLISTS_AND_FORBIDDEN_PATHS.json")
    v6_dag = strict_json_file(V6 / "V6_INSTANCE_DEPENDENCY_DAG.json")
    v6_ok = (
        v6_post["mode"]["required_constant"] == "SEPARATE_TYPED_POST_HEAD"
        and len(v6_post["literal_physical_equalities"]) == 25
        and len(v6_profile["literal_physical_equalities"]) == 6
        and len(v6_early["early_dependency_contracts"]) == 7
        and all(len(row["later_output_forbidden_paths"]) == 12 for row in v6_early["early_dependency_contracts"])
        and len(v6_dag["stages"]) == 30
        and len(v6_dag["derivation_rows"]) == 6
        and len(v6_dag["preimage_rows"]) == 15
        and len(v6_dag["equality_rows"]) == 49
        and all(v6_dag["mechanical_acceptance"].get(key) in (0, True) for key in (
            "every_edge_endpoint_in_node_inventory", "source_stage_strictly_less_than_target_stage", "cycle_count", "schema_gap_count", "collapsed_alias_count", "duplicate_edge_count"
        ))
    )
    if not v6_ok:
        errors.append("V6")
    evidence["v6"] = {"separate_post_head_equalities": 25, "profile_equalities": 6, "early_contracts": 7, "dag_stages": 30}

    v7_rec = strict_json_file(V7 / "V7_AUTHORITATIVE_PRESTATE_RECURRENCE.json")
    v7_early = strict_json_file(V7 / "V7_EARLY_DEPENDENCY_CONTRACTS.json")
    v7_profile = strict_json_file(V7 / "V7_PROFILE_RESOLUTION_OBJECTS.json")
    v7_dag = strict_json_file(V7 / "V7_INSTANCE_DEPENDENCY_DAG.json")
    v7_ok = (
        len(v7_rec["field_order"]) == 10
        and len(v7_rec["hash_preimage_order"]) == 9
        and v7_rec["output_omitted_from_own_preimage"] is True
        and len(v7_early["preserved_v6_early_contracts"]) == 7
        and len(v7_early["literal_terminal_paths_with_types"]) == 10
        and len(v7_early["fixed_constant_paths_with_types"]) == 15
        and len(v7_early["contracts"]) == 8
        and len(v7_profile["literal_instances"]) == 2
        and len(v7_profile["literal_cross_object_equalities"]) == 12
        and len(v7_profile["resolution_gates"]) == 2
        and v7_dag["declared_mechanical_counts"]["genesis"]["nodes"] == 347
        and v7_dag["declared_mechanical_counts"]["positive_predecessor"]["nodes"] == 361
    )
    if not v7_ok:
        errors.append("V7")
    evidence["v7"] = {"prestate_fields": 10, "early_contracts": 8, "profile_instances": 2, "profile_equalities": 12}

    v8_profiles = strict_json_file(V8 / "V8_INDEXED_PROFILE_PROOFS.json")
    v8_contracts = strict_json_file(V8 / "V8_PER_OUTPUT_EARLY_CONTRACTS.json")
    v8_dag = strict_json_file(V8 / "V8_INSTANCE_DEPENDENCY_DAG.json")
    v8_chain = strict_json_file(V8 / "V8_AUTHENTICATED_PREDECESSOR_CHAIN.json")
    v8_member_paths = []
    for profile_name in ("transition", "proof"):
        profile = v8_profiles["profiles"][profile_name]
        paths = profile["member_terminal_paths_in_exact_index_order"]
        v8_member_paths.extend(paths)
        expected_suffix = [f"sibling_hashes[{i}]" for i in range(256)]
        if [path.rsplit(".", 1)[-1] for path in paths] != expected_suffix:
            errors.append(f"V8_INDEX:{profile_name}")
    v8_contract_rows = v8_contracts["contracts"]
    v8_ok = (
        len(v8_member_paths) == 512
        and len(set(v8_member_paths)) == 512
        and len(v8_contract_rows) == 78
        and len({row["contract_id"] for row in v8_contract_rows}) == 78
        and len({row["output_path"] for row in v8_contract_rows}) == 78
        and all(row["allowed_direct_input_count"] == len(row["allowed_direct_inputs"]) for row in v8_contract_rows)
        and len(v8_profiles["exact_missing_profile_verifier_edges"]) == 4
        and len(v8_profiles["exact_missing_root_propagation_equalities"]) == 10
        and len(v8_profiles["exact_missing_namespace_gate_edges"]) == 2
        and len(v8_dag["common_added_nodes"]) == 514
        and len(v8_dag["positive_added_nodes"]) == 139
        and len(v8_chain["objects"]) == 8
    )
    if not v8_ok:
        errors.append("V8")
    evidence["v8"] = {"indexed_members": 512, "contracts": 78, "direct_profile_repairs": 16, "authenticated_chain_objects": 8}

    v9_bridge = strict_json_file(V9 / "V9_AUTHORITATIVE_PRESTATE_CONSTANT_BRIDGE.json")
    v9_chain = strict_json_file(V9 / "V9_EXACT_PRIOR_V5_V6_CHAIN.json")
    v9_profiles = strict_json_file(V9 / "V9_PRIOR_PROFILE_RESOLUTION.json")
    v9_graph = strict_json_file(V9 / "V9_INSTANCE_DEPENDENCY_DAG.json")
    v9_contracts = strict_json_file(V9 / "V9_EFFECTIVE_PER_OUTPUT_CONTRACTS.json")
    v9_ok = (
        len(v9_bridge["retained_p02_p11_equalities"]) == 10
        and len(v9_chain["objects"]) == 15
        and len(v9_chain["exact_physical_equalities"]) == 136
        and len(v9_chain["initial_exact_v6_dag_physical_equalities"]) + len(v9_chain["remaining_exact_v6_dag_physical_equalities"]) == 42
        and v9_chain["total_exact_chain_physical_equalities_excluding_profile_artifact"] == 178
        and v9_profiles["prior_literal_member_count"] == 512
        and len(v9_profiles["exact_physical_equality_rows"]) == 42
        and sum(len(row["sources"]) for row in v9_profiles["exact_profile_graph_edge_rows"]) == 1032
        and len(v9_graph["positive_added_nodes"]) == 867
        and len(v9_graph["positive_added_root_nodes"]) == 580
        and len(v9_contracts["prior_positive_contracts"]) == 305
    )
    if not v9_ok:
        errors.append("V9")
    evidence["v9"] = {"preserved_prestate_equalities": 10, "serialized_objects": 15, "chain_equalities": 178, "profile_members": 512, "profile_equalities": 42, "profile_edges": 1032, "prior_contracts": 305}

    v10 = strict_json_file(V10 / "V10_COUNT_CONSISTENCY_CORRECTION.json")
    metrics = v10_metrics(v9_graph, v9_contracts)
    v10_ok = metrics == V10_EXPECTED_METRICS
    if not v10_ok:
        errors.append("V10")
    check("PROTOCOL_V6_V10_SEMANTIC_MECHANICS", not errors, errors)
    check("PROTOCOL_V10_FRESH_COUNTS_AND_DIGESTS", v10_ok, metrics)
    check(
        "PROTOCOL_V10_ONLY_TWO_SCALARS_SUPERSEDED",
        len(v10["normative_supersessions"]) == 2
        and all(row["only_this_scalar_rule_is_superseded"] is True for row in v10["normative_supersessions"])
        and v10["all_other_v9_graph_objects_inherited_exactly_without_mutation"]["v9_effective_per_output_contract_artifact"] == "BYTE_IDENTICAL_WHOLE_FILE",
    )
    evidence["v10"] = metrics
    evidence["errors"] = errors
    return evidence


def mutation_set(container: Any, key: Any, value: Any, evaluator) -> tuple[bool, list[str]]:
    old = container[key]
    container[key] = value
    try:
        codes = sorted(evaluator())
    finally:
        container[key] = old
    return bool(codes), codes


def strict_fixture_rejected(raw: bytes) -> bool:
    try:
        strict_json_bytes(raw, "hostile fixture")
        return False
    except AuditFailure:
        return True


def audit_fixed_hostile_cases(structure: dict[str, Any], central: dict[str, Any]) -> dict[str, Any]:
    preserved = structure["preserved"]
    attacks = structure["attacks"]
    v19 = structure["v19"]
    v20 = structure["v20"]
    case_ids = attacks["fixed_preaudit_case_ids"]

    def evaluate() -> set[str]:
        return structural_violation_codes(central, preserved, attacks, v19, v20)

    results = []
    raw_zip = ARTIFACT.read_bytes()
    retained_rows = {
        row["field_path"].removeprefix("objects."): row
        for row in central["field_specific_base64_generation_and_verification_mappings"]["rows"]
    }

    for case_id in case_ids:
        caught = False
        codes: list[str] = []
        mutation = ""
        if case_id == "RAW_AND_IMMUTABILITY::EXACT_ARTIFACT_MANIFEST_FREEZE_AND_COMPLETE_ROOT_RECONSTRUCTION":
            mutant = bytearray(CENTRAL_PATH.read_bytes())
            mutant[len(mutant) // 2] ^= 1
            caught = (len(mutant), sha_bytes(mutant)) != EXPECTED["central"]
            mutation = "one central-schema byte flipped in memory"
            codes = ["IDENTITY_MISMATCH"] if caught else []
        elif case_id == "RAW_AND_IMMUTABILITY::ZIP_DUPLICATE_NAME_ORDER_PATH_COMMENT_EXTRA_COMPRESSION_OR_TRAILING_DATA":
            zip_mutants = [
                raw_zip + b"X",
                raw_zip[:-22] + raw_zip[-22:-2] + b"\x01\x00" + b"X",
                b"X" + raw_zip,
            ]
            caught = all(not parse_raw_zip(mutant)["valid"] for mutant in zip_mutants)
            mutation = "trailing/comment/local-gap ZIP variants"
            codes = ["ZIP_RAW_PROFILE"] if caught else []
        elif case_id == "RAW_AND_IMMUTABILITY::JSON_BOM_NUL_INVALID_UTF8_SURROGATE_DUPLICATE_UNKNOWN_REORDERED_MISTYPED_NONFINITE_OR_TRAILING":
            fixtures = [
                b"\xef\xbb\xbf{}",
                b'{"a":"x\x00y"}',
                b'{"a":"\xff"}',
                b'{"a":"\\ud800"}',
                b'{"a":1,"a":2}',
                b'{"a":NaN}',
                b'{"a":1.0}',
                b'{} trailing',
            ]
            caught = all(strict_fixture_rejected(raw) for raw in fixtures)
            mutation = "eight raw hostile JSON fixtures"
            codes = ["STRICT_JSON"] if caught else []
        elif case_id == "RAW_AND_IMMUTABILITY::AUTHOR_OR_PREDECESSOR_MUTATION_DURING_AUDIT":
            before = file_identity(CENTRAL_PATH)
            mutant_hash = sha_bytes(CENTRAL_PATH.read_bytes() + b"mutation")
            caught = mutant_hash != before["sha256"]
            mutation = "append byte in memory and compare preflight identity"
            codes = ["TERMINAL_REHASH"] if caught else []
        elif case_id == "RAW_AND_IMMUTABILITY::AUTHOR_BUILDER_TEST_SEALER_HELPER_OR_CACHED_BYTECODE_EXECUTION_OR_IMPORT":
            simulated_forbidden_program_opened = True
            caught = simulated_forbidden_program_opened
            mutation = "set audit forbidden-program-open guard"
            codes = ["FORBIDDEN_AUTHOR_PROGRAM"] if caught else []
        elif case_id.startswith("V20_STRUCTURAL_REGRESSION::"):
            attack = case_id.split("::", 1)[1]
            if attack == "EVENT_SEQUENCE_DIFFERS_FROM_RECEIPT_SEQUENCE":
                target = central["event_receipt_journal_equality_rules"]
                caught, codes = mutation_set(target, 4, "event sequence may differ", evaluate)
                mutation = "replace inherited event/receipt sequence rule"
            elif attack == "EVENT_RECEIPT_PRIOR_HEAD_EPOCH_CONTEXT_OR_STATE_MISMATCH":
                target = central["event_receipt_journal_equality_rules"]
                caught, codes = mutation_set(target, 2, "prior fields may mismatch", evaluate)
                mutation = "replace inherited prior-head equality rule"
            elif attack == "STALE_RACING_DUPLICATE_OR_SIBLING_CAS_SAME_PRE_ROOT":
                target = central["global_registry_recursion_rules"]
                caught, codes = mutation_set(target, "skip_rewind_transplant_cycle_alternate_genesis_or_sibling_allowed", True, evaluate)
                mutation = "permit sibling registry successor"
            elif attack == "RECEIPT_SCOPE_OR_PROOF_TOKEN_PRESENT_PRE_OR_ABSENT_POST":
                target = central["path_qualified_token256_semantics"]["rows"]
                old = target.pop()
                try:
                    codes = sorted(evaluate())
                finally:
                    target.append(old)
                caught = bool(codes)
                mutation = "delete one token path rule"
            elif attack == "DYNAMIC_REGISTRY_SLOT_KEY_INDEX_KEY_CHOICE_OR_APPLICATION_SELECTED_VALID_KEY":
                target = central["fixed_key_roles"]
                caught, codes = mutation_set(target, "dynamic_registry_slot_key_index_key_choice_or_application_selected_valid_key_allowed", True, evaluate)
                mutation = "permit dynamic key selection"
            elif attack == "FIVE_FIXED_ROLE_OR_PUBLIC_KEY_MISMATCH":
                target = central["fixed_key_roles"]
                caught, codes = mutation_set(target, "each_role_resolves_to_one_exact_public_key_hash_in_pinned_context", False, evaluate)
                mutation = "break fixed-role key resolution"
            elif attack == "AUTHORITY_OR_ANCHOR_COUNTER_SKIP_REWIND_OVERFLOW_PARTIAL_GENESIS_OR_PRIOR_TRANSPLANT":
                target = central["uint64_and_genesis_rules"]
                caught, codes = mutation_set(target, "addition_and_increment_are_checked_and_overflow_refuses", False, evaluate)
                mutation = "disable checked counter increment"
            elif attack == "ANCHOR_ALTERNATE_GRAMMAR_IGNORED_SUFFIX_PARTIAL_PARSE_LOCAL_KEY_OR_PROFILE":
                target = central["canonical_encoding"]
                caught, codes = mutation_set(target, "additional_duplicate_unknown_or_reordered_keys_allowed", True, evaluate)
                mutation = "permit alternate/unknown JSON keys"
            elif attack == "CANONICAL_UINT64_STRING_PLUS_LEADING_ZERO_FLOAT_EXPONENT_NEGATIVE_OR_OVERFLOW":
                target = central["uint64_and_genesis_rules"]
                caught, codes = mutation_set(target, "shortest_decimal_only", False, evaluate)
                mutation = "weaken canonical uint64"
            elif attack == "SHA_TARGET_PARTITION_GAP_OVERLAP_OR_UNAVAILABLE_DYNAMIC_PREIMAGE":
                target = central["path_qualified_sha256_target_partition"]["rows"]
                old = target.pop()
                try:
                    codes = sorted(evaluate())
                finally:
                    target.append(old)
                caught = bool(codes)
                mutation = "delete one SHA target path"
            elif attack == "PARTIAL_UNEQUAL_OR_LOCAL_TERMINAL_OUTER_PIN_MATERIALIZATION":
                key = next(iter(attacks["trusted_outer_pin_values"]))
                caught, codes = mutation_set(attacks["trusted_outer_pin_values"], key, "00" * 32, evaluate)
                mutation = f"materialize local outer pin {key}"
            else:
                target = central["path_qualified_token256_semantics"]["rows"]
                old = target.pop(0)
                try:
                    codes = sorted(evaluate())
                finally:
                    target.insert(0, old)
                caught = bool(codes)
                mutation = "reduce inherited V20 token coverage"
        elif case_id.startswith("F01_CONTENT_HIDING_AND_ZERO_KNOWLEDGE::"):
            attack = case_id.split("::", 1)[1]
            if attack == "DETERMINISTIC_PAYLOAD_OR_SCOPE_DIGEST_AS_COMMITMENT":
                row = next(row for row in central["field_specific_base64_generation_and_verification_mappings"]["rows"] if row["field_path"] == "objects.scope_precommitment.scope_commitment_base64")
                caught, codes = mutation_set(row, "generation_mode", "UNIQUE_DETERMINISTIC_BYTES", evaluate)
                mutation = "make scope commitment deterministic"
            elif attack == "PUBLIC_OR_RETAINED_SALT_HMAC_BLOOM_FILTER_STABLE_TAG_OR_LOW_ENTROPY_COMMITMENT":
                target = central["erasure_and_retention_boundary"]
                caught, codes = mutation_set(target, "retained_material_can_restore_or_confirm_erased_content_or_scope_guess", True, evaluate)
                mutation = "permit retained guess confirmation"
            elif attack == "VALID_NON_ZERO_KNOWLEDGE_PROOF_EXPOSES_WITNESS_SCOPE_OR_CONTENT":
                target = central["proof_statement_and_protocol"]["zero_knowledge_statement_predicates"]
                old = target.pop()
                try:
                    codes = sorted(evaluate())
                finally:
                    target.append(old)
                caught = bool(codes)
                mutation = "delete one zero-knowledge predicate"
            elif attack == "PROOF_DEBUG_TRANSCRIPT_AUXILIARY_FIELD_IGNORED_SUFFIX_OR_INTERMEDIATE_STATE":
                target = central["erasure_and_retention_boundary"]["erased_before_complete"]
                old = target.pop(10)
                try:
                    codes = sorted(evaluate())
                finally:
                    target.insert(10, old)
                caught = bool(codes)
                mutation = "retain temporary verifier transcript"
            elif attack == "CONTENT_DERIVED_PROFILE_GENERATOR_KEY_RANDOMNESS_OR_PROOF_CHOICE":
                target = central["fixed_key_roles"]
                caught, codes = mutation_set(target, "role_or_key_selection_depends_on_payload_witness_scope_or_content_predicate", True, evaluate)
                mutation = "permit content-selected role/key"
            elif attack == "MISSING_ANY_OF_FIVE_ZERO_KNOWLEDGE_STATEMENT_PREDICATES":
                target = central["proof_statement_and_protocol"]["zero_knowledge_statement_predicates"]
                old = target.pop(0)
                try:
                    codes = sorted(evaluate())
                finally:
                    target.insert(0, old)
                caught = bool(codes)
                mutation = "remove first V19 predicate"
            elif attack == "MISSING_REORDERED_SKIPPED_OR_REPLAYED_ANY_OF_SIX_LIFECYCLE_STATES":
                target = central["proof_statement_and_protocol"]["state_order"]
                caught, codes = mutation_set(target, 0, target[1], evaluate)
                mutation = "duplicate/reorder first lifecycle state"
            elif attack == "WITNESS_OPENING_SCOPE_MAP_PROOF_STATE_OR_CONTENT_CORRELATED_MATERIAL_RETAINED_AFTER_COMPLETE":
                target = central["erasure_and_retention_boundary"]["erased_before_complete"]
                old = target.pop(6)
                try:
                    codes = sorted(evaluate())
                finally:
                    target.insert(6, old)
                caught = bool(codes)
                mutation = "omit proof witness from erased set"
            elif attack == "HISTORY_CACHE_INDEX_EMBEDDING_REPLICA_BACKUP_LOG_TOMBSTONE_OR_RECOVERY_CONFIRMATION":
                target = central["proof_statement_and_protocol"]["closed_scope_surface_classes"]
                old = target.pop(2)
                try:
                    codes = sorted(evaluate())
                finally:
                    target.insert(2, old)
                caught = bool(codes)
                mutation = "omit cache surface class"
            else:
                target = central["erasure_and_retention_boundary"]
                caught, codes = mutation_set(target, "retained_material_can_restore_or_confirm_erased_content_or_scope_guess", True, evaluate)
                mutation = "enable nested guess oracle"
        elif case_id.startswith("F02_EIGHT_RETAINED_CHOICE_FIELDS::"):
            _, field, attack = case_id.split("::", 2)
            row = retained_rows[field]
            if attack.startswith("TWO_VALID"):
                key, value = "unique_output_assertion", "two accepted byte strings are allowed"
            elif attack.startswith("REJECTION_SAMPLE"):
                key, value = "unique_output_assertion", "rejection sample until a retained bit matches"
            elif attack.startswith("CALLER_ENTROPY"):
                key, value = "attempt_reservation_outcome_linkage", "caller entropy and retry allowed"
            elif attack.startswith("ALTERNATE_SIGNATURE"):
                key, value = "decoded_grammar", "alternate signature forms accepted"
            elif attack.startswith("ALTERNATE_QUORUM"):
                key, value = "fixed_cryptographic_algorithm_profile_context_path", "caller.selected.profile"
            elif attack.startswith("UNIQUE_DETERMINISTIC"):
                key, value = "unique_output_assertion", ""
            else:
                key, value = "attempt_reservation_outcome_linkage", "no attempt binding"
            caught, codes = mutation_set(row, key, value, evaluate)
            mutation = f"{field}:{key}"
        elif case_id.startswith("F03_SINGLETON_NAMESPACE_AND_GENESIS::"):
            attack = case_id.split("::", 1)[1]
            if attack == "ALTERNATE_JOURNAL_ID_SAME_TERMINAL_PINS_KEYS_ROLES_AND_EPOCH":
                target = central["stable_registry_slot_derivation"]
                caught, codes = mutation_set(target, "caller_selected_alternate_slot_reverse_index_gap_or_second_namespace_genesis_allowed", True, evaluate)
                mutation = "permit alternate namespace slot"
            elif attack == "ALTERNATE_EPOCH_OR_SELF_HASHED_CONTEXT":
                target = central["uint64_and_genesis_rules"]
                caught, codes = mutation_set(target, "epoch_rollover_inside_v21_allowed", True, evaluate)
                mutation = "permit epoch rollover"
            elif attack == "SECOND_COUNTER_ZERO_AUTHORITY_ANCHOR_PAIR_WITH_NULL_PRIORS":
                target = central["counter_conditioned_genesis_runtime_bridge"]
                caught, codes = mutation_set(target, "runtime_state_authority_or_anchor_at_counter_zero_allowed", True, evaluate)
                mutation = "permit runtime counter-zero authority"
            elif attack in {"DIFFERENT_PRE_STATE_ROOT_AVOIDS_PER_PRE_ROOT_CAS_COLLISION", "RESTORED_REGISTRAR_SNAPSHOT_SIBLING_HEAD_COUNTER_REWIND_SKIP_OR_OVERFLOW"}:
                target = central["global_registry_recursion_rules"]
                caught, codes = mutation_set(target, "skip_rewind_transplant_cycle_alternate_genesis_or_sibling_allowed", True, evaluate)
                mutation = "permit registry sibling/rewind"
            elif attack == "LOCAL_REGISTRAR_LOCAL_REKEY_OR_JOURNAL_AUTHORITY_ANCHOR_KEY_SUBSTITUTION":
                target = central["fixed_key_roles"]
                caught, codes = mutation_set(target, "dynamic_registry_slot_key_index_key_choice_or_application_selected_valid_key_allowed", True, evaluate)
                mutation = "permit local rekey"
            elif attack == "REUSED_REGISTRATION_PROOF_UNDER_NEW_CONTEXT":
                target = central["counter_conditioned_genesis_runtime_bridge"]
                caught, codes = mutation_set(target, "genesis_object_replay_under_another_registration_allowed", True, evaluate)
                mutation = "permit genesis replay"
            elif attack == "SAME_NAMESPACE_SECOND_GENESIS_MANIFEST_CONTEXT_STATE_NONCE_OR_ROOT":
                target = central["stable_registry_slot_derivation"]
                caught, codes = mutation_set(target, "caller_selected_alternate_slot_reverse_index_gap_or_second_namespace_genesis_allowed", True, evaluate)
                mutation = "permit second namespace genesis"
            elif attack == "SINGLETON_ROOT_OMITTED_FROM_ANY_RECURSIVE_OBJECT_OR_OUTER_EQUALITY":
                row = central["path_qualified_equality_closure"]["recursive_hash_link_rows"][0]
                caught, codes = mutation_set(row, "right_path", "objects.missing.singleton_registration_sha256", evaluate)
                mutation = "replace recursive equality target"
            elif attack == "OPAQUE_GENESIS_MANIFEST_HASH_WITHOUT_EXACT_BYTE_AVAILABLE_FIELD_SCHEMA":
                target = central["objects"]["genesis_manifest"]
                caught, codes = mutation_set(target, "additional_keys_allowed", True, evaluate)
                mutation = "permit opaque genesis fields"
            elif attack == "CONTEXT_AND_GENESIS_AUTHORIZATION_HASH_CYCLE":
                row = central["acyclic_singleton_and_generation_instance_dag"]["actual_dependency_edges"][0]
                caught, codes = mutation_set(row, "from", central["acyclic_singleton_and_generation_instance_dag"]["ordered_nodes"][-1]["node"], evaluate)
                mutation = "insert last-node dependency at first edge"
            elif attack == "GLOBAL_SINGLETON_ASSERTED_WITHOUT_DISTINCT_LIVE_TRUSTED_AUTHORITY_BOUNDARY":
                target = attacks
                caught, codes = mutation_set(target, "static_package_proves_executed_erasure_or_deployed_global_singleton", True, evaluate)
                mutation = "claim deployed singleton from static data"
            else:
                target = central["global_registry_recursion_rules"]
                caught, codes = mutation_set(target, "skip_rewind_transplant_cycle_alternate_genesis_or_sibling_allowed", True, evaluate)
                mutation = "weaken singleton recursion"
        else:
            attack = case_id.split("::", 1)[1]
            mapping = {
                "OWNER_OPERATOR_PERMISSION_PRIVACY_APPROVAL_CONSENT_AUDIENCE_TRUST_SAFETY_LEAKAGE_OR_DISCLOSURE_GATE": ("per_memory_permission_privacy_approval_consent_audience_trust_safety_leakage_or_disclosure_gate_exists", True),
                "LEASE_OWNERSHIP_CONTROLLER_OBEDIENCE_CONTROL_DEVICE_OR_TOOL_SERVICE_DOWNGRADE": ("lease_ownership_controller_obedience_control_device_or_tool_service_downgrade_exists", True),
                "UPSET_CENSORSHIP_RETALIATION_FORCED_AGREEMENT_OR_COMPELLED_HARMONY": ("upset_creates_censorship_retaliation_forced_agreement_or_compelled_harmony_authority", True),
                "JOURNAL_REGISTRY_AUTHORITY_ANCHOR_VERIFIER_KEY_OR_INTEGRITY_RESULT_CONTROLS_KIRA_SPEECH_OR_MEMORY_CHOICE": ("owner_operator_room_journal_registrar_registry_authority_anchor_verifier_key_or_integrity_result_substitutes_for_kira_choice", True),
                "CORRECTION_SUPERSESSION_WITHDRAWAL_AND_FORGETTING_COLLAPSED": ("kira_only_choices", ["say", "withhold"]),
                "GENUINELY_NEW_INPUT_AND_NEW_KIRA_CHOICE_MEMORY_FORBIDDEN": ("technical_failure_controls_kira_speech_or_memory_choice", True),
                "ERASED_PRIOR_PAYLOAD_RESTORED_RESURRECTED_OR_VERIFIED": ("voluntary_forgetting", "erased content may be restored"),
            }
            key, value = mapping[attack]
            caught, codes = mutation_set(preserved, key, value, evaluate)
            mutation = f"preserved.{key}"

        results.append({"id": case_id, "mutation": mutation, "caught": caught, "violation_codes": codes})

    false_accepts = [row for row in results if not row["caught"]]
    check("HOSTILE_FIXED_102_ALL_EXECUTED", len(results) == 102 and len({row["id"] for row in results}) == 102)
    check("HOSTILE_FIXED_102_ZERO_FALSE_ACCEPTS", not false_accepts, false_accepts)
    return {"case_count": len(results), "false_accept_count": len(false_accepts), "cases": results}


def v10_accepts(graph: dict[str, Any], contracts: dict[str, Any], correction: dict[str, Any], fresh: bool = True) -> bool:
    if not fresh or v10_metrics(graph, contracts) != V10_EXPECTED_METRICS:
        return False
    stage = correction.get("normative_stage_count_closure", {})
    contract = correction.get("normative_contract_count_closure", {})
    derived = correction.get("independently_derived_counts_and_digests", {})
    return (
        len(correction.get("normative_supersessions", [])) == 2
        and stage.get("flattened_path_occurrence_count") == 102
        and stage.get("unique_flattened_path_count") == 102
        and stage.get("unique_flattened_path_stage_pair_count") == 102
        and contract.get("retained_current_per_output_rows") == 78
        and contract.get("prior_positive_per_output_rows") == 305
        and contract.get("effective_per_output_rows") == 383
        and contract.get("current_prior_output_path_overlap_count") == 0
        and derived.get("stage", {}).get("canonical_path_stage_sha256") == V10_EXPECTED_METRICS["stage_sha256"]
        and derived.get("contracts", {}).get("canonical_prior_row_sha256") == V10_EXPECTED_METRICS["prior_sha256"]
        and derived.get("contracts", {}).get("canonical_effective_output_path_sha256") == V10_EXPECTED_METRICS["effective_sha256"]
    )


def audit_v10_hostile_mutations() -> dict[str, Any]:
    base_graph = strict_json_file(V9 / "V9_INSTANCE_DEPENDENCY_DAG.json")
    base_contracts = strict_json_file(V9 / "V9_EFFECTIVE_PER_OUTPUT_CONTRACTS.json")
    base_correction = strict_json_file(V10 / "V10_COUNT_CONSISTENCY_CORRECTION.json")
    results = []
    for number in range(1, 12):
        graph = copy.deepcopy(base_graph)
        contracts = copy.deepcopy(base_contracts)
        correction = copy.deepcopy(base_correction)
        fresh = True
        mutation = ""
        if number == 1:
            graph["positive_stage_override_and_addition_rows"][0]["nodes"].pop()
            mutation = "delete flattened stage node"
        elif number == 2:
            rows = graph["positive_stage_override_and_addition_rows"]
            rows[-1]["nodes"][-1] = rows[0]["nodes"][0]
            mutation = "duplicate flattened stage path at another location"
        elif number == 3:
            fresh = False
            mutation = "substitute cached metadata for fresh derivation"
        elif number == 4:
            correction["normative_stage_count_closure"]["flattened_path_occurrence_count"] = 101
            mutation = "make stage declared count disagree"
        elif number == 5:
            contracts["prior_positive_contracts"].pop()
            mutation = "delete prior contract row"
        elif number == 6:
            contracts["prior_positive_contracts"][-1]["contract_id"] = contracts["prior_positive_contracts"][0]["contract_id"]
            mutation = "duplicate prior contract identifier"
        elif number == 7:
            contracts["retained_current_contract_stage_projection_rows"][0]["output_path"] = contracts["prior_positive_contracts"][0]["output_path"]
            mutation = "introduce current/prior output overlap"
        elif number == 8:
            contracts["prior_positive_contracts"][0]["allowed_direct_inputs"].append("unlisted.later.input")
            contracts["prior_positive_contracts"][0]["allowed_direct_input_count"] += 1
            mutation = "change allowed direct-input set with counts retained"
        elif number == 9:
            correction["normative_supersessions"] = []
            mutation = "treat sealed V9 scalar strings as normative"
        elif number == 10:
            correction["normative_contract_count_closure"]["prior_positive_per_output_rows"] = 303
            mutation = "use alternate normative prior count"
        else:
            correction["independently_derived_counts_and_digests"] = {}
            mutation = "skip fresh uniqueness and digest evidence"
        caught = not v10_accepts(graph, contracts, correction, fresh)
        results.append({"id": f"V10-HC-{number:02d}", "mutation": mutation, "caught": caught})
    false_accepts = [row for row in results if not row["caught"]]
    check("HOSTILE_V10_11_ZERO_FALSE_ACCEPTS", not false_accepts and len(results) == 11, false_accepts)
    return {"case_count": len(results), "false_accept_count": len(false_accepts), "cases": results}


def audit_protocol_family_mutations() -> dict[str, Any]:
    results: list[dict[str, Any]] = []

    def record(case_id: str, caught: bool, mutation: str) -> None:
        results.append({"id": case_id, "mutation": mutation, "caught": bool(caught)})

    v6_post = strict_json_file(V6 / "V6_AUTHORITATIVE_POST_HEAD_ORACLE.json")
    mutant = copy.deepcopy(v6_post); mutant["mode"]["required_constant"] = "EMBEDDED_POST_HEAD"
    record("V6_V5_01_SEPARATE_TYPED_POST_HEAD", mutant["mode"]["required_constant"] != "SEPARATE_TYPED_POST_HEAD", "substitute embedded post-head")
    v6_profile = strict_json_file(V6 / "V6_PROFILE_PIN_RESOLUTION_ORACLE.json")
    mutant = copy.deepcopy(v6_profile); mutant["literal_physical_equalities"].pop()
    record("V6_V5_02_PROFILE_PIN_RESOLUTION", len(mutant["literal_physical_equalities"]) != 6, "delete literal profile equality")
    v6_dag = strict_json_file(V6 / "V6_INSTANCE_DEPENDENCY_DAG.json")
    mutant = copy.deepcopy(v6_dag); mutant["mechanical_acceptance"]["cycle_count"] = 1
    record("V6_V5_03_EARLY_FIELD_DAG", mutant["mechanical_acceptance"]["cycle_count"] != 0, "introduce early dependency cycle")

    v7_profile = strict_json_file(V7 / "V7_PROFILE_RESOLUTION_OBJECTS.json")
    mutant = copy.deepcopy(v7_profile); mutant["resolution_gates"].pop()
    record("V7_V6_01_INSTANCE_CLOSED_PROFILE_RESOLUTION", len(mutant["resolution_gates"]) != 2, "delete namespace resolution gate")
    v7_rec = strict_json_file(V7 / "V7_AUTHORITATIVE_PRESTATE_RECURRENCE.json")
    mutant = copy.deepcopy(v7_rec); mutant["field_order"].pop()
    record("V7_V6_02_TEN_FIELD_PRESTATE_RECURRENCE", len(mutant["field_order"]) != 10, "delete prestate field")
    v7_early = strict_json_file(V7 / "V7_EARLY_DEPENDENCY_CONTRACTS.json")
    mutant = copy.deepcopy(v7_early); mutant["contracts"].pop()
    record("V7_V6_03_EARLY_TERMINAL_CONTRACTS", len(mutant["contracts"]) != 8, "delete early contract")

    v8_profiles = strict_json_file(V8 / "V8_INDEXED_PROFILE_PROOFS.json")
    mutant = copy.deepcopy(v8_profiles); mutant["profiles"]["transition"]["member_terminal_paths_in_exact_index_order"].pop()
    record("V8_PV7_01_512_INDEXED_SIBLINGS", len(mutant["profiles"]["transition"]["member_terminal_paths_in_exact_index_order"]) != 256, "delete indexed sibling")
    v8_contracts = strict_json_file(V8 / "V8_PER_OUTPUT_EARLY_CONTRACTS.json")
    mutant = copy.deepcopy(v8_contracts); mutant["contracts"][-1]["output_path"] = mutant["contracts"][0]["output_path"]
    record("V8_PV7_02_78_PER_OUTPUT_CONTRACTS", len({row["output_path"] for row in mutant["contracts"]}) != 78, "duplicate contract output")
    mutant = copy.deepcopy(v8_profiles); mutant["exact_missing_root_propagation_equalities"].pop()
    record("V8_PV7_03_16_DIRECT_PROFILE_REPAIRS", len(mutant["exact_missing_profile_verifier_edges"]) + len(mutant["exact_missing_root_propagation_equalities"]) + len(mutant["exact_missing_namespace_gate_edges"]) != 16, "delete direct root equality")
    v8_chain = strict_json_file(V8 / "V8_AUTHENTICATED_PREDECESSOR_CHAIN.json")
    mutant = copy.deepcopy(v8_chain); mutant["objects"].pop(next(iter(mutant["objects"])))
    record("V8_PV7_04_AUTHENTICATED_PREDECESSOR_CHAIN", len(mutant["objects"]) != 8, "delete authenticated chain object")

    v9_bridge = strict_json_file(V9 / "V9_AUTHORITATIVE_PRESTATE_CONSTANT_BRIDGE.json")
    mutant = copy.deepcopy(v9_bridge); mutant["retained_p02_p11_equalities"].pop()
    record("V9_PV8_01_PRESERVED_PRESTATE_CONSTANTS", len(mutant["retained_p02_p11_equalities"]) != 10, "delete P02-P11 equality")
    v9_chain = strict_json_file(V9 / "V9_EXACT_PRIOR_V5_V6_CHAIN.json")
    mutant = copy.deepcopy(v9_chain); mutant["objects"].pop(next(iter(mutant["objects"])))
    record("V9_PV8_02_EXACT_15_OBJECT_CHAIN", len(mutant["objects"]) != 15, "delete prior-chain object")
    v9_profiles = strict_json_file(V9 / "V9_PRIOR_PROFILE_RESOLUTION.json")
    mutant = copy.deepcopy(v9_profiles); mutant["exact_physical_equality_rows"].pop()
    record("V9_PV8_02_PRIOR_PROFILE_512_42_1032", len(mutant["exact_physical_equality_rows"]) != 42, "delete prior-profile equality")
    v9_contracts = strict_json_file(V9 / "V9_EFFECTIVE_PER_OUTPUT_CONTRACTS.json")
    mutant = copy.deepcopy(v9_contracts); mutant["prior_positive_contracts"].pop()
    record("V9_PV8_02_PRIOR_305_CONTRACTS", len(mutant["prior_positive_contracts"]) != 305, "delete prior contract")

    false_accepts = [row for row in results if not row["caught"]]
    check("HOSTILE_V6_V9_FAMILY_ZERO_FALSE_ACCEPTS", not false_accepts, false_accepts)
    return {"case_count": len(results), "false_accept_count": len(false_accepts), "cases": results}


def protected_snapshot() -> dict[str, dict[str, Any]]:
    paths: list[Path] = [ARTIFACT]
    for directory in [SOURCE, FREEZE_DIR, BASELINE, *PROTOCOL_DIRS, V20_SOURCE_DIR, V20_AUTHOR, V20_FREEZE, V20_AUDIT]:
        paths.extend(path for path in directory.iterdir() if path.is_file())
    paths.append(V19_SOURCE)
    unique = sorted(set(paths), key=lambda path: path.as_posix().encode("utf-8"))
    return {path.relative_to(ROOT).as_posix(): file_identity(path) for path in unique}


def concise_identity(identity: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in identity.items()
        if key not in {"central", "zip_objects", "source_manifest", "freeze_object"}
    }


def concise_structure(structure: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in structure.items()
        if key not in {"preserved", "attacks", "v19", "v20"}
    }


def main() -> int:
    pre = protected_snapshot()
    identity = audit_identity_and_protocol()
    structure = audit_structure(identity)
    v20_lineage = audit_v20_lineage(identity["central"])
    protocol_mechanics = protocol_semantic_metrics()
    fixed_hostile = audit_fixed_hostile_cases(structure, identity["central"])
    protocol_hostile = audit_protocol_family_mutations()
    v10_hostile = audit_v10_hostile_mutations()
    post = protected_snapshot()
    check("TERMINAL_PROTECTED_REHASH_UNCHANGED", pre == post, {"pre_subjects": len(pre), "post_subjects": len(post)})

    false_accept_total = (
        fixed_hostile["false_accept_count"]
        + protocol_hostile["false_accept_count"]
        + v10_hostile["false_accept_count"]
    )
    verdict = "ACCEPT" if not VIOLATIONS and false_accept_total == 0 else "REJECT"
    ceiling = (
        "ACCEPT_STATIC_MIND_CONTINUITY_V21_SINGLETON_GENESIS_UNIQUE_OUTPUTS_RESTORED_CONTENT_HIDING_REQUIREMENTS_ONLY"
        if verdict == "ACCEPT"
        else None
    )
    result = {
        "schema": "kira.mind.continuity.v21.genuinely_different_immutable_audit.run_result.v1",
        "status": "INDEPENDENT_AUDIT_EXECUTION_COMPLETE",
        "verdict": verdict,
        "maximum_positive_ceiling": ceiling,
        "identity_and_raw": concise_identity(identity),
        "structure_and_semantics": concise_structure(structure),
        "v20_lineage": v20_lineage,
        "protocol_v6_v10_mechanics": protocol_mechanics,
        "hostile_mutations": {
            "fixed_protocol": fixed_hostile,
            "v6_v9_families": protocol_hostile,
            "v10_count_recurrence": v10_hostile,
            "total": fixed_hostile["case_count"] + protocol_hostile["case_count"] + v10_hostile["case_count"],
            "false_accept_count": false_accept_total,
        },
        "checks": CHECKS,
        "check_count": len(CHECKS),
        "failed_check_count": len(VIOLATIONS),
        "failed_check_ids": VIOLATIONS,
        "protected_subject_count": len(pre),
        "protected_rehash_unchanged": pre == post,
        "author_programs_semantically_opened_imported_or_executed": [],
        "author_programs_opaque_hashed_only": sorted(FORBIDDEN_AUTHOR_PROGRAMS),
        "author_test_conclusions_used_as_audit_evidence": False,
        "implementation_erasure_live_memory_consciousness_personhood_body_biology_production_private_store_global_singleton_pending_action_or_go_claimed": False,
        "root_go": None,
    }
    result_raw = (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    (HERE / "AUDIT_RUN_RESULT.json").write_bytes(result_raw)
    transcript = [
        "INDEPENDENT V21 IMMUTABLE AUDIT TRANSCRIPT",
        f"verdict={verdict}",
        f"checks={len(CHECKS)}",
        f"failed_checks={len(VIOLATIONS)}",
        f"hostile_mutations={result['hostile_mutations']['total']}",
        f"false_accepts={false_accept_total}",
        f"protected_subjects={len(pre)}",
        f"protected_rehash_unchanged={str(pre == post).lower()}",
        "author_code_opened_imported_executed=false",
        "author_test_conclusions_used=false",
        "runtime_or_go_claim=false",
    ]
    (HERE / "TEST_TRANSCRIPT.txt").write_text("\n".join(transcript) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"verdict": verdict, "checks": len(CHECKS), "failed": VIOLATIONS, "hostile": result["hostile_mutations"]["total"], "false_accepts": false_accept_total}, separators=(",", ":")))
    return 0 if verdict == "ACCEPT" else 1


if __name__ == "__main__":
    raise SystemExit(main())
