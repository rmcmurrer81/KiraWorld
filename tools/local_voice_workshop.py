"""Owner CLI for the inactive local Voice Workshop evidence workflow.

This command has no capture, extraction, generation, playback, model-loading,
activation, or default-changing operation.  It validates supplied artifacts
and writes immutable evidence records under Voice/workshop only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.local_voice_workshop import (  # noqa: E402
    VoiceWorkshopError,
    append_candidate_review,
    create_preview_request,
    create_promotion_proposal,
    create_rollback_proposal,
    file_sha256,
    initialize_version,
    inspect_pcm_wav,
    record_owner_approval,
    record_preview_result,
    resolve_project_file,
    select_clean_master,
    validate_permission_record,
    verify_version,
)


def _read_request(value: str) -> dict[str, Any]:
    path = Path(value).expanduser().resolve(strict=True)
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise VoiceWorkshopError("Request JSON must contain one object.")
    return data


def _version_path(value: str) -> Path:
    return Path(value)


def _record_path(version_dir: Path, record: dict[str, Any]) -> Path | None:
    record_type = record.get("record_type")
    identifiers = {
        "voice_workshop_version": ("version_manifest.json", None),
        "candidate_review": ("reviews", "review_id"),
        "clean_master_selection": ("selections", "selection_id"),
        "preview_request": ("previews/requests", "preview_id"),
        "preview_result_receipt": ("previews/results", "result_id"),
        "owner_approval_receipt": ("approvals", "approval_id"),
        "promotion_proposal": ("proposals/promotion", "proposal_id"),
        "rollback_proposal": ("proposals/rollback", "rollback_id"),
    }
    binding = identifiers.get(str(record_type))
    if binding is None:
        return None
    directory, id_key = binding
    base = version_dir if version_dir.is_absolute() else PROJECT_ROOT / version_dir
    if id_key is None:
        return (base / directory).resolve()
    return (base / directory / f"{record[id_key]}.json").resolve()


def _emit(record: dict[str, Any], *, version_dir: Path | None = None) -> None:
    envelope: dict[str, Any] = {"result": record}
    if version_dir is not None:
        path = _record_path(version_dir, record)
        if path is not None and path.is_file():
            envelope["record_path"] = path.relative_to(PROJECT_ROOT).as_posix()
            envelope["record_sha256"] = file_sha256(path)
    print(json.dumps(envelope, indent=2, ensure_ascii=False))


def _run_request_command(
    args: argparse.Namespace,
    operation: Callable[..., dict[str, Any]],
) -> None:
    version_dir = _version_path(args.version_dir)
    result = operation(
        version_dir,
        _read_request(args.request_json),
        project_root=PROJECT_ROOT,
    )
    _emit(result, version_dir=version_dir)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inactive local Voice Workshop evidence CLI (no audio/model/runtime actions)."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser(
        "inspect-wav", help="Read-only technical inspection of one existing project WAV."
    )
    inspect_parser.add_argument("--wav", required=True, help="Project-relative WAV path.")
    inspect_parser.add_argument(
        "--purpose",
        choices=("source", "master_candidate", "preview_output"),
        default="source",
    )

    permission_parser = subparsers.add_parser(
        "validate-permission", help="Read-only validation of one permission request JSON."
    )
    permission_parser.add_argument("--request-json", required=True)

    operations: tuple[tuple[str, str], ...] = (
        ("init-version", "Initialize one immutable inactive evidence version."),
        ("append-review", "Append one human and technical candidate review."),
        ("select-master", "Deterministically select one accepted 6-10 second master."),
        ("create-preview-request", "Create a hash-bound external preview request only."),
        ("record-preview-result", "Record and validate externally produced preview WAVs."),
        ("approve", "Record one exact owner approval without activation."),
        ("propose-promotion", "Create an inactive promotion proposal without applying it."),
        ("propose-rollback", "Create an inactive rollback proposal without applying it."),
    )
    for name, help_text in operations:
        command = subparsers.add_parser(name, help=help_text)
        command.add_argument(
            "--version-dir",
            required=True,
            help="Directory under Voice/workshop whose final name is version_id.",
        )
        command.add_argument("--request-json", required=True)

    verify_parser = subparsers.add_parser(
        "verify", help="Verify immutable records and the append-only history chain."
    )
    verify_parser.add_argument("--version-dir", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect-wav":
            wav = resolve_project_file(
                args.wav, project_root=PROJECT_ROOT, suffixes={".wav"}
            )
            _emit(
                inspect_pcm_wav(
                    wav,
                    project_root=PROJECT_ROOT,
                    purpose=args.purpose,
                )
            )
            return 0
        if args.command == "validate-permission":
            _emit(
                validate_permission_record(
                    _read_request(args.request_json), project_root=PROJECT_ROOT
                )
            )
            return 0
        if args.command == "verify":
            _emit(
                verify_version(
                    _version_path(args.version_dir), project_root=PROJECT_ROOT
                )
            )
            return 0
        operation_map: dict[str, Callable[..., dict[str, Any]]] = {
            "init-version": initialize_version,
            "append-review": append_candidate_review,
            "select-master": select_clean_master,
            "create-preview-request": create_preview_request,
            "record-preview-result": record_preview_result,
            "approve": record_owner_approval,
            "propose-promotion": create_promotion_proposal,
            "propose-rollback": create_rollback_proposal,
        }
        _run_request_command(args, operation_map[args.command])
        return 0
    except (VoiceWorkshopError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "failed_closed", "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
