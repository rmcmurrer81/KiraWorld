from __future__ import annotations

import ctypes
from ctypes import wintypes
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
import unicodedata

from tools import kira_r25_canonical_receipt as receipt


def raw_frame(payload: bytes, *, digest: bytes | None = None, length: int | None = None) -> bytes:
    return receipt.RECEIPT_HEADER.pack(
        receipt.RECEIPT_MAGIC,
        receipt.RECEIPT_VERSION,
        len(payload) if length is None else length,
        hashlib.sha256(payload).digest() if digest is None else digest,
    ) + payload


class CanonicalReceiptFrameTests(unittest.TestCase):
    def test_01_fixture_round_trip_is_deterministic(self) -> None:
        payload = {
            "schema": "kira.avatar.r25.harmless_fixture.v1",
            "status": "FIXTURE_ONLY",
            "values": [3, True, None, "Kira"],
        }
        frame = receipt.encode_receipt_frame(payload)
        self.assertEqual(frame, receipt.encode_receipt_frame(dict(reversed(list(payload.items())))))
        decoded = receipt.decode_receipt_frame(frame)
        self.assertEqual(decoded.payload, payload)
        self.assertEqual(decoded.canonical_payload, receipt.canonical_json_bytes(payload))
        self.assertEqual(decoded.frame_sha256, hashlib.sha256(frame).hexdigest())

    def test_02_truncated_and_trailing_frames_fail_closed(self) -> None:
        frame = receipt.encode_receipt_frame({"schema": "fixture", "status": "OK"})
        for candidate, code in (
            (frame[: receipt.RECEIPT_HEADER_BYTES - 1], "TRUNCATED_HEADER"),
            (frame[:-1], "TRUNCATED_PAYLOAD"),
            (frame + b"x", "TRAILING_BYTES"),
        ):
            with self.subTest(code=code):
                with self.assertRaises(receipt.ReceiptFrameError) as raised:
                    receipt.decode_receipt_frame(candidate)
                self.assertEqual(raised.exception.code, code)

    def test_03_digest_magic_version_and_maximum_fail_closed(self) -> None:
        payload = b'{"schema":"fixture"}'
        cases = []
        cases.append((raw_frame(payload, digest=b"\x00" * 32), "DIGEST_MISMATCH"))
        wrong_magic = bytearray(raw_frame(payload))
        wrong_magic[0] ^= 1
        cases.append((bytes(wrong_magic), "MAGIC_MISMATCH"))
        wrong_version = receipt.RECEIPT_HEADER.pack(
            receipt.RECEIPT_MAGIC,
            receipt.RECEIPT_VERSION + 1,
            len(payload),
            hashlib.sha256(payload).digest(),
        ) + payload
        cases.append((wrong_version, "VERSION_MISMATCH"))
        too_large = receipt.RECEIPT_HEADER.pack(
            receipt.RECEIPT_MAGIC,
            receipt.RECEIPT_VERSION,
            receipt.MAX_RECEIPT_PAYLOAD_BYTES + 1,
            hashlib.sha256(b"").digest(),
        )
        cases.append((too_large, "PAYLOAD_TOO_LARGE"))
        for candidate, code in cases:
            with self.subTest(code=code):
                with self.assertRaises(receipt.ReceiptFrameError) as raised:
                    receipt.decode_receipt_frame(candidate)
                self.assertEqual(raised.exception.code, code)

    def test_04_noncanonical_duplicate_and_float_payloads_fail_closed(self) -> None:
        noncanonical = b'{"status": "OK", "schema": "fixture"}'
        duplicate = b'{"schema":"one","schema":"two"}'
        floating = b'{"schema":"fixture","value":1.5}'
        for payload, code in (
            (noncanonical, "NONCANONICAL_JSON"),
            (duplicate, "DUPLICATE_KEY"),
            (floating, "FLOAT_FORBIDDEN"),
        ):
            with self.subTest(code=code):
                with self.assertRaises(receipt.ReceiptFrameError) as raised:
                    receipt.decode_receipt_frame(raw_frame(payload))
                self.assertEqual(raised.exception.code, code)

    @unittest.skipUnless(os.name == "nt", "Win32 CREATE_NEW semantics are Windows-only")
    def test_05_parent_holds_exact_create_new_receipt_and_commits_fixture(self) -> None:
        payload = {"schema": "kira.avatar.r25.harmless_fixture.v1", "status": "FIXTURE_ONLY"}
        frame = receipt.encode_receipt_frame(payload)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "receipt.frame"
            reservation = receipt.WindowsExclusiveReceiptReservation.reserve(path)
            try:
                self.assertTrue(path.exists())
                kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
                kernel32.CreateFileW.argtypes = [
                    wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
                    wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
                ]
                kernel32.CreateFileW.restype = wintypes.HANDLE
                competing = kernel32.CreateFileW(
                    str(path),
                    0x40000000,
                    0x00000001 | 0x00000002 | 0x00000004,
                    None,
                    3,
                    0x00000080,
                    None,
                )
                self.assertEqual(competing, ctypes.c_void_p(-1).value)
                self.assertEqual(ctypes.get_last_error(), 32)
                decoded = reservation.accept_child_frame(frame)
                self.assertEqual(decoded.payload, payload)
                self.assertEqual(path.read_bytes(), frame)
            finally:
                reservation.close()
            original = path.read_bytes()
            with self.assertRaises(receipt.ReceiptPersistenceError):
                receipt.WindowsExclusiveReceiptReservation.reserve(path)
            self.assertEqual(path.read_bytes(), original)

    @unittest.skipUnless(os.name == "nt", "Win32 CREATE_NEW semantics are Windows-only")
    def test_06_invalid_child_consumes_slot_with_append_only_failure_truth(self) -> None:
        invalid = receipt.encode_receipt_frame({"schema": "fixture", "status": "BAD"}) + b"trailing"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "receipt.frame"
            with receipt.WindowsExclusiveReceiptReservation.reserve(path) as reservation:
                with self.assertRaises(receipt.ReceiptFrameError) as raised:
                    reservation.accept_child_frame(invalid)
                self.assertEqual(raised.exception.code, "TRAILING_BYTES")
                self.assertTrue(reservation.written)
                persisted = receipt.decode_receipt_frame(path.read_bytes()).payload
                self.assertEqual(persisted["status"], "REJECTED_APPEND_ONLY")
                self.assertEqual(persisted["failure_code"], "TRAILING_BYTES")
                self.assertEqual(persisted["received_sha256"], hashlib.sha256(invalid).hexdigest())
            self.assertTrue(path.exists())

    def test_07_helper_is_transport_and_process_inert(self) -> None:
        source = Path(receipt.__file__).read_text(encoding="utf-8")
        self.assertNotIn("import subprocess", source)
        self.assertNotIn("subprocess.Popen", source)
        self.assertNotIn("CreatePipe", source)
        self.assertNotIn("CreateNamedPipe", source)
        self.assertNotIn("import bpy", source)

    def test_08_pre_json_depth_and_node_bounds_return_receipt_errors(self) -> None:
        deep = (
            b'{"value":'
            + b"[" * receipt.MAX_RECEIPT_DEPTH
            + b"0"
            + b"]" * receipt.MAX_RECEIPT_DEPTH
            + b"}"
        )
        wide = (
            b'{"value":['
            + b",".join([b"0"] * receipt.MAX_RECEIPT_NODES)
            + b"]}"
        )
        for payload, code in ((deep, "DEPTH_LIMIT"), (wide, "NODE_LIMIT")):
            with self.subTest(code=code):
                with self.assertRaises(receipt.ReceiptFrameError) as raised:
                    receipt.decode_receipt_frame(raw_frame(payload))
                self.assertEqual(raised.exception.code, code)

    def test_09_exact_maximum_passes_and_one_byte_more_fails_before_deep_work(self) -> None:
        empty = receipt.canonical_json_bytes({"pad": ""})
        payload = {"pad": "x" * (receipt.MAX_RECEIPT_PAYLOAD_BYTES - len(empty))}
        frame = receipt.encode_receipt_frame(payload)
        self.assertEqual(len(frame), receipt.MAX_RECEIPT_FRAME_BYTES)
        self.assertEqual(receipt.decode_receipt_frame(frame).payload, payload)
        with self.assertRaises(receipt.ReceiptFrameError) as raised:
            receipt.encode_receipt_frame({"pad": payload["pad"] + "x"})
        self.assertEqual(raised.exception.code, "PAYLOAD_TOO_LARGE")
        with self.assertRaises(receipt.ReceiptFrameError) as raised:
            receipt.decode_receipt_frame(frame + b"x")
        self.assertEqual(raised.exception.code, "FRAME_TOO_LARGE")

    def test_10_nested_duplicate_unicode_surrogate_and_nfc_rules(self) -> None:
        nested_duplicate = b'{"outer":{"same":1,"same":2}}'
        decomposed = "e\u0301"
        non_nfc = ('{"value":"' + decomposed + '"}').encode("utf-8")
        surrogate = b'{"value":"\\ud800"}'
        for payload, code in (
            (nested_duplicate, "DUPLICATE_KEY"),
            (non_nfc, "STRING_NOT_NFC"),
            (surrogate, "SURROGATE_FORBIDDEN"),
        ):
            with self.subTest(code=code):
                with self.assertRaises(receipt.ReceiptFrameError) as raised:
                    receipt.decode_receipt_frame(raw_frame(payload))
                self.assertEqual(raised.exception.code, code)
        composed = unicodedata.normalize("NFC", decomposed)
        self.assertEqual(receipt.decode_receipt_frame(receipt.encode_receipt_frame({"value": composed})).payload["value"], composed)
        with self.assertRaises(receipt.ReceiptFrameError) as raised:
            receipt.encode_receipt_frame({"value": decomposed})
        self.assertEqual(raised.exception.code, "STRING_NOT_NFC")

    def test_11_boolean_and_signed_64_bit_integer_subset(self) -> None:
        payload = {
            "false": False,
            "maximum": receipt.MAX_RECEIPT_INTEGER,
            "minimum": receipt.MIN_RECEIPT_INTEGER,
            "true": True,
        }
        self.assertEqual(receipt.decode_receipt_frame(receipt.encode_receipt_frame(payload)).payload, payload)
        for value in (receipt.MIN_RECEIPT_INTEGER - 1, receipt.MAX_RECEIPT_INTEGER + 1):
            with self.subTest(value=value):
                with self.assertRaises(receipt.ReceiptFrameError) as raised:
                    receipt.encode_receipt_frame({"value": value})
                self.assertEqual(raised.exception.code, "INTEGER_RANGE")

    @unittest.skipUnless(os.name == "nt", "Win32 CREATE_NEW semantics are Windows-only")
    def test_12_nonbytes_rejection_records_no_immutable_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "receipt.frame"
            with receipt.WindowsExclusiveReceiptReservation.reserve(path) as reservation:
                with self.assertRaises(receipt.ReceiptFrameError) as raised:
                    reservation.accept_child_frame(bytearray(b"not immutable"))
                self.assertEqual(raised.exception.code, "FRAME_TYPE")
                persisted = receipt.decode_receipt_frame(path.read_bytes()).payload
                self.assertFalse(persisted["immutable_byte_snapshot_available"])
                self.assertIsNone(persisted["received_bytes"])
                self.assertIsNone(persisted["received_sha256"])
                self.assertEqual(persisted["received_type"], "bytearray")

    @unittest.skipUnless(os.name == "nt", "Win32 CREATE_NEW semantics are Windows-only")
    def test_13_graceful_unused_close_persists_abandoned_record(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "receipt.frame"
            reservation = receipt.WindowsExclusiveReceiptReservation.reserve(path)
            reservation.close()
            persisted = receipt.decode_receipt_frame(path.read_bytes()).payload
            self.assertEqual(persisted["status"], "ABANDONED_UNUSED")
            self.assertEqual(persisted["reason"], "GRACEFUL_CLOSE_WITHOUT_CHILD_FRAME")
            self.assertTrue(reservation.consumed)
            self.assertTrue(reservation.written)
            self.assertFalse(reservation.poisoned)

    def test_14_every_post_write_failure_poison_prevents_retry(self) -> None:
        class FakeKernel:
            def __init__(self, mode: str) -> None:
                self.mode = mode
                self.write_calls = 0
                self.reservation = None
                self.pre_io_states = []

            def WriteFile(self, handle, buffer, length, written_pointer, overlapped):
                del handle, buffer, overlapped
                self.write_calls += 1
                self.pre_io_states.append(
                    (self.reservation.consumed, self.reservation.poisoned)
                )
                amount = length - 1 if self.mode == "partial" else length
                ctypes.cast(written_pointer, ctypes.POINTER(wintypes.DWORD)).contents.value = amount
                return True

            def FlushFileBuffers(self, handle):
                del handle
                return self.mode != "flush"

            def GetFileSizeEx(self, handle, size_pointer):
                del handle
                if self.mode == "size_call":
                    return False
                size = 0 if self.mode == "size_mismatch" else len(frame)
                ctypes.cast(size_pointer, ctypes.POINTER(ctypes.c_longlong)).contents.value = size
                return True

            def CloseHandle(self, handle):
                del handle
                return True

        frame = receipt.encode_receipt_frame({"schema": "fixture", "status": "OK"})
        for mode in ("partial", "flush", "size_call", "size_mismatch", "readback"):
            with self.subTest(mode=mode):
                kernel = FakeKernel(mode)
                reservation = receipt.WindowsExclusiveReceiptReservation(Path("unused"), 1, kernel)
                kernel.reservation = reservation
                with self.assertRaises(receipt.ReceiptPersistenceError):
                    reservation._write_once(frame)
                self.assertTrue(reservation.consumed)
                self.assertTrue(reservation.poisoned)
                self.assertFalse(reservation.written)
                with self.assertRaises(receipt.ReceiptPersistenceError):
                    reservation._write_once(frame)
                self.assertEqual(kernel.write_calls, 1)
                self.assertEqual(kernel.pre_io_states, [(True, True)])
                reservation.close()

    @unittest.skipUnless(os.name == "nt", "Win32 CREATE_NEW semantics are Windows-only")
    def test_15_deep_child_becomes_terminal_rejection_evidence(self) -> None:
        payload = (
            b'{"value":'
            + b"[" * receipt.MAX_RECEIPT_DEPTH
            + b"0"
            + b"]" * receipt.MAX_RECEIPT_DEPTH
            + b"}"
        )
        deep_frame = raw_frame(payload)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "receipt.frame"
            with receipt.WindowsExclusiveReceiptReservation.reserve(path) as reservation:
                with self.assertRaises(receipt.ReceiptFrameError) as raised:
                    reservation.accept_child_frame(deep_frame)
                self.assertEqual(raised.exception.code, "DEPTH_LIMIT")
                self.assertTrue(reservation.consumed)
                self.assertTrue(reservation.written)
                self.assertFalse(reservation.poisoned)
                persisted = receipt.decode_receipt_frame(path.read_bytes()).payload
                self.assertEqual(persisted["status"], "REJECTED_APPEND_ONLY")
                self.assertEqual(persisted["failure_code"], "DEPTH_LIMIT")


if __name__ == "__main__":
    unittest.main()
