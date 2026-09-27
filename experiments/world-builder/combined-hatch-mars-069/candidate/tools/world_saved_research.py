"""Read-only discovery of the World Builder's existing research projects.

Opening a saved project must not queue research, claim a model attempt, mutate
the notebook index or import geometry into a world.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

JOB_NAME = re.compile(r"world_research_[0-9a-f]{20}\Z")
MAX_JOB_BYTES = 2 * 1024 * 1024


def _plain(path: Path) -> bool:
    return not path.is_symlink() and not path.is_junction()


def read_saved_research(job_dir: Path, *, job_root: Path) -> dict:
    """Read current metadata from one immediate, ordinary saved-job folder."""
    root = Path(job_root).resolve(strict=True)
    path = Path(job_dir)
    if not _plain(path) or path.resolve(strict=True).parent != root or not JOB_NAME.fullmatch(path.name):
        raise ValueError("Choose a saved research job from this installation")
    path = path.resolve(strict=True)
    metadata = path / "job.json"
    if not _plain(metadata) or not metadata.is_file():
        raise ValueError("The saved job metadata is missing or linked elsewhere")
    if metadata.stat().st_size > MAX_JOB_BYTES:
        raise ValueError("The saved job metadata exceeds its supported size")
    raw = metadata.read_bytes()
    if len(raw) > MAX_JOB_BYTES:
        raise ValueError("The saved job metadata changed beyond its supported size")
    data = json.loads(raw.decode("utf-8-sig"))
    if not isinstance(data, dict) or data.get("schema_version") != 1 or data.get("job_kind") != "isolated_world_research_job" or data.get("job_id") != path.name:
        raise ValueError("The saved research identity is invalid")
    brief = data.get("brief")
    if not isinstance(brief, dict):
        raise ValueError("The saved research brief is unavailable")
    canonical = (json.dumps(brief, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    digest = hashlib.sha256(canonical).hexdigest()
    if data.get("brief_sha256") != digest or path.name != "world_research_" + digest[:20]:
        raise ValueError("The saved research brief no longer matches its identity")
    subject, stage = brief.get("subject"), data.get("stage")
    if not isinstance(subject, str) or not subject.strip() or not isinstance(stage, str) or not stage:
        raise ValueError("The saved research subject or status is unavailable")
    return {"job_dir": path, "job_id": path.name, "subject": subject, "stage": stage,
            "job_sha256": hashlib.sha256(raw).hexdigest()}


def list_saved_research(job_root: Path) -> list[dict]:
    """List valid and damaged projects; a damaged project is retained, not erased."""
    root = Path(job_root)
    if not root.exists():
        return []
    root = root.resolve(strict=True)
    items = []
    for path in root.iterdir():
        if not JOB_NAME.fullmatch(path.name) or not path.is_dir():
            continue
        try:
            item = read_saved_research(path, job_root=root)
            subject = " ".join(item["subject"].split())
            item.update(available=True, label=f"{subject[:90]} · {item['stage']} · {path.name}")
        except (OSError, ValueError, UnicodeError) as exc:
            item = {"job_dir": path, "job_id": path.name, "available": False,
                    "label": f"Needs attention · {path.name}", "error": str(exc)}
        try:
            modified = (path / "job.json").stat().st_mtime_ns if _plain(path) else 0
        except OSError:
            modified = 0
        items.append((modified, item))
    return [item for _, item in sorted(items, key=lambda pair: (pair[0], pair[1]["job_id"]), reverse=True)]
