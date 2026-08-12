from __future__ import annotations

"""Loopback-only, transient visual-cue sidecar for Text + Voice use.

The service accepts one signed-lease-bound JPEG at a time and reduces it to a
small set of non-identifying factual cues.  It never opens a camera, saves,
replays, or hashes a frame, performs identity recognition, generates SPOKEN
text, writes memory, or contacts a model or online service.

Production decoding prefers an already-installed local OpenCV package.  When
OpenCV is absent, an already-installed Pillow package may provide the reduced
frame-size, brightness, and motion path; face counting is then explicitly
unavailable.  This module never installs or downloads anything.
"""

import argparse
import hmac
import importlib
import io
import ipaddress
import json
import math
import os
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Core.sensory_lease import SensoryLeaseError, validate_sensory_lease
from Core.process_liveness import process_is_alive


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8771
MAX_JPEG_BYTES = 1 * 1024 * 1024
MAX_FRAME_WIDTH = 1920
MAX_FRAME_HEIGHT = 1080
MAX_FRAME_PIXELS = MAX_FRAME_WIDTH * MAX_FRAME_HEIGHT
MOTION_GRID_WIDTH = 16
MOTION_GRID_HEIGHT = 12
MAX_COARSE_FACE_COUNT = 8
ALLOWED_CONTENT_TYPE = "image/jpeg"
LOOPBACK_HOST_NAMES = frozenset({"localhost"})


class VisualCapabilityUnavailable(RuntimeError):
    """Raised when the approved local OpenCV path is unavailable."""


class InvalidTransientJpeg(ValueError):
    """Raised when a payload is not one bounded, readable JPEG."""


class VisualSidecarBusy(RuntimeError):
    """Raised instead of allowing multiple raw JPEGs in flight."""


@dataclass(frozen=True, slots=True)
class DerivedFrame:
    """Non-replayable values derived from one decoded frame."""

    width: int
    height: int
    mean_luminance: float
    coarse_face_count: int | None
    motion_grid: bytes


class VisualBackend(Protocol):
    backend_name: str
    face_count_available: bool

    def derive_frame(self, jpeg_bytes: bytes) -> DerivedFrame:
        """Decode transient bytes and return derived values only."""


class LocalOpenCVBackend:
    """Small, local OpenCV adapter with no device or network operations."""

    backend_name = "local_opencv"

    def __init__(self, cv2_module: Any, numpy_module: Any) -> None:
        self._cv2 = cv2_module
        self._numpy = numpy_module
        self._face_detector = self._load_local_face_detector()
        self.face_count_available = self._face_detector is not None

    @classmethod
    def try_load(cls) -> tuple[LocalOpenCVBackend | None, str]:
        try:
            cv2_module = importlib.import_module("cv2")
            numpy_module = importlib.import_module("numpy")
        except (ImportError, ModuleNotFoundError):
            return None, "opencv_not_installed"
        except Exception:
            return None, "opencv_import_failed"
        try:
            return cls(cv2_module, numpy_module), ""
        except Exception:
            return None, "opencv_initialization_failed"

    def _load_local_face_detector(self) -> Any | None:
        data = getattr(self._cv2, "data", None)
        cascade_root = str(getattr(data, "haarcascades", "") or "")
        if not cascade_root:
            return None
        try:
            detector = self._cv2.CascadeClassifier(
                cascade_root + "haarcascade_frontalface_default.xml"
            )
            if detector is None or bool(detector.empty()):
                return None
            return detector
        except Exception:
            return None

    def derive_frame(self, jpeg_bytes: bytes) -> DerivedFrame:
        encoded = self._numpy.frombuffer(jpeg_bytes, dtype=self._numpy.uint8)
        gray = self._cv2.imdecode(encoded, self._cv2.IMREAD_GRAYSCALE)
        if gray is None or getattr(gray, "ndim", 0) != 2:
            raise InvalidTransientJpeg("OpenCV could not decode the JPEG")
        height, width = (int(value) for value in gray.shape[:2])
        _validate_decoded_dimensions(width, height)
        mean_luminance = float(self._cv2.mean(gray)[0])

        resized = self._cv2.resize(
            gray,
            (MOTION_GRID_WIDTH, MOTION_GRID_HEIGHT),
            interpolation=self._cv2.INTER_AREA,
        )
        # Four-bit luminance cells make this 192-byte baseline non-replayable
        # while retaining enough spatial change for a coarse motion cue.
        motion_grid = bytes(
            max(0, min(15, int(value) // 16))
            for value in resized.reshape(-1)
        )

        face_count: int | None = None
        if self._face_detector is not None:
            try:
                faces = self._face_detector.detectMultiScale(
                    gray,
                    scaleFactor=1.1,
                    minNeighbors=5,
                    minSize=(30, 30),
                )
                face_count = min(MAX_COARSE_FACE_COUNT, len(faces))
            except Exception:
                face_count = None

        return DerivedFrame(
            width=width,
            height=height,
            mean_luminance=mean_luminance,
            coarse_face_count=face_count,
            motion_grid=motion_grid,
        )


class LocalPillowFallbackBackend:
    """Reduced local fallback: JPEG size, brightness, and motion only."""

    backend_name = "local_pillow_fallback"
    face_count_available = False

    def __init__(self, image_module: Any) -> None:
        self._image = image_module

    @classmethod
    def try_load(cls) -> tuple[LocalPillowFallbackBackend | None, str]:
        try:
            image_module = importlib.import_module("PIL.Image")
        except (ImportError, ModuleNotFoundError):
            return None, "pillow_not_installed"
        except Exception:
            return None, "pillow_import_failed"
        return cls(image_module), ""

    def derive_frame(self, jpeg_bytes: bytes) -> DerivedFrame:
        try:
            with self._image.open(io.BytesIO(jpeg_bytes)) as image:
                if str(getattr(image, "format", "")).upper() != "JPEG":
                    raise InvalidTransientJpeg("Pillow decoded a non-JPEG image")
                width, height = (int(value) for value in image.size)
                _validate_decoded_dimensions(width, height)
                gray = image.convert("L")
                gray.load()
                histogram = gray.histogram()
                pixel_count = width * height
                mean_luminance = sum(
                    level * count for level, count in enumerate(histogram)
                ) / pixel_count
                resampling = getattr(self._image, "Resampling", self._image)
                box_filter = getattr(resampling, "BOX", 4)
                resized = gray.resize(
                    (MOTION_GRID_WIDTH, MOTION_GRID_HEIGHT),
                    resample=box_filter,
                )
                motion_grid = bytes(int(value) // 16 for value in resized.tobytes())
        except InvalidTransientJpeg:
            raise
        except Exception as exc:
            raise InvalidTransientJpeg("Pillow could not decode the JPEG") from exc

        return DerivedFrame(
            width=width,
            height=height,
            mean_luminance=float(mean_luminance),
            coarse_face_count=None,
            motion_grid=motion_grid,
        )


BackendLoader = Callable[[], tuple[VisualBackend | None, str]]
Clock = Callable[[], float]


def load_local_opencv_backend() -> tuple[VisualBackend | None, str]:
    return LocalOpenCVBackend.try_load()


def load_local_visual_backend() -> tuple[VisualBackend | None, str]:
    """Prefer OpenCV, then use an already-installed reduced Pillow fallback."""

    opencv_backend, opencv_reason = load_local_opencv_backend()
    if opencv_backend is not None:
        return opencv_backend, ""
    pillow_backend, pillow_reason = LocalPillowFallbackBackend.try_load()
    if pillow_backend is not None:
        return pillow_backend, ""
    reasons = [reason for reason in (opencv_reason, pillow_reason) if reason]
    return None, "_and_".join(reasons) or "local_visual_decoder_unavailable"


class VisualCueEngine:
    """One-frame-at-a-time reducer retaining only a tiny derived baseline."""

    def __init__(
        self,
        *,
        backend: VisualBackend | None = None,
        backend_loader: BackendLoader = load_local_visual_backend,
        clock: Clock = time.time,
    ) -> None:
        if not callable(backend_loader) or not callable(clock):
            raise TypeError("backend_loader and clock must be callable")
        self._backend = backend
        self._backend_loader = backend_loader
        self._backend_checked = backend is not None
        self._capability_reason = "" if backend is not None else "not_checked"
        self._clock = clock
        self._frame_lock = threading.Lock()
        self._state_lock = threading.RLock()
        self._active_lease_key: tuple[str, str, str] | None = None
        self._previous_motion_grid: bytes | None = None

    def capability(self) -> dict[str, Any]:
        with self._state_lock:
            backend = self._ensure_backend_locked()
            return {
                "available": backend is not None,
                "status": "ready" if backend is not None else "capability_unavailable",
                "reason": "" if backend is not None else self._capability_reason,
                "backend": backend.backend_name if backend is not None else "none",
                "reduced_pillow_fallback": bool(
                    backend is not None
                    and backend.backend_name == LocalPillowFallbackBackend.backend_name
                ),
                "face_count_available": bool(
                    backend is not None and backend.face_count_available
                ),
                "face_recognition_available": False,
                "person_recognition_available": False,
                "robert_recognition_available": False,
            }

    def process_transient_jpeg(
        self,
        jpeg_bytes: bytes,
        *,
        lease_claims: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Reduce one JPEG and discard all decoded/raw frame state."""

        if not self._frame_lock.acquire(blocking=False):
            raise VisualSidecarBusy("one transient JPEG is already being processed")
        try:
            frame_bytes = _validate_transient_jpeg_bytes(jpeg_bytes)
            lease_key = _exact_lease_key(lease_claims)
            with self._state_lock:
                if lease_key != self._active_lease_key:
                    self._active_lease_key = lease_key
                    self._previous_motion_grid = None
                backend = self._ensure_backend_locked()
                if backend is None:
                    raise VisualCapabilityUnavailable(self._capability_reason)

            # This local variable is the only decoded-frame input.  The backend
            # returns no pixels and retains no reference to the JPEG.
            derived = backend.derive_frame(frame_bytes)
            _validate_derived_frame(derived)

            with self._state_lock:
                previous_grid = self._previous_motion_grid
                motion_class, motion_confidence = _classify_motion(
                    previous_grid,
                    derived.motion_grid,
                )
                self._previous_motion_grid = bytes(derived.motion_grid)

            observed_at = _utc_iso_from_clock(self._clock)
            cues = [
                {
                    "name": "frame_size",
                    "value": {"width": derived.width, "height": derived.height},
                    "confidence": 1.0,
                },
                {
                    "name": "brightness_class",
                    "value": _classify_brightness(derived.mean_luminance),
                    "confidence": 0.9,
                },
                {
                    "name": "coarse_face_count",
                    "value": _coarse_face_count(derived.coarse_face_count),
                    "confidence": 0.6 if derived.coarse_face_count is not None else 0.0,
                },
                {
                    "name": "motion_class",
                    "value": motion_class,
                    "confidence": motion_confidence,
                },
            ]
            return {
                "ok": True,
                "kind": "derived_visual_factual_cues",
                "source": f"{backend.backend_name}_transient_jpeg",
                "observed_at": observed_at,
                "lease_person_id": lease_key[0],
                "activation_revision": lease_key[1],
                "cues": cues,
                "raw_frame_persisted": False,
                "raw_frame_replayed": False,
                "raw_frame_hashed": False,
                "identity_inference_performed": False,
                "face_recognition_status": "unavailable_not_performed",
                "person_recognition_status": "unavailable_not_performed",
                "robert_recognition_status": "unavailable_not_performed",
                "spoken_generated": False,
                "memory_written": False,
                "consent_changed": False,
                "relationship_changed": False,
                "qwen_used": False,
                "online_service_used": False,
            }
        finally:
            # Rebinding cannot zero immutable caller-owned bytes, but it makes
            # the sidecar retain no reference after this method returns.
            jpeg_bytes = b""
            self._frame_lock.release()

    def purge(self, lease_claims: Mapping[str, Any] | None = None) -> bool:
        """Purge the derived motion baseline on deactivation or switching."""

        expected = _exact_lease_key(lease_claims) if lease_claims is not None else None
        with self._frame_lock, self._state_lock:
            if expected is not None and self._active_lease_key not in {None, expected}:
                return False
            had_state = self._active_lease_key is not None or self._previous_motion_grid is not None
            self._active_lease_key = None
            self._previous_motion_grid = None
            return had_state

    @property
    def retained_derived_bytes(self) -> int:
        with self._state_lock:
            return len(self._previous_motion_grid or b"")

    def _ensure_backend_locked(self) -> VisualBackend | None:
        if not self._backend_checked:
            try:
                backend, reason = self._backend_loader()
            except Exception:
                backend, reason = None, "opencv_capability_probe_failed"
            self._backend = backend
            self._capability_reason = str(reason or "opencv_not_installed")
            self._backend_checked = True
        return self._backend


def _validate_transient_jpeg_bytes(value: bytes) -> bytes:
    if not isinstance(value, bytes):
        raise TypeError("transient JPEG must be supplied as bytes")
    length = len(value)
    if length < 4:
        raise InvalidTransientJpeg("transient JPEG is empty or incomplete")
    if length > MAX_JPEG_BYTES:
        raise InvalidTransientJpeg(f"transient JPEG exceeds {MAX_JPEG_BYTES} bytes")
    if not value.startswith(b"\xff\xd8") or not value.endswith(b"\xff\xd9"):
        raise InvalidTransientJpeg("payload is not one complete JPEG")
    return value


def _validate_decoded_dimensions(width: int, height: int) -> None:
    if width < 1 or height < 1:
        raise InvalidTransientJpeg("decoded JPEG dimensions are invalid")
    if (
        width > MAX_FRAME_WIDTH
        or height > MAX_FRAME_HEIGHT
        or width * height > MAX_FRAME_PIXELS
    ):
        raise InvalidTransientJpeg("decoded JPEG dimensions exceed the local visual cap")


def _validate_derived_frame(frame: DerivedFrame) -> None:
    _validate_decoded_dimensions(frame.width, frame.height)
    if not math.isfinite(frame.mean_luminance) or not 0.0 <= frame.mean_luminance <= 255.0:
        raise ValueError("backend returned invalid luminance")
    if frame.coarse_face_count is not None:
        if isinstance(frame.coarse_face_count, bool) or not isinstance(
            frame.coarse_face_count, int
        ):
            raise ValueError("backend returned invalid face count")
        if not 0 <= frame.coarse_face_count <= MAX_COARSE_FACE_COUNT:
            raise ValueError("backend returned out-of-range face count")
    if not isinstance(frame.motion_grid, bytes) or len(frame.motion_grid) != (
        MOTION_GRID_WIDTH * MOTION_GRID_HEIGHT
    ):
        raise ValueError("backend returned invalid motion grid")
    if any(value > 15 for value in frame.motion_grid):
        raise ValueError("backend motion grid is not four-bit quantized")


def _exact_lease_key(claims: Mapping[str, Any]) -> tuple[str, str, str]:
    if not isinstance(claims, Mapping):
        raise SensoryLeaseError("validated sensory lease claims are required")
    person = claims.get("person_id")
    revision = claims.get("activation_revision")
    nonce = claims.get("nonce")
    if not all(isinstance(value, str) and value and value == value.strip() for value in (
        person,
        revision,
        nonce,
    )):
        raise SensoryLeaseError("sensory lease claims are incomplete")
    return person, revision, nonce


def validate_bound_lease(
    token: str,
    secret: str | bytes,
    *,
    person_id: str,
    activation_revision: str,
    clock: Clock = time.time,
) -> dict[str, Any]:
    """Use the shared signed-lease validator with canonical exact bindings."""

    if not isinstance(person_id, str) or not person_id or person_id != person_id.strip():
        raise SensoryLeaseError("person id must be an exact canonical value")
    if (
        not isinstance(activation_revision, str)
        or not activation_revision
        or activation_revision != activation_revision.strip()
    ):
        raise SensoryLeaseError("activation revision must be an exact canonical value")
    return validate_sensory_lease(
        token,
        secret,
        expected_person_id=person_id,
        expected_activation_revision=activation_revision,
        clock=clock,
    )


def _classify_brightness(mean_luminance: float) -> str:
    if mean_luminance < 55.0:
        return "dark"
    if mean_luminance < 105.0:
        return "dim"
    if mean_luminance < 190.0:
        return "balanced"
    return "bright"


def _coarse_face_count(count: int | None) -> str:
    if count is None:
        return "unavailable"
    if count == 0:
        return "none"
    if count == 1:
        return "one"
    return "multiple"


def _classify_motion(previous: bytes | None, current: bytes) -> tuple[str, float]:
    if previous is None or len(previous) != len(current):
        return "baseline_unavailable", 0.0
    normalized_difference = sum(
        abs(int(before) - int(after)) for before, after in zip(previous, current)
    ) / (len(current) * 15.0)
    if normalized_difference < 0.015:
        return "still", 0.8
    if normalized_difference < 0.06:
        return "low", 0.75
    if normalized_difference < 0.18:
        return "moderate", 0.7
    return "high", 0.65


def _utc_iso_from_clock(clock: Clock) -> str:
    value = clock()
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("clock must return finite epoch seconds")
    timestamp = float(value)
    if not math.isfinite(timestamp):
        raise ValueError("clock must return finite epoch seconds")
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()


def is_loopback_host(host: str) -> bool:
    candidate = str(host or "").strip().lower()
    if candidate in LOOPBACK_HOST_NAMES:
        return True
    if "%" in candidate:
        candidate = candidate.split("%", 1)[0]
    try:
        return ipaddress.ip_address(candidate).is_loopback
    except ValueError:
        return False


def require_loopback_host(host: str) -> str:
    candidate = str(host or "").strip()
    if not is_loopback_host(candidate):
        raise ValueError("visual-perception sidecar must remain on loopback")
    return candidate


def health_payload(
    *,
    engine: VisualCueEngine | None = None,
) -> dict[str, Any]:
    local_engine = engine or VisualCueEngine()
    capability = local_engine.capability()
    return {
        "service": "kira_text_voice_visual_perception_sidecar",
        "status": capability["status"],
        "capability": capability,
        "loopback_only": True,
        "one_transient_jpeg_at_a_time": True,
        "max_jpeg_bytes": MAX_JPEG_BYTES,
        "raw_frame_persisted": False,
        "raw_frame_replayed": False,
        "raw_frame_hashed": False,
        "identity_recognition_enabled": False,
        "face_recognition_available": False,
        "person_recognition_available": False,
        "robert_recognition_available": False,
        "physical_camera_opened": False,
        "spoken_generated": False,
        "memory_written": False,
        "qwen_used": False,
        "online_service_used": False,
        "exact_signed_sensory_lease_required": True,
    }


def _json_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


class VisualPerceptionHTTPServer(HTTPServer):
    """Single-request loopback server, preventing concurrent JPEG bodies."""

    def __init__(
        self,
        server_address: tuple[str, int],
        *,
        engine: VisualCueEngine,
        session_token: str,
        lease_secret: str | bytes,
        clock: Clock = time.time,
    ) -> None:
        host, port = server_address
        require_loopback_host(host)
        if not str(session_token or "").strip():
            raise ValueError("visual sidecar session token is required")
        secret_bytes = lease_secret if isinstance(lease_secret, bytes) else str(
            lease_secret or ""
        ).encode("utf-8")
        if len(secret_bytes) < 32:
            raise ValueError("sensory lease secret must contain at least 32 bytes")
        self.engine = engine
        self.session_token = str(session_token)
        self.lease_secret = lease_secret
        self.clock = clock
        super().__init__((host, port), VisualPerceptionHandler)

    def server_close(self) -> None:
        self.engine.purge()
        super().server_close()


class VisualPerceptionHandler(BaseHTTPRequestHandler):
    server_version = "KiraVisualPerception/1.0"

    @property
    def visual_server(self) -> VisualPerceptionHTTPServer:
        return self.server  # type: ignore[return-value]

    def _client_is_loopback(self) -> bool:
        return bool(self.client_address and is_loopback_host(str(self.client_address[0])))

    def _allowed_origin(self) -> str:
        origin = str(self.headers.get("Origin", "")).strip()
        allowed = {
            item.strip()
            for item in str(
                os.environ.get(
                    "KIRA_VISUAL_ALLOWED_ORIGINS",
                    "http://127.0.0.1:8768,http://localhost:8768",
                )
            ).split(",")
            if item.strip()
        }
        return origin if origin in allowed else ""

    def _origin_is_allowed(self) -> bool:
        origin = str(self.headers.get("Origin", "")).strip()
        return not origin or bool(self._allowed_origin())

    def _authorized(self) -> bool:
        supplied = str(self.headers.get("X-Kira-Visual-Token", "")).strip()
        expected = self.visual_server.session_token
        if not supplied or not expected:
            return False
        return hmac.compare_digest(supplied.encode("utf-8"), expected.encode("utf-8"))

    def _send_json(self, status: int, payload: Mapping[str, Any]) -> None:
        body = _json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        origin = self._allowed_origin()
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)
        self.close_connection = True

    def _request_gate(self) -> bool:
        if not self._client_is_loopback():
            self._send_json(403, {"ok": False, "error": "loopback_required"})
            return False
        if not self._origin_is_allowed():
            self._send_json(403, {"ok": False, "error": "origin_not_allowed"})
            return False
        if not self._authorized():
            self._send_json(401, {"ok": False, "error": "unauthorized"})
            return False
        return True

    def _validated_lease(self) -> dict[str, Any] | None:
        person = str(self.headers.get("X-Kira-Person", ""))
        activation_revision = str(self.headers.get("X-Kira-Activation-Revision", ""))
        sensory_lease = str(self.headers.get("X-Kira-Sensory-Lease", "")).strip()
        if not person or not activation_revision or not sensory_lease:
            self._send_json(
                400,
                {"ok": False, "error": "person_activation_lease_required"},
            )
            return None
        try:
            return validate_bound_lease(
                sensory_lease,
                self.visual_server.lease_secret,
                person_id=person,
                activation_revision=activation_revision,
                clock=self.visual_server.clock,
            )
        except SensoryLeaseError:
            self._send_json(409, {"ok": False, "error": "sensory_lease_invalid"})
            return None

    def do_OPTIONS(self) -> None:  # noqa: N802
        if not self._client_is_loopback() or not self._allowed_origin():
            self._send_json(403, {"ok": False, "error": "origin_not_allowed"})
            return
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", self._allowed_origin())
        self.send_header("Vary", "Origin")
        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type, X-Kira-Visual-Token, X-Kira-Person, "
            "X-Kira-Activation-Revision, X-Kira-Sensory-Lease",
        )
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Max-Age", "600")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        if urlparse(self.path).path != "/health":
            self._send_json(404, {"ok": False, "error": "not_found"})
            return
        if not self._request_gate():
            return
        self._send_json(200, health_payload(engine=self.visual_server.engine))

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path not in {"/api/derive-cues", "/api/purge"}:
            self._send_json(404, {"ok": False, "error": "not_found"})
            return
        if not self._request_gate():
            return
        lease_claims = self._validated_lease()
        if lease_claims is None:
            return
        if path == "/api/purge":
            purged = self.visual_server.engine.purge(lease_claims)
            self._send_json(
                200,
                {
                    "ok": True,
                    "purged": purged,
                    "raw_frame_persisted": False,
                    "memory_written": False,
                },
            )
            return

        content_type = str(self.headers.get("Content-Type", "")).split(";", 1)[0].strip().lower()
        if content_type != ALLOWED_CONTENT_TYPE:
            self._send_json(415, {"ok": False, "error": "jpeg_required"})
            return
        if str(self.headers.get("Transfer-Encoding", "")).strip():
            self._send_json(400, {"ok": False, "error": "content_length_required"})
            return
        try:
            content_length = int(self.headers.get("Content-Length", ""))
        except (TypeError, ValueError):
            content_length = 0
        if content_length < 1 or content_length > MAX_JPEG_BYTES:
            self._send_json(
                413,
                {
                    "ok": False,
                    "error": "invalid_jpeg_size",
                    "max_bytes": MAX_JPEG_BYTES,
                },
            )
            return
        capability = self.visual_server.engine.capability()
        if not capability["available"]:
            self._send_json(
                503,
                {
                    "ok": False,
                    "error": "capability_unavailable",
                    "capability": capability,
                },
            )
            return

        jpeg_bytes = self.rfile.read(content_length)
        if len(jpeg_bytes) != content_length:
            jpeg_bytes = b""
            self._send_json(400, {"ok": False, "error": "incomplete_jpeg"})
            return
        try:
            result = self.visual_server.engine.process_transient_jpeg(
                jpeg_bytes,
                lease_claims=lease_claims,
            )
        except VisualSidecarBusy:
            self._send_json(429, {"ok": False, "error": "one_frame_at_a_time"})
            return
        except VisualCapabilityUnavailable:
            self._send_json(503, {"ok": False, "error": "capability_unavailable"})
            return
        except (InvalidTransientJpeg, ValueError, TypeError):
            self._send_json(422, {"ok": False, "error": "invalid_jpeg"})
            return
        finally:
            jpeg_bytes = b""
        self._send_json(200, result)

    def log_message(self, format: str, *args: Any) -> None:
        # Suppress request logging so no frame metadata or lease value enters a
        # log through this sidecar.
        return


def stop_when_parent_exits(server: VisualPerceptionHTTPServer, parent_pid: int) -> None:
    while process_is_alive(parent_pid):
        threading.Event().wait(0.5)
    server.shutdown()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the loopback-only transient visual-perception sidecar."
    )
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--parent-pid", type=int, default=0)
    parser.add_argument("--health", action="store_true")
    args = parser.parse_args()

    engine = VisualCueEngine()
    if args.health:
        payload = health_payload(engine=engine)
        print(json.dumps(payload, indent=2))
        return 0 if payload["status"] == "ready" else 2

    require_loopback_host(args.host)
    session_token = str(os.environ.get("KIRA_VISUAL_SESSION_TOKEN", "")).strip()
    lease_secret = str(os.environ.get("KIRA_SENSORY_LEASE_SECRET", "")).strip()
    if not session_token:
        raise SystemExit("KIRA_VISUAL_SESSION_TOKEN is required")
    if len(lease_secret.encode("utf-8")) < 32:
        raise SystemExit("KIRA_SENSORY_LEASE_SECRET is required")

    server = VisualPerceptionHTTPServer(
        (args.host, args.port),
        engine=engine,
        session_token=session_token,
        lease_secret=lease_secret,
    )
    if args.parent_pid:
        threading.Thread(
            target=stop_when_parent_exits,
            args=(server, args.parent_pid),
            daemon=True,
            name="kira-visual-parent-watch",
        ).start()
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
