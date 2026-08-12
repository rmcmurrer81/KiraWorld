from __future__ import annotations

import io
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import prepare_qwen35_non_body_media_acceptance_v2 as v2  # noqa: E402


class Qwen35NonBodyMediaAcceptanceV2Tests(unittest.TestCase):
    def test_exact_static_v2_contract_passes(self) -> None:
        result = v2.validate_static_v2()
        self.assertEqual(result["status"], "STATIC_V2_BINDINGS_PASS_PENDING_INDEPENDENT_AUDIT")
        self.assertFalse(result["live_execution_authorized"])
        self.assertFalse(result["model_or_media_executed"])
        self.assertFalse(result["experience_or_memory_created"])

    def test_historical_and_current_harness_are_both_pinned_and_distinct(self) -> None:
        result = v2.validate_static_v2()
        self.assertEqual(result["historical_harness_provenance_sha256"], v2.HISTORICAL_MEDIA_HARNESS_SHA256)
        self.assertEqual(result["current_harness_sha256"], v2.CURRENT_MEDIA_HARNESS_SHA256)
        self.assertTrue(result["historical_and_current_harness_are_distinct"])

    def test_current_harness_exact_qwen_identity_is_parsed_without_import(self) -> None:
        source = v2._read_exact(v2.BINDINGS["current_media_harness"], "current")
        self.assertEqual(v2._literal_assignment(source, "EXACT_QWEN_MODEL"), v2.EXACT_MODEL)
        self.assertEqual(v2._literal_assignment(source, "EXACT_QWEN_DIGEST"), v2.EXACT_DIGEST)

    def test_exact_four_library_sources_are_rehashed(self) -> None:
        result = v2.validate_static_v2()
        self.assertEqual(len(result["exact_sources"]), 4)
        self.assertEqual(len({item["stimulus_id"] for item in result["exact_sources"]}), 4)
        self.assertTrue(all(item["path"].startswith("Data/library/") for item in result["exact_sources"]))

    def test_v2_config_equals_derived_contract(self) -> None:
        config = v2.load_and_validate_config()
        self.assertEqual(config["derived_contract"], v2.validate_static_v2())
        self.assertFalse(config["execution_allowed"])

    def test_duplicate_json_keys_fail_closed(self) -> None:
        with self.assertRaisesRegex(v2.Qwen35MediaV2Error, "duplicate JSON key"):
            json.loads('{"status":"safe","status":"forged"}', object_pairs_hook=v2._strict_object)

    def test_default_cli_is_static_descriptor_only(self) -> None:
        output = io.StringIO()
        with patch("sys.stdout", output):
            self.assertEqual(v2.main([]), 0)
        value = json.loads(output.getvalue())
        self.assertFalse(value["execution_allowed"])

    def test_live_flag_is_rejected(self) -> None:
        with self.assertRaisesRegex(SystemExit, "not authorized"):
            v2.main(["--execute-live"])


if __name__ == "__main__":
    unittest.main()
