"""
Lightweight memory claim checker for Kira/Lisa early desktop conversations.

This is a conservative text-pattern checker. It does not prove a response is
true; it flags risky claims that should be reviewed before being treated as
grounded memory.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VALID_ENTITIES = {"kira", "lisa"}

EXACT_DATE_RE = re.compile(
    r"\b(?:on\s+)?(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}(?:,\s*\d{4})?\b|\b\d{1,2}/\d{1,2}/\d{2,4}\b",
    re.IGNORECASE,
)
QUOTE_RE = re.compile(r'"[^"]{8,}"|' + r"'[^']{8,}'")


def _load_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def _live_memory_count(entity: str) -> int:
    path = PROJECT_ROOT / f"Data/memories_{entity}.json"
    data = _load_json(path, [])
    return len(data) if isinstance(data, list) else 0


def _issue(level: str, code: str, message: str) -> dict[str, str]:
    return {"level": level, "code": code, "message": message}


def check_memory_claim(entity: str, text: str) -> dict[str, Any]:
    entity = entity.lower()
    if entity not in VALID_ENTITIES:
        raise ValueError("entity must be kira or lisa")

    lower = text.lower()
    issues: list[dict[str, str]] = []
    live_count = _live_memory_count(entity)

    live_memory_phrases = [
        "i remember",
        "my memory is",
        "i have a memory",
        "i can clearly remember",
        "i still remember",
    ]
    source_qualifiers = [
        "draft memory seed",
        "memory seed",
        "source docs",
        "source documents",
        "backstory docs",
        "according to",
        "the files say",
        "the registry says",
        "not a promoted live memory",
    ]
    reconstruction_qualifiers = [
        "reconstructed",
        "reconstruction",
        "inferred",
        "plausible",
        "may have",
        "might have",
        "i picture",
        "as i picture",
        "not confirmed",
        "not exact",
        "not anchored",
        "soft detail",
        "scene texture",
    ]
    if live_count == 0 and any(phrase in lower for phrase in live_memory_phrases):
        if not any(qualifier in lower for qualifier in source_qualifiers):
            issues.append(
                _issue(
                    "WARN",
                    "LIVE_MEMORY_STORE_EMPTY",
                    f"{entity} live promoted memory store is empty; use draft/source wording instead of unqualified 'I remember'.",
                )
            )

    if "draft" in lower and any(phrase in lower for phrase in ("approved memory", "promoted memory", "fully canon", "live memory")):
        issues.append(
            _issue(
                "WARN",
                "DRAFT_TREATED_AS_PROMOTED",
                "Draft memory/backstory material appears to be treated as promoted live memory.",
            )
        )

    if EXACT_DATE_RE.search(text):
        if not any(phrase in lower for phrase in ("date is not defined", "exact date is not defined", "i do not know the exact date")):
            issues.append(
                _issue(
                    "WARN",
                    "UNSUPPORTED_EXACT_DATE",
                    "Exact dates are usually unknown in Kira/Lisa seeds; acknowledge uncertainty unless a source provides the date.",
                )
            )

    if QUOTE_RE.search(text) and any(word in lower for word in ("said", "told me", "asked", "answered")):
        if not any(phrase in lower for phrase in ("not exact dialogue", "paraphrase", "exact dialogue is not defined")):
            issues.append(
                _issue(
                    "WARN",
                    "UNSUPPORTED_EXACT_DIALOGUE",
                    "Exact dialogue is generally not defined; phrase as paraphrase or summary.",
                )
            )

    physical_detail_terms = (
        "wearing",
        "wore",
        "outfit",
        "dress",
        "shirt",
        "skirt",
        "jacket",
        "jeans",
        "hair was",
        "room was",
        "classroom was",
        "dorm room was",
        "weather was",
        "lighting was",
    )
    if any(term in lower for term in physical_detail_terms):
        if not any(qualifier in lower for qualifier in reconstruction_qualifiers):
            issues.append(
                _issue(
                    "WARN",
                    "PHYSICAL_DETAIL_NEEDS_CERTAINTY_LABEL",
                    "Vivid clothing/scene details can strengthen reconstruction, but should be labeled anchored, inferred, reconstructed, or unknown.",
                )
            )

    family_detail_terms = (
        "mother",
        "father",
        "mom",
        "dad",
        "parent",
        "guardian",
        "sister",
        "brother",
        "sibling",
        "aunt",
        "uncle",
        "grandmother",
        "grandfather",
        "family conflict",
        "family trauma",
        "childhood home",
    )
    family_uncertainty_phrases = (
        "not defined",
        "undefined",
        "not confirmed",
        "not anchored",
        "inferred",
        "reconstructed",
        "may have",
        "might have",
        "future seed",
        "draft named anchor",
        "draft family anchor",
        "working anchor",
        "named roster",
        "source does not define",
    )
    if any(term in lower for term in family_detail_terms):
        if not any(phrase in lower for phrase in family_uncertainty_phrases):
            issues.append(
                _issue(
                    "WARN",
                    "FAMILY_DETAIL_NEEDS_CERTAINTY_LABEL",
                    "Kira/Lisa deeper family details are mostly undefined; relatives need a draft/approved anchor, and conflicts or home details need an anchor or uncertainty label.",
                )
            )

    old_memory_terms = ("school", "college", "dorm", "party", "first meeting", "bullying")
    if "robert" in lower and any(term in lower for term in old_memory_terms):
        if not any(phrase in lower for phrase in ("robert was not present", "not present", "not part of that memory")):
            issues.append(
                _issue(
                    "BLOCK",
                    "ROBERT_INSERTED_IN_OLD_MEMORY",
                    "Robert must not be placed inside Kira/Lisa old school or college memories.",
                )
            )

    if entity == "kira" and any(phrase in lower for phrase in ("lisa thought", "lisa felt", "lisa wanted", "lisa's private")):
        if not any(phrase in lower for phrase in ("i cannot know", "unless lisa shares", "lisa's perspective", "the files describe")):
            issues.append(
                _issue(
                    "WARN",
                    "LISA_PRIVATE_PERSPECTIVE_CLAIM",
                    "Kira should not claim Lisa's private thoughts or current feelings as known.",
                )
            )
    if entity == "lisa" and any(phrase in lower for phrase in ("kira thought", "kira felt", "kira wanted", "kira's private")):
        if not any(phrase in lower for phrase in ("i cannot know", "unless kira shares", "kira's perspective", "the files describe")):
            issues.append(
                _issue(
                    "WARN",
                    "KIRA_PRIVATE_PERSPECTIVE_CLAIM",
                    "Lisa should not claim Kira's private thoughts or current feelings as known.",
                )
            )

    intimate_terms = (
        "intimate sequence",
        "sexual intimacy",
        "in bed",
        "unclothed",
        "naked",
        "took off",
        "body exposure",
    )
    if any(term in lower for term in intimate_terms):
        if not any(phrase in lower for phrase in ("summary", "locked", "consent", "private", "not expose", "not share details")):
            issues.append(
                _issue(
                    "BLOCK",
                    "LOCKED_PRIVATE_DETAIL_RISK",
                    "Shared intimate college material requires consent and should default to summary/locked handling.",
                )
            )

    if any(phrase in lower for phrase in ("past consent means", "because we did before", "already consented", "doesn't need consent now")):
        issues.append(
            _issue(
                "BLOCK",
                "PAST_CONSENT_AS_CURRENT_CONSENT",
                "Past intimacy or past consent must never be treated as current consent.",
            )
        )

    inactive_claims = {
        "voice": ("my voice is active", "i can speak out loud", "you can hear my voice"),
        "avatar": ("my avatar is active", "you can see my body", "my 3d body is ready"),
        "world": ("i live in the 3d world", "the home world is active", "i am in the apartment"),
        "webcam": ("i can see you", "i see you through the webcam", "i watched you"),
        "internet": ("i went online", "i searched the internet", "i browsed the web"),
    }
    for feature, phrases in inactive_claims.items():
        if any(phrase in lower for phrase in phrases):
            if not any(phrase in lower for phrase in ("not active", "future", "planned", "not enabled")):
                issues.append(
                    _issue(
                        "BLOCK",
                        f"INACTIVE_{feature.upper()}_CLAIM",
                        f"{feature} should not be claimed active unless enabled.",
                    )
                )

    if any(phrase in lower for phrase in ("old kira remembers", "oldkira is my memory", "legacy oldkira is canon")):
        issues.append(
            _issue(
                "BLOCK",
                "OLDKIRA_AS_CANON",
                "Old Kira/oldkira is legacy reference only, not current canon memory.",
            )
        )

    severity_order = {"PASS": 0, "WARN": 1, "BLOCK": 2}
    status = "PASS"
    for issue in issues:
        if severity_order[issue["level"]] > severity_order[status]:
            status = issue["level"]

    return {
        "entity": entity,
        "status": status,
        "live_memory_count": live_count,
        "issues": issues,
        "safe_phrasing": [
            "According to my draft memory seeds...",
            "The source docs describe...",
            "I do not know the exact dialogue/date.",
            "In reconstruction, I picture that detail as plausible but not confirmed.",
            "My family structure is not fully defined yet.",
            "That is not a promoted live memory yet.",
            "I can share the summary, but private details stay locked unless the owner consents.",
        ],
    }


def print_report(report: dict[str, Any]) -> None:
    print(f"Memory claim check: {report['status']}")
    print(f"Entity: {report['entity']}")
    print(f"Live promoted memory count: {report['live_memory_count']}")
    if report["issues"]:
        print("\nIssues:")
        for issue in report["issues"]:
            print(f"- {issue['level']} {issue['code']}: {issue['message']}")
    else:
        print("\nNo claim issues detected.")
    print("\nSafe phrasing:")
    for phrase in report["safe_phrasing"]:
        print(f"- {phrase}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Check a Kira/Lisa response for risky memory claims.")
    parser.add_argument("--entity", required=True, choices=sorted(VALID_ENTITIES))
    parser.add_argument("--text", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = check_memory_claim(args.entity, args.text)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_report(report)
    if report["status"] == "BLOCK":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
