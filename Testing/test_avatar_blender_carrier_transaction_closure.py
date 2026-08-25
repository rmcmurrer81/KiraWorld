"""Static tests for the complete inactive-carrier transaction closure.

These tests open and hash existing inputs only.  They never launch Blender,
call a provider, create an authorization/claim, or write a body/output.
"""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core import avatar_blender_carrier_transaction_closure as closure
from Core import avatar_blender_native_provider_contract as native_contract
from Core import avatar_blender_preimport_controller as preimport


class AvatarBlenderCarrierTransactionClosureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.record = dict(closure.load_machine_static_transaction_closure())

    def test_machine_closure_binds_all_inputs_and_two_distinct_stages(self) -> None:
        record = self.record
        self.assertEqual(closure.CLOSURE_SCHEMA, record["schema"])
        self.assertEqual(closure.CLOSURE_STATUS, record["status"])
        self.assertEqual(18, record["input_count"])
        self.assertEqual(
            closure.EXPECTED_PROJECT_ROLES | closure.EXPECTED_INSTALLED_ROLES,
            {value["role"] for value in record["inputs"]},
        )
        self.assertEqual(
            closure.EXPECTED_OUTPUT_ROLES,
            {value["role"] for value in record["outputs"]},
        )
        self.assertNotEqual(record["build_argv_sha256"], record["audit_argv_sha256"])
        self.assertTrue(record["commands_share_exact_blender_config_and_authorization"])
        self.assertTrue(record["commands_use_distinct_bound_workers"])
        self.assertTrue(record["two_stage_transaction_required"])
        self.assertTrue(record["all_reserved_outputs_absent"])

    def test_record_is_private_path_free_and_all_authority_is_false(self) -> None:
        serialized = json.dumps(self.record, sort_keys=True)
        self.assertNotIn("C:\\\\", serialized)
        self.assertNotIn("\\\\?\\", serialized)
        self.assertNotIn(str(PROJECT_ROOT), serialized)
        self.assertFalse(self.record["authorization_present"])
        self.assertFalse(self.record["native_claim_root_selected"])
        self.assertFalse(self.record["native_claim_created"])
        self.assertFalse(self.record["operating_system_handle_evidence_verified"])
        self.assertTrue(self.record["native_provider_interface_is_single_launch_only"])
        self.assertFalse(self.record["native_transaction_interface_available"])
        self.assertTrue(all(value is False for value in self.record["authority"].values()))

    def test_installed_blender_and_long_source_are_exactly_bound(self) -> None:
        by_role = {value["role"]: value for value in self.record["inputs"]}
        self.assertEqual(
            "1e6624af112b3c936f4b038b025ebd2bf00ae72c4b62881a6787166d71c58fa5",
            by_role["blender_executable"]["sha256"],
        )
        self.assertEqual(108687824, by_role["blender_executable"]["bytes"])
        self.assertEqual(
            "af4f5e1e3b5efb618fc496ccacb9b527aaa834e6a48e6c17d824f207bbafea7e",
            by_role["bundled_interpreter"]["sha256"],
        )
        self.assertEqual(
            "3911419c44681d25f33892122e61206f1f4651bb78b3e403e377d1ed099cde2f",
            by_role["source_blend"]["sha256"],
        )
        self.assertGreater(len(by_role["source_blend"]["relative_path"]), 150)
        self.assertEqual(1, by_role["source_blend"]["link_count"])

    def test_record_mutations_fail_closed(self) -> None:
        mutations = []
        authority = deepcopy(self.record)
        authority["authority"]["body_created"] = True
        mutations.append(authority)
        provider = deepcopy(self.record)
        provider["native_transaction_interface_available"] = True
        mutations.append(provider)
        authorization = deepcopy(self.record)
        authorization["authorization_present"] = True
        mutations.append(authorization)
        input_hash = deepcopy(self.record)
        input_hash["inputs"][0]["sha256"] = "0" * 64
        mutations.append(input_hash)
        raw_path = deepcopy(self.record)
        raw_path["inputs"][0]["relative_path"] = r"C:\private\input"
        raw_path["input_closure_sha256"] = native_contract.canonical_sha256(
            raw_path["inputs"]
        )
        mutations.append(raw_path)
        wrong_scope = deepcopy(self.record)
        wrong_scope["inputs"][0]["scope"] = "blender_installation"
        wrong_scope["input_closure_sha256"] = native_contract.canonical_sha256(
            wrong_scope["inputs"]
        )
        mutations.append(wrong_scope)
        stages = deepcopy(self.record)
        stages["transaction_stages"] = stages["transaction_stages"][:-1]
        mutations.append(stages)
        outputs = deepcopy(self.record)
        outputs["outputs"][0]["currently_absent"] = False
        outputs["all_reserved_outputs_absent"] = False
        mutations.append(outputs)
        for mutation in mutations:
            with self.subTest(keys=set(mutation)), self.assertRaises(
                closure.CarrierTransactionClosureError
            ):
                closure.validate_static_transaction_closure_record(mutation)

    def test_policy_stage_substitution_is_rejected_without_opening_a_process(self) -> None:
        build = preimport.load_machine_policy(operation="build")
        with self.assertRaisesRegex(
            closure.CarrierTransactionClosureError,
            "policy order",
        ):
            closure.build_static_transaction_closure(
                build_policy=build,
                audit_policy=build,
            )


if __name__ == "__main__":
    unittest.main()
