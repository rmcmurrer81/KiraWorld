#!/usr/bin/env python3
"""Run one bounded, no-playback approved-Kira sidecar voice proof."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "Core") not in sys.path:
    sys.path.insert(0, str(ROOT / "Core"))

from Core.voice_output import release_voice_output, synthesize_text_to_wav  # noqa: E402
from tools import kira_world_shell_server as shell  # noqa: E402
from tools.run_qwen_text_voice_acceptance import (  # noqa: E402
    compare_protected_hashes,
    hash_protected_files,
    validate_wav,
)


EVIDENCE_ROOT = ROOT / "RecoverySprint" / "continuation_20260801" / "chatterbox_sidecar_acceptance"
PUBLIC_TEXT = "I received your typed message, Robert, and this approved Kira voice test is complete."


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def qwen_loaded() -> bool:
    completed = subprocess.run(
        ["ollama", "ps"],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    return "qwen3.5:9b" in completed.stdout.casefold()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempt", type=int, choices=(1, 2), required=True)
    args = parser.parse_args()
    run_dir = EVIDENCE_ROOT / f"attempt_{args.attempt:02d}"
    if run_dir.exists():
        raise SystemExit(f"refusing to overwrite existing evidence: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=False)
    target = run_dir / "kira_approved_sidecar_probe.wav"
    report: dict[str, object] = {
        "schema_version": 1,
        "attempt": args.attempt,
        "started_at": utc_now(),
        "public_spoken_text": PUBLIC_TEXT,
        "public_spoken_text_sha256": hashlib.sha256(PUBLIC_TEXT.encode("utf-8")).hexdigest(),
        "typed_input": True,
        "microphone_used": False,
        "image_input_used": False,
        "playback_requested": False,
        "generic_voice_allowed": False,
        "errors": [],
    }
    before = hash_protected_files()
    report["protected_before"] = before
    started = time.perf_counter()
    try:
        if qwen_loaded():
            raise RuntimeError("Qwen must be absent before serialized sidecar synthesis")
        binding = shell.required_reference_voice_binding("kira", "Kira")
        cfg = binding.get("config")
        if cfg is None or cfg.engine != "chatterbox_tts":
            raise RuntimeError("approved Kira Chatterbox binding is unavailable")
        reference = ROOT / cfg.chatterbox_reference_audio
        profile = ROOT / "Voice/profiles/temp_ai/kira_voice_profile.json"
        report["binding"] = {
            "engine": cfg.engine,
            "reference_relative": cfg.chatterbox_reference_audio,
            "reference_sha256": sha256_file(reference),
            "profile_sha256": sha256_file(profile),
        }
        result = synthesize_text_to_wav(
            PUBLIC_TEXT,
            target,
            config=replace(cfg, play_audio=False, output_dir=str(run_dir.relative_to(ROOT))),
        )
        report["synthesis_result"] = result
        report["generation_wall_seconds"] = round(time.perf_counter() - started, 3)
        report["wav_validation"] = validate_wav(target)
        report["voice_release"] = release_voice_output()
        report["qwen_absent_after"] = not qwen_loaded()
        issues = []
        if result.get("generated") is not True or result.get("sidecar") is not True:
            issues.append("sealed_sidecar_did_not_generate")
        if result.get("engine") != "chatterbox_tts" or result.get("generic_voice_used") is not False:
            issues.append("approved_chatterbox_identity_failed")
        if result.get("playback") is not False:
            issues.append("playback_was_not_disabled")
        if result.get("text_sha256") != report["public_spoken_text_sha256"]:
            issues.append("requested_text_binding_failed")
        if result.get("reference_sha256") != report["binding"]["reference_sha256"]:
            issues.append("approved_reference_hash_failed")
        if (report["wav_validation"] or {}).get("passed") is not True:
            issues.append("wav_validation_failed")
        if report["qwen_absent_after"] is not True:
            issues.append("qwen_not_absent_after_voice")
        report["issues"] = issues
    except Exception as exc:
        report["errors"].append(f"{type(exc).__name__}: {exc}")
        report["generation_wall_seconds"] = round(time.perf_counter() - started, 3)
        report["issues"] = ["sidecar_acceptance_exception"]
        try:
            report["voice_release"] = release_voice_output()
        except Exception as cleanup_exc:
            report["errors"].append(f"cleanup:{type(cleanup_exc).__name__}:{cleanup_exc}")
    after = hash_protected_files()
    report["protected_after"] = after
    report["protected_integrity"] = compare_protected_hashes(before, after)
    report["finished_at"] = utc_now()
    report["status"] = (
        "PASS"
        if not report.get("issues")
        and not report.get("errors")
        and (report.get("protected_integrity") or {}).get("passed") is True
        else "FAIL"
    )
    report_path = run_dir / "sidecar_acceptance.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "evidence": str(report_path)}, indent=2))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
