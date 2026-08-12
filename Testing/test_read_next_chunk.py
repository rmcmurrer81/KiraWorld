import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from read_next_chunk import _extract_pdf_pages, run_read_chunk  # noqa: E402
from slow_reading import build_session  # noqa: E402
from validate_reading_reaction import validate_reading_reaction  # noqa: E402


class ReadNextChunkTests(unittest.TestCase):
    def test_reads_text_chunk_advances_session_and_writes_reaction(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            library = root / "Data" / "library"
            index_path = root / "index.json"
            source = library / "stories" / "demo.md"
            source.parent.mkdir(parents=True)
            source.write_text("\n".join(f"line {index}" for index in range(1, 21)), encoding="utf-8")
            index_path.write_text(
                json.dumps(
                    {
                        "index_id": "test_index",
                        "generated_at": "now",
                        "entries": [
                            {
                                "path": str(source).replace("\\", "/"),
                                "name": "demo.md",
                                "category": "story",
                                "media_type": "document",
                                "library_use": {"can_create_slow_reading_session": True},
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            session_path, session = build_session(
                str(source).replace("\\", "/"),
                "kira",
                index_path=index_path,
                output_dir=root / "sessions",
                unit_type="section",
            )
            session_path.parent.mkdir(parents=True)
            session_path.write_text(json.dumps(session, indent=2), encoding="utf-8")

            result = run_read_chunk(
                session_path,
                chunk_dir=root / "chunks",
                reaction_dir=root / "reactions",
                start_line=1,
                lines=5,
                reaction_summary="Kira read the first five lines.",
            )

            self.assertTrue((root / result["chunk_path"]).exists() or Path(result["chunk_path"]).exists())
            reaction_path = Path(result["reaction_path"])
            if not reaction_path.is_absolute():
                reaction_path = PROJECT_ROOT / reaction_path
            if not reaction_path.exists():
                reaction_path = root / "reactions" / Path(result["reaction_path"]).name
            reaction = json.loads(reaction_path.read_text(encoding="utf-8"))
            self.assertEqual(validate_reading_reaction(reaction), [])
            self.assertIn("Kira read a small piece", reaction["reaction"]["shareable_summary"])
            self.assertTrue(reaction["preference_signal"]["reasons"])
            updated_session = json.loads(session_path.read_text(encoding="utf-8"))
            self.assertIn("lines_0001_0005", updated_session["progress"]["completed_units"])

    def test_pdf_extraction_skips_blank_front_pages(self) -> None:
        class FakePage:
            def __init__(self, text: str) -> None:
                self.text = text

            def extract_text(self) -> str:
                return self.text

        class FakeReader:
            def __init__(self, _path: str) -> None:
                self.pages = [
                    FakePage(""),
                    FakePage("   "),
                    FakePage("French Grammar For Dummies\nAbout the Author"),
                    FakePage("The Parts of Speech\nNouns\nArticles"),
                ]

        with patch.dict("sys.modules", {"pypdf": type("FakePypdf", (), {"PdfReader": FakeReader})}):
            text, position = _extract_pdf_pages(Path("fake.pdf"), 1, 2)

        self.assertIn("French Grammar For Dummies", text)
        self.assertEqual(position["unit_label"], "pages_003_004")
        self.assertEqual(position["skipped_blank_pages"], [1, 2])


if __name__ == "__main__":
    unittest.main()
