"""Rebuild the reading ledger from saved reading chunk records."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from reading_ledger import LEDGER_PATH, append_reading_event, load_ledger, write_ledger  # noqa: E402


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild Kira/Lisa reading ledger from chunk JSON files.")
    parser.add_argument("--chunk-dir", default="Data/reading/chunks")
    parser.add_argument("--ledger-path", default=str(LEDGER_PATH.relative_to(PROJECT_ROOT)))
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    chunk_dir = PROJECT_ROOT / args.chunk_dir
    ledger_path = PROJECT_ROOT / args.ledger_path
    if args.reset and ledger_path.exists():
        ledger_path.unlink()
    count = 0
    skipped = 0
    for path in sorted(chunk_dir.glob("*.json")):
        try:
            chunk = load_json(path)
            source = chunk.get("source", {})
            reader = str(chunk.get("reader", "kira"))
            position = chunk.get("position", {})
            title = str(source.get("title", path.stem))
            source_path = str(source.get("source_path", ""))
            reaction_id = str(chunk.get("chunk_id", "")).replace("reading_chunk_", "reading_reaction_")
            reaction_path = f"Data/reading/reactions/{reaction_id}.draft.json"
            append_reading_event(
                reader=reader,
                title=title,
                source_path=source_path,
                position=position,
                chunk_path=path.relative_to(PROJECT_ROOT).as_posix(),
                reaction_path=reaction_path,
                session_path=str(chunk.get("session_id", "")),
                notes=["rebuilt_from_existing_chunk"],
                ledger_path=ledger_path,
            )
            count += 1
        except Exception:
            skipped += 1
    ledger = load_ledger(ledger_path)
    ledger["rebuilt_from_chunks"] = True
    ledger["rebuild_stats"] = {"processed": count, "skipped": skipped}
    write_ledger(ledger, ledger_path)
    print(json.dumps({"ledger": ledger_path.relative_to(PROJECT_ROOT).as_posix(), "processed": count, "skipped": skipped, "entries": len(ledger.get("entries", []))}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
