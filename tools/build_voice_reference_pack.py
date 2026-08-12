"""CLI for building reviewable voice-reference packs."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
from Core.voice_reference_pipeline import build_local_reference_pack

def main() -> None:
    parser = argparse.ArgumentParser(description="Extract candidate voice clips from local media.")
    parser.add_argument("--target-name", required=True); parser.add_argument("--target-id", default="")
    parser.add_argument("--source", required=True); parser.add_argument("--script", default=""); parser.add_argument("--version", default="")
    parser.add_argument("--authorization-status", choices=["review_required", "owned", "licensed", "authorized", "self_recorded"], default="review_required")
    args = parser.parse_args()
    result = build_local_reference_pack(target_name=args.target_name, target_id=args.target_id or args.target_name, source_path=Path(args.source).resolve(), script_path=Path(args.script).resolve() if args.script else None, authorization_status=args.authorization_status, form_or_version=args.version)
    print(json.dumps(result, indent=2, ensure_ascii=False))
if __name__ == "__main__": main()
