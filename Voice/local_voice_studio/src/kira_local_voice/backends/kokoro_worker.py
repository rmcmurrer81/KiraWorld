"""One-shot Kokoro worker with no socket, download, telemetry, or text logging."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import stat
import sys
import types
import wave
from importlib.metadata import distribution
from pathlib import Path

MAX_INPUT = 32_768
MAX_TEXT_CHARACTERS = 4_000
MAX_TEXT_UTF8_BYTES = 16_000
MAX_OUTPUT_BYTES = 64 * 1024 * 1024
ALLOWLIST = frozenset({"af_heart", "am_fenrir"})
MODEL_REPO = "hexgrad/Kokoro-82M"
MODEL_REVISION = "fbba31e67ad83eb66394c926627e99d35abeb087"
MODEL_FILES = {
    "config.json": "5abb01e2403b072bf03d04fde160443e209d7a0dad49a423be15196b9b43c17f",
    "kokoro-v1_0.pth": "496dba118d1a58f5f3db2efc88dbdc216e0483fc89fe6e47ee1f2c53f18ad1e4",
    "voices/af_heart.pt": "0ab5709b8ffab19bfd849cd11d98f75b60af7733253ad0d67b12382a102cb4ff",
    "voices/am_fenrir.pt": "98e507eca1db08230ae3b6232d59c10aec9630022d19accac4f5d12fcec3c37a",
}


def fail(code: str) -> None:
    print(json.dumps({"schema": "kira.kokoro.result.v2", "ok": False, "error": code}), flush=True)
    raise SystemExit(2)


def _is_unc(value: str) -> bool:
    return value.startswith("\\\\") or value.startswith("//")


def _regular_contained(root: Path, relative: str, expected_sha256: str) -> Path:
    path = root.joinpath(*relative.split("/"))
    if path.is_symlink() or (hasattr(os.path, "isjunction") and os.path.isjunction(path)):
        fail("bundle_link_rejected")
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError):
        fail("bundle_path_invalid")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(resolved, flags)
    except OSError:
        fail("bundle_file_unreadable")
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            fail("bundle_file_not_regular")
        digest = hashlib.sha256()
        while True:
            block = os.read(fd, 1024 * 1024)
            if not block:
                break
            digest.update(block)
        after = os.fstat(fd)
        if (
            (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
            or digest.hexdigest() != expected_sha256
        ):
            fail("bundle_integrity_failure")
    finally:
        os.close(fd)
    return resolved


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--one-shot", action="store_true", required=True)
    parser.add_argument("--bundle-root", type=Path, required=True)
    parser.add_argument("--staging-root", type=Path, required=True)
    parser.add_argument("--device", choices=("cpu", "cuda"), required=True)
    args = parser.parse_args()
    for raw_path in (str(args.bundle_root), str(args.staging_root)):
        if _is_unc(raw_path):
            fail("unc_path_rejected")
    for configured in (args.bundle_root,args.staging_root):
        if configured.is_symlink() or (hasattr(os.path,"isjunction") and os.path.isjunction(configured)):
            fail("configured_root_link_rejected")
    try:
        bundle_root = args.bundle_root.resolve(strict=True)
        staging_root = args.staging_root.resolve(strict=True)
    except OSError:
        fail("configured_root_missing")
    for root in (bundle_root, staging_root):
        if root.is_symlink() or (hasattr(os.path, "isjunction") and os.path.isjunction(root)):
            fail("configured_root_link_rejected")
        if not root.is_dir():
            fail("configured_root_invalid")
    staging_identity = staging_root.stat()

    raw = sys.stdin.buffer.read(MAX_INPUT + 1)
    if len(raw) > MAX_INPUT:
        fail("request_too_large")
    def strict_object(pairs):
        result={}
        for key,value in pairs:
            if key in result: raise ValueError
            result[key]=value
        return result
    try:
        request = json.loads(raw,object_pairs_hook=strict_object,
            parse_constant=lambda _value: (_ for _ in ()).throw(ValueError()))
    except (UnicodeDecodeError, json.JSONDecodeError,ValueError):
        fail("invalid_json")
    required = {"schema", "text", "voice_id", "speed", "output_path"}
    if not isinstance(request, dict) or set(request) != required:
        fail("invalid_schema")
    if request.get("schema") != "kira.kokoro.request.v2":
        fail("invalid_schema")
    text, voice = request["text"], request["voice_id"]
    speed, output_value = request["speed"], request["output_path"]
    if (
        not isinstance(text, str)
        or not text.strip()
        or len(text) > MAX_TEXT_CHARACTERS
        or len(text.encode("utf-8")) > MAX_TEXT_UTF8_BYTES
    ):
        fail("invalid_text")
    if voice not in ALLOWLIST:
        fail("invalid_voice")
    if (
        not isinstance(speed, (int, float))
        or isinstance(speed, bool)
        or not math.isfinite(float(speed))
        or not 0.5 <= float(speed) <= 2.0
    ):
        fail("invalid_speed")
    if not isinstance(output_value, str) or _is_unc(output_value):
        fail("invalid_output")
    target = Path(output_value)
    if target.is_symlink() or (hasattr(os.path, "isjunction") and os.path.isjunction(target)):
        fail("invalid_output")
    try:
        target = target.resolve(strict=False)
        target.relative_to(staging_root)
    except (OSError, ValueError):
        fail("output_escape")
    if target.parent != staging_root or target.exists() or target.suffix != ".partial":
        fail("invalid_output")
    current_staging=staging_root.stat()
    if (current_staging.st_dev,current_staging.st_ino)!=(staging_identity.st_dev,staging_identity.st_ino):
        fail("staging_root_changed")

    files = {
        relative: _regular_contained(bundle_root, relative, digest)
        for relative, digest in MODEL_FILES.items()
    }
    os.environ.update(
        HF_HUB_OFFLINE="1",
        TRANSFORMERS_OFFLINE="1",
        HF_HUB_DISABLE_TELEMETRY="1",
        DO_NOT_TRACK="1",
    )
    try:
        import soundfile as sf
        import torch
        from misaki.espeak import EspeakG2P

        # Import the official model module without executing kokoro.__init__,
        # which imports KPipeline/spaCy and reaches the Windows-blocked gold_io
        # extension. This does not patch any installed package or security rule.
        package_root=Path(distribution("kokoro").locate_file("kokoro")).resolve(strict=True)
        if package_root.is_symlink() or (hasattr(os.path,"isjunction") and os.path.isjunction(package_root)):
            fail("kokoro_package_link_rejected")
        kokoro_package=types.ModuleType("kokoro"); kokoro_package.__path__=[str(package_root)]
        sys.modules["kokoro"]=kokoro_package
        from kokoro.model import KModel

        model = KModel(
            repo_id=MODEL_REPO,
            config=str(files["config.json"]),
            model=str(files["kokoro-v1_0.pth"]),
        ).to(args.device).eval()
        pack = torch.load(files[f"voices/{voice}.pt"], weights_only=True).to(args.device)
        phonemes, _ = EspeakG2P(language="en-us")(text.strip())
        if not phonemes or len(phonemes) > 510:
            fail("phoneme_length")
        with torch.inference_mode():
            audio = model(
                phonemes,
                pack[len(phonemes) - 1],
                float(speed),
                return_output=True,
            ).audio
        samples = audio.detach().cpu().numpy()
        sf.write(str(target), samples, 24_000, subtype="PCM_16", format="WAV")
        info = target.stat(follow_symlinks=False)
        if not stat.S_ISREG(info.st_mode) or not 44 < info.st_size <= MAX_OUTPUT_BYTES:
            fail("output_contract_failure")
        with wave.open(str(target), "rb") as wav:
            if wav.getnchannels() != 1 or wav.getsampwidth() != 2 or wav.getframerate() != 24_000:
                fail("output_contract_failure")
            duration = wav.getnframes() / wav.getframerate()
        if not math.isfinite(duration) or not 0 < duration <= 600:
            fail("output_contract_failure")
        response = {
            "schema": "kira.kokoro.result.v2",
            "ok": True,
            "format": "wav",
            "sample_rate_hz": 24_000,
            "duration_seconds": round(duration, 6),
            "output_bytes": info.st_size,
            "backend_name": "kokoro-direct-subprocess",
            "backend_version": "2.0",
            "model_source": MODEL_REPO,
            "model_revision": MODEL_REVISION,
            "voice_id": voice,
            "license_id": "Apache-2.0",
            "offline": True,
            "provenance_scope": "two_voice_runtime_bundle_only",
        }
        print(json.dumps(response, sort_keys=True, allow_nan=False), flush=True)
    except SystemExit:
        raise
    except Exception:
        target.unlink(missing_ok=True)
        fail("worker_failure")


if __name__ == "__main__":
    main()
