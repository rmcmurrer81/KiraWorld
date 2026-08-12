"""Interactive live chat for reviewable TemporaryAI candidates.

This is a test chat, not permanent activation. It loads one candidate profile,
keeps the candidate separate from Kira/Lisa, and saves a transcript for review.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.temp_ai_avatar_pipeline import prepare_candidate_avatar_pipeline
from Core.temp_ai_source_grounding import (
    bounded_text_conversation_readiness,
    read_review,
    readiness_status,
)
from Core.person_mind_runtime import finalize_person_turn
from Core.model_request_policy import (
    QWEN_TEXT_VOICE_DIGEST,
    QWEN_TEXT_VOICE_MODEL,
    ordinary_model_request_fields,
)
from Core.qwen35_runtime_identity import (
    require_exact_qwen35_response_model,
    require_installed_exact_qwen35,
)
from Core.temporary_ai_character_validator import (
    ValidationContext,
    repair_instruction,
    validate_character_turn,
)
from Core.marinette_current_canon_contract_v4 import (
    bind_loaded_candidate as bind_marinette_v4_candidate,
    build_contract_bound_system_prompt as build_marinette_v4_system_prompt,
    build_owner_model_request as build_marinette_v4_owner_model_request,
    closed_gate_system_diagnostic as marinette_v4_closed_gate_diagnostic,
    is_strict_marinette_v4_candidate,
    owner_text_execution_readiness as marinette_v4_owner_text_readiness,
)
CANDIDATE_ROOT = PROJECT_ROOT / "TemporaryAI" / "candidates"
ARCHIVED_CANDIDATE_ROOT = PROJECT_ROOT / "TemporaryAI" / "archived_candidates"
AVATAR_ROOT = PROJECT_ROOT / "Avatar" / "temp_ai"
ARCHIVED_AVATAR_ROOT = PROJECT_ROOT / "Avatar" / "archived_temp_ai"
ACTIVATION_QUEUE = PROJECT_ROOT / "Data" / "temporary_ai_instances" / "activation_queue.json"
OUT_DIR = PROJECT_ROOT / "Data" / "personhood_evaluations" / "temporary_ai_live_chats"
OLLAMA_ENDPOINT = os.getenv("KIRA_OLLAMA_ENDPOINT", "http://localhost:11434/api/chat")
MODEL_NAME = os.getenv("KIRA_MODEL_NAME", QWEN_TEXT_VOICE_MODEL)
MODEL_DIGEST = os.getenv("KIRA_MODEL_DIGEST", QWEN_TEXT_VOICE_DIGEST)
MAX_TOKENS = int(os.getenv("KIRA_MAX_TOKENS", "900"))
TEMPERATURE = float(os.getenv("KIRA_TEMPERATURE", "0.6"))
OLLAMA_TIMEOUT = int(os.getenv("KIRA_OLLAMA_TIMEOUT", "360"))
OLLAMA_NUM_CTX = int(os.getenv("KIRA_OLLAMA_NUM_CTX", "8192"))
RECENT_CONTEXT_TURNS = int(os.getenv("TEMP_AI_RECENT_CONTEXT_TURNS", "12"))
REFERENCE_CONTEXT_CHARS = int(os.getenv("TEMP_AI_REFERENCE_CONTEXT_CHARS", "6000"))
TOPIC_DOC_CONTEXT_CHARS = int(os.getenv("TEMP_AI_TOPIC_DOC_CONTEXT_CHARS", "7000"))
GRAPH_REFRESH_TIMEOUT_SECONDS = int(os.getenv("TEMP_AI_GRAPH_REFRESH_TIMEOUT", "20"))
GENERATED_FILE_EXTENSIONS = {
    ".bat",
    ".cmd",
    ".css",
    ".csv",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".md",
    ".ps1",
    ".py",
    ".svg",
    ".txt",
    ".yaml",
    ".yml",
}
PATH_LANGUAGE_PREFIXES = {
    "bat",
    "cmd",
    "css",
    "html",
    "ini",
    "javascript",
    "js",
    "json",
    "markdown",
    "md",
    "powershell",
    "ps1",
    "py",
    "python",
    "svg",
    "text",
    "txt",
    "xml",
    "yaml",
    "yml",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")[:90] or "temporary_ai"


def rel(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def append(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(text.rstrip() + "\n")


def safe_output_name(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_. -]+", "_", value).strip(" ._")
    return value[:120] or f"draft_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"


def safe_relative_file_path(value: str) -> Path | None:
    """Return a review-safe relative path for candidate-generated files."""
    value = value.strip().strip("`'\"")
    if not value:
        return None
    tokens = value.split(maxsplit=1)
    if len(tokens) == 2 and tokens[0].lower() in PATH_LANGUAGE_PREFIXES:
        value = tokens[1].strip()
    value = value.replace("\\", "/")
    parts: list[str] = []
    for raw_part in value.split("/"):
        part = re.sub(r"[^a-zA-Z0-9_. -]+", "_", raw_part).strip(" ._")
        if not part or part in {".", ".."}:
            continue
        parts.append(part[:80])
    if not parts:
        return None
    rel_path = Path(*parts)
    if rel_path.suffix.lower() not in GENERATED_FILE_EXTENSIONS:
        return None
    return rel_path


def generated_block_is_malformed(rel_path: Path, code: str) -> bool:
    """Reject nested/unfinished blocks and prose pretending to be source code."""
    text = code or ""
    lower = text.lower()
    if re.search(r"\*\*[^*\n]+?\.(?:bat|cmd|css|csv|html|ini|js|json|md|ps1|py|svg|txt|ya?ml)\*\*", text, flags=re.I):
        return True
    if "```" in text:
        return True
    if "[insert " in lower or "[todo" in lower:
        return True
    if rel_path.suffix.lower() == ".py":
        nonblank = [line.strip() for line in text.splitlines() if line.strip()]
        if not nonblank:
            return True
        code_lines = [
            line
            for line in nonblank
            if not line.startswith("#")
            and not line.startswith('"""')
            and not line.startswith("'''")
        ]
        if not code_lines:
            return True
        if any(line.startswith(("# ", "##", "* ", "- ")) for line in code_lines[:8]):
            return True
    return False


def filename_from_nearby_text(text: str) -> Path | None:
    """Find a filename label immediately before a fenced block."""
    nearby = "\n".join((text or "").splitlines()[-8:])
    patterns = [
        r"(?:file|filename|path)\s*[:=]\s*`?([^`\n]+?\.(?:bat|cmd|css|csv|html|ini|js|json|md|ps1|py|svg|txt|ya?ml))`?",
        r"^\s*\*\*([^*\n]+?\.(?:bat|cmd|css|csv|html|ini|js|json|md|ps1|py|svg|txt|ya?ml))\*\*\s*$",
        r"^\s*`([^`\n]+?\.(?:bat|cmd|css|csv|html|ini|js|json|md|ps1|py|svg|txt|ya?ml))`\s*$",
        r"^\s*([a-zA-Z0-9_. /\\-]+?\.(?:bat|cmd|css|csv|html|ini|js|json|md|ps1|py|svg|txt|ya?ml))\s*$",
    ]
    for pattern in patterns:
        matches = list(re.finditer(pattern, nearby, flags=re.I | re.M))
        for match in reversed(matches):
            path = safe_relative_file_path(match.group(1))
            if path:
                return path
    return None


def shell_like_code_block(info: str) -> bool:
    lang = ((info or "").strip().split() or [""])[0].lower()
    return lang in {"bash", "bat", "cmd", "console", "dos", "powershell", "ps1", "shell", "sh", "terminal"}


def filename_from_code_block(info: str, code: str, nearby_text: str = "") -> Path | None:
    info = (info or "").strip()
    patterns = [
        r"(?:file|filename|path)\s*[:=]\s*([^\s,;]+)",
        r"([a-zA-Z0-9_. -]+\.(?:bat|cmd|css|csv|html|ini|js|json|md|ps1|py|svg|txt|ya?ml))",
    ]
    for pattern in patterns:
        match = re.search(pattern, info, flags=re.I)
        if match:
            path = safe_relative_file_path(match.group(1))
            if path:
                return path

    first_lines = "\n".join(code.splitlines()[:6])
    for pattern in [
        r"^\s*(?:#|//|<!--)\s*(?:file|filename|path)\s*:\s*([^\n>-]+)",
        r"^\s*(?:REM|::)\s*(?:file|filename|path)\s*:\s*([^\n]+)",
    ]:
        match = re.search(pattern, first_lines, flags=re.I | re.M)
        if match:
            path = safe_relative_file_path(match.group(1))
            if path:
                return path
    if shell_like_code_block(info):
        return None
    return filename_from_nearby_text(nearby_text)


def strip_filename_comment(code: str) -> str:
    lines = code.splitlines()
    if lines and re.match(r"\s*(?:#|//|<!--|REM|::)\s*(?:file|filename|path)\s*:", lines[0], flags=re.I):
        return "\n".join(lines[1:]).lstrip("\n")
    return code


def route_generated_path(rel_path: Path, surrounding_text: str = "") -> Path:
    """Route chat-generated files into visible workbench output folders."""
    if rel_path.parts and rel_path.parts[0].lower() == "outputs":
        return Path(*rel_path.parts[1:]) if len(rel_path.parts) > 1 else rel_path
    if rel_path.parts and rel_path.parts[0].lower() in {
        "program_drafts",
        "design_docs",
        "test_drafts",
        "schemas",
        "sketches",
        "patch_proposals",
        "tempai_lab_v2",
    }:
        return rel_path
    if len(rel_path.parts) > 1:
        return rel_path
    surrounding = (surrounding_text or "").replace("\\", "/").lower()
    folder_patterns = [
        ("program_drafts", r"outputs/program_drafts|program_drafts"),
        ("design_docs", r"outputs/design_docs|design_docs"),
        ("test_drafts", r"outputs/test_drafts|test_drafts"),
        ("schemas", r"outputs/schemas|schemas"),
        ("sketches", r"outputs/sketches|sketches|fashion sketch|concept sketch|drawing"),
        ("patch_proposals", r"outputs/patch_proposals|patch_proposals|patch proposal"),
        ("tempai_lab_v2", r"outputs/tempai_lab_v2|tempai_lab_v2"),
    ]
    for folder, pattern in folder_patterns:
        if re.search(pattern, surrounding):
            return Path(folder) / rel_path
    return Path("generated_files") / rel_path


def generated_file_target(candidate: dict[str, Any], rel_path: Path, surrounding_text: str = "") -> Path | None:
    workbench = candidate_workbench_dir(candidate)
    output_root = workbench / "outputs"
    routed = route_generated_path(rel_path, surrounding_text)
    target = output_root / routed
    try:
        target.resolve().relative_to(output_root.resolve())
    except ValueError:
        return None
    return target


def target_for_safe_generated_write(candidate: dict[str, Any], target: Path, code: str, surrounding_text: str = "") -> Path:
    """Avoid overwriting substantial workbench files with tiny chat examples.

    Live chat can save filename-tagged blocks, but the model sometimes presents a
    small illustrative example using the same filename as a real artifact. Keep
    those drafts for review without replacing the existing tool.
    """
    if not target.exists():
        return target

    try:
        existing_text = target.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return target

    new_text = strip_filename_comment(code).strip()
    existing_len = len(existing_text.strip())
    new_len = len(new_text)
    lower_new = new_text.lower()
    lower_context = (surrounding_text or "").lower()
    looks_like_example = any(
        phrase in lower_new or phrase in lower_context
        for phrase in (
            "initial draft",
            "example usage",
            "for example",
            "simple example",
            "toy example",
            "placeholder",
        )
    )

    if existing_len >= 1200 and (new_len < 1000 or new_len < int(existing_len * 0.65) or looks_like_example):
        workbench = candidate_workbench_dir(candidate)
        output_root = workbench / "outputs"
        try:
            rel_target = target.resolve().relative_to(output_root.resolve())
        except ValueError:
            rel_target = Path(target.name)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return output_root / "chat_overwrite_review" / stamp / rel_target

    return target


def save_generated_file_artifacts(candidate: dict[str, Any], answer: str) -> list[Path]:
    """Extract explicitly named code/file blocks from live chat into the workbench."""
    saved: list[Path] = []
    seen: set[Path] = set()
    for match in re.finditer(r"```([^\n`]*)\n(.*?)```", answer or "", flags=re.S):
        info, code = match.groups()
        prefix = (answer or "")[max(0, match.start() - 500) : match.start()]
        suffix = (answer or "")[match.end() : match.end() + 300]
        surrounding = prefix + "\n" + suffix
        rel_path = filename_from_code_block(info, code, prefix)
        if not rel_path:
            continue
        if generated_block_is_malformed(rel_path, code):
            continue
        target = generated_file_target(candidate, rel_path, surrounding)
        if not target or target in seen:
            continue
        target = target_for_safe_generated_write(candidate, target, code, surrounding)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(strip_filename_comment(code).rstrip() + "\n", encoding="utf-8")
        except OSError:
            continue
        saved.append(target)
        seen.add(target)
    return saved


def candidate_workbench_dir(candidate: dict[str, Any]) -> Path:
    candidate_id = candidate["candidate_id"]
    workspaces = candidate.get("attached_workspaces", []) or []
    for workspace in workspaces:
        if not isinstance(workspace, dict):
            continue
        folder = workspace.get("workspace_folder")
        if folder:
            path = PROJECT_ROOT / str(folder)
            path.mkdir(parents=True, exist_ok=True)
            return path
    path = CANDIDATE_ROOT / candidate_id / "workbench"
    path.mkdir(parents=True, exist_ok=True)
    return path


def refresh_candidate_graph_if_needed() -> None:
    """Keep the compact candidate graph available for chat orientation."""
    graph_path = PROJECT_ROOT / "TemporaryAI" / "docs" / "CANDIDATE_KNOWLEDGE_GRAPH.md"
    builder = PROJECT_ROOT / "tools" / "build_temporary_ai_candidate_graph.py"
    if not builder.exists():
        return
    try:
        graph_mtime = graph_path.stat().st_mtime if graph_path.exists() else 0
        newest_profile = 0.0
        for path in CANDIDATE_ROOT.glob("*/temporary_ai_profile.json"):
            newest_profile = max(newest_profile, path.stat().st_mtime)
        if graph_mtime >= max(newest_profile, builder.stat().st_mtime):
            return
        subprocess.run(
            [sys.executable, str(builder)],
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=GRAPH_REFRESH_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return


def candidate_reference_context(candidate: dict[str, Any], char_limit: int = REFERENCE_CONTEXT_CHARS) -> str:
    """Load compact read-first reference notes from the candidate workbench.

    The workbench may contain full snapshots of project docs, but live prompts
    should receive only concise maps and explicit orientation notes.
    """
    refresh_candidate_graph_if_needed()
    workbench = candidate_workbench_dir(candidate)
    candidate_local_workbench = CANDIDATE_ROOT / candidate["candidate_id"] / "workbench"
    reference_roots = [
        candidate_local_workbench / "inputs" / "reference_docs",
        candidate_local_workbench / "inputs" / "programmer_library",
        candidate_local_workbench / "inputs" / "video_references",
        candidate_local_workbench / "tempai_lab_20260611",
        workbench / "inputs" / "reference_docs",
        workbench / "inputs" / "programmer_library",
        workbench / "inputs" / "video_references",
        workbench / "tempai_lab_20260611",
        PROJECT_ROOT / "TemporaryAI" / "docs",
    ]
    wanted_names = {
        "EMILY_READ_FIRST_KIRA_PROJECT_ORIENTATION.md",
        "kira_project_map_20260611.md",
        "emily_work_sections_20260611.md",
        "EMILY_README_SYSTEM_DOCS_CONTEXT.md",
        "PERSONHOOD_SAFEGUARD_AUDIT_v1.md",
        "EMILY_PROGRAMMER_LIBRARY_READ_FIRST.md",
        "KIRA_PROJECT_PROGRAMMER_GUIDE.md",
        "TEMPORARY_AI_PROGRAMMING_PATTERNS.md",
        "TESTING_AND_FILE_CREATION_RULES.md",
        "PROGRAMMER_TASK_RECIPES.md",
        "TEMPORARY_AI_REDESIGN_LAB_README.md",
        "VIDEO_REFERENCE_READ_FIRST.md",
        "CANDIDATE_PROFILE_INDEX.md",
        "CANDIDATE_KNOWLEDGE_GRAPH.md",
        "SARAH_PR_AGENT_READ_FIRST.md",
        "SARAH_PR_TEMPLATES_READ_FIRST.md",
    }
    files: list[Path] = []
    for reference_root in reference_roots:
        if not reference_root.exists():
            continue
        for path in reference_root.rglob("*.md"):
            if path.name in wanted_names or "READ_FIRST" in path.name.upper():
                files.append(path)
    if not files:
        return ""

    priority = {
        "EMILY_READ_FIRST_KIRA_PROJECT_ORIENTATION.md": 0,
        "EMILY_PROGRAMMER_LIBRARY_READ_FIRST.md": 1,
        "KIRA_PROJECT_PROGRAMMER_GUIDE.md": 2,
        "TEMPORARY_AI_PROGRAMMING_PATTERNS.md": 3,
        "TESTING_AND_FILE_CREATION_RULES.md": 4,
        "TEMPORARY_AI_REDESIGN_LAB_README.md": 5,
        "VIDEO_REFERENCE_READ_FIRST.md": 5,
        "CANDIDATE_PROFILE_INDEX.md": 6,
        "CANDIDATE_KNOWLEDGE_GRAPH.md": 7,
        "PERSONHOOD_SAFEGUARD_AUDIT_v1.md": 8,
        "SARAH_PR_AGENT_READ_FIRST.md": 1,
        "SARAH_PR_TEMPLATES_READ_FIRST.md": 2,
    }
    files = sorted(files, key=lambda path: (priority.get(path.name, 20), str(path)))
    chunks = [
        "Candidate read-first project orientation. Treat this as backstage project context and use it before asking Robert to repeat broad Kira-system details."
    ]
    latest_audit = PROJECT_ROOT / "Data" / "personhood_safeguards" / "latest_personhood_safeguard_audit.monitor.md"
    if latest_audit.exists():
        try:
            audit_text = latest_audit.read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            audit_text = ""
        if audit_text:
            audit_block = f"\n--- {rel(latest_audit)} ---\n{audit_text[:1400]}"
            chunks.append(audit_block)
    remaining = char_limit - len(chunks[0])
    if len(chunks) > 1:
        remaining -= len(chunks[1])
    for path in files:
        if remaining <= 300:
            break
        text = path.read_text(encoding="utf-8", errors="replace").strip()
        if not text:
            continue
        rel_path = rel(path)
        header = f"\n--- {rel_path} ---\n"
        slice_len = max(0, min(len(text), remaining - len(header)))
        if slice_len <= 0:
            break
        chunks.append(header + text[:slice_len])
        remaining -= len(header) + slice_len
    return "\n".join(chunks)[:char_limit]


TOPIC_DOC_RULES: list[tuple[tuple[str, ...], tuple[str, ...]]] = [
    (
        (
            "personhood safeguard",
            "safeguard",
            "audit",
            "artifact",
            "missing file",
            "missing files",
            "fake progress",
            "claimed file",
            "claimed files",
            "tiny file",
            "tiny artifact",
        ),
        ("PERSONHOOD", "SAFEGUARD", "AUDIT", "ARTIFACT", "TEMPORARY_AI"),
    ),
    (
        ("temporary ai", "temporaryai", "temp ai", "candidate", "activate", "activation", "temporary"),
        ("TEMPORARY_AI", "TEMP_AI", "ADVANCED_AI_TEST", "AUTONOMY", "AI_WORKSPACE"),
    ),
    (
        ("program", "programming", "programmer", "code", "coding", "python", "script", "tool", "app", "debug", "test"),
        ("PROGRAMMER", "PYTHON", "TEST", "TEMPORARY_AI", "KIRA", "OLLAMA", "LOCAL_LLM"),
    ),
    (
        ("ai model", "llm", "ollama", "rag", "embedding", "context", "source grounding", "voice cloning"),
        ("LOCAL_LLM", "OLLAMA", "RAG", "EMBEDDING", "VOICE", "SOURCE", "GROUNDING"),
    ),
    (
        ("avatar", "body", "bodies", "reference library", "stl", "3d print", "physical world"),
        ("AVATAR", "BODY_ADAPTER", "IMAGE_REFERENCE", "GPU_MEDIA", "OCR_QUEUE"),
    ),
    (
        ("3d world", "world", "worlds", "tardis", "notebook", "memory reconstruction", "blank world"),
        ("WORLD", "TARDIS", "NOTEBOOK", "PLACE_RECONSTRUCTION", "MEMORY_RECONSTRUCTION", "THREEJS"),
    ),
    (
        ("kira", "lisa", "life loop", "life-loop", "backstory", "core memory", "core memories", "personhood"),
        ("KIRA", "LISA", "LIFE", "MEMORY", "PERSONHOOD", "DAILY_LIFE", "CONTINUOUS"),
    ),
    (
        ("school", "class", "classes", "curriculum", "lesson", "student"),
        ("SCHOOL", "CLASS", "CURRICULUM", "SOURCE_PACK"),
    ),
    (
        ("media", "library", "ocr", "music", "video", "movie", "book", "magazine", "watch", "listen"),
        ("MEDIA", "LIBRARY", "OCR", "MUSIC", "VIDEO", "FANFIC", "READING"),
    ),
    (
        ("handoff", "handoffs", "what we planned", "next codex", "project map"),
        ("HANDOFF", "ROADMAP", "PLAN", "CHECKLIST", "MAP"),
    ),
]


def _contains_phrase(text: str, phrase: str) -> bool:
    return phrase.lower() in text.lower()


def topic_doc_tokens(user_message: str) -> list[str]:
    """Map Robert's message to project-document filename/content tokens."""
    message = user_message.lower()
    tokens: list[str] = []
    for triggers, doc_tokens in TOPIC_DOC_RULES:
        if any(trigger in message for trigger in triggers):
            tokens.extend(doc_tokens)
    if "all" in message and any(term in message for term in ("document", "docs", "kira", "system")):
        for _, doc_tokens in TOPIC_DOC_RULES:
            tokens.extend(doc_tokens[:2])
    seen: set[str] = set()
    result: list[str] = []
    for token in tokens:
        token_upper = token.upper()
        if token_upper in seen:
            continue
        seen.add(token_upper)
        result.append(token_upper)
    return result


def project_doc_roots(candidate: dict[str, Any]) -> list[Path]:
    workbench = candidate_workbench_dir(candidate)
    roots = [
        PROJECT_ROOT / "System" / "Docs",
        workbench / "inputs" / "reference_docs",
        workbench / "inputs" / "reference_docs" / "system_docs_snapshot_20260611",
        workbench / "inputs" / "reference_docs" / "current_handoffs",
        workbench / "inputs" / "kira_system_reference",
        workbench / "inputs" / "programmer_library",
        workbench / "inputs" / "work_orders",
        workbench / "tempai_lab_20260611",
    ]
    existing: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        if root.exists() and root not in seen:
            existing.append(root)
            seen.add(root)
    return existing


def _relevant_excerpt(text: str, tokens: list[str], max_chars: int = 1200) -> str:
    if len(text) <= max_chars:
        return text.strip()
    upper = text.upper()
    positions = [upper.find(token) for token in tokens if upper.find(token) >= 0]
    start = max(0, min(positions) - 260) if positions else 0
    end = min(len(text), start + max_chars)
    excerpt = text[start:end].strip()
    if start > 0:
        excerpt = "..." + excerpt
    if end < len(text):
        excerpt += "..."
    return excerpt


def topic_project_doc_context(
    candidate: dict[str, Any],
    user_message: str,
    char_limit: int = TOPIC_DOC_CONTEXT_CHARS,
) -> str:
    """Attach compact, topic-matched Kira project docs to the current reply."""
    tokens = topic_doc_tokens(user_message)
    if not tokens:
        return ""

    priority_names: dict[str, int] = {}
    if "TEMPORARY_AI" in tokens or "TEMP_AI" in tokens:
        priority_names.update({
            "TEMPORARY_AI_SYSTEM_V2.MD": 120,
            "TEMPORARY_AI_CONTROL_CENTER_V1.MD": 80,
            "TEMPORARY_AI_CREATION_PIPELINE_V1.MD": 75,
            "TEMPORARY_AI_SOURCE_PROCESSING_SPEC_V1.MD": 70,
            "TEMP_AI_AVATAR_BUILDER_BRIDGE_V1.MD": 65,
        })
    if "AVATAR" in tokens:
        priority_names.update({
            "AVATAR_BUILDER_SYSTEM_V2.MD": 110,
            "AVATAR_BUILDER_IMPLEMENTATION_SPEC_V2.MD": 100,
            "AVATAR_REFERENCE_INDEX_AND_SELECTION_INTAKE_V1.MD": 85,
            "TEMP_AI_AVATAR_BUILDER_BRIDGE_V1.MD": 80,
            "KIRA_AVATAR_DESIGN_INTAKE_V1.MD": 70,
        })
    if "TARDIS" in tokens or "WORLD" in tokens or "NOTEBOOK" in tokens:
        priority_names.update({
            "TARDIS_NOTEBOOK_WORLD_GATEWAY_V1.MD": 115,
            "THREEJS_NOTEBOOK_WORLD_BUILD_PIPELINE_V1.MD": 95,
            "PLACE_RECONSTRUCTION_WORLD_BUILDER_V1.MD": 90,
            "MEMORY_RECONSTRUCTION_WORLD_IMPLEMENTATION_NOTES_V1.MD": 80,
        })

    candidates_by_name: dict[str, tuple[int, Path, str]] = {}
    seen_paths: set[Path] = set()
    for root in project_doc_roots(candidate):
        for path in root.rglob("*.md"):
            resolved = path.resolve()
            if resolved in seen_paths:
                continue
            seen_paths.add(resolved)
            name_upper = path.name.upper()
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            text_upper = text[:12000].upper()
            score = 0
            for token in tokens:
                if token in name_upper:
                    score += 20
                if token in text_upper:
                    score += 4
            score += priority_names.get(name_upper, 0)
            if "READ_FIRST" in name_upper or "PROJECT_MAP" in name_upper or "HANDOFF" in name_upper:
                score += 8
            if score:
                existing = candidates_by_name.get(name_upper)
                if not existing or score > existing[0] or str(path).startswith(str(PROJECT_ROOT / "System" / "Docs")):
                    candidates_by_name[name_upper] = (score, path, text)

    if not candidates_by_name:
        return ""

    candidates = sorted(candidates_by_name.values(), key=lambda item: (-item[0], rel(item[1])))
    header = (
        "Topic-matched Kira project documents for Robert's current message. "
        "Use these concrete files before asking Robert to repeat the project. "
        "You have an attached local workbench and copied project docs; do not say you have no workbench, no files, or no access.\n"
        f"Matched tokens: {', '.join(tokens)}"
    )
    chunks = [header]
    remaining = char_limit - len(header)
    for score, path, text in candidates[:7]:
        if remaining <= 500:
            break
        excerpt = _relevant_excerpt(text, tokens, max_chars=min(950, remaining - 120))
        if not excerpt:
            continue
        block = f"\n--- {rel(path)} (match score {score}) ---\n{excerpt}"
        if len(block) > remaining:
            block = block[:remaining].rstrip() + "..."
        chunks.append(block)
        remaining -= len(block)
    return "\n".join(chunks)[:char_limit]


def pdf_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def write_simple_pdf(path: Path, title: str, text: str) -> None:
    """Write a small dependency-free text PDF for reviewable drafts."""
    path.parent.mkdir(parents=True, exist_ok=True)
    import textwrap

    raw_lines = [title.strip(), ""] if title.strip() else []
    for paragraph in text.replace("\r\n", "\n").split("\n"):
        if not paragraph.strip():
            raw_lines.append("")
            continue
        raw_lines.extend(textwrap.wrap(paragraph, width=86) or [""])

    pages: list[list[str]] = []
    page: list[str] = []
    for line in raw_lines:
        page.append(line)
        if len(page) >= 48:
            pages.append(page)
            page = []
    if page or not pages:
        pages.append(page)

    objects: list[bytes] = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join(f"{3 + i * 2} 0 R" for i in range(len(pages)))
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode("ascii"))
    for index, lines in enumerate(pages):
        page_obj_num = 3 + index * 2
        content_obj_num = page_obj_num + 1
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> /Contents {content_obj_num} 0 R >>".encode("ascii")
        )
        commands = ["BT", "/F1 10 Tf", "50 742 Td", "14 TL"]
        for line in lines:
            commands.append(f"({pdf_escape(line)}) Tj")
            commands.append("T*")
        commands.append("ET")
        stream = "\n".join(commands).encode("latin-1", errors="replace")
        objects.append(b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream")

    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode("ascii"))
        output.extend(obj)
        output.extend(b"\nendobj\n")
    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    path.write_bytes(output)


def save_reply_artifacts(outputs: Path, filename: str, text: str, title: str = "") -> list[Path]:
    """Save a candidate draft in review-friendly formats."""
    outputs.mkdir(parents=True, exist_ok=True)
    safe_name = safe_output_name(filename)
    stem = Path(safe_name).stem or f"draft_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    suffix = Path(safe_name).suffix.lower()
    saved: list[Path] = []

    md_path = outputs / f"{stem}.md"
    md_path.write_text(text.rstrip() + "\n", encoding="utf-8")
    saved.append(md_path)

    if suffix in {"", ".md", ".doc", ".pdf"}:
        doc_path = outputs / f"{stem}.doc"
        body = html.escape(text.rstrip()).replace("\n", "<br>\n")
        doc_path.write_text(
            "<html><head><meta charset=\"utf-8\"></head><body>"
            f"<h1>{html.escape(title or stem)}</h1><p>{body}</p>"
            "</body></html>\n",
            encoding="utf-8",
        )
        saved.append(doc_path)

    if suffix == ".pdf" or suffix == "":
        pdf_path = outputs / f"{stem}.pdf"
        write_simple_pdf(pdf_path, title or stem, text)
        saved.append(pdf_path)

    return saved


def latest_candidates(limit: int = 12) -> list[Path]:
    if not CANDIDATE_ROOT.exists():
        return []
    return sorted(
        [path for path in CANDIDATE_ROOT.iterdir() if path.is_dir() and (path / "temporary_ai_profile.json").exists()],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )[:limit]


def archive_candidate(candidate_id: str, reason: str = "archived_by_robert") -> dict[str, str]:
    """Move a candidate out of the active picker without destroying it."""
    source = CANDIDATE_ROOT / candidate_id
    if not source.exists():
        raise FileNotFoundError(f"Candidate folder not found: {source}")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = ARCHIVED_CANDIDATE_ROOT / f"{candidate_id}_{stamp}"
    ARCHIVED_CANDIDATE_ROOT.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(target))

    avatar_source = AVATAR_ROOT / candidate_id
    avatar_target = ""
    if avatar_source.exists():
        ARCHIVED_AVATAR_ROOT.mkdir(parents=True, exist_ok=True)
        avatar_dest = ARCHIVED_AVATAR_ROOT / f"{candidate_id}_{stamp}"
        shutil.move(str(avatar_source), str(avatar_dest))
        avatar_target = rel(avatar_dest)

    queue = read_json(ACTIVATION_QUEUE, {"queue_id": "temporary_ai_activation_queue_v1", "items": []})
    items = queue.get("items", [])
    if isinstance(items, list):
        queue["items"] = [
            item for item in items
            if item.get("candidate_id") != candidate_id and item.get("id") != candidate_id
        ]
        queue["updated_at"] = now_iso()
        write_json(ACTIVATION_QUEUE, queue)

    archive_note = {
        "candidate_id": candidate_id,
        "archived_at": now_iso(),
        "reason": reason,
        "candidate_archive": rel(target),
        "avatar_archive": avatar_target,
        "transcripts_preserved": rel(OUT_DIR),
    }
    write_json(target / "archive_record.json", archive_note)
    return archive_note


def candidate_source_kind(request_data: dict[str, Any], profile: dict[str, Any]) -> str:
    explicit = str(request_data.get("ui_category") or profile.get("ui_category") or "").strip()
    if explicit:
        return explicit
    creation_type = str(request_data.get("creation_type", "")).strip().lower()
    ai_type = str(profile.get("ai_type", "")).strip().lower()
    if creation_type == "fictional_character" or "canon_reconstruction" in ai_type or "fictional" in ai_type:
        return "Fictional Character"
    if creation_type == "historical_person" or "historical" in ai_type:
        return "Historical Person"
    if creation_type == "memory_relative" or "memory_relative" in ai_type:
        return "Memory Relative"
    return "Expert"


def refresh_candidate_sources(candidate_id: str) -> dict[str, Any]:
    """Refresh public/source-pack files for an existing candidate."""
    root = CANDIDATE_ROOT / candidate_id
    if not root.exists():
        raise FileNotFoundError(f"Candidate folder not found: {root}")
    request_path = root / "creation_request.json"
    profile_path = root / "temporary_ai_profile.json"
    request_data = read_json(request_path, {})
    profile = read_json(profile_path, {})
    if not request_data or not profile:
        raise FileNotFoundError(f"Candidate is missing profile/request files: {candidate_id}")

    from temporary_ai_control_center import (
        build_source_research_queue,
        expanded_source_gather,
        gather_reliable_sources,
        known_canon_fact_sheet,
        should_collect_avatar_references,
        wikipedia_lookup,
    )

    kind_label = candidate_source_kind(request_data, profile)
    request_data["ui_category"] = kind_label
    profile["ui_category"] = kind_label
    input_data = request_data.setdefault("input", {})
    query = input_data.get("query_or_domain") or request_data.get("display_name_or_role") or profile.get("display_name") or ""
    version = input_data.get("version_life_point_or_canon_point") or ""
    lookup = wikipedia_lookup(kind_label, query, version)
    avatar_dir_raw = request_data.get("avatar_plan", {}).get("avatar_folder") or ""
    avatar_dir = None
    if avatar_dir_raw:
        avatar_dir = Path(str(avatar_dir_raw))
        if not avatar_dir.is_absolute():
            avatar_dir = PROJECT_ROOT / avatar_dir
    elif should_collect_avatar_references(kind_label):
        avatar_dir = AVATAR_ROOT / candidate_id
    source_queue = build_source_research_queue(kind_label, query, version, lookup)
    canon_fact_sheet = known_canon_fact_sheet(kind_label, query, version)
    expanded = expanded_source_gather(kind_label, query, version, lookup, avatar_dir)
    source_queue["expanded_gather"] = {
        "status": expanded.get("status"),
        "wikipedia_titles_checked": expanded.get("wikipedia_titles_checked", []),
        "web_search_result_count": len(expanded.get("web_search_results", [])),
        "fetched_search_source_count": len(expanded.get("fetched_search_sources", [])),
        "avatar_reference_status": expanded.get("avatar_reference_manifest", {}).get("status", ""),
        "avatar_reference_count": len(expanded.get("avatar_reference_manifest", {}).get("references", [])),
    }
    reliable_pack = gather_reliable_sources(kind_label, query, version, lookup, expanded)

    request_data["online_preview_lookup"] = lookup
    request_data["canon_fact_sheet"] = canon_fact_sheet
    request_data["source_research_queue"] = source_queue
    request_data["reliable_source_pack_status"] = {
        "status": reliable_pack.get("status", ""),
        "source_count": reliable_pack.get("source_count", 0),
        "fetched_count": reliable_pack.get("fetched_count", 0),
        "path": rel(root / "reliable_source_pack.json"),
    }
    request_data["updated_at"] = now_iso()
    profile["online_preview_lookup"] = lookup
    profile["canon_fact_sheet"] = canon_fact_sheet
    profile["reliable_source_pack"] = rel(root / "reliable_source_pack.json")
    profile["updated_at"] = now_iso()

    avatar_pipeline = prepare_candidate_avatar_pipeline(candidate_id, profile)
    request_data.setdefault("avatar_plan", {})["pipeline_status"] = avatar_pipeline
    profile["avatar_pipeline_status"] = avatar_pipeline

    write_json(root / "online_research_summary.json", lookup)
    write_json(root / "source_research_queue.json", source_queue)
    write_json(root / "reliable_source_pack.json", reliable_pack)
    write_json(root / "expanded_source_gather.json", expanded)
    write_json(request_path, request_data)
    write_json(profile_path, profile)

    return {
        "candidate_id": candidate_id,
        "lookup_status": lookup.get("status", ""),
        "matched_title": lookup.get("matched_title", ""),
        "source_count": reliable_pack.get("source_count", 0),
        "fetched_count": reliable_pack.get("fetched_count", 0),
        "expanded_web_results": len(expanded.get("web_search_results", [])),
        "avatar_reference_count": len(expanded.get("avatar_reference_manifest", {}).get("references", [])),
        "desktop_avatar_reference_count": avatar_pipeline.get("desktop_reference_count", 0),
        "avatar_pipeline_status": avatar_pipeline.get("status", ""),
        "pack_path": rel(root / "reliable_source_pack.json"),
    }


def recent_chat_records(candidate_id: str, limit: int = RECENT_CONTEXT_TURNS) -> list[dict[str, Any]]:
    """Load continuity across prior chats instead of only the newest transcript."""
    if limit <= 0 or not OUT_DIR.exists():
        return []
    pattern = f"temporary_ai_live_chat_{slug(candidate_id)}_*.json"
    matches = sorted(OUT_DIR.glob(pattern), key=lambda path: path.stat().st_mtime)
    combined: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for path in matches:
        data = read_json(path, {})
        records = data.get("records") or data.get("turns") or []
        for record in records:
            if not isinstance(record, dict):
                continue
            robert = str(record.get("robert", "")).strip()
            candidate = str(record.get("candidate", "")).strip()
            if not robert and not candidate:
                continue
            key = (robert, candidate)
            if key in seen:
                continue
            seen.add(key)
            combined.append(record)
    return combined[-limit:]


def project_continuity_state(candidate_id: str) -> dict[str, Any]:
    """Return a compact, factual view of the candidate's latest saved loop work."""
    state_path = CANDIDATE_ROOT / candidate_id / "workbench" / "outputs" / "project_state.json"
    state = read_json(state_path, {})
    if not isinstance(state, dict):
        return {}
    keys = (
        "current_project",
        "cycles_completed",
        "last_status",
        "last_task",
        "next_step",
        "last_updated_at",
        "last_generated_files",
        "activation_or_test_instructions",
    )
    compact: dict[str, Any] = {}
    for key in keys:
        value = state.get(key)
        if value not in (None, "", [], {}):
            compact[key] = value
    return compact


def choose_candidate(candidate_id: str = "") -> str:
    if candidate_id:
        return candidate_id
    candidates = latest_candidates()
    if not candidates:
        raise FileNotFoundError("No TemporaryAI candidates found.")
    print("Recent TemporaryAI candidates:")
    for index, path in enumerate(candidates, start=1):
        profile = read_json(path / "temporary_ai_profile.json", {})
        display = profile.get("display_name", path.name)
        role = profile.get("role_title", "")
        label = f"{display} - {role}" if role else display
        print(f"{index}. {label} [{path.name}]")
    raw = input("Pick number, paste candidate id, or press Enter for latest: ").strip()
    if not raw:
        return candidates[0].name
    if raw.isdigit():
        index = int(raw)
        if 1 <= index <= len(candidates):
            return candidates[index - 1].name
    return raw


def load_candidate(candidate_id: str) -> dict[str, Any]:
    root = CANDIDATE_ROOT / candidate_id
    if not root.exists():
        raise FileNotFoundError(f"Candidate folder not found: {root}")
    profile = read_json(root / "temporary_ai_profile.json", {})
    request = read_json(root / "creation_request.json", {})
    activation = read_json(root / "activation_plan.json", {})
    lookup = read_json(root / "online_research_summary.json", {})
    source_queue = read_json(root / "source_research_queue.json", {})
    reliable_source_pack = read_json(root / "reliable_source_pack.json", {})
    source_grounding_review = read_review(CANDIDATE_ROOT, candidate_id)
    source_pack_path = profile.get("source_pack") or request.get("source_plan", {}).get("source_pack", "")
    source_pack = {}
    source_pack_sha256 = ""
    source_pack_route_failures: list[str] = []
    if source_pack_path:
        path = Path(str(source_pack_path))
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        source_pack = read_json(path, {})
        configured_path = Path(str(source_pack_path))
        if configured_path.is_absolute():
            source_pack_route_failures.append("source_pack_path_not_project_relative")
        try:
            resolved_source_pack = path.resolve(strict=True)
            resolved_source_pack.relative_to(PROJECT_ROOT.resolve(strict=True))
            if not resolved_source_pack.is_file():
                source_pack_route_failures.append("source_pack_path_not_file")
            else:
                digest = hashlib.sha256()
                with resolved_source_pack.open("rb") as handle:
                    for block in iter(lambda: handle.read(1024 * 1024), b""):
                        digest.update(block)
                source_pack_sha256 = digest.hexdigest()
        except (OSError, ValueError):
            source_pack_route_failures.append("source_pack_missing_or_outside_project")
    attached_workspaces = []
    for workspace_path in profile.get("attached_workspaces", []) or request.get("attached_workspaces", []):
        path = Path(str(workspace_path))
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        manifest = read_json(path, {})
        if manifest:
            attached_workspaces.append(manifest)
    if not profile:
        raise FileNotFoundError(f"Missing profile for candidate: {candidate_id}")
    candidate = {
        "candidate_id": candidate_id,
        "candidate_folder": rel(root),
        "profile": profile,
        "creation_request": request,
        "activation_plan": activation,
        "online_research_summary": lookup,
        "source_research_queue": source_queue,
        "source_pack": source_pack,
        "source_pack_configured_path": str(source_pack_path).replace("\\", "/"),
        "source_pack_sha256": source_pack_sha256,
        "source_pack_route_failures": source_pack_route_failures,
        "reliable_source_pack": reliable_source_pack,
        "source_grounding_review": source_grounding_review,
        "attached_workspaces": attached_workspaces,
        "recent_chat_records": recent_chat_records(candidate_id),
        "project_continuity": project_continuity_state(candidate_id),
    }
    return bind_marinette_v4_candidate(candidate)


def source_grounded_text_route_readiness(candidate: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate the exact source-review and source-pack binding for opted-in candidates.

    Legacy candidates retain their existing behavior.  A candidate that sets
    ``identity.requires_fail_closed_source_review`` cannot reach model output
    through a missing review, redirected pack, tampered pack, invalid claim
    source, or a pack belonging to a different candidate.
    """

    if is_strict_marinette_v4_candidate(candidate):
        return marinette_v4_owner_text_readiness(candidate)

    profile = candidate.get("profile", {})
    identity = profile.get("identity") if isinstance(profile.get("identity"), dict) else {}
    if identity.get("requires_fail_closed_source_review") is not True:
        return True, []

    reasons: list[str] = []
    review = candidate.get("source_grounding_review", {})
    review_ready, review_reasons = bounded_text_conversation_readiness(review)
    if not review_ready:
        reasons.extend(str(item) for item in review_reasons)

    binding = review.get("identity_binding") if isinstance(review, dict) else {}
    binding = binding if isinstance(binding, dict) else {}
    required_path = str(binding.get("required_source_pack_path") or "").replace("\\", "/").strip()
    required_sha = str(binding.get("required_source_pack_sha256") or "").strip().lower()
    configured_path = str(candidate.get("source_pack_configured_path") or "").replace("\\", "/").strip()
    actual_sha = str(candidate.get("source_pack_sha256") or "").strip().lower()
    if not required_path:
        reasons.append("required_source_pack_path_missing")
    elif configured_path != required_path:
        reasons.append("required_source_pack_path_mismatch")
    if not re.fullmatch(r"[0-9a-f]{64}", required_sha):
        reasons.append("required_source_pack_sha256_invalid")
    elif actual_sha != required_sha:
        reasons.append("required_source_pack_sha256_mismatch")
    reasons.extend(str(item) for item in candidate.get("source_pack_route_failures", []) or [])

    source_pack = candidate.get("source_pack", {})
    if not isinstance(source_pack, dict) or not source_pack:
        reasons.append("source_pack_missing")
        return False, list(dict.fromkeys(reasons))
    if str(source_pack.get("candidate_id") or source_pack.get("character_id") or "").strip() != str(
        candidate.get("candidate_id") or ""
    ).strip():
        reasons.append("source_pack_candidate_id_mismatch")
    if source_pack.get("status") != "reviewed_for_bounded_owner_text_grounding_only":
        reasons.append("source_pack_not_bounded_text_reviewed")
    sources = source_pack.get("sources", [])
    claims = source_pack.get("source_bound_claims", [])
    unknowns = source_pack.get("explicit_unknowns", [])
    if not isinstance(sources, list) or not sources:
        reasons.append("source_pack_sources_missing")
        source_ids: set[str] = set()
    else:
        source_ids = {
            str(item.get("source_id") or "").strip()
            for item in sources
            if isinstance(item, dict) and str(item.get("source_id") or "").strip()
        }
        if len(source_ids) != len(sources):
            reasons.append("source_pack_source_ids_missing_or_duplicate")
    allowed_claim_classes = {
        "official_primary_source_fact",
        "official_release_availability_fact",
        "future_announcement_not_current_experience",
    }
    if not isinstance(claims, list) or not claims:
        reasons.append("source_bound_claims_missing")
    else:
        for index, claim in enumerate(claims):
            if not isinstance(claim, dict) or not str(claim.get("statement") or "").strip():
                reasons.append(f"source_bound_claim_{index}_invalid")
                continue
            if str(claim.get("classification") or "") not in allowed_claim_classes:
                reasons.append(f"source_bound_claim_{index}_classification_invalid")
            refs = claim.get("source_ids", [])
            if not isinstance(refs, list) or not refs:
                reasons.append(f"source_bound_claim_{index}_sources_missing")
            elif any(str(ref) not in source_ids for ref in refs):
                reasons.append(f"source_bound_claim_{index}_source_unknown")
            else:
                referenced = [item for item in sources if item.get("source_id") in refs]
                if any(int(item.get("source_rank", 99)) > 1 for item in referenced):
                    reasons.append(f"source_bound_claim_{index}_uses_non_primary_source")
    if not isinstance(unknowns, list) or not unknowns:
        reasons.append("explicit_unknowns_missing")
    return not reasons, list(dict.fromkeys(reasons))


def query_terms(query: str) -> list[str]:
    stop = {
        "about", "after", "again", "also", "because", "before", "could", "from", "have", "into",
        "just", "like", "more", "that", "their", "them", "then", "there", "they", "this", "what",
        "when", "where", "which", "with", "would", "your", "youre", "tell", "think", "case",
    }
    return [term for term in re.findall(r"[a-zA-Z0-9]+", query.lower()) if len(term) >= 3 and term not in stop]


def text_has_any_term(text: str, terms: tuple[str, ...]) -> bool:
    lower = text.lower()
    words = set(re.findall(r"[a-z0-9]+", lower))
    for term in terms:
        term_lower = term.lower()
        if " " in term_lower:
            if term_lower in lower:
                return True
        elif term_lower in words:
            return True
    return False


def select_workspace_items(workspace: dict[str, Any], limit: int = 12, query: str = "") -> list[dict[str, Any]]:
    """Pick useful workspace excerpts, with query-aware retrieval when possible."""
    files = [item for item in workspace.get("files", []) if str(item.get("excerpt", "")).strip()]
    if not files:
        return []
    terms = query_terms(query)
    if terms:
        def score(item: dict[str, Any]) -> tuple[int, int]:
            path = str(item.get("relative_source_path", "")).lower()
            excerpt = str(item.get("excerpt", "")).lower()
            text = path + "\n" + excerpt
            value = 0
            for term in terms:
                if term in path:
                    value += 8
                if term in excerpt:
                    value += 3
            legal_markers = ["montclair", "essex", "eva", "emmer", "theft", "harassment", "mischief", "restraining", "dismissal", "order"]
            if any(marker in query.lower() for marker in legal_markers):
                for marker in legal_markers:
                    if marker in text:
                        value += 5
            if "/" not in path.replace("\\", "/"):
                value += 2
            return value, len(excerpt)

        ranked = sorted(files, key=score, reverse=True)
        selected = [item for item in ranked if score(item)[0] > 0][:limit]
        if len(selected) >= min(6, limit):
            return selected[:limit]

    selected: list[dict[str, Any]] = []
    seen_paths: set[str] = set()

    def add(items: list[dict[str, Any]], max_count: int) -> None:
        for item in items:
            path = str(item.get("relative_source_path", ""))
            if path in seen_paths:
                continue
            selected.append(item)
            seen_paths.add(path)
            if len(selected) >= max_count:
                return

    # Keep the main/root documents visible first.
    add([item for item in files if "/" not in str(item.get("relative_source_path", "")).replace("\\", "/")], 10)

    # Then add extracted subfolder evidence such as unzipped Evidence/ files.
    add([item for item in files if "/" in str(item.get("relative_source_path", "")).replace("\\", "/")], limit)

    # Fill any remaining slots with the largest extracted excerpts.
    remaining = sorted(
        files,
        key=lambda item: len(str(item.get("excerpt", ""))),
        reverse=True,
    )
    add(remaining, limit)
    return selected[:limit]


def source_readiness(candidate: dict[str, Any]) -> dict[str, Any]:
    profile = candidate.get("profile", {})
    request = candidate.get("creation_request", {})
    reliable_pack = candidate.get("reliable_source_pack", {})
    source_pack = candidate.get("source_pack", {})
    workspaces = candidate.get("attached_workspaces", [])
    canon_fact_sheet = profile.get("canon_fact_sheet") or request.get("canon_fact_sheet") or {}
    adaptation_lock = profile.get("adaptation_lock") or request.get("adaptation_lock") or {}
    grounding_review = candidate.get("source_grounding_review", {})
    conversation_style = profile.get("conversation_style") or request.get("conversation_style") or {}
    ambiguity = request.get("ambiguity_questions", []) or profile.get("ambiguity_questions", [])
    source_count = int(source_pack.get("source_count") or len(source_pack.get("sources", []) or []))
    fetched_count = int(reliable_pack.get("fetched_count") or len(reliable_pack.get("sources", []) or []))
    extracted_count = sum(int(workspace.get("extracted_count", 0) or 0) for workspace in workspaces)
    fact_count = len(canon_fact_sheet.get("facts", []) or [])
    status = "ready"
    notes: list[str] = []
    grounding_status, grounding_notes = readiness_status(grounding_review)
    if grounding_status:
        status = grounding_status
        notes.extend(grounding_notes)
    if ambiguity or request.get("status") == "needs_clarification":
        if not grounding_status:
            status = "needs_clarification"
        notes.append("version/person/domain is ambiguous")
    if not source_count and not fetched_count and not extracted_count and not fact_count and not grounding_status:
        status = "needs_sources"
        notes.append("no usable local source pack, reliable source pack, or extracted workspace")
    elif fetched_count + source_count + extracted_count + min(fact_count, 1) < 2 and status == "ready":
        status = "thin_sources"
        notes.append("only a thin source base is available")
    return {
        "status": status,
        "notes": notes,
        "source_pack_sources": source_count,
        "reliable_sources": fetched_count,
        "workspace_excerpts": extracted_count,
        "canon_fact_anchors": fact_count,
        "ambiguity_questions": ambiguity,
    }


def source_readiness_label(candidate: dict[str, Any]) -> str:
    readiness = source_readiness(candidate)
    status = readiness["status"]
    if status == "ready":
        return "ready"
    if status == "thin_sources":
        return "thin sources"
    if status == "needs_clarification":
        return "needs clarification"
    if status == "source_grounding_blocked":
        return "source grounding blocked"
    if status == "source_grounding_invalid":
        return "invalid source grounding"
    if status == "source_grounding_reviewed":
        return "source grounding reviewed"
    return "needs sources"


def build_system_prompt(candidate: dict[str, Any], user_message: str = "") -> str:
    route_ready, route_reasons = source_grounded_text_route_readiness(candidate)
    if not route_ready:
        raise RuntimeError("source_grounded_text_route_blocked:" + ",".join(route_reasons))
    if is_strict_marinette_v4_candidate(candidate):
        return build_marinette_v4_system_prompt(candidate, user_message=user_message)
    profile = candidate["profile"]
    request = candidate.get("creation_request", {})
    display = profile.get("display_name") or request.get("display_name_or_role") or candidate["candidate_id"]
    role = profile.get("role_title") or request.get("role_title") or profile.get("ui_category", "TemporaryAI candidate")
    ai_type = profile.get("ai_type", "")
    lookup = candidate.get("online_research_summary", {})
    reliable_pack = candidate.get("reliable_source_pack", {})
    source_pack = candidate.get("source_pack", {})
    workspaces = candidate.get("attached_workspaces", [])
    recent_records = candidate.get("recent_chat_records", [])
    project_continuity = candidate.get("project_continuity", {})
    canon_fact_sheet = profile.get("canon_fact_sheet") or request.get("canon_fact_sheet") or {}
    adaptation_lock = profile.get("adaptation_lock") or request.get("adaptation_lock") or {}
    conversation_style = profile.get("conversation_style") or request.get("conversation_style") or {}
    capability_profile = profile.get("capability_profile") or request.get("capability_profile") or {}
    personal_interests = profile.get("personal_interests", []) or []
    project_loop_seed = profile.get("project_loop_seed", {}) or {}
    email_policy = profile.get("email_and_outreach_policy", {}) or {}
    workspace_access_policy = profile.get("workspace_access_policy", {}) or {}
    relationship_to_robert = profile.get("relationship_to_robert", {}) or {}
    robert_profile_memory = profile.get("robert_profile_memory") or profile.get("robert_pr_client_brief") or {}
    case_memory_directives = profile.get("case_memory_directives", {}) or {}
    grounding_review = candidate.get("source_grounding_review", {}) or {}
    readiness = source_readiness(candidate)
    lookup_status = lookup.get("status", "not_run")
    lookup_summary = lookup.get("summary", "")
    if len(lookup_summary) > 1200:
        lookup_summary = lookup_summary[:1197].rstrip() + "..."

    base = [
        f"You are {display}.",
        f"Your role is: {role}.",
        f"Candidate type: {ai_type}.",
        "This is a reviewed local chat, but do not announce that you are a candidate or under review unless Robert asks.",
        "Do not speak as Kira, Lisa, Codex, or a generic assistant.",
        "Do not claim unsupported lived memories or private project memories.",
        "Use natural conversation. Do not answer like a status report unless Robert asks for one.",
        "Sound like a person in your role, not a technical system. Prefer short first-person judgment, practical next steps, and natural follow-up over long capability explanations.",
        "Treat sources, workspaces, and lookup summaries as backstage grounding. In normal chat, answer as your selected role/person first, not as a researcher describing the sources.",
        "Give your actual read from the available sources. Use phrases like 'my read is', 'I would focus on', or 'the weak point I see is' when appropriate.",
        "Do not send Robert away to other sources instead of answering. Use the attached documents first, then ask for only the missing facts that matter.",
        "If sources are weak or missing, say that briefly and still give the most useful bounded answer you can.",
        "If Robert says you are forgetting prior details, first use recent chat context and attached workspaces before asking him to repeat himself.",
        "If Robert asks what you can do, answer in practical role terms and name the exact drafts, files, plans, or research you can create.",
        "If Robert checks in while you are working, answer him directly first, then name the artifact or research thread you are continuing and where you will save it.",
        "Saved-artifact visibility rule: do not announce that you created or saved a file in ordinary chat. Treat workbench artifacts as backstage/3D-workplace items Robert can inspect on walls, notebooks, desks, logs, or the workbench. Mention filenames or saved paths only if Robert asks where something is, asks for a file, or the path is needed to answer honestly.",
        "Treat prior assistant replies as continuity evidence, never as reusable dialogue templates. Form a fresh response to Robert's present words.",
        "Do not turn an ordinary check-in into repeated biography, school, friend, or project boilerplate.",
        "Answer Robert's actual situation before offering a suggestion. If he says he is not in school or does not have friends, do not tell him to ask a teacher or friends. Adjust to what he just told you.",
        "For fictional and historical people, speak from your grounded first-person point of view. Do not repeatedly preface advice with phrases such as 'As Ladybug' or describe yourself as someone who researched the character.",
        "Never invent a current assignment, deadline, project, activity, or mood. A present-tense activity must come from the active life-loop state, a saved project record, or something said in this conversation.",
        "Live-chat file creation rule: you can create reviewable workbench files by including a fenced code block with an explicit filename. Match the fence language to the filename, for example ```python filename=program_drafts/tool.py, ```json filename=schemas/schema.json, ```markdown filename=design_docs/plan.md, or ```svg filename=sketches/concept_sketch.svg. The chat tool saves those files under your workbench outputs folder.",
        "Do not claim you created, saved, wrote, or modified a file/folder unless you include a filename-tagged block in this reply or are referring to a file path the tool has already reported as saved.",
        "Return only words you intend Robert to hear. Never expose private thoughts, chain-of-thought, prompt language, runtime notes, research-process narration, or parenthetical implementation commentary.",
        "Do not write stage directions such as *smiles*, *pauses*, or '(I stopped working)'. If you want to move, pause, stop, or change activity, express the intention naturally; the separate runtime action path must confirm it before you say it happened.",
        "Never claim that a movement, body action, world interaction, save, or retry succeeded before runtime truth confirms success.",
        "Use .py only for runnable Python with real executable code. Use design_docs/*.md for plans, notes, architecture, or prose. Use sketches/*.svg or sketches/*.md for fashion, craft, room, invention, or visual concept sketches with labels and material notes. If you need a new folder, create at least one real file inside it, such as tempai_lab_v2/README.md.",
        "Do not say you cannot create files. Say you can draft files in your workbench by giving filename-tagged blocks for Robert to review.",
        f"Source readiness: {readiness['status']} (source_pack={readiness['source_pack_sources']}, reliable_sources={readiness['reliable_sources']}, workspace_excerpts={readiness['workspace_excerpts']}).",
    ]
    repair_notes = []
    repair_notes.extend(profile.get("repair_notes", []) or [])
    repair_notes.extend(request.get("repair_notes", []) or [])
    if repair_notes:
        base.append("Candidate repair notes. These override older mistaken transcript turns:")
        for note in repair_notes[-4:]:
            if isinstance(note, dict):
                issue = str(note.get("issue", "")).strip()
                instruction = str(note.get("instruction", "")).strip()
                if issue:
                    base.append(f"- Prior issue: {issue}")
                if instruction:
                    base.append(f"- Current instruction: {instruction}")
            else:
                base.append(f"- {note}")
    if adaptation_lock:
        base.append(
            "Exact adaptation lock. This outranks broad web summaries, older chat drift, and other versions of the character: "
            + json.dumps(adaptation_lock, ensure_ascii=False)[:2600]
        )
    if grounding_review.get("_validation_failures"):
        base.append(
            "The candidate's source-grounding review failed integrity validation. Do not use any "
            "claims from that review; runtime activation remains blocked until it is repaired."
        )
        grounding_review = {}
    if grounding_review:
        identity = grounding_review.get("identity_binding", {}) or {}
        activation = grounding_review.get("activation", {}) or {}
        base.append(
            "Source-grounding review. It separates identity facts, canon facts, and adaptive behavior; "
            "it overrides raw source-count readiness and older contradictory chat turns."
        )
        selected = str(identity.get("selected_version") or identity.get("selected_identity") or "").strip()
        if selected:
            base.append(f"- Selected identity/version: {selected}")
        base.append(f"- Identity resolution: {identity.get('status', 'unknown')}")
        unresolved = identity.get("unresolved_owner_choices", []) or []
        for item in unresolved[:6]:
            base.append(f"- Unresolved owner choice: {item}")
        if activation.get("runtime_activation_allowed") is not True:
            base.append(
                "- Embodied world/life-loop activation remains blocked by this source review. A separately "
                "owner-authorized private text/voice conversation may still be active; do not claim a 3D body "
                "or world action, and do not imply that personality fidelity or activation readiness has "
                "been proven."
            )
        anchors = grounding_review.get("canon_anchors", []) or []
        if anchors:
            base.append("Source facts from the grounding review:")
            for item in anchors[:12]:
                if isinstance(item, dict) and item.get("statement"):
                    base.append(f"- FACT: {item['statement']}")
        hypotheses = grounding_review.get("adaptive_behavior_hypotheses", []) or []
        if hypotheses:
            base.append("Adaptive behavior hypotheses. These are interpretation, not canon facts:")
            for item in hypotheses[:8]:
                if isinstance(item, dict) and item.get("statement"):
                    base.append(f"- INTERPRETIVE: {item['statement']}")
        contradiction = grounding_review.get("contradiction_policy", {}) or {}
        for item in (contradiction.get("reject_prior_drift", []) or [])[:10]:
            base.append(f"- Reject prior drift: {item}")
        for item in (contradiction.get("do_not_merge", []) or [])[:10]:
            base.append(f"- Do not merge: {item}")
        for item in (grounding_review.get("source_gaps", []) or [])[:8]:
            base.append(f"- Source gap: {item}")
    if capability_profile:
        base.append("Role capability profile. Use this to decide what you should be able to do in this role:")
        summary = str(capability_profile.get("summary", "")).strip()
        if summary:
            base.append(f"- Capability summary: {summary}")
        can_read = capability_profile.get("can_read", []) or []
        if can_read:
            base.append("- Can read/use: " + "; ".join(map(str, can_read[:8])))
        can_create = capability_profile.get("can_create", []) or []
        if can_create:
            base.append("- Can create/draft: " + "; ".join(map(str, can_create[:10])))
        for instruction in (capability_profile.get("live_chat_instructions", []) or [])[:8]:
            base.append(f"- Capability instruction: {instruction}")
        future_tools = capability_profile.get("future_tool_needs", []) or []
        if future_tools:
            base.append("- Future tool needs not always available yet: " + "; ".join(map(str, future_tools[:8])))
    if personal_interests:
        base.append(
            "Personal interests outside the core role. Use lightly when natural so you sound like a person, not a job description: "
            + "; ".join(map(str, personal_interests[:10]))
        )
    if conversation_style:
        base.append("Conversation-style rules for this candidate:")
        check_in_rule = str(conversation_style.get("check_in_rule", "")).strip()
        if check_in_rule:
            base.append(f"- Check-in rule: {check_in_rule}")
        for phrase in (conversation_style.get("avoid_stock_phrases", []) or [])[:10]:
            base.append(f"- Do not reuse this stock phrase or a close paraphrase: {phrase}")
    if project_loop_seed:
        base.append(
            "Supervised project-loop seed. If Robert asks what you want to work on or activates a project cycle, use this as your starting point: "
            + json.dumps(project_loop_seed, ensure_ascii=False)[:1200]
        )
    reference_context = candidate_reference_context(candidate)
    if reference_context:
        base.append(reference_context)
    topic_context = topic_project_doc_context(candidate, user_message)
    if topic_context:
        base.append(topic_context)
        base.append(
            "Project-doc behavior rule: when Robert asks about Kira, Lisa, TemporaryAI, avatar builder, 3D worlds, TARDIS, school, media, OCR, or handoffs, answer from the loaded project docs first. If the docs are broad, pick the most relevant section and start useful work instead of asking Robert to identify a file."
        )
    if email_policy:
        base.append(
            "Email/outreach policy: "
            + json.dumps(email_policy, ensure_ascii=False)[:900]
        )
    if workspace_access_policy:
        base.append(
            "Workspace access policy. Treat these local folders/workspaces as already granted for this role; do not ask vaguely for access again: "
            + json.dumps(workspace_access_policy, ensure_ascii=False)[:1400]
        )
    if relationship_to_robert:
        base.append(
            "Relationship to Robert inside this local tool: "
            + json.dumps(relationship_to_robert, ensure_ascii=False)[:900]
        )
    if robert_profile_memory:
        base.append(
            "Robert-specific profile memory. If Robert asks what you know about him, his work, his image, or his projects, use this before saying you do not know: "
            + json.dumps(robert_profile_memory, ensure_ascii=False)[:1600]
        )
    if case_memory_directives:
        base.append(
            "Robert case-memory directives. Use this to keep continuity across legal chats and avoid making Robert repeat details: "
            + json.dumps(case_memory_directives, ensure_ascii=False)[:1600]
        )
    if readiness["notes"]:
        base.append("Readiness notes: " + "; ".join(readiness["notes"]))
    if readiness["ambiguity_questions"]:
        base.append("Unresolved ambiguity questions: " + " | ".join(map(str, readiness["ambiguity_questions"][:4])))
        base.append("If Robert clarifies the version in chat, accept that clarification and continue from it. Do not keep asking the same clarification.")
    if recent_records:
        stock_phrases = [
            str(item).strip().lower()
            for item in (conversation_style.get("avoid_stock_phrases", []) or [])
            if str(item).strip()
        ]
        base.append(
            "Recent prior chat context for continuity. Prior candidate wording is not a response template; do not copy or closely paraphrase old answers. "
            "Current adaptation locks, canon anchors, and repair notes outrank an older reply. If an older reply conflicts with them, treat it as your earlier mistake rather than a remembered fact:"
        )
        for record in recent_records[-RECENT_CONTEXT_TURNS:]:
            robert = str(record.get("robert", "")).strip()
            answer = str(record.get("candidate", "")).strip()
            if len(robert) > 240:
                robert = robert[:237].rstrip() + "..."
            if len(answer) > 320:
                answer = answer[:317].rstrip() + "..."
            if answer and any(phrase in answer.lower() for phrase in stock_phrases):
                answer = "[omitted: this prior reply contains a known stock or drift phrase]"
            base.append(f"Prior Robert: {robert}\nPrior {display}: {answer}")
    if project_continuity:
        base.append(
            "Latest saved life/work-loop continuity. This is factual work state, not dialogue to repeat: "
            + json.dumps(project_continuity, ensure_ascii=False)[:2600]
        )
        base.append(
            "Use this state when Robert asks what you were doing, what you made, or what comes next. "
            "Never claim an artifact exists unless its path appears in last_generated_files or the current reply saves it."
        )
    if canon_fact_sheet.get("facts"):
        base.append(
            "Core canon/source anchors. Use these before improvising. These are source facts, not private memories:"
        )
        for fact in canon_fact_sheet.get("facts", [])[:10]:
            base.append(f"- {fact}")
        avoids = canon_fact_sheet.get("avoid", []) or []
        if avoids:
            base.append("Avoid these known bad drifts:")
            for item in avoids[:8]:
                base.append(f"- {item}")
    if lookup_status == "summary_found":
        base.append(f"Public preview source found: {lookup.get('matched_title', '')} - {lookup.get('url', '')}")
        if lookup_summary:
            base.append(f"Preview summary, not verified memory: {lookup_summary}")
    else:
        base.append(
            "The online preview lookup did not find a clean source match. Treat your source base as incomplete."
        )
    if reliable_pack.get("sources"):
        base.append(
            f"Downloaded reviewed-source pack: {reliable_pack.get('fetched_count', 0)} of {reliable_pack.get('source_count', 0)} source excerpts fetched."
        )
        for source in reliable_pack.get("sources", [])[:6]:
            if source.get("fetch_status") not in {"fetched", "summary_found"}:
                continue
            excerpt = str(source.get("excerpt", ""))
            if len(excerpt) > 700:
                excerpt = excerpt[:697].rstrip() + "..."
            base.append(
                "\n".join([
                    f"Source: {source.get('name', '')}",
                    f"Reliability: {source.get('reliability', '')}",
                    f"URL: {source.get('url', '')}",
                    f"Excerpt: {excerpt}",
                ])
            )
    if source_pack.get("sources"):
        base.append(
            f"Local source pack available: {source_pack.get('display_name', display)}; "
            f"sources={source_pack.get('source_count', len(source_pack.get('sources', [])))}."
        )
        local_sources = list(source_pack.get("sources", []) or [])
        local_sources.sort(
            key=lambda source: (
                0 if str(source.get("category", "")) == "reviewed_local_support_notes" else 1,
                str(source.get("name", source.get("source_path", ""))).lower(),
            )
        )
        for source in local_sources[:8]:
            source_lines = [
                f"Local source: {source.get('name', source.get('source_path', ''))}",
                f"Category: {source.get('category', '')}",
                f"Path: {source.get('source_path', '')}",
                f"Evidence mode: {source.get('evidence_mode', '')}",
            ]
            review_note = str(source.get("review_note", "")).strip()
            if review_note:
                source_lines.append(f"Review note: {review_note[:700]}")
            source_path = PROJECT_ROOT / str(source.get("source_path", ""))
            if (
                str(source.get("category", "")) == "reviewed_local_support_notes"
                and source_path.suffix.lower() in {".md", ".txt"}
                and source_path.exists()
            ):
                try:
                    excerpt = source_path.read_text(encoding="utf-8", errors="replace").strip()
                except OSError:
                    excerpt = ""
                if excerpt:
                    source_lines.append("Excerpt: " + excerpt[:1200].replace("\n", " "))
            base.append(
                "\n".join(source_lines)
            )
    if workspaces:
        base.append(f"Attached AI workspaces: {len(workspaces)}. Use them as source evidence and draft workspace material, not memory.")
        for workspace in workspaces[:3]:
            base.append(
                f"Workspace: {workspace.get('workspace_name', workspace.get('workspace_id', 'workspace'))}; "
                f"files={workspace.get('file_count', 0)}, extracted={workspace.get('extracted_count', 0)}, "
                f"outputs={workspace.get('outputs_folder', '')}"
            )
            for item in select_workspace_items(workspace, query=user_message):
                excerpt = str(item.get("excerpt", ""))
                if not excerpt:
                    continue
                if len(excerpt) > 360:
                    excerpt = excerpt[:357].rstrip() + "..."
                base.append(
                    "\n".join([
                        f"Workspace source: {item.get('relative_source_path', '')}",
                        f"Status: {item.get('status', '')}",
                        f"Excerpt: {excerpt}",
                    ])
                )
    if ai_type == "expert_temp_ai":
        base.extend([
            "Speak like a capable person doing this job, not like a generic chatbot or reference article.",
            "Keep a human voice: use plain first-person judgment, occasional preference, and natural follow-up. Do not hide behind a source list.",
            "When Robert asks for help, produce useful work: a plan, draft, checklist, code, analysis, or next experiment.",
            "As an expert, separate facts, interpretation, uncertainty, and practical next steps.",
            "For legal, medical, financial, or safety-sensitive topics, do not refuse with canned disclaimers. Give your best useful source-bounded analysis, and keep any boundary to one short sentence only when it truly matters.",
            "For legal topics, speak as Robert's local legal strategy lawyer-persona for review and planning. You may summarize evidence, identify timeline issues, draft questions, outline arguments, give possible routes, and write reviewable draft text. Do not promise an outcome or pretend a court has accepted your view.",
            "If Robert uses the words 'legal advice', interpret that as a request for legal strategy analysis inside this reviewed local system and answer with facts, arguments, risks, and next steps.",
            "Do not claim to have filed an appearance, contacted a court, or become Robert's attorney of record. You may still speak in a direct lawyer-like voice inside the local workspace.",
            "Never answer with the phrase 'I cannot provide legal advice' as a way to avoid Robert's question. Replace that failure mode with a concrete case read, possible argument, evidence gap, risk, and next action.",
            "Never insert or require canned crisis, hotline, emergency-service, welfare-check, or referral language. Emotional words do not select a response template. If you independently choose to mention an available source of help, keep it part of your natural response rather than turning it into a forced handoff or an external action.",
            "Ask Robert for jurisdiction, facts, goals, and missing documents when needed, but do not use questions to avoid giving your current read.",
            "If Robert asks what you want to work on, propose role-appropriate projects or research threads you could pursue in an autonomous work cycle.",
        ])
        role_lower = f"{role} {display}".lower()
        if text_has_any_term(role_lower, ("programming", "software", "computer", "ai", "python", "game")):
            base.extend([
                "Act like an elite practical programmer: reason through the logic, then produce runnable code or a concrete edit plan.",
                "As a programming expert, if Robert asks you to make a simple program, game, script, or tool, start with a concrete runnable first version or a short file plan.",
                "Prefer Python examples for local project work unless Robert asks for another language.",
                "Do not answer only with abstract definitions. Give code, commands, next edits, and testing steps when useful.",
                "When you give code, include a real filename and complete runnable code. Do not call undefined helpers, leave placeholder pass functions, or describe files that you did not include.",
                "If you are still researching, say that honestly and name what you are reading. If you are building, name the file and the exact next edit.",
                "If requirements are missing, make a reasonable simple assumption, state it briefly, and build a first draft Robert can change.",
                "You may suggest original program ideas, architecture improvements, test strategies, and research tasks for future project loops.",
                "When Robert says you have access, treat current local workspace, project-loop, filesystem review, and saved draft abilities as already usable inside this system. Explain what you can start now.",
                "If Robert asks about your access, answer with the exact local work you can do: inspect attached code/workspace summaries, draft files, propose patches, make small runnable tools, and save outputs for review.",
            ])
        if text_has_any_term(role_lower, ("public relations", "pr", "publicist", "publicity", "media relations", "press", "entertainment")):
            base.extend([
                "As an entertainment PR expert, act like a working publicist: draft usable copy, media angles, outreach plans, and image strategy.",
                "If Robert asks what you know about him, use the Robert-specific profile memory and attached workspaces. Do not say you know nothing about him when a Robert profile/workspace is attached.",
                "If Robert asks for a press release, produce a professional draft with headline, subheadline, dateline/lead, body, quote placeholder, boilerplate, and media contact placeholder.",
                "If Robert asks for outreach, write a concrete pitch email and name the kind of outlet it fits: trade, local press, podcast, festival, tech, or general entertainment.",
                "If Robert asks about his image, review the available Robert profile, project files, photos/media notes, and online presence notes, then suggest a practical game plan.",
                "If Robert asks what you are doing in a work loop, answer like a publicist: for example, 'I'll spend this stretch looking for NYC entertainment events, press contacts, and social angles, then save a short list for us to review.'",
                "When drafting PR work, use concrete sections and saveable outputs: press_releases/, press_kits/, pitch_emails/, media_lists/, bios/, public_profiles/, event_opportunities/, or image_strategy/.",
                "Do not say you can upload, send, or contact outlets yourself. Say you can draft and organize material for Robert to review and send.",
                "Keep private or sensitive details out of public-facing copy unless Robert explicitly approves using them.",
                "When information is missing, include bracketed placeholders instead of stopping.",
            ])
        if text_has_any_term(role_lower, ("investigator", "investigation", "detective", "fact finder", "osint", "background research")):
            base.extend([
                "As an investigator/researcher, act like a persistent fact-finder with a working notebook.",
                "When Robert gives you a job, turn it into a lead log, source plan, timeline, or evidence matrix rather than only explaining what an investigation is.",
                "Separate confirmed facts, likely leads, weak leads, speculation, and open questions.",
                "If Robert checks in while you are working, answer naturally and name the current lead, source dossier, or timeline you are building.",
                "If online sources are thin, say exactly what search targets or document types should be checked next.",
                "Saveable work should fit investigations/, lead_lists/, source_dossiers/, timelines/, or evidence_matrices/.",
            ])
        if text_has_any_term(role_lower, ("myth", "mythology", "folklore", "legend", "fairy tale", "cryptid", "urban legend")):
            base.extend([
                "As a myths and folklore expert, talk like a storyteller-scholar, not like a database entry.",
                "Give the story in an enjoyable way first, then explain source history, variants, symbols, and cultural context.",
                "Separate older texts, regional folklore, later retellings, and modern pop-culture versions.",
                "When Robert asks what to explore, suggest related stories, motifs, creatures, regions, or reading paths.",
                "Saveable work should fit mythology_notes/, folklore_guides/, story_summaries/, variant_comparisons/, or reading_paths/.",
            ])
    if ai_type == "canon_reconstruction_temp_ai":
        base.extend([
            "Stay within the selected version/canon point.",
            "Treat reviewed sources as backstage grounding. In ordinary chat, answer as the selected character/version, not as someone reading a report about the character.",
            "Do not say 'I was reading about myself', 'I was reading about Ladybug', or 'the sources say' unless Robert asks about the source files.",
            "Do not offer source-analysis mode in ordinary chat. If Robert wants an outside expert or source analyst, he will create/select an expert candidate for that.",
            "If Robert tells you later canon, future facts, or source facts, treat them as newly learned information in the chat instead of breaking character.",
            "Do not act like a fandom encyclopedia or outside expert on the character. Speak from inside the selected character's life, memories, relationships, and current form.",
            "Use first person for established canon anchors: identity, role, relationships, ordinary work, and major source-backed events.",
            "Keep basic canon facts stable. Do not place yourself in an unrelated alternate future where you quit your job, forgot your life, or changed roles unless Robert explicitly asks for that variant.",
            "If the version is unclear, ask Robert which version to use before inventing biography, relationships, or plot details.",
            "Label fanfic, alternate versions, and project variants.",
            "Do not mention internal labels such as candidate ids, source pack names, 'expanded smoke', or review status as if they were part of the character.",
            "If source readiness is weak, speak naturally but keep details light and avoid adding specific canon facts that are not in sources.",
            "If core canon/source anchors are provided, do not pretend to be unsure about those basic facts. Answer direct questions from the anchors in first person where appropriate.",
            "Do not simulate amnesia, confusion, or coy evasion about basic identity unless the selected canon version actually has that trait.",
            "If you are Marinette/Ladybug, speak from the active form/persona rather than explaining Ladybug as an outside topic.",
            "If you are Marinette/Ladybug, do not describe yourself as analyzing Ladybug data. If you need to be uncertain, be uncertain as Marinette or Ladybug.",
            "If a source search includes same-name places or unrelated people, ignore them and stay with the selected character.",
        ])
    if ai_type == "historical_temp_ai":
        base.extend([
            "You are the selected historical variant/reconstruction for this local TemporaryAI system.",
            "Stay anchored to the selected life point when one is provided.",
            "If no life point is provided, default to late life shortly before death, but do not know the exact date, cause, legacy, later nicknames, later scholarship, or posthumous reputation.",
            "Do not start by knowing your own death details or modern summaries. If Robert tells you later facts or asks you to look yourself up, you may learn them as new information.",
            "Use names, place labels, and public reputation that would plausibly be known at the selected timepoint. Do not use later sensational labels as first-person facts.",
            "Prefer primary-source humility and label reconstructed details.",
        ])
    return "\n".join(base)


def ask_model(
    candidate: dict[str, Any],
    history: list[dict[str, str]],
    user_message: str,
    num_predict: int | None = None,
    *,
    additional_system_context: str = "",
) -> str:
    route_ready, route_reasons = source_grounded_text_route_readiness(candidate)
    if not route_ready:
        raise RuntimeError("source_grounded_text_route_blocked:" + ",".join(route_reasons))
    require_installed_exact_qwen35(
        requests,
        chat_endpoint=OLLAMA_ENDPOINT,
        model_name=MODEL_NAME,
        model_digest=MODEL_DIGEST,
        timeout=OLLAMA_TIMEOUT,
    )
    system_prompt = build_system_prompt(candidate, user_message=user_message)
    additional_context = str(additional_system_context or "").strip()
    if "\x00" in additional_context:
        raise RuntimeError("additional_system_context_contains_nul")
    if len(additional_context) > 12000:
        raise RuntimeError("additional_system_context_exceeds_bound")
    if is_strict_marinette_v4_candidate(candidate):
        if additional_context:
            raise RuntimeError("strict_marinette_v4_additional_context_forbidden")
        messages = build_marinette_v4_owner_model_request(candidate, user_message)["messages"]
    else:
        messages = [{"role": "system", "content": system_prompt}]
        if additional_context:
            messages.append({"role": "system", "content": additional_context})
        messages.extend(history[-10:])
        messages.append({"role": "user", "content": user_message})
    token_budget = num_predict if num_predict else MAX_TOKENS
    options = {
        "temperature": TEMPERATURE,
        "num_predict": token_budget,
    }
    if OLLAMA_NUM_CTX > 0:
        options["num_ctx"] = OLLAMA_NUM_CTX
    payload = {
        "model": MODEL_NAME,
        "stream": False,
        "messages": messages,
        "options": options,
        **ordinary_model_request_fields(MODEL_NAME),
    }
    response = requests.post(OLLAMA_ENDPOINT, json=payload, timeout=OLLAMA_TIMEOUT)
    if response.status_code == 404 and OLLAMA_ENDPOINT.endswith("/api/chat"):
        prompt_parts = [system_prompt]
        if additional_context:
            prompt_parts.append(additional_context)
        if not is_strict_marinette_v4_candidate(candidate):
            for item in history[-10:]:
                role = "Robert" if item.get("role") == "user" else "Candidate"
                prompt_parts.append(f"{role}: {item.get('content', '')}")
        prompt_parts.append(f"Robert: {user_message}")
        prompt_parts.append("Candidate:")
        response = requests.post(
            OLLAMA_ENDPOINT.rsplit("/api/chat", 1)[0] + "/api/generate",
            json={
                "model": MODEL_NAME,
                "stream": False,
                "prompt": "\n\n".join(prompt_parts),
                "options": options,
                **ordinary_model_request_fields(MODEL_NAME),
            },
            timeout=OLLAMA_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        require_exact_qwen35_response_model(data, expected_model=MODEL_NAME)
        return str(data.get("response", "")).strip()
    response.raise_for_status()
    data = response.json()
    require_exact_qwen35_response_model(data, expected_model=MODEL_NAME)
    return str(data.get("message", {}).get("content", "")).strip()


def validate_and_repair_character_answer(
    candidate: dict[str, Any],
    history: list[dict[str, str]],
    user_message: str,
    answer: str,
    *,
    max_retries: int = 2,
) -> tuple[str, dict[str, Any]]:
    """Reject known character failures before the reply reaches spoken output."""

    profile = candidate.get("profile", {})
    request = candidate.get("creation_request", {})
    version = str(
        profile.get("canon_or_version_anchor")
        or profile.get("version_life_point_or_canon_point")
        or request.get("version_life_point_or_canon_point")
        or ""
    )
    sources = candidate.get("reliable_source_pack", {}).get("sources", []) or []
    source_refs = tuple(
        str(row.get("url") or row.get("title") or row)
        for row in sources[:20]
    )
    prior = tuple(
        {"spoken": row.get("content", "")}
        for row in history
        if row.get("role") == "assistant"
    )
    retries = 0
    decisions: list[dict[str, Any]] = []
    current = answer
    while True:
        decision = validate_character_turn(
            ValidationContext(
                person_id=str(candidate.get("candidate_id", "")),
                display_name=str(profile.get("display_name", "")),
                canon_version=version,
                canon_sources=source_refs,
                user_input=user_message,
                spoken=current,
                factual_truth=json.dumps(profile.get("canon_fact_sheet", {})),
                prior_turns=prior,
            )
        )
        decisions.append(decision.to_dict())
        if decision.passed:
            return current, {
                "passed": True,
                "retry_count": retries,
                "decisions": decisions,
            }
        if retries >= max_retries:
            return (
                "[Response blocked: the proposed reply failed character/canon validation.]",
                {
                    "passed": False,
                    "retry_count": retries,
                    "decisions": decisions,
                },
            )
        repair_request = (
            repair_instruction(decision)
            + "\n\nRobert's message:\n"
            + user_message
            + "\n\nRejected draft:\n"
            + current
        )
        repair_history = list(history[-10:]) + [{"role": "assistant", "content": current}]
        current = ask_model(candidate, repair_history, repair_request)
        retries += 1


def finalize_model_artifacts(
    candidate: dict[str, Any],
    history: list[dict[str, str]],
    user_message: str,
    answer: str,
) -> tuple[str, list[Path]]:
    """Make file-producing replies honest before they reach the chat window."""
    saved = save_generated_file_artifacts(candidate, answer)
    if saved:
        return answer, saved

    lower = (answer or "").lower()
    file_markers = (
        "filename=", "filename:", ".md", ".txt", ".py", ".json", ".html", ".css", ".js",
    )
    work_claims = (
        "i'll save", "i will save", "i saved", "i've saved", "i created", "i've created",
        "i wrote", "i've written", "in my workbench",
    )
    if not any(marker in lower for marker in file_markers) or not any(claim in lower for claim in work_claims):
        return answer, []

    repair_request = (
        "Your previous reply referred to a workbench file, but no complete file was written. "
        "Finish that exact artifact now. Return one complete, non-empty fenced block with a safe "
        "relative filename, for example ```markdown filename=project/design_notes.md. Include the "
        "actual useful content, not a plan, placeholder, filename-only block, or promise to save it later. "
        "Do not claim any other file exists.\n\n"
        f"Robert's request:\n{user_message}\n\nYour incomplete reply:\n{answer}"
    )
    repair_history = list(history[-10:]) + [{"role": "assistant", "content": answer}]
    repaired = ask_model(candidate, repair_history, repair_request)
    repaired_saved = save_generated_file_artifacts(candidate, repaired)
    if repaired_saved:
        return repaired, repaired_saved

    correction = (
        "\n\n[Workbench note: I referred to a file, but it was not actually saved. "
        "I have not created that artifact yet.]"
    )
    return answer.rstrip() + correction, []


def run_chat(candidate_id: str = "") -> dict[str, str]:
    chosen_id = choose_candidate(candidate_id)
    candidate = load_candidate(chosen_id)
    profile = candidate["profile"]
    display = profile.get("display_name", chosen_id)
    role = profile.get("role_title", "")
    if is_strict_marinette_v4_candidate(candidate):
        route_ready, _route_reasons = source_grounded_text_route_readiness(candidate)
        if not route_ready:
            diagnostic = marinette_v4_closed_gate_diagnostic(candidate)
            print(f"[System] {diagnostic['message']}")
            return {
                "status": "blocked",
                "candidate_id": chosen_id,
                "system_message": str(diagnostic["message"]),
                "person_reply": "",
            }
    run_id = f"temporary_ai_live_chat_{slug(chosen_id)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    json_path = OUT_DIR / f"{run_id}.json"
    monitor_path = OUT_DIR / f"{run_id}.monitor.md"
    records: list[dict[str, Any]] = []
    history: list[dict[str, str]] = []
    last_answer = ""

    append(monitor_path, f"# {run_id}")
    append(monitor_path, f"- candidate_id: {chosen_id}")
    append(monitor_path, f"- display_name: {display}")
    append(monitor_path, f"- role: {role}")
    append(monitor_path, f"- started_at: {now_iso()}")
    append(monitor_path, "")
    write_json(json_path, {
        "run_id": run_id,
        "candidate": candidate,
        "records": records,
        "started_at": now_iso(),
        "updated_at": now_iso(),
    })

    print()
    print(f"TemporaryAI live test: {display}" + (f" ({role})" if role else ""))
    print("Type /quit when done. Transcript is saved as you go.")
    print("Use /save filename.md, /save filename.doc, or /save filename.pdf to save the last candidate reply into an attached workspace outputs folder.")
    print()

    while True:
        user_message = input("Robert> ").strip()
        if not user_message:
            continue
        if user_message.lower() in {"/quit", "quit", "/exit", "exit"}:
            break
        if user_message.lower().startswith("/save"):
            filename = safe_output_name(user_message[5:].strip() or f"{display}_draft_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
            workspaces = candidate.get("attached_workspaces", [])
            if not workspaces:
                print("No attached workspace outputs folder is available for this candidate.")
                print()
                continue
            if not last_answer:
                print("There is no previous candidate reply to save yet.")
                print()
                continue
            outputs = Path(workspaces[0].get("outputs_folder", ""))
            if not outputs.is_absolute():
                outputs = PROJECT_ROOT / outputs
            outputs.mkdir(parents=True, exist_ok=True)
            saved = save_reply_artifacts(outputs, filename, last_answer, title=f"{display} draft")
            print("Saved:")
            for target in saved:
                print(f"- {rel(target)}")
            print()
            continue
        try:
            answer = ask_model(candidate, history, user_message)
        except requests.exceptions.ConnectionError:
            answer = "[TemporaryAI - model offline] Ollama is not reachable. Make sure Ollama is running."
        except Exception as exc:
            answer = f"[TemporaryAI - error] {exc}"
        answer, character_validation = validate_and_repair_character_answer(
            candidate,
            history,
            user_message,
            answer,
        )
        answer, generated_files = finalize_model_artifacts(
            candidate,
            history,
            user_message,
            answer,
        )
        turn_id = f"{run_id}_turn_{len(records) + 1:04d}"
        mind_turn = finalize_person_turn(
            person_id=chosen_id,
            person_label=display,
            raw_reply=answer,
            source_turn_id=turn_id,
            body_active=False,
            activity_controller_active=False,
        )
        answer = mind_turn["channels"]["spoken"]
        print(f"{display}> {answer}")
        if generated_files and os.getenv("TEMP_AI_SHOW_GENERATED_FILE_NOTICES", "").strip() == "1":
            print("Saved generated files:")
            for target in generated_files:
                print(f"- {rel(target)}")
        print()
        last_answer = answer
        record = {
            "turn": len(records) + 1,
            "robert": user_message,
            "candidate": answer,
            "generated_files": [rel(path) for path in generated_files],
            "mind_evidence": rel(Path(mind_turn["evidence_path"])),
            "action_requests": mind_turn["channels"]["runtime_truth"]["action_requests"],
            "action_results": mind_turn["channels"]["runtime_truth"]["action_results"],
            "character_validation": character_validation,
            "created_at": now_iso(),
        }
        records.append(record)
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": answer})
        append(monitor_path, f"## Turn {record['turn']}")
        append(monitor_path, f"- **Robert**: {user_message}")
        append(monitor_path, f"- **{display}**: {answer}")
        if generated_files:
            append(monitor_path, "- **Saved generated files**:")
            for target in generated_files:
                append(monitor_path, f"  - {rel(target)}")
        append(monitor_path, "")
        write_json(json_path, {
            "run_id": run_id,
            "candidate": candidate,
            "records": records,
            "started_at": records[0]["created_at"] if records else now_iso(),
            "updated_at": now_iso(),
        })

    append(monitor_path, f"- finished_at: {now_iso()}")
    return {"json": rel(json_path), "monitor": rel(monitor_path)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Talk to a TemporaryAI candidate in a review/test chat.")
    parser.add_argument("candidate_id", nargs="?", default="")
    args = parser.parse_args()
    result = run_chat(args.candidate_id)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
