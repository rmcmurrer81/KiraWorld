from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from Core.shared_person_growth_capabilities_v3 import ProtectedGrowthController
from Core.shared_person_growth_v3_integration_candidate_v1 import (
    SharedGrowthV3IntegrationAdapter,
)
from Testing.test_shared_person_growth_v3_integration_candidate_v1 import (
    SharedGrowthV3IntegrationCandidateTests,
)

SEAL_PATH = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260811"
    / "shared_person_growth_v3_integration_candidate_static_preparation"
    / "attempt_01"
    / "SEALED_MANIFEST.json"
)
INVENTORY_REL = Path(
    "Data/foundation/shared_person_growth_v3_integration_candidate_v1.json"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sealed_rows() -> list[dict[str, object]]:
    seal = json.loads(SEAL_PATH.read_text(encoding="utf-8"))
    rows: list[dict[str, object]] = []
    for section in (
        "candidate_subjects",
        "protected_growth_v3",
        "protected_current_runtime",
    ):
        rows.extend(seal[section])
    rows.append(seal["author_evidence"])
    return rows


def verify_seal() -> dict[str, object]:
    mismatches: list[str] = []
    for row in sealed_rows():
        path = ROOT / str(row["path"])
        if not path.is_file() or sha256(path) != row["sha256"]:
            mismatches.append(str(row["path"]))
            continue
        if "bytes" in row and path.stat().st_size != row["bytes"]:
            mismatches.append(str(row["path"]))
    return {
        "checked": len(sealed_rows()),
        "mismatches": sorted(set(mismatches)),
    }


def copy_inventory_closure(clone_root: Path) -> dict[str, object]:
    inventory = json.loads((ROOT / INVENTORY_REL).read_text(encoding="utf-8"))
    paths = {INVENTORY_REL.as_posix()}
    growth = inventory["growth_v3_binding"]
    paths.update(
        str(growth[key])
        for key in (
            "policy_path",
            "core_path",
            "creator_path",
            "fresh_audit_checkpoint_path",
        )
    )
    paths.update(item["path"] for item in inventory["discovery_sources"])
    paths.update(
        item["path"]
        for item in inventory["maturity_sources"]
        if item["path"] is not None
    )
    paths.update(item["source_path"] for item in inventory["routes"])
    for relative in sorted(paths):
        source = ROOT / relative
        target = clone_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    return inventory


def probe_same_process_capability_exposure() -> dict[str, object]:
    fixture = SharedGrowthV3IntegrationCandidateTests(methodName="test_01_v3_and_acceptance_bytes_are_preserved")
    fixture.setUp()
    try:
        profile = fixture.build_profile("kira", profile_id="growth_profile:hostile_introspection")
        adapter = fixture.adapter
        leaked_secret = getattr(
            adapter,
            "_SharedGrowthV3IntegrationAdapter__secret",
        )
        leaked_controller = getattr(
            adapter,
            "_SharedGrowthV3IntegrationAdapter__authority_controller",
        )
        leaked_controller_identity = getattr(
            adapter,
            "_SharedGrowthV3IntegrationAdapter__authority_identity",
        )
        identity = adapter.identity
        receipt = adapter.issue_existing_person_migration(
            identity=identity,
            secret=leaked_secret,
            operation_id="hostile_introspection:issue",
            route_id="permanent:kira",
            profile=profile,
        )
        output = adapter.stage_receipt(
            identity=identity,
            secret=leaked_secret,
            receipt=receipt,
            operation_id="hostile_introspection:stage",
        )
        return {
            "unexpected_acceptance": output.is_file(),
            "public_identity_retrieved": identity is adapter.identity,
            "private_secret_retrieved": leaked_secret == fixture.integration_secret,
            "private_controller_retrieved": leaked_controller is fixture.controller,
            "private_controller_identity_retrieved": (
                leaked_controller_identity is fixture.controller.identity
            ),
            "staged_filename": output.name,
        }
    finally:
        fixture.tearDown()


def probe_post_construction_route_source_drift() -> dict[str, object]:
    fixture = SharedGrowthV3IntegrationCandidateTests(methodName="test_01_v3_and_acceptance_bytes_are_preserved")
    fixture.setUp()
    try:
        profile = fixture.build_profile("kira", profile_id="growth_profile:hostile_toctou")
        with tempfile.TemporaryDirectory() as clone_name:
            clone_root = Path(clone_name) / "project"
            copy_inventory_closure(clone_root)
            adapter = SharedGrowthV3IntegrationAdapter(
                authority_controller=fixture.controller,
                authority_identity=fixture.controller.identity,
                integration_secret=fixture.integration_secret,
                ledger_root=Path(clone_name) / "ledger",
                staging_root=Path(clone_name) / "staging",
                inventory_path=clone_root / INVENTORY_REL,
                project_root=clone_root,
            )
            route_source = clone_root / "tools/kira_world_shell_server.py"
            before = sha256(route_source)
            route_source.write_bytes(
                route_source.read_bytes()
                + b"\n# hostile post-construction route-source drift\n"
            )
            after = sha256(route_source)
            receipt = adapter.issue_existing_person_migration(
                identity=adapter.identity,
                secret=fixture.integration_secret,
                operation_id="hostile_toctou:issue",
                route_id="permanent:kira",
                profile=profile,
            )
            output = adapter.stage_receipt(
                identity=adapter.identity,
                secret=fixture.integration_secret,
                receipt=receipt,
                operation_id="hostile_toctou:stage",
            )
            return {
                "unexpected_acceptance": output.is_file(),
                "route_source_changed_after_adapter_init": before != after,
                "sealed_expected_sha256": before,
                "mutated_observed_sha256": after,
                "staged_filename": output.name,
            }
    finally:
        fixture.tearDown()


def main() -> int:
    before = verify_seal()
    introspection = probe_same_process_capability_exposure()
    toctou = probe_post_construction_route_source_drift()
    after = verify_seal()
    blockers = []
    if introspection["unexpected_acceptance"]:
        blockers.append("BLOCK_SAME_PROCESS_ADAPTER_CAPABILITY_EXPOSURE")
    if toctou["unexpected_acceptance"]:
        blockers.append("BLOCK_ROUTE_SOURCE_TOCTOU_AFTER_ADAPTER_INIT")
    result = {
        "schema": "kira.shared_person_growth_v3_integration_independent_hostile_result.v1",
        "decision": "REJECT_STATIC_INTEGRATION_CANDIDATE_NO_PROMOTION",
        "blockers": blockers,
        "seal_before": before,
        "seal_after": after,
        "probes": {
            "same_process_capability_exposure": introspection,
            "post_construction_route_source_drift": toctou,
        },
        "pass_means_blocker_reproduced": len(blockers) == 2,
        "live_or_production_action_performed": False,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if len(blockers) == 2 and not before["mismatches"] and not after["mismatches"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
