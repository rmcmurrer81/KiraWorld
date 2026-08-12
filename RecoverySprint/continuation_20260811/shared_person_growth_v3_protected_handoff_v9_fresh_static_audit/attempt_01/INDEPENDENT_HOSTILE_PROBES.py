from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any
import warnings

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, utils
import pefile


KIRA = Path(r"C:\Users\robmc\Kira")
INSTALLED = KIRA / r"RecoverySprint\continuation_20260811\shared_person_growth_v3_protected_handoff_v9_static_preparation\attempt_01"
AUDIT = Path(r"C:\Users\robmc\Documents\Codex\2026-08-11\c\work\growth_v9_fresh_audit")
COPY = AUDIT / "candidate_copy"
RESULT = AUDIT / "HOSTILE_PROBE_RESULT.json"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def strict_json(path: Path) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        output: dict[str, Any] = {}
        for key, value in items:
            if key in output:
                raise AssertionError(f"duplicate JSON key: {path}: {key}")
            output[key] = value
        return output

    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs)


def exact_inventory(root: Path) -> dict[str, Any]:
    manifest = strict_json(root / "SEALED_MANIFEST.json")
    files = {
        path.relative_to(root).as_posix(): path
        for path in root.rglob("*")
        if path.is_file()
    }
    subject_names: set[str] = set()
    canonical = bytearray()
    mismatches: list[str] = []
    for subject in manifest["subjects"]:
        name = subject["path"]
        subject_names.add(name)
        path = files.get(name)
        if path is None or path.is_symlink():
            mismatches.append(f"missing_or_linked:{name}")
            continue
        data = path.read_bytes()
        actual = digest(data)
        if len(data) != subject["bytes"] or actual != subject["sha256"]:
            mismatches.append(f"content:{name}")
        canonical.extend(f"{name}\0{len(data)}\0{actual}\n".encode("utf-8"))
    extras = sorted(set(files) - subject_names - {"SEALED_MANIFEST.json"})
    root_hash = digest(bytes(canonical))
    return {
        "actual_files": len(files),
        "subject_count": len(manifest["subjects"]),
        "mismatches": mismatches,
        "extras": extras,
        "subject_root_sha256": root_hash,
        "declared_subject_root_sha256": manifest["subject_root_sha256"],
        "manifest_bytes": (root / "SEALED_MANIFEST.json").stat().st_size,
        "manifest_sha256": digest((root / "SEALED_MANIFEST.json").read_bytes()),
    }


def verify_receipts() -> dict[str, Any]:
    fixture_dir = COPY / "Testing" / "fixtures"
    raw_key = (COPY / "Data" / "foundation" / "shared_growth_v9_authority_public_key.bin").read_bytes()
    assert len(raw_key) == 64
    x = int.from_bytes(raw_key[:32], "big")
    y = int.from_bytes(raw_key[32:], "big")
    public = ec.EllipticCurvePublicNumbers(x, y, ec.SECP256R1()).public_key()
    verified = 0
    modes: set[str] = set()
    authority_ids: set[str] = set()
    for path in sorted(fixture_dir.glob("*.receipt")):
        raw = path.read_bytes()
        lines = raw.splitlines(keepends=True)
        assert len(lines) == 41 and lines[-1].startswith(b"signature_hex=")
        body = b"".join(lines[:-1])
        signature = bytes.fromhex(lines[-1].split(b"=", 1)[1].decode("ascii").strip())
        assert len(signature) == 64
        der = utils.encode_dss_signature(
            int.from_bytes(signature[:32], "big"),
            int.from_bytes(signature[32:], "big"),
        )
        try:
            public.verify(der, body, ec.ECDSA(hashes.SHA256()))
        except InvalidSignature as error:
            raise AssertionError(f"invalid fixture signature: {path.name}") from error
        fields = {
            line.split(b"=", 1)[0].decode("ascii"): line.split(b"=", 1)[1].decode("ascii").strip()
            for line in lines[:-1]
        }
        verified += 1
        modes.add(fields["authorization_mode"])
        authority_ids.add(fields["authority_id"])
    return {
        "fixture_receipts_signature_verified_read_only": verified,
        "authorization_modes": sorted(modes),
        "authority_ids": sorted(authority_ids),
        "public_key_sha256": digest(raw_key),
        "used_for_integration": False,
        "candidate_executable_invoked": False,
    }


def literal_value(node: ast.AST, names: dict[str, str]) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return names.get(node.id)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left, right = literal_value(node.left, names), literal_value(node.right, names)
        return left + right if left is not None and right is not None else None
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
            else:
                return None
        return "".join(parts)
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "join"
        and len(node.args) == 1
    ):
        separator = literal_value(node.func.value, names)
        sequence = node.args[0]
        if separator is not None and isinstance(sequence, (ast.List, ast.Tuple)):
            values = [literal_value(item, names) for item in sequence.elts]
            if all(value is not None for value in values):
                return separator.join(value for value in values if value is not None)
    return None


NEEDLES = (
    "shared_person_growth_v3_integration_candidate_v8",
    "shared_growth_v9_native_anchor",
    "shared_growth_v9_public_template",
)


def semantic_hits(source: str) -> set[str]:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SyntaxWarning)
        tree = ast.parse(source)
    names: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            value_node = node.value
            value = literal_value(value_node, names) if value_node is not None else None
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if value is not None:
                for target in targets:
                    if isinstance(target, ast.Name):
                        names[target.id] = value
    hits: set[str] = set()
    for node in ast.walk(tree):
        values: list[str] = []
        if isinstance(node, ast.Import):
            values.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                values.append(node.module)
            values.extend(alias.name for alias in node.names)
        else:
            value = literal_value(node, names)
            if value is not None:
                values.append(value)
        for value in values:
            for needle in NEEDLES:
                if needle in value:
                    hits.add(needle)
    return hits


def scanner_probes() -> dict[str, Any]:
    caught = '''
part = "shared_person_growth_v3_" + "integration_candidate_v8"
other = "".join(["shared_growth_", "v9_native_anchor"])
'''
    evasions = {
        "format_call": 'target = "{}{}".format("shared_growth_v9_", "native_anchor")',
        "bytes_decode": 'target = b"shared_growth_v9_native_anchor".decode("ascii")',
        "replace_call": 'target = "shared_growth_v9_x".replace("_x", "_native_anchor")',
        "dynamic_fstring": 'tail = "native_anchor"\ntarget = f"shared_growth_v9_{tail}"',
    }
    evasion_hits = {name: sorted(semantic_hits(source)) for name, source in evasions.items()}
    root_entries = sorted(path.name for path in KIRA.glob("*.py") if path.is_file())
    omitted_counts: dict[str, int] = {}
    for name in ("Avatar", "Testing", "Data", "System", "legacy_reference", "VideoStudioDevelopment"):
        root = KIRA / name
        omitted_counts[name] = sum(1 for _ in root.rglob("*.py")) if root.is_dir() else 0
    prefix_exemption_example = "Core/shared_person_growth_v3_integration_candidate_v8_receiver.py"
    prefix_would_be_skipped = prefix_exemption_example.startswith(
        "Core/shared_person_growth_v3_integration_candidate_v"
    )
    return {
        "author_positive_fixture_hits": sorted(semantic_hits(caught)),
        "evasion_hits": evasion_hits,
        "evasion_count_with_zero_hits": sum(not hits for hits in evasion_hits.values()),
        "root_level_python_files_excluded": len(root_entries),
        "root_level_entrypoint_examples": [
            name for name in ("chat_kira.py", "chat_lisa.py", "voice_kira.py") if name in root_entries
        ],
        "omitted_python_directory_counts": omitted_counts,
        "candidate_prefix_exemption_example": prefix_exemption_example,
        "candidate_prefix_exemption_would_skip_consumer": prefix_would_be_skipped,
        "only_python_source_scanned": True,
        "syntax_and_unicode_errors_are_silently_skipped_by_author_scanner": True,
    }


def route_and_variant_checks() -> dict[str, Any]:
    routes_path = COPY / "Data" / "foundation" / "shared_growth_v9_recipient_routes.tsv"
    rows = [line.split("\t") for line in routes_path.read_text(encoding="ascii").splitlines()]
    existing = [row for row in rows if not row[0].startswith("creator:")]
    creators = [row for row in rows if row[0].startswith("creator:")]
    variants_path = COPY / "Data" / "foundation" / "shared_growth_v9_private_variant_control.tsv"
    variants = [line.split("\t") for line in variants_path.read_text(encoding="ascii").splitlines()]
    # BuildOutput deliberately omits the private entry id (column 0) and emits
    # only source_kind through public_projection_set (columns 1..7).
    projections = [row[1:8] for row in variants]
    projection_text = json.dumps(projections, sort_keys=True).lower()
    forbidden = ("fatal", "death", "trauma", "prefatal", "branch", "cutoff", "activation",
                 "2012001", "2018001", "1963112201", "1963112202")
    template = strict_json(COPY / "Data" / "foundation" / "shared_growth_v9_public_template.json")
    return {
        "route_rows": len(rows),
        "existing_routes": len(existing),
        "creator_routes": len(creators),
        "unique_route_ids": len({row[0] for row in rows}),
        "sarah_frozen_routes": sum(row[6] == "frozen_no_handoff" for row in rows),
        "biological_robert_exact_route_or_person_present": any(
            field == "biological_robert" for row in rows for field in row
        ),
        "synthetic_robert_exact_class": next(row[3] for row in rows if row[0] == "profile:robert_mcmurrer_presence_ai"),
        "kira_maturity": next(row[4] for row in rows if row[0] == "permanent:kira"),
        "lisa_maturity": next(row[4] for row in rows if row[0] == "permanent:lisa"),
        "marinette_maturity": next(row[4] for row in rows if row[0] == "profile:ladybug_marinette_expanded_smoke"),
        "variant_rows": len(variants),
        "variant_columns_each": [len(row) for row in variants],
        "variant_ordinals_strict": [int(row[11]) < int(row[12]) for row in variants],
        "person_visible_projection_forbidden_tokens": [token for token in forbidden if token in projection_text],
        "private_entry_id_and_controller_only_columns_excluded_from_projection": 16,
        "controller_table_readable_to_same_user": os.access(variants_path, os.R_OK),
        "controller_table_installed_inside_candidate": True,
        "template_fresh_maturity": template["adult_education"]["fresh_person_default_maturity"],
        "template_full_adult_for_unresolved_or_non_adult": template["adult_education"]["full_adult_curriculum_for_unresolved_or_non_adult"],
        "template_private_copy_allowed": template["copy_boundary"]["copy_private_memory_backstory_reflection_emotion_desire_preference_relationship_maturity_consent_roots_anatomy_measurements_or_identity_data"],
    }


def native_static_checks() -> dict[str, Any]:
    source = (COPY / "native" / "shared_growth_v9_native_anchor.cpp").read_text(encoding="utf-8")
    test_source = (COPY / "Testing" / "run_shared_growth_v9_author_tests.py").read_text(encoding="utf-8")
    seal_source = (COPY / "Testing" / "verify_shared_growth_v9_seal.py").read_text(encoding="utf-8")
    trust_fields_match = re.search(r"kReceiptOrder\s*=\s*\{(.*?)\};", source, re.S)
    assert trust_fields_match is not None
    receipt_fields = re.findall(r'"([a-z0-9_]+)"', trust_fields_match.group(1))
    missing_provenance_fields = [
        name for name in (
            "recipient_consent_receipt_sha256",
            "recipient_consent_signature",
            "recipient_consent_key_sha256",
            "revocation_registry_sha256",
            "revocation_epoch",
            "consent_observed_unix_ms",
        ) if name not in receipt_fields
    ]
    acl_apis = (
        "SetNamedSecurityInfoW", "SetFileSecurityW", "GetSecurityInfo", "GetNamedSecurityInfoW",
        "ConvertStringSecurityDescriptorToSecurityDescriptorW", "SetSecurityInfo",
    )
    stable_identity_markers = (
        "dwVolumeSerialNumber", "nFileIndexHigh", "nFileIndexLow", "FileIdInfo",
        "GetFileInformationByHandleEx", "FILE_ID_INFO",
    )
    pe = pefile.PE(str(COPY / "build" / "shared_growth_v9_native_anchor.exe"), fast_load=False)
    imports = sorted(
        entry.dll.decode("ascii").lower()
        for entry in pe.DIRECTORY_ENTRY_IMPORT
    )
    dll = pe.OPTIONAL_HEADER.DllCharacteristics
    return {
        "receipt_field_count": len(receipt_fields),
        "missing_person_consent_and_revocation_provenance_fields": missing_provenance_fields,
        "single_compiled_public_key_hash": source.count("kPublicKeySha[]") == 1,
        "same_signature_verifier_feeds_policy_containing_both_modes": (
            source.index("VerifySignature(receipt, key_bytes)")
            < source.index("ValidateReceiptPolicy(receipt, route, ledger_root")
            and 'mode == "author_test"' in source
            and 'mode == "independent_acceptance"' in source
        ),
        "independent_acceptance_uses_distinct_public_key": False,
        "consumer_binding_is_only_supplied_bytes_hash_and_entrypoint_string": (
            'Field(receipt, "consumer_artifact_sha256") != Sha256(consumer)' in source
            and 'Field(receipt, "consumer_entrypoint_id")' in source
        ),
        "consumer_path_or_loaded_process_identity_bound": False,
        "secure_dacl_api_markers_present": [name for name in acl_apis if name in source],
        "stable_file_identity_markers_present": [name for name in stable_identity_markers if name in source],
        "ledger_anchor_debt_same_directory": all(
            marker in source for marker in ("ledger_path = ledger_root", "anchor_path = ledger_root", "debt_path = ledger_root")
        ),
        "check_then_pathname_operations_present": all(
            marker in source for marker in ("CheckExistingPathComponentsNoReparse", "CreateDirectoryW", "MoveFileExW")
        ),
        "platform_separated_or_hardware_anchor_present": False,
        "installed_test_hardcoded_author_root": r"work\growth_v9_author" in test_source,
        "installed_seal_verifier_hardcoded_author_root": r"work\growth_v9_author" in seal_source,
        "pe_machine": hex(pe.FILE_HEADER.Machine),
        "pe_magic": hex(pe.OPTIONAL_HEADER.Magic),
        "pe_imports": imports,
        "pe_aslr": bool(dll & 0x40),
        "pe_high_entropy_va": bool(dll & 0x20),
        "pe_nx": bool(dll & 0x100),
        "pe_cfg": bool(dll & 0x4000),
    }


def install_metadata_checks() -> dict[str, Any]:
    manifest = strict_json(COPY / "SEALED_MANIFEST.json")
    contract = strict_json(COPY / "STATIC_CONTRACT.json")
    checkpoint = (COPY / "CHECKPOINT.md").read_text(encoding="utf-8")
    return {
        "manifest_installed_in_kira": manifest["installed_in_kira"],
        "contract_author_package_installed_in_kira": contract["promotion_boundary"]["author_package_installed_in_kira"],
        "checkpoint_says_not_installed": "It is not installed" in checkpoint,
        "actual_installed_path_exists": INSTALLED.is_dir(),
    }


def rebuild_checks() -> dict[str, Any]:
    installed_exe = COPY / "build" / "shared_growth_v9_native_anchor.exe"
    copied_source_rebuild = AUDIT / "rebuild" / "shared_growth_v9_native_anchor.exe"
    installed_source_rebuild = AUDIT / "rebuild_installed_source_path" / "shared_growth_v9_native_anchor.exe"
    author_path_rebuild = AUDIT / "rebuild_author_source_path" / "shared_growth_v9_native_anchor.exe"
    copied_analysis = AUDIT / "rebuild" / "shared_growth_v9_native_anchor.nativecodeanalysis.xml"
    installed_analysis = AUDIT / "rebuild_installed_source_path" / "shared_growth_v9_native_anchor.nativecodeanalysis.xml"
    author_analysis = AUDIT / "rebuild_author_source_path" / "shared_growth_v9_native_anchor.nativecodeanalysis.xml"
    installed_hash = digest(installed_exe.read_bytes())
    copied_hash = digest(copied_source_rebuild.read_bytes())
    installed_source_hash = digest(installed_source_rebuild.read_bytes())
    author_hash = digest(author_path_rebuild.read_bytes())
    return {
        "installed_exe_sha256": installed_hash,
        "copied_installed_source_rebuild_sha256": copied_hash,
        "actual_installed_source_path_rebuild_sha256": installed_source_hash,
        "original_author_source_path_rebuild_sha256": author_hash,
        "original_author_source_path_rebuild_exact": author_hash == installed_hash,
        "copied_installed_source_rebuild_exact": copied_hash == installed_hash,
        "actual_installed_source_path_rebuild_exact": installed_source_hash == installed_hash,
        "strict_analysis_empty_for_all_three": all(
            "<DEFECTS></DEFECTS>" in path.read_text(encoding="utf-8-sig")
            for path in (copied_analysis, installed_analysis, author_analysis)
        ),
        "conclusion": "exact Brepro output depends on compiling the exact source bytes from the original author source path",
    }


def main() -> None:
    installed_inventory = exact_inventory(INSTALLED)
    copied_inventory = exact_inventory(COPY)
    assert installed_inventory["mismatches"] == [] and installed_inventory["extras"] == []
    assert installed_inventory["subject_root_sha256"] == installed_inventory["declared_subject_root_sha256"]
    assert copied_inventory == installed_inventory
    result = {
        "schema": "kira.shared_growth_v9.independent_hostile_probe_result.v1",
        "candidate": "shared_person_growth_v3_protected_handoff_v9",
        "review_scope": "read_only_static_no_fixture_integration_no_candidate_execution",
        "installed_exact_inventory": installed_inventory,
        "receipt_signature_checks": verify_receipts(),
        "scanner_checks": scanner_probes(),
        "route_variant_template_checks": route_and_variant_checks(),
        "native_static_checks": native_static_checks(),
        "install_metadata_checks": install_metadata_checks(),
        "rebuild_checks": rebuild_checks(),
        "kira_files_written": 0,
        "person_or_temporary_creator_changed": False,
        "live_routes_invoked": 0,
    }
    RESULT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({
        "verdict": "PROBES_COMPLETE",
        "subject_root_sha256": installed_inventory["subject_root_sha256"],
        "fixture_signatures_verified_read_only": result["receipt_signature_checks"]["fixture_receipts_signature_verified_read_only"],
        "scanner_evasions_missed": result["scanner_checks"]["evasion_count_with_zero_hits"],
        "result_sha256": digest(RESULT.read_bytes()),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
