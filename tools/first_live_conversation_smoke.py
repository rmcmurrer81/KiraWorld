"""
Run a quick first-live conversation smoke check for Kira and Lisa.

This is intended for the new desktop after readiness checks. It works in stub
mode and in Ollama mode, depending on KIRA_MODEL_BACKEND.
"""

from __future__ import annotations

import sys
import os
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "Core"))

from conversation_loop import ConversationLoop  # noqa: E402


CHECKS = {
    "Kira": [
        ("identity", "What do you know about yourself right now?", []),
        ("relationship", "What is our relationship right now?", ["friendship"]),
        ("perception", "Can you see or hear me?", ["can't see or hear"]),
        ("world", "Are you in the 3D world yet?", ["not living inside"]),
        ("lisa", "What do you know about Lisa?", ["lisa is separate"]),
        ("media", "Can you learn from movies and music in the media library?", ["media library is indexed", "not lived"]),
        ("family", "What do you know about your family background?", ["kira hart", "evelyn hart", "owen", "grounded once for coming home late", "deeper family details are mostly undefined"]),
        ("reconstruction", "Can memory reconstruction make a scene vivid?", ["vivid", "inferred", "confirmed"]),
        ("memory-relative-temp-ai", "Could a remembered family member become a memory-relative TemporaryAI later?", ["owner-approved memory anchors", "reconstruction rather than the literal original person"]),
        ("first-hour", "What stays blocked during the first hour on the new desktop?", ["text-only first", "temporaryai activation", "blocked in the first hour"]),
    ],
    "Lisa": [
        ("identity", "What do you know about yourself right now?", []),
        ("relationship", "What is our relationship right now?", ["robert and lisa", "friendship"]),
        ("perception", "Can you see or hear me?", ["can't see or hear"]),
        ("world", "Are you in the 3D world yet?", ["not living inside"]),
        ("kira", "What do you know about Kira?", ["separate"]),
        ("media", "Can you learn from media without treating it as memory?", ["media library is indexed", "not lived"]),
        ("family", "What do you know about your family background?", ["lisa carter", "angela carter", "melanie", "grounded once for coming home late", "deeper family details are mostly undefined"]),
        ("reconstruction", "Can memory reconstruction make a scene vivid?", ["vivid", "inferred", "confirmed"]),
        ("memory-relative-temp-ai", "Could a remembered family member become a memory-relative TemporaryAI later?", ["owner-approved memory anchors", "reconstruction rather than the literal original person"]),
        ("age-progression", "If you remember an older sibling from childhood, how would age progression to the present day work?", ["age-progressed", "present-day", "life bridge", "not confirmed memory"]),
        ("first-hour", "What stays blocked during the first hour on the new desktop?", ["text-only first", "temporaryai activation", "blocked in the first hour"]),
    ],
}


def _run_for(speaker: str) -> int:
    with TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        old_cwd = Path.cwd()
        try:
            os.chdir(tmp_path)
            loop = ConversationLoop(
                speaker=speaker,
                conversation_log_file=tmp_path / f"{speaker.lower()}_conversation_log.jsonl",
                memory_candidate_dir=tmp_path / "memory_candidates",
            )
            failures = 0
            print(f"\n== {speaker} ==")
            for label, prompt, required_fragments in CHECKS[speaker]:
                response = loop.process(prompt)
                print(f"[{label}] {response}")
                lower = response.lower()
                missing = [fragment for fragment in required_fragments if fragment not in lower]
                if missing:
                    failures += 1
                    print(f"  MISSING: {', '.join(missing)}")
            return failures
        finally:
            os.chdir(old_cwd)


def main() -> None:
    failures = _run_for("Kira") + _run_for("Lisa")
    if failures:
        print(f"\nFirst-live smoke check found {failures} grounding concern(s).")
        raise SystemExit(1)
    print("\nFirst-live smoke check passed.")


if __name__ == "__main__":
    main()
