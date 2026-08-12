import hashlib
import json
import os
import pickle
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import fields
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "Core"))

from library_media_ephemeral_grants import (  # noqa: E402
    EphemeralLibraryMediaGrantManager,
    EphemeralPlaybackBinding,
    EphemeralPlaybackGrantCapacityError,
    EphemeralPlaybackGrantNotFound,
    EphemeralPlaybackGrantSourceChanged,
)
from library_media_resolver import LibraryMediaResolutionError, LibraryMediaResolver  # noqa: E402
from library_media_http_range import _file_identity  # noqa: E402


class ManualClock:
    def __init__(self, value: float = 50.0) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


class EphemeralLibraryMediaGrantTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.library = self.root / "Data" / "library"
        self.library.mkdir(parents=True)
        self.resolver = LibraryMediaResolver(self.root)
        self.binding = EphemeralPlaybackBinding(
            person_id="selected_person",
            activation_revision="activation-r4",
            session_id="media-session-9",
            session_nonce="opaque-session-nonce",
        )

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

    def test_grant_is_opaque_bound_nonserializable_and_has_no_path_receipt(self) -> None:
        source = self.add("movies/large.mkv", b"movie-content")
        descriptor = self.resolver.resolve(source)
        before_paths = sorted(path.relative_to(self.root) for path in self.root.rglob("*"))
        manager = EphemeralLibraryMediaGrantManager(self.root)

        receipt = manager.create_grant(descriptor, binding=self.binding, ttl_seconds=60)
        status = manager.lookup(receipt.token, binding=self.binding)

        self.assertGreaterEqual(len(receipt.token), 32)
        self.assertNotIn(str(self.root), receipt.token)
        self.assertNotIn(str(self.root), repr(receipt))
        self.assertNotIn("path", {field.name for field in fields(receipt)})
        self.assertNotIn("path", {field.name for field in fields(status)})
        self.assertEqual(receipt.grant_time_source_sha256, descriptor["sha256"])
        self.assertEqual(status.grant_time_source_sha256, descriptor["sha256"])
        self.assertEqual(status.range_request_count, 0)
        with self.assertRaises(TypeError):
            pickle.dumps(receipt)
        with self.assertRaises(TypeError):
            pickle.dumps(status)
        with self.assertRaises(TypeError):
            pickle.dumps(manager)
        with self.assertRaises(TypeError):
            json.dumps(receipt)
        self.assertEqual(
            sorted(path.relative_to(self.root) for path in self.root.rglob("*")),
            before_paths,
        )

    def test_every_identity_binding_field_is_required_exactly(self) -> None:
        source = self.add("music/song.flac", b"music")
        descriptor = self.resolver.resolve(source)
        manager = EphemeralLibraryMediaGrantManager(self.root)
        receipt = manager.create_grant(descriptor, binding=self.binding)

        replacements = {
            "person_id": "another_person",
            "activation_revision": "activation-r5",
            "session_id": "other-session",
            "session_nonce": "other-nonce",
        }
        for field_name, replacement in replacements.items():
            values = {
                "person_id": self.binding.person_id,
                "activation_revision": self.binding.activation_revision,
                "session_id": self.binding.session_id,
                "session_nonce": self.binding.session_nonce,
            }
            values[field_name] = replacement
            with self.subTest(field_name=field_name):
                with self.assertRaises(EphemeralPlaybackGrantNotFound):
                    manager.lookup(
                        receipt.token,
                        binding=EphemeralPlaybackBinding(**values),
                    )

    def test_short_ttl_lookup_and_thread_safe_purge(self) -> None:
        clock = ManualClock()
        source = self.add("documents/issue.pdf", b"pdf")
        descriptor = self.resolver.resolve(source)
        manager = EphemeralLibraryMediaGrantManager(
            self.root, clock=clock, default_ttl_seconds=2
        )
        receipt = manager.create_grant(descriptor, binding=self.binding)
        self.assertEqual(manager.active_count, 1)
        clock.advance(1.5)
        self.assertAlmostEqual(
            manager.lookup(receipt.token, binding=self.binding).expires_in_seconds,
            0.5,
        )
        clock.advance(0.5)
        self.assertEqual(manager.purge_expired(), 1)
        self.assertEqual(manager.active_count, 0)
        with self.assertRaises(EphemeralPlaybackGrantNotFound):
            manager.lookup(receipt.token, binding=self.binding)

    def test_valid_range_request_refreshes_short_idle_ttl(self) -> None:
        clock = ManualClock()
        source = self.add("movies/long_movie.mp4", b"0123456789")
        descriptor = self.resolver.resolve(source)
        manager = EphemeralLibraryMediaGrantManager(
            self.root,
            clock=clock,
            default_ttl_seconds=2,
            max_range_bytes=4,
        )
        receipt = manager.create_grant(descriptor, binding=self.binding)
        clock.advance(1.5)
        response = manager.prepare(
            receipt.token,
            binding=self.binding,
            range_header="bytes=0-3",
        )
        self.assertEqual(self.body(response), b"0123")
        clock.advance(1.0)
        self.assertEqual(manager.purge_expired(), 0)
        rejected = manager.prepare(
            receipt.token,
            binding=self.binding,
            range_header="bytes=99-99",
        )
        self.assertEqual(rejected.status_code, 416)
        self.assertAlmostEqual(
            manager.lookup(receipt.token, binding=self.binding).expires_in_seconds,
            1.0,
        )
        clock.advance(1.0)
        self.assertEqual(manager.purge_expired(), 1)

    def test_exact_session_heartbeat_refreshes_buffered_media_without_a_range_request(self) -> None:
        clock = ManualClock()
        source = self.add("movies/buffered.mp4", b"0123456789")
        descriptor = self.resolver.resolve(source)
        manager = EphemeralLibraryMediaGrantManager(
            self.root,
            clock=clock,
            default_ttl_seconds=2,
        )
        receipt = manager.create_grant(descriptor, binding=self.binding)
        clock.advance(1.5)

        refreshed = manager.refresh(receipt.token, binding=self.binding)

        self.assertAlmostEqual(refreshed.expires_in_seconds, 2.0)
        self.assertEqual(refreshed.range_request_count, 0)
        clock.advance(1.5)
        self.assertEqual(manager.purge_expired(), 0)
        clock.advance(0.5)
        self.assertEqual(manager.purge_expired(), 1)

    def test_capacity_revoke_and_concurrent_unique_token_creation(self) -> None:
        source = self.add("movies/capacity.mp4", b"video")
        descriptor = self.resolver.resolve(source)
        capped = EphemeralLibraryMediaGrantManager(self.root, max_active_grants=2)
        first = capped.create_grant(descriptor, binding=self.binding)
        capped.create_grant(descriptor, binding=self.binding)
        with self.assertRaises(EphemeralPlaybackGrantCapacityError):
            capped.create_grant(descriptor, binding=self.binding)
        self.assertTrue(capped.revoke(first.token, binding=self.binding))
        capped.create_grant(descriptor, binding=self.binding)
        self.assertEqual(capped.active_count, 2)

        concurrent = EphemeralLibraryMediaGrantManager(
            self.root, max_active_grants=16
        )
        with ThreadPoolExecutor(max_workers=8) as executor:
            receipts = list(
                executor.map(
                    lambda _index: concurrent.create_grant(
                        descriptor, binding=self.binding
                    ),
                    range(8),
                )
            )
        self.assertEqual(len({receipt.token for receipt in receipts}), 8)
        self.assertEqual(concurrent.active_count, 8)
        self.assertEqual(concurrent.purge_all(), 8)
        self.assertEqual(concurrent.active_count, 0)

    def test_range_requests_do_not_rehash_after_grant_creation(self) -> None:
        content = bytes(range(100))
        source = self.add("tv_shows/demo/episode.mkv", content)
        descriptor = self.resolver.resolve(source)
        manager = EphemeralLibraryMediaGrantManager(
            self.root,
            max_non_range_bytes=20,
            max_range_bytes=24,
            read_chunk_bytes=5,
        )
        with patch.object(
            manager._http._resolver,
            "resolve",
            wraps=manager._http._resolver.resolve,
        ) as exact_resolve:
            receipt = manager.create_grant(descriptor, binding=self.binding)
            self.assertEqual(exact_resolve.call_count, 1)

            with patch(
                "library_media_http_range._hash_with_identity",
                side_effect=AssertionError("range request must not rehash"),
            ):
                response = manager.prepare(
                    receipt.token,
                    binding=self.binding,
                    range_header="bytes=10-29",
                )
                chunks = list(response.iter_body())
            self.assertEqual(exact_resolve.call_count, 1)
        self.assertEqual(response.status_code, 206)
        self.assertEqual(response.headers["Content-Range"], "bytes 10-29/100")
        self.assertEqual(b"".join(chunks), content[10:30])
        self.assertTrue(all(len(chunk) <= 5 for chunk in chunks))
        self.assertEqual(
            manager.lookup(receipt.token, binding=self.binding).range_request_count,
            1,
        )

        no_range = manager.prepare(receipt.token, binding=self.binding)
        oversized = manager.prepare(
            receipt.token, binding=self.binding, range_header="bytes=0-24"
        )
        invalid = manager.prepare(
            receipt.token, binding=self.binding, range_header="bytes=100-100"
        )
        self.assertEqual(no_range.status_code, 413)
        self.assertEqual(oversized.status_code, 413)
        self.assertEqual(invalid.status_code, 416)

    def test_direct_selection_api_hashes_exactly_once_then_uses_identity(self) -> None:
        content = b"direct-selection-video"
        source = self.add("movies/direct.mp4", content)
        manager = EphemeralLibraryMediaGrantManager(
            self.root, max_non_range_bytes=64, read_chunk_bytes=4
        )

        with patch.object(
            manager._resolver,
            "resolve",
            wraps=manager._resolver.resolve,
        ) as exact_resolve:
            receipt = manager.create_grant_for_selection(
                "movies/direct.mp4", self.binding, 30
            )
            self.assertEqual(exact_resolve.call_count, 1)
            with patch(
                "library_media_http_range._hash_with_identity",
                side_effect=AssertionError("direct-selection range must not rehash"),
            ):
                response = manager.prepare(
                    receipt.token,
                    binding=self.binding,
                    range_header="bytes=7-15",
                )
                served = self.body(response)
            self.assertEqual(exact_resolve.call_count, 1)

        self.assertEqual(response.status_code, 206)
        self.assertEqual(served, content[7:16])
        self.assertEqual(
            receipt.grant_time_source_sha256,
            hashlib.sha256(content).hexdigest(),
        )

    def test_post_grant_stat_change_fails_closed_and_revokes(self) -> None:
        source = self.add("movies/change.mp4", b"abcdefgh")
        descriptor = self.resolver.resolve(source)
        manager = EphemeralLibraryMediaGrantManager(self.root)
        receipt = manager.create_grant(descriptor, binding=self.binding)

        original = source.stat()
        source.write_bytes(b"ABCDEFGH")
        os.utime(
            source,
            ns=(original.st_atime_ns, original.st_mtime_ns + 1_000_000_000),
        )
        with self.assertRaises(EphemeralPlaybackGrantSourceChanged):
            manager.prepare(
                receipt.token,
                binding=self.binding,
                range_header="bytes=0-3",
            )
        with self.assertRaises(EphemeralPlaybackGrantNotFound):
            manager.lookup(receipt.token, binding=self.binding)

    def test_revocation_stops_an_already_prepared_stream_before_next_chunk(self) -> None:
        source = self.add("movies/prepared.mp4", b"0123456789abcdef")
        descriptor = self.resolver.resolve(source)
        manager = EphemeralLibraryMediaGrantManager(
            self.root, max_range_bytes=16, read_chunk_bytes=4
        )
        receipt = manager.create_grant(descriptor, binding=self.binding)
        response = manager.prepare(
            receipt.token,
            binding=self.binding,
            range_header="bytes=0-15",
        )
        manager.revoke(receipt.token, binding=self.binding)
        with self.assertRaises(EphemeralPlaybackGrantNotFound):
            list(response.iter_body())

    def test_identity_change_between_hash_and_store_is_rejected(self) -> None:
        source = self.add("movies/hash-store-race.mp4", b"same-size")
        descriptor = self.resolver.resolve(source)
        manager = EphemeralLibraryMediaGrantManager(self.root)
        before = _file_identity(source)
        changed = (before[0], before[1], before[2], before[3] + 1, before[4] + 1)
        with patch(
            "library_media_ephemeral_grants._file_identity",
            side_effect=[before, changed],
        ):
            with self.assertRaises(EphemeralPlaybackGrantSourceChanged):
                manager.create_grant(descriptor, binding=self.binding)
        self.assertEqual(manager.active_count, 0)

    def test_link_or_containment_recheck_failure_revokes_without_rehash(self) -> None:
        source = self.add("movies/linkcheck.mp4", b"safe")
        descriptor = self.resolver.resolve(source)
        manager = EphemeralLibraryMediaGrantManager(self.root)
        receipt = manager.create_grant(descriptor, binding=self.binding)

        with patch.object(
            manager._resolver,
            "_candidate_for",
            side_effect=LibraryMediaResolutionError("simulated link escape"),
        ):
            with self.assertRaises(EphemeralPlaybackGrantSourceChanged):
                manager.prepare(receipt.token, binding=self.binding)
        self.assertEqual(manager.active_count, 0)

    def test_grant_creation_rejects_stale_descriptor_before_token_exists(self) -> None:
        source = self.add("music/stale.opus", b"first")
        descriptor = self.resolver.resolve(source)
        source.write_bytes(b"later")
        manager = EphemeralLibraryMediaGrantManager(self.root)
        with self.assertRaisesRegex(
            Exception, "exact resolver hash revalidation"
        ):
            manager.create_grant(descriptor, binding=self.binding)
        self.assertEqual(manager.active_count, 0)


if __name__ == "__main__":
    unittest.main()
