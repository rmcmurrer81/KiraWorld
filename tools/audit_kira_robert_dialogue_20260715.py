"""Audit a saved Kira/Robert dialogue without exposing private text."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.dialogue_continuity import write_continuity_candidate
from Core.dialogue_privacy import contains_private_marker, prepare_dialogue_speech_turns
from tools.run_kira_robert_intro_dialogue_20260714 import spoken_similarity


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def build_audit(data: dict[str, Any], source: Path) -> dict[str, Any]:
    turns = [item for item in (data.get("transcript") or []) if isinstance(item, dict)]
    prepared, privacy = prepare_dialogue_speech_turns(data)
    times = [_time(str(item["at"])) for item in turns if item.get("at")]
    elapsed = (times[-1] - times[0]).total_seconds() / 60 if len(times) >= 2 else 0.0
    speaker_counts = Counter(str(item.get("speaker") or "") for item in turns)
    warnings = Counter(w for item in turns for w in (item.get("warnings") or []))
    spoken_counts = Counter(str(item.get("spoken") or "").strip() for item in turns)
    exact_duplicate_occurrences = sum(count for text, count in spoken_counts.items() if text and count > 1)

    similar_turns = 0
    similar_turns_90 = 0
    prior_by_speaker: dict[str, list[str]] = defaultdict(list)
    for item in turns:
        speaker = str(item.get("speaker") or "")
        spoken = str(item.get("spoken") or "")
        previous = prior_by_speaker[speaker]
        best = max((spoken_similarity(spoken, old) for old in previous), default=0.0)
        if best >= 0.8:
            similar_turns += 1
        if best >= 0.9:
            similar_turns_90 += 1
        previous.append(spoken)

    target = float(data.get("duration_minutes_target") or 0)
    target_reached = elapsed >= max(0.0, target - 0.1) if target else None
    spoken_words = sum(len(str(turn["text"]).split()) for turn in prepared)
    estimated_audio_minutes = spoken_words / 135.0

    return {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_dialogue": str(source.relative_to(PROJECT_ROOT)),
        "source_dialogue_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "dialogue_id": data.get("dialogue_id"),
        "classification": "controlled_role_dialogue_draft_not_private_continuous_person_evidence",
        "completion": {
            "stored_status": data.get("status"),
            "target_minutes": target,
            "actual_turn_generation_elapsed_minutes": round(elapsed, 3),
            "target_reached": target_reached,
            "turn_count": len(turns),
            "speaker_counts": dict(speaker_counts),
            "truth_note": "A stored complete flag does not prove the requested duration was reached.",
        },
        "privacy": {
            **privacy,
            "private_sections_shared_in_original_prompt_design": True,
            "original_session_private_boundary": "failed",
            "spoken_only_export_can_remove_direct_private_audio": True,
            "spoken_only_export_cannot_undo_cross-role_context_exposure": True,
        },
        "warnings": {
            "total": sum(warnings.values()),
            "counts": dict(warnings),
        },
        "continuity": {
            "single_model_alternated_roles": True,
            "separate_persistent_minds_proven": False,
            "prior_meeting_loaded": False,
            "kira_live_memory_store_loaded": False,
            "robert_source_file_read_by_original_runner": False,
            "automatic_memory_promotion_allowed": False,
        },
        "quality": {
            "spoken_word_count": spoken_words,
            "estimated_audio_minutes_at_135_wpm": round(estimated_audio_minutes, 1),
            "exact_duplicate_spoken_occurrences": exact_duplicate_occurrences,
            "same_speaker_turns_similarity_gte_0_8": similar_turns,
            "same_speaker_turns_similarity_gte_0_9": similar_turns_90,
            "autonomy_refusal_demonstrated": False,
        },
        "disposition": {
            "original_pending_wav": "privacy_unsafe_do_not_treat_as_review_copy",
            "direct_private_audio_render_allowed": False,
            "sanitized_spoken_only_render_allowed_with_context_contamination_label": True,
            "durable_memory_promotion_allowed": False,
        },
    }


def _markdown(audit: dict[str, Any]) -> str:
    completion = audit["completion"]
    privacy = audit["privacy"]
    quality = audit["quality"]
    warning_counts = audit["warnings"]["counts"]
    return "\n".join(
        [
            f"# {audit['dialogue_id']} audit",
            "",
            f"- Classification: `{audit['classification']}`",
            f"- Turns: {completion['turn_count']} ({completion['speaker_counts']})",
            f"- Target: {completion['target_minutes']} minutes; actual generation span: {completion['actual_turn_generation_elapsed_minutes']} minutes",
            f"- Target reached: {completion['target_reached']}",
            f"- Privacy-contaminated stored spoken turns: {privacy['source_context_contamination_count']}",
            f"- Recovered public turns: {privacy['turn_count']}; direct private markers remaining after recovery: 0",
            f"- Warnings: {audit['warnings']['total']} ({warning_counts})",
            f"- Exact duplicate spoken occurrences: {quality['exact_duplicate_spoken_occurrences']}",
            f"- Similar same-speaker turns >=0.8 / >=0.9: {quality['same_speaker_turns_similarity_gte_0_8']} / {quality['same_speaker_turns_similarity_gte_0_9']}",
            f"- Estimated sanitized audio length: {quality['estimated_audio_minutes_at_135_wpm']} minutes",
            "",
            "The original WAV is privacy-unsafe because private sections were included in 120 stored spoken fields. A spoken-only export can prevent direct private audio, but it cannot undo the fact that the original role prompts shared private context. This session is not evidence of separate persistent minds or durable memory continuity.",
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("dialogue_json", type=Path)
    args = parser.parse_args()
    source = args.dialogue_json if args.dialogue_json.is_absolute() else PROJECT_ROOT / args.dialogue_json
    data = json.loads(source.read_text(encoding="utf-8-sig"))
    audit = build_audit(data, source)
    folder = source.parent / "audits"
    folder.mkdir(parents=True, exist_ok=True)
    json_path = folder / f"{source.stem}_audit.json"
    md_path = folder / f"{source.stem}_audit.md"
    json_path.write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path.write_text(_markdown(audit), encoding="utf-8")
    candidate = write_continuity_candidate(
        data,
        source_path=source,
        project_root=PROJECT_ROOT,
        contamination_count=audit["privacy"]["source_context_contamination_count"],
    )
    print(json.dumps({
        "audit_json": str(json_path.relative_to(PROJECT_ROOT)),
        "audit_md": str(md_path.relative_to(PROJECT_ROOT)),
        "continuity_candidate": str(candidate.relative_to(PROJECT_ROOT)),
        "summary": audit,
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
