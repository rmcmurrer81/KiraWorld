import datetime as dt
import unittest

from tools.audit_recent_person_runtime import parse_time


class RecentPersonRuntimeAuditTests(unittest.TestCase):
    def test_parses_zulu_and_rejects_bad_timestamp(self):
        self.assertEqual(
            dt.datetime(2026, 7, 25, tzinfo=dt.timezone.utc),
            parse_time("2026-07-25T00:00:00Z"),
        )
        self.assertIsNone(parse_time("not-a-time"))


if __name__ == "__main__":
    unittest.main()
