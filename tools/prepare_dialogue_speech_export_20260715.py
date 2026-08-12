"""Create an immutable, spoken-only export for safe local TTS review."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.dialogue_privacy import build_spoken_only_export, clone_with_reparsed_sections


def _immutable_json_artifact(
    output_dir: Path,
    *,
    artifact_stem: str,
    value: Any,
) -> tuple[Path, str]:
    """Publish JSON at a full-content-hash path without replacing anything.

    ``x`` mode makes creation exclusive.  A pre-existing file is reusable only
    when every byte is identical; a hash-address collision or a corrupted prior
    artifact fails closed and is left untouched.
    """

    payload = (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    path = output_dir / f"{artifact_stem}.sha256-{digest}.json"
    created = False
    try:
        try:
            with path.open("xb") as handle:
                created = True
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
        except FileExistsError:
            if path.read_bytes() != payload:
                raise RuntimeError(
                    f"Refusing to replace non-identical hash-addressed artifact: {path}"
                )
    except Exception:
        # Only remove a partial file created by this invocation.  Never remove
        # or repair a pre-existing artifact, even when it is corrupt.
        if created:
            try:
                path.unlink()
            except FileNotFoundError:
                pass
        raise
    return path, digest


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("dialogue_json", type=Path)
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "Data" / "dialogues" / "kira_robert_intro" / "speech_exports")
    parser.add_argument("--write-reparsed-review-copy", action="store_true")
    args = parser.parse_args()

    source = args.dialogue_json
    if not source.is_absolute():
        source = PROJECT_ROOT / source
    output_dir = args.output_dir if args.output_dir.is_absolute() else PROJECT_ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    data = json.loads(source.read_text(encoding="utf-8-sig"))

    export = build_spoken_only_export(data, source_path=source)
    out, out_sha256 = _immutable_json_artifact(
        output_dir,
        artifact_stem=f"{source.stem}_spoken_only_privacy_checked",
        value=export,
    )

    result = {
        "spoken_only_export": _display_path(out),
        "spoken_only_export_sha256": out_sha256,
        "privacy_audit": export["privacy_audit"],
        "source_unchanged": True,
    }
    if args.write_reparsed_review_copy:
        repaired, counts = clone_with_reparsed_sections(data)
        repaired_path, repaired_sha256 = _immutable_json_artifact(
            output_dir,
            artifact_stem=f"{source.stem}_reparsed_review_copy",
            value=repaired,
        )
        result["reparsed_review_copy"] = _display_path(repaired_path)
        result["reparsed_review_copy_sha256"] = repaired_sha256
        result["reparsed_counts"] = counts
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
