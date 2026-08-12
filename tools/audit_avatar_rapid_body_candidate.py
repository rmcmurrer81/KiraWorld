#!/usr/bin/env python3
"""Write existing-Avatar-Builder rapid-body workspace and audit records.

This command is an offline record/audit utility.  It does not launch Blender,
start a server, create a user-facing interface, assign a body, or touch runtime
selection files.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.avatar_rapid_body_candidate import (  # noqa: E402
    build_workspace_record,
    evaluate_candidate_package,
    private_roster_entry,
    roster_with_entry,
)


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Create or audit an inactive Avatar Builder rapid-body workspace."
        )
    )
    parser.add_argument(
        "--request",
        required=True,
        help="Project-relative or absolute validated request JSON",
    )
    parser.add_argument(
        "--write-workspace",
        default="",
        help="Write the owner-readable Avatar Builder workspace JSON",
    )
    parser.add_argument(
        "--evidence",
        default="",
        help="Blender build evidence JSON to audit",
    )
    parser.add_argument(
        "--visual-review",
        default="",
        help="Exact-hash independent visual-review JSON",
    )
    parser.add_argument(
        "--topology-audit",
        default="",
        help=(
            "Separately generated exact-candidate topology/intersection "
            "audit JSON"
        ),
    )
    parser.add_argument(
        "--deformation-audit",
        default="",
        help=(
            "Separately generated exact-candidate bounded deformation "
            "audit JSON"
        ),
    )
    parser.add_argument(
        "--write-audit",
        default="",
        help="Write the candidate audit JSON",
    )
    parser.add_argument(
        "--roster",
        default="",
        help=(
            "Append an admitted entry to this existing private inspection "
            "roster; requires --write-audit"
        ),
    )
    args = parser.parse_args()

    root = PROJECT_ROOT.resolve(strict=True)
    request = Path(args.request)
    if not request.is_absolute():
        request = root / request
    request = request.resolve(strict=True)

    output: dict[str, object] = {
        "ok": True,
        "runtime_mutation_performed": False,
        "runtime_assignment_allowed": False,
    }
    if args.write_workspace:
        workspace_path = Path(args.write_workspace)
        if not workspace_path.is_absolute():
            workspace_path = root / workspace_path
        workspace = build_workspace_record(root, request)
        write_json(workspace_path, workspace)
        output["workspace"] = str(workspace_path)

    if args.evidence:
        evidence_path = Path(args.evidence)
        if not evidence_path.is_absolute():
            evidence_path = root / evidence_path
        evidence_path = evidence_path.resolve(strict=True)
        review = None
        if args.visual_review:
            review_path = Path(args.visual_review)
            if not review_path.is_absolute():
                review_path = root / review_path
            review = read_json(review_path.resolve(strict=True))
        topology_audit = None
        topology_audit_path = None
        if args.topology_audit:
            topology_audit_path = Path(args.topology_audit)
            if not topology_audit_path.is_absolute():
                topology_audit_path = root / topology_audit_path
            topology_audit_path = topology_audit_path.resolve(strict=True)
            topology_audit = read_json(topology_audit_path)
        deformation_audit = None
        deformation_audit_path = None
        if args.deformation_audit:
            deformation_audit_path = Path(args.deformation_audit)
            if not deformation_audit_path.is_absolute():
                deformation_audit_path = root / deformation_audit_path
            deformation_audit_path = deformation_audit_path.resolve(
                strict=True
            )
            deformation_audit = read_json(deformation_audit_path)
        audit = evaluate_candidate_package(
            root,
            request,
            evidence_path,
            topology_audit=topology_audit,
            topology_audit_path=topology_audit_path,
            deformation_audit=deformation_audit,
            deformation_audit_path=deformation_audit_path,
            visual_review=review,
        )
        output["audit_status"] = audit["status"]
        output["private_inspection_roster_admission_allowed"] = audit[
            "private_inspection_roster_admission_allowed"
        ]
        output["failure_count"] = len(audit.get("failures", []))
        if args.write_audit:
            audit_path = Path(args.write_audit)
            if not audit_path.is_absolute():
                audit_path = root / audit_path
            write_json(audit_path, audit)
            output["audit"] = str(audit_path)
            if args.roster:
                roster_path = Path(args.roster)
                if not roster_path.is_absolute():
                    roster_path = root / roster_path
                roster = read_json(roster_path)
                entry = private_roster_entry(root, audit_path.resolve(strict=True))
                write_json(roster_path, roster_with_entry(roster, entry))
                output["private_roster"] = str(roster_path)
        elif args.roster:
            raise ValueError("--roster requires --write-audit")

    sys.stdout.write(json.dumps(output, indent=2) + "\n")
    return 0 if output.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
