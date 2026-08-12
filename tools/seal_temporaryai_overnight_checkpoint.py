"""Create a hash-manifest ZIP of the authorized TemporaryAI repair checkpoint."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BACKUP = Path(r"C:\KiraVideos\Backups\Kira_TemporaryAI_shared_mind_20260726_031500.zip")
MANIFEST = BACKUP.with_suffix(".manifest.json")

PATHS = (
    "Core/person_mind_runtime.py",
    "Core/person_runtime_safeguards.py",
    "Core/candidate_movement_intents.py",
    "Core/temporary_person_request.py",
    "tools/temporary_ai_live_chat.py",
    "tools/temporary_ai_live_chat_gui.py",
    "tools/audit_recent_person_runtime.py",
    "tools/request_temporary_person.py",
    "tools/run_required_person_retests.py",
    "tools/seal_temporaryai_overnight_checkpoint.py",
    "Testing/test_person_mind_runtime.py",
    "Testing/test_person_runtime_safeguards.py",
    "Testing/test_temporary_person_request.py",
    "Testing/test_audit_recent_person_runtime.py",
    "HANDOFF_FOR_NEXT_CODEX_SESSION.md",
    "System/Docs/README_MASTER_INDEX.md",
    "System/Docs/KIRA_TEMPORARYAI_AND_VIDEO_STUDIO_OVERNIGHT_CHECKPOINT_20260726.md",
    "Data/codex_reports/20260726_temporaryai_shared_mind_and_video_studio_owner_packages.md",
    "Data/person_runtime_audits/recent_person_runtime_audit_20260726_023809.json",
    "Data/person_runtime_audits/recent_person_runtime_audit_20260726_023809.md",
    "Data/person_runtime_audits/required_person_retests_20260726_024800/required_person_retests.json",
)


def main() -> int:
    if BACKUP.exists() or MANIFEST.exists():
        raise FileExistsError("checkpoint backup target already exists")
    rows = []
    BACKUP.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(BACKUP, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for relative in PATHS:
            path = ROOT / relative
            if not path.is_file():
                raise FileNotFoundError(path)
            data = path.read_bytes()
            archive.write(path, relative)
            rows.append({
                "path": relative,
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            })
    payload = {
        "backup": str(BACKUP),
        "file_count": len(rows),
        "zip_sha256": hashlib.sha256(BACKUP.read_bytes()).hexdigest(),
        "files": rows,
    }
    MANIFEST.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
