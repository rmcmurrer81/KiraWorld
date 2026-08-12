from __future__ import annotations

import unittest

from tools.run_temporary_ai_candidate_probe import build_context


class TemporaryAICandidateProbeContextTests(unittest.TestCase):
    def test_beth_probe_binds_reviewed_canon_profile_and_source_pack(self) -> None:
        data, text = build_context("beth_smith_ordinary_temp_20260716")

        self.assertEqual(data["source_pack"]["source_count"], 13)
        profile = data["candidate_profile"]
        self.assertEqual(profile["adaptation_lock"]["selected_identity"], "ordinary domestic Home Beth")
        self.assertEqual(profile["adaptation_lock"]["clone_identity"], "unresolved_in_canon")
        self.assertEqual(profile["adaptation_lock"]["current_survival_state"]["space_beth"], "alive")
        self.assertIn("Do not say Home Beth is the only Beth left.", profile["canon_fact_sheet"]["avoid"])
        self.assertIn("ordinary domestic Home Beth", text)
        self.assertIn("Space Beth did not remain dead", text)


if __name__ == "__main__":
    unittest.main()
