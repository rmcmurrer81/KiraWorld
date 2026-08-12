#!/usr/bin/env python3
"""One-click Elsa bounded official-source evidence preparation."""
from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.temp_ai_elsa_automatic_voice_evidence import (  # noqa: E402
    build_elsa_automatic_voice_evidence,
)


def main() -> int:
    try:
        result = build_elsa_automatic_voice_evidence()
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "blocked_no_identity_model_or_runtime_change",
                    "error": str(exc)[:1000],
                    "voice_assigned": False,
                    "candidate_activated": False,
                },
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1
    print(
        json.dumps(
            {
                "status": result["status"],
                "source": result["source"]["url"],
                "ranges": [
                    [item["start_seconds"], item["end_seconds"]]
                    for item in result["source"]["ranges"]
                ],
                "cache": result["cache"],
                "evidence_wav": result["combined_evidence_wav"]["path"],
                "evidence_sha256": result["combined_evidence_wav"]["sha256"],
                "manifest": result["manifest_path"],
                "speaker_identity_claimed": False,
                "voice_assigned": False,
                "candidate_activated": False,
                "manual_review_gui_opened": False,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
