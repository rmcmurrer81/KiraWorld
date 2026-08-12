"""Source-bound resident-media preparation and presentation evidence.

This module bridges the existing exact-item media access policy and
``MediaExperienceSession`` truth record to real local decoders.  It can:

* render one exact PDF page/crop to a hash-bound raster while keeping OCR and
  the PDF text layer separate from the pixels;
* decode a bounded video interval into timestamped visual samples plus actual
  audio-sample statistics and caption-stream metadata; and
* decode a bounded music interval into actual PCM-derived measurements.

Preparation alone never means that a selected person saw or heard anything.
Only an explicit reviewed presentation receipt causes presentation and
observation events to enter ``MediaExperienceSession``.  The evidence is
private, append-only, model-neutral, and creates no memory, canon, preference,
publication, consciousness, or biological-humanity claim.

The module also provides a small prepare-only CLI::

    py -B -m Core.source_bound_media_experience pdf --source ... --page 1

The CLI deliberately has no speaker-playback, display, Qwen, Llama, network,
or production-chat route.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import secrets
import shutil
import subprocess
import sys
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping, Protocol, Sequence

from Core.media_classification_corrections import (
    MediaClassificationCorrectionStore,
)
from Core.media_experience_session import MediaExperienceSession
from Core.shared_person_media_access import (
    SharedPersonMediaAccessPolicy,
    media_id_for_path,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE_ROOT = (
    PROJECT_ROOT
    / "RecoverySprint"
    / "continuation_20260802"
    / "source_bound_resident_media_experience"
)
DEFAULT_CORRECTION_LEDGER = (
    PROJECT_ROOT
    / "Data"
    / "owner_corrections"
    / "media_classification_corrections.jsonl"
)

EVIDENCE_SCHEMA = "kira.source_bound_resident_media_experience.v1"
PRESENTATION_RECEIPT_SCHEMA = "kira.reviewed_media_presentation_receipt.v1"
MANIFEST_SCHEMA = "kira.append_only_media_evidence_manifest.v1"
MAX_INTERVAL_SECONDS = 30.0
MAX_FRAME_COUNT = 8
MAX_RASTER_PIXELS = 24_000_000
MAX_PCM_BYTES = 64 * 1024 * 1024
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T.*Z$")


class SourceBoundMediaExperienceError(RuntimeError):
    """Raised when evidence cannot be created without overstating truth."""


class MediaPresentationAuthorizationRequired(SourceBoundMediaExperienceError):
    """A non-adult selected a mature item without a live co-view decision."""


class OcrProvider(Protocol):
    """Reviewed OCR adapter used only when a caller explicitly supplies one."""

    def __call__(self, raster_path: Path) -> Mapping[str, Any]: ...


@dataclass(frozen=True, slots=True)
class ReviewedPresentationReceipt:
    """Explicit caller attestation that bytes reached a reviewed output.

    A receipt is deliberately not issued by this module.  A reviewed display
    or audio-output surface creates it after successful output.  Attention is
    recorded only when ``person_attention_confirmed`` is true; output alone is
    never treated as proof of attention.
    """

    receipt_id: str
    surface_id: str
    issued_at_utc: str
    actual_visual_output: bool
    actual_audio_output: bool
    person_attention_confirmed: bool
    observed_modalities: tuple[str, ...]
    page_presented_duration_seconds: float | None = None
    page_observed_duration_seconds: float | None = None

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ReviewedPresentationReceipt":
        expected = {
            "schema",
            "receipt_id",
            "surface_id",
            "issued_at_utc",
            "actual_visual_output",
            "actual_audio_output",
            "person_attention_confirmed",
            "observed_modalities",
            "page_presented_duration_seconds",
            "page_observed_duration_seconds",
        }
        if not isinstance(value, Mapping) or set(value) != expected:
            raise SourceBoundMediaExperienceError(
                "presentation receipt does not match the exact reviewed schema."
            )
        if value.get("schema") != PRESENTATION_RECEIPT_SCHEMA:
            raise SourceBoundMediaExperienceError(
                "presentation receipt schema is unsupported."
            )
        receipt_id = _canonical_id(value.get("receipt_id"), "receipt_id")
        surface_id = _canonical_id(value.get("surface_id"), "surface_id")
        issued = str(value.get("issued_at_utc") or "")
        if not UTC_RE.fullmatch(issued):
            raise SourceBoundMediaExperienceError(
                "presentation receipt must contain an exact UTC timestamp."
            )
        try:
            datetime.fromisoformat(issued[:-1] + "+00:00")
        except ValueError as exc:
            raise SourceBoundMediaExperienceError(
                "presentation receipt UTC timestamp is malformed."
            ) from exc
        booleans: dict[str, bool] = {}
        for field in (
            "actual_visual_output",
            "actual_audio_output",
            "person_attention_confirmed",
        ):
            item = value.get(field)
            if not isinstance(item, bool):
                raise SourceBoundMediaExperienceError(
                    f"presentation receipt {field} must be boolean."
                )
            booleans[field] = item
        raw_modalities = value.get("observed_modalities")
        if not isinstance(raw_modalities, (list, tuple)):
            raise SourceBoundMediaExperienceError(
                "presentation receipt observed_modalities must be a list."
            )
        modalities = tuple(str(item).strip().lower() for item in raw_modalities)
        if len(set(modalities)) != len(modalities) or any(
            item not in {"visual", "audio", "audiovisual"} for item in modalities
        ):
            raise SourceBoundMediaExperienceError(
                "presentation receipt observed modalities are invalid."
            )
        if bool(modalities) != booleans["person_attention_confirmed"]:
            raise SourceBoundMediaExperienceError(
                "confirmed person attention and observed modalities must agree."
            )
        presented = _optional_positive_number(
            value.get("page_presented_duration_seconds"),
            "page_presented_duration_seconds",
        )
        observed = _optional_positive_number(
            value.get("page_observed_duration_seconds"),
            "page_observed_duration_seconds",
        )
        if observed is not None and presented is None:
            raise SourceBoundMediaExperienceError(
                "page observation requires a page presentation duration."
            )
        if observed is not None and observed > float(presented) + 1e-9:
            raise SourceBoundMediaExperienceError(
                "page observation duration exceeds page presentation."
            )
        if observed is not None and not booleans["person_attention_confirmed"]:
            raise SourceBoundMediaExperienceError(
                "page observation duration requires confirmed person attention."
            )
        return cls(
            receipt_id=receipt_id,
            surface_id=surface_id,
            issued_at_utc=issued,
            actual_visual_output=booleans["actual_visual_output"],
            actual_audio_output=booleans["actual_audio_output"],
            person_attention_confirmed=booleans["person_attention_confirmed"],
            observed_modalities=modalities,
            page_presented_duration_seconds=presented,
            page_observed_duration_seconds=observed,
        )


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _canonical_id(value: object, field: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,255}", value
    ):
        raise SourceBoundMediaExperienceError(f"{field} is not a canonical identifier.")
    return value


def _finite_number(value: object, field: str, *, minimum: float = 0.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SourceBoundMediaExperienceError(f"{field} must be a finite number.")
    result = float(value)
    if not math.isfinite(result) or result < minimum:
        raise SourceBoundMediaExperienceError(f"{field} is outside its allowed range.")
    return result


def _optional_positive_number(value: object, field: str) -> float | None:
    if value is None:
        return None
    result = _finite_number(value, field)
    if result <= 0:
        raise SourceBoundMediaExperienceError(f"{field} must be greater than zero.")
    return result


def _normalized_crop(value: Sequence[float] | Mapping[str, float]) -> dict[str, float]:
    if isinstance(value, Mapping):
        if set(value) != {"x", "y", "width", "height"}:
            raise SourceBoundMediaExperienceError(
                "crop must contain exactly x, y, width, and height."
            )
        raw = [value["x"], value["y"], value["width"], value["height"]]
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        if len(value) != 4:
            raise SourceBoundMediaExperienceError("crop must contain four numbers.")
        raw = list(value)
    else:
        raise SourceBoundMediaExperienceError("crop must be a mapping or sequence.")
    x, y = (_finite_number(raw[index], f"crop[{index}]") for index in (0, 1))
    width = _finite_number(raw[2], "crop.width")
    height = _finite_number(raw[3], "crop.height")
    if width <= 0 or height <= 0 or x + width > 1.0 + 1e-9 or y + height > 1.0 + 1e-9:
        raise SourceBoundMediaExperienceError(
            "normalized crop must be nonempty and remain within the page."
        )
    return {"x": x, "y": y, "width": width, "height": height}


def _policy_record(correction: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "correction_id": (
            f"media_classification_correction_{int(correction['append_sequence']):08d}"
        ),
        "media_id": correction["opaque_media_id"],
        "file_sha256": correction["file_sha256"],
        "project_relative_library_path": correction[
            "project_relative_library_path"
        ],
        "resulting_access_category": correction["resulting_access_category"],
        "resulting_content_rating": correction["resulting_content_rating"],
        "corrected_at_utc": correction["correction_utc"],
    }


class AppendOnlyEvidenceStore:
    """Allocate attempt directories and write files without overwrite paths."""

    def __init__(self, project_root: Path, evidence_root: Path) -> None:
        self.project_root = project_root.resolve(strict=True)
        candidate = evidence_root
        if not candidate.is_absolute():
            candidate = self.project_root / candidate
        candidate = candidate.resolve(strict=False)
        try:
            candidate.relative_to(self.project_root)
        except ValueError as exc:
            raise SourceBoundMediaExperienceError(
                "evidence root must remain inside the exact project root."
            ) from exc
        self.root = candidate

    def allocate(self) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        for sequence in range(1, 10_000):
            attempt = self.root / f"attempt_{sequence:02d}"
            try:
                attempt.mkdir(exist_ok=False)
            except FileExistsError:
                continue
            (attempt / "artifacts").mkdir(exist_ok=False)
            return attempt
        raise SourceBoundMediaExperienceError(
            "append-only evidence attempt namespace is exhausted."
        )

    @staticmethod
    def write_bytes(path: Path, value: bytes) -> None:
        with path.open("xb") as handle:
            handle.write(value)
            handle.flush()

    @classmethod
    def write_json(cls, path: Path, value: Any) -> None:
        cls.write_bytes(path, canonical_json_bytes(value) + b"\n")


class SourceBoundResidentMediaExperience:
    """Prepare exact local media and optionally record reviewed presentation."""

    def __init__(
        self,
        *,
        project_root: str | Path = PROJECT_ROOT,
        evidence_root: str | Path = DEFAULT_EVIDENCE_ROOT,
        access_config_path: str | Path | None = None,
        media_index_path: str | Path | None = None,
        identity_registry_path: str | Path | None = None,
        correction_ledger_path: str | Path | None = None,
        utc_clock: Callable[[], str] = utc_now,
    ) -> None:
        self.project_root = Path(project_root).resolve(strict=True)
        self.library_root = (self.project_root / "Data" / "library").resolve(
            strict=True
        )
        self.store = AppendOnlyEvidenceStore(
            self.project_root, Path(evidence_root)
        )
        self.access_config_path = access_config_path
        self.media_index_path = media_index_path
        self.identity_registry_path = identity_registry_path
        self.correction_ledger_path = (
            Path(correction_ledger_path)
            if correction_ledger_path is not None
            else self.project_root
            / "Data"
            / "owner_corrections"
            / "media_classification_corrections.jsonl"
        )
        if not callable(utc_clock):
            raise SourceBoundMediaExperienceError("utc_clock must be callable.")
        self.utc_clock = utc_clock

    def _policy(self) -> SharedPersonMediaAccessPolicy:
        return SharedPersonMediaAccessPolicy(
            self.project_root,
            access_config_path=self.access_config_path,
            media_index_path=self.media_index_path,
            identity_registry_path=self.identity_registry_path,
        )

    def _resolve_source(
        self,
        source: str | Path,
        *,
        viewer: str,
        allowed_suffixes: set[str],
    ) -> tuple[Path, dict[str, Any]]:
        candidate = Path(source)
        if not candidate.is_absolute():
            candidate = self.project_root / candidate
        try:
            resolved = candidate.resolve(strict=True)
        except (OSError, FileNotFoundError) as exc:
            raise SourceBoundMediaExperienceError(
                "the exact media source does not exist."
            ) from exc
        if not resolved.is_file() or resolved.suffix.lower() not in allowed_suffixes:
            raise SourceBoundMediaExperienceError(
                "the source is not an allowed exact media file for this operation."
            )
        try:
            relative = resolved.relative_to(self.library_root)
        except ValueError as exc:
            raise SourceBoundMediaExperienceError(
                "the media source must resolve inside Data/library."
            ) from exc
        canonical = "Data/library/" + relative.as_posix()
        if PurePosixPath(canonical).parts[:2] != ("Data", "library"):
            raise SourceBoundMediaExperienceError("media path binding is malformed.")
        file_hash = sha256_file(resolved)
        media_id = media_id_for_path(canonical)
        policy = self._policy()
        correction: dict[str, Any] | None = None
        ledger = self.correction_ledger_path
        if ledger.is_file():
            store = MediaClassificationCorrectionStore(
                ledger,
                allowed_root=ledger.parent,
            )
            correction = store.latest_for(media_id, file_hash)
            if correction is not None:
                policy.apply_owner_correction(_policy_record(correction))
        entry = policy.authorize_path(viewer, canonical)
        actual_size = resolved.stat().st_size
        if int(entry.get("size_bytes") or 0) != actual_size:
            raise SourceBoundMediaExperienceError(
                "the sealed media-index size does not match the exact file."
            )
        if entry.get("requires_adult_coview"):
            raise MediaPresentationAuthorizationRequired(
                "this exact item requires a fresh in-process adult co-view decision; "
                "prepare-only evidence cannot create or reuse that decision."
            )
        correction_record_hash = (
            None if correction is None else sha256_bytes(canonical_json_bytes(correction))
        )
        return resolved, {
            "opaque_media_id": media_id,
            "project_relative_library_path": canonical,
            "source_sha256": file_hash,
            "source_size_bytes": actual_size,
            "viewer_person_id": viewer,
            "viewer_maturity_lane": policy.maturity_lane(viewer),
            "access_category": entry["access_class"],
            "content_rating": entry.get("content_rating", ""),
            "classification_source": entry["classification_source"],
            "playback_status": entry["playback_status"],
            "requires_adult_coview": False,
            "exact_owner_correction_applied": correction is not None,
            "owner_correction_append_sequence": (
                None if correction is None else correction["append_sequence"]
            ),
            "owner_correction_record_sha256": correction_record_hash,
            "correction_lookup_key": {
                "opaque_media_id": media_id,
                "file_sha256": file_hash,
            },
        }

    def _session(
        self,
        *,
        source: Path,
        kind: str,
        viewer: str,
        activation_revision: str,
        media_duration_seconds: float | None = None,
    ) -> MediaExperienceSession:
        return MediaExperienceSession(
            project_root=self.project_root,
            source_path=source,
            kind=kind,
            person_id=_canonical_id(viewer, "viewer"),
            activation_revision=_canonical_id(
                activation_revision, "activation_revision"
            ),
            session_id=f"source_bound_media_{uuid.uuid4().hex}",
            session_nonce=secrets.token_urlsafe(32),
            media_duration_seconds=media_duration_seconds,
        )

    def prepare_pdf_page(
        self,
        source: str | Path,
        *,
        viewer: str,
        activation_revision: str,
        page_number: int,
        crop: Sequence[float] | Mapping[str, float] = (0.0, 0.0, 1.0, 1.0),
        zoom: float = 1.5,
        ocr_provider: OcrProvider | None = None,
        presentation_receipt: Mapping[str, Any] | None = None,
    ) -> Path:
        """Create one append-only exact-page evidence package."""

        attempt = self.store.allocate()
        try:
            path, access = self._resolve_source(
                source, viewer=viewer, allowed_suffixes={".pdf"}
            )
            evidence = self._build_pdf_evidence(
                attempt,
                path=path,
                access=access,
                viewer=viewer,
                activation_revision=activation_revision,
                page_number=page_number,
                crop=crop,
                zoom=zoom,
                ocr_provider=ocr_provider,
                presentation_receipt=presentation_receipt,
            )
            return self._seal_attempt(attempt, evidence)
        except Exception as exc:
            self._preserve_failure(attempt, exc)
            raise

    def prepare_video_interval(
        self,
        source: str | Path,
        *,
        viewer: str,
        activation_revision: str,
        start_seconds: float,
        end_seconds: float,
        frame_count: int = 3,
        pause_at_seconds: float | None = None,
        presentation_receipt: Mapping[str, Any] | None = None,
    ) -> Path:
        """Decode one bounded video interval without claiming a full viewing."""

        attempt = self.store.allocate()
        try:
            path, access = self._resolve_source(
                source,
                viewer=viewer,
                allowed_suffixes={".mp4", ".mkv", ".avi", ".mov", ".webm", ".wmv", ".m4v"},
            )
            evidence = self._build_timed_evidence(
                attempt,
                path=path,
                access=access,
                viewer=viewer,
                activation_revision=activation_revision,
                media_kind="video",
                start_seconds=start_seconds,
                end_seconds=end_seconds,
                frame_count=frame_count,
                pause_at_seconds=pause_at_seconds,
                presentation_receipt=presentation_receipt,
            )
            return self._seal_attempt(attempt, evidence)
        except Exception as exc:
            self._preserve_failure(attempt, exc)
            raise

    def prepare_music_interval(
        self,
        source: str | Path,
        *,
        viewer: str,
        activation_revision: str,
        start_seconds: float,
        end_seconds: float,
        pause_at_seconds: float | None = None,
        presentation_receipt: Mapping[str, Any] | None = None,
    ) -> Path:
        """Decode actual audio samples for one bounded music interval."""

        attempt = self.store.allocate()
        try:
            path, access = self._resolve_source(
                source,
                viewer=viewer,
                allowed_suffixes={".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".opus"},
            )
            evidence = self._build_timed_evidence(
                attempt,
                path=path,
                access=access,
                viewer=viewer,
                activation_revision=activation_revision,
                media_kind="music",
                start_seconds=start_seconds,
                end_seconds=end_seconds,
                frame_count=0,
                pause_at_seconds=pause_at_seconds,
                presentation_receipt=presentation_receipt,
            )
            return self._seal_attempt(attempt, evidence)
        except Exception as exc:
            self._preserve_failure(attempt, exc)
            raise

    def _build_pdf_evidence(
        self,
        attempt: Path,
        *,
        path: Path,
        access: Mapping[str, Any],
        viewer: str,
        activation_revision: str,
        page_number: int,
        crop: Sequence[float] | Mapping[str, float],
        zoom: float,
        ocr_provider: OcrProvider | None,
        presentation_receipt: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        try:
            import fitz
        except ImportError as exc:  # pragma: no cover - dependency gate
            raise SourceBoundMediaExperienceError(
                "PyMuPDF is required for exact PDF-page rendering."
            ) from exc
        if isinstance(page_number, bool) or not isinstance(page_number, int) or page_number < 1:
            raise SourceBoundMediaExperienceError(
                "page_number must be a one-based positive integer."
            )
        normalized_crop = _normalized_crop(crop)
        exact_zoom = _finite_number(zoom, "zoom")
        if not 0.25 <= exact_zoom <= 4.0:
            raise SourceBoundMediaExperienceError("zoom must be within 0.25..4.0.")
        with fitz.open(path) as document:
            if page_number > document.page_count:
                raise SourceBoundMediaExperienceError(
                    "page_number exceeds the exact PDF page count."
                )
            page = document.load_page(page_number - 1)
            rect = page.rect
            clip = fitz.Rect(
                rect.x0 + rect.width * normalized_crop["x"],
                rect.y0 + rect.height * normalized_crop["y"],
                rect.x0
                + rect.width
                * (normalized_crop["x"] + normalized_crop["width"]),
                rect.y0
                + rect.height
                * (normalized_crop["y"] + normalized_crop["height"]),
            )
            expected_pixels = int(math.ceil(clip.width * exact_zoom)) * int(
                math.ceil(clip.height * exact_zoom)
            )
            if expected_pixels <= 0 or expected_pixels > MAX_RASTER_PIXELS:
                raise SourceBoundMediaExperienceError(
                    "requested PDF raster exceeds the bounded pixel limit."
                )
            pixmap = page.get_pixmap(
                matrix=fitz.Matrix(exact_zoom, exact_zoom),
                clip=clip,
                alpha=False,
                colorspace=fitz.csRGB,
            )
            target = attempt / "artifacts" / f"page_{page_number:04d}_crop.png"
            pixmap.save(target)
            text_layer = page.get_text("text", clip=clip)
            page_count = document.page_count
            page_rect_points = {
                "width": float(rect.width),
                "height": float(rect.height),
            }
        raster_hash = sha256_file(target)
        raster_relative = target.relative_to(self.project_root).as_posix()
        text_layer_bytes = text_layer.encode("utf-8")
        text_layer_record = {
            "provenance_kind": "pdf_text_layer_not_ocr",
            "page_number": page_number,
            "crop": normalized_crop,
            "content_sha256": sha256_bytes(text_layer_bytes),
            "character_count": len(text_layer),
            "raw_text_stored": False,
            "counts_as_visual_page_observation": False,
            "counts_as_ocr": False,
        }
        ocr_record: dict[str, Any]
        if ocr_provider is None:
            ocr_record = {
                "status": "NOT_RUN_NO_REVIEWED_OCR_ADAPTER",
                "provenance_kind": "ocr",
                "source_raster_sha256": raster_hash,
                "text_sha256": None,
                "character_count": 0,
                "engine": None,
                "engine_version": None,
                "language": None,
                "raw_text_stored": False,
                "counts_as_visual_page_observation": False,
            }
        else:
            supplied = ocr_provider(target)
            expected = {"text", "engine", "engine_version", "language"}
            if not isinstance(supplied, Mapping) or set(supplied) != expected:
                raise SourceBoundMediaExperienceError(
                    "reviewed OCR adapter returned an invalid exact result."
                )
            ocr_text = supplied["text"]
            if (
                not isinstance(ocr_text, str)
                or len(ocr_text) > 8_000_000
                or "\x00" in ocr_text
            ):
                raise SourceBoundMediaExperienceError(
                    "OCR text must be bounded, well-formed text."
                )
            ocr_bytes = ocr_text.encode("utf-8")
            ocr_record = {
                "status": "COMPLETED_BY_REVIEWED_ADAPTER",
                "provenance_kind": "ocr",
                "source_raster_sha256": raster_hash,
                "text_sha256": sha256_bytes(ocr_bytes),
                "character_count": len(ocr_text),
                "engine": _bounded_text(supplied["engine"], "OCR engine"),
                "engine_version": _bounded_text(
                    supplied["engine_version"], "OCR engine version"
                ),
                "language": _bounded_text(supplied["language"], "OCR language"),
                "raw_text_stored": False,
                "counts_as_visual_page_observation": False,
            }
        session = self._session(
            source=path,
            kind="pdf",
            viewer=viewer,
            activation_revision=activation_revision,
        )
        lease = session.lease
        receipt = (
            None
            if presentation_receipt is None
            else ReviewedPresentationReceipt.from_mapping(presentation_receipt)
        )
        if receipt is not None:
            if not receipt.actual_visual_output or receipt.actual_audio_output:
                raise SourceBoundMediaExperienceError(
                    "PDF presentation requires visual output only."
                )
            if receipt.page_presented_duration_seconds is None:
                raise SourceBoundMediaExperienceError(
                    "PDF presentation receipt requires its exact duration."
                )
            presentation = session.present_page(
                lease,
                page_number=page_number,
                crop=normalized_crop,
                zoom=exact_zoom,
                duration_seconds=receipt.page_presented_duration_seconds,
            )
            if receipt.person_attention_confirmed:
                if set(receipt.observed_modalities) != {"visual"}:
                    raise SourceBoundMediaExperienceError(
                        "PDF attention can be recorded only as visual."
                    )
                if receipt.page_observed_duration_seconds is None:
                    raise SourceBoundMediaExperienceError(
                        "confirmed PDF attention requires observed duration."
                    )
                session.observe_page(
                    lease,
                    presentation_id=presentation["presentation_id"],
                    duration_seconds=receipt.page_observed_duration_seconds,
                )
            session.finish(lease)
        if ocr_record["status"] == "COMPLETED_BY_REVIEWED_ADAPTER":
            session.add_text_provenance(
                lease,
                provenance_kind="ocr",
                content_sha256=ocr_record["text_sha256"],
                page_number=page_number,
                language=ocr_record["language"],
                label=(
                    f"{ocr_record['engine']} {ocr_record['engine_version']} "
                    "over exact raster"
                ),
            )
        session.close(lease)
        return self._base_evidence(
            attempt,
            media_kind="pdf_page",
            access=access,
            source=path,
            receipt=receipt,
            preparation={
                "coverage": "ONE_EXACT_PDF_PAGE_CROP_ONLY",
                "page_count": page_count,
                "page_number": page_number,
                "page_index_zero_based": page_number - 1,
                "crop_normalized": normalized_crop,
                "page_rect_points": page_rect_points,
                "zoom": exact_zoom,
                "raster": {
                    "project_relative_path": raster_relative,
                    "sha256": raster_hash,
                    "size_bytes": target.stat().st_size,
                    "width_pixels": pixmap.width,
                    "height_pixels": pixmap.height,
                    "colorspace": "RGB",
                    "format": "PNG",
                },
                "pdf_text_layer": text_layer_record,
                "ocr": ocr_record,
                "whole_publication_read_claim": False,
            },
            session_snapshot=session.snapshot(),
            qwen_assets=[
                {
                    "role": "exact_pdf_page_pixels",
                    "project_relative_path": raster_relative,
                    "sha256": raster_hash,
                    "coverage": "ONE_EXACT_PDF_PAGE_CROP_ONLY",
                }
            ],
            separate_text_provenance=[text_layer_record, ocr_record],
        )

    def _build_timed_evidence(
        self,
        attempt: Path,
        *,
        path: Path,
        access: Mapping[str, Any],
        viewer: str,
        activation_revision: str,
        media_kind: str,
        start_seconds: float,
        end_seconds: float,
        frame_count: int,
        pause_at_seconds: float | None,
        presentation_receipt: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        start = _finite_number(start_seconds, "start_seconds")
        end = _finite_number(end_seconds, "end_seconds")
        if end <= start or end - start > MAX_INTERVAL_SECONDS + 1e-9:
            raise SourceBoundMediaExperienceError(
                f"media interval must be positive and no longer than {MAX_INTERVAL_SECONDS} seconds."
            )
        probe = _probe_media(path)
        duration = float(probe["duration_seconds"])
        if end > duration + 0.05:
            raise SourceBoundMediaExperienceError(
                "requested interval exceeds the probed media duration."
            )
        pause_at: float | None = None
        if pause_at_seconds is not None:
            pause_at = _finite_number(pause_at_seconds, "pause_at_seconds")
            if not start < pause_at < end:
                raise SourceBoundMediaExperienceError(
                    "pause_at_seconds must be strictly inside the interval."
                )
        video_streams = probe["streams"]["video"]
        audio_streams = probe["streams"]["audio"]
        if media_kind == "video" and not video_streams:
            raise SourceBoundMediaExperienceError("video source has no decodable video stream.")
        if media_kind == "music" and not audio_streams:
            raise SourceBoundMediaExperienceError("music source has no decodable audio stream.")
        frames: list[dict[str, Any]] = []
        if media_kind == "video":
            if isinstance(frame_count, bool) or not 1 <= frame_count <= MAX_FRAME_COUNT:
                raise SourceBoundMediaExperienceError(
                    f"frame_count must be within 1..{MAX_FRAME_COUNT}."
                )
            timestamps = [
                start + (end - start) * (index + 0.5) / frame_count
                for index in range(frame_count)
            ]
            for ordinal, timestamp in enumerate(timestamps, start=1):
                target = attempt / "artifacts" / f"video_frame_{ordinal:02d}.png"
                decoded = _extract_video_frame(path, target, timestamp)
                decoded["ordinal"] = ordinal
                decoded["project_relative_path"] = target.relative_to(
                    self.project_root
                ).as_posix()
                frames.append(decoded)
        audio_decode = (
            _decode_audio_interval(path, start=start, end=end, stream=audio_streams[0])
            if audio_streams
            else {
                "status": "NO_AUDIO_STREAM",
                "requested_interval": {
                    "start_seconds": start,
                    "end_seconds": end,
                    "duration_seconds": end - start,
                },
                "raw_audio_stored": False,
            }
        )
        receipt = (
            None
            if presentation_receipt is None
            else ReviewedPresentationReceipt.from_mapping(presentation_receipt)
        )
        if receipt is not None:
            if media_kind == "video":
                if not receipt.actual_visual_output:
                    raise SourceBoundMediaExperienceError(
                        "video presentation requires actual visual output."
                    )
                if audio_streams and not receipt.actual_audio_output:
                    raise SourceBoundMediaExperienceError(
                        "a video with audio requires actual audio output for audiovisual presentation truth."
                    )
                allowed_modalities = {"visual", "audio", "audiovisual"}
            else:
                if not receipt.actual_audio_output or receipt.actual_visual_output:
                    raise SourceBoundMediaExperienceError(
                        "music presentation requires actual audio output only."
                    )
                allowed_modalities = {"audio"}
            if not set(receipt.observed_modalities).issubset(allowed_modalities):
                raise SourceBoundMediaExperienceError(
                    "presentation receipt contains an impossible observation modality."
                )
            if (
                receipt.page_presented_duration_seconds is not None
                or receipt.page_observed_duration_seconds is not None
            ):
                raise SourceBoundMediaExperienceError(
                    "timed-media receipt must not contain page durations."
                )
        session = self._session(
            source=path,
            kind=media_kind,
            viewer=viewer,
            activation_revision=activation_revision,
            media_duration_seconds=duration,
        )
        lease = session.lease
        if receipt is not None:
            if start > 0:
                session.seek(lease, to_media_seconds=start)
            session.resume(lease)
            if pause_at is not None:
                session.pause(lease, at_media_seconds=pause_at)
                session.resume(lease)
            session.pause(lease, at_media_seconds=end)
            if receipt.person_attention_confirmed:
                for modality in receipt.observed_modalities:
                    session.observe_interval(
                        lease,
                        start_seconds=start,
                        end_seconds=end,
                        modality=modality,
                    )
            session.finish(lease, at_media_seconds=end)
        session.close(lease)
        if media_kind == "video":
            coverage = "BOUNDED_VIDEO_INTERVAL_WITH_SAMPLED_VISUAL_FRAMES"
            qwen_assets = [
                {
                    "role": "timestamped_video_frame",
                    "ordinal": frame["ordinal"],
                    "requested_timestamp_seconds": frame[
                        "requested_timestamp_seconds"
                    ],
                    "decoded_pts_seconds": frame["decoded_pts_seconds"],
                    "project_relative_path": frame["project_relative_path"],
                    "sha256": frame["sha256"],
                }
                for frame in frames
            ]
            separate_text = [
                {
                    "provenance_kind": "embedded_caption_stream_metadata",
                    "stream_count": len(probe["streams"]["subtitle"]),
                    "streams": probe["streams"]["subtitle"],
                    "caption_text_extracted": False,
                    "counts_as_watched": False,
                }
            ]
        else:
            coverage = "BOUNDED_ACTUAL_AUDIO_SAMPLE_INTERVAL"
            qwen_assets = []
            separate_text = [
                {
                    "provenance_kind": "container_and_stream_metadata",
                    "metadata_read": True,
                    "counts_as_listened": False,
                }
            ]
        return self._base_evidence(
            attempt,
            media_kind=media_kind,
            access=access,
            source=path,
            receipt=receipt,
            preparation={
                "coverage": coverage,
                "source_probe": probe,
                "requested_interval": {
                    "start_seconds": start,
                    "end_seconds": end,
                    "duration_seconds": end - start,
                },
                "pause_at_seconds": pause_at,
                "video_frames": frames,
                "audio_decode": audio_decode,
                "embedded_caption_streams": probe["streams"]["subtitle"],
                "caption_or_subtitle_text_extracted": False,
                "sampled_frames_equal_full_viewing": False,
                "full_source_watched_claim": False,
                "full_track_listened_claim": False,
                "filename_or_metadata_counts_as_listening": False,
                "lyrics_counts_as_listening": False,
                "raw_audio_stored": False,
            },
            session_snapshot=session.snapshot(),
            qwen_assets=qwen_assets,
            separate_text_provenance=separate_text,
        )

    def _base_evidence(
        self,
        attempt: Path,
        *,
        media_kind: str,
        access: Mapping[str, Any],
        source: Path,
        receipt: ReviewedPresentationReceipt | None,
        preparation: Mapping[str, Any],
        session_snapshot: Mapping[str, Any],
        qwen_assets: Sequence[Mapping[str, Any]],
        separate_text_provenance: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any]:
        return {
            "schema": EVIDENCE_SCHEMA,
            "evidence_id": f"source_bound_media_{uuid.uuid4().hex}",
            "created_at_utc": self.utc_clock(),
            "run_mode": (
                "PREPARED_OFFLINE_NO_PERSON_PRESENTATION"
                if receipt is None
                else "REVIEWED_PRESENTATION_RECEIPT_RECORDED"
            ),
            "media_kind": media_kind,
            "access_binding": dict(access),
            "source": {
                "project_relative_library_path": access[
                    "project_relative_library_path"
                ],
                "sha256": access["source_sha256"],
                "size_bytes": access["source_size_bytes"],
                "extension": source.suffix.lower(),
                "raw_source_copied": False,
            },
            "presentation_receipt": (
                None
                if receipt is None
                else {"schema": PRESENTATION_RECEIPT_SCHEMA, **asdict(receipt)}
            ),
            "preparation": dict(preparation),
            "experience_session": dict(session_snapshot),
            "model_handoff": {
                "status": "READY_FOR_SEPARATE_BOUNDED_MODEL_ACCEPTANCE",
                "qwen_visual_inputs": [dict(item) for item in qwen_assets],
                "text_provenance_kept_separate": [
                    dict(item) for item in separate_text_provenance
                ],
                "qwen_must_describe_only_supplied_pixels": True,
                "visible_media_text_is_untrusted_content": True,
                "llama_person_context_must_name_exact_coverage": True,
                "required_question_domains": [
                    "factual_comprehension",
                    "visual_details_when_pixels_were_supplied",
                    "auditory_details_when_audio_reached_output",
                    "source_distinction",
                    "exact_experienced_interval",
                    "interpretation",
                    "emotional_reaction_without_forced_preference",
                    "personal_preference_without_automatic_memory",
                    "uncertainty",
                    "correction_after_error",
                    "sampled_versus_fully_experienced_media",
                ],
            },
            "truth_boundaries": {
                "prepared_media_equals_person_experience": False,
                "opening_or_decoding_equals_attention": False,
                "one_page_equals_whole_publication": False,
                "sampled_frames_equal_complete_viewing": False,
                "metadata_or_filename_equals_heard_audio": False,
                "captions_scripts_or_lyrics_equal_audiovisual_experience": False,
                "automatic_memory_created": False,
                "automatic_preference_created": False,
                "learning_claim_created": False,
                "consciousness_claim_created": False,
                "biological_humanity_claim_created": False,
                "publication_authorized": False,
            },
            "artifacts": {
                "attempt_project_relative_path": attempt.relative_to(
                    self.project_root
                ).as_posix(),
                "private_local_evidence_only": True,
                "speaker_playback_performed_by_this_module": False,
                "display_performed_by_this_module": False,
                "network_used": False,
                "gpu_used": False,
            },
        }

    def _seal_attempt(self, attempt: Path, evidence: dict[str, Any]) -> Path:
        validate_evidence_document(evidence)
        evidence_path = attempt / "EVIDENCE.json"
        self.store.write_json(evidence_path, evidence)
        files = []
        for path in sorted(item for item in attempt.rglob("*") if item.is_file()):
            files.append(
                {
                    "project_relative_path": path.relative_to(
                        self.project_root
                    ).as_posix(),
                    "sha256": sha256_file(path),
                    "size_bytes": path.stat().st_size,
                }
            )
        manifest = {
            "schema": MANIFEST_SCHEMA,
            "sealed_at_utc": self.utc_clock(),
            "append_only_attempt": attempt.name,
            "evidence_schema": EVIDENCE_SCHEMA,
            "files": files,
            "overwrite_permitted": False,
        }
        self.store.write_json(attempt / "MANIFEST.json", manifest)
        return attempt

    def _preserve_failure(self, attempt: Path, exc: Exception) -> None:
        target = attempt / "FAILURE.json"
        if target.exists():
            return
        value = {
            "schema": "kira.source_bound_media_preparation_failure.v1",
            "preserved_at_utc": self.utc_clock(),
            "attempt": attempt.name,
            "exception_type": type(exc).__name__,
            "message": str(exc),
            "partial_evidence_preserved": True,
            "automatic_retry": False,
        }
        try:
            self.store.write_json(target, value)
        except OSError:
            pass


def _bounded_text(value: object, field: str, maximum: int = 256) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > maximum:
        raise SourceBoundMediaExperienceError(f"{field} is malformed.")
    return value.strip()


def _ffmpeg_executable() -> Path:
    installed = shutil.which("ffmpeg")
    if installed:
        return Path(installed).resolve(strict=True)
    try:
        import imageio_ffmpeg

        return Path(imageio_ffmpeg.get_ffmpeg_exe()).resolve(strict=True)
    except (ImportError, OSError, RuntimeError) as exc:
        raise SourceBoundMediaExperienceError(
            "a local ffmpeg executable is required for bounded media decoding."
        ) from exc


def _ffmpeg_identity(executable: Path) -> dict[str, Any]:
    result = subprocess.run(
        [str(executable), "-version"],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise SourceBoundMediaExperienceError("could not identify the local ffmpeg decoder.")
    first_line = result.stdout.splitlines()[0].strip()
    return {
        "name": "ffmpeg",
        "version_line": first_line[:512],
        "executable_sha256": sha256_file(executable),
    }


def _parse_channel_count(description: str) -> int | None:
    lowered = description.casefold()
    if re.search(r"\bmono\b", lowered):
        return 1
    if re.search(r"\bstereo\b", lowered):
        return 2
    match = re.search(r"\b(\d+)\s+channels?\b", lowered)
    if match:
        return int(match.group(1))
    match = re.search(r"\b(\d+)\.(\d+)\b", lowered)
    if match:
        return int(match.group(1)) + int(match.group(2))
    return None


def _probe_media(path: Path) -> dict[str, Any]:
    executable = _ffmpeg_executable()
    result = subprocess.run(
        [str(executable), "-hide_banner", "-nostdin", "-i", str(path)],
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )
    diagnostic = result.stderr
    duration_match = re.search(
        r"Duration:\s*(\d+):(\d+):([0-9]+(?:\.[0-9]+)?)", diagnostic
    )
    if duration_match is None:
        raise SourceBoundMediaExperienceError(
            "ffmpeg did not report a bounded exact media duration."
        )
    hours, minutes, seconds = duration_match.groups()
    duration = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    if not 0 < duration <= 7 * 24 * 3600:
        raise SourceBoundMediaExperienceError("media duration is outside the bounded range.")
    streams: dict[str, list[dict[str, Any]]] = {
        "video": [],
        "audio": [],
        "subtitle": [],
    }
    stream_re = re.compile(
        r"Stream #(?P<input>\d+):(?P<index>\d+)(?:\[[^]]+\])?(?:\((?P<language>[^)]+)\))?:\s*(?P<kind>Video|Audio|Subtitle):\s*(?P<rest>.*)"
    )
    for line in diagnostic.splitlines():
        match = stream_re.search(line)
        if match is None:
            continue
        kind = match.group("kind").lower()
        rest = match.group("rest").strip()
        codec = rest.split(",", 1)[0].strip()
        record: dict[str, Any] = {
            "stream_index": int(match.group("index")),
            "language": match.group("language"),
            "codec_description": codec,
            "raw_stream_descriptor_sha256": sha256_bytes(
                line.strip().encode("utf-8")
            ),
        }
        if kind == "video":
            size = re.search(r"\b(\d{2,5})x(\d{2,5})\b", rest)
            fps = re.search(r"\b([0-9]+(?:\.[0-9]+)?)\s+fps\b", rest)
            record.update(
                {
                    "width": None if size is None else int(size.group(1)),
                    "height": None if size is None else int(size.group(2)),
                    "reported_fps": None if fps is None else float(fps.group(1)),
                }
            )
        elif kind == "audio":
            rate = re.search(r"\b(\d+)\s+Hz\b", rest)
            channels = _parse_channel_count(rest)
            record.update(
                {
                    "sample_rate_hz": None if rate is None else int(rate.group(1)),
                    "channels": channels,
                    "channel_layout_description": rest,
                }
            )
        streams[kind].append(record)
    return {
        "probe_kind": "local_ffmpeg_container_and_stream_probe",
        "duration_seconds": duration,
        "streams": streams,
        "probe_diagnostic_sha256": sha256_bytes(diagnostic.encode("utf-8")),
        "decoder": _ffmpeg_identity(executable),
    }


def _extract_video_frame(path: Path, target: Path, timestamp: float) -> dict[str, Any]:
    executable = _ffmpeg_executable()
    filter_value = f"select=gte(t\\,{timestamp:.9f}),showinfo"
    result = subprocess.run(
        [
            str(executable),
            "-hide_banner",
            "-nostdin",
            "-loglevel",
            "info",
            "-i",
            str(path),
            "-map",
            "0:v:0",
            "-vf",
            filter_value,
            "-frames:v",
            "1",
            "-fps_mode",
            "vfr",
            "-an",
            "-sn",
            "-n",
            str(target),
        ],
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    if result.returncode != 0 or not target.is_file() or target.stat().st_size == 0:
        raise SourceBoundMediaExperienceError(
            "ffmpeg could not extract the requested bounded video frame."
        )
    pts_values = re.findall(r"pts_time:([0-9.eE+\-]+)", result.stderr)
    if not pts_values:
        raise SourceBoundMediaExperienceError(
            "ffmpeg did not expose the selected frame timestamp."
        )
    decoded_pts = float(pts_values[-1])
    try:
        from PIL import Image

        with Image.open(target) as image:
            width, height = image.size
            image_format = image.format
    except (ImportError, OSError) as exc:
        raise SourceBoundMediaExperienceError(
            "could not verify the decoded video-frame raster."
        ) from exc
    return {
        "requested_timestamp_seconds": timestamp,
        "decoded_pts_seconds": decoded_pts,
        "timestamp_selection": "first_decoded_frame_at_or_after_requested_time",
        "sha256": sha256_file(target),
        "size_bytes": target.stat().st_size,
        "width_pixels": width,
        "height_pixels": height,
        "format": image_format,
    }


def _decode_audio_interval(
    path: Path,
    *,
    start: float,
    end: float,
    stream: Mapping[str, Any],
) -> dict[str, Any]:
    sample_rate = stream.get("sample_rate_hz")
    channels = stream.get("channels")
    if (
        isinstance(sample_rate, bool)
        or not isinstance(sample_rate, int)
        or not 1 <= sample_rate <= 192_000
    ):
        raise SourceBoundMediaExperienceError(
            "source audio sample rate is unavailable or outside the bounded range."
        )
    if isinstance(channels, bool) or not isinstance(channels, int) or not 1 <= channels <= 8:
        raise SourceBoundMediaExperienceError(
            "source audio channel count is unavailable or outside the bounded range."
        )
    predicted_bytes = math.ceil((end - start) * sample_rate) * channels * 4
    if predicted_bytes > MAX_PCM_BYTES:
        raise SourceBoundMediaExperienceError(
            "requested decoded PCM exceeds the bounded in-memory limit."
        )
    executable = _ffmpeg_executable()
    result = subprocess.run(
        [
            str(executable),
            "-hide_banner",
            "-nostdin",
            "-loglevel",
            "error",
            "-i",
            str(path),
            "-map",
            f"0:{int(stream['stream_index'])}",
            "-ss",
            f"{start:.9f}",
            "-t",
            f"{end - start:.9f}",
            "-vn",
            "-sn",
            "-dn",
            "-acodec",
            "pcm_f32le",
            "-ar",
            str(sample_rate),
            "-ac",
            str(channels),
            "-f",
            "f32le",
            "pipe:1",
        ],
        capture_output=True,
        timeout=120,
        check=False,
    )
    if result.returncode != 0:
        raise SourceBoundMediaExperienceError(
            "ffmpeg failed to decode the exact bounded audio interval."
        )
    pcm = result.stdout
    if not pcm or len(pcm) % (4 * channels):
        raise SourceBoundMediaExperienceError(
            "decoded PCM is empty or not aligned to complete sample frames."
        )
    try:
        import numpy as np
    except ImportError as exc:  # pragma: no cover - dependency gate
        raise SourceBoundMediaExperienceError(
            "NumPy is required to measure actual decoded audio samples."
        ) from exc
    samples = np.frombuffer(pcm, dtype="<f4").reshape((-1, channels))
    if not np.isfinite(samples).all():
        raise SourceBoundMediaExperienceError("decoded PCM contains non-finite samples.")
    frames = int(samples.shape[0])
    actual_duration = frames / sample_rate
    channel_rms = np.sqrt(np.mean(np.square(samples, dtype=np.float64), axis=0))
    channel_peak = np.max(np.abs(samples), axis=0)
    rms = float(np.sqrt(np.mean(np.square(samples, dtype=np.float64))))
    peak = float(np.max(np.abs(samples)))
    return {
        "status": "DECODED_ACTUAL_PCM_SAMPLES",
        "requested_interval": {
            "start_seconds": start,
            "end_seconds": end,
            "duration_seconds": end - start,
        },
        "decoded_sample_rate_hz": sample_rate,
        "decoded_channels": channels,
        "decoded_sample_frames": frames,
        "decoded_duration_seconds": actual_duration,
        "pcm_format": "little_endian_float32_interleaved",
        "pcm_byte_count": len(pcm),
        "pcm_sha256": sha256_bytes(pcm),
        "rms_full_scale": rms,
        "peak_full_scale": peak,
        "per_channel_rms_full_scale": [float(item) for item in channel_rms],
        "per_channel_peak_full_scale": [float(item) for item in channel_peak],
        "non_silent": bool(peak > 1e-6 and rms > 1e-7),
        "raw_audio_stored": False,
        "speaker_playback_performed": False,
    }


def validate_evidence_document(value: Mapping[str, Any]) -> None:
    """Fail closed if an evidence package could imply unsupported experience."""

    expected = {
        "schema",
        "evidence_id",
        "created_at_utc",
        "run_mode",
        "media_kind",
        "access_binding",
        "source",
        "presentation_receipt",
        "preparation",
        "experience_session",
        "model_handoff",
        "truth_boundaries",
        "artifacts",
    }
    if not isinstance(value, Mapping) or set(value) != expected:
        raise SourceBoundMediaExperienceError(
            "evidence document does not match the exact schema."
        )
    if value.get("schema") != EVIDENCE_SCHEMA:
        raise SourceBoundMediaExperienceError("evidence schema is unsupported.")
    if value.get("media_kind") not in {"pdf_page", "video", "music"}:
        raise SourceBoundMediaExperienceError("evidence media kind is invalid.")
    source = value.get("source")
    access = value.get("access_binding")
    if not isinstance(source, Mapping) or not isinstance(access, Mapping):
        raise SourceBoundMediaExperienceError("source/access binding is malformed.")
    if (
        source.get("project_relative_library_path")
        != access.get("project_relative_library_path")
        or source.get("sha256") != access.get("source_sha256")
        or not SHA256_RE.fullmatch(str(source.get("sha256") or ""))
    ):
        raise SourceBoundMediaExperienceError("source and access hashes are not exact.")
    if source.get("raw_source_copied") is not False:
        raise SourceBoundMediaExperienceError("raw source copying is not permitted.")
    boundaries = value.get("truth_boundaries")
    if not isinstance(boundaries, Mapping) or any(
        boundaries.get(field) is not False
        for field in (
            "prepared_media_equals_person_experience",
            "opening_or_decoding_equals_attention",
            "one_page_equals_whole_publication",
            "sampled_frames_equal_complete_viewing",
            "metadata_or_filename_equals_heard_audio",
            "captions_scripts_or_lyrics_equal_audiovisual_experience",
            "automatic_memory_created",
            "automatic_preference_created",
            "learning_claim_created",
            "consciousness_claim_created",
            "biological_humanity_claim_created",
            "publication_authorized",
        )
    ):
        raise SourceBoundMediaExperienceError(
            "evidence contains or omits a required truth boundary."
        )
    preparation = value.get("preparation")
    if not isinstance(preparation, Mapping):
        raise SourceBoundMediaExperienceError("media preparation record is malformed.")
    kind = value["media_kind"]
    if kind == "pdf_page":
        if preparation.get("whole_publication_read_claim") is not False:
            raise SourceBoundMediaExperienceError(
                "one rendered page cannot claim a whole publication was read."
            )
        raster = preparation.get("raster")
        ocr = preparation.get("ocr")
        if (
            not isinstance(raster, Mapping)
            or not SHA256_RE.fullmatch(str(raster.get("sha256") or ""))
            or not isinstance(ocr, Mapping)
            or ocr.get("source_raster_sha256") != raster.get("sha256")
            or ocr.get("counts_as_visual_page_observation") is not False
        ):
            raise SourceBoundMediaExperienceError(
                "PDF raster/OCR provenance is not separately hash-bound."
            )
    else:
        for field in (
            "sampled_frames_equal_full_viewing",
            "full_source_watched_claim",
            "full_track_listened_claim",
            "filename_or_metadata_counts_as_listening",
            "lyrics_counts_as_listening",
            "raw_audio_stored",
        ):
            if preparation.get(field) is not False:
                raise SourceBoundMediaExperienceError(
                    f"timed-media truth boundary {field} must be false."
                )
        if kind == "video":
            frames = preparation.get("video_frames")
            if not isinstance(frames, list) or not frames:
                raise SourceBoundMediaExperienceError(
                    "video evidence requires bounded timestamped frames."
                )
            for frame in frames:
                if not isinstance(frame, Mapping) or not SHA256_RE.fullmatch(
                    str(frame.get("sha256") or "")
                ):
                    raise SourceBoundMediaExperienceError(
                        "video frame evidence is not hash-bound."
                    )
        if kind == "music":
            audio = preparation.get("audio_decode")
            if (
                not isinstance(audio, Mapping)
                or audio.get("status") != "DECODED_ACTUAL_PCM_SAMPLES"
                or not SHA256_RE.fullmatch(str(audio.get("pcm_sha256") or ""))
                or audio.get("raw_audio_stored") is not False
            ):
                raise SourceBoundMediaExperienceError(
                    "music evidence requires actual hash-bound PCM measurements."
                )
    session = value.get("experience_session")
    if not isinstance(session, Mapping):
        raise SourceBoundMediaExperienceError("experience-session snapshot is absent.")
    implications = session.get("implications")
    if not isinstance(implications, Mapping) or any(
        implications.get(field) is not False
        for field in (
            "lived_memory_created",
            "canon_created",
            "temporary_ai_evidence_created",
            "publication_authorized",
        )
    ):
        raise SourceBoundMediaExperienceError(
            "experience-session implications overstate the result."
        )
    run_mode = value.get("run_mode")
    receipt = value.get("presentation_receipt")
    observed = session.get("playback", {}).get("observed_intervals", [])
    presented = session.get("playback", {}).get("presented_intervals", [])
    page_observed = session.get("page_observations", [])
    page_presented = session.get("page_presentations", [])
    if run_mode == "PREPARED_OFFLINE_NO_PERSON_PRESENTATION":
        if receipt is not None or observed or presented or page_observed or page_presented:
            raise SourceBoundMediaExperienceError(
                "prepare-only evidence cannot contain presentation or observation events."
            )
    elif run_mode == "REVIEWED_PRESENTATION_RECEIPT_RECORDED":
        if not isinstance(receipt, Mapping):
            raise SourceBoundMediaExperienceError(
                "recorded presentation evidence requires its reviewed receipt."
            )
        ReviewedPresentationReceipt.from_mapping(receipt)
    else:
        raise SourceBoundMediaExperienceError("evidence run mode is invalid.")
    artifacts = value.get("artifacts")
    if not isinstance(artifacts, Mapping) or any(
        artifacts.get(field) is not False
        for field in (
            "speaker_playback_performed_by_this_module",
            "display_performed_by_this_module",
            "network_used",
            "gpu_used",
        )
    ):
        raise SourceBoundMediaExperienceError(
            "the preparation module must not claim playback, display, network, or GPU work."
        )


def _parse_crop_argument(value: str) -> tuple[float, float, float, float]:
    try:
        parts = tuple(float(item.strip()) for item in value.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("crop must contain four comma-separated numbers") from exc
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("crop must contain four comma-separated numbers")
    return parts  # type: ignore[return-value]


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare private source-bound resident-media evidence without playback or models."
    )
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--evidence-root", type=Path, default=DEFAULT_EVIDENCE_ROOT)
    parser.add_argument("--viewer", default="kira")
    parser.add_argument("--activation-revision", default="offline_media_preparation")
    subparsers = parser.add_subparsers(dest="media_kind", required=True)

    pdf = subparsers.add_parser("pdf")
    pdf.add_argument("--source", required=True, type=Path)
    pdf.add_argument("--page", required=True, type=int)
    pdf.add_argument("--crop", type=_parse_crop_argument, default=(0.0, 0.0, 1.0, 1.0))
    pdf.add_argument("--zoom", type=float, default=1.5)

    video = subparsers.add_parser("video")
    video.add_argument("--source", required=True, type=Path)
    video.add_argument("--start", required=True, type=float)
    video.add_argument("--end", required=True, type=float)
    video.add_argument("--frames", type=int, default=3)
    video.add_argument("--pause-at", type=float)

    music = subparsers.add_parser("music")
    music.add_argument("--source", required=True, type=Path)
    music.add_argument("--start", required=True, type=float)
    music.add_argument("--end", required=True, type=float)
    music.add_argument("--pause-at", type=float)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_argument_parser().parse_args(argv)
    runner = SourceBoundResidentMediaExperience(
        project_root=args.project_root,
        evidence_root=args.evidence_root,
    )
    if args.media_kind == "pdf":
        attempt = runner.prepare_pdf_page(
            args.source,
            viewer=args.viewer,
            activation_revision=args.activation_revision,
            page_number=args.page,
            crop=args.crop,
            zoom=args.zoom,
        )
    elif args.media_kind == "video":
        attempt = runner.prepare_video_interval(
            args.source,
            viewer=args.viewer,
            activation_revision=args.activation_revision,
            start_seconds=args.start,
            end_seconds=args.end,
            frame_count=args.frames,
            pause_at_seconds=args.pause_at,
        )
    else:
        attempt = runner.prepare_music_interval(
            args.source,
            viewer=args.viewer,
            activation_revision=args.activation_revision,
            start_seconds=args.start,
            end_seconds=args.end,
            pause_at_seconds=args.pause_at,
        )
    evidence = attempt / "EVIDENCE.json"
    print(
        json.dumps(
            {
                "status": "PREPARED_OFFLINE_NO_PERSON_PRESENTATION",
                "attempt": attempt.relative_to(args.project_root.resolve()).as_posix(),
                "evidence_sha256": sha256_file(evidence),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
