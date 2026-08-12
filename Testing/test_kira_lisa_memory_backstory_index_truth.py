from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "System/Docs/KIRA_LISA_MEMORY_BACKSTORY_INDEX_v1.md"


class KiraLisaMemoryBackstoryIndexTruthTests(unittest.TestCase):
    def test_live_store_counts_match_documented_current_status(self) -> None:
        text = INDEX.read_text(encoding="utf-8")
        for person in ("kira", "lisa"):
            records = json.loads(
                (ROOT / f"Data/memories_{person}.json").read_text(encoding="utf-8")
            )
            self.assertIsInstance(records, list)
            noun = "record" if len(records) == 1 else "records"
            self.assertIn(
                f"Data/memories_{person}.json contains {len(records)} {noun}.",
                text,
            )

    def test_index_does_not_repeat_the_obsolete_empty_store_claim(self) -> None:
        text = INDEX.read_text(encoding="utf-8").casefold()
        self.assertNotIn("data/memories_kira.json is empty", text)
        self.assertNotIn("data/memories_lisa.json is empty", text)
        self.assertNotIn("both are empty arrays", text)

    def test_source_draft_reconstruction_and_promoted_memory_stay_distinct(self) -> None:
        text = INDEX.read_text(encoding="utf-8")
        self.assertIn(
            "Every source document, draft seed, reconstruction, and conversation log "
            "is already a promoted live memory.",
            text,
        )
        self.assertIn("Kira/Lisa must not say:", text)
        self.assertIn(
            "Conversation logs are not memory unless reviewed and promoted.",
            text,
        )


if __name__ == "__main__":
    unittest.main()
