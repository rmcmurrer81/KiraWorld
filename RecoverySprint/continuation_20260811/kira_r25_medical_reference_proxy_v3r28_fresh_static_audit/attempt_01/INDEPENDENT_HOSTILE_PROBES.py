from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import types


STAGE1 = Path(
    r"C:\Users\robmc\Kira\RecoverySprint\continuation_20260811"
    r"\kira_r25_medical_reference_proxy_v3r28_static_preparation\attempt_01"
)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def load_materializer() -> types.ModuleType:
    path = STAGE1 / "materialize_stage2_v3r28.py"
    module = types.ModuleType("v3r28_materializer_independent_static_probe")
    module.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), "exec"), module.__dict__)
    return module


def audit_snapshot(module: types.ModuleType, decision: dict[str, object]) -> dict[str, bytes]:
    decision_raw = (
        json.dumps(decision, sort_keys=True, separators=(",", ":"), allow_nan=False)
        + "\n"
    ).encode("utf-8")
    independent = (
        "row_id\tstatus\tevidence_sha256\tfinding\n"
        + "".join(
            f"{row_id}\tPASS\t{'2' * 64}\tindependent_static_probe\n"
            for row_id in module.AUDIT_ROW_IDS
        )
    ).encode("utf-8")
    checkpoint = b"# Independent static probe checkpoint\n"
    artifacts = {
        "AUDIT_DECISION.json": decision_raw,
        "CHECKPOINT.md": checkpoint,
        "INDEPENDENT_AUDIT.tsv": independent,
    }
    manifest = (
        "path\tbytes\tsha256\n"
        + "".join(
            f"{name}\t{len(raw)}\t{digest(raw)}\n"
            for name, raw in sorted(artifacts.items())
        )
    ).encode("utf-8")
    return {"AUDIT_ARTIFACT_MANIFEST.tsv": manifest, **artifacts}


def main() -> int:
    module = load_materializer()
    installed = module.directory_snapshot(STAGE1)
    seal = json.loads(installed["STATIC_SEAL_MANIFEST.json"])
    stage1_root = str(seal["package_root_sha256"])

    # The externally supplied package root covers only the 18 subjects, not
    # STATIC_SEAL_MANIFEST.json itself.  Demonstrate that authority-bearing seal
    # fields can drift while parse_stage1 still accepts the same external root.
    mutated_seal = copy.deepcopy(seal)
    mutated_seal["audit_a_maximum_authority"] = "RUN_BLENDER"
    mutated_seal["audit_b_required"] = False
    mutated_seal["maximum_future_blender_invocations_after_both_acceptances"] = 999
    mutated_snapshot = dict(installed)
    mutated_snapshot["STATIC_SEAL_MANIFEST.json"] = (
        json.dumps(mutated_seal, indent=2) + "\n"
    ).encode("utf-8")
    module.parse_stage1(mutated_snapshot, stage1_root)

    # Python bool/int equality lets a non-exactly-typed audit decision pass the
    # materializer's whole-dict equality check.
    auditor = "independent_v3r28_audit_a_probe"
    typed_mutant = {
        "schema": "kira.r25.medical_reference_proxy.v3r28.audit_a_decision.v1",
        "status": "ACCEPT_STAGE1_FOR_STAGE2_MATERIALIZATION_ONLY_NO_BLENDER_AUTHORITY",
        "auditor_id": auditor,
        "accepted_stage1_package_root": stage1_root,
        "execution_authority": "MATERIALIZE_STAGE2_ONLY_NO_BLENDER",
        "candidate_executed": 0,
        "blender_invoked": 0,
        "maximum_materializations": True,
        "stage2_requires_different_audit_b": 1,
        "audit_scope": "CACHE_FREE_STATIC_SYNTAX_MOCKED_HOSTILE_ONLY",
    }
    snapshot = audit_snapshot(module, typed_mutant)
    manifest_sha = digest(snapshot["AUDIT_ARTIFACT_MANIFEST.tsv"])
    module.parse_audit(snapshot, manifest_sha, stage1_root, auditor)

    native = (STAGE1 / "post_audit_native_anchor_template_v3r28.c").read_text(
        encoding="utf-8"
    )
    close_outputs = native.index(
        "for (index = 0U; index < 7U; ++index) if (handles[index] != INVALID_HANDLE_VALUE) CloseHandle(handles[index]);"
    )
    finalize_return = native.index("return ok;", close_outputs)
    finalize_call = native.index("if (!finalize_outputs(capability_sha, manifest_sha))")
    success_ledger = native.index(
        "ledger_update(ledger, LEDGER_SUCCESS_CONSUMED", finalize_call
    )
    assert close_outputs < finalize_return < finalize_call < success_ledger

    # Stage-2 materialization has only a deletable destination-presence guard;
    # no durable, separately retained materialization-consumption record exists.
    materializer_source = (STAGE1 / "materialize_stage2_v3r28.py").read_text(
        encoding="utf-8"
    )
    assert "output_absolute.exists()" in materializer_source
    assert "maximum_materializations" in materializer_source
    assert "CREATE_NEW" not in materializer_source
    assert "consumed" not in materializer_source.lower()

    result = {
        "schema": "kira.r25.medical_reference_proxy.v3r28.independent_audit_a_hostile_probe.v1",
        "candidate_invoked": False,
        "blender_invoked": False,
        "materializer_main_invoked": False,
        "stage1_external_root_does_not_bind_seal_bytes": True,
        "authority_bearing_seal_mutant_accepted_by_parse_stage1": True,
        "wrong_exact_json_types_accepted_by_parse_audit": True,
        "final_output_and_manifest_handles_close_before_success_ledger": True,
        "durable_materialization_consumption_record_present": False,
        "verdict": "REJECT_AUDIT_A_NO_STAGE2_MATERIALIZATION_OR_BUILD_AUTHORITY",
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
