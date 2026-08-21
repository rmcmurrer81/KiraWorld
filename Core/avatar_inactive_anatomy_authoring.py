"""Private, inactive anatomy authoring gated by the audited package preflight.

This module is deliberately narrower than a body builder.  It can copy one
qualified carrier into a fresh private workspace and import the exact GLB
sources named by a READY preflight as a separate, default-hidden anatomy
module.  It does not modify an input file, implement biological function,
activate a resident, infer review, or authorize public export.

The controller and Blender worker both re-run the same read-only preflight.
The Blender-specific API is behind a small adapter so the security and truth
boundaries can be tested without opening a real resident carrier.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat
import subprocess
from typing import Any, Mapping, Protocol, Sequence

from Core import avatar_anatomy_package as anatomy_preflight


JOB_SCHEMA = "kira.avatar.private_inactive_anatomy_authoring_job.v1"
WORKER_RESULT_SCHEMA = "kira.avatar.private_inactive_anatomy_worker_result.v1"
MANIFEST_SCHEMA = "kira.avatar.private_inactive_anatomy_manifest.v1"
RECEIPT_SCHEMA = "kira.avatar.private_inactive_anatomy_receipt.v1"
AUTHORED_STATUS = anatomy_preflight.AUTHORED_PRIVATE_INACTIVE_PENDING_GEOMETRY_REVIEW
PRIVATE_WORKSPACE_PARENT = Path("Avatar/avatar_builder/workspaces")
PRIVATE_OUTPUT_PREFIX = "private_inactive_anatomy_"
WORKER_SCRIPT = Path("tools/blender_author_inactive_anatomy_package.py")
JOB_NAME = "authoring_job.json"
ARTIFACT_NAME = "private_inactive_internal_anatomy.blend"
WORKER_RESULT_NAME = "worker_result.json"
MANIFEST_NAME = "manifest.json"
RECEIPT_NAME = "receipt.json"
MODULE_COLLECTION_NAME = "PRIVATE_INACTIVE_INTERNAL_ANATOMY"
SAFE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,95}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class InactiveAnatomyAuthoringError(ValueError):
    """Fail-closed plan, execution, worker, or integrity error."""


class AnatomySceneAdapter(Protocol):
    """Minimal scene operations required by the deterministic worker engine."""

    def load_carrier_read_only(self, carrier_path: Path) -> None: ...

    def create_hidden_module_collection(self, collection_name: str) -> Any: ...

    def import_normalized_source(
        self,
        *,
        source_path: Path,
        source_collection_name: str,
        module_collection: Any,
        normalization_matrix: Sequence[float],
        object_name_prefix: str,
        source_sha256: str,
    ) -> list[dict[str, Any]]: ...

    def save_private_copy(self, output_path: Path) -> None: ...


@dataclass(frozen=True)
class PlannedAuthoring:
    project_root: Path
    request_path: str
    run_id: str
    output_root: Path
    report: dict[str, Any]
    job: dict[str, Any]


@dataclass(frozen=True)
class _FreshDirectoryIdentity:
    output_path: Path
    parent_path: Path
    output_device: int
    output_inode: int
    parent_device: int
    parent_inode: int


def _safe_id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not SAFE_ID_RE.fullmatch(value):
        raise InactiveAnatomyAuthoringError(f"{label} must be a safe lowercase identifier")
    return value


def _sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise InactiveAnatomyAuthoringError(f"{label} must be a lowercase SHA-256")
    return value


def _strict_object(value: Any, fields: set[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise InactiveAnatomyAuthoringError(f"{label} fields do not match the version-1 schema")
    return value


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise InactiveAnatomyAuthoringError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise InactiveAnatomyAuthoringError(f"non-finite JSON number: {value}")


def _read_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = anatomy_preflight._read_bytes(path)
        value = json.loads(
            payload.decode("utf-8-sig"),
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_nonfinite,
        )
    except InactiveAnatomyAuthoringError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise InactiveAnatomyAuthoringError(f"{label} is not strict UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise InactiveAnatomyAuthoringError(f"{label} must be a JSON object")
    return value


def _write_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    payload = anatomy_preflight.canonical_json_bytes(value)
    try:
        with anatomy_preflight._io_path(path).open("xb") as stream:
            stream.write(payload)
    except FileExistsError as exc:
        raise InactiveAnatomyAuthoringError(f"fresh output already exists: {path.name}") from exc
    except OSError as exc:
        raise InactiveAnatomyAuthoringError(f"cannot write fresh output: {path.name}") from exc


def _relative(path: Path, root: Path) -> str:
    return anatomy_preflight._project_relative(path, root)


def _private_output_root(root: Path, run_id: str, *, must_exist: bool) -> Path:
    run_id = _safe_id(run_id, "run_id")
    parent = anatomy_preflight._lexical_absolute(root / PRIVATE_WORKSPACE_PARENT)
    if not anatomy_preflight._io_path(parent).is_dir():
        raise InactiveAnatomyAuthoringError("private workspace parent is missing")
    current = parent
    while current != root:
        if anatomy_preflight._is_reparse_point(current):
            raise InactiveAnatomyAuthoringError(
                "private workspace path contains a reparse point"
            )
        if current.parent == current:
            raise InactiveAnatomyAuthoringError("private workspace path escapes the project")
        current = current.parent
    output = anatomy_preflight._lexical_absolute(parent / f"{PRIVATE_OUTPUT_PREFIX}{run_id}")
    if not anatomy_preflight._is_within(output, parent):
        raise InactiveAnatomyAuthoringError("private output root escapes its workspace")
    exists = anatomy_preflight._io_path(output).exists()
    if must_exist and not exists:
        raise InactiveAnatomyAuthoringError("private output root is missing")
    if not must_exist and exists:
        raise InactiveAnatomyAuthoringError("private output root must be fresh")
    if exists:
        if not anatomy_preflight._io_path(output).is_dir():
            raise InactiveAnatomyAuthoringError("private output root is not a directory")
        if anatomy_preflight._is_reparse_point(output):
            raise InactiveAnatomyAuthoringError("private output root is a reparse point")
    return output


def _bound_file(
    root: Path,
    relative_path: Any,
    expected_bytes: Any,
    expected_sha256: Any,
    label: str,
) -> Path:
    path = anatomy_preflight._project_file(root, relative_path, label)
    if isinstance(expected_bytes, bool) or not isinstance(expected_bytes, int) or expected_bytes <= 0:
        raise InactiveAnatomyAuthoringError(f"{label} bytes must be a positive integer")
    expected_sha = _sha(expected_sha256, f"{label} sha256")
    if anatomy_preflight._file_size(path) != expected_bytes:
        raise InactiveAnatomyAuthoringError(f"{label} byte count changed")
    if anatomy_preflight.sha256_file(path) != expected_sha:
        raise InactiveAnatomyAuthoringError(f"{label} SHA-256 changed")
    return path


def _source_project_path(root: Path, report: Mapping[str, Any], source: Mapping[str, Any]) -> Path:
    package = report["source_package"]
    manifest_path = Path(str(package["manifest_path"]))
    source_name = str(source["path"])
    combined = (manifest_path.parent / Path(source_name)).as_posix()
    return _bound_file(root, combined, source["bytes"], source["sha256"], "anatomy source")


def _input_records(root: Path, report: Mapping[str, Any]) -> list[dict[str, Any]]:
    carrier = report["carrier"]
    carrier_path = _bound_file(
        root,
        carrier["path"],
        carrier["bytes"],
        carrier["sha256"],
        "carrier",
    )
    records: list[dict[str, Any]] = [
        {
            "role": "carrier",
            "path": _relative(carrier_path, root),
            "bytes": anatomy_preflight._file_size(carrier_path),
            "sha256": anatomy_preflight.sha256_file(carrier_path),
        }
    ]
    for source in sorted(report["source_package"]["files"], key=lambda row: row["path"]):
        source_path = _source_project_path(root, report, source)
        records.append(
            {
                "role": "anatomy_source",
                "path": _relative(source_path, root),
                "bytes": anatomy_preflight._file_size(source_path),
                "sha256": anatomy_preflight.sha256_file(source_path),
            }
        )
    return records


def _verify_input_records(root: Path, records: Sequence[Mapping[str, Any]]) -> None:
    for index, record in enumerate(records):
        _bound_file(
            root,
            record.get("path"),
            record.get("bytes"),
            record.get("sha256"),
            f"bound input {index}",
        )


def _source_collection_name(index: int, source_path: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9_]+", "_", Path(source_path).stem).strip("_") or "SOURCE"
    return f"ANATOMY_SOURCE_{index:03d}_{stem[:48]}"


def _job_document(
    root: Path,
    *,
    request_path: str,
    run_id: str,
    report: Mapping[str, Any],
    existing_output_root: Path | None = None,
) -> dict[str, Any]:
    output_root = (
        existing_output_root
        if existing_output_root is not None
        else _private_output_root(root, run_id, must_exist=False)
    )
    normalization = report["normalization"]["per_source_transform"]
    components = report["components"]
    sources: list[dict[str, Any]] = []
    for index, source in enumerate(
        sorted(report["source_package"]["files"], key=lambda row: row["path"]),
        start=1,
    ):
        source_path = _source_project_path(root, report, source)
        source_name = str(source["path"])
        if source_name not in normalization:
            raise InactiveAnatomyAuthoringError("preflight omitted a source normalization matrix")
        sources.append(
            {
                "source_id": f"source_{index:03d}",
                "path": _relative(source_path, root),
                "bytes": source["bytes"],
                "sha256": source["sha256"],
                "collection_name": _source_collection_name(index, source_name),
                "normalization_matrix": list(normalization[source_name]),
                "component_ids": sorted(
                    row["anatomy_id"] for row in components if row["source_file"] == source_name
                ),
            }
        )
    carrier = report["carrier"]
    document: dict[str, Any] = {
        "schema": JOB_SCHEMA,
        "schema_version": 1,
        "status": anatomy_preflight.READY_FOR_PRIVATE_INACTIVE_AUTHORING,
        "run_id": run_id,
        "package_id": report["package_id"],
        "candidate_id": report["candidate_id"],
        "subject_id": report["subject_id"],
        "maturity_status": report["maturity_status"],
        "anatomy_profile_id": report["anatomy_profile_id"],
        "request_path": request_path,
        "preflight_receipt_sha256": report["preflight_receipt_sha256"],
        "output": {
            "root": _relative(output_root, root),
            "artifact": _relative(output_root / ARTIFACT_NAME, root),
            "worker_result": _relative(output_root / WORKER_RESULT_NAME, root),
        },
        "carrier": {
            "path": carrier["path"],
            "bytes": carrier["bytes"],
            "sha256": carrier["sha256"],
            "access": "READ_ONLY_INPUT_SAVE_COPY_ONLY",
        },
        "sources": sources,
        "separation": {
            "module_collection_name": MODULE_COLLECTION_NAME,
            "separate_artifact": True,
            "one_hidden_collection_per_source": True,
            "objects_joined": False,
            "default_hidden": True,
            "contains_hair": False,
            "contains_clothing": False,
        },
        "truth": {
            "medical_completeness_claimed": False,
            "whole_body_complete": False,
            "external_anatomy_complete": False,
            "internal_anatomy_complete": False,
            "function_implemented": False,
            "owner_approved": False,
            "runtime_activation_allowed": False,
            "public_export_allowed": False,
        },
        "execution_authorization": {
            "versioned_private_controller": True,
            "ready_preflight_required_again_in_worker": True,
            "background_required": True,
            "factory_startup_required": True,
            "autoexec_disabled_required": True,
            "fresh_output_root_required": True,
            "input_mutation_allowed": False,
        },
    }
    document["job_receipt_sha256"] = anatomy_preflight.canonical_sha256(document)
    return document


def plan_private_inactive_anatomy_authoring(
    project_root: str | Path,
    *,
    request_path: str,
    run_id: str,
) -> PlannedAuthoring:
    """Return a deterministic plan, or refuse before creating an output root."""

    try:
        root = anatomy_preflight._validated_project_root(project_root)
        request = anatomy_preflight.load_preflight_request(root, request_path)
        report = anatomy_preflight.evaluate_avatar_anatomy_package_preflight(root, request)
    except (anatomy_preflight.AvatarAnatomyPackageError, OSError) as exc:
        raise InactiveAnatomyAuthoringError(f"anatomy preflight is invalid: {exc}") from exc
    if report.get("status") != anatomy_preflight.READY_FOR_PRIVATE_INACTIVE_AUTHORING:
        raise InactiveAnatomyAuthoringError(
            "authoring refused: preflight status is " + str(report.get("status"))
        )
    if report.get("blockers") != [] or report.get("missing_required_structures") != []:
        raise InactiveAnatomyAuthoringError("authoring refused: READY preflight retained blockers")
    request_file = anatomy_preflight._project_file(root, request_path, "request_path")
    normalized_request_path = _relative(request_file, root)
    run_id = _safe_id(run_id, "run_id")
    output_root = _private_output_root(root, run_id, must_exist=False)
    job = _job_document(
        root,
        request_path=normalized_request_path,
        run_id=run_id,
        report=report,
    )
    return PlannedAuthoring(
        project_root=root,
        request_path=normalized_request_path,
        run_id=run_id,
        output_root=output_root,
        report=dict(report),
        job=job,
    )


def _validate_job(root: Path, job_path: Path) -> tuple[dict[str, Any], dict[str, Any], Path]:
    job = _read_json_object(job_path, "authoring job")
    _strict_object(
        job,
        {
            "schema",
            "schema_version",
            "status",
            "run_id",
            "package_id",
            "candidate_id",
            "subject_id",
            "maturity_status",
            "anatomy_profile_id",
            "request_path",
            "preflight_receipt_sha256",
            "output",
            "carrier",
            "sources",
            "separation",
            "truth",
            "execution_authorization",
            "job_receipt_sha256",
        },
        "authoring job",
    )
    if job.get("schema") != JOB_SCHEMA or job.get("schema_version") != 1:
        raise InactiveAnatomyAuthoringError("unsupported authoring job schema")
    receipt = _sha(job.get("job_receipt_sha256"), "job receipt")
    unsigned = dict(job)
    del unsigned["job_receipt_sha256"]
    if receipt != anatomy_preflight.canonical_sha256(unsigned):
        raise InactiveAnatomyAuthoringError("authoring job receipt mismatch")
    if job.get("status") != anatomy_preflight.READY_FOR_PRIVATE_INACTIVE_AUTHORING:
        raise InactiveAnatomyAuthoringError("worker refuses a job that is not READY")

    request = anatomy_preflight.load_preflight_request(root, str(job.get("request_path")))
    report = anatomy_preflight.evaluate_avatar_anatomy_package_preflight(root, request)
    if report.get("status") != anatomy_preflight.READY_FOR_PRIVATE_INACTIVE_AUTHORING:
        raise InactiveAnatomyAuthoringError("worker preflight is not READY")
    if report.get("preflight_receipt_sha256") != job.get("preflight_receipt_sha256"):
        raise InactiveAnatomyAuthoringError("worker preflight receipt changed")
    output_root = _private_output_root(root, str(job["run_id"]), must_exist=True)
    expected = _job_document(
        root,
        request_path=str(job["request_path"]),
        run_id=_safe_id(job.get("run_id"), "run_id"),
        report=report,
        existing_output_root=output_root,
    )
    if anatomy_preflight.canonical_json_bytes(job) != anatomy_preflight.canonical_json_bytes(expected):
        raise InactiveAnatomyAuthoringError("authoring job differs from its READY preflight")
    if anatomy_preflight._lexical_absolute(job_path.parent) != output_root:
        raise InactiveAnatomyAuthoringError("authoring job is outside its fresh output root")
    return job, report, output_root


def run_blender_authoring_job(
    project_root: str | Path,
    *,
    job_path: str | Path,
    adapter: AnatomySceneAdapter,
) -> dict[str, Any]:
    """Execute one already-created job inside Blender through ``adapter``."""

    root = anatomy_preflight._validated_project_root(project_root)
    job_file = anatomy_preflight._project_file(root, str(job_path), "job_path")
    job, report, output_root = _validate_job(root, job_file)
    expected_initial = {JOB_NAME}
    actual_initial = {item.name for item in anatomy_preflight._io_path(output_root).iterdir()}
    if actual_initial != expected_initial:
        raise InactiveAnatomyAuthoringError("fresh worker root contains unexpected entries")

    inputs = _input_records(root, report)
    _verify_input_records(root, inputs)
    carrier = job["carrier"]
    carrier_path = _bound_file(
        root,
        carrier["path"],
        carrier["bytes"],
        carrier["sha256"],
        "worker carrier",
    )
    artifact_path = anatomy_preflight._lexical_absolute(output_root / ARTIFACT_NAME)
    result_path = anatomy_preflight._lexical_absolute(output_root / WORKER_RESULT_NAME)
    adapter.load_carrier_read_only(carrier_path)
    module_collection = adapter.create_hidden_module_collection(MODULE_COLLECTION_NAME)

    imports: list[dict[str, Any]] = []
    seen_collections: set[str] = set()
    for source in job["sources"]:
        collection_name = str(source["collection_name"])
        if collection_name in seen_collections:
            raise InactiveAnatomyAuthoringError("source collection names are not unique")
        seen_collections.add(collection_name)
        source_path = _bound_file(
            root,
            source["path"],
            source["bytes"],
            source["sha256"],
            "worker anatomy source",
        )
        objects = adapter.import_normalized_source(
            source_path=source_path,
            source_collection_name=collection_name,
            module_collection=module_collection,
            normalization_matrix=source["normalization_matrix"],
            object_name_prefix=str(source["source_id"]),
            source_sha256=str(source["sha256"]),
        )
        if not isinstance(objects, list) or not objects:
            raise InactiveAnatomyAuthoringError("an anatomy source imported no objects")
        clean_objects: list[dict[str, str]] = []
        names: set[str] = set()
        mesh_count = 0
        for item in objects:
            if not isinstance(item, Mapping) or set(item) != {"name", "type"}:
                raise InactiveAnatomyAuthoringError("imported object evidence is invalid")
            name = str(item["name"])
            object_type = str(item["type"])
            if not name or name in names or not object_type:
                raise InactiveAnatomyAuthoringError("imported object names are invalid")
            names.add(name)
            mesh_count += object_type == "MESH"
            clean_objects.append({"name": name, "type": object_type})
        if mesh_count == 0:
            raise InactiveAnatomyAuthoringError("an anatomy source imported no mesh object")
        imports.append(
            {
                "source_id": source["source_id"],
                "source_path": source["path"],
                "source_sha256": source["sha256"],
                "collection_name": collection_name,
                "normalization_matrix": list(source["normalization_matrix"]),
                "component_ids": list(source["component_ids"]),
                "object_count": len(clean_objects),
                "mesh_object_count": mesh_count,
                "objects": sorted(clean_objects, key=lambda row: (row["name"], row["type"])),
                "default_hidden": True,
                "function_implemented": False,
            }
        )

    adapter.save_private_copy(artifact_path)
    if not anatomy_preflight._io_path(artifact_path).is_file():
        raise InactiveAnatomyAuthoringError("Blender did not create the private artifact")
    if anatomy_preflight._is_reparse_point(artifact_path):
        raise InactiveAnatomyAuthoringError("private artifact is a reparse point")
    if getattr(anatomy_preflight._io_path(artifact_path).stat(), "st_nlink", 1) != 1:
        raise InactiveAnatomyAuthoringError("private artifact is multiply linked")
    with anatomy_preflight._io_path(artifact_path).open("rb") as stream:
        if stream.read(7) != b"BLENDER":
            raise InactiveAnatomyAuthoringError("private artifact is not an uncompressed Blender file")
    _verify_input_records(root, inputs)

    source_integrity = [
        {
            **record,
            "before_sha256": record["sha256"],
            "after_sha256": record["sha256"],
            "changed": False,
        }
        for record in inputs
    ]
    result: dict[str, Any] = {
        "schema": WORKER_RESULT_SCHEMA,
        "schema_version": 1,
        "status": AUTHORED_STATUS,
        "run_id": job["run_id"],
        "package_id": job["package_id"],
        "candidate_id": job["candidate_id"],
        "subject_id": job["subject_id"],
        "job_receipt_sha256": job["job_receipt_sha256"],
        "preflight_receipt_sha256": job["preflight_receipt_sha256"],
        "artifact": {
            "path": _relative(artifact_path, root),
            "bytes": anatomy_preflight._file_size(artifact_path),
            "sha256": anatomy_preflight.sha256_file(artifact_path),
        },
        "module_collection": {
            "name": MODULE_COLLECTION_NAME,
            "separate_from_carrier_objects": True,
            "default_hidden": True,
        },
        "imports": sorted(imports, key=lambda row: row["source_id"]),
        "source_integrity": source_integrity,
        "separation": dict(job["separation"]),
        "truth": dict(job["truth"]),
        "build_performed": True,
        "blender_invoked": True,
    }
    result["worker_receipt_sha256"] = anatomy_preflight.canonical_sha256(result)
    _write_exclusive(result_path, result)
    return result


class BpyInactiveAnatomySceneAdapter:
    """Blender implementation used only by the background worker entrypoint."""

    def __init__(self, bpy_module: Any, matrix_factory: Any) -> None:
        self._bpy = bpy_module
        self._matrix_factory = matrix_factory

    def load_carrier_read_only(self, carrier_path: Path) -> None:
        result = self._bpy.ops.wm.open_mainfile(
            filepath=str(carrier_path),
            load_ui=False,
            use_scripts=False,
        )
        if "FINISHED" not in result:
            raise InactiveAnatomyAuthoringError("Blender could not open the carrier read-only")
        self._bpy.context.preferences.filepaths.save_version = 0

    def create_hidden_module_collection(self, collection_name: str) -> Any:
        if self._bpy.data.collections.get(collection_name) is not None:
            raise InactiveAnatomyAuthoringError("carrier already contains the reserved module collection")
        collection = self._bpy.data.collections.new(collection_name)
        self._bpy.context.scene.collection.children.link(collection)
        collection.hide_viewport = True
        collection.hide_render = True
        collection["private_inactive"] = True
        collection["function_implemented"] = False
        collection["runtime_activation_allowed"] = False
        collection["public_export_allowed"] = False
        return collection

    def import_normalized_source(
        self,
        *,
        source_path: Path,
        source_collection_name: str,
        module_collection: Any,
        normalization_matrix: Sequence[float],
        object_name_prefix: str,
        source_sha256: str,
    ) -> list[dict[str, Any]]:
        if self._bpy.data.collections.get(source_collection_name) is not None:
            raise InactiveAnatomyAuthoringError("source collection already exists")
        source_collection = self._bpy.data.collections.new(source_collection_name)
        module_collection.children.link(source_collection)
        source_collection.hide_viewport = True
        source_collection.hide_render = True
        source_collection["private_inactive"] = True
        source_collection["function_implemented"] = False
        before_objects = {obj.as_pointer() for obj in self._bpy.data.objects}
        result = self._bpy.ops.import_scene.gltf(filepath=str(source_path))
        if "FINISHED" not in result:
            raise InactiveAnatomyAuthoringError("Blender GLB import failed")
        imported = sorted(
            (obj for obj in self._bpy.data.objects if obj.as_pointer() not in before_objects),
            key=lambda obj: (str(obj.name), str(obj.type)),
        )
        if not imported:
            raise InactiveAnatomyAuthoringError("Blender GLB import created no objects")
        imported_pointers = {obj.as_pointer() for obj in imported}
        rows = [tuple(float(value) for value in normalization_matrix[index:index + 4]) for index in range(0, 16, 4)]
        normalization = self._matrix_factory(rows)
        for obj in imported:
            if obj.parent is None or obj.parent.as_pointer() not in imported_pointers:
                obj.matrix_world = normalization @ obj.matrix_world
        evidence: list[dict[str, Any]] = []
        for index, obj in enumerate(imported, start=1):
            original_name = re.sub(r"[^A-Za-z0-9_]+", "_", str(obj.name)).strip("_") or "object"
            obj.name = f"{object_name_prefix}_{index:03d}_{original_name[:48]}"
            for collection in list(obj.users_collection):
                collection.objects.unlink(obj)
            source_collection.objects.link(obj)
            obj.hide_render = True
            obj.hide_viewport = True
            obj.hide_set(True)
            obj["private_inactive"] = True
            obj["source_sha256"] = source_sha256
            obj["function_implemented"] = False
            obj["runtime_activation_allowed"] = False
            obj["public_export_allowed"] = False
            evidence.append({"name": str(obj.name), "type": str(obj.type)})
        return evidence

    def save_private_copy(self, output_path: Path) -> None:
        if anatomy_preflight._io_path(output_path).exists():
            raise InactiveAnatomyAuthoringError("private Blender output already exists")
        result = self._bpy.ops.wm.save_as_mainfile(
            filepath=str(output_path),
            check_existing=False,
            compress=False,
            copy=True,
        )
        if "FINISHED" not in result:
            raise InactiveAnatomyAuthoringError("Blender could not save the private copy")


def _validate_blender_executable(path: str | Path) -> Path:
    try:
        blender = Path(path).resolve(strict=True)
        metadata = os.lstat(blender)
    except OSError as exc:
        raise InactiveAnatomyAuthoringError("Blender executable is unavailable") from exc
    marker = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    attributes = getattr(metadata, "st_file_attributes", 0)
    if stat.S_ISLNK(metadata.st_mode) or bool(marker and attributes & marker):
        raise InactiveAnatomyAuthoringError("Blender executable is a symlink or reparse point")
    if not blender.is_file():
        raise InactiveAnatomyAuthoringError("Blender executable is not a regular file")
    if getattr(metadata, "st_nlink", 1) != 1:
        raise InactiveAnatomyAuthoringError("Blender executable must not be multiply linked")
    return blender


def _directory_file_id(path: Path, label: str) -> tuple[int, int]:
    try:
        metadata = os.lstat(anatomy_preflight._io_path(path))
    except OSError as exc:
        raise InactiveAnatomyAuthoringError(f"cannot inspect {label} identity") from exc
    marker = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    attributes = getattr(metadata, "st_file_attributes", 0)
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or stat.S_ISLNK(metadata.st_mode)
        or bool(marker and attributes & marker)
    ):
        raise InactiveAnatomyAuthoringError(f"{label} is not a regular non-reparse directory")
    device = int(metadata.st_dev)
    inode = int(metadata.st_ino)
    if device < 0 or inode <= 0:
        raise InactiveAnatomyAuthoringError(f"{label} has no stable directory identity")
    return device, inode


def _capture_fresh_directory_identity(output_root: Path) -> _FreshDirectoryIdentity:
    output = anatomy_preflight._lexical_absolute(output_root)
    parent = anatomy_preflight._lexical_absolute(output.parent)
    output_device, output_inode = _directory_file_id(output, "fresh output root")
    parent_device, parent_inode = _directory_file_id(parent, "fresh output parent")
    return _FreshDirectoryIdentity(
        output_path=output,
        parent_path=parent,
        output_device=output_device,
        output_inode=output_inode,
        parent_device=parent_device,
        parent_inode=parent_inode,
    )


def _quarantine_fresh_output_root(
    project_root: Path,
    output_root: Path,
    identity: _FreshDirectoryIdentity,
) -> None:
    root = anatomy_preflight._validated_project_root(project_root)
    output = anatomy_preflight._lexical_absolute(output_root)
    parent = anatomy_preflight._lexical_absolute(output.parent)
    if output != identity.output_path or parent != identity.parent_path:
        raise InactiveAnatomyAuthoringError(
            "rollback cleanup refused: immutable output path changed"
        )
    if not anatomy_preflight._is_within(output, parent) or not anatomy_preflight._is_within(
        parent, root
    ):
        raise InactiveAnatomyAuthoringError(
            "rollback cleanup refused: output containment changed"
        )
    current = parent
    while True:
        if anatomy_preflight._is_reparse_point(current):
            raise InactiveAnatomyAuthoringError(
                "rollback cleanup refused: output ancestry contains a reparse point"
            )
        if current == root:
            break
        if current.parent == current:
            raise InactiveAnatomyAuthoringError(
                "rollback cleanup refused: output ancestry escapes the project"
            )
        current = current.parent
    if _directory_file_id(parent, "rollback output parent") != (
        identity.parent_device,
        identity.parent_inode,
    ):
        raise InactiveAnatomyAuthoringError(
            "rollback cleanup refused: output parent identity changed"
        )
    if not anatomy_preflight._io_path(output_root).exists():
        return
    if _directory_file_id(output, "rollback output root") != (
        identity.output_device,
        identity.output_inode,
    ):
        raise InactiveAnatomyAuthoringError(
            "rollback cleanup refused: output directory identity changed"
        )
    quarantine = parent / (
        ".rollback_" + output.name + "_" + secrets.token_hex(16)
    )
    if anatomy_preflight._io_path(quarantine).exists():
        raise InactiveAnatomyAuthoringError(
            "rollback cleanup refused: quarantine path already exists"
        )
    try:
        os.rename(
            anatomy_preflight._io_path(output),
            anatomy_preflight._io_path(quarantine),
        )
    except OSError as exc:
        raise InactiveAnatomyAuthoringError(
            "rollback cleanup refused: could not quarantine the output root"
        ) from exc
    if _directory_file_id(quarantine, "quarantined output root") != (
        identity.output_device,
        identity.output_inode,
    ):
        raise InactiveAnatomyAuthoringError(
            "rollback cleanup refused: quarantined directory identity changed"
        )
    # Retain failed output for recoverable/manual review. Recursive deletion by
    # pathname after an external process fails has an unavoidable late-swap
    # race on platforms without handle-relative tree removal. Retention avoids
    # ever deleting an unrelated directory substituted at this path.


def _validated_worker_result(
    root: Path,
    plan: PlannedAuthoring,
    result_path: Path,
    artifact_path: Path,
) -> dict[str, Any]:
    result = _read_json_object(result_path, "worker result")
    required = {
        "schema",
        "schema_version",
        "status",
        "run_id",
        "package_id",
        "candidate_id",
        "subject_id",
        "job_receipt_sha256",
        "preflight_receipt_sha256",
        "artifact",
        "module_collection",
        "imports",
        "source_integrity",
        "separation",
        "truth",
        "build_performed",
        "blender_invoked",
        "worker_receipt_sha256",
    }
    _strict_object(result, required, "worker result")
    if result.get("schema") != WORKER_RESULT_SCHEMA or result.get("schema_version") != 1:
        raise InactiveAnatomyAuthoringError("unsupported worker result schema")
    receipt = _sha(result.get("worker_receipt_sha256"), "worker receipt")
    unsigned = dict(result)
    del unsigned["worker_receipt_sha256"]
    if receipt != anatomy_preflight.canonical_sha256(unsigned):
        raise InactiveAnatomyAuthoringError("worker receipt mismatch")
    for key, expected in (
        ("status", AUTHORED_STATUS),
        ("run_id", plan.run_id),
        ("package_id", plan.job["package_id"]),
        ("candidate_id", plan.job["candidate_id"]),
        ("subject_id", plan.job["subject_id"]),
        ("job_receipt_sha256", plan.job["job_receipt_sha256"]),
        ("preflight_receipt_sha256", plan.job["preflight_receipt_sha256"]),
    ):
        if result.get(key) != expected:
            raise InactiveAnatomyAuthoringError(f"worker result {key} mismatch")
    if result.get("build_performed") is not True or result.get("blender_invoked") is not True:
        raise InactiveAnatomyAuthoringError("worker did not attest the bounded build")
    if result.get("truth") != plan.job["truth"] or result.get("separation") != plan.job["separation"]:
        raise InactiveAnatomyAuthoringError("worker changed the truth or separation boundary")
    module = result.get("module_collection")
    if not isinstance(module, Mapping) or module != {
        "name": MODULE_COLLECTION_NAME,
        "separate_from_carrier_objects": True,
        "default_hidden": True,
    }:
        raise InactiveAnatomyAuthoringError("worker module collection is not separate and hidden")
    artifact = result.get("artifact")
    if not isinstance(artifact, Mapping):
        raise InactiveAnatomyAuthoringError("worker artifact binding is invalid")
    actual_artifact = {
        "path": _relative(artifact_path, root),
        "bytes": anatomy_preflight._file_size(artifact_path),
        "sha256": anatomy_preflight.sha256_file(artifact_path),
    }
    if artifact != actual_artifact:
        raise InactiveAnatomyAuthoringError("worker artifact binding mismatch")
    expected_sources = plan.job["sources"]
    imports = result.get("imports")
    if not isinstance(imports, list) or len(imports) != len(expected_sources):
        raise InactiveAnatomyAuthoringError("worker source import count mismatch")
    for expected, imported in zip(expected_sources, imports):
        if not isinstance(imported, Mapping):
            raise InactiveAnatomyAuthoringError("worker import evidence is invalid")
        for key, expected_value in (
            ("source_id", expected["source_id"]),
            ("source_path", expected["path"]),
            ("source_sha256", expected["sha256"]),
            ("collection_name", expected["collection_name"]),
            ("normalization_matrix", expected["normalization_matrix"]),
            ("component_ids", expected["component_ids"]),
            ("default_hidden", True),
            ("function_implemented", False),
        ):
            if imported.get(key) != expected_value:
                raise InactiveAnatomyAuthoringError(f"worker import {key} mismatch")
        if isinstance(imported.get("object_count"), bool) or not isinstance(imported.get("object_count"), int) or imported["object_count"] <= 0:
            raise InactiveAnatomyAuthoringError("worker object count is invalid")
        if isinstance(imported.get("mesh_object_count"), bool) or not isinstance(imported.get("mesh_object_count"), int) or imported["mesh_object_count"] <= 0:
            raise InactiveAnatomyAuthoringError("worker mesh count is invalid")
    integrity = result.get("source_integrity")
    expected_integrity = _input_records(root, plan.report)
    if not isinstance(integrity, list) or len(integrity) != len(expected_integrity):
        raise InactiveAnatomyAuthoringError("worker input-integrity record count mismatch")
    for expected, row in zip(expected_integrity, integrity):
        if not isinstance(row, Mapping) or set(row) != {
            "role",
            "path",
            "bytes",
            "sha256",
            "before_sha256",
            "after_sha256",
            "changed",
        }:
            raise InactiveAnatomyAuthoringError("worker input-integrity evidence is invalid")
        for key in ("role", "path", "bytes", "sha256"):
            if row.get(key) != expected[key]:
                raise InactiveAnatomyAuthoringError("worker input-integrity binding mismatch")
    _verify_input_records(root, integrity)
    if any(
        row.get("changed") is not False
        or row.get("before_sha256") != row.get("sha256")
        or row.get("after_sha256") != row.get("sha256")
        for row in result["source_integrity"]
    ):
        raise InactiveAnatomyAuthoringError("worker reported an input mutation")
    return result


def execute_private_inactive_anatomy_authoring(
    project_root: str | Path,
    *,
    request_path: str,
    run_id: str,
    blender_path: str | Path,
    timeout_seconds: int = 900,
    runner: Any | None = None,
) -> dict[str, Any]:
    """Run Blender once and atomically retain only a validated private result."""

    plan = plan_private_inactive_anatomy_authoring(
        project_root,
        request_path=request_path,
        run_id=run_id,
    )
    root = plan.project_root
    blender = _validate_blender_executable(blender_path)
    worker = anatomy_preflight._project_file(root, WORKER_SCRIPT.as_posix(), "Blender worker")
    worker_sha = anatomy_preflight.sha256_file(worker)
    blender_sha = anatomy_preflight.sha256_file(blender)
    input_records = _input_records(root, plan.report)
    created = False
    rollback_identity: _FreshDirectoryIdentity | None = None
    try:
        anatomy_preflight._io_path(plan.output_root).mkdir(exist_ok=False)
        created = True
        rollback_identity = _capture_fresh_directory_identity(plan.output_root)
        job_path = plan.output_root / JOB_NAME
        artifact_path = plan.output_root / ARTIFACT_NAME
        result_path = plan.output_root / WORKER_RESULT_NAME
        _write_exclusive(job_path, plan.job)
        command = [
            str(blender),
            "--background",
            "--factory-startup",
            "--disable-autoexec",
            "--python",
            str(worker),
            "--",
            "--project-root",
            str(root),
            "--job",
            _relative(job_path, root),
        ]
        run = runner or subprocess.run
        try:
            completed = run(
                command,
                cwd=plan.output_root,
                check=False,
                capture_output=True,
                text=True,
                timeout=max(30, int(timeout_seconds)),
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise InactiveAnatomyAuthoringError(f"Blender worker did not complete: {exc}") from exc
        if completed.returncode != 0:
            raise InactiveAnatomyAuthoringError(
                f"Blender worker failed with exit code {completed.returncode}"
            )
        if anatomy_preflight.sha256_file(worker) != worker_sha:
            raise InactiveAnatomyAuthoringError("Blender worker changed during execution")
        if anatomy_preflight.sha256_file(blender) != blender_sha:
            raise InactiveAnatomyAuthoringError("Blender executable changed during execution")
        _verify_input_records(root, input_records)
        actual_entries = {item.name for item in anatomy_preflight._io_path(plan.output_root).iterdir()}
        if actual_entries != {JOB_NAME, ARTIFACT_NAME, WORKER_RESULT_NAME}:
            raise InactiveAnatomyAuthoringError("worker wrote unexpected output entries")
        result = _validated_worker_result(root, plan, result_path, artifact_path)

        manifest: dict[str, Any] = {
            "schema": MANIFEST_SCHEMA,
            "schema_version": 1,
            "status": AUTHORED_STATUS,
            "run_id": plan.run_id,
            "package_id": plan.job["package_id"],
            "candidate_id": plan.job["candidate_id"],
            "subject_id": plan.job["subject_id"],
            "preflight_receipt_sha256": plan.job["preflight_receipt_sha256"],
            "job": {
                "path": _relative(job_path, root),
                "bytes": anatomy_preflight._file_size(job_path),
                "sha256": anatomy_preflight.sha256_file(job_path),
                "receipt_sha256": plan.job["job_receipt_sha256"],
            },
            "worker": {
                "path": WORKER_SCRIPT.as_posix(),
                "sha256": worker_sha,
                "result_path": _relative(result_path, root),
                "result_bytes": anatomy_preflight._file_size(result_path),
                "result_sha256": anatomy_preflight.sha256_file(result_path),
                "result_receipt_sha256": result["worker_receipt_sha256"],
                "required_flags": ["--background", "--factory-startup", "--disable-autoexec"],
            },
            "artifact": dict(result["artifact"]),
            "module_collection": dict(result["module_collection"]),
            "imports": list(result["imports"]),
            "source_integrity": list(result["source_integrity"]),
            "separation": dict(result["separation"]),
            "truth": dict(result["truth"]),
            "review_state": {
                "geometry_review_passed": False,
                "owner_reviewed": False,
                "owner_approved": False,
            },
        }
        manifest_path = plan.output_root / MANIFEST_NAME
        _write_exclusive(manifest_path, manifest)
        receipt: dict[str, Any] = {
            "schema": RECEIPT_SCHEMA,
            "schema_version": 1,
            "status": AUTHORED_STATUS,
            "run_id": plan.run_id,
            "manifest": {
                "path": _relative(manifest_path, root),
                "bytes": anatomy_preflight._file_size(manifest_path),
                "sha256": anatomy_preflight.sha256_file(manifest_path),
            },
            "artifact": dict(result["artifact"]),
            "preflight_receipt_sha256": plan.job["preflight_receipt_sha256"],
            "job_receipt_sha256": plan.job["job_receipt_sha256"],
            "worker_receipt_sha256": result["worker_receipt_sha256"],
            "function_implemented": False,
            "runtime_activation_allowed": False,
            "public_export_allowed": False,
        }
        receipt["receipt_sha256"] = anatomy_preflight.canonical_sha256(receipt)
        receipt_path = plan.output_root / RECEIPT_NAME
        _write_exclusive(receipt_path, receipt)
        final_entries = {item.name for item in anatomy_preflight._io_path(plan.output_root).iterdir()}
        if final_entries != {
            JOB_NAME,
            ARTIFACT_NAME,
            WORKER_RESULT_NAME,
            MANIFEST_NAME,
            RECEIPT_NAME,
        }:
            raise InactiveAnatomyAuthoringError("final private output contains unexpected entries")
        return {
            "status": AUTHORED_STATUS,
            "output_root": _relative(plan.output_root, root),
            "manifest_path": _relative(manifest_path, root),
            "manifest_sha256": anatomy_preflight.sha256_file(manifest_path),
            "receipt_path": _relative(receipt_path, root),
            "receipt_sha256": receipt["receipt_sha256"],
            "artifact_path": result["artifact"]["path"],
            "artifact_sha256": result["artifact"]["sha256"],
            "function_implemented": False,
            "runtime_activation_allowed": False,
            "public_export_allowed": False,
        }
    except BaseException:
        if created and rollback_identity is not None:
            _quarantine_fresh_output_root(root, plan.output_root, rollback_identity)
        raise


__all__ = [
    "ARTIFACT_NAME",
    "AUTHORED_STATUS",
    "BpyInactiveAnatomySceneAdapter",
    "InactiveAnatomyAuthoringError",
    "JOB_NAME",
    "JOB_SCHEMA",
    "MANIFEST_SCHEMA",
    "MODULE_COLLECTION_NAME",
    "PRIVATE_OUTPUT_PREFIX",
    "RECEIPT_SCHEMA",
    "WORKER_RESULT_NAME",
    "WORKER_RESULT_SCHEMA",
    "execute_private_inactive_anatomy_authoring",
    "plan_private_inactive_anatomy_authoring",
    "run_blender_authoring_job",
]
