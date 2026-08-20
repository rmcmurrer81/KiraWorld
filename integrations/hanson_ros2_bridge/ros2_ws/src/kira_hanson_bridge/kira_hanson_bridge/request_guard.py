from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping


@dataclass(frozen=True)
class ReplayDecision:
    should_dispatch: bool
    reason_code: str
    detail: str
    request_digest: str


class RequestGuard:
    """Bounded in-memory duplicate and conflicting-ID guard.

    The guard is deliberately transport-independent. A production adapter should
    additionally persist the session journal or use an official robot-side
    idempotency mechanism across process restarts.
    """

    def __init__(self, maximum_entries: int = 2048):
        if isinstance(maximum_entries, bool) or not isinstance(maximum_entries, int):
            raise ValueError("maximum_entries must be an integer.")
        if maximum_entries <= 0:
            raise ValueError("maximum_entries must be positive.")
        self.maximum_entries = maximum_entries
        self._digests: OrderedDict[str, str] = OrderedDict()

    RECEIPT_LOCAL_FIELDS = frozenset({"age_ms"})

    @staticmethod
    def digest(category: str, payload: Mapping[str, Any]) -> str:
        wire_semantics = {
            key: value
            for key, value in payload.items()
            if key not in RequestGuard.RECEIPT_LOCAL_FIELDS
        }
        canonical = json.dumps(
            {"category": category, "payload": wire_semantics},
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()

    def assess(self, category: str, payload: Mapping[str, Any]) -> ReplayDecision:
        intent_id = str(payload["intent_id"])
        request_digest = self.digest(category, payload)
        previous = self._digests.get(intent_id)

        if previous is None:
            self._digests[intent_id] = request_digest
            self._digests.move_to_end(intent_id)
            while len(self._digests) > self.maximum_entries:
                self._digests.popitem(last=False)
            return ReplayDecision(
                True,
                "NEW_REQUEST",
                "The intent ID and canonical payload have not been seen in this process session.",
                request_digest,
            )

        self._digests.move_to_end(intent_id)
        if previous == request_digest:
            return ReplayDecision(
                False,
                "DUPLICATE_SUPPRESSED",
                "An identical request with this intent ID was already admitted; it will not be dispatched again.",
                request_digest,
            )

        return ReplayDecision(
            False,
            "INTENT_ID_REUSE_CONFLICT",
            "This intent ID was already used for a different canonical request.",
            request_digest,
        )
