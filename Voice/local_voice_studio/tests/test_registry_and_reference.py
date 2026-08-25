from __future__ import annotations

import json
import hashlib
import hmac
import os
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from .support import generic_voice, source_voice, write_wav
from kira_local_voice.errors import ConflictError, ValidationError
from kira_local_voice.models import AuditionStatus, SourceBasis
from kira_local_voice.reference import inspect_wav
from kira_local_voice.registry import VoiceRegistry


class RegistryAndReferenceTests(unittest.TestCase):
    def test_reference_inspection_reads_metadata_and_hash_without_copying(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            wav_path = root / "reference.wav"
            expected_hash = write_wav(wav_path)
            before = sorted(path.name for path in root.iterdir())
            descriptor = inspect_wav(wav_path)
            self.assertEqual(descriptor.sha256, expected_hash)
            self.assertEqual(descriptor.sample_rate_hz, 16_000)
            self.assertEqual(descriptor.duration_seconds, 1.0)
            self.assertEqual(before, sorted(path.name for path in root.iterdir()))

    def test_reference_rejects_non_wav_and_invalid_wav(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            bad = root / "reference.txt"
            bad.write_text("private audio should never be copied", encoding="utf-8")
            with self.assertRaises(ValidationError):
                inspect_wav(bad)
            fake = root / "fake.wav"
            fake.write_bytes(b"not-wave")
            with self.assertRaises(ValidationError):
                inspect_wav(fake)

    def test_registry_is_immutable_and_round_trips_taxonomy(self):
        with tempfile.TemporaryDirectory() as raw:
            registry = VoiceRegistry(Path(raw))
            registered = registry.register(generic_voice())
            self.assertEqual(registered.source_basis, SourceBasis.GENERIC_FALLBACK)
            self.assertEqual(registered.audition_status, AuditionStatus.AUDITIONED)
            loaded = registry.get(registered.voice_id)
            self.assertEqual(loaded.to_dict(), registered.to_dict())
            with self.assertRaises(ConflictError):
                registry.register(replace(registered, display_name="Silent identity swap"))

    def test_source_voice_requires_consent_evidence_and_reference_hash(self):
        with tempfile.TemporaryDirectory() as raw:
            registry = VoiceRegistry(Path(raw))
            profile = source_voice("a" * 64)
            registry.register(profile)
            stored = json.loads((Path(raw) / "consented-source-v1.json").read_text(encoding="utf-8"))
            self.assertEqual(stored["profile"]["reference_hashes"], ["a" * 64])
            with self.assertRaises(ValidationError):
                registry.register(replace(profile, voice_id="bad-source", reference_hashes=()))

    def test_designed_or_generic_voice_cannot_hide_reference_recordings(self):
        with tempfile.TemporaryDirectory() as raw:
            registry = VoiceRegistry(Path(raw))
            with self.assertRaises(ValidationError):
                registry.register(replace(generic_voice(), reference_hashes=("a" * 64,)))

    def test_voice_id_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as raw:
            registry = VoiceRegistry(Path(raw))
            with self.assertRaises(ValidationError):
                registry.register(replace(generic_voice(), voice_id="../escape"))

    def test_consent_timestamps_must_be_zoned_and_ordered(self):
        with tempfile.TemporaryDirectory() as raw:
            registry = VoiceRegistry(Path(raw))
            base = generic_voice()
            with self.assertRaises(ValidationError):
                registry.register(
                    replace(base, voice_id="naive-time", consent=replace(base.consent, recorded_at="2026-08-25T12:00:00"))
                )
            with self.assertRaises(ValidationError):
                registry.register(
                    replace(base,voice_id="backward-expiry",
                        consent=replace(base.consent,expires_at="2020-01-01T00:00:00Z"))
                )
            with self.assertRaises(ValidationError):
                registry.register(replace(base,voice_id="future-consent",
                    consent=replace(base.consent,recorded_at="2999-01-01T00:00:00Z")))

    def test_reference_symlink_is_rejected_when_platform_allows_creation(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw); target=root/"real.wav"; write_wav(target); link=root/"link.wav"
            try: link.symlink_to(target)
            except OSError: self.skipTest("symlink creation is unavailable")
            with self.assertRaises(ValidationError): inspect_wav(link,allowed_root=root)

    def test_registry_detects_tampering_and_deactivation_is_append_only(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw); registry=VoiceRegistry(root); registry.register(generic_voice())
            record=root/"calm-fallback.json"; envelope=json.loads(record.read_text())
            envelope["profile"]["display_name"]="tampered"
            record.write_text(json.dumps(envelope),encoding="utf-8")
            with self.assertRaises(ValidationError): registry.get("calm-fallback")
        with tempfile.TemporaryDirectory() as raw:
            registry=VoiceRegistry(Path(raw)); registry.register(generic_voice())
            registry.deactivate("calm-fallback",authority="owner",reason="owner request")
            self.assertTrue(registry.is_deactivated("calm-fallback"))
            with self.assertRaises(ConflictError):
                registry.deactivate("calm-fallback",authority="owner",reason="again")

    def test_registry_integrity_is_keyed_outside_records_and_schema_is_revalidated(self):
        with tempfile.TemporaryDirectory() as raw:
            voices=Path(raw)/"voices"; registry=VoiceRegistry(voices); registry.register(generic_voice())
            self.assertEqual(registry.key_path.parent,voices.parent)
            self.assertFalse(registry.key_path.is_relative_to(voices))
            path=voices/"calm-fallback.json"; envelope=json.loads(path.read_text())
            envelope["profile"]["consent"]["generated_audio_permitted"]="yes"
            canonical=json.dumps(envelope["profile"],sort_keys=True,separators=(",", ":")).encode()
            envelope["profile_hmac_sha256"]=hmac.new(registry._key,canonical,hashlib.sha256).hexdigest()
            path.write_text(json.dumps(envelope),encoding="utf-8")
            with self.assertRaises(ValidationError): registry.get("calm-fallback")

    def test_deactivation_tampering_is_detected(self):
        with tempfile.TemporaryDirectory() as raw:
            registry=VoiceRegistry(Path(raw)/"voices"); registry.register(generic_voice())
            registry.deactivate("calm-fallback",authority="owner",reason="stop")
            path=registry.deactivation_root/"calm-fallback.json"; envelope=json.loads(path.read_text())
            envelope["record"]["reason"]="forged"; path.write_text(json.dumps(envelope),encoding="utf-8")
            with self.assertRaises(ValidationError): registry.is_deactivated("calm-fallback")

    def test_reference_rejects_a_file_identity_change_during_single_open_read(self):
        with tempfile.TemporaryDirectory() as raw:
            path=Path(raw)/"reference.wav"; write_wav(path)
            real_fstat=os.fstat; count=0
            def changed(fd):
                nonlocal count
                info=real_fstat(fd); count+=1
                if count!=2: return info
                values={name:getattr(info,name) for name in dir(info) if name.startswith("st_")}
                values["st_mtime_ns"]=info.st_mtime_ns+1
                return SimpleNamespace(**values)
            with mock.patch("kira_local_voice.reference.os.fstat",side_effect=changed):
                with self.assertRaises(ValidationError): inspect_wav(path)


if __name__ == "__main__":
    unittest.main()
