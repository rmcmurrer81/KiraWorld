"""Explicit bounded test of real controlled research; never starts the owner proof."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGING = Path(r"C:\KiraVideos\KiraLabsVideoStudio_v2_staging\2.0.0-alpha.1")
sys.path.insert(0, str(STAGING))
from kira_video_studio.robert_presence_service import RobertPresenceService  # noqa: E402


def main() -> int:
    output = ROOT / "VideoStudioDevelopment" / "robert_presence_video_cocreator" / "research_smoke"
    service = RobertPresenceService(output)
    service.prepare_bounded_proof(owner_confirmed=True)
    service.start_supervised_proof(owner_confirmed=True)
    result = service.research(
        query="artificial intelligence film",
        reason="controlled adapter connectivity test",
        related_project="ROBERT_PRESENCE_RESEARCH_ADAPTER_SMOKE",
    )
    service.stop_safely(owner_confirmed=True)
    report = {
        "status": "PASSED" if result["results"] else "FAILED",
        "real_query_executed": True,
        "result_count": len(result["results"]),
        "proof_was_owner_production_proof": False,
        "test_only": True,
        "service_stopped_after_test": service.state == "STOPPED",
        "publication_attempted": False,
        "external_message_attempted": False,
    }
    (output / "REAL_RESEARCH_SMOKE_REPORT.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))
    return 0 if report["status"] == "PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
