from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import time

import soundfile as sf
import torch
import torchaudio


ASR_CHECKPOINT_NAME = "wav2vec2_fairseq_base_ls960_asr_ls960.pth"
ASR_CHECKPOINT_BYTES = 377_664_473
ASR_CHECKPOINT_SHA256 = "488fd4f16de84438ffc945334278c1b9fb9b7159a806c1080b16111a958c945d"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def normalize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.casefold().replace("'", ""))


def word_error_rate(reference: str, hypothesis: str) -> float:
    target = normalize(reference)
    predicted = normalize(hypothesis)
    previous = list(range(len(predicted) + 1))
    for row, expected_word in enumerate(target, start=1):
        current = [row]
        for column, actual_word in enumerate(predicted, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[column] + 1,
                    previous[column - 1] + (expected_word != actual_word),
                )
            )
        previous = current
    return previous[-1] / max(1, len(target))


def decode(emission: torch.Tensor, labels: tuple[str, ...]) -> str:
    token_ids = torch.argmax(emission, dim=-1)[0]
    token_ids = torch.unique_consecutive(token_ids)
    tokens = [labels[index] for index in token_ids if index != 0]
    return "".join(tokens).replace("|", " ").strip().lower()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wav", required=True, type=Path)
    parser.add_argument("--request", required=True, type=Path)
    args = parser.parse_args()
    request = json.loads(args.request.read_text(encoding="utf-8"))
    expected = request["text"]
    torch_home = os.environ.get("TORCH_HOME")
    if not torch_home:
        raise ValueError("TORCH_HOME must identify the pinned local ASR cache")
    asr_checkpoint = (
        Path(torch_home).resolve(strict=True)
        / "hub"
        / "checkpoints"
        / ASR_CHECKPOINT_NAME
    )
    if (
        not asr_checkpoint.is_file()
        or asr_checkpoint.is_symlink()
        or asr_checkpoint.stat().st_size != ASR_CHECKPOINT_BYTES
        or sha256_file(asr_checkpoint) != ASR_CHECKPOINT_SHA256
    ):
        raise ValueError("pinned ASR checkpoint is missing or mismatched")
    wav_sha256 = sha256_file(args.wav)
    request_sha256 = sha256_file(args.request)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    bundle = torchaudio.pipelines.WAV2VEC2_ASR_BASE_960H
    load_started = time.perf_counter()
    model = bundle.get_model().to(device).eval()
    load_seconds = time.perf_counter() - load_started
    labels = bundle.get_labels()
    data, sample_rate = sf.read(args.wav, dtype="float32", always_2d=False)
    waveform = torch.from_numpy(data).float().unsqueeze(0)
    if sample_rate != bundle.sample_rate:
        waveform = torchaudio.functional.resample(
            waveform, sample_rate, bundle.sample_rate
        )
    waveform = waveform.to(device)
    started = time.perf_counter()
    with torch.inference_mode():
        emission, _ = model(waveform)
    if device == "cuda":
        torch.cuda.synchronize()
    transcript = decode(emission.cpu(), labels)
    wer = word_error_rate(expected, transcript)
    report = {
        "schema": "kira-qwen3-voice-design-asr-audit-v1",
        "status": "PASS" if wer <= 0.25 else "REVIEW",
        "auditor": "torchaudio_WAV2VEC2_ASR_BASE_960H_greedy",
        "torchaudio": torchaudio.__version__,
        "asr_checkpoint": {
            "filename": ASR_CHECKPOINT_NAME,
            "bytes": ASR_CHECKPOINT_BYTES,
            "sha256": ASR_CHECKPOINT_SHA256,
        },
        "input": {
            "wav_filename": args.wav.name,
            "wav_sha256": wav_sha256,
            "request_filename": args.request.name,
            "request_sha256": request_sha256,
        },
        "device": device,
        "model_load_seconds": round(load_seconds, 4),
        "asr_seconds": round(time.perf_counter() - started, 4),
        "expected": expected,
        "transcript": transcript,
        "word_error_rate": round(wer, 4),
        "note": "ASR WER is an intelligibility proxy, not a naturalness or identity rating.",
    }
    destination = args.wav.with_name("asr-audit.json")
    destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
