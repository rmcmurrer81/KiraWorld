from __future__ import annotations

import unittest

from Core.temporary_ai_variant_identity import (
    LOKI_2012_EXAMPLE,
    validate_variant_identity_record,
)


class TemporaryAIVariantIdentityTests(unittest.TestCase):
    def test_loki_authority_example_is_complete(self) -> None:
        self.assertEqual(validate_variant_identity_record(LOKI_2012_EXAMPLE), [])

    def test_later_branch_events_cannot_become_inherited_autobiography(self) -> None:
        record = dict(LOKI_2012_EXAMPLE)
        record["post_branch_events_inherited_as_autobiography"] = True
        self.assertIn(
            "post-branch events must not be inherited as autobiography",
            validate_variant_identity_record(record),
        )

    def test_source_update_cannot_overwrite_lived_variant_memory(self) -> None:
        record = dict(LOKI_2012_EXAMPLE)
        record["later_source_updates_overwrite_variant_memories"] = True
        self.assertIn(
            "later source updates must never overwrite variant memories",
            validate_variant_identity_record(record),
        )


if __name__ == "__main__":
    unittest.main()
