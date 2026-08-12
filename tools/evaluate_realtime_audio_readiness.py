"""Evaluate one artifact-bound end-to-end voice-readiness evidence file."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVALUATION_ROOT = PROJECT_ROOT / "Data" / "voice" / "realtime_audio_readiness" / "evaluations"
sys.path.insert(0, str(PROJECT_ROOT))

from Core.realtime_audio_readiness import evaluate_realtime_audio_readiness  # noqa: E402


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _project_relative(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def _bind_evaluation_source(result: dict[str, object], evidence_path: Path) -> dict[str, object]:
    """Bind a saved/printed decision to exact evidence and evaluator bytes."""
    core_path = PROJECT_ROOT / "Core" / "realtime_audio_readiness.py"
    tool_path = Path(__file__).resolve()
    bound = dict(result)
    bound["evaluation_record"] = {
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "source_evidence_path": _project_relative(evidence_path),
        "source_evidence_sha256": _sha256_file(evidence_path),
        "source_evidence_bytes": evidence_path.stat().st_size,
        "profile": result.get("profile"),
        "run_id": result.get("run_id", "unverified_or_missing"),
        "evaluator_core_path": _project_relative(core_path),
        "evaluator_core_sha256": _sha256_file(core_path),
        "evaluator_tool_path": _project_relative(tool_path),
        "evaluator_tool_sha256": _sha256_file(tool_path),
        "immutable_output_required": True,
    }
    return bound


def _has_symlink_component(path: Path, stop: Path) -> bool:
    current = stop.resolve()
    try:
        relative = path.absolute().relative_to(stop.absolute())
    except ValueError:
        return True
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def _resolve_evidence_path(raw: str) -> Path:
    path = Path(raw)
    lexical = path if path.is_absolute() else PROJECT_ROOT / path
    if _has_symlink_component(lexical, PROJECT_ROOT):
        raise ValueError("Evidence path cannot contain a symlink or escape the project root.")
    resolved = lexical.resolve()
    try:
        resolved.relative_to(PROJECT_ROOT.resolve())
    except ValueError as exc:
        raise ValueError("Evidence must remain inside the Kira project root.") from exc
    if not resolved.is_file():
        raise FileNotFoundError(f"Evidence file does not exist: {resolved}")
    return resolved


def _resolve_output_path(raw: str, *, evidence_path: Path) -> Path:
    fragment = Path(raw)
    if fragment.is_absolute():
        lexical = fragment
    else:
        if ".." in fragment.parts:
            raise ValueError("Output cannot traverse parent directories.")
        lexical = EVALUATION_ROOT / fragment
    if lexical.suffix.lower() != ".json":
        raise ValueError("Output must be a JSON file.")
    if _has_symlink_component(lexical, EVALUATION_ROOT):
        raise ValueError("Output cannot contain a symlink or escape the evaluation folder.")
    resolved = lexical.resolve()
    try:
        resolved.relative_to(EVALUATION_ROOT.resolve())
    except ValueError as exc:
        raise ValueError("Output is limited to Data/voice/realtime_audio_readiness/evaluations.") from exc
    if resolved == evidence_path.resolve():
        raise ValueError("Output cannot overwrite the evidence input.")
    if resolved.exists():
        raise FileExistsError(f"Evaluation output already exists and is immutable: {resolved}")
    return resolved


def _write_json_exclusive(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            json.dump(payload, handle, indent=2, ensure_ascii=False, allow_nan=False)
            handle.write("\n")
        # A hard link gives exclusive-create behavior on the same volume; it
        # cannot overwrite an existing evidence/evaluation file.
        os.link(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", help="Project-local JSON evidence file from an instrumented voice run")
    parser.add_argument("--profile", choices=["desktop_live", "immersive_vr"], default="desktop_live")
    parser.add_argument(
        "--output",
        help="Optional new JSON filename below Data/voice/realtime_audio_readiness/evaluations (never overwrites)",
    )
    parser.add_argument(
        "--allow-not-ready-exit-zero",
        action="store_true",
        help="For interactive inspection only; default automation exit is 2 unless status is ready.",
    )
    args = parser.parse_args()

    try:
        evidence_path = _resolve_evidence_path(args.evidence)
        evidence = json.loads(evidence_path.read_text(encoding="utf-8-sig"))
        result = evaluate_realtime_audio_readiness(evidence, args.profile)
        result = _bind_evaluation_source(result, evidence_path)
        if args.output:
            output_path = _resolve_output_path(args.output, evidence_path=evidence_path)
            _write_json_exclusive(output_path, result)
        print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
        if result["status"] == "ready" or args.allow_not_ready_exit_zero:
            return 0
        return 2
    except Exception as exc:
        print(f"REALTIME AUDIO READINESS BLOCKED: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
