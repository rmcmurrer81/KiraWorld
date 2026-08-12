#!/usr/bin/env python3
"""Validate and hash-pin the isolated Louvre corrected R7 owner review."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from Core.world_reference_evidence import validate_reference_evidence_contract  # noqa: E402


BUILD_ID = "notebook_world_louvre_corrected_r7_20260716_235000"
PREVIEW = (
    ROOT
    / "Data"
    / "world_builds"
    / "notebook_worlds"
    / "paris_notebook_world"
    / "builds"
    / BUILD_ID
    / "preview"
)
DIST = PREVIEW / "dist"
CONTRACT_PATH = PREVIEW / "louvre_corrected_r7_contract.json"
EVIDENCE_PATH = PREVIEW / "louvre_reference_evidence_r7.json"
MANIFEST_PATH = PREVIEW / "louvre_corrected_r7_pinned_manifest.json"
SOURCE_INPUTS = (
    PREVIEW / "index.html",
    PREVIEW / "src" / "main.js",
    PREVIEW / "src" / "style.css",
    PREVIEW / "vite.config.js",
    PREVIEW / "README.md",
    CONTRACT_PATH,
    EVIDENCE_PATH,
    ROOT / "Core" / "world_reference_evidence.py",
    ROOT
    / "Data"
    / "world_builds"
    / "notebook_worlds"
    / "paris_notebook_world"
    / "builds"
    / "notebook_world_louvre_courtyard_20260628_210935"
    / "sources"
    / "robert_supplied_images"
    / "IM-Pei-designed-pyramid-Louvre-Paris-France.webp",
    ROOT
    / "Data"
    / "world_builds"
    / "notebook_worlds"
    / "paris_notebook_world"
    / "builds"
    / "notebook_world_louvre_courtyard_20260628_210935"
    / "sources"
    / "robert_supplied_images"
    / "d672e10204e3f70ceb3a9d080d421e93.jpg",
    ROOT
    / "Data"
    / "world_builds"
    / "notebook_worlds"
    / "paris_notebook_world"
    / "builds"
    / "notebook_world_louvre_courtyard_20260628_210935"
    / "sources"
    / "robert_supplied_images"
    / "e6a59f09a26358fcb1a65b56644c51b7.jpg",
    ROOT
    / "Data"
    / "world_builds"
    / "notebook_worlds"
    / "paris_notebook_world"
    / "builds"
    / "notebook_world_louvre_courtyard_20260628_210935"
    / "sources"
    / "robert_supplied_images"
    / "Louvre-Museum---Rost-Architects.webp",
)


class R7PackageError(RuntimeError):
    """Raised if the review does not satisfy its fixed truth contract."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def record(path: Path, **extra: Any) -> dict[str, Any]:
    if not path.is_file():
        raise R7PackageError(f"Required file is missing: {path}")
    result: dict[str, Any] = {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }
    result.update(extra)
    return result


def require_contract(contract: dict[str, Any], evidence: dict[str, Any]) -> None:
    if contract.get("build_id") != BUILD_ID:
        raise R7PackageError("Unexpected build ID")
    if contract.get("contract_kind") != "louvre_corrected_bounded_owner_review":
        raise R7PackageError("Unexpected contract kind")
    if contract.get("status") != "corrected_spatial_blockout_not_realism_not_approved":
        raise R7PackageError("R7 must remain an unapproved corrected spatial blockout")
    rejection = contract.get("owner_rejection") or {}
    if rejection.get("r5_r6_wide_scan_rejected") is not True:
        raise R7PackageError("R5/R6 owner rejection is missing")
    if rejection.get("r7_imports_r5_r6_scan_assets") is not False:
        raise R7PackageError("Rejected R5/R6 scan content cannot enter R7")
    isolation = contract.get("runtime_isolation") or {}
    if isolation.get("solo_review_only") is not True:
        raise R7PackageError("R7 is not marked solo-review only")
    if int(isolation.get("people_loaded", -1)) != 0 or int(isolation.get("minds_loaded", -1)) != 0:
        raise R7PackageError("R7 binds a person or mind")
    for flag in (
        "temporary_ai_activation_allowed",
        "person_systems_loaded",
        "mind_systems_loaded",
        "voice_systems_loaded",
        "ollama_loaded",
        "home_world_loaded",
        "home_world_mutation_allowed",
        "tardis_loaded",
        "tardis_mutation_allowed",
        "runtime_registered",
        "full_louvre_interior_enabled",
        "working_doors_enabled",
        "working_elevator_enabled",
        "working_escalator_enabled",
        "gallery_inventory_enabled",
        "artwork_inventory_enabled",
        "r4_port_5183_mutation_allowed",
        "r5_port_5195_mutation_allowed",
        "r6_port_5196_mutation_allowed",
    ):
        if isolation.get(flag) is not False:
            raise R7PackageError(f"Isolation flag must remain false: {flag}")
    anchors = contract.get("spatial_anchors") or {}
    main = anchors.get("main_pyramid") or {}
    small = anchors.get("smaller_pyramidions") or {}
    if (main.get("base_width_m"), main.get("height_m")) != (35, 21):
        raise R7PackageError("Main Pyramid is not pinned to the official 35 m x 21 m scale")
    if small.get("count") != 3 or set((small.get("centers_m") or {})) != {"north", "east", "south"}:
        raise R7PackageError("R7 must contain the three north/east/south smaller pyramidions")
    invariants = contract.get("object_invariants") or {}
    expected = {
        "main_pyramid_count": 1,
        "smaller_pyramidion_count": 3,
        "palace_wing_groups": 3,
        "hall_stair_tread_count": 56,
        "physical_open_portals": 0,
        "locked_portals": 4,
        "people": 0,
        "minds": 0,
        "voices": 0,
        "artworks": 0,
    }
    for name, value in expected.items():
        if invariants.get(name) != value:
            raise R7PackageError(f"Object invariant differs: {name}")
    decisions = validate_reference_evidence_contract(evidence)
    by_id = {item.area_id: item for item in decisions}
    if not by_id["cour_napoleon_bounded_exterior"].evidence_sufficient_for_draft:
        raise R7PackageError("Cour Napoleon evidence gate did not pass")
    if not by_id["under_pyramid_hall_napoleon_stair_study"].evidence_sufficient_for_draft:
        raise R7PackageError("Hall Napoleon visual-draft evidence gate did not pass")
    for area_id in ("richelieu_gallery_cells", "sully_gallery_cells", "denon_gallery_cells"):
        if by_id[area_id].evidence_sufficient_for_draft:
            raise R7PackageError(f"Unsupported gallery unexpectedly passed: {area_id}")
    if any(
        item.get("runtime_state") != "closed_locked_solid"
        or item.get("collision_solid") is not True
        or item.get("opens") is not False
        for item in evidence.get("portals") or []
    ):
        raise R7PackageError("Every R7 portal must remain closed, locked, and solid")


def main() -> int:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    require_contract(contract, evidence)
    if not DIST.is_dir():
        raise R7PackageError("Run the Vite production build before packaging")
    source_records = [record(path, role="reference_or_build_input") for path in SOURCE_INPUTS]
    served_records: list[dict[str, Any]] = []
    for path in sorted(item for item in DIST.rglob("*") if item.is_file()):
        rel = path.relative_to(DIST).as_posix()
        role = "entrypoint" if rel == "index.html" else "style" if path.suffix == ".css" else "bundle"
        served_records.append(record(path, url=f"/{rel}", role=role))
    manifest = {
        "manifest_kind": "louvre_corrected_r7_pinned_owner_review",
        "schema_version": 1,
        "build_id": BUILD_ID,
        "status": contract["status"],
        "launch_url": "http://127.0.0.1:5197/?solo=1&bookmark=west_arrival",
        "runtime_isolation": contract["runtime_isolation"],
        "owner_rejection": contract["owner_rejection"],
        "spatial_anchors": contract["spatial_anchors"],
        "object_invariants": contract["object_invariants"],
        "review_bookmarks": contract["review_bookmarks"],
        "evidence_decisions": [item.as_dict() for item in validate_reference_evidence_contract(evidence)],
        "owner_review_routing": {
            "registered_in_world_shell_or_tardis": True,
            "integration_kind": "separate_world_shell_owner_review_button",
            "production_destination_replaced": False,
            "transports_person": False,
            "activates_person": False,
            "mutates_shell_location": False,
            "reason": "The explicit Louvre Corrected R7 Review button opens the pinned zero-person service in a separate window while leaving the active person, shell location, old audit route, and approval status unchanged.",
            "launcher": "Start_Louvre_Corrected_R7_Owner_Review.bat",
        },
        "source_inputs": source_records,
        "served_files": served_records,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        f"Pinned {BUILD_ID}: {len(source_records)} inputs, {len(served_records)} served files, "
        "main + 3 smaller pyramids, 4 locked portals, people=0."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
