"""Build an H. H. Holmes source pack for Chicago archivist classes.

This pack is for true-crime/source-verification work. It should be used to
separate documented claims from sensationalized legends, not to promote
fictionalized true-crime claims as memory.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from pypdf import PdfReader


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "Data" / "school" / "source_packs"


SOURCES = [
    {
        "source_id": "holmes_pitezel_case_1896",
        "path": PROJECT_ROOT / "Data" / "library" / "history" / "chicago" / "h_h_holmes" / "the_holmes_pitezel_case.pdf",
        "role": "Holmes/Pitezel primary-era detective account",
        "min_page": 11,
        "keywords": [
            "Holmes committed four murders",
            "Chicago \"Castle\"",
            "Holmes' \" Castle \"",
            "missing children",
            "Pitezel",
            "insurance money",
            "Chicago, Illinois",
            "Truth is Stranger than Fiction",
        ],
    },
    {
        "source_id": "sold_to_satan",
        "path": PROJECT_ROOT / "Data" / "library" / "history" / "chicago" / "h_h_holmes" / "sold_to_satan.pdf",
        "role": "Holmes-related scanned source",
        "keywords": ["Holmes", "Mudgett", "Pitezel", "Chicago", "Castle"],
    },
]


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "")
    text = re.sub(r"([a-z])-\s+([a-z])", r"\1\2", text)
    return text.strip()


def windows(text: str, keywords: Iterable[str], radius: int = 420) -> list[dict]:
    found: list[dict] = []
    lower = text.lower()
    for keyword in keywords:
        start = 0
        keyword_lower = keyword.lower()
        while True:
            index = lower.find(keyword_lower, start)
            if index == -1:
                break
            left = max(0, index - radius)
            right = min(len(text), index + len(keyword) + radius)
            excerpt = clean_text(text[left:right])
            if len(excerpt) >= 220:
                found.append({"keyword": keyword, "excerpt": excerpt})
            start = index + len(keyword)
            if len(found) >= 8:
                return found
    return found


def extract_cards(source: dict, max_pages: int = 140) -> tuple[list[dict], str]:
    path = source["path"]
    if not path.exists():
        return [], "missing"
    reader = PdfReader(str(path))
    cards: list[dict] = []
    pages_with_text = 0
    start_page = max(0, int(source.get("min_page", 1)) - 1)
    for page_index in range(start_page, min(len(reader.pages), max_pages)):
        try:
            page_text = clean_text(reader.pages[page_index].extract_text() or "")
        except Exception:
            continue
        if len(page_text) < 160:
            continue
        if re.search(r"\b(CONTENTS|List of Illustrations)\b", page_text[:360], re.IGNORECASE):
            continue
        pages_with_text += 1
        for hit in windows(page_text, source["keywords"]):
            cards.append(
                {
                    "card_id": f"{source['source_id']}_p{page_index + 1:04d}_{len(cards) + 1:02d}",
                    "source_id": source["source_id"],
                    "source_path": str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                    "role": source["role"],
                    "page": page_index + 1,
                    "keyword": hit["keyword"],
                    "excerpt": hit["excerpt"][:1000],
                    "source_material_remains_source": True,
                    "does_not_create_lived_memory": True,
                }
            )
            break
        if len(cards) >= 10:
            break
    if cards:
        return cards, "usable_text_found"
    if pages_with_text:
        return [], "text_found_but_no_keyword_cards"
    return [], "no_extractable_text_found"


def build_pack() -> dict:
    source_cards: list[dict] = []
    source_status: list[dict] = []
    for source in SOURCES:
        cards, status = extract_cards(source)
        source_cards.extend(cards)
        source_status.append(
            {
                "source_id": source["source_id"],
                "source_path": str(source["path"].relative_to(PROJECT_ROOT)).replace("\\", "/"),
                "status": status,
                "cards_extracted": len(cards),
            }
        )
    return {
        "source_pack_id": "kira_h_h_holmes_chicago_true_crime_source_pack_20260515",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "owner": "kira",
        "status": "active_source_pack_not_memory",
        "purpose": "Add H. H. Holmes as a source-verification / true-crime legend block for Chicago archivist work.",
        "memory_policy": {
            "does_not_create_lived_memory": True,
            "does_not_prove_full_book_reading": True,
            "do_not_treat_sensational_claims_as_fact": True,
            "conversation_use_requires_source_labels": True,
        },
        "source_status": source_status,
        "source_cards": source_cards,
        "teaching_rules": [
            "Holmes in this pack means H. H. Holmes / Herman Webster Mudgett, the real historical criminal connected to the Pitezel case, not Sherlock Holmes.",
            "Do not import Sherlock Holmes details such as Baker Street, Watson, marksmanship, fictional detective methods, or dog-observation deductions.",
            "Holmes may be discussed only from source cards or clearly labeled outside context.",
            "Separate confirmed claims, suspected claims, sensationalized claims, and invented story parts.",
            "Do not claim Holmes killed hundreds unless a source card supports that exact claim and uncertainty is labeled.",
            "Do not treat true-crime material as lived memory or roleplay.",
        ],
    }


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pack = build_pack()
    output_path = OUTPUT_DIR / f"{pack['source_pack_id']}.json"
    output_path.write_text(json.dumps(pack, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(output_path.relative_to(PROJECT_ROOT))
    print(f"cards={len(pack['source_cards'])}")
    for source in pack["source_status"]:
        print(f"{source['source_id']}: {source['status']} cards={source['cards_extracted']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
