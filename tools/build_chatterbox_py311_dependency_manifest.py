#!/usr/bin/env python3
"""Seal the isolated Chatterbox Python 3.11 environment without copying it."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SIDECAR_ROOT = ROOT / "Voice" / "sidecars" / "chatterbox_py311"
VENV_PYTHON = SIDECAR_ROOT / ".venv" / "Scripts" / "python.exe"
EVIDENCE = SIDECAR_ROOT / "evidence"
REPORTS = (
    EVIDENCE / "torch_install_report.raw.json",
    EVIDENCE / "chatterbox_install_report.raw.json",
    EVIDENCE / "resource_install_report.raw.json",
)
REFERENCE = ROOT / "Voice/reference_packs/kira/kira_online_source_20260706_221447/model_input/approved_reference.wav"
PROFILE = ROOT / "Voice/profiles/temp_ai/kira_voice_profile.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalized_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value.strip().casefold())


def run_sidecar(*args: str) -> str:
    completed = subprocess.run(
        [str(VENV_PYTHON), *args],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        timeout=180,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip())
    return completed.stdout


def main() -> int:
    if not VENV_PYTHON.is_file():
        raise FileNotFoundError(VENV_PYTHON)
    for path in (*REPORTS, REFERENCE, PROFILE):
        if not path.is_file():
            raise FileNotFoundError(path)
    EVIDENCE.mkdir(parents=True, exist_ok=True)

    archive_records: dict[str, dict[str, str]] = {}
    report_records: list[dict[str, object]] = []
    for report_path in REPORTS:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        report_records.append(
            {
                "path": report_path.relative_to(ROOT).as_posix(),
                "bytes": report_path.stat().st_size,
                "sha256": sha256_file(report_path),
                "pip_version": report.get("pip_version"),
                "python_full_version": (report.get("environment") or {}).get("python_full_version"),
                "install_record_count": len(report.get("install") or []),
            }
        )
        for item in report.get("install") or []:
            metadata = item.get("metadata") or {}
            name = normalized_name(str(metadata.get("name") or ""))
            archive = ((item.get("download_info") or {}).get("archive_info") or {})
            digest = str(archive.get("hash") or "")
            if not digest:
                digest = "sha256=" + str((archive.get("hashes") or {}).get("sha256") or "")
            if not name or not digest.startswith("sha256=") or len(digest) != 71:
                raise RuntimeError(f"missing SHA-256 archive hash for {name or '<unnamed>'}")
            archive_records[name] = {
                "archive_sha256": digest.removeprefix("sha256="),
                "archive_url": str((item.get("download_info") or {}).get("url") or ""),
            }

    distribution_script = r'''
import hashlib, importlib.metadata as metadata, json
from pathlib import Path
records=[]
for dist in metadata.distributions():
    meta_path=Path(dist._path)/"METADATA"
    record_path=Path(dist._path)/"RECORD"
    def digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
    records.append({
        "name": dist.metadata["Name"],
        "version": dist.version,
        "dist_info": Path(dist._path).name,
        "metadata_sha256": digest(meta_path),
        "record_sha256": digest(record_path),
    })
print(json.dumps(sorted(records, key=lambda item: item["name"].casefold())))
'''
    distributions = json.loads(run_sidecar("-c", distribution_script))
    missing_archives: list[str] = []
    for record in distributions:
        key = normalized_name(record["name"])
        archive = archive_records.get(key)
        record["archive_sha256"] = archive["archive_sha256"] if archive else None
        record["archive_url"] = archive["archive_url"] if archive else None
        record["archive_status"] = "installer_report_bound" if archive else "venv_bootstrap"
        if archive is None and key not in {"pip", "setuptools"}:
            missing_archives.append(record["name"])
    if missing_archives:
        raise RuntimeError(f"installed packages lack archive hashes: {missing_archives}")

    freeze = run_sidecar("-m", "pip", "freeze", "--all").strip().splitlines()
    lock_path = SIDECAR_ROOT / "requirements.lock.txt"
    lock_path.write_text(
        "# Exact installed Python 3.11 Chatterbox sidecar environment.\n"
        "# Archive SHA-256 values are in evidence/dependency_manifest.json.\n"
        + "\n".join(sorted(freeze, key=str.casefold))
        + "\n",
        encoding="utf-8",
    )
    pip_check = run_sidecar("-m", "pip", "check").strip()
    version_text = run_sidecar("-c", "import platform,sys; print(platform.python_version()); print(sys.executable)").splitlines()
    base_python = Path(r"C:\Users\robmc\AppData\Local\Programs\Python\Python311\python.exe")
    manifest = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "scope": "isolated_kira_chatterbox_0_1_7_sidecar",
        "global_python_314_modified": False,
        "python": {
            "version": version_text[0],
            "venv_executable_relative": VENV_PYTHON.relative_to(ROOT).as_posix(),
            "venv_executable_sha256": sha256_file(VENV_PYTHON),
            "base_executable": str(base_python),
            "base_executable_sha256": sha256_file(base_python),
        },
        "requirements_lock": {
            "path": lock_path.relative_to(ROOT).as_posix(),
            "bytes": lock_path.stat().st_size,
            "sha256": sha256_file(lock_path),
            "line_count": len(freeze),
        },
        "install_reports": report_records,
        "installed_distributions": distributions,
        "installed_distribution_count": len(distributions),
        "pip_check": pip_check,
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
            "process_model_cache": "one_shot_exit_and_release",
        },
    }
    manifest_path = EVIDENCE / "dependency_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (EVIDENCE / "dependency_manifest.sha256").write_text(
        f"{sha256_file(manifest_path)}  dependency_manifest.json\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "PASS",
                "python": version_text[0],
                "distribution_count": len(distributions),
                "lock_sha256": sha256_file(lock_path),
                "manifest_sha256": sha256_file(manifest_path),
                "pip_check": pip_check,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
