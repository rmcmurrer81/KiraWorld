from __future__ import annotations

import unittest

from Core.world_shell_session_policy import resolve_world_shell_session_policy


GIB = 1024**3


class WorldShellSessionPolicyTests(unittest.TestCase):
    def test_default_remains_one_even_on_128_gb_machine(self) -> None:
        policy = resolve_world_shell_session_policy({}, total_ram_bytes=128 * GIB)

        self.assertEqual(policy.effective_max_active_sessions, 1)
        self.assertFalse(policy.group_sessions_enabled)
        self.assertEqual(policy.reason, "group_sessions_require_explicit_opt_in")

    def test_32_gb_machine_stays_at_one_after_opt_in(self) -> None:
        policy = resolve_world_shell_session_policy(
            {
                "KIRA_WORLD_GROUP_SESSIONS": "1",
                "KIRA_WORLD_MAX_ACTIVE_SESSIONS": "4",
            },
            total_ram_bytes=32 * GIB,
        )

        self.assertEqual(policy.hardware_max_active_sessions, 1)
        self.assertEqual(policy.effective_max_active_sessions, 1)
        self.assertFalse(policy.group_sessions_enabled)
        self.assertEqual(policy.reason, "hardware_capacity_allows_only_one_session")

    def test_128_gb_machine_can_explicitly_opt_into_four(self) -> None:
        policy = resolve_world_shell_session_policy(
            {
                "KIRA_WORLD_GROUP_SESSIONS": "true",
                "KIRA_WORLD_MAX_ACTIVE_SESSIONS": "4",
            },
            total_ram_bytes=128 * GIB,
        )

        self.assertEqual(policy.hardware_max_active_sessions, 4)
        self.assertEqual(policy.effective_max_active_sessions, 4)
        self.assertTrue(policy.group_sessions_enabled)
        self.assertFalse(policy.as_dict()["activation_performed"])

    def test_request_is_capped_by_hardware(self) -> None:
        policy = resolve_world_shell_session_policy(
            {
                "KIRA_WORLD_GROUP_SESSIONS": "on",
                "KIRA_WORLD_MAX_ACTIVE_SESSIONS": "8",
            },
            total_ram_bytes=96 * GIB,
        )

        self.assertEqual(policy.hardware_max_active_sessions, 3)
        self.assertEqual(policy.effective_max_active_sessions, 3)

    def test_missing_or_invalid_inputs_fail_closed(self) -> None:
        missing_ram = resolve_world_shell_session_policy(
            {
                "KIRA_WORLD_GROUP_SESSIONS": "yes",
                "KIRA_WORLD_MAX_ACTIVE_SESSIONS": "4",
            },
            total_ram_bytes=0,
        )
        invalid_limit = resolve_world_shell_session_policy(
            {
                "KIRA_WORLD_GROUP_SESSIONS": "1",
                "KIRA_WORLD_MAX_ACTIVE_SESSIONS": "everyone",
            },
            total_ram_bytes=128 * GIB,
        )

        self.assertEqual(missing_ram.effective_max_active_sessions, 1)
        self.assertEqual(invalid_limit.effective_max_active_sessions, 1)
        self.assertEqual(invalid_limit.reason, "invalid_capacity_configuration_fail_closed")


if __name__ == "__main__":
    unittest.main()
