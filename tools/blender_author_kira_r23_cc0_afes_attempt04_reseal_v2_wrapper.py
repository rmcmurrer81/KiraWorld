#!/usr/bin/env python3
"""Blender-side execution seal for R23 Attempt04 reseal v2.

Only stdlib and Blender's external ``bpy`` module are imported before every
project-local module is hash verified. Live authorization is independently
opened and validated here; environment hashes are consistency checks only.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import types
from typing import Any, Mapping, Sequence

import bpy


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = Path(
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_author_attempt04_reseal_v2_preparation/"
    "KIRA_R23_CC0_AFES_AUTHOR_ATTEMPT04_RESEAL_V2_CONFIG.json"
)
MANIFEST_PATH = Path(
    "RecoverySprint/continuation_20260803/"
    "kira_r23_cc0_afes_author_attempt04_reseal_v2_preparation/"
    "PACKAGE_MANIFEST.json"
)


class BlenderResealV2Error(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def is_reparse(path: Path) -> bool:
    details = path.lstat()
    flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return path.is_symlink() or bool(
        getattr(details, "st_file_attributes", 0) & flag
    )


def lexical_project_path(
    raw: str | Path,
    *,
    require_exists: bool,
    require_leaf_regular: bool = False,
) -> Path:
    value = Path(str(raw))
    if (
        not str(raw)
        or value.is_absolute()
        or value.drive
        or value.root
        or any(part in {"", ".", ".."} for part in value.parts)
    ):
        raise BlenderResealV2Error(f"unsafe lexical project path: {raw}")
    if not os.path.lexists(ROOT) or is_reparse(ROOT) or not ROOT.is_dir():
        raise BlenderResealV2Error("project root is invalid or reparse")
    current = ROOT
    missing = False
    for part in value.parts:
        current = current / part
        if os.path.lexists(current):
            if missing:
                raise BlenderResealV2Error("path reappeared below missing ancestor")
            if is_reparse(current):
                raise BlenderResealV2Error(f"project path contains reparse component: {current}")
        else:
            missing = True
    if require_exists and missing:
        raise BlenderResealV2Error(f"required project path is absent: {raw}")
    if require_leaf_regular and (
        missing or not current.is_file() or is_reparse(current)
    ):
        raise BlenderResealV2Error(f"required project path is not a regular file: {raw}")
    resolved = current.resolve(strict=False)
    try:
        resolved.relative_to(ROOT.resolve(strict=True))
    except ValueError as exc:
        raise BlenderResealV2Error(f"project path escaped root: {raw}") from exc
    return current


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise BlenderResealV2Error(f"JSON root is not an object: {path}")
    return value


def verify_binding_bootstrap(binding: Mapping[str, Any], label: str) -> dict[str, Any]:
    path = lexical_project_path(
        binding["path"], require_exists=True, require_leaf_regular=True
    )
    size = path.stat().st_size
    digest = sha256_file(path)
    if size != int(binding["bytes"]) or digest != str(binding["sha256"]):
        raise BlenderResealV2Error(
            f"bootstrap binding drifted for {label}: bytes={size}, sha256={digest}"
        )
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": size, "sha256": digest}


def bootstrap_verify_all_project_modules() -> tuple[dict[str, Any], dict[str, Any]]:
    """Verify the full project closure before importing any project module."""

    config_path = lexical_project_path(
        CONFIG_PATH, require_exists=True, require_leaf_regular=True
    )
    manifest_path = lexical_project_path(
        MANIFEST_PATH, require_exists=True, require_leaf_regular=True
    )
    config = read_json(config_path)
    manifest = read_json(manifest_path)
    if config.get("schema") != "kira.avatar.r23_author_attempt04_reseal_v2.v1":
        raise BlenderResealV2Error("wrong reseal v2 config schema")
    if manifest.get("artifact_kind") != "KIRA_R23_AUTHOR_ATTEMPT04_RESEAL_V2_PREPARATION":
        raise BlenderResealV2Error("wrong reseal v2 package kind")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        raise BlenderResealV2Error("reseal v2 manifest artifacts absent")
    expected_paths = set(config["manifest_contract"]["required_artifact_paths"])
    actual_paths = {str(entry.get("path")) for entry in artifacts}
    if actual_paths != expected_paths or len(actual_paths) != len(artifacts):
        raise BlenderResealV2Error("reseal v2 manifest closure drifted")
    verified: dict[str, Any] = {}
    for entry in artifacts:
        verified[f"manifest/{entry['path']}"] = verify_binding_bootstrap(
            entry, f"manifest/{entry['path']}"
        )
    for label, binding in config["bound_artifacts"].items():
        verified[f"bound/{label}"] = verify_binding_bootstrap(binding, label)
    required_modules = set(
        config["runtime_dependency_closure"]["project_local_modules"]
    )
    bound_paths = {binding["path"] for binding in config["bound_artifacts"].values()}
    if not required_modules.issubset(bound_paths):
        raise BlenderResealV2Error(
            f"unverified module would be imported: {sorted(required_modules - bound_paths)}"
        )
    return config, {
        "config_sha256": sha256_file(config_path),
        "manifest_sha256": sha256_file(manifest_path),
        "verified_snapshot_sha256": canonical_sha256(verified),
        "verified_count": len(verified),
    }


def parse_exact_worker_argv(argv: Sequence[str] | None = None, *, expected: str) -> list[str]:
    values = list(sys.argv if argv is None else argv)
    if "--" not in values:
        raise BlenderResealV2Error("Blender worker delimiter is absent")
    tail = values[values.index("--") + 1 :]
    required = ["--config", expected, "--execute-authoring"]
    if tail != required:
        raise BlenderResealV2Error(
            f"worker arguments differ from exact sealed invocation: {tail}"
        )
    return tail


def bootstrap_expected_command(config: Mapping[str, Any]) -> list[str]:
    source = lexical_project_path(
        config["bound_artifacts"]["r19_source_blend"]["path"],
        require_exists=True,
        require_leaf_regular=True,
    )
    wrapper = lexical_project_path(
        config["bound_artifacts"]["reseal_v2_blender_wrapper"]["path"],
        require_exists=True,
        require_leaf_regular=True,
    )
    delegated = Path(config["command_contract"]["delegated_config_argument"]).as_posix()
    return [
        str(Path(config["blender_identity"]["path"])),
        "--background",
        "--factory-startup",
        "--disable-autoexec",
        str(source),
        "--python-exit-code",
        str(int(config["command_contract"]["python_exit_code"])),
        "--python",
        str(wrapper),
        "--",
        "--config",
        delegated,
        "--execute-authoring",
    ]


def bootstrap_verify_live_authorization(
    config: Mapping[str, Any], command: Sequence[str]
) -> dict[str, Any]:
    """Independently verify live authorization before any project import."""

    contract = config["authorization_contract"]
    directory = lexical_project_path(contract["directory"], require_exists=True)
    if not directory.is_dir() or is_reparse(directory):
        raise BlenderResealV2Error("live authorization directory invalid")
    entries = sorted(entry.name for entry in directory.iterdir())
    if entries != sorted(contract["directory_entries"]):
        raise BlenderResealV2Error(
            f"live authorization directory closure drifted: {entries}"
        )
    record_path = lexical_project_path(
        contract["record_path"], require_exists=True, require_leaf_regular=True
    )
    manifest_path = lexical_project_path(
        contract["manifest_path"], require_exists=True, require_leaf_regular=True
    )
    manifest = read_json(manifest_path)
    if set(manifest) != {
        "schema_version",
        "artifact_kind",
        "created_utc",
        "authorization_id",
        "artifacts",
    }:
        raise BlenderResealV2Error("authorization manifest has unexpected fields")
    if (
        manifest.get("schema_version") != 1
        or manifest.get("artifact_kind")
        != "KIRA_R23_AUTHOR_ATTEMPT04_RESEAL_V2_AUTHORIZATION_PACKAGE"
    ):
        raise BlenderResealV2Error("wrong authorization manifest schema/kind")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or len(artifacts) != 1:
        raise BlenderResealV2Error("authorization manifest must bind exactly one record")
    binding = artifacts[0]
    if binding.get("path") != contract["record_path"]:
        raise BlenderResealV2Error("authorization manifest record path drifted")
    verified_record = verify_binding_bootstrap(binding, "live authorization record")
    record = read_json(record_path)
    expected_keys = {
        "schema",
        "artifact_kind",
        "authorization_id",
        "created_utc",
        "owner_decision_text",
        "execution_enabled",
        "owner_authorized",
        "one_run_only",
        "nonce",
        "reviewed",
        "command_sha256",
        "outputs",
        "restrictions",
    }
    if set(record) != expected_keys:
        raise BlenderResealV2Error("authorization record has unexpected fields")
    if (
        record.get("schema") != "kira.avatar.r23_attempt04_reseal_v2_authorization.v1"
        or record.get("artifact_kind")
        != "KIRA_R23_AUTHOR_ATTEMPT04_RESEAL_V2_AUTHORIZATION"
        or record.get("execution_enabled") is not True
        or record.get("owner_authorized") is not True
        or record.get("one_run_only") is not True
    ):
        raise BlenderResealV2Error("authorization is not explicitly enabled for one run")
    if record.get("authorization_id") != manifest.get("authorization_id"):
        raise BlenderResealV2Error("authorization ID differs from manifest")
    if not isinstance(record.get("owner_decision_text"), str) or not record["owner_decision_text"].strip():
        raise BlenderResealV2Error("authorization owner decision text is empty")
    nonce = str(record.get("nonce", ""))
    if not re.fullmatch(r"[A-Za-z0-9_-]{32,128}", nonce):
        raise BlenderResealV2Error("authorization nonce is invalid")
    config_path = lexical_project_path(
        CONFIG_PATH, require_exists=True, require_leaf_regular=True
    )
    preparation_manifest_path = lexical_project_path(
        MANIFEST_PATH, require_exists=True, require_leaf_regular=True
    )
    expected_reviewed = {
        "preparation_manifest": {
            "path": preparation_manifest_path.relative_to(ROOT).as_posix(),
            "bytes": preparation_manifest_path.stat().st_size,
            "sha256": sha256_file(preparation_manifest_path),
        },
        "reseal_v2_config": {
            "path": config_path.relative_to(ROOT).as_posix(),
            "bytes": config_path.stat().st_size,
            "sha256": sha256_file(config_path),
        },
        "reseal_v2_controller": verify_binding_bootstrap(
            config["bound_artifacts"]["reseal_v2_controller"],
            "authorization/controller",
        ),
        "reseal_v2_wrapper": verify_binding_bootstrap(
            config["bound_artifacts"]["reseal_v2_blender_wrapper"],
            "authorization/wrapper",
        ),
        "delegated_repair_config": verify_binding_bootstrap(
            config["bound_artifacts"]["delegated_reseal_config"],
            "authorization/delegated config",
        ),
        "r19_source_blend": verify_binding_bootstrap(
            config["bound_artifacts"]["r19_source_blend"],
            "authorization/source",
        ),
        "blender_identity": verify_blender_runtime(config),
    }
    if record.get("reviewed") != expected_reviewed:
        raise BlenderResealV2Error("authorization reviewed-content bindings drifted")
    output = config["output_contract"]
    expected_outputs = {
        "effective_directory": output["effective_directory"],
        "execution_directory": output["execution_directory"],
        "candidate_basename": output["candidate_basename"],
        "build_evidence_basename": output["build_evidence_basename"],
        "failure_evidence_basename": output["failure_evidence_basename"],
    }
    if record.get("outputs") != expected_outputs:
        raise BlenderResealV2Error("authorization output bindings drifted")
    if record.get("restrictions") != contract["required_restrictions"]:
        raise BlenderResealV2Error("authorization restrictions drifted")
    command_hash = canonical_sha256(list(command))
    if record.get("command_sha256") != command_hash:
        raise BlenderResealV2Error("authorization command binding drifted")
    return {
        "directory": directory.relative_to(ROOT).as_posix(),
        "record": verified_record,
        "record_content_sha256": canonical_sha256(record),
        "manifest": {
            "path": manifest_path.relative_to(ROOT).as_posix(),
            "bytes": manifest_path.stat().st_size,
            "sha256": sha256_file(manifest_path),
        },
        "authorization_id": record["authorization_id"],
        "nonce": nonce,
        "reviewed": expected_reviewed,
        "command_sha256": command_hash,
        "outputs": expected_outputs,
        "restrictions": record["restrictions"],
    }


def _load_verified_controller(config: Mapping[str, Any]) -> Any:
    binding = config["bound_artifacts"]["reseal_v2_controller"]
    path = lexical_project_path(
        binding["path"], require_exists=True, require_leaf_regular=True
    )
    # Compile the bytes that were just verified. This bypasses project pyc files
    # and prevents an unverified sys.modules object from being reused.
    name = "_kira_r23_reseal_v2_controller"
    if name in sys.modules:
        raise BlenderResealV2Error("verified controller private name was preloaded")
    source = path.read_bytes()
    if hashlib.sha256(source).hexdigest() != binding["sha256"]:
        raise BlenderResealV2Error("controller bytes changed after bootstrap verification")
    module = types.ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = ""
    sys.modules[name] = module
    try:
        exec(compile(source, str(path), "exec", dont_inherit=True), module.__dict__)
    except Exception:
        sys.modules.pop(name, None)
        raise
    return module


def project_module_name(path: str) -> str:
    value = Path(path)
    if value.parent.as_posix().lower() != "tools" or value.suffix != ".py":
        raise BlenderResealV2Error(f"runtime module path is not a Tools Python file: {path}")
    return f"tools.{value.stem}"


def assert_project_modules_not_preloaded(config: Mapping[str, Any]) -> None:
    loaded = sorted(
        name
        for name in (
            project_module_name(path)
            for path in config["runtime_dependency_closure"]["project_local_modules"]
        )
        if name in sys.modules
    )
    if loaded:
        raise BlenderResealV2Error(
            f"project runtime modules were loaded before verified import: {loaded}"
        )

    if "tools" in sys.modules:
        raise BlenderResealV2Error(
            "project tools package was loaded before verified source import"
        )


def load_verified_project_sources(config: Mapping[str, Any]) -> Any:
    order = config["runtime_dependency_closure"]["verified_source_import_order"]
    expected_old_paths = set(config["runtime_dependency_closure"]["project_local_modules"]) - {
        "Tools/blender_author_kira_r23_cc0_afes_attempt04_reseal_v2_wrapper.py",
        "Tools/kira_r23_author_attempt04_reseal_v2_invocation.py",
    }
    if set(order) != expected_old_paths or len(order) != len(expected_old_paths):
        raise BlenderResealV2Error("verified source import order is incomplete or duplicated")
    package = types.ModuleType("tools")
    package.__package__ = "tools"
    package.__path__ = [str(ROOT / "Tools")]
    package.__file__ = None
    sys.modules["tools"] = package
    loaded: dict[str, Any] = {}
    try:
        for raw in order:
            name = project_module_name(raw)
            path = lexical_project_path(
                raw, require_exists=True, require_leaf_regular=True
            )
            binding = next(
                value
                for value in config["bound_artifacts"].values()
                if value["path"] == raw
            )
            source = path.read_bytes()
            if (
                len(source) != int(binding["bytes"])
                or hashlib.sha256(source).hexdigest() != binding["sha256"]
            ):
                raise BlenderResealV2Error(
                    f"project module changed before source compile: {raw}"
                )
            module = types.ModuleType(name)
            module.__file__ = str(path)
            module.__package__ = "tools"
            sys.modules[name] = module
            setattr(package, Path(raw).stem, module)
            loaded[name] = module
            exec(
                compile(source, str(path), "exec", dont_inherit=True),
                module.__dict__,
            )
    except Exception:
        for name in loaded:
            sys.modules.pop(name, None)
        sys.modules.pop("tools", None)
        raise
    topology_name = project_module_name(
        "Tools/blender_author_kira_r23_cc0_afes_attempt04_wrapper.py"
    )
    topology = sys.modules.get(topology_name)
    if topology is None:
        raise BlenderResealV2Error("topology implementation missing after source import")
    # All allowed project modules are now resident from verified source bytes.
    # An empty package path prevents a later undeclared tools.* disk import.
    package.__path__ = []
    return topology


def verify_imported_dependency_files(config: Mapping[str, Any]) -> dict[str, str]:
    excluded = {
        "Tools/blender_author_kira_r23_cc0_afes_attempt04_reseal_v2_wrapper.py",
        "Tools/kira_r23_author_attempt04_reseal_v2_invocation.py",
    }
    verified: dict[str, str] = {}
    for raw in config["runtime_dependency_closure"]["project_local_modules"]:
        if raw in excluded:
            continue
        name = project_module_name(raw)
        module = sys.modules.get(name)
        if module is None or not getattr(module, "__file__", None):
            raise BlenderResealV2Error(f"verified dependency was not imported: {name}")
        actual = Path(module.__file__).resolve()
        expected = lexical_project_path(
            raw, require_exists=True, require_leaf_regular=True
        ).resolve()
        if actual != expected:
            raise BlenderResealV2Error(
                f"imported dependency path drifted for {name}: {actual}"
            )
        verified[name] = str(actual)
    return verified


def verify_blender_runtime(config: Mapping[str, Any]) -> dict[str, Any]:
    expected = config["blender_identity"]
    executable = Path(sys.executable)
    if executable.resolve() != Path(expected["path"]).resolve():
        raise BlenderResealV2Error(f"wrong Blender executable: {executable}")
    if executable.stat().st_size != int(expected["bytes"]) or sha256_file(executable) != expected["sha256"]:
        raise BlenderResealV2Error("Blender executable identity drifted in worker")
    version = ".".join(str(part) for part in bpy.app.version[:2])
    if version != str(expected["bpy_version_prefix"]):
        raise BlenderResealV2Error(f"Blender bpy version drifted: {version}")
    return {
        "path": str(executable.resolve()),
        "bytes": executable.stat().st_size,
        "sha256": sha256_file(executable),
        "file_version": expected["file_version"],
        "product_version": expected["product_version"],
    }


def verify_pre_run_journal(
    controller: Any,
    config: Mapping[str, Any],
    preparation: Mapping[str, Any],
    authorization: Mapping[str, Any],
    provenance: Mapping[str, Any],
    command: Sequence[str],
) -> dict[str, Any]:
    expected_path = (
        f"{config['output_contract']['execution_directory']}/"
        f"{config['journal_contract']['pre_run_basename']}"
    )
    env_path = os.environ.get("KIRA_R23_RESEAL_V2_PRE_RUN_PATH", "")
    if env_path != expected_path:
        raise BlenderResealV2Error("PRE_RUN environment path differs from sealed path")
    path = lexical_project_path(
        expected_path, require_exists=True, require_leaf_regular=True
    )
    record = read_json(path)
    if (
        record.get("schema_version") != 1
        or record.get("artifact_kind")
        != "KIRA_R23_AUTHOR_ATTEMPT04_RESEAL_V2_PRE_RUN"
        or record.get("preparation") != preparation
        or record.get("authorization") != authorization
        or record.get("provenance") != provenance
        or record.get("command") != list(command)
        or record.get("command_sha256") != controller.canonical_sha256(list(command))
        or record.get("forbidden_environment_keys_present") != []
    ):
        raise BlenderResealV2Error("PRE_RUN journal content does not match sealed execution")
    expected_env = {
        "KIRA_R23_RESEAL_V2_PREPARATION_MANIFEST_SHA256": preparation["manifest"]["sha256"],
        "KIRA_R23_RESEAL_V2_CONFIG_SHA256": preparation["config"]["sha256"],
        "KIRA_R23_RESEAL_V2_AUTHORIZATION_RECORD_SHA256": authorization["record"]["sha256"],
        "KIRA_R23_RESEAL_V2_AUTHORIZATION_MANIFEST_SHA256": authorization["manifest"]["sha256"],
        "KIRA_R23_RESEAL_V2_AUTHORIZATION_NONCE": authorization["nonce"],
    }
    for name, expected in expected_env.items():
        if os.environ.get(name) != expected:
            raise BlenderResealV2Error(f"child environment consistency value drifted: {name}")
    for name in config["process_contract"]["forbidden_environment_keys"]:
        if name in os.environ:
            raise BlenderResealV2Error(f"forbidden environment key reached Blender: {name}")
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def validate_delegated_contract(
    controller: Any, config: Mapping[str, Any]
) -> None:
    delegated_path = lexical_project_path(
        config["command_contract"]["delegated_config_argument"],
        require_exists=True,
        require_leaf_regular=True,
    )
    delegated = read_json(delegated_path)
    output = config["output_contract"]
    repair = delegated.get("repair_contract", {})
    success = delegated.get("success_contract", {})
    expected_repair = {
        "configured_output_required": output["delegated_configured_directory"],
        "effective_output": output["effective_directory"],
        "effective_candidate": output["candidate_basename"],
    }
    for key, expected in expected_repair.items():
        if repair.get(key) != expected:
            raise BlenderResealV2Error(f"delegated repair output drifted: {key}")
    if (
        success.get("candidate") != output["candidate_basename"]
        or success.get("build_evidence") != output["build_evidence_basename"]
        or success.get("failure_evidence") != output["failure_evidence_basename"]
    ):
        raise BlenderResealV2Error("delegated success/failure basenames drifted")
    author_config = read_json(
        lexical_project_path(
            config["bound_artifacts"]["sealed_author_config"]["path"],
            require_exists=True,
            require_leaf_regular=True,
        )
    )
    author_output = author_config.get("output", {})
    if (
        author_output.get("candidate_blend")
        != output["delegated_author_candidate_basename"]
        or author_output.get("build_evidence") != output["build_evidence_basename"]
        or author_output.get("failure_evidence") != output["failure_evidence_basename"]
    ):
        raise BlenderResealV2Error("sealed author evidence basenames drifted")
    # Validate names and exact containment using verified controller logic before import.
    controller.validate_basename(output["candidate_basename"], "candidate")
    controller.validate_basename(output["build_evidence_basename"], "build")
    controller.validate_basename(output["failure_evidence_basename"], "failure")
    directory = controller.lexical_project_path(
        output["effective_directory"], require_exists=False
    )
    for label, name in (
        ("candidate", output["candidate_basename"]),
        ("build", output["build_evidence_basename"]),
        ("failure", output["failure_evidence_basename"]),
    ):
        controller.path_within_exact_directory(directory, name, label)


def inject_provenance_record(path: Path, provenance: Mapping[str, Any]) -> dict[str, Any]:
    if not os.path.lexists(path) or is_reparse(path) or not path.is_file():
        raise BlenderResealV2Error(f"evidence for provenance injection is invalid: {path}")
    record = read_json(path)
    existing = record.get("reseal_v2_provenance")
    if existing is not None and existing != provenance:
        raise BlenderResealV2Error("evidence contains conflicting reseal v2 provenance")
    record["reseal_v2_provenance"] = dict(provenance)
    temporary = path.parent / f".{path.name}.reseal_v2_injection.tmp"
    if os.path.lexists(temporary):
        raise BlenderResealV2Error("provenance injection temporary path already exists")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(record, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        if is_reparse(temporary) or not temporary.is_file():
            raise BlenderResealV2Error("provenance temporary file became non-regular")
        os.replace(temporary, path)
    finally:
        if os.path.lexists(temporary):
            temporary.unlink()
    verified = read_json(path)
    if verified.get("reseal_v2_provenance") != provenance:
        raise BlenderResealV2Error("provenance did not persist exactly")
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def main(argv: Sequence[str] | None = None) -> int:
    # This bootstrap runs before any project-local import.
    config, bootstrap = bootstrap_verify_all_project_modules()
    delegated_argument = config["command_contract"]["delegated_config_argument"]
    parse_exact_worker_argv(argv, expected=delegated_argument)
    bootstrap_command = bootstrap_expected_command(config)
    bootstrap_authorization = bootstrap_verify_live_authorization(
        config, bootstrap_command
    )
    controller = _load_verified_controller(config)
    sealed_config, preparation = controller.verify_preparation()
    if sealed_config != config:
        raise BlenderResealV2Error("bootstrap/controller config records disagree")
    command = controller.build_command(config)
    if command != bootstrap_command:
        raise BlenderResealV2Error("bootstrap/controller command records disagree")
    authorization = controller.verify_authorization(config, preparation, command)
    if authorization != bootstrap_authorization:
        raise BlenderResealV2Error(
            "bootstrap/controller authorization records disagree"
        )
    provenance = controller.provenance_record(config, preparation, authorization)
    verify_pre_run_journal(
        controller, config, preparation, authorization, provenance, command
    )
    verify_blender_runtime(config)
    validate_delegated_contract(controller, config)
    # Only now may the old topology module and its dependency graph be imported.
    assert_project_modules_not_preloaded(config)
    topology_impl = load_verified_project_sources(config)
    imported_path = Path(topology_impl.__file__).resolve()
    expected_topology = lexical_project_path(
        config["bound_artifacts"]["topology_repair_implementation"]["path"],
        require_exists=True,
        require_leaf_regular=True,
    ).resolve()
    if imported_path != expected_topology:
        raise BlenderResealV2Error(f"wrong topology implementation imported: {imported_path}")
    verify_imported_dependency_files(config)
    original_bind = topology_impl.bind_attempt04_runtime

    def bind_with_provenance(repair_config: Mapping[str, Any]) -> None:
        original_bind(repair_config)  # This performs the inherited RUNTIME.clear().
        topology_impl.RUNTIME["reseal_v2_provenance"] = provenance
        topology_impl.RUNTIME["reseal_v2_bootstrap"] = bootstrap

    topology_impl.bind_attempt04_runtime = bind_with_provenance
    topology_impl.REPAIR_CONFIG = Path(delegated_argument)
    result = int(topology_impl.main())
    if topology_impl.RUNTIME.get("reseal_v2_provenance") != provenance:
        raise BlenderResealV2Error("reseal provenance did not survive old RUNTIME.clear")
    output = config["output_contract"]
    directory = lexical_project_path(output["effective_directory"], require_exists=True)
    build = directory / output["build_evidence_basename"]
    failure = directory / output["failure_evidence_basename"]
    if result == 0:
        inject_provenance_record(build, provenance)
    else:
        inject_provenance_record(failure, provenance)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
