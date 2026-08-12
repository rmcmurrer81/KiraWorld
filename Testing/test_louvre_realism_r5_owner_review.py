from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREVIEW = (
    ROOT
    / "Data"
    / "world_builds"
    / "notebook_worlds"
    / "paris_notebook_world"
    / "builds"
    / "notebook_world_louvre_realism_r5_20260716_190000"
    / "preview"
)
MANIFEST = json.loads((PREVIEW / "louvre_realism_r5_pinned_manifest.json").read_text(encoding="utf-8"))
CONTRACT = json.loads((PREVIEW / "louvre_realism_r5_contract.json").read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _check_hash_pinned_server_accepts_exact_r5_build() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "serve_louvre_realism_r5_owner_review.py"), "--verify-only"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "solo, zero people, no interior" in result.stdout


def _check_manifest_is_separate_bounded_zero_person_review() -> None:
    assert MANIFEST["build_id"] == "louvre_realism_owner_review_20260716_r5"
    assert MANIFEST["launch_url"].startswith("http://127.0.0.1:5195/")
    assert "5183" not in MANIFEST["launch_url"]
    assert MANIFEST["status"] == "bounded_owner_review_not_complete_not_approved"
    isolation = MANIFEST["runtime_isolation"]
    assert isolation["solo_review_only"] is True
    assert isolation["people_loaded"] == 0
    assert isolation["minds_loaded"] == 0
    assert isolation["bounded_realism_owner_review_enabled"] is True
    assert isolation["supplied_site_context_enabled"] is True
    assert isolation["supplied_pavillon_sully_facade_enabled"] is True
    for key in (
        "temporary_ai_activation_allowed",
        "person_systems_loaded",
        "mind_systems_loaded",
        "voice_systems_loaded",
        "home_world_loaded",
        "home_world_mutation_allowed",
        "bounded_approximate_circulation_enabled",
        "full_louvre_interior_enabled",
        "working_door_enabled",
        "working_stairs_enabled",
        "working_elevator_enabled",
        "working_escalator_enabled",
        "gallery_inventory_enabled",
        "artwork_inventory_enabled",
    ):
        assert isolation[key] is False, key


def _check_licenses_provenance_and_adaptations_are_explicit() -> None:
    assets = {item["source_filename"]: item for item in CONTRACT["supplied_asset_provenance"]}
    wide = assets["THE_LOUVRE.usdz"]
    facade = assets["Pavillon_Sully_Louvre_Museum_-_Photogrammetry.usdz"]
    assert wide["license"] == "Sketchfab Standard License"
    assert wide["author"] == "PeeJaa"
    assert wide["private_source_directory_redacted"] is True
    assert wide["derived_triangles"] == 951353
    assert wide["context_cutout_radius_m"] == 96.6
    assert facade["license"] == "CC BY-NC-SA 4.0"
    assert facade["author"] == "Nicolas Diolez"
    assert "private local noncommercial" in facade["usage_scope"]
    assert facade["derived_triangles"] == 599959
    assert facade["alignment_exact"] is False
    assert "C:\\Users" not in json.dumps(CONTRACT)


def _check_served_files_are_exact_and_contain_only_review_assets() -> None:
    actual = {path.resolve() for path in (PREVIEW / "dist").rglob("*") if path.is_file()}
    pinned = set()
    roles = set()
    for item in MANIFEST["served_files"]:
        path = (ROOT / item["path"]).resolve()
        pinned.add(path)
        roles.add(item["role"])
        assert path.stat().st_size == item["bytes"]
        assert sha256(path) == item["sha256"]
    assert actual == pinned
    assert roles == {"entrypoint", "style", "bundle", "pavillon_sully_facade_glb", "wide_site_context_glb"}
    assert not any("actor" in path.name.lower() or "avatar" in path.name.lower() for path in actual)


def _check_conversion_audits_match_contract_and_remain_visual_only() -> None:
    wide = json.loads((ROOT / "Data" / "codex_reports" / "louvre_r5_asset_audit" / "the_louvre_context_cutout96m_source_mesh.json").read_text(encoding="utf-8"))
    facade = json.loads((ROOT / "Data" / "codex_reports" / "louvre_r5_asset_audit" / "pavillon_sully_lod600k.json").read_text(encoding="utf-8"))
    assert wide["source"]["sha256"] == "b8238fd76e5f801a346804f9a687098868ae4577d298b6b6e34478d229f8dc9d"
    assert wide["cutout"]["radius"] == 4.6
    assert wide["post_optimization"]["triangles"] == 951353
    assert wide["export"]["sha256"] == "1a1e69277cbe968e3155d4adf9304a2a51e0be581d949b2184fed2850cb87ecb"
    assert facade["source"]["sha256"] == "5811c62692472418e02a9aa0d6fe2af544a127d486ed492377f60dec378c9e35"
    assert facade["post_optimization"]["triangles"] == 599959
    assert facade["export"]["sha256"] == "9015233de2e77a24aea77ad342589c8b78eeff0f3c4021cc890ee22af9ef2d68"
    for audit in (wide, facade):
        assert audit["truth"]["visual_reference_asset_only"] is True
        assert audit["truth"]["exact_scan_claim_allowed"] is False
        assert audit["truth"]["working_doors_or_vertical_transport_proven"] is False


def _check_browser_smoke_evidence_stays_under_review_ceiling() -> None:
    report_path = ROOT / "Data" / "codex_reports" / "20260716_louvre_realism_r5_browser_smoke_final.json"
    if not report_path.exists():
        return
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "passed"
    diagnostics = report["state"]["diagnostics"]
    assert diagnostics["contextCell"]["state"] == "loaded"
    assert diagnostics["facadeCell"]["state"] == "loaded"
    assert diagnostics["isolation"]["activePeople"] == 0
    assert diagnostics["render"]["triangles"] <= CONTRACT["resource_ceiling"]["measured_render_triangle_ceiling"]
    assert diagnostics["render"]["calls"] <= CONTRACT["resource_ceiling"]["measured_draw_call_ceiling"]
    assert diagnostics["render"]["frameP95Milliseconds"] <= CONTRACT["resource_ceiling"]["frame_p95_ceiling_ms"]
    assert report["state"]["ui"]["loadStatus"].startswith("Real-model site and eye-level Pavillon Sully context loaded")
    assert not report["diagnostics"]["pageErrors"]
    assert not report["diagnostics"]["consoleErrors"]


class TestLouvreRealismR5OwnerReview(unittest.TestCase):
    """Standard-library discoverable wrappers around the six R5 checks."""

    def test_hash_pinned_server_accepts_exact_r5_build(self) -> None:
        _check_hash_pinned_server_accepts_exact_r5_build()

    def test_manifest_is_separate_bounded_zero_person_review(self) -> None:
        _check_manifest_is_separate_bounded_zero_person_review()

    def test_licenses_provenance_and_adaptations_are_explicit(self) -> None:
        _check_licenses_provenance_and_adaptations_are_explicit()

    def test_served_files_are_exact_and_contain_only_review_assets(self) -> None:
        _check_served_files_are_exact_and_contain_only_review_assets()

    def test_conversion_audits_match_contract_and_remain_visual_only(self) -> None:
        _check_conversion_audits_match_contract_and_remain_visual_only()

    def test_browser_smoke_evidence_stays_under_review_ceiling(self) -> None:
        _check_browser_smoke_evidence_stays_under_review_ceiling()


if __name__ == "__main__":
    unittest.main()
