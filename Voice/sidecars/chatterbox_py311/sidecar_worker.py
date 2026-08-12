#!/usr/bin/env python3
"""One-shot, offline, approved-Kira-reference Chatterbox synthesis worker."""

from __future__ import annotations

import argparse
import contextlib
import gc
import hashlib
import importlib.metadata
import json
import math
import os
import subprocess
import sys
import threading
import time
import uuid
import wave
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = Path(__file__).with_name("sidecar_config.json")
MAX_STDIN_BYTES = 64 * 1024
PRIVATE_MARKERS = (
    "private mind:",
    "factual truth:",
    "hidden reasoning:",
    "internal monologue:",
    "private thought:",
)
GPU_PROBE_ERRORS: list[str] = []


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def project_file(relative: str) -> Path:
    value = Path(str(relative).replace("\\", "/"))
    if value.is_absolute() or ".." in value.parts:
        raise ValueError("unsafe project-relative path")
    resolved = (ROOT / value).resolve()
    resolved.relative_to(ROOT.resolve())
    return resolved


def load_and_verify_config() -> dict[str, Any]:
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError("unsupported sidecar config schema")
    if sha256_file(Path(__file__)) != str(data.get("worker_sha256") or "").casefold():
        raise ValueError("sidecar worker hash mismatch")
    dependency_manifest = project_file(data["dependency_manifest"])
    profile = project_file(data["approved_profile"])
    reference = project_file(data["approved_reference"])
    checks = (
        (dependency_manifest, data["dependency_manifest_sha256"], "dependency manifest"),
        (profile, data["approved_profile_sha256"], "voice profile"),
        (reference, data["approved_reference_sha256"], "approved reference"),
    )
    for path, expected, label in checks:
        if not path.is_file() or sha256_file(path) != str(expected).casefold():
            raise ValueError(f"{label} hash mismatch")
    profile_data = json.loads(profile.read_text(encoding="utf-8-sig"))
    approved = str((profile_data.get("source_audio") or {}).get("approved_reference_wav") or "").replace("\\", "/")
    if approved != data["approved_reference"] or (profile_data.get("source_audio") or {}).get("required") is not True:
        raise ValueError("voice profile no longer requires the sealed reference")
    if tuple(sys.version_info[:2]) != (3, 11):
        raise ValueError("sidecar must run on Python 3.11")
    required_versions = {
        "chatterbox-tts": data["chatterbox_version"],
        "torch": "2.6.0+cu124",
        "torchaudio": "2.6.0+cu124",
    }
    for package, expected in required_versions.items():
        if importlib.metadata.version(package) != expected:
            raise ValueError(f"sealed dependency mismatch: {package}")
    if str(os.environ.get("HF_HUB_OFFLINE", "")) != "1" or str(os.environ.get("TRANSFORMERS_OFFLINE", "")) != "1":
        raise ValueError("sidecar requires offline cache-only environment")
    return data


def safe_output_path(relative: str, config: dict[str, Any]) -> Path:
    target = project_file(relative)
    if target.suffix.casefold() != ".wav":
        raise ValueError("sidecar output must be a WAV")
    allowed = False
    for root_value in config.get("allowed_output_roots") or []:
        root = project_file(root_value)
        try:
            target.relative_to(root)
            allowed = target != root
        except ValueError:
            continue
        if allowed:
            break
    if not allowed:
        raise ValueError("sidecar output is outside approved project roots")
    return target


def read_request(config: dict[str, Any]) -> dict[str, Any]:
    raw = sys.stdin.buffer.read(MAX_STDIN_BYTES + 1)
    if len(raw) > MAX_STDIN_BYTES:
        raise ValueError("sidecar request exceeds 64 KiB")
    request = json.loads(raw.decode("utf-8"))
    if not isinstance(request, dict) or request.get("schema_version") != 1:
        raise ValueError("invalid sidecar request schema")
    if request.get("channel") != config["input_channel"]:
        raise ValueError("sidecar accepts only public SPOKEN text")
    request_id = str(request.get("request_id") or "")
    try:
        uuid.UUID(request_id)
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError("invalid sidecar request id") from exc
    text = str(request.get("text") or "").strip()
    if not text or len(text) > int(config["max_text_characters"]):
        raise ValueError("public spoken text is empty or oversized")
    lowered = text.casefold()
    if any(marker in lowered for marker in PRIVATE_MARKERS):
        raise ValueError("private or factual channel marker reached sidecar")
    if request.get("text_sha256") != sha256_text(text):
        raise ValueError("spoken text hash mismatch")
    if request.get("reference_sha256") != config["approved_reference_sha256"]:
        raise ValueError("request did not bind the approved reference hash")
    safe_output_path(str(request.get("output_relative") or ""), config)
    return {**request, "text": text}


def gpu_memory_used_mib() -> float | None:
    try:
        executable = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "nvidia-smi.exe"
        if not executable.is_file():
            GPU_PROBE_ERRORS.append(f"missing:{executable}")
            return None
        completed = subprocess.run(
            [str(executable), "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            text=True,
            capture_output=True,
            timeout=3,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        values = [float(line.strip()) for line in completed.stdout.splitlines() if line.strip()]
        if completed.returncode != 0 or not values:
            GPU_PROBE_ERRORS.append(
                f"exit={completed.returncode}:stderr={completed.stderr.strip()[:300]}:stdout={completed.stdout.strip()[:100]}"
            )
            return None
        return sum(values)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        GPU_PROBE_ERRORS.append(f"{type(exc).__name__}:{exc}")
        return None


class ResourceSampler:
    def __init__(self) -> None:
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="chatterbox-sidecar-resource-sampler", daemon=True)
        self.samples = 0
        self.peak_process_rss_mib = 0.0
        self.peak_system_used_mib = 0.0
        self.peak_gpu_used_mib = 0.0
        self.baseline_gpu_used_mib: float | None = None

    def _sample(self) -> None:
        import psutil

        process_mib = psutil.Process().memory_info().rss / (1024 * 1024)
        memory = psutil.virtual_memory()
        system_used_mib = (memory.total - memory.available) / (1024 * 1024)
        gpu_mib = gpu_memory_used_mib()
        if self.samples == 0:
            self.baseline_gpu_used_mib = gpu_mib
        self.samples += 1
        self.peak_process_rss_mib = max(self.peak_process_rss_mib, process_mib)
        self.peak_system_used_mib = max(self.peak_system_used_mib, system_used_mib)
        if gpu_mib is not None:
            self.peak_gpu_used_mib = max(self.peak_gpu_used_mib, gpu_mib)

    def _run(self) -> None:
        while not self._stop.wait(0.2):
            try:
                self._sample()
            except Exception:
                continue

    def start(self) -> None:
        self._sample()
        self._thread.start()

    def stop(self) -> dict[str, Any]:
        self._stop.set()
        self._thread.join(timeout=2)
        self._sample()
        baseline = self.baseline_gpu_used_mib
        return {
            "sample_count": self.samples,
            "peak_process_rss_mib": round(self.peak_process_rss_mib, 1),
            "peak_system_ram_used_mib": round(self.peak_system_used_mib, 1),
            "baseline_gpu_vram_used_mib": round(baseline, 1) if baseline is not None else None,
            "peak_gpu_vram_used_mib": round(self.peak_gpu_used_mib, 1) if self.peak_gpu_used_mib else None,
            "peak_sidecar_gpu_delta_mib": (
                round(max(0.0, self.peak_gpu_used_mib - baseline), 1)
                if baseline is not None and self.peak_gpu_used_mib
                else None
            ),
            "gpu_probe_errors": list(dict.fromkeys(GPU_PROBE_ERRORS))[:10],
        }


def validate_wav(path: Path) -> dict[str, Any]:
    with wave.open(str(path), "rb") as handle:
        channels = handle.getnchannels()
        sample_width = handle.getsampwidth()
        sample_rate = handle.getframerate()
        frames = handle.getnframes()
        payload = handle.readframes(frames)
    if sample_width != 2:
        raise ValueError("sidecar WAV is not PCM16")
    import array

    samples = array.array("h")
    samples.frombytes(payload[: len(payload) - (len(payload) % 2)])
    if sys.byteorder != "little":
        samples.byteswap()
    peak = max((abs(int(value)) for value in samples), default=0) / 32767.0
    rms = math.sqrt(sum(float(value) ** 2 for value in samples) / len(samples)) / 32767.0 if samples else 0.0
    duration = frames / sample_rate if sample_rate else 0.0
    passed = channels == 1 and sample_rate >= 8000 and duration >= 0.1 and peak >= 0.001 and rms >= 0.0001
    return {
        "passed": passed,
        "channels": channels,
        "sample_width_bytes": sample_width,
        "sample_rate": sample_rate,
        "frames": frames,
        "duration_seconds": round(duration, 3),
        "peak_normalized": round(peak, 6),
        "rms_normalized": round(rms, 6),
        "non_silent": peak >= 0.001 and rms >= 0.0001,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def synthesize(request: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    core = ROOT / "Core"
    if str(core) not in sys.path:
        sys.path.insert(0, str(core))
    import numpy as np
    import soundfile as sf
    import torch
    from chatterbox.tts import ChatterboxTTS
    from dialogue_audio_signal import assess_generated_speech_chunk
    from dialogue_tts import split_for_tts, spoken_words
    from voice_output import VoiceOutputConfig, postprocess_chatterbox_samples

    text = request["text"]
    target = safe_output_path(request["output_relative"], config)
    reference = project_file(config["approved_reference"])
    chunks, chunk_manifest = split_for_tts(text, max_chars=180)
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(f".{target.stem}.{request['request_id']}.part.wav")
    partial.unlink(missing_ok=True)
    if target.exists():
        raise FileExistsError("sidecar refuses to overwrite an existing WAV")
    device = str(config["compute_device"])
    model = None
    checks: list[dict[str, Any]] = []
    postprocess_checks: list[dict[str, Any]] = []
    started = time.perf_counter()
    try:
        with contextlib.redirect_stdout(sys.stderr):
            model = ChatterboxTTS.from_pretrained(device=device)
            sample_rate = int(model.sr)
            output_config = VoiceOutputConfig(
                engine="chatterbox_tts",
                chatterbox_reference_audio=config["approved_reference"],
                chatterbox_device=device,
                play_audio=False,
                pcm_output_gain_db=float(request.get("pcm_output_gain_db") or 0.0),
                proximity_cut_hz=float(request.get("proximity_cut_hz") or 0.0),
                proximity_cut_mix=float(request.get("proximity_cut_mix") or 0.0),
            )
            with sf.SoundFile(
                str(partial),
                mode="w",
                samplerate=sample_rate,
                channels=1,
                subtype="PCM_16",
                format="WAV",
            ) as output:
                for index, chunk in enumerate(chunks):
                    accepted = None
                    latest: dict[str, Any] = {}
                    for attempt in range(1, 4):
                        wav = model.generate(chunk, audio_prompt_path=str(reference))
                        value = wav.squeeze().detach().cpu().numpy() if hasattr(wav, "detach") else wav
                        samples = np.asarray(value, dtype=np.float32).reshape(-1)
                        latest = assess_generated_speech_chunk(
                            samples,
                            sample_rate=sample_rate,
                            queued_word_count=len(spoken_words(chunk)),
                        )
                        latest.update({"chunk_index": index, "attempt": attempt})
                        if latest.get("passed"):
                            accepted = samples
                            break
                    checks.append(latest)
                    if accepted is None:
                        raise RuntimeError("chatterbox_signal_validation_failed")
                    processed, postprocess = postprocess_chatterbox_samples(
                        accepted,
                        sample_rate=sample_rate,
                        config=output_config,
                    )
                    postprocess["chunk_index"] = index
                    postprocess_checks.append(postprocess)
                    output.write(processed)
                    if index < len(chunks) - 1:
                        output.write(np.zeros(max(1, int(sample_rate * 0.06)), dtype=np.float32))
        partial.replace(target)
        wav = validate_wav(target)
        if not wav["passed"]:
            raise RuntimeError("sidecar_wav_validation_failed")
        return {
            "generated": True,
            "reason": "ok",
            "engine": "chatterbox_tts",
            "sidecar_id": config["sidecar_id"],
            "request_id": request["request_id"],
            "channel": config["input_channel"],
            "text_sha256": sha256_text(text),
            "text_characters": len(text),
            "requested_public_words": spoken_words(text),
            "requested_text_bound": True,
            "reference_relative": config["approved_reference"],
            "reference_sha256": sha256_file(reference),
            "voice_identity_status": "reviewed_reference_chatterbox",
            "generic_voice_used": False,
            "playback": False,
            "device": device,
            "generation_seconds": round(time.perf_counter() - started, 3),
            "audio_path": str(target),
            "audio_relative": target.relative_to(ROOT).as_posix(),
            "wav_validation": wav,
            "chunks": chunk_manifest,
            "chunk_checks": checks,
            "audio_postprocess": {
                "applied": any(item.get("applied") for item in postprocess_checks),
                "application_count_per_chunk": 1,
                "chunks": postprocess_checks,
            },
        }
    finally:
        try:
            partial.unlink(missing_ok=True)
        except OSError:
            pass
        model = None
        gc.collect()
        if device == "cuda" and torch.cuda.is_available():
            torch.cuda.empty_cache()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()
    sampler = ResourceSampler()
    sampler.start()
    started = time.perf_counter()
    result: dict[str, Any]
    try:
        config = load_and_verify_config()
        if args.self_check:
            result = {
                "ready": True,
                "reason": "sealed_sidecar_ready",
                "sidecar_id": config["sidecar_id"],
                "python_version": ".".join(str(value) for value in sys.version_info[:3]),
                "chatterbox_version": importlib.metadata.version("chatterbox-tts"),
                "reference_sha256": config["approved_reference_sha256"],
                "playback": False,
                "model_loaded": False,
            }
        else:
            request = read_request(config)
            result = synthesize(request, config)
    except Exception as exc:
        result = {
            "generated": False,
            "ready": False,
            "reason": "sidecar_error",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "playback": False,
            "generic_voice_used": False,
        }
    result["process_seconds"] = round(time.perf_counter() - started, 3)
    result["resources"] = sampler.stop()
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("generated") is True or result.get("ready") is True else 2


if __name__ == "__main__":
    raise SystemExit(main())
