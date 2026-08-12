import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = PROJECT_ROOT / "tools"
sys.path.insert(0, str(TOOLS_ROOT))

from create_fuzzy_memory_thread import append_thread, load_threads, make_thread, validate_thread  # noqa: E402


class FuzzyMemoryThreadTests(unittest.TestCase):
    def test_thread_allows_conflicting_soft_perspectives(self) -> None:
        thread = make_thread(
            "Kira and Lisa remember a shirt color differently.",
            [
                {
                    "owner": "kira",
                    "claim": "pink shirt",
                    "certainty": "low_to_medium",
                    "allowed_language": "I remember it as pink, but I might be filling in the edge.",
                },
                {
                    "owner": "lisa",
                    "claim": "blue shirt",
                    "certainty": "low_to_medium",
                    "allowed_language": "It feels blue to me, unless my brain is showing off.",
                },
            ],
            ["objective shirt color"],
        )

        self.assertEqual(validate_thread(thread), [])
        self.assertEqual(thread["canon_status"], "soft_reconstructive_memory")

    def test_append_thread_preserves_policy(self) -> None:
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "threads.json"
            thread = make_thread(
                "Kira pictures an old kitchen differently over time.",
                [
                    {
                        "owner": "kira",
                        "claim": "warm kitchen light",
                        "certainty": "low",
                        "allowed_language": "I picture it with warm light, but that is soft memory.",
                    }
                ],
                ["exact kitchen layout"],
            )

            data = append_thread(thread, path)
            loaded = load_threads(path)

            self.assertTrue(data["policy"]["conflicting_perspectives_allowed"])
            self.assertEqual(len(loaded["threads"]), 1)


if __name__ == "__main__":
    unittest.main()
