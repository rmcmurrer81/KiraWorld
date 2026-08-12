from __future__ import annotations

import http.client
import importlib
import io
import json
import sys
import threading
import unittest
from pathlib import Path
from unittest import mock

import numpy
from PIL import Image, ImageDraw


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.sensory_lease import SensoryLeaseError, issue_sensory_lease
from tools import kira_text_voice_visual_perception_sidecar as visual


LEASE_SECRET = "visual-sidecar-unit-test-secret-32-bytes-minimum"
SESSION_TOKEN = "visual-sidecar-test-token"


class FakeClock:
    def __init__(self, value: float = 1_800_000_000.0) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


class InMemoryImageBackend:
    """Test-only decoder; production remains OpenCV-only."""

    backend_name = "test_in_memory_backend"
    face_count_available = True

    def __init__(self, face_count: int = 0) -> None:
        self.face_count = face_count
        self.started: threading.Event | None = None
        self.release: threading.Event | None = None

    def derive_frame(self, jpeg_bytes: bytes) -> visual.DerivedFrame:
        if self.started is not None:
            self.started.set()
        if self.release is not None:
            self.release.wait(timeout=3)
        with Image.open(io.BytesIO(jpeg_bytes)) as image:
            self.assert_jpeg(image)
            gray = image.convert("L")
            width, height = gray.size
            pixels = numpy.asarray(gray, dtype=numpy.uint8)
            small = gray.resize(
                (visual.MOTION_GRID_WIDTH, visual.MOTION_GRID_HEIGHT),
                Image.Resampling.BOX,
            )
            grid = bytes(int(value) // 16 for value in numpy.asarray(small).reshape(-1))
            return visual.DerivedFrame(
                width=width,
                height=height,
                mean_luminance=float(pixels.mean()),
                coarse_face_count=self.face_count,
                motion_grid=grid,
            )

    @staticmethod
    def assert_jpeg(image: Image.Image) -> None:
        if image.format != "JPEG":
            raise visual.InvalidTransientJpeg("test payload is not JPEG")


def generated_jpeg(
    luminance: int,
    *,
    size: tuple[int, int] = (96, 64),
    rectangle: tuple[int, int, int, int] | None = None,
) -> bytes:
    image = Image.new("L", size, color=luminance)
    if rectangle is not None:
        ImageDraw.Draw(image).rectangle(rectangle, fill=255 - luminance)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=88)
    return buffer.getvalue()


def claims(person: str = "kira", revision: str = "r1", nonce: str = "nonce-1") -> dict:
    return {
        "person_id": person,
        "activation_revision": revision,
        "nonce": nonce,
    }


def cue_value(result: dict, name: str):
    return next(cue["value"] for cue in result["cues"] if cue["name"] == name)


class VisualPerceptionSidecarTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = FakeClock()
        self.backend = InMemoryImageBackend()
        self.engine = visual.VisualCueEngine(backend=self.backend, clock=self.clock)

    def test_loopback_binding_is_mandatory(self) -> None:
        for host in ("127.0.0.1", "127.12.0.4", "::1", "localhost"):
            with self.subTest(host=host):
                self.assertTrue(visual.is_loopback_host(host))
                self.assertEqual(visual.require_loopback_host(host), host)
        for host in ("0.0.0.0", "192.168.1.12", "8.8.8.8", "example.com", ""):
            with self.subTest(host=host):
                self.assertFalse(visual.is_loopback_host(host))
                with self.assertRaisesRegex(ValueError, "loopback"):
                    visual.require_loopback_host(host)

    def test_signed_lease_requires_exact_person_activation_and_unexpired_signature(self) -> None:
        token = issue_sensory_lease(
            LEASE_SECRET,
            person_id="temporary_person_42",
            activation_revision="activation-7",
            ttl_seconds=30,
            clock=self.clock,
            nonce="signed-test-nonce",
        )
        valid = visual.validate_bound_lease(
            token,
            LEASE_SECRET,
            person_id="temporary_person_42",
            activation_revision="activation-7",
            clock=self.clock,
        )
        self.assertEqual(valid["nonce"], "signed-test-nonce")
        for person, revision, candidate in (
            ("different_person", "activation-7", token),
            ("temporary_person_42", "activation-8", token),
            ("temporary_person_42", "activation-7", token[:-1] + "A"),
        ):
            with self.subTest(person=person, revision=revision):
                with self.assertRaises(SensoryLeaseError):
                    visual.validate_bound_lease(
                        candidate,
                        LEASE_SECRET,
                        person_id=person,
                        activation_revision=revision,
                        clock=self.clock,
                    )
        self.clock.advance(30)
        with self.assertRaisesRegex(SensoryLeaseError, "expired"):
            visual.validate_bound_lease(
                token,
                LEASE_SECRET,
                person_id="temporary_person_42",
                activation_revision="activation-7",
                clock=self.clock,
            )

    def test_generated_jpeg_produces_only_non_identifying_derived_cues(self) -> None:
        self.backend.face_count = 3
        result = self.engine.process_transient_jpeg(
            generated_jpeg(220),
            lease_claims=claims(person="arbitrary_person", revision="rev-2"),
        )
        self.assertTrue(result["ok"])
        self.assertEqual(cue_value(result, "frame_size"), {"width": 96, "height": 64})
        self.assertEqual(cue_value(result, "brightness_class"), "bright")
        self.assertEqual(cue_value(result, "coarse_face_count"), "multiple")
        self.assertEqual(cue_value(result, "motion_class"), "baseline_unavailable")
        self.assertEqual(result["lease_person_id"], "arbitrary_person")
        for key in (
            "raw_frame_persisted",
            "raw_frame_replayed",
            "raw_frame_hashed",
            "identity_inference_performed",
            "spoken_generated",
            "memory_written",
            "consent_changed",
            "relationship_changed",
            "qwen_used",
            "online_service_used",
        ):
            self.assertFalse(result[key])
        serialized = json.dumps(result).lower()
        self.assertNotIn("jpeg_bytes", serialized)
        self.assertNotIn("recognized_person", serialized)
        self.assertEqual(self.engine.retained_derived_bytes, 16 * 12)

    def test_brightness_classes_are_bounded(self) -> None:
        cases = ((20, "dark"), (80, "dim"), (140, "balanced"), (230, "bright"))
        for index, (level, expected) in enumerate(cases):
            with self.subTest(level=level):
                result = self.engine.process_transient_jpeg(
                    generated_jpeg(level),
                    lease_claims=claims(nonce=f"brightness-{index}"),
                )
                self.assertEqual(cue_value(result, "brightness_class"), expected)

    def test_motion_uses_only_quantized_grid_and_resets_on_person_or_activation_switch(self) -> None:
        first = generated_jpeg(20, rectangle=(4, 12, 35, 50))
        second = generated_jpeg(20, rectangle=(58, 12, 90, 50))
        first_result = self.engine.process_transient_jpeg(first, lease_claims=claims())
        second_result = self.engine.process_transient_jpeg(second, lease_claims=claims())
        self.assertEqual(cue_value(first_result, "motion_class"), "baseline_unavailable")
        self.assertIn(cue_value(second_result, "motion_class"), {"moderate", "high"})
        switched = self.engine.process_transient_jpeg(
            second,
            lease_claims=claims(person="lisa", revision="r9", nonce="nonce-9"),
        )
        self.assertEqual(cue_value(switched, "motion_class"), "baseline_unavailable")
        self.assertTrue(self.engine.purge(claims(person="lisa", revision="r9", nonce="nonce-9")))
        self.assertEqual(self.engine.retained_derived_bytes, 0)

    def test_strict_jpeg_byte_and_format_limits_fail_before_backend(self) -> None:
        for invalid in (
            b"",
            b"not-a-jpeg",
            b"\x89PNG\r\n\x1a\n",
            b"\xff\xd8" + (b"x" * visual.MAX_JPEG_BYTES) + b"\xff\xd9",
        ):
            with self.subTest(length=len(invalid)):
                with self.assertRaises(visual.InvalidTransientJpeg):
                    self.engine.process_transient_jpeg(invalid, lease_claims=claims())
        self.assertEqual(self.engine.retained_derived_bytes, 0)

    def test_only_one_transient_frame_can_be_processed_at_a_time(self) -> None:
        self.backend.started = threading.Event()
        self.backend.release = threading.Event()
        failures: list[BaseException] = []

        def first_request() -> None:
            try:
                self.engine.process_transient_jpeg(
                    generated_jpeg(100),
                    lease_claims=claims(),
                )
            except BaseException as exc:  # pragma: no cover - diagnostic capture
                failures.append(exc)

        thread = threading.Thread(target=first_request)
        thread.start()
        self.assertTrue(self.backend.started.wait(timeout=2))
        try:
            with self.assertRaises(visual.VisualSidecarBusy):
                self.engine.process_transient_jpeg(
                    generated_jpeg(120),
                    lease_claims=claims(),
                )
        finally:
            self.backend.release.set()
            thread.join(timeout=3)
        self.assertFalse(thread.is_alive())
        self.assertEqual(failures, [])

    def test_missing_all_local_decoders_returns_clean_capability_unavailable(self) -> None:
        engine = visual.VisualCueEngine(
            backend_loader=lambda: (None, "opencv_not_installed"),
            clock=self.clock,
        )
        health = visual.health_payload(engine=engine)
        self.assertEqual(health["status"], "capability_unavailable")
        self.assertFalse(health["capability"]["available"])
        self.assertEqual(health["capability"]["reason"], "opencv_not_installed")
        with self.assertRaisesRegex(visual.VisualCapabilityUnavailable, "opencv_not_installed"):
            engine.process_transient_jpeg(generated_jpeg(100), lease_claims=claims())
        self.assertEqual(engine.retained_derived_bytes, 0)

    def test_local_opencv_probe_does_not_install_or_hide_unavailability(self) -> None:
        with mock.patch.object(
            visual.importlib,
            "import_module",
            side_effect=ModuleNotFoundError("cv2 unavailable"),
        ) as importer:
            backend, reason = visual.load_local_opencv_backend()
        self.assertIsNone(backend)
        self.assertEqual(reason, "opencv_not_installed")
        importer.assert_called_once_with("cv2")

    def test_forced_cv2_unavailable_uses_reduced_in_memory_pillow_fallback(self) -> None:
        real_import_module = importlib.import_module

        def import_without_cv2(name: str):
            if name == "cv2":
                raise ModuleNotFoundError("cv2 deliberately unavailable")
            return real_import_module(name)

        with mock.patch.object(
            visual.importlib,
            "import_module",
            side_effect=import_without_cv2,
        ):
            backend, reason = visual.load_local_visual_backend()
        self.assertEqual(reason, "")
        self.assertIsInstance(backend, visual.LocalPillowFallbackBackend)

        fallback_engine = visual.VisualCueEngine(backend=backend, clock=self.clock)
        first = fallback_engine.process_transient_jpeg(
            generated_jpeg(225, rectangle=(4, 8, 30, 48)),
            lease_claims=claims(),
        )
        second = fallback_engine.process_transient_jpeg(
            generated_jpeg(225, rectangle=(62, 8, 91, 48)),
            lease_claims=claims(),
        )
        capability = fallback_engine.capability()
        self.assertTrue(capability["available"])
        self.assertTrue(capability["reduced_pillow_fallback"])
        self.assertEqual(capability["backend"], "local_pillow_fallback")
        self.assertFalse(capability["face_count_available"])
        self.assertFalse(capability["face_recognition_available"])
        self.assertFalse(capability["person_recognition_available"])
        self.assertFalse(capability["robert_recognition_available"])
        self.assertEqual(cue_value(first, "frame_size"), {"width": 96, "height": 64})
        self.assertEqual(cue_value(first, "brightness_class"), "balanced")
        self.assertEqual(cue_value(first, "coarse_face_count"), "unavailable")
        self.assertEqual(cue_value(first, "motion_class"), "baseline_unavailable")
        self.assertIn(cue_value(second, "motion_class"), {"low", "moderate", "high"})
        self.assertEqual(first["source"], "local_pillow_fallback_transient_jpeg")
        self.assertEqual(first["face_recognition_status"], "unavailable_not_performed")
        self.assertEqual(first["person_recognition_status"], "unavailable_not_performed")
        self.assertEqual(first["robert_recognition_status"], "unavailable_not_performed")
        self.assertFalse(first["identity_inference_performed"])
        self.assertEqual(fallback_engine.retained_derived_bytes, 16 * 12)

    def test_loopback_http_route_validates_lease_and_processes_in_memory_jpeg(self) -> None:
        token = issue_sensory_lease(
            LEASE_SECRET,
            person_id="kira",
            activation_revision="activation-http",
            ttl_seconds=60,
            clock=self.clock,
            nonce="http-nonce",
        )
        server = visual.VisualPerceptionHTTPServer(
            ("127.0.0.1", 0),
            engine=self.engine,
            session_token=SESSION_TOKEN,
            lease_secret=LEASE_SECRET,
            clock=self.clock,
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        connection = http.client.HTTPConnection(
            "127.0.0.1",
            server.server_address[1],
            timeout=3,
        )
        headers = {
            "Content-Type": "image/jpeg",
            "X-Kira-Visual-Token": SESSION_TOKEN,
            "X-Kira-Person": "kira",
            "X-Kira-Activation-Revision": "activation-http",
            "X-Kira-Sensory-Lease": token,
            "Origin": "http://127.0.0.1:8768",
        }
        try:
            connection.request("POST", "/api/derive-cues", generated_jpeg(140), headers=headers)
            response = connection.getresponse()
            payload = json.loads(response.read().decode("utf-8"))
            self.assertEqual(response.status, 200)
            self.assertTrue(payload["ok"])
            self.assertEqual(cue_value(payload, "brightness_class"), "balanced")

            connection.close()
            connection = http.client.HTTPConnection(
                "127.0.0.1",
                server.server_address[1],
                timeout=3,
            )
            bad_headers = dict(headers)
            bad_headers["X-Kira-Activation-Revision"] = "wrong-activation"
            connection.request(
                "POST",
                "/api/derive-cues",
                generated_jpeg(140),
                headers=bad_headers,
            )
            bad_response = connection.getresponse()
            bad_payload = json.loads(bad_response.read().decode("utf-8"))
            self.assertEqual(bad_response.status, 409)
            self.assertEqual(bad_payload["error"], "sensory_lease_invalid")
        finally:
            connection.close()
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

    def test_source_has_no_camera_capture_identity_model_network_or_frame_persistence(self) -> None:
        source = (
            PROJECT_ROOT / "tools" / "kira_text_voice_visual_perception_sidecar.py"
        ).read_text(encoding="utf-8")
        for forbidden in (
            "VideoCapture(",
            "imwrite(",
            "import face_recognition",
            "face_recognition.load_image_file",
            "FaceRecognizer",
            "ollama",
            "requests.",
            "urlopen(",
            "hashlib",
            "write_bytes(",
            "write_text(",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
