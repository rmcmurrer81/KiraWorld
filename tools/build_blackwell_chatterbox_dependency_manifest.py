#!/usr/bin/env python3
"""Seal the isolated Blackwell Chatterbox environment without copying its venv."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SIDECAR = ROOT / "Voice" / "sidecars" / "chatterbox_blackwell_gpu"
PYTHON = SIDECAR / ".venv" / "Scripts" / "python.exe"
EVIDENCE = SIDECAR / "evidence"
PROFILE = ROOT / "Voice" / "profiles" / "temp_ai" / "kira_voice_profile.json"
REFERENCE = (
    ROOT
    / "Voice"
    / "reference_packs"
    / "kira"
    / "kira_online_source_20260706_221447"
    / "model_input"
    / "approved_reference.wav"
)
INSTALL_REPORTS = (
    EVIDENCE / "torch_install_report.raw.json",
    EVIDENCE / "dependency_install_report.raw.json",
    EVIDENCE / "chatterbox_install_report.raw.json",
)
SUPPORTING_EVIDENCE = (
    EVIDENCE / "preinstall_system_snapshot.json",
    EVIDENCE / "dependency_resolution_dry_run.json",
    EVIDENCE / "torch_gpu_readiness.json",
    EVIDENCE / "torch_gpu_readiness_postdeps.json",
)
EXPECTED_PIN_CONFLICT_PACKAGES = {"torch", "torchaudio"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalized_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value.strip().casefold())


def run(*args: str, allow_failure: bool = False) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        [str(PYTHON), *args],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        timeout=180,
        check=False,
    )
    if completed.returncode != 0 and not allow_failure:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip())
    return completed


def report_record(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "pip_version": data.get("pip_version"),
        "python_full_version": (data.get("environment") or {}).get("python_full_version"),
        "install_record_count": len(data.get("install") or []),
    }


def current_cpu_sidecar_snapshot() -> dict[str, Any]:
    from tools.build_blackwell_chatterbox_preflight import cpu_sidecar_snapshot

    return cpu_sidecar_snapshot()


def main() -> int:
    if not PYTHON.is_file():
        raise FileNotFoundError(PYTHON)
    for path in (*INSTALL_REPORTS, *SUPPORTING_EVIDENCE, PROFILE, REFERENCE):
        if not path.is_file():
            raise FileNotFoundError(path)

    preinstall = json.loads(SUPPORTING_EVIDENCE[0].read_text(encoding="utf-8"))
    cpu_after = current_cpu_sidecar_snapshot()
    cpu_before = preinstall["cpu_sidecar"]
    cpu_unchanged = {
        "non_venv_manifest_sha256": (
            cpu_after["non_venv_manifest_sha256"] == cpu_before["non_venv_manifest_sha256"]
        ),
        "pip_freeze_sha256": cpu_after["pip_freeze_sha256"] == cpu_before["pip_freeze_sha256"],
        "ready": (cpu_after.get("self_check") or {}).get("ready") is True,
    }
    if not all(cpu_unchanged.values()):
        raise RuntimeError(f"accepted CPU sidecar changed or is not runnable: {cpu_unchanged}")

    archive_records: dict[str, dict[str, str]] = {}
    install_report_records: list[dict[str, Any]] = []
    for path in INSTALL_REPORTS:
        data = json.loads(path.read_text(encoding="utf-8"))
        install_report_records.append(report_record(path))
        for item in data.get("install") or []:
            metadata = item.get("metadata") or {}
            name = normalized_name(str(metadata.get("name") or ""))
            download = item.get("download_info") or {}
            archive = download.get("archive_info") or {}
            digest = str(archive.get("hash") or "")
            if not digest:
                digest = "sha256=" + str((archive.get("hashes") or {}).get("sha256") or "")
            if not name or not re.fullmatch(r"sha256=[0-9a-f]{64}", digest):
                raise RuntimeError(f"missing installer archive SHA-256 for {name or '<unnamed>'}")
            archive_records[name] = {
                "archive_sha256": digest.removeprefix("sha256="),
                "archive_url": str(download.get("url") or ""),
            }

    distribution_script = r'''
import hashlib, importlib.metadata as metadata, json
from pathlib import Path
rows=[]
for dist in metadata.distributions():
    base=Path(dist._path)
    def digest(name):
        path=base/name
        return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
    rows.append({
        "name": dist.metadata["Name"],
        "version": dist.version,
        "dist_info": base.name,
        "metadata_sha256": digest("METADATA"),
        "record_sha256": digest("RECORD"),
    })
print(json.dumps(sorted(rows, key=lambda item: item["name"].casefold())))
'''
    distributions = json.loads(run("-c", distribution_script).stdout)
    missing_archives: list[str] = []
    for record in distributions:
        archive = archive_records.get(normalized_name(record["name"]))
        record["archive_sha256"] = archive["archive_sha256"] if archive else None
        record["archive_url"] = archive["archive_url"] if archive else None
        record["archive_status"] = "installer_report_bound" if archive else "venv_bootstrap"
        if archive is None and normalized_name(record["name"]) not in {"pip", "setuptools"}:
            missing_archives.append(record["name"])
    if missing_archives:
        raise RuntimeError(f"installed packages lack installer archive hashes: {missing_archives}")

    versions_script = (
        "import importlib.metadata as m,json,platform,sys,torch,torchaudio;"
        "print(json.dumps({'python':platform.python_version(),'executable':sys.executable,"
        "'base_executable':sys._base_executable,'torch':torch.__version__,"
        "'torchaudio':torchaudio.__version__,'torch_cuda_runtime':torch.version.cuda,"
        "'chatterbox':m.version('chatterbox-tts'),'cuda_available':torch.cuda.is_available(),"
        "'device_name':torch.cuda.get_device_name(0),'capability':list(torch.cuda.get_device_capability(0)),"
        "'compiled_architectures':torch.cuda.get_arch_list()}))"
    )
    versions = json.loads(run("-c", versions_script).stdout)
    expected_versions = {
        "python": "3.11.9",
        "torch": "2.11.0+cu130",
        "torchaudio": "2.11.0+cu130",
        "torch_cuda_runtime": "13.0",
        "chatterbox": "0.1.7",
        "device_name": "NVIDIA GeForce RTX 5060 Ti",
    }
    version_checks = {key: versions.get(key) == value for key, value in expected_versions.items()}
    version_checks.update(
        {
            "cuda_available": versions.get("cuda_available") is True,
            "capability_12_0": versions.get("capability") == [12, 0],
            "sm_120_compiled": "sm_120" in (versions.get("compiled_architectures") or []),
        }
    )
    if not all(version_checks.values()):
        raise RuntimeError(f"Blackwell runtime version/readiness mismatch: {version_checks}")

    pip_check = run("-m", "pip", "check", allow_failure=True)
    conflict_lines = [line.strip() for line in pip_check.stdout.splitlines() if line.strip()]
    mentioned = {
        package
        for package in EXPECTED_PIN_CONFLICT_PACKAGES
        if any(f"requirement {package}==2.6.0" in line.casefold() for line in conflict_lines)
    }
    conflicts_expected_only = (
        pip_check.returncode == 1
        and len(conflict_lines) == 2
        and mentioned == EXPECTED_PIN_CONFLICT_PACKAGES
        and all(line.casefold().startswith("chatterbox-tts 0.1.7 has requirement ") for line in conflict_lines)
    )
    if not conflicts_expected_only:
        raise RuntimeError(
            f"pip check contained more than the two authorized legacy pins: "
            f"returncode={pip_check.returncode}, lines={conflict_lines}"
        )

    freeze = sorted(
        [line.strip() for line in run("-m", "pip", "freeze", "--all").stdout.splitlines() if line.strip()],
        key=str.casefold,
    )
    lock = SIDECAR / "requirements.lock.txt"
    lock.write_text(
        "# Exact installed Blackwell GPU Chatterbox sidecar environment.\n"
        "# Chatterbox's Torch 2.6 metadata pins are intentionally superseded by the reviewed\n"
        "# matched official Torch/Torchaudio 2.11.0 CUDA 13.0 pair.\n"
        + "\n".join(freeze)
        + "\n",
        encoding="utf-8",
    )

    supporting_records = [
        {
            "path": path.relative_to(ROOT).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in SUPPORTING_EVIDENCE
    ]
    manifest = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "scope": "isolated_kira_chatterbox_0_1_7_blackwell_gpu_candidate",
        "production_status": "experimental_not_promoted_pending_voice_and_serialized_qwen_proofs",
        "global_python_314_modified": False,
        "versions": versions,
        "version_checks": version_checks,
        "requirements_lock": {
            "path": lock.relative_to(ROOT).as_posix(),
            "bytes": lock.stat().st_size,
            "sha256": sha256_file(lock),
            "line_count": len(freeze),
        },
        "requirements_inputs": [
            {
                "path": path.relative_to(ROOT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in (SIDECAR / "requirements.in.txt", SIDECAR / "torch_constraints.txt")
        ],
        "install_reports": install_report_records,
        "supporting_evidence": supporting_records,
        "installed_distributions": distributions,
        "installed_distribution_count": len(distributions),
        "pip_check": {
            "returncode": pip_check.returncode,
            "stdout_lines": conflict_lines,
            "stderr": pip_check.stderr.strip(),
            "expected_legacy_pin_conflicts_only": conflicts_expected_only,
            "authorized_superseded_pins": ["torch==2.6.0", "torchaudio==2.6.0"],
        },
        "accepted_cpu_sidecar_integrity": {
            "before_non_venv_manifest_sha256": cpu_before["non_venv_manifest_sha256"],
            "after_non_venv_manifest_sha256": cpu_after["non_venv_manifest_sha256"],
            "before_pip_freeze_sha256": cpu_before["pip_freeze_sha256"],
            "after_pip_freeze_sha256": cpu_after["pip_freeze_sha256"],
            "checks": cpu_unchanged,
        },
        "approved_kira_voice": {
            "profile_path": PROFILE.relative_to(ROOT).as_posix(),
            "profile_sha256": sha256_file(PROFILE),
            "reference_path": REFERENCE.relative_to(ROOT).as_posix(),
            "reference_sha256": sha256_file(REFERENCE),
        },
        "runtime_policy": {
            "input_channel": "public_spoken_only",
            "playback": False,
            "network": "offline_cache_only",
            "generic_voice_fallback_allowed": False,
            "compute_device": "cuda",
            "process_model_cache": "one_shot_exit_and_release",
            "cpu_sidecar_remains_production_fallback": True,
        },
    }
    output = EVIDENCE / "dependency_manifest.json"
    output.write_text(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    digest = sha256_file(output)
    (EVIDENCE / "dependency_manifest.sha256").write_text(
        f"{digest}  {output.name}\n",
        encoding="ascii",
    )
    print(
        json.dumps(
            {
                "status": "PASS",
                "distribution_count": len(distributions),
                "lock_sha256": sha256_file(lock),
                "manifest_sha256": digest,
                "expected_legacy_pin_conflicts_only": conflicts_expected_only,
                "accepted_cpu_sidecar_unchanged": all(cpu_unchanged.values()),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
