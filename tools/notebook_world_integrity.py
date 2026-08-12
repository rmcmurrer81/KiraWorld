"""Fail-closed verification for code-pinned notebook-world preview builds."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def read_json_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return data


def _project_file(root: Path, declared: object) -> tuple[str, Path]:
    relative = str(declared or "")
    posix = PurePosixPath(relative)
    if (
        not relative
        or "\\" in relative
        or posix.is_absolute()
        or any(part in {"", ".", ".."} for part in posix.parts)
        or ":" in posix.parts[0]
    ):
        raise ValueError(f"Manifest path is not a normalized project-relative path: {relative!r}")
    root = root.resolve()
    target = root.joinpath(*posix.parts).resolve()
    try:
        resolved_relative = target.relative_to(root).as_posix()
    except ValueError as exc:
        raise ValueError(f"Manifest path escapes the project root: {relative}") from exc
    if resolved_relative != relative:
        raise ValueError(
            f"Manifest path diverges after resolution: {relative!r} -> {resolved_relative!r}"
        )
    if not target.is_file():
        raise FileNotFoundError(f"Pinned notebook file is missing: {relative}")
    return relative, target


def _verify_file(root: Path, item: dict[str, Any], *, label: str) -> tuple[str, Path]:
    relative, target = _project_file(root, item.get("path"))
    expected_sha = str(item.get("sha256") or "").lower()
    if not _SHA256_RE.fullmatch(expected_sha):
        raise ValueError(f"{label} has an invalid SHA-256: {relative}")
    expected_bytes = item.get("bytes")
    if isinstance(expected_bytes, bool) or not isinstance(expected_bytes, int) or expected_bytes < 0:
        raise ValueError(f"{label} has an invalid byte count: {relative}")
    actual_bytes = target.stat().st_size
    if actual_bytes != expected_bytes:
        raise ValueError(
            f"{label} byte count changed: {relative} (expected {expected_bytes}, got {actual_bytes})"
        )
    actual_sha = sha256_file(target)
    if actual_sha != expected_sha:
        raise ValueError(
            f"{label} SHA-256 changed: {relative} (expected {expected_sha}, got {actual_sha})"
        )
    return relative, target


@dataclass(frozen=True)
class VerifiedNotebookBuild:
    world_id: str
    request_id: str
    build_id: str
    manifest_path: Path
    manifest_sha256: str
    registration_path: Path
    registration_sha256: str
    registration: dict[str, Any]
    entrypoint_relative_path: str
    served_urls: dict[str, Path]
    served_sha256: dict[str, str]
    served_bytes: dict[str, int]
    role_paths: dict[str, tuple[Path, ...]]
    index_anchor_sha256: str


def verify_code_pinned_build(
    *,
    root: Path,
    manifest_path: Path,
    expected_manifest_sha256: str,
    expected_world_id: str,
    expected_request_id: str,
    expected_registration_relative_path: str,
    required_roles: set[str],
) -> VerifiedNotebookBuild:
    """Verify the manifest, registration, index anchor, and every declared byte.

    The manifest digest is supplied by launcher code, not by another mutable data
    file.  All verification completes before the caller creates a listening socket.
    """

    root = root.resolve()
    manifest_path = manifest_path.resolve()
    try:
        manifest_path.relative_to(root)
    except ValueError as exc:
        raise ValueError("Pinned manifest is outside the project root") from exc
    expected_manifest_sha256 = expected_manifest_sha256.lower()
    if not _SHA256_RE.fullmatch(expected_manifest_sha256):
        raise ValueError("Launcher contains an invalid pinned manifest SHA-256")
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Pinned build manifest is missing: {manifest_path}")
    actual_manifest_sha = sha256_file(manifest_path)
    if actual_manifest_sha != expected_manifest_sha256:
        raise ValueError(
            "Pinned build manifest changed "
            f"(expected {expected_manifest_sha256}, got {actual_manifest_sha})"
        )

    manifest = read_json_object(manifest_path)
    if manifest.get("schema_version") != 1:
        raise ValueError("Unsupported pinned notebook build manifest schema")
    if manifest.get("manifest_kind") != "code_pinned_notebook_world_build":
        raise ValueError("Unexpected notebook build manifest kind")
    world_id = str(manifest.get("world_id") or "")
    request_id = str(manifest.get("request_id") or "")
    build_id = str(manifest.get("build_id") or "")
    if world_id != expected_world_id or request_id != expected_request_id or not build_id:
        raise ValueError("Pinned notebook build identity does not match launcher code")

    registration_spec = manifest.get("registration")
    if not isinstance(registration_spec, dict):
        raise ValueError("Pinned notebook manifest has no registration binding")
    registration_relative, registration_path = _verify_file(
        root,
        registration_spec,
        label="Notebook registration",
    )
    if registration_relative != expected_registration_relative_path:
        raise ValueError(
            "Notebook registration path diverges from launcher code: "
            f"{registration_relative!r} != {expected_registration_relative_path!r}"
        )
    registration_sha = str(registration_spec["sha256"]).lower()
    registration = read_json_object(registration_path)
    if str(registration.get("request_id") or "") != request_id:
        raise ValueError("Pinned registration request_id does not match the manifest")

    raw_files = manifest.get("files")
    if not isinstance(raw_files, list) or not raw_files:
        raise ValueError("Pinned notebook manifest has no file bindings")
    served_urls: dict[str, Path] = {}
    served_sha256: dict[str, str] = {}
    served_bytes: dict[str, int] = {}
    role_paths_mutable: dict[str, list[Path]] = {}
    paths_seen: set[str] = set()
    registration_bound = False
    for index, raw_item in enumerate(raw_files):
        if not isinstance(raw_item, dict):
            raise ValueError(f"Pinned file entry {index} is not an object")
        role = str(raw_item.get("role") or "")
        if not role:
            raise ValueError(f"Pinned file entry {index} has no role")
        relative, target = _verify_file(root, raw_item, label=f"Pinned {role}")
        if relative in paths_seen:
            raise ValueError(f"Pinned file path is declared more than once: {relative}")
        paths_seen.add(relative)
        role_paths_mutable.setdefault(role, []).append(target)
        if relative == registration_relative:
            if (
                str(raw_item.get("sha256") or "").lower() != registration_sha
                or raw_item.get("bytes") != registration_spec.get("bytes")
            ):
                raise ValueError("Registration binding disagrees with its pinned file entry")
            registration_bound = True
        url_value = raw_item.get("url")
        if url_value is None:
            continue
        url = str(url_value)
        if not url.startswith("/") or "?" in url or "#" in url or "\\" in url:
            raise ValueError(f"Pinned served URL is invalid: {url!r}")
        if url in served_urls:
            raise ValueError(f"Pinned served URL is declared more than once: {url}")
        served_urls[url] = target
        served_sha256[url] = str(raw_item["sha256"]).lower()
        served_bytes[url] = int(raw_item["bytes"])

    if not registration_bound:
        raise ValueError("Registration is not included in the full pinned file set")
    missing_roles = required_roles.difference(role_paths_mutable)
    if missing_roles:
        raise ValueError(f"Pinned notebook manifest is missing roles: {sorted(missing_roles)}")

    entrypoint = manifest.get("entrypoint")
    if not isinstance(entrypoint, dict):
        raise ValueError("Pinned notebook manifest has no entrypoint binding")
    entry_url = str(entrypoint.get("url") or "")
    entry_relative = str(entrypoint.get("path") or "")
    if entry_url != "/index.html" or served_urls.get(entry_url) is None:
        raise ValueError("Pinned notebook entrypoint must be served at /index.html")
    entry_path = served_urls[entry_url]
    if entry_path.relative_to(root).as_posix() != entry_relative:
        raise ValueError("Entrypoint path disagrees with its served file binding")
    entry_items = [
        item
        for item in raw_files
        if isinstance(item, dict) and item.get("path") == entry_relative
    ]
    if len(entry_items) != 1 or any(
        entrypoint.get(key) != entry_items[0].get(key) for key in ("sha256", "bytes")
    ):
        raise ValueError("Entrypoint binding disagrees with its pinned file entry")

    index_binding = manifest.get("index_registration")
    if not isinstance(index_binding, dict):
        raise ValueError("Pinned notebook manifest has no notebook-index binding")
    index_relative, index_path = _project_file(root, index_binding.get("path"))
    if index_relative != "Data/world_builds/notebook_world_index.json":
        raise ValueError("Notebook index path diverges from the required project index")
    index_data = read_json_object(index_path)
    worlds = index_data.get("notebook_worlds")
    if not isinstance(worlds, dict):
        raise ValueError("Notebook index has no notebook_worlds object")
    matches: list[tuple[str, dict[str, Any]]] = []
    for candidate_world_id, world in worlds.items():
        if not isinstance(world, dict):
            continue
        anchors = world.get("anchors")
        if not isinstance(anchors, list):
            continue
        for anchor in anchors:
            if isinstance(anchor, dict) and anchor.get("request_id") == request_id:
                matches.append((str(candidate_world_id), anchor))
    if len(matches) != 1 or matches[0][0] != world_id:
        raise ValueError("Pinned request is missing, duplicated, or registered in another notebook world")
    anchor = matches[0][1]
    expected_scene_folder = str(index_binding.get("scene_folder") or "")
    if anchor.get("scene_folder") != expected_scene_folder:
        raise ValueError("Notebook index scene_folder diverges from the pinned build")
    expected_anchor_sha = str(index_binding.get("anchor_sha256") or "").lower()
    if not _SHA256_RE.fullmatch(expected_anchor_sha):
        raise ValueError("Notebook index anchor binding has an invalid SHA-256")
    actual_anchor_sha = canonical_json_sha256(anchor)
    if actual_anchor_sha != expected_anchor_sha:
        raise ValueError(
            "Notebook index registration changed "
            f"(expected {expected_anchor_sha}, got {actual_anchor_sha})"
        )

    served_urls["/"] = entry_path
    served_sha256["/"] = served_sha256["/index.html"]
    served_bytes["/"] = served_bytes["/index.html"]
    return VerifiedNotebookBuild(
        world_id=world_id,
        request_id=request_id,
        build_id=build_id,
        manifest_path=manifest_path,
        manifest_sha256=actual_manifest_sha,
        registration_path=registration_path,
        registration_sha256=registration_sha,
        registration=registration,
        entrypoint_relative_path=entry_relative,
        served_urls=served_urls,
        served_sha256=served_sha256,
        served_bytes=served_bytes,
        role_paths={key: tuple(value) for key, value in role_paths_mutable.items()},
        index_anchor_sha256=actual_anchor_sha,
    )
