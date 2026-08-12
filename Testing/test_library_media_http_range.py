import hashlib
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "Core"))

from library_media_http_range import (  # noqa: E402
    LibraryMediaHttpRange,
    LibraryMediaHttpRangeError,
    RangeNotSatisfiable,
    parse_single_byte_range,
)
from library_media_resolver import LibraryMediaResolver  # noqa: E402


class LibraryMediaHttpRangeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.library = self.root / "Data" / "library"
        self.library.mkdir(parents=True)
        self.resolver = LibraryMediaResolver(self.root)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def add(self, relative: str, content: bytes) -> Path:
        path = self.library / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    @staticmethod
    def body(response) -> bytes:
        return b"".join(response.iter_body())

    def test_small_non_range_pdf_is_200_read_only_and_chunk_bounded(self) -> None:
        content = b"%PDF-" + bytes(range(64))
        source = self.add("documents/manual.pdf", content)
        descriptor = self.resolver.resolve(source)
        before_paths = sorted(path.relative_to(self.root) for path in self.root.rglob("*"))
        before_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        helper = LibraryMediaHttpRange(
            self.root, max_non_range_bytes=128, read_chunk_bytes=11
        )

        response = helper.prepare(descriptor)
        chunks = list(response.iter_body())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "application/pdf")
        self.assertEqual(response.headers["Content-Length"], str(len(content)))
        self.assertEqual(response.headers["Accept-Ranges"], "bytes")
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertEqual(b"".join(chunks), content)
        self.assertTrue(all(0 < len(chunk) <= 11 for chunk in chunks))
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), before_hash)
        self.assertEqual(
            sorted(path.relative_to(self.root) for path in self.root.rglob("*")),
            before_paths,
        )

    def test_explicit_open_suffix_and_clamped_ranges_have_206_semantics(self) -> None:
        content = b"0123456789"
        source = self.add("movies/feature.mp4", content)
        descriptor = self.resolver.resolve(source)
        helper = LibraryMediaHttpRange(
            self.root,
            max_non_range_bytes=20,
            max_range_bytes=20,
            read_chunk_bytes=2,
        )

        cases = [
            ("bytes=2-5", b"2345", "bytes 2-5/10"),
            ("bytes=6-", b"6789", "bytes 6-9/10"),
            ("bytes=-3", b"789", "bytes 7-9/10"),
            ("bytes=7-999", b"789", "bytes 7-9/10"),
            ("Bytes = 0 - 0", b"0", "bytes 0-0/10"),
        ]
        for header, wanted_body, wanted_content_range in cases:
            with self.subTest(header=header):
                response = helper.prepare(descriptor, range_header=header)
                chunks = list(response.iter_body())
                self.assertEqual(response.status_code, 206)
                self.assertEqual(response.headers["Content-Range"], wanted_content_range)
                self.assertEqual(response.headers["Content-Length"], str(len(wanted_body)))
                self.assertEqual(b"".join(chunks), wanted_body)
                self.assertTrue(all(len(chunk) <= 2 for chunk in chunks))

    def test_malformed_multiple_and_unsatisfiable_ranges_return_416(self) -> None:
        source = self.add("audio/sample.wav", b"12345")
        descriptor = self.resolver.resolve(source)
        helper = LibraryMediaHttpRange(self.root)

        for header in (
            "items=0-1",
            "bytes=",
            "bytes=3-2",
            "bytes=5-5",
            "bytes=-0",
            "bytes=0-1,3-4",
            "bytes=0-1\r\nX-Injected: true",
            "garbage",
        ):
            with self.subTest(header=header):
                response = helper.prepare(descriptor, range_header=header)
                self.assertEqual(response.status_code, 416)
                self.assertEqual(response.headers["Content-Range"], "bytes */5")
                self.assertEqual(response.headers["Content-Length"], "0")
                self.assertEqual(list(response.iter_body()), [])

        empty = self.add("audio/empty.flac", b"")
        empty_response = helper.prepare(
            self.resolver.resolve(empty), range_header="bytes=0-0"
        )
        self.assertEqual(empty_response.status_code, 416)
        self.assertEqual(empty_response.headers["Content-Range"], "bytes */0")

    def test_non_range_and_range_caps_return_413_without_truncation(self) -> None:
        source = self.add("tv_shows/demo/episode.mkv", bytes(range(40)))
        descriptor = self.resolver.resolve(source)
        helper = LibraryMediaHttpRange(
            self.root,
            max_non_range_bytes=8,
            max_range_bytes=10,
            read_chunk_bytes=3,
        )

        non_range = helper.prepare(descriptor)
        oversized_range = helper.prepare(descriptor, range_header="bytes=0-10")
        allowed = helper.prepare(descriptor, range_header="bytes=5-14")

        self.assertEqual(non_range.status_code, 413)
        self.assertEqual(non_range.headers["X-Kira-Range-Required"], "true")
        self.assertEqual(list(non_range.iter_body()), [])
        self.assertEqual(oversized_range.status_code, 413)
        self.assertEqual(oversized_range.headers["X-Kira-Max-Range-Bytes"], "10")
        self.assertEqual(list(oversized_range.iter_body()), [])
        self.assertEqual(allowed.status_code, 206)
        self.assertEqual(self.body(allowed), bytes(range(5, 15)))

    def test_pdf_image_video_audio_mime_allowlist(self) -> None:
        cases = {
            "documents/file.pdf": "application/pdf",
            "documents/pages/page.png": "image/png",
            "movies/file.webm": "video/webm",
            "music/file.mp3": "audio/mpeg",
        }
        helper = LibraryMediaHttpRange(self.root, max_non_range_bytes=64)
        for relative, mime_type in cases.items():
            with self.subTest(relative=relative):
                source = self.add(relative, b"safe")
                response = helper.prepare(self.resolver.resolve(source))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.headers["Content-Type"], mime_type)
                self.assertEqual(self.body(response), b"safe")

        sidecar = self.add("movies/file.en.srt", b"captions")
        with self.assertRaisesRegex(LibraryMediaHttpRangeError, "supported PDF"):
            helper.prepare(self.resolver.resolve(sidecar))

    def test_tampered_or_stale_descriptor_is_rejected_before_serving(self) -> None:
        source = self.add("movies/exact.mp4", b"original")
        descriptor = self.resolver.resolve(source)
        helper = LibraryMediaHttpRange(self.root)

        tampered_hash = dict(descriptor)
        tampered_hash["sha256"] = "0" * 64
        with self.assertRaisesRegex(LibraryMediaHttpRangeError, "sha256"):
            helper.prepare(tampered_hash)

        tampered_size = dict(descriptor)
        tampered_size["size_bytes"] += 1
        with self.assertRaisesRegex(LibraryMediaHttpRangeError, "size_bytes"):
            helper.prepare(tampered_size)

        source.write_bytes(b"changed!")
        with self.assertRaisesRegex(LibraryMediaHttpRangeError, "sha256"):
            helper.prepare(descriptor)

    def test_source_change_after_prepare_blocks_body_iteration(self) -> None:
        source = self.add("music/change.flac", b"abcdefgh")
        descriptor = self.resolver.resolve(source)
        helper = LibraryMediaHttpRange(self.root, max_non_range_bytes=16)
        response = helper.prepare(descriptor)
        source.write_bytes(b"ABCDEFGH")

        with self.assertRaisesRegex(LibraryMediaHttpRangeError, "changed"):
            list(response.iter_body())

    def test_parser_contract_is_independent_and_deterministic(self) -> None:
        explicit = parse_single_byte_range("bytes=1-3", 8)
        suffix = parse_single_byte_range("bytes=-99", 8)
        self.assertEqual((explicit.start, explicit.end, explicit.length), (1, 3, 3))
        self.assertEqual((suffix.start, suffix.end, suffix.length), (0, 7, 8))
        with self.assertRaises(RangeNotSatisfiable):
            parse_single_byte_range("bytes=9-", 8)


if __name__ == "__main__":
    unittest.main()
