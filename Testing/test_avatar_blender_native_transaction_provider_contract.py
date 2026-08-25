"""Hostile static tests for the two-stage native transaction request.

The suite opens/hashes existing closure inputs only.  It never calls a
provider or native API, creates a claim/authorization, launches Blender, or
writes a carrier/body/output.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path, PureWindowsPath
import sys
from types import MappingProxyType
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core import avatar_blender_carrier_transaction_closure as closure
from Core import avatar_blender_native_provider_contract as native_contract
from Core import avatar_blender_native_transaction_provider_contract as transaction
from Core import avatar_blender_preimport_controller as preimport


PROVIDER_ID = "review_candidate_transaction_provider_v1"
RUN_ID = "carrier_transaction_20260825"
CLAIM_ROOT = rf"C:\KiraNativeTransactions\{RUN_ID}"
CLAIM_PATH = rf"{CLAIM_ROOT}\attempt.claim.json"
OUTCOME_PATH = rf"{CLAIM_ROOT}\attempt.outcome.json"
DIRECTORY_PATHS = (
    "C:\\",
    r"C:\KiraNativeTransactions",
    CLAIM_ROOT,
)
HOSTILE_WIN32_COMPONENT_TOKENS = (
    "<",
    ">",
    ":",
    '"',
    "/",
    "|",
    "?",
    "*",
    *(chr(value) for value in range(0x20)),
)
EXPECTED_DOS_DEVICE_NAMES = frozenset(
    {
        "CON",
        "CONIN$",
        "CONOUT$",
        "CLOCK$",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{index}" for index in range(1, 10)),
        *(f"LPT{index}" for index in range(1, 10)),
        *(f"COM{index}" for index in "¹²³"),
        *(f"LPT{index}" for index in "¹²³"),
    }
)


def _unchecked_path_digests(value: str) -> tuple[str, str]:
    """Mirror digest algorithms without accepting the path grammar."""

    private_digest = hashlib.sha256(value.encode("utf-16le")).hexdigest()
    parsed = value[4:] if value.startswith("\\\\?\\") else value
    canonical = str(PureWindowsPath(parsed)).casefold()
    canonical_digest = hashlib.sha256(canonical.encode("utf-16le")).hexdigest()
    return private_digest, canonical_digest


def _unchecked_directory_binding(
    directory_paths: tuple[str, ...],
) -> dict[str, object]:
    digest_pairs = tuple(_unchecked_path_digests(value) for value in directory_paths)
    lexical_digests = tuple(pair[0] for pair in digest_pairs)
    canonical_digests = tuple(pair[1] for pair in digest_pairs)
    chain_sha256 = native_contract.canonical_sha256(
        [
            {
                "depth": index,
                "final_path_sha256": digest,
                "canonical_path_sha256": canonical_digest,
            }
            for index, (digest, canonical_digest) in enumerate(digest_pairs)
        ]
    )
    return {
        "directory_paths": directory_paths,
        "directory_path_sha256": lexical_digests,
        "directory_canonical_path_sha256": canonical_digests,
        "directory_chain_sha256": chain_sha256,
    }


def _unchecked_namespace_binding(
    *,
    directory_paths: tuple[str, ...],
    claim_root_path: str,
    claim_path: str,
    outcome_path: str,
) -> dict[str, object]:
    values = _unchecked_directory_binding(directory_paths)
    root_lexical, root_canonical = _unchecked_path_digests(claim_root_path)
    claim_lexical, claim_canonical = _unchecked_path_digests(claim_path)
    outcome_lexical, outcome_canonical = _unchecked_path_digests(outcome_path)
    values.update(
        {
            "claim_root_path": claim_root_path,
            "claim_root_path_sha256": root_lexical,
            "claim_root_canonical_path_sha256": root_canonical,
            "claim_path": claim_path,
            "claim_path_sha256": claim_lexical,
            "claim_canonical_path_sha256": claim_canonical,
            "outcome_path": outcome_path,
            "outcome_path_sha256": outcome_lexical,
            "outcome_canonical_path_sha256": outcome_canonical,
        }
    )
    return values


def _environment() -> dict[str, str]:
    return {
        "SystemRoot": r"C:\Windows",
        "WINDIR": r"C:\Windows",
        "ComSpec": r"C:\Windows\System32\cmd.exe",
        "PATH": r"C:\Windows\System32",
        "TEMP": r"C:\Temp",
        "TMP": r"C:\Temp",
    }


def _command(
    policy: preimport.ControllerPolicy,
    authorization_path: Path,
) -> tuple[str, ...]:
    by_role = policy.by_role
    return (
        str(by_role["blender_executable"].path.resolve(strict=True)),
        *preimport.REQUIRED_BLENDER_FLAGS,
        "--python",
        str(by_role["worker_script"].path.resolve(strict=True)),
        "--",
        "--config",
        str(by_role["config"].path.resolve(strict=True)),
        "--authorization",
        str(authorization_path.absolute()),
    )


class AvatarBlenderNativeTransactionProviderContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.closure_record = dict(closure.load_machine_static_transaction_closure())
        cls.output_paths = {
            value["role"]: str(PROJECT_ROOT / value["relative_path"])
            for value in cls.closure_record["outputs"]
        }
        authorization_path = Path(cls.output_paths["one_run_authorization"])
        cls.build_command = _command(
            preimport.load_machine_policy(operation="build"),
            authorization_path,
        )
        cls.audit_command = _command(
            preimport.load_machine_policy(operation="audit"),
            authorization_path,
        )
        cls.request = cls._request()

    @classmethod
    def _request(cls, **overrides: object) -> transaction.NativeCarrierTransactionRequest:
        values: dict[str, object] = {
            "closure_record": cls.closure_record,
            "provider_id": PROVIDER_ID,
            "run_id": RUN_ID,
            "build_command": cls.build_command,
            "audit_command": cls.audit_command,
            "environment": _environment(),
            "working_directory": str(PROJECT_ROOT),
            "output_paths": cls.output_paths,
            "directory_paths": DIRECTORY_PATHS,
            "claim_root_path": CLAIM_ROOT,
            "claim_path": CLAIM_PATH,
            "outcome_path": OUTCOME_PATH,
            "build_timeout_ms": 60 * 60 * 1000,
            "audit_timeout_ms": 30 * 60 * 1000,
        }
        values.update(overrides)
        return transaction.build_native_transaction_request(**values)  # type: ignore[arg-type]

    def test_machine_closure_binds_one_private_two_stage_request(self) -> None:
        request = self.request
        receipt = dict(transaction.validate_native_transaction_request(request))
        self.assertEqual(transaction.STAGE_ORDER, tuple(x.stage_id for x in request.stages))
        self.assertEqual(
            ("build_worker", "audit_worker"),
            tuple(x.worker_role for x in request.stages),
        )
        self.assertFalse(request.stages[0].candidate_custody_required_before_launch)
        self.assertTrue(request.stages[1].candidate_custody_required_before_launch)
        self.assertEqual(transaction.OUTPUT_ORDER, tuple(x.role for x in request.outputs))
        self.assertEqual(
            tuple(closure.TRANSACTION_STAGES),
            request.transaction_phases,
        )
        self.assertEqual(
            len(request.directory_paths),
            len(set(request.directory_canonical_path_sha256)),
        )
        self.assertEqual(
            request.claim_root_canonical_path_sha256,
            request.directory_canonical_path_sha256[-1],
        )
        self.assertTrue(receipt["exact_two_stage_shape_valid"])
        self.assertTrue(receipt["private_payload_digest_bindings_valid"])
        self.assertFalse(receipt["provider_invocation_authorized"])
        self.assertFalse(receipt["blender_execution_authorized"])
        self.assertFalse(receipt["body_created"])

    def test_safe_record_redacts_every_private_payload_value(self) -> None:
        record = self.request.safe_record()
        serialized = json.dumps(record, sort_keys=True)
        self.assertNotIn("C:\\\\", serialized)
        self.assertNotIn("\\\\?\\", serialized)
        self.assertNotIn(str(PROJECT_ROOT), serialized)
        self.assertNotIn("command", record["stages"][0])
        self.assertNotIn("path", record["outputs"][0])
        self.assertNotIn("environment", record)
        self.assertNotIn("person_id", serialized)
        self.assertNotIn("body_owner", serialized)
        self.assertTrue(all(value is False for value in record["authority"].values()))

    def test_contract_does_not_change_controller_review_or_execution_boundary(self) -> None:
        self.assertEqual(frozenset(), preimport.REVIEWED_NATIVE_PROVIDER_IDS)
        evidence = transaction.static_contract_evidence_record()
        self.assertFalse(evidence["native_provider_reviewed"])
        self.assertFalse(evidence["provider_invocation_authorized"])
        self.assertFalse(evidence["operating_system_evidence_verified"])
        self.assertFalse(evidence["blender_execution_authorized"])
        self.assertFalse(evidence["short_name_alias_identity_verified"])
        self.assertFalse(evidence["reparse_identity_verified"])
        self.assertFalse(evidence["hardlink_identity_verified"])
        self.assertIn(
            "ASCII_LOCAL_DRIVE_ONLY",
            evidence["windows_component_grammar"],
        )
        self.assertIn(
            "NO_WIN32_FORBIDDEN_OR_CONTROL_CHARACTERS",
            evidence["windows_component_grammar"],
        )
        self.assertEqual(
            preimport.NATIVE_PROVIDER_INTERFACE,
            evidence["source_single_launch_interface"],
        )
        self.assertNotEqual(
            evidence["provider_interface"],
            evidence["source_single_launch_interface"],
        )

    def test_private_command_substitution_and_stage_swap_fail_closed(self) -> None:
        with self.assertRaisesRegex(
            transaction.NativeTransactionProviderContractError,
            "commands differ|commands alias",
        ):
            self._request(build_command=self.audit_command)
        with self.assertRaisesRegex(
            transaction.NativeTransactionProviderContractError,
            "commands differ|commands alias",
        ):
            self._request(
                build_command=self.audit_command,
                audit_command=self.build_command,
            )

    def test_private_output_substitution_fails_before_provider_invocation(self) -> None:
        outputs = dict(self.output_paths)
        outputs["audit_report"] = outputs["build_report"]
        with self.assertRaisesRegex(
            transaction.NativeTransactionProviderContractError,
            "audit_report private path|output paths alias",
        ):
            self._request(output_paths=outputs)

    def test_hostile_claim_namespaces_fail_closed_without_creating_them(self) -> None:
        native_drive_root = "\\\\?\\C:\\"
        cases = (
            {"claim_path": OUTCOME_PATH},
            {
                "claim_root_path": r"\\server\share\claims",
                "claim_path": r"\\server\share\claims\attempt.claim.json",
                "outcome_path": r"\\server\share\claims\attempt.outcome.json",
                "directory_paths": (r"\\server\share", r"\\server\share\claims"),
            },
            {
                "directory_paths": (
                    "C:\\",
                    r"C:\KiraNativeTransactions\skipped",
                    CLAIM_ROOT,
                )
            },
            {"directory_paths": (*DIRECTORY_PATHS, CLAIM_ROOT)},
            {"directory_paths": (CLAIM_ROOT,)},
            {
                "directory_paths": (
                    r"C:\KiraNativeTransactions",
                    CLAIM_ROOT,
                )
            },
            {
                "directory_paths": ("C:\\", native_drive_root),
                "claim_root_path": native_drive_root,
                "claim_path": native_drive_root + "attempt.claim.json",
                "outcome_path": native_drive_root + "attempt.outcome.json",
            },
        )
        for values in cases:
            with self.subTest(values=values), self.assertRaises(
                transaction.NativeTransactionProviderContractError
            ):
                self._request(**values)

    def test_builder_rejects_windows_path_normalization_aliases(self) -> None:
        self.assertEqual(EXPECTED_DOS_DEVICE_NAMES, transaction.DOS_DEVICE_NAMES)
        hostile_values: list[dict[str, object]] = [
            {"claim_path": OUTCOME_PATH + "."},
            {"claim_path": OUTCOME_PATH + " "},
            {"claim_path": OUTCOME_PATH + "::$DATA"},
            {"working_directory": str(PROJECT_ROOT) + "."},
        ]
        output_alias = dict(self.output_paths)
        output_alias["audit_report"] = output_alias["candidate_blend"] + "."
        hostile_values.append({"output_paths": output_alias})
        device_root = r"C:\NUL"
        hostile_values.append(
            {
                "directory_paths": ("C:\\", device_root),
                "claim_root_path": device_root,
                "claim_path": device_root + r"\attempt.claim.json",
                "outcome_path": device_root + r"\attempt.outcome.json",
            }
        )
        for device_name in sorted(EXPECTED_DOS_DEVICE_NAMES):
            hostile_values.append(
                {"claim_path": CLAIM_ROOT + rf"\{device_name}.json"}
            )
            hostile_values.append(
                {"outcome_path": CLAIM_ROOT + rf"\{device_name.lower()}.TxT"}
            )
        for values in hostile_values:
            with self.subTest(values=values), self.assertRaisesRegex(
                transaction.NativeTransactionProviderContractError,
                "forbidden Windows path component",
            ):
                self._request(**values)

    def test_builder_rejects_full_win32_path_grammar_across_roles(self) -> None:
        for token in HOSTILE_WIN32_COMPONENT_TOKENS:
            component = f"bad{token}name"
            output_paths = dict(self.output_paths)
            output_paths["audit_report"] = rf"C:\Rejected\{component}.json"
            hostile_root = rf"C:\KiraNativeTransactions\{component}"
            cases: tuple[dict[str, object], ...] = (
                {"claim_path": CLAIM_ROOT + rf"\{component}.json"},
                {"outcome_path": CLAIM_ROOT + rf"\{component}.json"},
                {"working_directory": rf"C:\Rejected\{component}"},
                {"output_paths": output_paths},
                {
                    "directory_paths": (
                        "C:\\",
                        r"C:\KiraNativeTransactions",
                        hostile_root,
                    ),
                    "claim_root_path": hostile_root,
                    "claim_path": hostile_root + r"\attempt.claim.json",
                    "outcome_path": hostile_root + r"\attempt.outcome.json",
                },
            )
            for values in cases:
                with self.subTest(
                    token=repr(token),
                    role=next(iter(values)),
                ), self.assertRaises(
                    transaction.NativeTransactionProviderContractError
                ):
                    self._request(**values)

    def test_builder_rejects_non_ascii_or_nonletter_drive_designators(self) -> None:
        for prefix in ("", "\\\\?\\"):
            for designator in ("1:", "?:", "É:"):
                drive_root = f"{prefix}{designator}\\"
                hostile_root = f"{drive_root}Rejected"
                output_paths = dict(self.output_paths)
                output_paths["audit_report"] = hostile_root + r"\audit.json"
                cases: tuple[dict[str, object], ...] = (
                    {"claim_path": hostile_root + r"\attempt.claim.json"},
                    {"outcome_path": hostile_root + r"\attempt.outcome.json"},
                    {"working_directory": hostile_root},
                    {"output_paths": output_paths},
                    {
                        "directory_paths": (drive_root, hostile_root),
                        "claim_root_path": hostile_root,
                        "claim_path": hostile_root + r"\attempt.claim.json",
                        "outcome_path": hostile_root + r"\attempt.outcome.json",
                    },
                )
                for values in cases:
                    with self.subTest(
                        prefix=prefix,
                        designator=designator,
                        role=next(iter(values)),
                    ), self.assertRaisesRegex(
                        transaction.NativeTransactionProviderContractError,
                        "ASCII local drive designator",
                    ):
                        self._request(**values)

    def test_hostile_safe_record_mutations_fail_closed(self) -> None:
        base = self.request.safe_record()
        mutations: list[dict[str, object]] = []

        one_stage = deepcopy(base)
        one_stage["stages"] = one_stage["stages"][:1]
        mutations.append(one_stage)

        reversed_stages = deepcopy(base)
        reversed_stages["stages"].reverse()
        mutations.append(reversed_stages)

        aliased_stage = deepcopy(base)
        aliased_stage["stages"][1]["argv_sha256"] = aliased_stage["stages"][0][
            "argv_sha256"
        ]
        mutations.append(aliased_stage)

        early_audit = deepcopy(base)
        early_audit["stages"][1]["candidate_custody_required_before_launch"] = False
        mutations.append(early_audit)

        pid_identity = deepcopy(base)
        pid_identity["stages"][0]["pid_process_identity_forbidden"] = False
        mutations.append(pid_identity)

        early_publication = deepcopy(base)
        early_publication["outputs"][0]["path_publication_before_terminal"] = True
        mutations.append(early_publication)

        output_alias = deepcopy(base)
        output_alias["outputs"][3]["canonical_path_sha256"] = output_alias[
            "outputs"
        ][1]["canonical_path_sha256"]
        mutations.append(output_alias)

        canonical_directory_alias = deepcopy(base)
        canonical_directory_alias["directory_canonical_path_sha256"][1] = (
            canonical_directory_alias["directory_canonical_path_sha256"][0]
        )
        mutations.append(canonical_directory_alias)

        claim_alias = deepcopy(base)
        claim_alias["outcome_path_sha256"] = claim_alias["claim_path_sha256"]
        mutations.append(claim_alias)

        canonical_claim_alias = deepcopy(base)
        canonical_claim_alias["outcome_canonical_path_sha256"] = (
            canonical_claim_alias["claim_canonical_path_sha256"]
        )
        mutations.append(canonical_claim_alias)

        phase_reorder = deepcopy(base)
        phase_reorder["transaction_phases"][3:5] = reversed(
            phase_reorder["transaction_phases"][3:5]
        )
        mutations.append(phase_reorder)

        authority = deepcopy(base)
        authority["authority"]["body_created"] = True
        mutations.append(authority)

        legacy_interface = deepcopy(base)
        legacy_interface["interface_version"] = preimport.NATIVE_PROVIDER_INTERFACE
        mutations.append(legacy_interface)

        extra_key = deepcopy(base)
        extra_key["provider_claimed_success"] = True
        mutations.append(extra_key)

        for mutated in mutations:
            with self.subTest(keys=set(mutated)), self.assertRaises(
                transaction.NativeTransactionProviderContractError
            ):
                transaction.validate_static_native_transaction_request_record(mutated)

    def test_authority_mapping_is_immutable_inside_the_request(self) -> None:
        self.assertIsInstance(self.request.authority, MappingProxyType)
        with self.assertRaises(TypeError):
            self.request.authority["body_created"] = True  # type: ignore[index]
        hostile_authority = dict(self.request.authority)
        hostile_authority["body_created"] = True
        with self.assertRaises(transaction.NativeTransactionProviderContractError):
            replace(
                self.request,
                authority=MappingProxyType(hostile_authority),
            )

    def test_private_source_closure_bytes_cannot_be_replaced_or_reformatted(self) -> None:
        with self.assertRaises(transaction.NativeTransactionProviderContractError):
            replace(
                self.request,
                source_closure_canonical_json=(
                    self.request.source_closure_canonical_json + b" "
                ),
            )
        with self.assertRaises(transaction.NativeTransactionProviderContractError):
            replace(
                self.request,
                source_closure_sha256="0" * 64,
            )

    def test_replaced_private_claim_or_outcome_cannot_escape_bound_root(self) -> None:
        for role in ("claim", "outcome"):
            outside_path = (
                rf"C:\OutsideNativeTransaction\attempt.{role}.json"
            )
            replacements = {
                f"{role}_path": outside_path,
                f"{role}_path_sha256": (
                    native_contract.private_windows_path_sha256(outside_path)
                ),
                f"{role}_canonical_path_sha256": (
                    native_contract.canonical_windows_path_sha256(outside_path)
                ),
            }
            with self.subTest(role=role), self.assertRaisesRegex(
                transaction.NativeTransactionProviderContractError,
                "outside the claim root",
            ):
                replace(self.request, **replacements)

    def test_replaced_private_directory_chain_cannot_skip_an_ancestor(self) -> None:
        noncontiguous_directories = ("C:\\", CLAIM_ROOT)
        lexical_digests = tuple(
            native_contract.private_windows_path_sha256(value)
            for value in noncontiguous_directories
        )
        canonical_digests = tuple(
            native_contract.canonical_windows_path_sha256(value)
            for value in noncontiguous_directories
        )
        chain_sha256 = native_contract.canonical_sha256(
            [
                {
                    "depth": index,
                    "final_path_sha256": digest,
                    "canonical_path_sha256": canonical_digest,
                }
                for index, (digest, canonical_digest) in enumerate(
                    zip(lexical_digests, canonical_digests)
                )
            ]
        )
        with self.assertRaisesRegex(
            transaction.NativeTransactionProviderContractError,
            "not contiguous",
        ):
            replace(
                self.request,
                directory_paths=noncontiguous_directories,
                directory_path_sha256=lexical_digests,
                directory_canonical_path_sha256=canonical_digests,
                directory_chain_sha256=chain_sha256,
            )

    def test_replaced_private_directory_chain_cannot_omit_drive_prefix(self) -> None:
        cases = (
            (CLAIM_ROOT,),
            (r"C:\KiraNativeTransactions", CLAIM_ROOT),
        )
        for truncated_directories in cases:
            lexical_digests = tuple(
                native_contract.private_windows_path_sha256(value)
                for value in truncated_directories
            )
            canonical_digests = tuple(
                native_contract.canonical_windows_path_sha256(value)
                for value in truncated_directories
            )
            chain_sha256 = native_contract.canonical_sha256(
                [
                    {
                        "depth": index,
                        "final_path_sha256": digest,
                        "canonical_path_sha256": canonical_digest,
                    }
                    for index, (digest, canonical_digest) in enumerate(
                        zip(lexical_digests, canonical_digests)
                    )
                ]
            )
            with self.subTest(
                directories=truncated_directories
            ), self.assertRaisesRegex(
                transaction.NativeTransactionProviderContractError,
                "does not begin at the local drive root",
            ):
                replace(
                    self.request,
                    directory_paths=truncated_directories,
                    directory_path_sha256=lexical_digests,
                    directory_canonical_path_sha256=canonical_digests,
                    directory_chain_sha256=chain_sha256,
                )

    def test_replaced_private_paths_reject_windows_alias_grammar(self) -> None:
        for role in ("claim", "outcome"):
            original = getattr(self.request, f"{role}_path")
            hostile_paths = (
                original + ".",
                original + " ",
                original + "::$DATA",
                CLAIM_ROOT + r"\CON.json",
                CLAIM_ROOT + r"\com1.txt",
                *(
                    CLAIM_ROOT + rf"\{device_name.lower()}.TxT"
                    for device_name in sorted(EXPECTED_DOS_DEVICE_NAMES)
                ),
            )
            for hostile_path in hostile_paths:
                replacements = {
                    f"{role}_path": hostile_path,
                    f"{role}_path_sha256": (
                        native_contract.private_windows_path_sha256(hostile_path)
                    ),
                    f"{role}_canonical_path_sha256": (
                        native_contract.canonical_windows_path_sha256(hostile_path)
                    ),
                }
                with self.subTest(
                    role=role,
                    hostile_path=hostile_path,
                ), self.assertRaisesRegex(
                    transaction.NativeTransactionProviderContractError,
                    "forbidden Windows path component",
                ):
                    replace(self.request, **replacements)

        hostile_working_directory = str(PROJECT_ROOT) + "."
        with self.assertRaisesRegex(
            transaction.NativeTransactionProviderContractError,
            "forbidden Windows path component",
        ):
            replace(
                self.request,
                working_directory=hostile_working_directory,
                working_directory_sha256=(
                    native_contract.private_windows_path_sha256(
                        hostile_working_directory
                    )
                ),
            )

        device_root = r"C:\NUL"
        device_directories = ("C:\\", device_root)
        lexical_digests = tuple(
            native_contract.private_windows_path_sha256(value)
            for value in device_directories
        )
        canonical_digests = tuple(
            native_contract.canonical_windows_path_sha256(value)
            for value in device_directories
        )
        chain_sha256 = native_contract.canonical_sha256(
            [
                {
                    "depth": index,
                    "final_path_sha256": digest,
                    "canonical_path_sha256": canonical_digest,
                }
                for index, (digest, canonical_digest) in enumerate(
                    zip(lexical_digests, canonical_digests)
                )
            ]
        )
        device_claim = device_root + r"\attempt.claim.json"
        device_outcome = device_root + r"\attempt.outcome.json"
        with self.assertRaisesRegex(
            transaction.NativeTransactionProviderContractError,
            "forbidden Windows path component",
        ):
            replace(
                self.request,
                directory_paths=device_directories,
                directory_path_sha256=lexical_digests,
                directory_canonical_path_sha256=canonical_digests,
                directory_chain_sha256=chain_sha256,
                claim_root_path=device_root,
                claim_root_path_sha256=lexical_digests[-1],
                claim_root_canonical_path_sha256=canonical_digests[-1],
                claim_path=device_claim,
                claim_path_sha256=(
                    native_contract.private_windows_path_sha256(device_claim)
                ),
                claim_canonical_path_sha256=(
                    native_contract.canonical_windows_path_sha256(device_claim)
                ),
                outcome_path=device_outcome,
                outcome_path_sha256=(
                    native_contract.private_windows_path_sha256(device_outcome)
                ),
                outcome_canonical_path_sha256=(
                    native_contract.canonical_windows_path_sha256(device_outcome)
                ),
            )

    def test_replaced_private_paths_reject_full_win32_path_grammar(self) -> None:
        for token in HOSTILE_WIN32_COMPONENT_TOKENS:
            component = f"bad{token}name"
            for role in ("claim", "outcome"):
                hostile_path = CLAIM_ROOT + rf"\{component}.json"
                lexical_digest, canonical_digest = _unchecked_path_digests(
                    hostile_path
                )
                with self.subTest(
                    token=repr(token),
                    role=role,
                ), self.assertRaises(
                    transaction.NativeTransactionProviderContractError
                ):
                    replace(
                        self.request,
                        **{
                            f"{role}_path": hostile_path,
                            f"{role}_path_sha256": lexical_digest,
                            f"{role}_canonical_path_sha256": canonical_digest,
                        },
                    )

            hostile_working_directory = rf"C:\Rejected\{component}"
            working_digest, _ = _unchecked_path_digests(
                hostile_working_directory
            )
            with self.subTest(
                token=repr(token),
                role="working_directory",
            ), self.assertRaises(
                transaction.NativeTransactionProviderContractError
            ):
                replace(
                    self.request,
                    working_directory=hostile_working_directory,
                    working_directory_sha256=working_digest,
                )

            hostile_output = rf"C:\Rejected\{component}.json"
            output_lexical, output_canonical = _unchecked_path_digests(
                hostile_output
            )
            with self.subTest(
                token=repr(token),
                role="output",
            ), self.assertRaises(
                transaction.NativeTransactionProviderContractError
            ):
                replace(
                    self.request.outputs[-1],
                    path=hostile_output,
                    path_sha256=output_lexical,
                    canonical_path_sha256=output_canonical,
                )

            hostile_root = rf"C:\KiraNativeTransactions\{component}"
            replacements = _unchecked_namespace_binding(
                directory_paths=(
                    "C:\\",
                    r"C:\KiraNativeTransactions",
                    hostile_root,
                ),
                claim_root_path=hostile_root,
                claim_path=hostile_root + r"\attempt.claim.json",
                outcome_path=hostile_root + r"\attempt.outcome.json",
            )
            with self.subTest(
                token=repr(token),
                role="directory_namespace",
            ), self.assertRaises(
                transaction.NativeTransactionProviderContractError
            ):
                replace(self.request, **replacements)

    def test_replaced_private_paths_reject_invalid_drive_designators(self) -> None:
        for prefix in ("", "\\\\?\\"):
            for designator in ("1:", "?:", "É:"):
                drive_root = f"{prefix}{designator}\\"
                hostile_root = f"{drive_root}Rejected"
                replacements = _unchecked_namespace_binding(
                    directory_paths=(drive_root, hostile_root),
                    claim_root_path=hostile_root,
                    claim_path=hostile_root + r"\attempt.claim.json",
                    outcome_path=hostile_root + r"\attempt.outcome.json",
                )
                with self.subTest(
                    prefix=prefix,
                    designator=designator,
                    role="directory_namespace",
                ), self.assertRaisesRegex(
                    transaction.NativeTransactionProviderContractError,
                    "ASCII local drive designator",
                ):
                    replace(self.request, **replacements)

                working_digest, _ = _unchecked_path_digests(hostile_root)
                with self.subTest(
                    prefix=prefix,
                    designator=designator,
                    role="working_directory",
                ), self.assertRaisesRegex(
                    transaction.NativeTransactionProviderContractError,
                    "ASCII local drive designator",
                ):
                    replace(
                        self.request,
                        working_directory=hostile_root,
                        working_directory_sha256=working_digest,
                    )

                hostile_output = hostile_root + r"\audit.json"
                output_lexical, output_canonical = _unchecked_path_digests(
                    hostile_output
                )
                with self.subTest(
                    prefix=prefix,
                    designator=designator,
                    role="output",
                ), self.assertRaisesRegex(
                    transaction.NativeTransactionProviderContractError,
                    "ASCII local drive designator",
                ):
                    replace(
                        self.request.outputs[-1],
                        path=hostile_output,
                        path_sha256=output_lexical,
                        canonical_path_sha256=output_canonical,
                    )


if __name__ == "__main__":
    unittest.main()
