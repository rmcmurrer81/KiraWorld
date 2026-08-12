"""Non-playing validation and privacy disposition for dialogue WAV artifacts."""

from __future__ import annotations

import hashlib
import json
import wave
from pathlib import Path
from typing import Any

from Core.artifact_binding import bind_artifact_hashes, sha256_file
from Core.dialogue_privacy import (
    DialoguePrivacyError,
    contains_private_marker,
    prepare_dialogue_speech_turns,
)
from Core.dialogue_tts import prepare_tts_turns, split_for_tts


def inspect_pcm_wav(path: Path) -> dict[str, Any]:
    """Inspect a WAV container without opening an audio output device."""

    with wave.open(str(path), "rb") as handle:
        channels = handle.getnchannels()
        sample_width = handle.getsampwidth()
        sample_rate = handle.getframerate()
        frame_count = handle.getnframes()
        compression_type = handle.getcomptype()
    return {
        "container": "RIFF/WAVE",
        "channels": channels,
        "sample_width_bytes": sample_width,
        "sample_rate": sample_rate,
        "frame_count": frame_count,
        "duration_seconds": round(frame_count / sample_rate, 3) if sample_rate else 0.0,
        "compression_type": compression_type,
        "wav_sha256": sha256_file(path),
    }


def review_dialogue_wav(
    *,
    source_path: Path,
    source_data: dict[str, Any],
    wav_path: Path,
    manifest: dict[str, Any] | None,
) -> dict[str, Any]:
    """Return a fail-closed, non-playing listening disposition."""

    source_sha256 = sha256_file(source_path)
    wav_info = inspect_pcm_wav(wav_path)
    raw_turns = source_data.get("transcript") or source_data.get("turns") or []
    stored_spoken_marker_count = sum(
        contains_private_marker(str(item.get("spoken") or ""))
        for item in raw_turns
        if isinstance(item, dict)
    )
    reasons: list[str] = []
    freshly_prepared_audit: dict[str, Any] | None = None
    freshly_prepared_turns: list[dict[str, Any]] | None = None
    fresh_tts_audit: dict[str, Any] | None = None
    fresh_tts_turns: list[dict[str, Any]] | None = None
    fresh_generation_sanity_sha256: str | None = None
    selected_last_turns = 0
    selected_max_chars = 0
    if manifest is not None:
        raw_last_turns = manifest.get("last_turns", 0)
        raw_max_chars = manifest.get("max_chars_per_turn", 0)
        if (
            isinstance(raw_last_turns, bool)
            or not isinstance(raw_last_turns, int)
            or raw_last_turns < 0
        ):
            reasons.append("manifest_last_turns_invalid")
        else:
            selected_last_turns = raw_last_turns
        if (
            isinstance(raw_max_chars, bool)
            or not isinstance(raw_max_chars, int)
            or raw_max_chars < 0
        ):
            reasons.append("manifest_max_chars_per_turn_invalid")
        else:
            selected_max_chars = raw_max_chars
    try:
        freshly_prepared_turns, freshly_prepared_audit = prepare_dialogue_speech_turns(
            source_data,
            last_turns=selected_last_turns,
            max_chars=selected_max_chars,
        )
    except DialoguePrivacyError as exc:
        reasons.append(f"source_cannot_be_proven_spoken_only:{exc}")

    if manifest is None:
        reasons.append("missing_render_manifest")
    else:
        privacy = manifest.get("privacy_audit")
        if not isinstance(privacy, dict) or privacy.get("privacy_status") != "passed_spoken_only":
            reasons.append("manifest_lacks_passed_spoken_only_audit")
        elif freshly_prepared_audit is not None:
            if privacy.get("spoken_payload_sha256") != freshly_prepared_audit.get("spoken_payload_sha256"):
                reasons.append("manifest_spoken_payload_hash_mismatch")
            if privacy.get("turn_count") != freshly_prepared_audit.get("turn_count"):
                reasons.append("manifest_privacy_turn_count_mismatch")
            if privacy.get("selection") != freshly_prepared_audit.get("selection"):
                reasons.append("manifest_privacy_selection_mismatch")
        if manifest.get("private_channels_spoken") is not False:
            reasons.append("manifest_does_not_attest_private_channels_excluded")
        if manifest.get("source_dialogue_sha256") != source_sha256:
            reasons.append("source_hash_missing_or_mismatched")
        if manifest.get("wav_sha256") != wav_info["wav_sha256"]:
            reasons.append("wav_hash_missing_or_mismatched")
        if freshly_prepared_audit is not None and manifest.get("turn_count") != freshly_prepared_audit.get("turn_count"):
            reasons.append("manifest_turn_count_mismatch")

        manifest_tts_audit = manifest.get("tts_audit")
        if manifest_tts_audit is not None:
            if not isinstance(manifest_tts_audit, dict):
                reasons.append("manifest_tts_audit_invalid")
            elif not isinstance(manifest.get("dialogue_names_spoken"), bool):
                reasons.append("manifest_dialogue_name_policy_missing")
            elif freshly_prepared_turns is not None:
                try:
                    fresh_tts_turns, fresh_tts_audit = prepare_tts_turns(
                        freshly_prepared_turns,
                        omit_names=not manifest["dialogue_names_spoken"],
                        prefix_speaker_names=bool(manifest.get("speak_speaker_names")),
                    )
                except ValueError as exc:
                    reasons.append(f"tts_payload_cannot_be_reconstructed:{exc}")
                else:
                    for field in (
                        "transform",
                        "dialogue_names_spoken",
                        "speaker_labels_spoken",
                        "turn_count",
                        "removed_dialogue_name_occurrences",
                        "non_name_word_coverage_exact",
                        "tts_payload_sha256",
                    ):
                        if manifest_tts_audit.get(field) != fresh_tts_audit.get(field):
                            reasons.append(f"manifest_tts_audit_{field}_mismatch")
                    if not manifest["dialogue_names_spoken"] and not manifest_tts_audit.get(
                        "non_name_word_coverage_exact"
                    ):
                        reasons.append("manifest_does_not_attest_exact_non_name_word_coverage")

        acoustic_gate = manifest.get("acoustic_sanity_gate")
        if acoustic_gate is not None:
            if not isinstance(acoustic_gate, dict):
                reasons.append("manifest_acoustic_sanity_gate_invalid")
            else:
                if acoustic_gate.get("status") != "passed_all_chunks":
                    reasons.append("manifest_acoustic_sanity_not_passed")
                if acoustic_gate.get("asr_word_coverage_verified") is not False:
                    reasons.append("manifest_acoustic_gate_overclaims_asr_verification")
                if acoustic_gate.get("human_listening_verified") is not False:
                    reasons.append("manifest_acoustic_gate_overclaims_human_verification")
            generated = manifest.get("generated")
            if not isinstance(generated, list) or len(generated) != manifest.get("turn_count"):
                reasons.append("manifest_generation_sanity_records_invalid")
            else:
                fresh_generation_sanity_sha256 = hashlib.sha256(
                    json.dumps(
                        generated,
                        sort_keys=True,
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ).encode("utf-8")
                ).hexdigest()
                if manifest.get("generation_sanity_sha256") != fresh_generation_sanity_sha256:
                    reasons.append("manifest_generation_sanity_hash_mismatch")
                for turn_index, turn_record in enumerate(generated, 1):
                    chunks = turn_record.get("chunk_generation") if isinstance(turn_record, dict) else None
                    if (
                        not isinstance(chunks, list)
                        or not isinstance(turn_record.get("chunks"), int)
                        or len(chunks) != turn_record.get("chunks")
                    ):
                        reasons.append(f"manifest_turn_{turn_index}_chunk_sanity_invalid")
                        continue
                    expected_chunks: list[str] | None = None
                    if fresh_tts_turns is not None and isinstance(manifest.get("chunk_chars"), int):
                        try:
                            expected_chunks, _ = split_for_tts(
                                fresh_tts_turns[turn_index - 1]["text"],
                                max_chars=manifest["chunk_chars"],
                            )
                        except (IndexError, KeyError, TypeError, ValueError) as exc:
                            reasons.append(
                                f"manifest_turn_{turn_index}_chunks_cannot_be_reconstructed:{exc}"
                            )
                        else:
                            if len(expected_chunks) != len(chunks):
                                reasons.append(
                                    f"manifest_turn_{turn_index}_chunk_count_mismatch"
                                )
                    for chunk_index, chunk_record in enumerate(chunks, 1):
                        attempts = chunk_record.get("sanity_attempts") if isinstance(chunk_record, dict) else None
                        if (
                            not isinstance(attempts, list)
                            or not attempts
                            or chunk_record.get("attempt_count") != len(attempts)
                            or chunk_record.get("accepted_attempt") != len(attempts)
                            or attempts[-1].get("passed") is not True
                            or attempts[-1].get("reasons") != []
                            or attempts[-1].get("duration_seconds", 0)
                            < attempts[-1].get("minimum_plausible_duration_seconds", 0)
                        ):
                            reasons.append(
                                f"manifest_turn_{turn_index}_chunk_{chunk_index}_sanity_not_proven"
                            )
                        if expected_chunks is not None and chunk_index <= len(expected_chunks):
                            expected_chunk_sha = hashlib.sha256(
                                expected_chunks[chunk_index - 1].encode("utf-8")
                            ).hexdigest()
                            if chunk_record.get("chunk_text_sha256") != expected_chunk_sha:
                                reasons.append(
                                    f"manifest_turn_{turn_index}_chunk_{chunk_index}_text_hash_mismatch"
                                )

        binding = manifest.get("artifact_binding")
        artifacts = binding.get("artifacts") if isinstance(binding, dict) else None
        expected_spoken_hash = (
            freshly_prepared_audit.get("spoken_payload_sha256")
            if freshly_prepared_audit
            else None
        )
        if not isinstance(artifacts, dict):
            reasons.append("missing_artifact_binding")
        else:
            required_matches = {
                "source_dialogue": source_sha256,
                "spoken_payload": expected_spoken_hash,
                "output_wav": wav_info["wav_sha256"],
            }
            if manifest.get("tts_audit") is not None:
                required_matches["tts_payload"] = (
                    fresh_tts_audit.get("tts_payload_sha256")
                    if fresh_tts_audit
                    else None
                )
            if manifest.get("acoustic_sanity_gate") is not None:
                required_matches["generation_sanity"] = fresh_generation_sanity_sha256
            for name, expected in required_matches.items():
                if not expected or artifacts.get(name) != expected:
                    reasons.append(f"artifact_binding_{name}_mismatch")
            binding_metadata = binding.get("metadata")
            if not isinstance(binding_metadata, dict):
                reasons.append("missing_artifact_binding_metadata")
            else:
                expected_metadata = {
                    "turn_count": freshly_prepared_audit.get("turn_count") if freshly_prepared_audit else None,
                    "last_turns": selected_last_turns,
                    "max_chars_per_turn": selected_max_chars,
                }
                acoustic_gate = manifest.get("acoustic_sanity_gate")
                if isinstance(acoustic_gate, dict):
                    expected_metadata.update(
                        {
                            "chunk_chars": manifest.get("chunk_chars"),
                            "chunk_max_attempts": acoustic_gate.get("max_attempts_per_chunk"),
                            "min_seconds_per_word": acoustic_gate.get("min_seconds_per_word"),
                        }
                    )
                    if manifest.get("chunk_max_attempts") != acoustic_gate.get(
                        "max_attempts_per_chunk"
                    ):
                        reasons.append("manifest_chunk_attempt_policy_mismatch")
                for name, expected in expected_metadata.items():
                    if expected is None or binding_metadata.get(name) != expected:
                        reasons.append(f"artifact_binding_metadata_{name}_mismatch")
            if not reasons:
                rebuilt = bind_artifact_hashes(
                    artifacts,
                    metadata=binding.get("metadata") if isinstance(binding.get("metadata"), dict) else {},
                )
                if rebuilt["binding_sha256"] != binding.get("binding_sha256"):
                    reasons.append("artifact_binding_digest_mismatch")

    if stored_spoken_marker_count and (
        manifest is None or "missing_artifact_binding" in reasons or
        "manifest_lacks_passed_spoken_only_audit" in reasons
    ):
        reasons.append("stored_spoken_fields_contain_private_channel_markers")

    status = (
        "manifest_bound_listening_copy_not_acoustically_verified"
        if not reasons and wav_info["frame_count"] > 0 and wav_info["duration_seconds"] > 0
        else "quarantined_do_not_play"
    )
    if wav_info["frame_count"] <= 0 or wav_info["duration_seconds"] <= 0:
        reasons.append("wav_has_no_audio_frames")
    return {
        "schema_version": 1,
        "status": status,
        "audio_was_played_during_review": False,
        "acoustic_speech_content_verified": False,
        "voice_identity_verified_by_this_review": False,
        "review_scope": "WAV container plus transcript/payload/reference/output hash binding; human listening is still required for spoken content and voice quality",
        "source_dialogue": str(source_path),
        "source_dialogue_sha256": source_sha256,
        "wav_path": str(wav_path),
        "wav": wav_info,
        "stored_spoken_private_marker_count": stored_spoken_marker_count,
        "fresh_spoken_privacy_audit": freshly_prepared_audit,
        "fresh_tts_audit": fresh_tts_audit,
        "fresh_generation_sanity_sha256": fresh_generation_sanity_sha256,
        "reasons": reasons,
    }
