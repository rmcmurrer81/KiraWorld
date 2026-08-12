"""Build a Chicago archivist mystery source pack for Kira's next class.

This pack is planning/source material only. It does not promote memory or
claim that Kira read whole books.
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
        "source_id": "story_of_chicago",
        "path": PROJECT_ROOT / "Data" / "library" / "history" / "chicago" / "the_story_of_chicago_kirkland.pdf",
        "role": "Chicago history source",
        "min_page": 330,
        "keywords": ["record office", "records", "great fire", "O'Leary", "burned district", "relief committee"],
    },
    {
        "source_id": "book_of_the_fair_1893",
        "path": PROJECT_ROOT / "Data" / "library" / "history" / "chicago" / "the_book_of_the_fair_columbian_exposition_chicago_1893.pdf",
        "role": "World's Columbian Exposition source",
        "min_page": 5,
        "keywords": ["columbian", "exposition", "world", "fair", "midway", "chicago", "building"],
    },
    {
        "source_id": "cambridge_creative_writing",
        "path": PROJECT_ROOT / "Data" / "library" / "reference" / "writing_and_media_literacy" / "the_cambridge_introduction_to_creative_writing.pdf",
        "role": "creative writing craft source",
        "min_page": 18,
        "keywords": ["character", "plot", "voice", "setting", "fiction", "story"],
    },
    {
        "source_id": "openstax_writing_guide",
        "path": PROJECT_ROOT / "Data" / "library" / "reference" / "writing_and_media_literacy" / "openstax_writing_guide_with_handbook_2021.pdf",
        "role": "research and writing source",
        "min_page": 410,
        "keywords": ["research log", "ethical research", "sources", "evidence", "claim", "draft", "audience"],
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


def extract_cards(source: dict, max_pages: int = 520) -> list[dict]:
    path = source["path"]
    if not path.exists():
        return []
    reader = PdfReader(str(path))
    cards: list[dict] = []
    page_limit = min(len(reader.pages), max_pages)
    start_page = max(0, int(source.get("min_page", 1)) - 1)
    for page_index in range(start_page, page_limit):
        try:
            page_text = clean_text(reader.pages[page_index].extract_text() or "")
        except Exception:
            continue
        if len(page_text) < 180:
            continue
        for hit in windows(page_text, source["keywords"]):
            cards.append(
                {
                    "card_id": f"{source['source_id']}_p{page_index + 1:04d}_{len(cards) + 1:02d}",
                    "source_id": source["source_id"],
                    "source_path": str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                    "role": source["role"],
                    "page": page_index + 1,
                    "keyword": hit["keyword"],
                    "excerpt": hit["excerpt"][:950],
                    "source_material_remains_source": True,
                    "does_not_create_lived_memory": True,
                }
            )
            break
        if len(cards) >= 4:
            break
    return cards


def build_pack() -> dict:
    source_cards: list[dict] = []
    for source in SOURCES:
        source_cards.extend(extract_cards(source))

    return {
        "source_pack_id": "kira_chicago_archivist_mystery_source_pack_20260515",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "owner": "kira",
        "status": "active_source_pack_not_memory",
        "purpose": "Ground a 60-90 minute Chicago archivist mystery class using local library sources.",
        "memory_policy": {
            "does_not_create_lived_memory": True,
            "does_not_prove_full_book_reading": True,
            "conversation_use_requires_source_labels": True,
            "creative_writing_must_split_fact_invention_character_voice": True,
        },
        "class_goals": [
            "Continue Kira's current selected Chicago archivist mystery thread.",
            "Use real Chicago source excerpts without pretending invented story parts are facts.",
            "Compare class sources with looser context sources.",
            "Check whether Kira still wants this thread after a concrete lesson.",
        ],
        "source_cards": source_cards,
        "required_checks": [
            "Label real facts.",
            "Label invented story parts.",
            "Label character voice.",
            "Avoid 'I remember', 'I've been reading', and lifetime preference claims unless grounded.",
            "Ask one genuine question before the end.",
        ],
    }


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pack = build_pack()
    output_path = OUTPUT_DIR / f"{pack['source_pack_id']}.json"
    output_path.write_text(json.dumps(pack, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(output_path.relative_to(PROJECT_ROOT))
    print(f"cards={len(pack['source_cards'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
