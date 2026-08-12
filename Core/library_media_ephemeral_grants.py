"""Short-lived, identity-bound grants for efficient local media byte ranges.

Grant creation performs one exact ``LibraryMediaResolver`` hash revalidation.
That grant-time SHA-256 remains the source identity for the grant.  Subsequent
range requests deliberately do not rehash a potentially multi-gigabyte file;
they fail closed if path containment, link/reparse status, regular-file
identity, size, mtime, or ctime differs from the grant-time evidence.

The short TTL is an idle timeout.  A valid, exactly bound range request renews
it; lookup alone does not.  This permits continuous local playback while still
purging an abandoned token quickly.

All grant state, including the resolved path and validated descriptor, exists
only in process memory.  There is no serialization or persistence API.
"""

from __future__ import annotations

import hmac
import math
import secrets
import threading
import time
from copy import deepcopy
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable, Mapping

from library_media_http_range import (
    LibraryMediaHttpRange,
    LibraryMediaHttpRangeError,
    ReadOnlyByteRangeResponse,
    _file_identity,
)
from library_media_resolver import LibraryMediaResolutionError, LibraryMediaResolver


DEFAULT_GRANT_TTL_SECONDS = 120.0
MAX_GRANT_TTL_SECONDS = 300.0
DEFAULT_MAX_ACTIVE_GRANTS = 16
ABSOLUTE_MAX_ACTIVE_GRANTS = 128


class EphemeralPlaybackGrantError(RuntimeError):
    """Base error for the in-memory grant boundary."""


class EphemeralPlaybackGrantNotFound(EphemeralPlaybackGrantError):
    """Unknown, expired, revoked, or incorrectly bound token."""


class EphemeralPlaybackGrantCapacityError(EphemeralPlaybackGrantError):
    """The bounded in-memory store has no free grant slot."""


class EphemeralPlaybackGrantSourceChanged(EphemeralPlaybackGrantError):
    """The grant-time path or regular-file identity no longer matches."""


def _nonserializable(*_args: Any, **_kwargs: Any) -> None:
    raise TypeError("ephemeral playback grants must not be serialized.")


def _binding_text(value: str, field_name: str, maximum: int = 256) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EphemeralPlaybackGrantError(f"{field_name} must be a non-empty string.")
    normalized = value.strip()
    if len(normalized) > maximum:
        raise EphemeralPlaybackGrantError(f"{field_name} exceeds {maximum} characters.")
    return normalized


@dataclass(frozen=True, slots=True)
class EphemeralPlaybackBinding:
    person_id: str
    activation_revision: str
    session_id: str
    session_nonce: str

    __getstate__ = _nonserializable
    __reduce_ex__ = _nonserializable

    def __repr__(self) -> str:
        return (
            "EphemeralPlaybackBinding(person_id=<bound>, "
            "activation_revision=<bound>, session_id=<bound>, session_nonce=<redacted>)"
        )


@dataclass(frozen=True, slots=True)
class EphemeralPlaybackGrantReceipt:
    token: str
    expires_at_monotonic: float
    grant_time_source_sha256: str
    source_size_bytes: int
    mime_type: str

    __getstate__ = _nonserializable
    __reduce_ex__ = _nonserializable

    def __repr__(self) -> str:
        return (
            "EphemeralPlaybackGrantReceipt(token=<redacted>, "
            f"expires_at_monotonic={self.expires_at_monotonic!r}, "
            f"source_size_bytes={self.source_size_bytes!r}, mime_type={self.mime_type!r})"
        )


@dataclass(frozen=True, slots=True)
class EphemeralPlaybackGrantStatus:
    active: bool
    expires_at_monotonic: float
    expires_in_seconds: float
    grant_time_source_sha256: str
    source_size_bytes: int
    mime_type: str
    range_request_count: int

    __getstate__ = _nonserializable
    __reduce_ex__ = _nonserializable


class _GrantState:
    __slots__ = (
        "token",
        "binding",
        "created_at",
        "expires_at",
        "idle_ttl_seconds",
        "descriptor",
        "resolved_path",
        "file_identity",
        "mime_type",
        "range_request_count",
        "last_used_at",
    )

    __getstate__ = _nonserializable
    __reduce_ex__ = _nonserializable

    def __init__(
        self,
        *,
        token: str,
        binding: EphemeralPlaybackBinding,
        created_at: float,
        expires_at: float,
        idle_ttl_seconds: float,
        descriptor: Mapping[str, Any],
        resolved_path: Path,
        file_identity: tuple[int | None, int | None, int, int, int],
        mime_type: str,
    ) -> None:
        self.token = token
        self.binding = binding
        self.created_at = created_at
        self.expires_at = expires_at
        self.idle_ttl_seconds = idle_ttl_seconds
        self.descriptor = deepcopy(dict(descriptor))
        self.resolved_path = resolved_path
        self.file_identity = file_identity
        self.mime_type = mime_type
        self.range_request_count = 0
        self.last_used_at: float | None = None


class EphemeralLibraryMediaGrantManager:
    """Thread-safe bounded capability store with no disk representation."""

    __getstate__ = _nonserializable
    __reduce_ex__ = _nonserializable

    def __init__(
        self,
        project_root: str | Path,
        *,
        clock: Callable[[], float] = time.monotonic,
        default_ttl_seconds: float = DEFAULT_GRANT_TTL_SECONDS,
        max_active_grants: int = DEFAULT_MAX_ACTIVE_GRANTS,
        max_non_range_bytes: int = 1024 * 1024,
        max_range_bytes: int = 8 * 1024 * 1024,
        read_chunk_bytes: int = 64 * 1024,
    ) -> None:
        if not callable(clock):
            raise EphemeralPlaybackGrantError("clock must be callable.")
        if (
            isinstance(default_ttl_seconds, bool)
            or not isinstance(default_ttl_seconds, (int, float))
            or not math.isfinite(float(default_ttl_seconds))
            or float(default_ttl_seconds) <= 0
            or float(default_ttl_seconds) > MAX_GRANT_TTL_SECONDS
        ):
            raise EphemeralPlaybackGrantError(
                f"default_ttl_seconds must be within (0, {MAX_GRANT_TTL_SECONDS}]."
            )
        if (
            isinstance(max_active_grants, bool)
            or not isinstance(max_active_grants, int)
            or max_active_grants < 1
            or max_active_grants > ABSOLUTE_MAX_ACTIVE_GRANTS
        ):
            raise EphemeralPlaybackGrantError(
                f"max_active_grants must be within [1, {ABSOLUTE_MAX_ACTIVE_GRANTS}]."
            )
        self._project_root = Path(project_root).resolve(strict=True)
        self._library_root = (self._project_root / "Data" / "library").resolve(strict=True)
        self._clock = clock
        self._last_clock_value: float | None = None
        self._default_ttl_seconds = float(default_ttl_seconds)
        self._max_active_grants = max_active_grants
        self._http = LibraryMediaHttpRange(
            self._project_root,
            max_non_range_bytes=max_non_range_bytes,
            max_range_bytes=max_range_bytes,
            read_chunk_bytes=read_chunk_bytes,
        )
        self._resolver = LibraryMediaResolver(self._project_root)
        self._grants: dict[str, _GrantState] = {}
        self._lock = threading.RLock()

    @staticmethod
    def _validated_binding(
        binding: EphemeralPlaybackBinding,
    ) -> EphemeralPlaybackBinding:
        if not isinstance(binding, EphemeralPlaybackBinding):
            raise EphemeralPlaybackGrantError(
                "an EphemeralPlaybackBinding is required."
            )
        return EphemeralPlaybackBinding(
            person_id=_binding_text(binding.person_id, "person_id"),
            activation_revision=_binding_text(
                binding.activation_revision, "activation_revision"
            ),
            session_id=_binding_text(binding.session_id, "session_id"),
            session_nonce=_binding_text(
                binding.session_nonce, "session_nonce", maximum=512
            ),
        )

    def _now_locked(self) -> float:
        raw = self._clock()
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise EphemeralPlaybackGrantError("clock must return a finite number.")
        now = float(raw)
        if not math.isfinite(now):
            raise EphemeralPlaybackGrantError("clock must return a finite number.")
        if self._last_clock_value is not None and now < self._last_clock_value:
            raise EphemeralPlaybackGrantError("grant clock must be monotonic.")
        self._last_clock_value = now
        return now

    @staticmethod
    def _token_text(token: str) -> str:
        if (
            not isinstance(token, str)
            or len(token) < 32
            or len(token) > 256
            or any(character.isspace() for character in token)
        ):
            raise EphemeralPlaybackGrantNotFound(
                "playback grant is unknown, expired, revoked, or incorrectly bound."
            )
        return token

    @staticmethod
    def _binding_matches(
        left: EphemeralPlaybackBinding, right: EphemeralPlaybackBinding
    ) -> bool:
        return all(
            hmac.compare_digest(left_value, right_value)
            for left_value, right_value in (
                (left.person_id, right.person_id),
                (left.activation_revision, right.activation_revision),
                (left.session_id, right.session_id),
                (left.session_nonce, right.session_nonce),
            )
        )

    def _purge_expired_locked(self, now: float) -> int:
        expired = [
            token for token, grant in self._grants.items() if now >= grant.expires_at
        ]
        for token in expired:
            del self._grants[token]
        return len(expired)

    def _new_token_locked(self) -> str:
        for _ in range(16):
            token = secrets.token_urlsafe(32)
            if token not in self._grants:
                return token
        raise EphemeralPlaybackGrantError("could not allocate a unique opaque token.")

    def _validated_ttl(self, ttl_seconds: float | None) -> float:
        ttl = self._default_ttl_seconds if ttl_seconds is None else ttl_seconds
        if (
            isinstance(ttl, bool)
            or not isinstance(ttl, (int, float))
            or not math.isfinite(float(ttl))
            or float(ttl) <= 0
            or float(ttl) > MAX_GRANT_TTL_SECONDS
        ):
            raise EphemeralPlaybackGrantError(
                f"ttl_seconds must be within (0, {MAX_GRANT_TTL_SECONDS}]."
            )
        return float(ttl)

    def _preflight_capacity(self) -> None:
        # Avoid hashing a large source when the bounded store is already full.
        # Capacity is checked again after hashing because other creators may
        # legitimately race for the remaining slot.
        with self._lock:
            preflight_now = self._now_locked()
            self._purge_expired_locked(preflight_now)
            if len(self._grants) >= self._max_active_grants:
                raise EphemeralPlaybackGrantCapacityError(
                    "ephemeral playback grant capacity is reached."
                )

    def _store_validated_grant(
        self,
        *,
        current: Mapping[str, Any],
        physical: Path,
        mime_type: str,
        exact_binding: EphemeralPlaybackBinding,
        ttl: float,
        expected_identity: tuple[int | None, int | None, int, int, int],
    ) -> EphemeralPlaybackGrantReceipt:
        identity = _file_identity(physical)
        if identity != expected_identity or identity[2] != current["size_bytes"]:
            raise EphemeralPlaybackGrantSourceChanged(
                "source identity changed across grant-time hashing."
            )
        with self._lock:
            now = self._now_locked()
            self._purge_expired_locked(now)
            if len(self._grants) >= self._max_active_grants:
                raise EphemeralPlaybackGrantCapacityError(
                    "ephemeral playback grant capacity is reached."
                )
            token = self._new_token_locked()
            expires_at = now + ttl
            self._grants[token] = _GrantState(
                token=token,
                binding=exact_binding,
                created_at=now,
                expires_at=expires_at,
                idle_ttl_seconds=ttl,
                descriptor=current,
                resolved_path=physical,
                file_identity=identity,
                mime_type=mime_type,
            )
            return EphemeralPlaybackGrantReceipt(
                token=token,
                expires_at_monotonic=expires_at,
                grant_time_source_sha256=current["sha256"],
                source_size_bytes=current["size_bytes"],
                mime_type=mime_type,
            )

    def create_grant(
        self,
        descriptor: Mapping[str, Any],
        *,
        binding: EphemeralPlaybackBinding,
        ttl_seconds: float | None = None,
    ) -> EphemeralPlaybackGrantReceipt:
        """Hash-revalidate once, then retain an ephemeral capability in memory."""

        exact_binding = self._validated_binding(binding)
        ttl = self._validated_ttl(ttl_seconds)
        self._preflight_capacity()
        if not isinstance(descriptor, Mapping):
            raise EphemeralPlaybackGrantError(
                "grant descriptor failed exact resolver hash revalidation."
            )

        # This is the grant's one exact resolver hash revalidation.  Per-range
        # calls below deliberately use path/file identity rather than rehashing.
        try:
            before_path = self._resolver._candidate_for(
                descriptor.get("project_relative_path")
            )
            before_path.relative_to(self._library_root)
            before_identity = _file_identity(before_path)
            current, physical, mime_type = self._http._revalidate_descriptor(
                descriptor
            )
            if physical != before_path:
                raise LibraryMediaHttpRangeError(
                    "descriptor source path changed across grant-time hashing."
                )
        except (LibraryMediaResolutionError, LibraryMediaHttpRangeError, ValueError) as exc:
            raise EphemeralPlaybackGrantError(
                "grant descriptor failed exact resolver hash revalidation."
            ) from exc
        return self._store_validated_grant(
            current=current,
            physical=physical,
            mime_type=mime_type,
            exact_binding=exact_binding,
            ttl=ttl,
            expected_identity=before_identity,
        )

    def create_grant_for_selection(
        self,
        owner_selected_path: str | Path,
        binding: EphemeralPlaybackBinding,
        ttl_seconds: float | None = None,
    ) -> EphemeralPlaybackGrantReceipt:
        """Resolve/hash one owner selection once and create an in-memory grant.

        Unlike :meth:`create_grant`, this convenience entry point starts with a
        path selection instead of a previously issued descriptor.  It performs
        exactly one public resolver ``resolve`` call, then uses stat-only safe
        path validation to capture the grant identity without a second hash.
        """

        exact_binding = self._validated_binding(binding)
        ttl = self._validated_ttl(ttl_seconds)
        self._preflight_capacity()
        try:
            before_path = self._resolver._candidate_for(owner_selected_path)
            before_path.relative_to(self._library_root)
            before_identity = _file_identity(before_path)
            current = self._resolver.resolve(owner_selected_path)
            mime_type = self._http._mime_type_for_validated_descriptor(current)
            physical = self._resolver._candidate_for(
                current["project_relative_path"]
            )
            physical.relative_to(self._library_root)
            if physical != before_path:
                raise LibraryMediaResolutionError(
                    "owner selection path changed across grant-time hashing."
                )
        except (LibraryMediaResolutionError, LibraryMediaHttpRangeError, ValueError) as exc:
            raise EphemeralPlaybackGrantError(
                "owner selection failed exact resolver hash validation."
            ) from exc
        return self._store_validated_grant(
            current=current,
            physical=physical,
            mime_type=mime_type,
            exact_binding=exact_binding,
            ttl=ttl,
            expected_identity=before_identity,
        )

    def _checked_grant_locked(
        self,
        token: str,
        binding: EphemeralPlaybackBinding,
        now: float,
    ) -> _GrantState:
        token = self._token_text(token)
        exact_binding = self._validated_binding(binding)
        self._purge_expired_locked(now)
        grant = self._grants.get(token)
        if grant is None or not self._binding_matches(grant.binding, exact_binding):
            raise EphemeralPlaybackGrantNotFound(
                "playback grant is unknown, expired, revoked, or incorrectly bound."
            )
        try:
            current_path = self._resolver._candidate_for(
                grant.descriptor["project_relative_path"]
            )
            current_path.relative_to(self._library_root)
            current_identity = _file_identity(current_path)
        except (LibraryMediaResolutionError, LibraryMediaHttpRangeError, ValueError) as exc:
            del self._grants[token]
            raise EphemeralPlaybackGrantSourceChanged(
                "grant source failed containment/link/regular-file revalidation."
            ) from exc
        if current_path != grant.resolved_path or current_identity != grant.file_identity:
            del self._grants[token]
            raise EphemeralPlaybackGrantSourceChanged(
                "grant source path or file identity changed; grant revoked."
            )
        return grant

    def lookup(
        self, token: str, *, binding: EphemeralPlaybackBinding
    ) -> EphemeralPlaybackGrantStatus:
        """Return bounded status only; no path or descriptor leaves the store."""

        with self._lock:
            now = self._now_locked()
            grant = self._checked_grant_locked(token, binding, now)
            return EphemeralPlaybackGrantStatus(
                active=True,
                expires_at_monotonic=grant.expires_at,
                expires_in_seconds=max(grant.expires_at - now, 0.0),
                grant_time_source_sha256=grant.descriptor["sha256"],
                source_size_bytes=grant.descriptor["size_bytes"],
                mime_type=grant.mime_type,
                range_request_count=grant.range_request_count,
            )

    def refresh(
        self, token: str, *, binding: EphemeralPlaybackBinding
    ) -> EphemeralPlaybackGrantStatus:
        """Revalidate and slide one active grant's idle expiry.

        A player may already have buffered bytes and therefore make no new
        range request for longer than the normal idle TTL.  The owner-facing
        runtime uses this narrow heartbeat so an exact active media session
        remains valid while it is actually presented.  Refresh exposes no path
        and performs the same binding, containment, link, regular-file, and
        identity checks as lookup/prepare.
        """

        with self._lock:
            now = self._now_locked()
            grant = self._checked_grant_locked(token, binding, now)
            grant.last_used_at = now
            grant.expires_at = now + grant.idle_ttl_seconds
            return EphemeralPlaybackGrantStatus(
                active=True,
                expires_at_monotonic=grant.expires_at,
                expires_in_seconds=grant.idle_ttl_seconds,
                grant_time_source_sha256=grant.descriptor["sha256"],
                source_size_bytes=grant.descriptor["size_bytes"],
                mime_type=grant.mime_type,
                range_request_count=grant.range_request_count,
            )

    def prepare(
        self,
        token: str,
        *,
        binding: EphemeralPlaybackBinding,
        range_header: str | None = None,
    ) -> ReadOnlyByteRangeResponse:
        """Prepare one bounded response without rehashing the grant source."""

        exact_token = self._token_text(token)
        exact_binding = self._validated_binding(binding)
        with self._lock:
            now = self._now_locked()
            grant = self._checked_grant_locked(exact_token, exact_binding, now)
            descriptor = deepcopy(grant.descriptor)
            path = grant.resolved_path
            mime_type = grant.mime_type
            try:
                response = self._http._prepare_validated(
                    descriptor,
                    path,
                    mime_type,
                    range_header=range_header,
                    rehash_before_stream=False,
                )
            except LibraryMediaHttpRangeError as exc:
                self._grants.pop(token, None)
                raise EphemeralPlaybackGrantSourceChanged(
                    "grant source changed during range preparation; grant revoked."
                ) from exc
            grant.range_request_count += 1
            grant.last_used_at = now
            if response.status_code in {200, 206}:
                grant.expires_at = now + grant.idle_ttl_seconds

            def continuation_guard() -> None:
                with self._lock:
                    guard_now = self._now_locked()
                    self._checked_grant_locked(exact_token, exact_binding, guard_now)

            return replace(response, _continuation_guard=continuation_guard)

    def revoke(self, token: str, *, binding: EphemeralPlaybackBinding) -> bool:
        with self._lock:
            now = self._now_locked()
            grant = self._checked_grant_locked(token, binding, now)
            del self._grants[grant.token]
            return True

    def purge_expired(self) -> int:
        with self._lock:
            return self._purge_expired_locked(self._now_locked())

    def purge_all(self) -> int:
        with self._lock:
            count = len(self._grants)
            self._grants.clear()
            return count

    @property
    def active_count(self) -> int:
        with self._lock:
            now = self._now_locked()
            self._purge_expired_locked(now)
            return len(self._grants)
