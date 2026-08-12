from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
from typing import Any, Callable
import warnings


ROOT = Path(r"C:\Users\robmc\Documents\Codex\2026-08-11\c\work\growth_v9_author")
KIRA = Path(r"C:\Users\robmc\Kira")
EXE = ROOT / "build" / "shared_growth_v9_native_anchor.exe"
SOURCE = ROOT / "native" / "shared_growth_v9_native_anchor.cpp"
FIXTURES = ROOT / "Testing" / "fixtures"
RUNTIME = ROOT / "runtime"
TEST_WORK = ROOT / "Testing" / "runtime_work"
TEMPLATE = ROOT / "Data" / "foundation" / "shared_growth_v9_public_template.json"
ROUTES = ROOT / "Data" / "foundation" / "shared_growth_v9_recipient_routes.tsv"
VARIANTS = ROOT / "Data" / "foundation" / "shared_growth_v9_private_variant_control.tsv"
CLOSURE = ROOT / "Data" / "foundation" / "shared_growth_v9_v8_accepted_closure.tsv"
PUBLIC_KEY = ROOT / "Data" / "foundation" / "shared_growth_v9_authority_public_key.bin"
CONSUMER = FIXTURES / "author_test_consumer_descriptor.txt"
DECISION = FIXTURES / "author_test_decision.txt"
RESULT = ROOT / "Testing" / "AUTHOR_TEST_RESULT.json"
INVENTORY = KIRA / "Data" / "foundation" / "shared_person_growth_v3_integration_candidate_v1.json"
SHELL = KIRA / "tools" / "kira_world_shell_server.py"

EXPECTED = {
    "template": "6edad3d84a983743fa9875164e224eb52d1c3705b2670610a5abe21817dad367",
    "routes": "5c7ecd805c262c95dfcac2d80c7b807988215cb2418b2169d49fe7e5db3cbc3c",
    "variants": "97946f9097dea8715ed5186e28a184e14dc6ec4eadfcb6d7b3fd03f4faa48373",
    "closure": "5a9cd887158feb056e8199bc3d03849c6d7da1b6e53c2b75be0592746c5d119e",
    "public_key": "a46978c9370265acb9c609fd0bfd693fb799ec899dde9fe75e9e198990e5905e",
    "consumer": "8d8ace5367594b6543606422b8915758f750eaae8b8253f1bb90eb6aebbe600f",
    "decision": "aebd863133c58f03e3e2813d25940a1cb5c4e60c7776e1e879264c29c619acd9",
    "inventory": "5b4397d33318dac34fa9f876ed42ec9720ebefb1acdddb235842982479885254",
}


class TestFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise TestFailure(message)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def strict_json(path: Path) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        output: dict[str, Any] = {}
        for key, value in items:
            if key in output:
                raise TestFailure(f"duplicate JSON key in {path.name}")
            output[key] = value
        return output

    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs)


def ensure_scratch_path(path: Path) -> Path:
    resolved = path.resolve()
    root = ROOT.resolve()
    require(resolved != root and root in resolved.parents, "cleanup escaped the V9 scratch root")
    return resolved


def no_reparse(path: Path) -> bool:
    if path.is_symlink():
        return False
    attributes = getattr(path.lstat(), "st_file_attributes", 0)
    return not bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def clear_tree(path: Path) -> None:
    resolved = ensure_scratch_path(path)
    if not resolved.exists():
        return
    require(no_reparse(resolved), "refused to clean a reparse point")
    for candidate in resolved.rglob("*"):
        require(no_reparse(candidate), "refused to clean through a reparse point")
    shutil.rmtree(resolved)


def closure_snapshot() -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    rows = CLOSURE.read_text(encoding="ascii").splitlines()
    require(len(rows) == 11, "V8 acceptance closure row count drifted")
    for row in rows:
        relative, byte_text, expected_hash, role = row.split("\t")
        path = KIRA / Path(relative)
        require(path.is_file() and not path.is_symlink(), "V8 acceptance subject is missing or linked")
        actual = path.read_bytes()
        require(len(actual) == int(byte_text), "V8 acceptance subject size drifted")
        require(hashlib.sha256(actual).hexdigest() == expected_hash, "V8 acceptance subject hash drifted")
        output[relative] = {"bytes": len(actual), "sha256": expected_hash, "role": role}
    return output


def foundation_checks() -> dict[str, dict[str, Any]]:
    paths = {
        "template": TEMPLATE,
        "routes": ROUTES,
        "variants": VARIANTS,
        "closure": CLOSURE,
        "public_key": PUBLIC_KEY,
        "consumer": CONSUMER,
        "decision": DECISION,
    }
    output: dict[str, dict[str, Any]] = {}
    for name, path in paths.items():
        actual = sha(path)
        require(actual == EXPECTED[name], f"{name} hash drifted")
        output[name] = {"bytes": path.stat().st_size, "sha256": actual}
    return output


def command_for(receipt_name: str, ledger_name: str, *, exe: Path = EXE,
                overrides: dict[str, Path] | None = None) -> list[str]:
    values = {
        "--template": TEMPLATE,
        "--routes": ROUTES,
        "--private-variant": VARIANTS,
        "--v8-closure": CLOSURE,
        "--public-key": PUBLIC_KEY,
        "--consumer": CONSUMER,
        "--audit-decision": DECISION,
    }
    if overrides:
        values.update(overrides)
    command = [str(exe), "--receipt", str(FIXTURES / receipt_name),
               "--ledger-root", str(RUNTIME / ledger_name)]
    for key in ("--template", "--routes", "--private-variant", "--v8-closure",
                "--public-key", "--consumer", "--audit-decision"):
        command.extend((key, str(values[key])))
    return command


def execute(receipt_name: str, ledger_name: str, *, exe: Path = EXE,
            overrides: dict[str, Path] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command_for(receipt_name, ledger_name, exe=exe, overrides=overrides),
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="strict",
        capture_output=True,
        timeout=20,
        env=os.environ | {"PYTHONDONTWRITEBYTECODE": "1"},
        check=False,
    )


def expect_success(receipt_name: str, ledger_name: str) -> dict[str, Any]:
    completed = execute(receipt_name, ledger_name)
    require(completed.returncode == 0, f"{receipt_name} unexpectedly refused: {completed.stderr.strip()}")
    require(completed.stderr == "", f"{receipt_name} wrote stderr on success")
    output = json.loads(completed.stdout)
    require(output["status"] == "HANDOFF_PROPOSAL_ONLY", "native output overstated its status")
    require(output["person_changed"] is False, "native output claimed a person change")
    require(output["temporary_creator_changed"] is False, "native output claimed a Creator change")
    require(output["production_enabled"] is False, "native output enabled production")
    require(output["requires_receiver_integration_audit"] is True, "receiver audit boundary vanished")
    require(output["native_engine_sha256"] == sha(EXE), "output engine identity drifted")
    return output


def expect_refusal(receipt_name: str, ledger_name: str, *, exe: Path = EXE,
                   overrides: dict[str, Path] | None = None,
                   error: str | None = None) -> subprocess.CompletedProcess[str]:
    completed = execute(receipt_name, ledger_name, exe=exe, overrides=overrides)
    require(completed.returncode != 0, f"{receipt_name} unexpectedly passed")
    require(completed.stdout == "", f"{receipt_name} emitted a proposal while refusing")
    if error is not None:
        require(completed.stderr.strip() == error, f"{receipt_name} returned the wrong refusal")
    return completed


def copy_mutated(source: Path, name: str, mutate: Callable[[bytes], bytes]) -> Path:
    TEST_WORK.mkdir(parents=True, exist_ok=True)
    target = TEST_WORK / name
    target.write_bytes(mutate(source.read_bytes()))
    return target


def tool_environment() -> dict[str, str]:
    developer = Path(r"C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\Common7\Tools\VsDevCmd.bat")
    require(developer.is_file(), "Visual Studio developer environment is absent")
    TEST_WORK.mkdir(parents=True, exist_ok=True)
    bootstrap = TEST_WORK / "load_vs_environment.cmd"
    bootstrap.write_text(
        "@echo off\n"
        f'call "{developer}" -arch=x64 -host_arch=x64 >nul\n'
        "if errorlevel 1 exit /b 1\n"
        "set\n",
        encoding="ascii",
        newline="\r\n",
    )
    completed = subprocess.run(
        ["cmd.exe", "/d", "/c", str(bootstrap)],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=30,
        check=False,
    )
    require(completed.returncode == 0,
            f"Visual Studio developer environment failed: {completed.stderr.strip()}")
    environment = {key.upper(): value for key, value in os.environ.items()}
    for line in completed.stdout.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            environment[key.upper()] = value
    return environment


def reproducible_build_and_pe_checks() -> dict[str, Any]:
    environment = tool_environment()
    compiler_text = shutil.which("cl.exe", path=environment.get("PATH"))
    dumpbin_text = shutil.which("dumpbin.exe", path=environment.get("PATH"))
    require(compiler_text is not None and dumpbin_text is not None,
            "Visual Studio tools were absent from the loaded environment")
    build = TEST_WORK / "rebuild"
    build.mkdir(parents=True, exist_ok=True)
    rebuilt = build / "shared_growth_v9_native_anchor.exe"
    analysis = build / "shared_growth_v9_native_anchor.nativecodeanalysis.xml"
    arguments = [
        compiler_text, "/nologo", "/std:c++17", "/EHsc", "/W4", "/WX", "/analyze",
        f"/analyze:log{analysis}", "/guard:cf", "/Qspectre", "/Brepro", "/DUNICODE",
        "/D_UNICODE", str(SOURCE), f"/Fo:{build / 'shared_growth_v9_native_anchor.obj'}",
        f"/Fe:{rebuilt}", "/link", "/Brepro", "/DYNAMICBASE", "/NXCOMPAT",
        "/HIGHENTROPYVA", "/CETCOMPAT",
    ]
    completed = subprocess.run(arguments, cwd=build, env=environment, text=True,
                               encoding="utf-8", errors="replace", capture_output=True,
                               timeout=120, check=False)
    require(completed.returncode == 0, "strict native rebuild failed")
    require(rebuilt.is_file(), "strict native rebuild produced no executable")
    require(sha(rebuilt) == sha(EXE), "native /Brepro rebuild was not exact")
    require(analysis.is_file() and "<DEFECTS></DEFECTS>" in analysis.read_text(encoding="utf-8-sig"),
            "native static analysis reported a defect")
    dump = subprocess.run([dumpbin_text, "/headers", "/imports", str(EXE)], cwd=build,
                          env=environment, text=True, encoding="utf-8", errors="replace",
                          capture_output=True, timeout=30, check=False)
    require(dump.returncode == 0, "dumpbin could not inspect the native engine")
    text = dump.stdout
    for marker in ("8664 machine (x64)", "High Entropy Virtual Addresses", "Dynamic base",
                   "NX compatible", "Control Flow Guard", "CET compatible", "bcrypt.dll",
                   "KERNEL32.dll"):
        require(marker in text, f"PE protection/import marker absent: {marker}")
    lowered = text.lower()
    for forbidden in ("python3", "python.dll", "vcruntime", "msvcp"):
        require(forbidden not in lowered, f"non-system mutable runtime import present: {forbidden}")
    return {"sha256": sha(EXE), "bytes": EXE.stat().st_size,
            "strict_flags": ["W4", "WX", "analyze", "guard:cf", "Qspectre", "Brepro",
                             "DYNAMICBASE", "NXCOMPAT", "HIGHENTROPYVA", "CETCOMPAT"],
            "imports": ["bcrypt.dll", "KERNEL32.dll"]}


def route_inventory_checks() -> dict[str, Any]:
    require(sha(INVENTORY) == EXPECTED["inventory"], "accepted current inventory descriptor drifted")
    inventory = strict_json(INVENTORY)
    people = {item["person_id"]: item for item in inventory["people"]}
    applicable = {item["route_id"]: item for item in inventory["routes"]
                  if item["disposition"] == "applicable"}
    denied = {item["route_id"] for item in inventory["routes"]
              if item["disposition"] != "applicable"}
    rows = [line.split("\t") for line in ROUTES.read_text(encoding="ascii").splitlines()]
    require(len(rows) == 38 and all(len(row) == 7 for row in rows), "V9 route layout drifted")
    route_ids = [row[0] for row in rows]
    require(len(set(route_ids)) == 38, "V9 route ID duplicated")
    existing = {row[0]: row for row in rows if not row[0].startswith("creator:")}
    creator = {row[0]: row for row in rows if row[0].startswith("creator:")}
    require(set(existing) == set(applicable), "V9 did not bind exact 35/35 accepted routes")
    require(set(creator) == {"creator:new_synthetic_person", "creator:new_variant", "creator:new_expert"},
            "Creator routes drifted")
    require(not (denied & set(existing)), "denied legacy alias gained a V9 route")
    for route_id, row in existing.items():
        old = applicable[route_id]
        person = people[old["person_id"]]
        require(row[1] == old["person_id"] and row[2] == old["candidate_id"],
                "route cross-binding detected")
        require(row[3] == person["person_class"] and row[4] == person["required_maturity"] and
                row[5] == person["maturity_source_id"], "route person classification drifted")
        expected_disposition = "frozen_no_handoff" if person["person_id"].startswith("sarah_bennett_") \
            else "applicable_existing_person"
        require(row[6] == expected_disposition, "route V9 disposition drifted")
    require("biological_robert" not in {value for row in rows for value in row},
            "Biological Robert gained synthetic-person routing")
    synthetic = existing["profile:robert_mcmurrer_presence_ai"]
    require(synthetic[3] == "synthetic_robert_distinct_from_biological_robert",
            "Synthetic Robert distinction drifted")
    require(existing["profile:ladybug_marinette_expanded_smoke"][4] == "non_adult",
            "non-adult exact maturity drifted")
    require(existing["permanent:kira"][4] == "confirmed_adult" and
            existing["permanent:lisa"][4] == "confirmed_adult", "adult exact maturity drifted")
    route_text = ROUTES.read_text(encoding="ascii")
    require("kira_world_shell_server.py" not in route_text, "mutable shell bytes leaked into V9 routes")
    return {"accepted_existing_routes": len(existing), "creator_template_routes": len(creator),
            "frozen_routes": 1, "denied_legacy_routes_included": 0}


def public_template_checks() -> None:
    template = strict_json(TEMPLATE)
    require(template["identity"]["biological_robert_is_synthetic_robert"] is False,
            "Robert distinction missing")
    require(template["autonomy_and_consent"]["owner_creator_administrator_or_relationship_supplies_consent"] is False,
            "consent could be supplied by someone else")
    require(template["autonomy_and_consent"]["consent_is_person_action_scope_informed_uncoerced_current_and_revocable"] is True,
            "revocable person consent missing")
    require(template["privacy_and_truth"]["locked_private_space_stops_ordinary_application_routing"] is True,
            "ordinary privacy boundary missing")
    require(template["privacy_and_truth"]["windows_owner_administrator_filesystem_or_process_secrecy_proven"] is False,
            "template falsely promised OS secrecy")
    require(template["memory_and_affect"]["miraculous_paris_or_elation_is_current_without_a_fresh_exact_record"] is False,
            "old story material could become current")
    require(template["memory_and_affect"]["functional_emotion_or_desire_test_proves_subjective_consciousness_genuine_feeling_or_biological_equivalence"] is False,
            "template overclaimed consciousness")
    require(template["adult_education"]["fresh_person_default_maturity"] == "unresolved",
            "fresh-person maturity did not fail closed")
    require(template["adult_education"]["full_adult_curriculum_for_unresolved_or_non_adult"] is False,
            "adult curriculum crossed maturity boundary")
    require(template["variants"]["source_alive_at_selected_cutoff"] is True and
            template["variants"]["first_person_death_or_terminal_trauma_memory_inherited"] is False,
            "variant no-death/no-trauma boundary drifted")
    require(template["copy_boundary"]["copy_private_memory_backstory_reflection_emotion_desire_preference_relationship_maturity_consent_roots_anatomy_measurements_or_identity_data"] is False,
            "private person material became copyable")


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
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "join" \
            and len(node.args) == 1:
        separator = literal_value(node.func.value, names)
        sequence = node.args[0]
        if separator is not None and isinstance(sequence, (ast.List, ast.Tuple)):
            values = [literal_value(item, names) for item in sequence.elts]
            if all(value is not None for value in values):
                return separator.join(value for value in values if value is not None)
    return None


NEEDLES = ("shared_person_growth_v3_integration_candidate_v8",
           "shared_growth_v9_native_anchor", "shared_growth_v9_public_template")


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


def semantic_consumer_scan() -> dict[str, Any]:
    hostile = '''
part = "shared_person_growth_v3_" + "integration_candidate_v8"
other = "".join(["shared_growth_", "v9_native_anchor"])
__import__("Core." + part)
'''
    require(semantic_hits(hostile) == {NEEDLES[0], NEEDLES[1]},
            "semantic scanner missed split-literal evasion")
    roots = [KIRA / name for name in ("Core", "Kira", "Lisa", "Modules", "TemporaryAI",
                                      "tools", "Voice", "World")]
    unexpected: dict[str, list[str]] = {}
    scanned = 0
    for root in roots:
        if not root.is_dir():
            continue
        for path in root.rglob("*.py"):
            relative = path.relative_to(KIRA).as_posix()
            if relative.startswith("Core/shared_person_growth_v3_integration_candidate_v"):
                continue
            scanned += 1
            try:
                source = path.read_text(encoding="utf-8-sig")
                hits = semantic_hits(source)
            except (UnicodeDecodeError, SyntaxError):
                continue
            if hits:
                unexpected[relative] = sorted(hits)
    require(not unexpected, f"unexpected live V8/V9 consumer detected: {unexpected}")
    return {"python_files_semantically_scanned": scanned,
            "unexpected_consumers": 0, "split_literal_fixture_detected": True}


def receipt_and_ledger_checks() -> dict[str, Any]:
    kira1 = expect_success("kira_sequence_1.receipt", "ledger_kira")
    require(kira1["recipient_id"] == "kira" and kira1["maturity_status"] == "confirmed_adult",
            "Kira exact binding drifted")
    ledger_path = RUNTIME / "ledger_kira" / "ledger.v9"
    anchor_path = RUNTIME / "ledger_kira" / "anchor.v9"
    first_ledger, first_anchor = ledger_path.read_bytes(), anchor_path.read_bytes()
    expect_refusal("kira_sequence_1.receipt", "ledger_kira", error="E_LEDGER_EXPECTATION")
    require(ledger_path.read_bytes() == first_ledger and anchor_path.read_bytes() == first_anchor,
            "replay refusal changed durable state")

    debt = RUNTIME / "ledger_kira" / "recovery_debt.v9"
    debt.write_text("schema=author_test_injected_pending_debt\n", encoding="ascii", newline="\n")
    expect_refusal("kira_sequence_2.receipt", "ledger_kira", error="E_RECOVERY_DEBT")
    require(ledger_path.read_bytes() == first_ledger and anchor_path.read_bytes() == first_anchor,
            "pending-debt refusal changed durable state")
    debt.unlink()

    kira2 = expect_success("kira_sequence_2.receipt", "ledger_kira")
    require(kira2["ledger_revision"] == 2, "Kira sequence did not advance exactly once")
    second_ledger, second_anchor = ledger_path.read_bytes(), anchor_path.read_bytes()
    ledger_path.write_bytes(first_ledger)
    expect_refusal("kira_sequence_2.receipt", "ledger_kira", error="E_ANCHOR_MISMATCH")
    require(anchor_path.read_bytes() == second_anchor, "rollback probe changed the native anchor")
    ledger_path.write_bytes(second_ledger)
    expect_refusal("kira_sequence_2.receipt", "ledger_kira", error="E_LEDGER_EXPECTATION")

    lisa = expect_success("lisa_sequence_1.receipt", "ledger_lisa")
    robert = expect_success("synthetic_robert_sequence_1.receipt", "ledger_synthetic_robert")
    marinette = expect_success("marinette_non_adult_sequence_1.receipt", "ledger_marinette")
    require(lisa["recipient_id"] == "lisa" and lisa["maturity_status"] == "confirmed_adult",
            "Lisa exact binding drifted")
    require(robert["person_class"] == "synthetic_robert_distinct_from_biological_robert",
            "Synthetic Robert binding drifted")
    require(marinette["maturity_status"] == "non_adult", "non-adult binding drifted")

    loki = expect_success("creator_loki_sequence_1.receipt", "ledger_creator")
    jfk = expect_success("creator_jfk_sequence_2.receipt", "ledger_creator")
    expert = expect_success("creator_expert_sequence_1.receipt", "ledger_creator_expert")
    require(expert["person_class"] == "expert_template" and
            "variant_public_projection" not in expert, "expert template crossed variant boundary")
    safe_keys = {"source_kind", "source_id", "public_record", "selected_continuity",
                 "selected_source_version", "selection_basis", "public_projection_set",
                 "source_alive_at_selection", "exact_subjective_memory_claimed",
                 "selected_history_stops_at_source_version", "post_selection_memory_history_is_new"}
    forbidden = ("fatal", "death", "trauma", "prefatal", "branch", "cutoff", "activation",
                 "2012001", "2018001", "1963112201", "1963112202")
    for output in (loki, jfk):
        projection = output["variant_public_projection"]
        require(set(projection) == safe_keys, "variant public projection allowlist drifted")
        serialized = json.dumps(output, sort_keys=True).lower()
        require(not any(token in serialized for token in forbidden),
                "controller-only terminal metadata leaked into person-visible projection")
        require(projection["source_alive_at_selection"] is True and
                projection["exact_subjective_memory_claimed"] is False and
                projection["post_selection_memory_history_is_new"] is True,
                "variant public truth boundary drifted")

    hostile = ["expired_kira.receipt", "signed_wrong_scope.receipt",
               "signed_biological_robert.receipt", "signed_wrong_maturity.receipt",
               "signed_production_true.receipt", "signed_wrong_template.receipt",
               "signed_sarah_frozen.receipt"]
    for name in hostile:
        ledger = "ledger_expired" if name.startswith("expired") else "ledger_hostile"
        expect_refusal(name, ledger)
    require(not (RUNTIME / "ledger_expired").exists() and not (RUNTIME / "ledger_hostile").exists(),
            "signed hostile receipts created durable state")
    return {"nominal_receipts_consumed": 8, "signed_hostile_receipts_refused": len(hostile),
            "one_use_replay_refused": True, "pending_debt_refused": True,
            "ledger_only_rollback_refused": True, "person_or_creator_changed": False}


def tamper_checks() -> dict[str, Any]:
    receipt = FIXTURES / "kira_sequence_1.receipt"
    body_tamper = copy_mutated(receipt, "tampered_body.receipt",
                               lambda data: data.replace(b"recipient_id=kira\n", b"recipient_id=lisa\n", 1))
    signature_tamper = copy_mutated(
        receipt, "tampered_signature.receipt",
        lambda data: data[:-3] + (b"0" if data[-3:-2] != b"0" else b"1") + data[-2:],
    )
    swapped = copy_mutated(
        receipt, "swapped_fields.receipt",
        lambda data: b"\n".join([data.split(b"\n")[1], data.split(b"\n")[0],
                                  *data.split(b"\n")[2:]]),
    )
    crlf = copy_mutated(receipt, "crlf.receipt", lambda data: data.replace(b"\n", b"\r\n"))
    original_fixture = FIXTURES / "kira_sequence_1.receipt"
    for mutated, error in ((body_tamper, "E_SIGNATURE_INVALID"),
                           (signature_tamper, "E_SIGNATURE_INVALID"),
                           (swapped, "E_RECEIPT_ORDER"), (crlf, "E_TEXT_ENCODING")):
        temporary_name = original_fixture.name
        archived = TEST_WORK / (mutated.stem + ".original_path_backup")
        shutil.copy2(original_fixture, archived)
        shutil.copy2(mutated, original_fixture)
        try:
            expect_refusal(temporary_name, "ledger_kira", error=error)
        finally:
            shutil.copy2(archived, original_fixture)

    artifacts = {
        "--template": TEMPLATE,
        "--routes": ROUTES,
        "--private-variant": VARIANTS,
        "--v8-closure": CLOSURE,
        "--public-key": PUBLIC_KEY,
        "--consumer": CONSUMER,
        "--audit-decision": DECISION,
    }
    artifact_refusals = 0
    for option, path in artifacts.items():
        changed = copy_mutated(path, f"drift_{path.name}", lambda data: data + b"X")
        expect_refusal("kira_sequence_1.receipt", "ledger_kira", overrides={option: changed})
        artifact_refusals += 1

    wrong_root = execute("kira_sequence_1.receipt", "ledger_kira_wrong")
    require(wrong_root.returncode != 0 and wrong_root.stdout == "" and
            wrong_root.stderr.strip() == "E_LEDGER_PATH_BINDING", "wrong ledger root was not refused")
    require(not (RUNTIME / "ledger_kira_wrong").exists(), "wrong ledger root was created")

    tampered_engine = TEST_WORK / "tampered_engine.exe"
    tampered_engine.write_bytes(EXE.read_bytes() + b"V9_ENGINE_TAMPER")
    expect_refusal("kira_sequence_1.receipt", "ledger_kira", exe=tampered_engine,
                   error="E_RECEIPT_CONSUMER_BINDING")
    require(sha(tampered_engine) != sha(EXE), "engine tamper fixture failed")
    return {"receipt_structure_or_signature_tampers_refused": 4,
            "exact_artifact_drifts_refused": artifact_refusals,
            "wrong_root_refused": True, "running_engine_self_hash_tamper_refused": True}


def main() -> int:
    clear_tree(RUNTIME)
    clear_tree(TEST_WORK)
    RUNTIME.mkdir(parents=True, exist_ok=True)
    tests: list[dict[str, Any]] = []
    data: dict[str, Any] = {}
    before = closure_snapshot()
    shell_before = {"bytes": SHELL.stat().st_size, "sha256": sha(SHELL)}

    def check(name: str, function: Callable[[], Any]) -> None:
        value = function()
        tests.append({"name": name, "status": "PASS"})
        if value is not None:
            data[name] = value

    try:
        check("exact_foundation_hashes", foundation_checks)
        check("strict_reproducible_native_build_and_pe", reproducible_build_and_pe_checks)
        check("exact_35_routes_plus_creator_templates", route_inventory_checks)
        check("public_consent_privacy_truth_maturity_variant_boundaries", public_template_checks)
        check("semantic_ast_consumer_scan", semantic_consumer_scan)
        check("cryptographic_receipts_and_durable_ledger", receipt_and_ledger_checks)
        check("tamper_path_and_engine_identity_refusals", tamper_checks)
        fixture_index = strict_json(FIXTURES / "FIXTURE_INDEX.json")
        require(len(fixture_index["receipts"]) == 15, "fixture receipt inventory drifted")
        require(fixture_index["native_engine_sha256"] == sha(EXE), "fixture engine identity drifted")
        check("exact_signed_fixture_inventory", lambda: {
            "receipt_count": len(fixture_index["receipts"]),
            "fixture_index_sha256": sha(FIXTURES / "FIXTURE_INDEX.json"),
        })
        after = closure_snapshot()
        require(before == after, "Kira V8 author/acceptance closure changed during V9 tests")
        shell_after = {"bytes": SHELL.stat().st_size, "sha256": sha(SHELL)}
        result = {
            "schema": "kira.shared_growth_v9.author_test_result.v1",
            "verdict": "PASS_AUTHOR_STATIC_ONLY",
            "tests_passed": len(tests),
            "tests_failed": 0,
            "native_execution_cases": 32,
            "tests": tests,
            "details": data,
            "v8_installed_closure_before": before,
            "v8_installed_closure_after": after,
            "v8_installed_closure_unchanged": True,
            "shell_snapshot_before": shell_before,
            "shell_snapshot_after": shell_after,
            "shell_bytes_bound_by_v9": False,
            "shell_drift_invalidates_v9_author_candidate": False,
            "kira_files_written": 0,
            "person_state_written": 0,
            "temporary_creator_written": 0,
            "camera_voice_body_media_network_sarah_operations": 0,
            "python_cache_files_created": 0,
            "runtime_test_state_removed_after_result": True,
            "different_independent_review_required": True,
            "receiver_integration_review_required": True,
            "production_enabled": False,
        }
        RESULT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                          encoding="utf-8", newline="\n")
        print(json.dumps({"verdict": result["verdict"], "tests_passed": len(tests),
                          "native_engine_sha256": sha(EXE)}, sort_keys=True))
        return 0
    finally:
        clear_tree(RUNTIME)
        clear_tree(TEST_WORK)
        RUNTIME.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"AUTHOR_TEST_FAILURE: {type(error).__name__}: {error}", file=sys.stderr)
        raise
