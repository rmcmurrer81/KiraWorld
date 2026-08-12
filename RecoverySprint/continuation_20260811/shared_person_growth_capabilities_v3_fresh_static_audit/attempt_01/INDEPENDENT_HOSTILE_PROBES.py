from __future__ import annotations

import copy
import hashlib
import inspect
import json
import pickle
import tempfile
from pathlib import Path
from typing import Any, Callable
from unittest import mock

import Core.shared_person_growth_capabilities_v3 as core
import tools.create_temporary_ai_growth_profile_v3 as creator


ROOT = Path(__file__).resolve().parents[4]
AUTHOR_ROOT = (
    ROOT
    / "RecoverySprint"
    / "continuation_20260810"
    / "shared_person_growth_capabilities_v3_static_repair"
    / "attempt_01"
)
SECRET_A = bytes(range(1, 33))
SECRET_B = bytes(range(33, 65))


def canonical_sha(value: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def resign_profile(value: dict[str, Any]) -> dict[str, Any]:
    unsigned = copy.deepcopy(value)
    unsigned.pop("profile_fingerprint_sha256", None)
    value["profile_fingerprint_sha256"] = canonical_sha(unsigned)
    return value


def resign_attachment(value: dict[str, Any]) -> dict[str, Any]:
    unsigned = copy.deepcopy(value)
    unsigned.pop("attachment_sha256", None)
    value["attachment_sha256"] = canonical_sha(unsigned)
    return value


def resign_bundle(value: dict[str, Any]) -> dict[str, Any]:
    unsigned = copy.deepcopy(value)
    unsigned.pop("bundle_sha256", None)
    value["bundle_sha256"] = canonical_sha(unsigned)
    return value


def expect(exc_types: type[BaseException] | tuple[type[BaseException], ...], call: Callable[[], Any]) -> str:
    try:
        call()
    except exc_types as exc:
        return type(exc).__name__
    except BaseException as exc:  # pragma: no cover - hostile evidence path
        raise AssertionError(
            f"expected {exc_types!r}, got {type(exc).__name__}: {exc}"
        ) from exc
    raise AssertionError(f"expected {exc_types!r}, but call succeeded")


class Clock:
    def __init__(self) -> None:
        self.value = 100.0

    def __call__(self) -> float:
        self.value += 1.0
        return self.value


class World:
    def __init__(self, root: Path, suffix: str, *, secret: bytes = SECRET_A) -> None:
        self.root = root
        self.suffix = suffix
        self.secret = secret
        self.controller = core.ProtectedGrowthController(
            controller_id=f"controller_{suffix}",
            authority_secret=secret,
            ledger_root=root / f"ledger_{suffix}",
        )

    def binding(self, suffix: str | None = None) -> dict[str, str]:
        value = suffix or self.suffix
        return {
            "person_id": f"person_{value}",
            "candidate_id": f"candidate_{value}",
            "profile_id": f"profile_{value}",
        }

    def profile(
        self,
        suffix: str | None = None,
        *,
        maturity: core.MaturityAuthorityHandle | None = None,
    ) -> dict[str, Any]:
        value = suffix or self.suffix
        row = self.binding(value)
        roots = self.controller.issue_fresh_profile_roots(
            authority_identity=self.controller.identity,
            authority_secret=self.secret,
            operation_id=f"roots_{value}",
            **row,
        )
        return core.build_fresh_capability_profile(
            authority_controller=self.controller,
            authority_identity=self.controller.identity,
            fresh_root_authority=roots,
            maturity_authority=maturity,
            **row,
        )

    def classified_profile(self, suffix: str, status: str) -> dict[str, Any]:
        row = self.binding(suffix)
        revision = f"classification_{suffix}"
        evidence = self.controller.issue_evidence_receipt(
            authority_identity=self.controller.identity,
            authority_secret=self.secret,
            operation_id=f"classification_source_{suffix}",
            purpose="maturity_classification_source",
            source_kind="classification_receipt",
            source_content=f"exact classification bytes {suffix}".encode("utf-8"),
            source_revision=f"classification_source_revision_{suffix}",
            event_binding_id=revision,
            **row,
        )
        maturity = self.controller.issue_maturity_classification(
            authority_identity=self.controller.identity,
            authority_secret=self.secret,
            operation_id=f"classification_issue_{suffix}",
            status=status,
            source_evidence=evidence,
            classification_revision=revision,
            **row,
        )
        return self.profile(suffix, maturity=maturity)

    def session(
        self,
        profile: dict[str, Any],
        suffix: str | None = None,
        *,
        max_events: int = 128,
    ) -> core.PersonGrowthSession:
        value = suffix or self.suffix
        return self.controller.open_session(
            authority_identity=self.controller.identity,
            authority_secret=self.secret,
            profile=profile,
            activation_revision=f"activation_{value}",
            session_open_operation_id=f"session_open_{value}",
            clock=Clock(),
            max_events=max_events,
        )

    def evidence(
        self,
        session: core.PersonGrowthSession,
        event_id: str,
        *,
        suffix: str | None = None,
        purpose: str = "present_source",
        source_kind: str = "owner_statement",
        source_content: bytes = b"exact authenticated source bytes",
    ) -> core.EvidenceReceiptHandle:
        value = suffix or self.suffix
        return self.controller.issue_evidence_receipt(
            authority_identity=self.controller.identity,
            authority_secret=self.secret,
            operation_id=f"evidence_{event_id}",
            purpose=purpose,
            source_kind=source_kind,
            source_content=source_content,
            source_revision=f"source_revision_{event_id}",
            event_binding_id=event_id,
            session=session,
            lease=session.lease,
            **self.binding(value),
        )


def record_present(
    session: core.PersonGrowthSession,
    receipt: core.EvidenceReceiptHandle,
    event_id: str,
) -> dict[str, Any]:
    return session.record_present_fact(
        session.lease,
        present_event_id=event_id,
        factual_summary="One exact bounded present fact.",
        source_kind="owner_statement",
        source_receipt=receipt,
        observed_at_utc="2026-08-11T00:00:00Z",
        expires_at_utc="2026-08-11T00:10:00Z",
    )


def probe_seal_closure() -> dict[str, Any]:
    manifest_path = AUTHOR_ROOT / "SEALED_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rows = [*manifest["sealed_subjects"], *manifest["protected_predecessor_anchors"]]
    mismatches: list[dict[str, Any]] = []
    for row in rows:
        path = ROOT / row["path"]
        actual = path.read_bytes()
        if len(actual) != row["bytes"] or hashlib.sha256(actual).hexdigest() != row["sha256"]:
            mismatches.append(
                {
                    "path": row["path"],
                    "actual_bytes": len(actual),
                    "actual_sha256": hashlib.sha256(actual).hexdigest(),
                }
            )
    assert not mismatches
    assert hashlib.sha256(manifest_path.read_bytes()).hexdigest() == "d570e804c8653a5b1e419dba84a09e831adf13704ad0a363d0213b39e2482f96"
    assert hashlib.sha256((AUTHOR_ROOT / "AUTHOR_STATIC_TEST_RESULT.json").read_bytes()).hexdigest() == "8dac40f5814b456fa19401520597f1c4bae621ff0daec180dfc1f6daf5e59848"
    return {"checked": len(rows), "mismatches": 0}


def probe_controller_and_session_authority() -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        first = World(root, "authority_a", secret=SECRET_A)
        second = core.ProtectedGrowthController(
            controller_id=first.controller.controller_id,
            authority_secret=SECRET_B,
            ledger_root=root / "ledger_authority_b",
        )
        profile = first.profile()
        session = first.session(profile)
        assert first.controller.controller_identity_sha256 != second.controller_identity_sha256
        forged_identity = core.ControllerIdentityHandle(core._HANDLE_CONSTRUCTION_KEY)
        forged_lease = core.GrowthLeaseHandle(core._HANDLE_CONSTRUCTION_KEY)
        outcomes = [
            expect(
                core.GrowthAuthorityError,
                lambda: first.controller.issue_fresh_profile_roots(
                    authority_identity=forged_identity,
                    authority_secret=SECRET_A,
                    operation_id="forged_identity_roots",
                    **first.binding("forged_identity"),
                ),
            ),
            expect(
                core.GrowthAuthorityError,
                lambda: first.controller.issue_fresh_profile_roots(
                    authority_identity=second.identity,
                    authority_secret=SECRET_A,
                    operation_id="cross_controller_roots",
                    **first.binding("cross_controller"),
                ),
            ),
            expect(core.GrowthLeaseError, lambda: session.public_snapshot(forged_lease)),
            expect(TypeError, lambda: copy.copy(first.controller.identity)),
            expect(TypeError, lambda: pickle.dumps(session.lease)),
        ]
        return {
            "forged_registered": False,
            "cross_controller_registered": False,
            "cross_lease_read": False,
            "expected_refusals": outcomes,
        }


def probe_secret_strength_and_nonexport() -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        rejected = []
        for index, value in enumerate(
            [
                bytearray(SECRET_A),
                SECRET_A[:31],
                SECRET_A + b"x",
                b"A" * 32,
                bytes([1] * 31 + [0]),
                bytes(([1, 2, 3, 4] * 8)),
            ]
        ):
            rejected.append(
                expect(
                    core.GrowthAuthorityError,
                    lambda value=value, index=index: core.ProtectedGrowthController(
                        controller_id=f"bad_secret_{index}",
                        authority_secret=value,  # type: ignore[arg-type]
                        ledger_root=root / f"bad_secret_{index}",
                    ),
                )
            )
        world = World(root, "secret")
        bundle = creator.build_fresh_creator_bundle(
            candidate_id="candidate_secret",
            display_name="Secret Probe",
            authority_controller=world.controller,
            authority_identity=world.controller.identity,
            authority_secret=SECRET_A,
            person_id="person_secret",
            profile_id="profile_secret",
            fresh_roots_operation_id="roots_secret_bundle",
        )
        audit = world.controller.protected_audit_snapshot(
            authority_identity=world.controller.identity,
            authority_secret=SECRET_A,
        )
        serialized = json.dumps({"bundle": bundle, "audit": audit}, sort_keys=True).encode()
        ledger_bytes = b"".join(path.read_bytes() for path in root.rglob("*.json"))
        for observed in (serialized, ledger_bytes, repr(world.controller).encode()):
            assert SECRET_A not in observed
            assert SECRET_A.hex().encode("ascii") not in observed
        assert audit["authority_secret_serialized"] is False
        return {"invalid_secret_shapes_rejected": len(rejected), "secret_export_found": False}


def probe_evidence_content_scope_and_replay() -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        world = World(root, "evidence")
        profile = world.profile()
        session = world.session(profile)
        forged = core.EvidenceReceiptHandle(core._HANDLE_CONSTRUCTION_KEY)
        expect(core.GrowthAuthorityError, lambda: record_present(session, forged, "present_forged"))
        expect(
            TypeError,
            lambda: world.controller.issue_evidence_receipt(  # type: ignore[call-arg]
                authority_identity=world.controller.identity,
                authority_secret=SECRET_A,
                operation_id="phantom_digest_only",
                purpose="present_source",
                source_kind="owner_statement",
                source_content_sha256="1" * 64,
                source_revision="phantom_revision",
                event_binding_id="present_phantom",
                session=session,
                lease=session.lease,
                **world.binding(),
            ),
        )
        expect(
            core.GrowthCapabilityError,
            lambda: world.controller.issue_evidence_receipt(
                authority_identity=world.controller.identity,
                authority_secret=SECRET_A,
                operation_id="zero_content",
                purpose="present_source",
                source_kind="owner_statement",
                source_content=b"",
                source_revision="zero_content_revision",
                event_binding_id="present_zero_content",
                session=session,
                lease=session.lease,
                **world.binding(),
            ),
        )
        content = b"fresh hostile exact bytes"
        receipt = world.evidence(session, "present_evidence", source_content=content)
        expect(
            core.GrowthAuthorityError,
            lambda: record_present(session, receipt, "present_wrong_binding"),
        )
        event = record_present(session, receipt, "present_evidence")
        assert event["source_content_sha256"] == hashlib.sha256(content).hexdigest()
        assert event["source_content_bytes"] == len(content)
        assert content.decode() not in json.dumps(event)
        expect(
            core.GrowthReplayError,
            lambda: record_present(session, receipt, "present_evidence_replay"),
        )
        other_profile = world.profile("evidence_other")
        other_session = world.session(other_profile, "evidence_other")
        expect(
            core.GrowthAuthorityError,
            lambda: world.controller.issue_evidence_receipt(
                authority_identity=world.controller.identity,
                authority_secret=SECRET_A,
                operation_id="evidence_cross_session",
                purpose="present_source",
                source_kind="owner_statement",
                source_content=b"cross-session exact content",
                source_revision="cross_session_revision",
                event_binding_id="present_cross_session",
                session=other_session,
                lease=other_session.lease,
                **world.binding(),
            ),
        )
        return {"content_bound": True, "event_bound": True, "single_use": True, "cross_session_refused": True}


def probe_maturity_authority_and_truth_separation() -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        world = World(root, "maturity")
        row = world.binding()
        fake = core.MaturityAuthorityHandle(core._HANDLE_CONSTRUCTION_KEY)
        roots = world.controller.issue_fresh_profile_roots(
            authority_identity=world.controller.identity,
            authority_secret=SECRET_A,
            operation_id="roots_fake_maturity",
            **row,
        )
        expect(
            core.GrowthAuthorityError,
            lambda: core.build_fresh_capability_profile(
                authority_controller=world.controller,
                authority_identity=world.controller.identity,
                fresh_root_authority=roots,
                maturity_authority=fake,
                **row,
            ),
        )
        revision = "classification_maturity"
        source = world.controller.issue_evidence_receipt(
            authority_identity=world.controller.identity,
            authority_secret=SECRET_A,
            operation_id="classification_source_maturity",
            purpose="maturity_classification_source",
            source_kind="classification_receipt",
            source_content=b"authenticated classification source bytes",
            source_revision="classification_source_revision",
            event_binding_id=revision,
            **row,
        )
        maturity = world.controller.issue_maturity_classification(
            authority_identity=world.controller.identity,
            authority_secret=SECRET_A,
            operation_id="classification_issue_maturity",
            status="confirmed_adult",
            source_evidence=source,
            classification_revision=revision,
            **row,
        )
        expect(
            core.GrowthReplayError,
            lambda: world.controller.issue_maturity_classification(
                authority_identity=world.controller.identity,
                authority_secret=SECRET_A,
                operation_id="classification_issue_maturity_replay",
                status="confirmed_adult",
                source_evidence=source,
                classification_revision=revision,
                **row,
            ),
        )
        adult = world.profile(maturity=maturity)
        assert adult["maturity"]["full_adult_curriculum_eligible"] is True
        assert adult["maturity"]["full_adult_curriculum_delivered"] is False
        assert adult["maturity"]["adult_anatomy_added"] is False
        assert adult["maturity"]["consent_granted"] is False
        reuse_roots = world.controller.issue_fresh_profile_roots(
            authority_identity=world.controller.identity,
            authority_secret=SECRET_A,
            operation_id="roots_maturity_reuse",
            **row,
        )
        expect(
            core.GrowthReplayError,
            lambda: core.build_fresh_capability_profile(
                authority_controller=world.controller,
                authority_identity=world.controller.identity,
                fresh_root_authority=reuse_roots,
                maturity_authority=maturity,
                **row,
            ),
        )
        nonadult = world.classified_profile("maturity_nonadult", "non_adult")
        unresolved = world.profile("maturity_unresolved")
        assert nonadult["maturity"]["full_adult_curriculum_eligible"] is False
        assert unresolved["maturity"]["full_adult_curriculum_eligible"] is False
        assert nonadult["maturity"]["default_body_lane"] == "doll_safe_non_anatomical"
        return {"phantom_refused": True, "classification_receipt_one_use": True, "adult_truths_separate": True}


def probe_exact_types_and_unknown_fields() -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        world = World(root, "types")
        profile = world.profile()
        profile_mutations: list[dict[str, Any]] = []
        for path, value in [
            (("runtime", "activated"), 0),
            (("inheritance", "copied_private_records"), False),
            (("maturity", "consent_granted"), 0),
            (("capabilities", "present_source_grounding", "implemented_by_core"), 1),
        ]:
            changed = copy.deepcopy(profile)
            cursor: dict[str, Any] = changed
            for key in path[:-1]:
                cursor = cursor[key]
            cursor[path[-1]] = value
            profile_mutations.append(resign_profile(changed))
        unknown = copy.deepcopy(profile)
        unknown["private_payload"] = {"memory": "must not enter"}
        profile_mutations.append(resign_profile(unknown))
        for changed in profile_mutations:
            expect(
                core.GrowthCapabilityError,
                lambda changed=changed: core.validate_capability_profile(
                    changed,
                    authority_controller=world.controller,
                    authority_identity=world.controller.identity,
                ),
            )
        bundle = creator.build_fresh_creator_bundle(
            candidate_id="candidate_types_bundle",
            display_name="Types",
            authority_controller=world.controller,
            authority_identity=world.controller.identity,
            authority_secret=SECRET_A,
            person_id="person_types_bundle",
            profile_id="profile_types_bundle",
            fresh_roots_operation_id="roots_types_bundle",
        )
        bad_bundle = copy.deepcopy(bundle)
        bad_bundle["write_contract"]["private_person_data_copied"] = 0
        resign_bundle(bad_bundle)
        expect(
            core.GrowthCapabilityError,
            lambda: creator.validate_creator_bundle(
                bad_bundle,
                authority_controller=world.controller,
                authority_identity=world.controller.identity,
            ),
        )
        nested_unknown = copy.deepcopy(bundle)
        nested_unknown["attachment"]["creator_truth"]["memory"] = "private alias"
        resign_attachment(nested_unknown["attachment"])
        resign_bundle(nested_unknown)
        expect(
            core.GrowthCapabilityError,
            lambda: creator.validate_creator_bundle(
                nested_unknown,
                authority_controller=world.controller,
                authority_identity=world.controller.identity,
            ),
        )
        return {"bool_int_mutations_rejected": 4, "unknown_field_mutations_rejected": 2}


def probe_creator_private_separation_and_propagation() -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        world = World(root, "creator")
        source = creator.build_fresh_creator_bundle(
            candidate_id="candidate_creator_source",
            display_name="Source",
            authority_controller=world.controller,
            authority_identity=world.controller.identity,
            authority_secret=SECRET_A,
            person_id="person_creator_source",
            profile_id="profile_creator_source",
            fresh_roots_operation_id="roots_creator_source",
        )
        target = creator.build_fresh_creator_bundle(
            candidate_id="candidate_creator_target",
            display_name="Target",
            authority_controller=world.controller,
            authority_identity=world.controller.identity,
            authority_secret=SECRET_A,
            person_id="person_creator_target",
            profile_id="profile_creator_target",
            fresh_roots_operation_id="roots_creator_target",
        )
        source_roots = source["attachment"]["growth_profile"]["private_state_roots"]
        target_roots = target["attachment"]["growth_profile"]["private_state_roots"]
        assert set(source_roots.values()).isdisjoint(target_roots.values())
        assert target["attachment"]["growth_profile"]["inheritance"]["copied_private_records"] == 0
        assert target["attachment"]["growth_profile"]["runtime"] == {
            "activated": False,
            "model_connected": False,
            "memory_writer_connected": False,
            "external_actions_connected": False,
            "sensory_devices_connected": False,
            "media_playback_connected": False,
            "body_control_connected": False,
        }
        forged = copy.deepcopy(target)
        forged["attachment"]["growth_profile"]["private_state_roots"] = copy.deepcopy(source_roots)
        resign_profile(forged["attachment"]["growth_profile"])
        resign_attachment(forged["attachment"])
        resign_bundle(forged)
        expect(
            core.GrowthAuthorityError,
            lambda: creator.validate_creator_bundle(
                forged,
                authority_controller=world.controller,
                authority_identity=world.controller.identity,
            ),
        )
        other = World(root, "creator_other", secret=SECRET_B)
        expect(
            core.GrowthAuthorityError,
            lambda: creator.validate_creator_bundle(
                target,
                authority_controller=other.controller,
                authority_identity=other.controller.identity,
            ),
        )
        return {"fresh_roots_disjoint": True, "private_payload_copied": False, "runtime_active": False, "cross_controller_refused": True}


def probe_creator_rollback() -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        world = World(root, "rollback")
        bundle = creator.build_fresh_creator_bundle(
            candidate_id="candidate_rollback",
            display_name="Rollback",
            authority_controller=world.controller,
            authority_identity=world.controller.identity,
            authority_secret=SECRET_A,
            person_id="person_rollback",
            profile_id="profile_rollback",
            fresh_roots_operation_id="roots_rollback",
        )
        candidate = root / "TemporaryAI" / "candidates" / "candidate_rollback"
        candidate.mkdir(parents=True)
        output = candidate / "shared_person_growth_capabilities_v3.json"
        with mock.patch.object(creator.json, "loads", side_effect=RuntimeError("forced semantic readback failure")):
            expect(
                RuntimeError,
                lambda: creator.write_bundle_exclusive(
                    bundle,
                    project_root=root,
                    authority_controller=world.controller,
                    authority_identity=world.controller.identity,
                ),
            )
        assert not output.exists()
        output.write_text("preserve-existing", encoding="utf-8")
        expect(
            FileExistsError,
            lambda: creator.write_bundle_exclusive(
                bundle,
                project_root=root,
                authority_controller=world.controller,
                authority_identity=world.controller.identity,
            ),
        )
        assert output.read_text(encoding="utf-8") == "preserve-existing"
        return {"new_output_removed_after_failure": True, "preexisting_output_preserved": True}


def probe_event_before_receipt_and_capacity() -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        world = World(root, "ordering")
        profile = world.profile()
        session = world.session(profile, max_events=1)
        receipt = world.evidence(session, "present_ordering")
        original = world.controller._consume_session_evidence
        observed: dict[str, int] = {}

        def wrapped(**kwargs: Any) -> dict[str, Any]:
            head = world.controller._session_readback(session=session, lease=session.lease)
            observed["revision_before_consume"] = head["revision"]
            return original(**kwargs)

        with mock.patch.object(world.controller, "_consume_session_evidence", side_effect=wrapped):
            record_present(session, receipt, "present_ordering")
        assert observed["revision_before_consume"] == 1
        second = world.evidence(session, "present_ordering_second")
        expect(
            core.GrowthCapabilityError,
            lambda: record_present(session, second, "present_ordering_second"),
        )
        available = world.controller._peek_session_evidence(
            session=session,
            lease=session.lease,
            handle=second,
            purpose="present_source",
            source_kind="owner_statement",
            event_binding_id="present_ordering_second",
        )
        assert available["event_binding_id"] == "present_ordering_second"
        return {"durable_revision_before_receipt_consume": 1, "capacity_failure_consumed_receipt": False}


def probe_receipt_consume_uncertainty() -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        world = World(root, "consume_uncertain")
        profile = world.profile()
        session = world.session(profile)
        receipt = world.evidence(session, "present_consume_uncertain")
        with mock.patch.object(
            world.controller,
            "_consume_session_evidence",
            side_effect=core.GrowthRecoveryDebtError("forced consume uncertainty"),
        ):
            expect(
                core.GrowthRecoveryDebtError,
                lambda: record_present(session, receipt, "present_consume_uncertain"),
            )
        assert session.private_records(session.lease) == []
        expect(core.GrowthRecoveryDebtError, lambda: session.public_snapshot(session.lease))
        debt = world.controller.protected_recovery_debt_snapshot(
            authority_identity=world.controller.identity,
            authority_secret=SECRET_A,
        )
        assert debt["accepted_state_from_debt"] is False
        assert len(debt["sessions"]) == 1
        recovered = world.controller.recover_durable_state(
            authority_identity=world.controller.identity,
            authority_secret=SECRET_A,
            session=session,
            lease=session.lease,
        )
        assert recovered["session"]["action"] == "commit_recovered_after_explicit_readback"
        expect(core.GrowthLeaseError, lambda: session.private_records(session.lease))
        return {"accepted_event_before_recovery": False, "debt_durable": True, "session_quarantined": True}


def probe_cas_candidate_and_postreplace_ambiguity() -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        binding = hashlib.sha256(b"binding").hexdigest()
        candidate = core._DurableCASLedger("ledger:candidate_probe", root / "candidate.json")
        real_candidate_read = candidate._read_snapshot_path
        calls = {"count": 0}

        def fail_candidate_once(path: Path) -> dict[str, Any]:
            calls["count"] += 1
            if calls["count"] == 1:
                raise core.GrowthCapabilityError("forced candidate readback")
            return real_candidate_read(path)

        with mock.patch.object(candidate, "_read_snapshot_path", side_effect=fail_candidate_once):
            expect(
                core.GrowthRecoveryDebtError,
                lambda: candidate.append_cas(
                    expected_revision=0,
                    operation_id="candidate_operation",
                    kind="hostile_probe",
                    binding_sha256=binding,
                ),
            )
        assert candidate.revision == 0
        expect(core.GrowthRecoveryDebtError, candidate.readback_head)
        candidate_recovery = candidate.resolve_recovery_debt()
        assert candidate_recovery["action"] == "candidate_not_committed"

        post = core._DurableCASLedger("ledger:postreplace_probe", root / "postreplace.json")
        real_post_read = post._read_snapshot_path
        post_calls = {"count": 0}

        def fail_second(path: Path) -> dict[str, Any]:
            post_calls["count"] += 1
            if post_calls["count"] == 2:
                raise core.GrowthCapabilityError("forced post-replace readback")
            return real_post_read(path)

        with mock.patch.object(post, "_read_snapshot_path", side_effect=fail_second):
            expect(
                core.GrowthRecoveryDebtError,
                lambda: post.append_cas(
                    expected_revision=0,
                    operation_id="postreplace_operation",
                    kind="hostile_probe",
                    binding_sha256=binding,
                ),
            )
        assert post.revision == 0
        expect(core.GrowthRecoveryDebtError, post.readback_head)
        post_recovery = post.resolve_recovery_debt()
        assert post_recovery["action"] == "commit_recovered_after_explicit_readback"
        assert post.revision == 1
        return {
            "candidate_action": candidate_recovery["action"],
            "postreplace_action": post_recovery["action"],
            "accepted_before_recovery": False,
        }


def probe_emotion_replay_and_session_namespace() -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        world = World(root, "emotion")
        first_profile = world.profile()
        first = world.session(first_profile)
        first_receipt = world.evidence(first, "present_emotion")
        record_present(first, first_receipt, "present_emotion")
        kwargs = {
            "emotion_event_id": "emotion_same_text",
            "cause_present_event_ids": ("present_emotion",),
            "possible_interpretations": ("One bounded interpretation.",),
            "selected_appraisal": "One bounded appraisal.",
            "emotion_label": "curiosity",
            "intensity": 0.4,
            "confidence": 0.7,
            "unresolved": True,
        }
        event = first.record_causal_emotion(first.lease, **kwargs)
        expect(core.GrowthReplayError, lambda: first.record_causal_emotion(first.lease, **kwargs))

        second_profile = world.profile("emotion_second")
        second = world.session(second_profile, "emotion_second")
        second_receipt = world.evidence(
            second,
            "present_emotion_second",
            suffix="emotion_second",
        )
        record_present(second, second_receipt, "present_emotion_second")
        second_kwargs = dict(kwargs)
        second_kwargs["cause_present_event_ids"] = ("present_emotion_second",)
        second_event = second.record_causal_emotion(second.lease, **second_kwargs)
        assert event["session_binding_sha256"] != second_event["session_binding_sha256"]
        assert event["event_sha256"] != second_event["event_sha256"]
        return {"same_session_replay_refused": True, "cross_session_namespace_distinct": True}


def probe_initiative_and_memory_truth() -> dict[str, Any]:
    policy = core.load_policy()
    initiative = policy["capabilities"]["bounded_initiative"]
    assert initiative == {
        "stage": "DESIGN_ONLY",
        "implemented_by_core": False,
        "live_enabled": False,
        "may_execute_external_action": False,
    }
    assert not hasattr(core.PersonGrowthSession, "propose_initiative")
    assert not hasattr(core.PersonGrowthSession, "execute_initiative")
    source = inspect.getsource(core.PersonGrowthSession)
    assert "external_action_executed\": False" in source
    with tempfile.TemporaryDirectory() as temporary:
        world = World(Path(temporary), "memory_truth")
        profile = world.profile()
        session = world.session(profile)
        receipt = world.evidence(session, "present_memory_truth")
        record_present(session, receipt, "present_memory_truth")
        proposal = session.propose_learning(
            session.lease,
            proposal_id="proposal_memory_truth",
            proposed_claim="One proposal, not a memory.",
            source_present_event_ids=("present_memory_truth",),
            privacy_class="person_private",
            contradiction_state="not_checked",
        )
        assert proposal["proposal_state"] == "PROPOSED_NOT_MEMORY"
        assert proposal["durable_memory_mutated"] is False
        snapshot = world.controller.protected_audit_snapshot(
            authority_identity=world.controller.identity,
            authority_secret=SECRET_A,
        )
        assert snapshot["durable_memory_connected"] is False
        assert snapshot["external_actions_connected"] is False
    return {"initiative_stage": "DESIGN_ONLY", "memory_writer_connected": False, "external_actions_connected": False}


PROBES: list[tuple[str, Callable[[], dict[str, Any]]]] = [
    ("seal_closure", probe_seal_closure),
    ("controller_and_session_authority", probe_controller_and_session_authority),
    ("secret_strength_and_nonexport", probe_secret_strength_and_nonexport),
    ("evidence_content_scope_and_replay", probe_evidence_content_scope_and_replay),
    ("maturity_authority_and_truth_separation", probe_maturity_authority_and_truth_separation),
    ("exact_types_and_unknown_fields", probe_exact_types_and_unknown_fields),
    ("creator_private_separation_and_propagation", probe_creator_private_separation_and_propagation),
    ("creator_rollback", probe_creator_rollback),
    ("event_before_receipt_and_capacity", probe_event_before_receipt_and_capacity),
    ("receipt_consume_uncertainty", probe_receipt_consume_uncertainty),
    ("cas_candidate_and_postreplace_ambiguity", probe_cas_candidate_and_postreplace_ambiguity),
    ("emotion_replay_and_session_namespace", probe_emotion_replay_and_session_namespace),
    ("initiative_and_memory_truth", probe_initiative_and_memory_truth),
]


def main() -> None:
    results: list[dict[str, Any]] = []
    for name, probe in PROBES:
        try:
            details = probe()
        except BaseException as exc:
            results.append(
                {
                    "name": name,
                    "passed": False,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )
        else:
            results.append({"name": name, "passed": True, "details": details})
    output = {
        "schema": "kira.shared_person_growth_v3_independent_hostile_probe_result.v1",
        "static_only": True,
        "live_execution_performed": False,
        "real_person_or_memory_writer_used": False,
        "all_mutating_probe_roots_were_temporary": True,
        "probe_count": len(results),
        "passed": sum(1 for row in results if row["passed"]),
        "failed": sum(1 for row in results if not row["passed"]),
        "results": results,
    }
    print(json.dumps(output, ensure_ascii=False, sort_keys=True, indent=2))
    raise SystemExit(0 if output["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
