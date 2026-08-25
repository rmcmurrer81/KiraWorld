from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import re
import time
import wave


os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"


MODEL_REVISION = "5ecdb67327fd37bb2e042aab12ff7391903235d3"
EXPECTED_MODEL_FILES = {
    ".gitattributes": (
        1_519,
        "11ad7efa24975ee4b0c3c3a38ed18737f0658a5f75a0a96787b576a78a023361",
    ),
    "README.md": (
        3_214,
        "acfaf6c0d433866cb5e2bb73e7915ea3767f5a2e3abca413b485635a2c72b5e6",
    ),
    "model.safetensors": (
        3_833_402_552,
        "391e8db219f292c515297cdceeb43e4eae67cdde35fa57e79a6a8a532fca0522",
    ),
    "speech_tokenizer/model.safetensors": (
        682_293_092,
        "836b7b357f5ea43e889936a3709af68dfe3751881acefe4ecf0dbd30ba571258",
    ),
    "config.json": (
        4_421,
        "aecd2cc4c1fe9edef1cb7ca7c401685a43879ad43f3f9e883f1c6760b61731e0",
    ),
    "generation_config.json": (
        245,
        "f1b90b4513f3b34c62851049e2492d7b4c5940daf1276f89c82b8ef04127f3aa",
    ),
    "merges.txt": (
        1_671_839,
        "599bab54075088774b1733fde865d5bd747cbcc7a547c5bc12610e874e26f5e3",
    ),
    "preprocessor_config.json": (
        127,
        "efdde1022ea9d76928bf7a9cd53139138f5ba2e466e837f08f6105ab1af1c119",
    ),
    "speech_tokenizer/config.json": (
        2_336,
        "ee65bb901c876664ab8707c487157aa1a6ee57c65969b28fb5ec9dc211e68167",
    ),
    "speech_tokenizer/configuration.json": (
        76,
        "6bc26d64eb5024b4d1dab5a52371958b429256d6c9d59787f1f5294a54e0cebd",
    ),
    "speech_tokenizer/preprocessor_config.json": (
        234,
        "fcb3805e597e786d4067706e602f6688524640f8d3396790e2e09b5942fcbdfb",
    ),
    "tokenizer_config.json": (
        7_344,
        "dc3c31c3bdaedd5016382bb3cbe07323026775ad51f5a4fb564505992ae4a670",
    ),
    "vocab.json": (
        2_776_833,
        "ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910",
    ),
}
REQUEST_KEYS = {
    "schema",
    "candidate_id",
    "language",
    "text",
    "voice_traits",
    "seed",
    "intent",
    "named_person_imitation",
    "nonproduction_feasibility",
}
VOICE_TRAIT_VALUES = {
    "presentation": {"adult_woman", "adult_man", "adult_neutral"},
    "pitch": {"low", "lower_mid", "mid", "upper_mid", "high"},
    "timbre": {"soft", "clear", "rounded", "grounded", "bright", "resonant"},
    "pace": {"slow", "moderate", "brisk"},
    "warmth": {"neutral", "warm", "very_warm"},
    "confidence": {"gentle", "steady", "assured"},
    "energy": {"calm", "balanced", "lively"},
    "accent": {"general_american", "neutral_english"},
    "breathiness": {"low", "moderate"},
}
TRAIT_PHRASES = {
    "adult_woman": "adult woman",
    "adult_man": "adult man",
    "adult_neutral": "adult gender-neutral person",
    "low": "low",
    "lower_mid": "lower-mid",
    "mid": "mid-range",
    "upper_mid": "upper-mid",
    "high": "high",
    "soft": "soft",
    "clear": "clear",
    "rounded": "rounded",
    "grounded": "grounded",
    "bright": "bright",
    "resonant": "resonant",
    "slow": "slow",
    "moderate": "moderate",
    "brisk": "brisk",
    "neutral": "neutral",
    "warm": "warm",
    "very_warm": "very warm",
    "gentle": "gentle",
    "steady": "steady",
    "assured": "assured",
    "calm": "calm",
    "balanced": "balanced",
    "lively": "lively",
    "general_american": "clear American English",
    "neutral_english": "neutral English",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON number is forbidden: {value}")


def strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_request(path: Path) -> dict[str, object]:
    request = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=strict_object,
        parse_constant=reject_constant,
    )
    if not isinstance(request, dict) or set(request) != REQUEST_KEYS:
        raise ValueError("request keys do not match the feasibility schema")
    if request["schema"] != "kira-qwen3-voice-design-feasibility-v1":
        raise ValueError("unsupported request schema")
    candidate_id = request["candidate_id"]
    if not isinstance(candidate_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{2,63}", candidate_id):
        raise ValueError("invalid candidate_id")
    if request["language"] != "English":
        raise ValueError("this bounded feasibility run supports exact English only")
    text = request["text"]
    if not isinstance(text, str) or not text.strip() or len(text) > 400:
        raise ValueError("invalid text")
    traits = request["voice_traits"]
    if not isinstance(traits, dict) or set(traits) != set(VOICE_TRAIT_VALUES):
        raise ValueError("voice_traits must contain only the exact allowlisted dimensions")
    for dimension, allowed in VOICE_TRAIT_VALUES.items():
        value = traits[dimension]
        if not isinstance(value, str) or value not in allowed:
            raise ValueError(f"unsupported voice trait: {dimension}")
    if request["intent"] != "generated_original_no_named_person_imitation":
        raise ValueError("invalid generated-original intent")
    if request["named_person_imitation"] is not False:
        raise ValueError("named-person imitation must be false")
    if request["nonproduction_feasibility"] is not True:
        raise ValueError("nonproduction feasibility acknowledgement is required")
    seed = request["seed"]
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= 2**31 - 1:
        raise ValueError("invalid seed")
    return request


def render_design_prompt(traits: dict[str, str]) -> str:
    phrase = {key: TRAIT_PHRASES[value] for key, value in traits.items()}
    return (
        f"An original {phrase['presentation']} with a {phrase['pitch']}, "
        f"{phrase['timbre']} voice, {phrase['pace']} pace, {phrase['warmth']} "
        f"tone, {phrase['confidence']} confidence, {phrase['energy']} energy, "
        f"{phrase['accent']}, and {phrase['breathiness']} breathiness. The voice "
        "must have no resemblance to any named person."
    )


def verify_model(model_dir: Path) -> list[dict[str, object]]:
    if not model_dir.is_dir() or model_dir.is_symlink():
        raise ValueError("model directory is missing or unsafe")
    expected_files = set(EXPECTED_MODEL_FILES)
    expected_directories = {
        Path(relative).parent.as_posix()
        for relative in expected_files
        if Path(relative).parent != Path(".")
    }
    actual_files: set[str] = set()
    actual_directories: set[str] = set()
    pending = [model_dir]
    while pending:
        directory = pending.pop()
        for entry in directory.iterdir():
            is_junction = getattr(entry, "is_junction", lambda: False)()
            if entry.is_symlink() or is_junction:
                raise ValueError("model payload contains a link or junction")
            relative = entry.relative_to(model_dir).as_posix()
            if entry.is_dir():
                actual_directories.add(relative)
                pending.append(entry)
            elif entry.is_file():
                actual_files.add(relative)
            else:
                raise ValueError("model payload contains an unsupported entry")
    if actual_files != expected_files or actual_directories != expected_directories:
        raise ValueError("model payload scope does not exactly match the manifest")

    verified: list[dict[str, object]] = []
    for relative, (expected_bytes, expected_sha256) in EXPECTED_MODEL_FILES.items():
        path = model_dir / relative
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"missing or unsafe model file: {relative}")
        actual_bytes = path.stat().st_size
        actual_sha256 = sha256_file(path)
        if actual_bytes != expected_bytes or actual_sha256 != expected_sha256:
            raise ValueError(f"model file mismatch: {relative}")
        verified.append(
            {"path": relative, "bytes": actual_bytes, "sha256": actual_sha256}
        )
    return verified


def inspect_wav(path: Path) -> dict[str, object]:
    with wave.open(str(path), "rb") as audio:
        channels = audio.getnchannels()
        sample_width = audio.getsampwidth()
        sample_rate = audio.getframerate()
        frames = audio.getnframes()
        compression = audio.getcomptype()
    duration = frames / sample_rate
    if channels != 1 or sample_width != 2 or sample_rate != 24_000 or compression != "NONE":
        raise ValueError("output is not canonical mono PCM16 24 kHz WAV")
    if not 0.25 <= duration <= 60.0:
        raise ValueError("output duration is outside the feasibility bound")
    return {
        "channels": channels,
        "sample_width_bytes": sample_width,
        "sample_rate_hz": sample_rate,
        "frames": frames,
        "duration_seconds": duration,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def write_json_exclusive(path: Path, payload: dict[str, object]) -> None:
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    with path.open("xb") as target:
        target.write(encoded)
        target.flush()
        os.fsync(target.fileno())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--model-dir", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    args = parser.parse_args()

    request_path = args.request.resolve(strict=True)
    model_dir = args.model_dir.resolve(strict=True)
    output_root = args.output_root.resolve(strict=True)
    request = load_request(request_path)
    model_files = verify_model(model_dir)
    design_prompt = render_design_prompt(request["voice_traits"])

    candidate_id = str(request["candidate_id"])
    run_dir = output_root / candidate_id
    run_dir.mkdir(mode=0o700, parents=False, exist_ok=False)
    wav_path = run_dir / "candidate.wav"
    temporary_wav = run_dir / "candidate.partial.wav"
    receipt_path = run_dir / "receipt.json"

    import numpy as np
    import soundfile as sf
    import torch
    import torchaudio
    import transformers
    from qwen_tts import Qwen3TTSModel

    torch.manual_seed(int(request["seed"]))
    torch.cuda.manual_seed_all(int(request["seed"]))
    torch.cuda.reset_peak_memory_stats()
    torch.cuda.synchronize()
    load_started = time.perf_counter()
    model = Qwen3TTSModel.from_pretrained(
        str(model_dir),
        device_map="cuda:0",
        dtype=torch.bfloat16,
        attn_implementation="sdpa",
        local_files_only=True,
    )
    torch.cuda.synchronize()
    load_seconds = time.perf_counter() - load_started

    generation_started = time.perf_counter()
    wavs, sample_rate = model.generate_voice_design(
        text=str(request["text"]),
        instruct=design_prompt,
        language="English",
        non_streaming_mode=True,
    )
    torch.cuda.synchronize()
    generation_seconds = time.perf_counter() - generation_started
    if not isinstance(wavs, list) or len(wavs) != 1 or sample_rate != 24_000:
        raise ValueError("unexpected model output shape or sample rate")
    waveform = np.asarray(wavs[0], dtype=np.float32).reshape(-1)
    if waveform.size == 0 or not np.isfinite(waveform).all():
        raise ValueError("model output is empty or non-finite")
    peak = float(np.max(np.abs(waveform)))
    rms = float(np.sqrt(np.mean(np.square(waveform, dtype=np.float64))))
    if not math.isfinite(peak) or not math.isfinite(rms) or peak <= 0.001 or rms <= 0.0001:
        raise ValueError("model output is silent or invalid")

    sf.write(str(temporary_wav), waveform, sample_rate, subtype="PCM_16", format="WAV")
    os.replace(temporary_wav, wav_path)
    wav_info = inspect_wav(wav_path)
    peak_allocated = int(torch.cuda.max_memory_allocated())
    peak_reserved = int(torch.cuda.max_memory_reserved())

    del waveform, wavs, model
    gc.collect()
    torch.cuda.empty_cache()
    torch.cuda.synchronize()
    final_allocated = int(torch.cuda.memory_allocated())
    final_reserved = int(torch.cuda.memory_reserved())

    receipt = {
        "schema": "kira-qwen3-voice-design-feasibility-receipt-v1",
        "status": "TECHNICAL_FEASIBILITY_SAMPLE_NOT_APPROVED_NOT_ACTIVE",
        "candidate_id": candidate_id,
        "request_path": request_path.name,
        "request_sha256": sha256_file(request_path),
        "voice_traits": request["voice_traits"],
        "rendered_design_prompt": design_prompt,
        "model_revision": MODEL_REVISION,
        "model_files": model_files,
        "runtime": {
            "python": os.sys.version.split()[0],
            "torch": torch.__version__,
            "torchaudio": torchaudio.__version__,
            "transformers": transformers.__version__,
            "cuda": torch.version.cuda,
            "device": torch.cuda.get_device_name(0),
            "capability": list(torch.cuda.get_device_capability(0)),
            "attention": "sdpa",
            "dtype": "bfloat16",
            "network_contract": "tool_restricted_network_plus_offline_flags_not_production_os_isolation",
        },
        "timing": {
            "load_seconds": load_seconds,
            "generation_seconds": generation_seconds,
        },
        "gpu_memory": {
            "peak_allocated_bytes": peak_allocated,
            "peak_reserved_bytes": peak_reserved,
            "final_allocated_bytes": final_allocated,
            "final_reserved_bytes": final_reserved,
        },
        "audio": {**wav_info, "peak_float": peak, "rms_float": rms},
        "limitations": [
            "No person identity, likeness, or named-voice claim is made.",
            "This sample has not passed listening, collision, pronunciation, or activation review.",
            "This worker does not bind, route, play, publish, or replace a voice.",
            "Production remains blocked pending reviewed OS-enforced isolation and a sealed parent/worker authority.",
        ],
    }
    write_json_exclusive(receipt_path, receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
