"""
Search public Wikimedia/Wikipedia references for a TemporaryAI avatar candidate.

This records review candidates and can optionally download Wikimedia/thumbnail
images into the candidate's downloaded reference folder. It does not approve
images or feed them into avatar generation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
AVATAR_ROOT = PROJECT_ROOT / "Avatar" / "temp_ai"

WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def safe_name(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", value).strip("_")[:100] or "reference"


def queue_path(candidate_id: str) -> Path:
    return AVATAR_ROOT / candidate_id / "online_reference_queue.json"


def wikipedia_search(query: str, limit: int) -> list[dict[str, Any]]:
    response = requests.get(
        WIKIPEDIA_API,
        params={
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": query,
            "gsrlimit": limit,
            "prop": "pageimages|info|extracts",
            "inprop": "url",
            "exintro": 1,
            "explaintext": 1,
            "piprop": "thumbnail|original|name",
            "pithumbsize": 900,
        },
        timeout=30,
        headers={"User-Agent": "KiraLocalAvatarReferenceTool/1.0"},
    )
    response.raise_for_status()
    pages = response.json().get("query", {}).get("pages", {})
    results = []
    for page in pages.values():
        image_url = ""
        if isinstance(page.get("original"), dict):
            image_url = page["original"].get("source", "")
        if not image_url and isinstance(page.get("thumbnail"), dict):
            image_url = page["thumbnail"].get("source", "")
        results.append(
            {
                "source_type": "wikipedia",
                "title": page.get("title", ""),
                "page_url": page.get("fullurl", ""),
                "image_url": image_url,
                "summary": str(page.get("extract", ""))[:700],
                "confidence": "secondary_reference",
                "status": "needs_review",
            }
        )
    return results


def commons_search(query: str, limit: int) -> list[dict[str, Any]]:
    response = requests.get(
        COMMONS_API,
        params={
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": query,
            "gsrnamespace": 6,
            "gsrlimit": limit,
            "prop": "imageinfo",
            "iiprop": "url|mime|extmetadata",
        },
        timeout=30,
        headers={"User-Agent": "KiraLocalAvatarReferenceTool/1.0"},
    )
    response.raise_for_status()
    pages = response.json().get("query", {}).get("pages", {})
    results = []
    for page in pages.values():
        info = (page.get("imageinfo") or [{}])[0]
        metadata = info.get("extmetadata") or {}
        results.append(
            {
                "source_type": "wikimedia_commons",
                "title": page.get("title", ""),
                "page_url": f"https://commons.wikimedia.org/wiki/{urllib.parse.quote(str(page.get('title', '')).replace(' ', '_'))}",
                "image_url": info.get("url", ""),
                "mime": info.get("mime", ""),
                "license": (metadata.get("LicenseShortName") or {}).get("value", ""),
                "artist": re.sub(r"<.*?>", "", (metadata.get("Artist") or {}).get("value", ""))[:300],
                "confidence": "secondary_or_public_reference",
                "status": "needs_review",
            }
        )
    return results


def download_image(candidate_id: str, item: dict[str, Any]) -> str:
    url = str(item.get("image_url", ""))
    if not url:
        return ""
    folder = AVATAR_ROOT / candidate_id / "references" / "downloaded"
    folder.mkdir(parents=True, exist_ok=True)
    ext = Path(urllib.parse.urlparse(url).path).suffix
    if ext.lower() not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        ext = ".jpg"
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
    filename = f"{safe_name(str(item.get('title', 'reference')))}_{digest}{ext}"
    path = folder / filename
    if path.exists():
        return rel(path)
    response = requests.get(url, timeout=45, headers={"User-Agent": "KiraLocalAvatarReferenceTool/1.0"})
    response.raise_for_status()
    path.write_bytes(response.content)
    return rel(path)


def search_candidate(candidate_id: str, queries: list[str], limit: int, download: bool, include_commons: bool) -> dict[str, Any]:
    path = queue_path(candidate_id)
    if not path.exists():
        raise FileNotFoundError(f"Reference queue not found: {path}")
    queue = read_json(path)
    if queries:
        queue["queries_to_review"] = queries
    queries_to_use = queue.get("queries_to_review", [])
    existing = queue.get("reference_candidates", queue.get("downloaded_items", []))
    seen = {item.get("image_url") or item.get("page_url") for item in existing}
    items = []
    for query in queries_to_use:
        for item in wikipedia_search(str(query), limit):
            key = item.get("image_url") or item.get("page_url")
            if key and key not in seen:
                seen.add(key)
                items.append(item)
        time.sleep(0.2)
        if include_commons:
            for item in commons_search(str(query), limit):
                key = item.get("image_url") or item.get("page_url")
                if key and key not in seen:
                    seen.add(key)
                    items.append(item)
            time.sleep(0.2)
    if download:
        for item in items:
            try:
                item["local_path"] = download_image(candidate_id, item)
            except Exception as exc:  # noqa: BLE001
                item["download_error"] = str(exc)
    queue.setdefault("reference_candidates", [])
    queue["reference_candidates"].extend(items)
    queue["downloaded_items"] = queue["reference_candidates"]
    queue["status"] = "references_found_needs_review" if items else "no_new_references_found"
    queue["updated_at"] = now_iso()
    queue.setdefault("review_notes", []).append(
        {
            "created_at": now_iso(),
            "note": f"Search added {len(items)} item(s). Download={download}. Commons={include_commons}. Items still need review before approval.",
        }
    )
    write_json(path, queue)
    return {"queue": rel(path), "items_added": len(items), "download": download}


def main() -> None:
    parser = argparse.ArgumentParser(description="Search Wikimedia/Wikipedia avatar references for a TemporaryAI candidate.")
    parser.add_argument("candidate_id")
    parser.add_argument("--query", action="append", default=[])
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--commons", action="store_true", help="Also search Wikimedia Commons. Off by default because broad character names can return unrelated public images.")
    args = parser.parse_args()
    print(json.dumps(search_candidate(args.candidate_id, args.query, args.limit, args.download, args.commons), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
