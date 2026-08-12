from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_HEALTH_DIR = PROJECT_ROOT / "Data" / "library" / "source_health"
UNREADABLE_SOURCES_PATH = SOURCE_HEALTH_DIR / "unreadable_sources.json"
OCR_REPAIRED_SOURCES_PATH = SOURCE_HEALTH_DIR / "ocr_repaired_sources.json"
OCR_REQUESTS_PATH = SOURCE_HEALTH_DIR / "ocr_requests.json"


def rel(path: Path | str) -> str:
    p = Path(path)
    if not p.is_absolute():
        return p.as_posix().replace("\\", "/")
    try:
        return p.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return p.as_posix().replace("\\", "/")


def load_unreadable_registry() -> dict[str, Any]:
    if not UNREADABLE_SOURCES_PATH.exists():
        return {
            "registry_id": "library_unreadable_sources_v1",
            "updated_at": datetime.now(timezone.utc).date().isoformat(),
            "policy": {
                "purpose": "Known scanned/image-only or text-extraction-failing files.",
                "not_a_quality_judgment": True,
                "can_be_restored_after_ocr": True,
            },
            "sources": {},
        }
    try:
        return json.loads(UNREADABLE_SOURCES_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"registry_id": "library_unreadable_sources_v1", "sources": {}}


def write_unreadable_registry(registry: dict[str, Any]) -> None:
    registry["updated_at"] = datetime.now(timezone.utc).date().isoformat()
    SOURCE_HEALTH_DIR.mkdir(parents=True, exist_ok=True)
    UNREADABLE_SOURCES_PATH.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def unreadable_source_record(source_path: Path | str) -> dict[str, Any] | None:
    registry = load_unreadable_registry()
    sources = registry.get("sources", {}) if isinstance(registry.get("sources"), dict) else {}
    key = rel(source_path)
    record = sources.get(key)
    return record if isinstance(record, dict) else None


def repaired_source_record(source_path: Path | str) -> dict[str, Any] | None:
    if not OCR_REPAIRED_SOURCES_PATH.exists():
        return None
    try:
        registry = json.loads(OCR_REPAIRED_SOURCES_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None
    sources = registry.get("sources", {}) if isinstance(registry.get("sources"), dict) else {}
    key = rel(source_path)
    record = sources.get(key)
    return record if isinstance(record, dict) else None


def repaired_output_path(source_path: Path | str) -> Path | None:
    record = repaired_source_record(source_path)
    if not record:
        return None
    output = record.get("repaired_output")
    if not output:
        return None
    path = Path(str(output))
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path if path.exists() else None


def is_text_reading_blocked(source_path: Path | str) -> bool:
    record = unreadable_source_record(source_path)
    if not record:
        return False
    return str(record.get("reader_behavior", "")).lower() == "skip_for_text_reading" or str(record.get("status", "")).lower() in {
        "needs_ocr",
        "unreadable",
        "image_only",
    }


def mark_unreadable(source_path: Path | str, *, reason: str, status: str = "needs_ocr") -> dict[str, Any]:
    registry = load_unreadable_registry()
    sources = registry.setdefault("sources", {})
    key = rel(source_path)
    existing = sources.get(key, {}) if isinstance(sources.get(key), dict) else {}
    record = {
        **existing,
        "status": status,
        "reason": reason,
        "last_seen": datetime.now(timezone.utc).date().isoformat(),
        "reader_behavior": "skip_for_text_reading",
    }
    record.setdefault("first_seen", record["last_seen"])
    sources[key] = record
    write_unreadable_registry(registry)
    return record


def request_ocr(source_path: Path | str, *, requester: str, reason: str, run_id: str = "") -> dict[str, Any]:
    try:
        registry = json.loads(OCR_REQUESTS_PATH.read_text(encoding="utf-8")) if OCR_REQUESTS_PATH.exists() else {}
    except Exception:
        registry = {}
    registry.setdefault("registry_id", "ocr_requests_v1")
    registry.setdefault("policy", {
        "purpose": "Requests from Kira/Lisa/tools for OCR repair of unreadable sources.",
        "does_not_run_ocr_automatically": True,
        "robert_or_tooling_can_review_and_batch": True,
    })
    requests = registry.setdefault("requests", [])
    request = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_path": rel(source_path),
        "requester": requester,
        "reason": reason,
        "run_id": run_id,
        "status": "requested",
    }
    if isinstance(requests, list):
        already = [
            item for item in requests
            if isinstance(item, dict)
            and item.get("source_path") == request["source_path"]
            and item.get("status") == "requested"
        ]
        if not already:
            requests.append(request)
    registry["updated_at"] = datetime.now(timezone.utc).isoformat()
    SOURCE_HEALTH_DIR.mkdir(parents=True, exist_ok=True)
    OCR_REQUESTS_PATH.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return request
