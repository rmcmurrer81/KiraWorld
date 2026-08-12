"""Restore the exact pre-R6 selection after a reversible live review trial."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKUP = (
    ROOT
    / "Avatar"
    / "state"
    / "body_selections"
    / "backups"
    / "kira_pre_r6_live_trial_20260719_001839"
)
RUNTIME_STATE = ROOT / "Data/runtime/kira_world_shell_state.json"
LIVE = ROOT / "Avatar/models/temp_ai/kira/avatar.glb"
RESTORES = {
    BACKUP / "kira_runtime_body_selection.pre_trial.json": ROOT
    / "Avatar/state/body_selections/kira_runtime_body_selection.json",
    BACKUP / "kira_r6_review_staging.pre_trial.json": ROOT
    / "Avatar/state/body_selections/kira_r6_review_staging.json",
    BACKUP / "kira_temp_ai_state.pre_trial.json": ROOT / "Avatar/state/temp_ai/kira.json",
}
EXPECTED = {
    BACKUP / "avatar_original_live_3ec62ba8.glb": "3ec62ba8d70a2c8235ef2013ff8183b7b3e9c41ca40c33e8b31d758b4ca3339e",
    BACKUP / "kira_runtime_body_selection.pre_trial.json": "c6bc5f3ddf1539c9705ae5ec4590466f79b0e00425b77717cc7fb0825f73e590",
    BACKUP / "kira_r6_review_staging.pre_trial.json": "995c2504d268794a8c8f60dd76b41592c01c79b103b34a11c1e28233c23ba60e",
    BACKUP / "kira_temp_ai_state.pre_trial.json": "4b08103daafceb61105592e4b3dc44229f6e2e3b3279c8d5da2c30e0c5029576",
    LIVE: "3ec62ba8d70a2c8235ef2013ff8183b7b3e9c41ca40c33e8b31d758b4ca3339e",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify() -> None:
    for path, expected in EXPECTED.items():
        if not path.is_file():
            raise RuntimeError(f"rollback file missing: {path}")
        actual = sha256(path)
        if actual != expected:
            raise RuntimeError(f"rollback hash mismatch: {path} ({actual})")


def require_inactive() -> None:
    if not RUNTIME_STATE.is_file():
        return
    state = json.loads(RUNTIME_STATE.read_text(encoding="utf-8-sig"))
    if str(state.get("active_candidate") or "").strip():
        raise RuntimeError("Deactivate Kira and close the World Shell before rollback.")


def atomic_restore(source: Path, target: Path) -> None:
    payload = source.read_bytes()
    temporary = target.with_suffix(target.suffix + ".restore.tmp")
    temporary.write_bytes(payload)
    os.replace(temporary, target)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    verify()
    require_inactive()
    if args.verify_only:
        print("Exact pre-R6 rollback files and inactive-state gate verified.")
        return 0
    for source, target in RESTORES.items():
        atomic_restore(source, target)
    print("Restored the exact pre-R6 runtime selection. The preserved live GLB was never overwritten.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
