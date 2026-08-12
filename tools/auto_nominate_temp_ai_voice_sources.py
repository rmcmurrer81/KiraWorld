"""One-command, metadata-only TemporaryAI online voice-source nomination."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.temp_ai_online_voice_nomination import (  # noqa: E402
    build_owner_attested_range_review,
    candidate_artifact_paths,
    candidate_owner_review_path,
    request_from_candidate,
    run_online_voice_nomination,
    validate_nomination_request,
    write_json,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Automatically rank exact online voice-source ranges for later bounded analysis. "
            "This stage downloads no media and never trains, clones, assigns, synthesizes, or activates a voice."
        )
    )
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--url", action="append", default=[], help="Exact public video URL; repeat for several sources.")
    parser.add_argument("--start-seconds", type=float, default=0.0)
    parser.add_argument("--end-seconds", type=float)
    parser.add_argument("--owner-nominated-target-only", action="store_true")
    parser.add_argument("--owner-note", default="")
    parser.add_argument("--search-query", action="append", default=[])
    parser.add_argument("--metadata-search", action="store_true")
    parser.add_argument("--machine-evidence", default="", help="Optional exact-bound analyzer-evidence JSON list.")
    parser.add_argument("--local-media", default="", help="Optional already-downloaded project-local media for exact owner-review binding.")
    parser.add_argument("--local-wav", default="", help="Optional exact-range project-local mono PCM WAV for quality diagnostics.")
    parser.add_argument("--owner-attestation", default="", help="Optional exact-bound Robert audiovisual attestation JSON.")
    parser.add_argument("--contamination-evidence", default="", help="Optional exact-bound tonal/music/noise/overlap audit JSON.")
    args = parser.parse_args()

    try:
        search_queries = list(args.search_query)
        metadata_search = bool(args.metadata_search)
        if not args.url and not search_queries:
            # A new TemporaryAI can start from its identity record without
            # making Robert hunt for a first clip.  The search remains bounded
            # by the core provider/result limits and creates nominations only.
            from Core.temp_ai_online_voice_nomination import read_json, resolve_candidate_dir

            candidate_dir = resolve_candidate_dir(args.candidate_id)
            discovery = read_json(candidate_dir / "voice_discovery_request.json", {})
            target = discovery.get("identity_target") if isinstance(discovery.get("identity_target"), dict) else {}
            character = target.get("character") if isinstance(target.get("character"), dict) else {}
            performer = target.get("performer") if isinstance(target.get("performer"), dict) else {}
            target_name = str(character.get("label") or target.get("display_name") or args.candidate_id).strip()
            performer_name = str(performer.get("name") or "").strip()
            search_queries = [
                " ".join(
                    part
                    for part in (
                        target_name,
                        performer_name,
                        "official non musical spoken dialogue scene",
                    )
                    if part
                )
            ]
            metadata_search = True
        request = request_from_candidate(
            args.candidate_id,
            urls=args.url,
            start_seconds=args.start_seconds,
            end_seconds=args.end_seconds,
            owner_nominated_target_only=args.owner_nominated_target_only,
            owner_note=args.owner_note,
            search_queries=search_queries,
        )
        validate_nomination_request(request, expected_candidate_id=args.candidate_id)
        evidence: list[dict] = []
        if args.machine_evidence:
            evidence_path = Path(args.machine_evidence).resolve()
            project_root = PROJECT_ROOT.resolve()
            evidence_path.relative_to(project_root)
            payload = json.loads(evidence_path.read_text(encoding="utf-8"))
            if not isinstance(payload, list):
                raise ValueError("--machine-evidence must contain a JSON list.")
            evidence = payload

        result = run_online_voice_nomination(
            request,
            metadata_search=metadata_search,
            machine_evidence=evidence,
        )
        request_path, result_path = candidate_artifact_paths(args.candidate_id)
        write_json(request_path, request)
        write_json(result_path, result)
        ranked = result["ranked_target_only_candidate_ranges"]
        if not ranked:
            raise ValueError("The bounded metadata search returned no candidate sources.")
        top = ranked[0]
        owner_review_path = None
        owner_review = None
        supplied_review_files = [args.local_media, args.local_wav, args.owner_attestation]
        if any(supplied_review_files) and not all(supplied_review_files):
            raise ValueError("--local-media, --local-wav, and --owner-attestation must be supplied together.")
        if all(supplied_review_files):
            top_range = top["candidate_range"]
            if top_range.get("end_seconds") is None:
                raise ValueError("Provider duration is required for an exact owner-attested range review.")
            owner_review = build_owner_attested_range_review(
                result,
                source_url=top["exact_url"],
                start_seconds=float(top_range["start_seconds"]),
                end_seconds=float(top_range["end_seconds"]),
                local_media_path=args.local_media,
                local_wav_path=args.local_wav,
                owner_attestation_path=args.owner_attestation,
                contamination_evidence_path=args.contamination_evidence or None,
            )
            owner_review_path = candidate_owner_review_path(args.candidate_id)
            write_json(owner_review_path, owner_review)
        print(
            json.dumps(
                {
                    "status": result["status"],
                    "candidate_id": args.candidate_id,
                    "request": request_path.relative_to(PROJECT_ROOT).as_posix(),
                    "result": result_path.relative_to(PROJECT_ROOT).as_posix(),
                    "top_source": top["exact_url"],
                    "top_range": top["candidate_range"],
                    "target_only_approved": False,
                    "owner_range_review": owner_review_path.relative_to(PROJECT_ROOT).as_posix() if owner_review_path else "not requested",
                    "eligible_for_private_reference_pack_input": bool(owner_review and owner_review.get("eligible_for_private_reference_pack_input")),
                    "eligible_for_cleanup_and_qc_workbench": bool(owner_review and owner_review.get("eligible_for_cleanup_and_qc_workbench")),
                    "manual_clip_box_required_now": False,
                    "media_downloaded": False,
                    "voice_trained_or_cloned": False,
                    "voice_assigned": False,
                    "candidate_activated": False,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0
    except Exception as exc:
        print(f"AUTOMATIC VOICE-SOURCE NOMINATION BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
