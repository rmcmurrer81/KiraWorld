from __future__ import annotations

from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
import re
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from jsonschema import Draft202012Validator, ValidationError

from standalone.schema_tools import schema_validator
from standalone.validate_hanson_intake import (
    MAX_JSON_BYTES,
    MAX_JSON_DEPTH,
    IntakeInputError,
    IntakeReferenceError,
    load_and_validate,
    main,
    strict_json_loads,
    validate_references,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
INTAKE_ROOT = PROJECT_ROOT / "hanson_interface_intake"
SOURCE_ID = "official-source-1"
OFFICIAL_SOURCE = {
    "source_id": SOURCE_ID,
    "source_kind": "public_documentation",
    "title": "Synthetic test-only interface reference",
    "reference": "https://example.invalid/official-reference",
    "revision": "revision-1",
    "publication_clearance": "public_or_authorized_for_repository",
}

# Test-only placeholders exercise reachability of the strict final gate. They are
# never emitted as a handoff and assert no real Hanson package, interface, or value.


def confirmation(status: str = "confirmed_official") -> dict:
    return {
        "status": status,
        "source_ids": [SOURCE_ID] if status != "provided_unverified" else [],
    }


def sourced_text(value: str) -> dict:
    return {"status": "confirmed_official", "value": value, "source_ids": [SOURCE_ID]}


def sourced_list(values: list[str]) -> dict:
    return {
        "status": "confirmed_official",
        "values": values,
        "source_ids": [SOURCE_ID],
    }


def sourced_integer(value: int) -> dict:
    return {"status": "confirmed_official", "value": value, "source_ids": [SOURCE_ID]}


def qos_profile(channel: str = "topic") -> dict:
    return {
        "confirmation": confirmation(),
        "channel": channel,
        "reliability": "reliable",
        "durability": "volatile",
        "history": "keep_last",
        "depth": 10,
        "deadline_ms": 1000,
        "lifespan_ms": 5000,
        "liveliness": "automatic",
        "lease_duration_ms": 3000,
        "notes": None,
    }


def interface_entry(interface_id: str, role: str) -> dict:
    return {
        "interface_id": interface_id,
        "confirmation": confirmation(),
        "capability": role,
        "kind": "topic",
        "direction": "bidirectional",
        "package_id": "official-package",
        "ros_type": "official_interfaces/Example",
        "endpoint_name": f"official/{interface_id}",
        "qos_profiles": [qos_profile()],
        "request_id_field": "request_id",
        "correlation_fields": ["request_id"],
        "frame_ids": ["official-frame"],
        "unit_ids": ["official-unit"],
        "acknowledgement_semantics": "Official acknowledgement",
        "completion_semantics": "Official terminal status",
        "cancellation_semantics": "Official cancellation",
        "notes": None,
    }


def _mark_unresolved_not_applicable(value: object) -> None:
    if isinstance(value, dict):
        if value.get("status") == "unresolved" and "source_ids" in value:
            value["status"] = "not_applicable_confirmed"
            value["source_ids"] = [SOURCE_ID]
            if "value" in value:
                value["value"] = None
            if "values" in value:
                value["values"] = []
        for child in value.values():
            _mark_unresolved_not_applicable(child)
    elif isinstance(value, list):
        for child in value:
            _mark_unresolved_not_applicable(child)


def complete_official_intake(template: dict) -> dict:
    intake = deepcopy(template)
    intake["official_sources"] = [deepcopy(OFFICIAL_SOURCE)]
    _mark_unresolved_not_applicable(intake)
    intake["intake_status"] = "hanson_reviewed"

    environment = intake["target_environment"]
    for field, value in {
        "ros_2_distribution": "Official ROS 2 distribution",
        "ros_2_patch_release": "Official patch release",
        "operating_system": "Official operating system",
        "architecture": "Official architecture",
        "python_version": "Official Python version",
        "rmw_implementation": "Official RMW implementation",
        "time_source": "Official simulator time source",
        "clock_synchronization": "Official clock synchronization rule",
    }.items():
        environment[field] = sourced_text(value)
    simulator = environment["simulator"]
    for field, value in {
        "product_name": "Official simulator product",
        "version": "Official simulator version",
        "access_method": "Authorized simulator access",
        "launch_package": "official_simulator_package",
        "launch_file_or_executable": "official_simulator_launch",
        "fixture": "Official isolated fixture",
        "readiness_signal": "Official readiness signal",
        "shutdown_procedure": "Official shutdown procedure",
    }.items():
        simulator[field] = sourced_text(value)
    simulator["launch_arguments"] = sourced_list([])

    intake["packages"] = {
        "confirmation": confirmation(),
        "entries": [
            {
                "package_id": "official-package",
                "confirmation": confirmation(),
                "official_name": "synthetic_test_package",
                "version_or_commit": "official-version",
                "distribution_reference": "https://example.invalid/package",
                "license_identifier": "Official license identifier",
                "purpose": "Official simulator interfaces",
            }
        ],
    }
    intake["frames"] = {
        "confirmation": confirmation(),
        "entries": [
            {
                "frame_id": "official-frame",
                "confirmation": confirmation(),
                "official_name": "official_frame",
                "parent_frame_id": None,
                "transform_authority": "Official transform authority",
                "handedness": "right_handed",
                "coordinate_convention": "Official coordinate convention",
                "availability_semantics": "Official availability semantics",
            }
        ],
    }
    intake["units"] = {
        "confirmation": confirmation(),
        "entries": [
            {
                "unit_id": "official-unit",
                "confirmation": confirmation(),
                "quantity": "official quantity",
                "official_unit_name": "official unit",
                "symbol": "ou",
                "scale_to_si": 1.0,
                "offset_to_si": 0.0,
            }
        ],
    }
    intake["limits"] = {
        "confirmation": confirmation(),
        "entries": [
            {
                "limit_id": "cross-limit",
                "confirmation": confirmation(),
                "capability": "cross_cutting",
                "field_or_quantity": "official normalized magnitude",
                "lower_bound": 0.0,
                "upper_bound": 1.0,
                "unit_id": "official-unit",
                "enforcement_component": "Official simulator authority",
                "violation_outcome": "reject",
                "notes": None,
            }
        ],
    }

    roles = (
        "speech",
        "gaze",
        "expression",
        "gesture",
        "execution_status",
        "capability_discovery",
        "session_management",
        "session_liveness",
        "safety_state",
    )
    intake["interfaces"] = {
        "confirmation": confirmation(),
        "entries": [interface_entry(f"{role}-interface", role) for role in roles],
    }

    for capability_name, capability in intake["capabilities"].items():
        capability["confirmation"] = confirmation()
        capability["interface_ids"] = sourced_list([f"{capability_name}-interface"])
        capability["official_vocabulary"] = sourced_list([f"official-{capability_name}"])
        capability["frame_ids"] = sourced_list(["official-frame"])
        capability["unit_ids"] = sourced_list(["official-unit"])
        capability["limit_ids"] = sourced_list(["cross-limit"])
        capability["queueing_semantics"] = sourced_text("Official queueing semantics")
        capability["concurrency_semantics"] = sourced_text("Official concurrency semantics")
        capability["preemption_semantics"] = sourced_text("Official preemption semantics")
        capability["completion_semantics"] = sourced_text("Official completion semantics")

    lifecycle = intake["lifecycle_semantics"]
    lifecycle["confirmation"] = confirmation()
    lifecycle["status_interface_ids"] = sourced_list(["execution_status-interface"])
    lifecycle["official_request_id_field"] = sourced_text("request_id")
    lifecycle["correlation_fields"] = sourced_list(["request_id"])
    lifecycle["status_ordering"] = sourced_text("Official monotonic status ordering")
    terminal_states = {
        "completed",
        "rejected",
        "failed",
        "cancelled",
        "interrupted",
        "expired",
    }
    for state_name in (
        "request_admission",
        "requested",
        "accepted",
        "started",
        "completed",
        "rejected",
        "failed",
        "cancelled",
        "interrupted",
        "expired",
    ):
        lifecycle[state_name] = {
            "confirmation": confirmation(),
            "official_state_or_outcome": sourced_text(f"OFFICIAL_{state_name.upper()}"),
            "official_event_field": sourced_text("state"),
            "terminal": state_name in terminal_states,
            "meaning": sourced_text(f"Official {state_name} meaning"),
            "late_event_handling": sourced_text("Official late-event handling"),
        }

    session = intake["session_and_liveness"]
    session["confirmation"] = confirmation()
    session["capability_discovery_interface_ids"] = sourced_list(
        ["capability_discovery-interface"]
    )
    session["session_interface_ids"] = sourced_list(["session_management-interface"])
    session["heartbeat_interface_ids"] = sourced_list(["session_liveness-interface"])
    for field in (
        "authentication_semantics",
        "one_active_session_fencing",
        "disconnect_detection",
        "in_flight_disconnect_outcome",
        "reconnect_semantics",
        "replacement_semantics",
        "retry_and_idempotency_semantics",
    ):
        session[field] = sourced_text(f"Official {field}")
    session["session_ttl_ms"] = sourced_integer(5000)
    session["heartbeat_period_ms"] = sourced_integer(1000)
    session["heartbeat_timeout_ms"] = sourced_integer(3000)

    safety = intake["safety_semantics"]
    safety["confirmation"] = confirmation()
    safety["authoritative_physical_safety_component"] = sourced_text(
        "Official simulator safety authority"
    )
    for safeguard_name in (
        "emergency_stop",
        "watchdog",
        "degraded_mode",
        "collision_or_safe_stop",
        "recovery",
    ):
        safety[safeguard_name] = {
            "confirmation": confirmation(),
            "interface_ids": sourced_list(["safety_state-interface"]),
            "official_states": sourced_list([f"OFFICIAL_{safeguard_name.upper()}"]),
            "trigger_semantics": sourced_text("Official trigger semantics"),
            "physical_outcome": sourced_text("Official physical outcome"),
            "recovery_semantics": sourced_text("Official recovery semantics"),
        }

    intake["review"]["hanson_review_disposition"] = sourced_text(
        "Reviewed against the named official interface sources"
    )
    return intake


def load_json(name: str) -> dict:
    value = strict_json_loads((INTAKE_ROOT / name).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{name} must contain a JSON object")
    return value


class HansonInterfaceIntakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = load_json("official-hanson-interface-intake.schema.json")
        cls.template = load_json("official-hanson-interface-intake.template.json")
        cls.validator = schema_validator(cls.schema)

    def test_schema_and_unresolved_template_are_valid(self) -> None:
        Draft202012Validator.check_schema(self.schema)
        self.validator.validate(self.template)
        validate_references(self.template)

    def test_all_committed_json_is_strict(self) -> None:
        for path in sorted(PROJECT_ROOT.rglob("*.json")):
            with self.subTest(path=path.relative_to(PROJECT_ROOT)):
                strict_json_loads(path.read_text(encoding="utf-8"))
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            strict_json_loads('{"field": 1, "field": 2}')
        with self.assertRaisesRegex(ValueError, "nonfinite JSON literal"):
            strict_json_loads('{"field": NaN}')
        with self.assertRaisesRegex(ValueError, "nonfinite JSON number"):
            strict_json_loads('{"field": 1e9999}')

    def test_every_declared_object_schema_is_closed(self) -> None:
        def walk(value: object) -> None:
            if isinstance(value, dict):
                if value.get("type") == "object":
                    self.assertIs(value.get("additionalProperties"), False)
                for child in value.values():
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)

        walk(self.schema)

    def test_unknown_root_and_nested_fields_fail_closed(self) -> None:
        intake = deepcopy(self.template)
        intake["guessed_hanson_topic"] = "/not/official"
        with self.assertRaises(ValidationError):
            self.validator.validate(intake)

        intake = deepcopy(self.template)
        intake["target_environment"]["simulator"]["shell_command"] = "launch"
        with self.assertRaises(ValidationError):
            self.validator.validate(intake)

    def test_unresolved_value_cannot_hide_a_guess(self) -> None:
        intake = deepcopy(self.template)
        intake["target_environment"]["ros_2_distribution"]["value"] = "guessed"
        with self.assertRaises(ValidationError):
            self.validator.validate(intake)

    def test_confirmed_value_requires_an_official_source(self) -> None:
        intake = deepcopy(self.template)
        field = intake["target_environment"]["ros_2_distribution"]
        field["status"] = "confirmed_official"
        field["value"] = "example"
        with self.assertRaises(ValidationError):
            self.validator.validate(intake)

    def test_duplicate_and_dangling_ids_are_rejected(self) -> None:
        intake = deepcopy(self.template)
        source = deepcopy(OFFICIAL_SOURCE)
        intake["official_sources"] = [source, deepcopy(source)]
        self.validator.validate(intake)
        with self.assertRaisesRegex(IntakeReferenceError, "duplicate source id"):
            validate_references(intake)

        intake = deepcopy(self.template)
        intake["capabilities"]["speech"]["confirmation"] = {
            "status": "provided_unverified",
            "source_ids": [],
        }
        intake["capabilities"]["speech"]["interface_ids"] = {
            "status": "provided_unverified",
            "values": ["missing-interface"],
            "source_ids": [],
        }
        self.validator.validate(intake)
        with self.assertRaisesRegex(IntakeReferenceError, "unknown interface id"):
            validate_references(intake)

    def test_require_official_reports_unresolved_fields(self) -> None:
        claimed_run = deepcopy(self.template)
        claimed_run["intake_status"] = "simulator_validated_for_named_versions"
        with self.assertRaises(ValidationError):
            self.validator.validate(claimed_run)

        with self.assertRaisesRegex(IntakeReferenceError, "Hanson-reviewed intake status"):
            validate_references(self.template, require_official=True)

        intake = deepcopy(self.template)
        intake["intake_status"] = "hanson_reviewed"
        with self.assertRaises(ValidationError):
            self.validator.validate(intake)
        with self.assertRaisesRegex(IntakeReferenceError, "official_sources"):
            validate_references(intake, require_official=True)

    def test_complete_official_intake_passes_strict_gate(self) -> None:
        intake = complete_official_intake(self.template)
        self.validator.validate(intake)
        validate_references(intake)
        validate_references(intake, require_official=True)

        simulator_shape = deepcopy(intake)
        simulator_shape["intake_status"] = "simulator_validated_for_named_versions"
        simulator_shape["review"]["simulator_evidence"] = {
            "status": "passed_for_named_versions",
            "commit_sha": "c" * 40,
            "run_record_reference": "https://example.invalid/synthetic-test-run",
            "completed_at_utc": "2020-01-01T00:00:00Z",
        }
        self.validator.validate(simulator_shape)
        validate_references(simulator_shape)

    def test_false_promotion_and_reverse_status_are_rejected(self) -> None:
        promoted = deepcopy(self.template)
        promoted["official_sources"] = [deepcopy(OFFICIAL_SOURCE)]
        _mark_unresolved_not_applicable(promoted)
        promoted["intake_status"] = "simulator_validated_for_named_versions"
        promoted["review"]["simulator_evidence"] = {
            "status": "passed_for_named_versions",
            "commit_sha": "a" * 40,
            "run_record_reference": "https://example.invalid/run",
            "completed_at_utc": "2026-08-18T12:00:00Z",
        }
        with self.assertRaises(ValidationError):
            self.validator.validate(promoted)
        with self.assertRaises(IntakeReferenceError):
            validate_references(promoted, require_official=True)

        false_review = deepcopy(promoted)
        false_review["intake_status"] = "hanson_reviewed"
        false_review["review"]["simulator_evidence"] = {
            "status": "not_run",
            "commit_sha": None,
            "run_record_reference": None,
            "completed_at_utc": None,
        }
        with self.assertRaises(ValidationError):
            self.validator.validate(false_review)
        with self.assertRaises(IntakeReferenceError):
            validate_references(false_review)

        reverse = deepcopy(self.template)
        reverse["review"]["simulator_evidence"] = {
            "status": "passed_for_named_versions",
            "commit_sha": "b" * 40,
            "run_record_reference": "https://example.invalid/run",
            "completed_at_utc": "2026-08-18T12:00:00Z",
        }
        with self.assertRaises(ValidationError):
            self.validator.validate(reverse)
        with self.assertRaisesRegex(IntakeReferenceError, "inconsistent"):
            validate_references(reverse)

    def test_lifecycle_terminality_is_coupled_and_unresolved_is_empty(self) -> None:
        for state_name, wrong_terminal in (
            ("requested", True),
            ("completed", False),
            ("failed", False),
        ):
            with self.subTest(state=state_name):
                intake = complete_official_intake(self.template)
                intake["lifecycle_semantics"][state_name]["terminal"] = wrong_terminal
                with self.assertRaises(ValidationError):
                    self.validator.validate(intake)

        unresolved = deepcopy(self.template)
        unresolved["lifecycle_semantics"]["requested"]["terminal"] = True
        with self.assertRaises(ValidationError):
            self.validator.validate(unresolved)

    def test_unresolved_containers_cannot_hide_resolved_children(self) -> None:
        attacks = []

        catalog = complete_official_intake(self.template)
        catalog["interfaces"]["confirmation"] = {
            "status": "unresolved",
            "source_ids": [],
        }
        attacks.append(catalog)

        capability = complete_official_intake(self.template)
        capability["capabilities"]["speech"]["confirmation"] = {
            "status": "unresolved",
            "source_ids": [],
        }
        attacks.append(capability)

        lifecycle = complete_official_intake(self.template)
        lifecycle["lifecycle_semantics"]["confirmation"] = {
            "status": "unresolved",
            "source_ids": [],
        }
        attacks.append(lifecycle)

        session = complete_official_intake(self.template)
        session["session_and_liveness"]["confirmation"] = {
            "status": "unresolved",
            "source_ids": [],
        }
        attacks.append(session)

        safety = complete_official_intake(self.template)
        safety["safety_semantics"]["confirmation"] = {
            "status": "unresolved",
            "source_ids": [],
        }
        attacks.append(safety)

        for index, intake in enumerate(attacks):
            with self.subTest(attack=index):
                with self.assertRaises(ValidationError):
                    self.validator.validate(intake)

    def test_timer_order_and_numeric_bounds_are_enforced(self) -> None:
        intake = complete_official_intake(self.template)
        session = intake["session_and_liveness"]
        session["heartbeat_period_ms"] = sourced_integer(4000)
        session["heartbeat_timeout_ms"] = sourced_integer(3000)
        session["session_ttl_ms"] = sourced_integer(2000)
        self.validator.validate(intake)
        with self.assertRaisesRegex(IntakeReferenceError, "period <= timeout <= TTL"):
            validate_references(intake)

        for value in (0, 86_400_001):
            with self.subTest(value=value):
                bounded = complete_official_intake(self.template)
                bounded["session_and_liveness"]["heartbeat_period_ms"] = sourced_integer(
                    value
                )
                with self.assertRaises(ValidationError):
                    self.validator.validate(bounded)

    def test_unresolved_qos_and_kind_channel_mismatch_are_rejected(self) -> None:
        unresolved = complete_official_intake(self.template)
        qos = unresolved["interfaces"]["entries"][0]["qos_profiles"][0]
        qos["confirmation"] = {"status": "unresolved", "source_ids": []}
        with self.assertRaises(ValidationError):
            self.validator.validate(unresolved)

        mismatch = complete_official_intake(self.template)
        mismatch["interfaces"]["entries"][0]["qos_profiles"][0]["channel"] = "goal"
        with self.assertRaises(ValidationError):
            self.validator.validate(mismatch)

        duplicate = complete_official_intake(self.template)
        duplicate["interfaces"]["entries"][0]["qos_profiles"].append(qos_profile())
        self.validator.validate(duplicate)
        with self.assertRaisesRegex(IntakeReferenceError, "duplicate channel"):
            validate_references(duplicate)

        oversized = complete_official_intake(self.template)
        oversized["interfaces"]["entries"][0]["qos_profiles"][0]["depth"] = 100_001
        with self.assertRaises(ValidationError):
            self.validator.validate(oversized)

        missing_depth = complete_official_intake(self.template)
        missing_depth["interfaces"]["entries"][0]["qos_profiles"][0]["depth"] = None
        with self.assertRaises(ValidationError):
            self.validator.validate(missing_depth)
        with self.assertRaisesRegex(IntakeReferenceError, "requires a positive depth"):
            validate_references(missing_depth)

    def test_semantic_interface_roles_are_enforced(self) -> None:
        mutations = (
            ("lifecycle", "status_interface_ids"),
            ("session", "capability_discovery_interface_ids"),
            ("session", "session_interface_ids"),
            ("session", "heartbeat_interface_ids"),
            ("safety", "emergency_stop"),
        )
        for section, field in mutations:
            with self.subTest(section=section, field=field):
                intake = complete_official_intake(self.template)
                if section == "lifecycle":
                    intake["lifecycle_semantics"][field] = sourced_list(
                        ["speech-interface"]
                    )
                elif section == "session":
                    intake["session_and_liveness"][field] = sourced_list(
                        ["speech-interface"]
                    )
                else:
                    intake["safety_semantics"][field]["interface_ids"] = sourced_list(
                        ["speech-interface"]
                    )
                self.validator.validate(intake)
                with self.assertRaisesRegex(IntakeReferenceError, "wrong role"):
                    validate_references(intake)

    def test_limit_capability_order_and_magnitude_are_enforced(self) -> None:
        wrong_capability = complete_official_intake(self.template)
        wrong_capability["limits"]["entries"][0]["capability"] = "gaze"
        self.validator.validate(wrong_capability)
        with self.assertRaisesRegex(IntakeReferenceError, "different capability"):
            validate_references(wrong_capability)

        reversed_bounds = complete_official_intake(self.template)
        limit = reversed_bounds["limits"]["entries"][0]
        limit["lower_bound"] = 10
        limit["upper_bound"] = 1
        self.validator.validate(reversed_bounds)
        with self.assertRaisesRegex(IntakeReferenceError, "lower_bound"):
            validate_references(reversed_bounds)

        huge = complete_official_intake(self.template)
        huge["limits"]["entries"][0]["upper_bound"] = 1_000_000_000_001
        with self.assertRaises(ValidationError):
            self.validator.validate(huge)

    def test_frame_parent_references_and_cycles_are_rejected(self) -> None:
        unknown = complete_official_intake(self.template)
        unknown["frames"]["entries"][0]["parent_frame_id"] = "missing-frame"
        self.validator.validate(unknown)
        with self.assertRaisesRegex(IntakeReferenceError, "unknown frame"):
            validate_references(unknown)

        self_parent = complete_official_intake(self.template)
        self_parent["frames"]["entries"][0]["parent_frame_id"] = "official-frame"
        self.validator.validate(self_parent)
        with self.assertRaisesRegex(IntakeReferenceError, "own parent"):
            validate_references(self_parent)

        cycle = complete_official_intake(self.template)
        cycle["frames"]["entries"][0]["parent_frame_id"] = "second-frame"
        second = deepcopy(cycle["frames"]["entries"][0])
        second["frame_id"] = "second-frame"
        second["official_name"] = "second_official_frame"
        second["parent_frame_id"] = "official-frame"
        cycle["frames"]["entries"].append(second)
        self.validator.validate(cycle)
        with self.assertRaisesRegex(IntakeReferenceError, "cycle"):
            validate_references(cycle)

    def test_numeric_and_timestamp_resource_bounds_are_enforced(self) -> None:
        with self.assertRaisesRegex(ValueError, "nonfinite JSON number"):
            strict_json_loads('{"scale_to_si": 1e9999}')

        scale = complete_official_intake(self.template)
        scale["units"]["entries"][0]["scale_to_si"] = 1_000_000_000_001
        with self.assertRaises(ValidationError):
            self.validator.validate(scale)

        timestamp = deepcopy(self.template)
        timestamp["intake_status"] = "hanson_reviewed"
        timestamp["review"]["simulator_evidence"] = {
            "status": "failed",
            "commit_sha": "a" * 40,
            "run_record_reference": "https://example.invalid/run",
            "completed_at_utc": "2026-08-18T12:00:00." + ("1" * 100_000) + "Z",
        }
        with self.assertRaises(ValidationError):
            self.validator.validate(timestamp)

    def test_trailing_controls_and_whitespace_only_values_are_rejected(self) -> None:
        source_mutations = (
            ("source_id", "official-source\n"),
            ("title", "   "),
            ("title", "Public title\n"),
            ("reference", "   "),
        )
        for field, value in source_mutations:
            with self.subTest(field=field, value=repr(value)):
                intake = deepcopy(self.template)
                source = deepcopy(OFFICIAL_SOURCE)
                source[field] = value
                intake["official_sources"] = [source]
                with self.assertRaises(ValidationError):
                    self.validator.validate(intake)

        whitespace = deepcopy(self.template)
        whitespace["target_environment"]["ros_2_distribution"] = {
            "status": "provided_unverified",
            "value": "   ",
            "source_ids": [],
        }
        with self.assertRaises(ValidationError):
            self.validator.validate(whitespace)

        sha = deepcopy(self.template)
        sha["intake_status"] = "hanson_reviewed"
        sha["review"]["simulator_evidence"] = {
            "status": "failed",
            "commit_sha": ("a" * 40) + "\n",
            "run_record_reference": "https://example.invalid/run",
            "completed_at_utc": "2026-08-18T12:00:00Z",
        }
        with self.assertRaises(ValidationError):
            self.validator.validate(sha)

    def test_unicode_invisible_controls_and_noncharacters_are_rejected(self) -> None:
        hostile_values = (
            "\u0085",  # C1 next-line control
            "\u2028",  # Unicode line separator
            "\u200b",  # zero-width space
            "\ufeff",  # byte-order mark / zero-width no-break space
            "\ud800",  # lone surrogate
            "\u202e",  # right-to-left override
            "\u2066",  # left-to-right isolate
            "\ufdd0",  # Unicode noncharacter
            "\ue000",  # private-use code point
            "\u0378",  # unassigned code point
            "\u0301",  # combining-mark-only text has no visible base
        )
        for value in hostile_values:
            with self.subTest(value=ascii(value)):
                with self.assertRaises(IntakeInputError):
                    strict_json_loads(json.dumps({"value": value}))

        promotion = complete_official_intake(self.template)
        promotion["official_sources"][0]["title"] = "\u200b"
        promotion["official_sources"][0]["reference"] = "\ufeff"
        promotion["review"]["hanson_review_disposition"] = sourced_text("\u200b")
        with self.assertRaises(ValidationError):
            self.validator.validate(promotion)
        with self.assertRaises(IntakeInputError):
            validate_references(promotion, require_official=True)

        visible_unicode = complete_official_intake(self.template)
        visible_unicode["target_environment"]["ros_2_distribution"] = sourced_text(
            "ROS café robot 🤖"
        )
        self.validator.validate(visible_unicode)
        validate_references(visible_unicode, require_official=True)

    def test_simulator_evidence_rejects_null_oid_and_future_completion(self) -> None:
        null_oid = complete_official_intake(self.template)
        null_oid["intake_status"] = "simulator_validated_for_named_versions"
        null_oid["review"]["simulator_evidence"] = {
            "status": "passed_for_named_versions",
            "commit_sha": "0" * 40,
            "run_record_reference": "https://example.invalid/synthetic-test-run",
            "completed_at_utc": "2020-01-01T00:00:00Z",
        }
        with self.assertRaises(ValidationError):
            self.validator.validate(null_oid)
        with self.assertRaisesRegex(IntakeReferenceError, "null object id"):
            validate_references(null_oid)

        future = complete_official_intake(self.template)
        future["intake_status"] = "simulator_validated_for_named_versions"
        future["review"]["simulator_evidence"] = {
            "status": "passed_for_named_versions",
            "commit_sha": "d" * 40,
            "run_record_reference": "https://example.invalid/synthetic-test-run",
            "completed_at_utc": "9999-12-31T23:59:59Z",
        }
        self.validator.validate(future)
        with self.assertRaisesRegex(IntakeReferenceError, "clock-skew allowance"):
            validate_references(future)

    def test_file_depth_container_and_recursion_bounds_are_enforced(self) -> None:
        nested = ("[" * (MAX_JSON_DEPTH + 1)) + "0" + ("]" * (MAX_JSON_DEPTH + 1))
        with self.assertRaisesRegex(ValueError, "depth limit"):
            strict_json_loads(nested)

        wide = "[" + ",".join("0" for _ in range(10_001)) + "]"
        with self.assertRaisesRegex(ValueError, "array item limit"):
            strict_json_loads(wide)

        with tempfile.TemporaryDirectory() as directory:
            oversized = Path(directory) / "oversized.json"
            oversized.write_bytes(b" " * (MAX_JSON_BYTES + 1))
            with self.assertRaisesRegex(ValueError, "file size limit"):
                load_and_validate(
                    oversized,
                    INTAKE_ROOT / "official-hanson-interface-intake.schema.json",
                )

    def test_cli_errors_are_sanitized(self) -> None:
        secret = "PRIVATE_EMAIL_BODY_DO_NOT_LOG"
        attacks = []

        schema_attack = deepcopy(self.template)
        schema_attack["target_environment"]["ros_2_distribution"]["value"] = secret
        attacks.append(schema_attack)

        semantic_attack = deepcopy(self.template)
        semantic_attack["capabilities"]["speech"]["confirmation"] = {
            "status": "provided_unverified",
            "source_ids": [],
        }
        semantic_attack["capabilities"]["speech"]["interface_ids"] = {
            "status": "provided_unverified",
            "values": [secret],
            "source_ids": [],
        }
        attacks.append(semantic_attack)

        with tempfile.TemporaryDirectory() as directory:
            for index, attack in enumerate(attacks):
                with self.subTest(index=index):
                    path = Path(directory) / f"attack-{index}.json"
                    path.write_text(json.dumps(attack), encoding="utf-8")
                    output = io.StringIO()
                    with patch("sys.argv", ["validate_hanson_intake.py", str(path)]):
                        with redirect_stdout(output):
                            result = main()
                    self.assertEqual(result, 1)
                    rendered = output.getvalue()
                    self.assertNotIn(secret, rendered)
                    self.assertIn("error_code=", rendered)

    def test_local_documentation_links_resolve(self) -> None:
        link_pattern = re.compile(r"!?\[[^]]*\]\(([^)]+)\)")
        for markdown_path in sorted(PROJECT_ROOT.rglob("*.md")):
            text = markdown_path.read_text(encoding="utf-8")
            for raw_target in link_pattern.findall(text):
                target = raw_target.split("#", 1)[0]
                if not target or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", target):
                    continue
                with self.subTest(document=markdown_path.name, target=target):
                    self.assertTrue((markdown_path.parent / target).resolve().exists())


if __name__ == "__main__":
    unittest.main()
