from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(r"C:\Users\robmc\Documents\Codex\2026-08-11\c\work\growth_v9_author")
MANIFEST = ROOT / "SEALED_MANIFEST.json"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def pairs(items: list[tuple[str, object]]) -> dict[str, object]:
    output: dict[str, object] = {}
    for key, value in items:
        if key in output:
            raise RuntimeError(f"duplicate manifest key: {key}")
        output[key] = value
    return output


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"), object_pairs_hook=pairs)
    subjects = manifest["subjects"]
    if not isinstance(subjects, list) or len(subjects) != manifest["subject_count"]:
        raise RuntimeError("manifest subject count drifted")
    hasher = hashlib.sha256()
    seen: set[str] = set()
    for subject in subjects:
        if not isinstance(subject, dict):
            raise RuntimeError("manifest subject type drifted")
        name = subject["path"]
        if not isinstance(name, str) or name in seen or "\\" in name or name.startswith("/") or ".." in name:
            raise RuntimeError("manifest subject path drifted")
        seen.add(name)
        path = ROOT / Path(name)
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"sealed subject absent or linked: {name}")
        data = path.read_bytes()
        digest = sha(data)
        if len(data) != subject["bytes"] or digest != subject["sha256"]:
            raise RuntimeError(f"sealed subject drifted: {name}")
        hasher.update(f"{name}\0{len(data)}\0{digest}\n".encode("utf-8"))
    if hasher.hexdigest() != manifest["subject_root_sha256"]:
        raise RuntimeError("subject root drifted")
    current = {
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("*")
        if path.is_file()
    }
    excluded = {item["path"] for item in manifest["excluded_author_or_private_files"]}
    allowed = seen | excluded | {"SEALED_MANIFEST.json", "Testing/seal_shared_growth_v9_author.py"}
    unexpected = sorted(current - allowed)
    if unexpected:
        raise RuntimeError(f"unexpected package file after seal: {unexpected}")
    if any(name.startswith("runtime/") or "__pycache__" in name or name.endswith(".pyc")
           for name in current):
        raise RuntimeError("runtime/cache file exists after seal")
    print(json.dumps({"verdict": "SEAL_VERIFIED",
                      "subject_count": len(seen),
                      "subject_root_sha256": hasher.hexdigest(),
                      "manifest_sha256": sha(MANIFEST.read_bytes())}, sort_keys=True))


if __name__ == "__main__":
    main()
