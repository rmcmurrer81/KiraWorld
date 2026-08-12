"""Render a saved Kira/Robert dialogue to one Chatterbox WAV file.

This uses approved/provisionally approved local reference WAVs for each speaker
and is intended for long-form review after weekly Kira/Robert meetings.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf
import torch
from chatterbox.tts import ChatterboxTTS


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.dialogue_privacy import DialoguePrivacyError, prepare_dialogue_speech_turns
from Core.artifact_binding import bind_artifact_hashes, sha256_file
from Core.dialogue_tts import prepare_tts_turns, split_for_tts, spoken_words
from Core.dialogue_audio_signal import (
    assess_generated_speech_chunk,
    gentle_proximity_correction,
)

DEFAULT_KIRA_REFERENCE = (
    "Voice/reference_packs/kira/kira_online_source_20260706_221447/model_input/approved_reference.wav"
)
DEFAULT_ROBERT_REFERENCE = (
    "Voice/reference_packs/robert_mcmurrer/robert_mcmurrer_online_source_20260714_230541/model_input/approved_reference.wav"
)


def _split_text(text: str, max_chars: int) -> list[str]:
    chunks, _ = split_for_tts(text, max_chars=max_chars)
    return chunks


def _load_turns(
    path: Path,
    last_turns: int,
    max_chars: int,
    *,
    omit_names: bool,
    prefix_speaker_names: bool,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    prepared, audit = prepare_dialogue_speech_turns(data, last_turns=last_turns, max_chars=max_chars)
    turns, tts_audit = prepare_tts_turns(
        prepared,
        omit_names=omit_names,
        prefix_speaker_names=prefix_speaker_names,
    )
    return turns, audit, tts_audit


def _resolve_reference(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    if not path.exists():
        raise FileNotFoundError(path)
    return path


def _as_mono_numpy(wav: Any) -> np.ndarray:
    if hasattr(wav, "detach"):
        arr = wav.squeeze(0).detach().cpu().numpy()
    else:
        arr = np.asarray(wav)
    arr = np.asarray(arr, dtype=np.float32).reshape(-1)
    return arr


def _apply_gain(arr: np.ndarray, gain_db: float) -> np.ndarray:
    if gain_db == 0:
        return arr
    factor = 10 ** (gain_db / 20)
    return np.clip(arr * factor, -0.98, 0.98).astype(np.float32)


def main() -> int:
    parser = argparse.ArgumentParser(description="Render dialogue JSON to one Chatterbox WAV.")
    parser.add_argument("dialogue_json", type=Path)
    parser.add_argument("--last-turns", type=int, default=0, help="Render only the last N turns. 0 means all.")
    parser.add_argument("--max-chars-per-turn", type=int, default=0, help="Legacy truncation cap. Weekly listening copies require 0 so every public SPOKEN word is retained.")
    parser.add_argument("--allow-truncated-speech", action="store_true", help="Explicitly permit the legacy per-turn truncation cap for a diagnostic draft.")
    parser.add_argument("--chunk-chars", type=int, default=180, help="Queue all words in short sentence/clause-aware chunks to reduce Chatterbox cutoffs.")
    parser.add_argument("--chunk-max-attempts", type=int, default=2, help="Bounded retries when a generated chunk is silent or implausibly short.")
    parser.add_argument("--min-seconds-per-word", type=float, default=0.18, help="Conservative non-ASR duration sanity threshold for each generated chunk.")
    parser.add_argument("--device", choices=["auto", "cuda", "cpu"], default="auto")
    parser.add_argument("--kira-reference", default=DEFAULT_KIRA_REFERENCE)
    parser.add_argument("--robert-reference", default=DEFAULT_ROBERT_REFERENCE)
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "Data" / "dialogues" / "kira_robert_intro" / "audio")
    parser.add_argument("--silence-ms", type=int, default=450)
    parser.add_argument("--chunk-silence-ms", type=int, default=90)
    parser.add_argument("--speak-speaker-names", action="store_true", help="Prefix each turn with the speaker name.")
    parser.add_argument("--speak-dialogue-names", action="store_true", help="Keep Kira/Robert name tokens inside public SPOKEN text. Default omits them because voices identify speakers.")
    parser.add_argument("--kira-gain-db", type=float, default=0.0)
    parser.add_argument("--robert-gain-db", type=float, default=-9.0)
    parser.add_argument("--robert-proximity-cut-hz", type=float, default=95.0, help="Gentle high-pass cutoff used only for Robert's close-mic correction. 0 disables it.")
    parser.add_argument("--robert-proximity-cut-mix", type=float, default=0.30, help="Dry/high-pass blend for Robert, from 0 (off) to 1.")
    parser.add_argument("--output-label", default="")
    args = parser.parse_args()

    if args.max_chars_per_turn > 0 and not args.allow_truncated_speech:
        print(
            "Refusing to truncate public SPOKEN words. Use --max-chars-per-turn 0 "
            "or explicitly mark a diagnostic with --allow-truncated-speech.",
            file=sys.stderr,
        )
        return 4
    if args.chunk_chars < 80:
        print("--chunk-chars must be at least 80.", file=sys.stderr)
        return 4
    if not 1 <= args.chunk_max_attempts <= 4 or args.min_seconds_per_word <= 0:
        print("Chunk sanity requires 1-4 attempts and a positive seconds-per-word threshold.", file=sys.stderr)
        return 4
    if not 0.0 <= args.robert_proximity_cut_mix <= 1.0 or args.robert_proximity_cut_hz < 0.0:
        print("Robert proximity correction requires a non-negative cutoff and a mix from 0 to 1.", file=sys.stderr)
        return 4

    dialogue_path = args.dialogue_json
    if not dialogue_path.is_absolute():
        dialogue_path = PROJECT_ROOT / dialogue_path
    try:
        turns, privacy_audit, tts_audit = _load_turns(
            dialogue_path,
            last_turns=args.last_turns,
            max_chars=args.max_chars_per_turn,
            omit_names=not (args.speak_dialogue_names or args.speak_speaker_names),
            prefix_speaker_names=args.speak_speaker_names,
        )
    except (DialoguePrivacyError, ValueError) as exc:
        print(f"Privacy gate blocked TTS: {exc}", file=sys.stderr)
        return 3
    if not turns:
        print("No Kira/Robert spoken turns found.", file=sys.stderr)
        return 2

    device = args.device
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    kira_reference = _resolve_reference(args.kira_reference)
    robert_reference = _resolve_reference(args.robert_reference)

    output_dir = args.output_dir if args.output_dir.is_absolute() else PROJECT_ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = "full" if args.last_turns <= 0 else f"last_{args.last_turns}_turns"
    output_label = args.output_label.strip() or suffix
    out_wav = output_dir / f"{dialogue_path.stem}_{output_label}_chatterbox_kira_robert.wav"
    manifest_path = output_dir / f"{dialogue_path.stem}_{output_label}_chatterbox_kira_robert_manifest.json"

    source_sha256 = sha256_file(dialogue_path)
    kira_reference_sha256 = sha256_file(kira_reference)
    robert_reference_sha256 = sha256_file(robert_reference)

    print(f"Loading Chatterbox on {device}...")
    model = ChatterboxTTS.from_pretrained(device=device)
    silence = np.zeros(int(model.sr * max(args.silence_ms, 0) / 1000), dtype=np.float32)
    chunk_silence = np.zeros(int(model.sr * max(args.chunk_silence_ms, 0) / 1000), dtype=np.float32)
    generated: list[dict[str, Any]] = []
    wav_frames = 0
    partial_wav = out_wav.with_suffix(".partial.wav")
    if partial_wav.exists():
        partial_wav.unlink()
    try:
        with sf.SoundFile(
            str(partial_wav),
            mode="w",
            samplerate=int(model.sr),
            channels=1,
            subtype="PCM_16",
        ) as writer:
            for index, turn in enumerate(turns, 1):
                reference = kira_reference if turn["speaker"] == "Kira" else robert_reference
                speaker_gain = args.kira_gain_db if turn["speaker"] == "Kira" else args.robert_gain_db
                chunks, chunk_audit = split_for_tts(turn["text"], max_chars=args.chunk_chars)
                chunk_records: list[dict[str, Any]] = []
                print(f"[{index}/{len(turns)}] {turn['speaker']} {len(turn['text'])} chars, {len(chunks)} chunk(s), gain {speaker_gain:+.1f} dB")
                for chunk_index, chunk in enumerate(chunks, 1):
                    attempt_records: list[dict[str, Any]] = []
                    accepted_raw: np.ndarray | None = None
                    for attempt in range(1, args.chunk_max_attempts + 1):
                        wav = model.generate(chunk, audio_prompt_path=str(reference))
                        raw_arr = _as_mono_numpy(wav)
                        sanity = assess_generated_speech_chunk(
                            raw_arr,
                            sample_rate=int(model.sr),
                            queued_word_count=len(spoken_words(chunk)),
                            min_seconds_per_word=args.min_seconds_per_word,
                        )
                        attempt_records.append({"attempt": attempt, **sanity})
                        if sanity["passed"]:
                            accepted_raw = raw_arr
                            break
                        print(
                            f"  chunk {chunk_index}/{len(chunks)} attempt {attempt} "
                            f"failed acoustic sanity: {', '.join(sanity['reasons'])}"
                        )
                    if accepted_raw is None:
                        raise RuntimeError(
                            f"Chunk {chunk_index} of turn {index} failed bounded acoustic sanity retries"
                        )
                    arr = accepted_raw
                    if turn["speaker"] == "Robert":
                        arr = gentle_proximity_correction(
                            arr,
                            sample_rate=int(model.sr),
                            cutoff_hz=args.robert_proximity_cut_hz,
                            mix=args.robert_proximity_cut_mix,
                        )
                    arr = _apply_gain(arr, speaker_gain)
                    writer.write(arr)
                    wav_frames += len(arr)
                    chunk_records.append(
                        {
                            "chunk_index": chunk_index,
                            "chunk_text_sha256": hashlib.sha256(chunk.encode("utf-8")).hexdigest(),
                            "attempt_count": len(attempt_records),
                            "accepted_attempt": len(attempt_records),
                            "sanity_attempts": attempt_records,
                        }
                    )
                    if chunk_index < len(chunks):
                        writer.write(chunk_silence)
                        wav_frames += len(chunk_silence)
                writer.write(silence)
                wav_frames += len(silence)
                generated.append(
                    {
                        "index": index,
                        "speaker": turn["speaker"],
                        "chars": len(turn["text"]),
                        "chunks": len(chunks),
                        "gain_db": speaker_gain,
                        "tts_text_sha256": turn["tts_text_sha256"],
                        "removed_dialogue_name_occurrences": turn["removed_dialogue_name_occurrences"],
                        "non_name_word_coverage_exact": turn["non_name_word_coverage_exact"],
                        "chunking_audit": chunk_audit,
                        "chunk_generation": chunk_records,
                        "proximity_correction": (
                            {
                                "algorithm": "second_order_highpass_dry_blend",
                                "cutoff_hz": args.robert_proximity_cut_hz,
                                "mix": args.robert_proximity_cut_mix,
                            }
                            if turn["speaker"] == "Robert"
                            else None
                        ),
                    }
                )
    except Exception as exc:
        if partial_wav.exists():
            partial_wav.unlink()
        print(f"Atomic audio render aborted: {exc}", file=sys.stderr)
        return 5
    partial_wav.replace(out_wav)
    wav_sha256 = sha256_file(out_wav)
    generation_sanity_sha256 = hashlib.sha256(
        json.dumps(generated, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    artifact_binding = bind_artifact_hashes(
        {
            "source_dialogue": source_sha256,
            "spoken_payload": privacy_audit["spoken_payload_sha256"],
            "tts_payload": tts_audit["tts_payload_sha256"],
            "generation_sanity": generation_sanity_sha256,
            "kira_voice_reference": kira_reference_sha256,
            "robert_voice_reference": robert_reference_sha256,
            "output_wav": wav_sha256,
        },
        metadata={
            "voice_mode": "chatterbox_tts_two_voice_dialogue",
            "turn_count": len(turns),
            "sample_rate": int(model.sr),
            "last_turns": args.last_turns,
            "max_chars_per_turn": args.max_chars_per_turn,
            "chunk_chars": args.chunk_chars,
            "chunk_max_attempts": args.chunk_max_attempts,
            "min_seconds_per_word": args.min_seconds_per_word,
            "speak_speaker_names": args.speak_speaker_names,
            "speak_dialogue_names": args.speak_dialogue_names,
            "kira_gain_db": args.kira_gain_db,
            "robert_gain_db": args.robert_gain_db,
            "robert_proximity_cut_hz": args.robert_proximity_cut_hz,
            "robert_proximity_cut_mix": args.robert_proximity_cut_mix,
        },
    )
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_dialogue_json": str(dialogue_path.relative_to(PROJECT_ROOT)),
        "source_dialogue_sha256": source_sha256,
        "audio_path": str(out_wav.relative_to(PROJECT_ROOT)),
        "turn_count": len(turns),
        "voice_mode": "chatterbox_tts_two_voice_dialogue",
        "device": device,
        "sample_rate": int(model.sr),
        "kira_reference": str(kira_reference.relative_to(PROJECT_ROOT)),
        "kira_reference_sha256": kira_reference_sha256,
        "robert_reference": str(robert_reference.relative_to(PROJECT_ROOT)),
        "robert_reference_sha256": robert_reference_sha256,
        "robert_reference_note": "Robert self-voice is provisionally prepared from Robert-authorized YouTube speech.",
        "max_chars_per_turn": args.max_chars_per_turn,
        "chunk_chars": args.chunk_chars,
        "chunk_max_attempts": args.chunk_max_attempts,
        "chunk_silence_ms": args.chunk_silence_ms,
        "acoustic_sanity_gate": {
            "status": "passed_all_chunks",
            "scope": "non_silent_pcm_and_conservative_duration_per_queued_word_not_asr_verified",
            "min_seconds_per_word": args.min_seconds_per_word,
            "max_attempts_per_chunk": args.chunk_max_attempts,
            "asr_word_coverage_verified": False,
            "human_listening_verified": False,
        },
        "generation_sanity_sha256": generation_sanity_sha256,
        "speak_speaker_names": args.speak_speaker_names,
        "speak_dialogue_names": args.speak_dialogue_names,
        "dialogue_names_spoken": bool(args.speak_dialogue_names or args.speak_speaker_names),
        "kira_gain_db": args.kira_gain_db,
        "robert_gain_db": args.robert_gain_db,
        "robert_proximity_correction": {
            "algorithm": "second_order_highpass_dry_blend",
            "cutoff_hz": args.robert_proximity_cut_hz,
            "mix": args.robert_proximity_cut_mix,
            "purpose": "conservative close-mic bass/proximity reduction; does not alter pitch or timing",
        },
        "last_turns": args.last_turns,
        "privacy_audit": privacy_audit,
        "tts_audit": tts_audit,
        "private_channels_spoken": False,
        "wav_sha256": wav_sha256,
        "wav_frames": int(wav_frames),
        "wav_duration_seconds": round(wav_frames / int(model.sr), 3),
        "render_write_mode": "incremental_atomic_finalize",
        "artifact_binding": artifact_binding,
        "generated": generated,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
