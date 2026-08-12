"""Run one supervised TemporaryAI project/research cycle.

This is not permanent autonomy. It lets one reviewed candidate choose or work on
one small role-shaped task, then saves the result for Robert/Kira/Lisa review.
"""

from __future__ import annotations

import argparse
import ast
import builtins
import importlib.util
import html
import json
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote_plus, unquote, urlparse
from urllib.request import Request, urlopen

import requests

# Running a script by its full path makes Python put only the tools directory on
# sys.path. Add the repository root before importing shared Core modules so the
# worker behaves the same from the GUI, a shortcut, or a command prompt.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from temporary_ai_live_chat import (
    MAX_TOKENS,
    MODEL_DIGEST,
    MODEL_NAME,
    OLLAMA_ENDPOINT,
    OLLAMA_NUM_CTX,
    OLLAMA_TIMEOUT,
    TEMPERATURE,
    PROJECT_ROOT,
    ask_model,
    candidate_reference_context,
    topic_project_doc_context,
    choose_candidate,
    load_candidate,
    rel,
    safe_output_name,
    save_reply_artifacts,
    slug,
    write_json,
)
from Core.avatar_activity_state import write_avatar_activity_state
from Core.model_request_policy import ordinary_model_request_fields
from Core.qwen35_runtime_identity import (
    require_exact_qwen35_response_model,
    require_installed_exact_qwen35,
)


RUN_ROOT = PROJECT_ROOT / "Data" / "personhood_evaluations" / "temporary_ai_project_loops"
MEDIA_LIBRARY_INDEX = PROJECT_ROOT / "Data" / "indexes" / "media_library_index.json"
_MEDIA_LIBRARY_CACHE: list[dict[str, Any]] | None = None
SEARCH_TIMEOUT_SECONDS = 12
MAX_RESEARCH_RESULTS = 5
GENERATED_FILE_EXTENSIONS = {
    ".bat",
    ".cmd",
    ".css",
    ".csv",
    ".doc",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".md",
    ".ps1",
    ".py",
    ".rtf",
    ".svg",
    ".txt",
    ".yaml",
    ".yml",
}
KNOWN_LOCAL_MODULES = {
    "temporary_ai_live_chat",
    "temporary_ai_project_loop",
}
FORBIDDEN_FAKE_PATH_TOKENS = {
    "candidate_profiles_flat",
    "candidateprofilesflat",
    "data/candidates",
    "datacandidates",
    "roles/",
    "role/",
    "systemdocs",
    "toolsource",
}
PR_OUTPUT_FOLDERS = {
    "bios",
    "event_opportunities",
    "image_strategy",
    "media_lists",
    "pitch_emails",
    "press_kits",
    "press_releases",
    "public_profiles",
}
INVESTIGATION_OUTPUT_FOLDERS = {
    "evidence_matrices",
    "investigations",
    "lead_lists",
    "source_dossiers",
    "timelines",
}
MYTH_FOLKLORE_OUTPUT_FOLDERS = {
    "folklore_guides",
    "mythology_notes",
    "reading_paths",
    "story_summaries",
    "variant_comparisons",
}
CHARACTER_OUTPUT_FOLDERS = {
    "personal_projects",
    "sketches",
}
ROLE_OUTPUT_FOLDERS = (
    PR_OUTPUT_FOLDERS
    | INVESTIGATION_OUTPUT_FOLDERS
    | MYTH_FOLKLORE_OUTPUT_FOLDERS
    | CHARACTER_OUTPUT_FOLDERS
)
CODE_BLOCK_LANGUAGE_EXTENSIONS = {
    "bat": {".bat", ".cmd"},
    "cmd": {".bat", ".cmd"},
    "css": {".css"},
    "html": {".html"},
    "ini": {".ini"},
    "javascript": {".js"},
    "js": {".js"},
    "json": {".json"},
    "markdown": {".md"},
    "md": {".md"},
    "powershell": {".ps1"},
    "ps1": {".ps1"},
    "py": {".py"},
    "python": {".py"},
    "svg": {".svg"},
    "text": {".txt", ".md"},
    "txt": {".txt"},
    "xml": {".svg"},
    "yaml": {".yaml", ".yml"},
    "yml": {".yaml", ".yml"},
}
MIN_USEFUL_ANSWER_WORDS = 35
MIN_USEFUL_ANSWER_ALNUM = 180
MAX_BAD_OUTPUT_STREAK = 3
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
    "text",
    "txt",
    "yaml",
    "yml",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def append(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(text.rstrip() + "\n")


def update_monitor_header_status(path: Path, status: str) -> None:
    if not path.exists():
        return
    lines = path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if line.startswith("- status: "):
            lines[index] = f"- status: {status}"
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return


def candidate_outputs_dir(candidate: dict[str, Any]) -> Path:
    workspaces = candidate.get("attached_workspaces", []) or []
    for workspace in workspaces:
        if not isinstance(workspace, dict):
            continue
        outputs = workspace.get("outputs_folder")
        if outputs:
            path = PROJECT_ROOT / str(outputs)
            path.mkdir(parents=True, exist_ok=True)
            return path
    candidate_id = candidate["candidate_id"]
    path = PROJECT_ROOT / "TemporaryAI" / "candidates" / candidate_id / "workbench" / "outputs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def candidate_role_text(candidate: dict[str, Any]) -> str:
    profile = candidate.get("profile", {}) or {}
    capability = profile.get("capability_profile", {}) or {}
    pieces = [
        str(profile.get("display_name", "")),
        str(profile.get("role_title", "")),
        str(profile.get("ai_type", "")),
        str(profile.get("ui_category", "")),
        json.dumps(capability, ensure_ascii=False),
    ]
    return " ".join(pieces).lower()


def candidate_prefers_doc_pdf_outputs(candidate: dict[str, Any]) -> bool:
    text = candidate_role_text(candidate)
    return bool(
        re.search(r"\bpr\b|\bpublic relations\b|\bpublicist\b|\bpublicity\b|\bpress\b|\bmedia relations\b", text)
    )


def candidate_project_state_path(candidate: dict[str, Any]) -> Path:
    path = candidate_outputs_dir(candidate) / "project_state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def read_json_file(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def compact_project_state_context(candidate: dict[str, Any], char_limit: int = 1800) -> str:
    state = read_json_file(candidate_project_state_path(candidate), default={}) or {}
    if not state:
        return ""
    last_status = str(state.get("last_status") or "")
    generated_files = [
        path for path in (state.get("last_generated_files") or [])
        if isinstance(path, str) and (PROJECT_ROOT / path).exists()
    ]
    if candidate_prefers_doc_pdf_outputs(candidate):
        generated_files = [
            path
            for path in generated_files
            if not low_quality_pr_candidate_answer(
                candidate,
                (PROJECT_ROOT / path).read_text(encoding="utf-8", errors="replace")
                if (PROJECT_ROOT / path).suffix.lower() in {".md", ".txt", ".json", ".yaml", ".yml"}
                else "",
            )
        ]
    artifact_paths = [
        path for path in (state.get("last_artifacts") or [])
        if isinstance(path, str) and (PROJECT_ROOT / path).exists()
    ]
    activation_or_test = state.get("activation_or_test_instructions", "")
    if last_status == "model_output_rejected" or not generated_files:
        activation_or_test = ""
    useful = {
        "current_project": state.get("current_project"),
        "stage": state.get("stage"),
        "cycles_completed": state.get("cycles_completed"),
        "last_status": state.get("last_status"),
        "last_cycle_id": state.get("last_cycle_id"),
        "last_artifacts_that_still_exist": artifact_paths[-5:],
        "last_generated_files_that_still_exist": generated_files[-5:],
        "next_step": state.get("next_step"),
        "activation_or_test_instructions": activation_or_test,
    }
    return (
        "Previous project-loop state for continuity. Use this quietly; continue or revise the work instead of starting over:\n"
        + json.dumps(useful, indent=2, ensure_ascii=False)[:char_limit]
    )


def latest_life_loop_record(candidate_id: str, exclude_run_id: str = "") -> dict[str, Any]:
    pattern = f"temporary_ai_life_loop_{slug(candidate_id)}_*.json"
    paths = sorted(RUN_ROOT.glob(pattern), key=lambda path: path.stat().st_mtime, reverse=True)
    for path in paths:
        data = read_json_file(path, default={}) or {}
        if exclude_run_id and data.get("run_id") == exclude_run_id:
            continue
        if data.get("candidate_id") != candidate_id:
            continue
        data["_record_path"] = rel(path)
        monitor = path.with_suffix(".monitor.md")
        if monitor.exists():
            data["_monitor_path"] = rel(monitor)
        return data
    return {}


def recent_candidate_workbench_artifacts(candidate: dict[str, Any], limit: int = 10) -> list[str]:
    outputs = candidate_outputs_dir(candidate)
    priority = [
        outputs / "program_drafts" / "source_generator.py",
        outputs / "source_generator" / "temporary_ai_source_plan.md",
        outputs / "source_generator" / "temporary_ai_source_plan.json",
        outputs / "tempai_lab_v2" / "design_docs" / "design_document.md",
        outputs / "tempai_lab_v2" / "profile_creation" / "profile_creation.py",
        outputs / "tempai_lab_v2" / "knowledge_graph_management" / "knowledge_graph_management.py",
    ]
    roots = [
        outputs / "program_drafts",
        outputs / "design_docs",
        outputs / "test_drafts",
        outputs / "schemas",
        outputs / "source_generator",
        outputs / "tempai_lab_v2",
    ]
    files: list[Path] = []
    for root in roots:
        if root.exists():
            files.extend(path for path in root.rglob("*") if path.is_file())
    useful_suffixes = {".py", ".md", ".json", ".txt", ".yaml", ".yml"}
    files = [
        path for path in files
        if path.suffix.lower() in useful_suffixes and path.stat().st_size > 20
    ]
    if candidate_prefers_doc_pdf_outputs(candidate):
        files = [
            path
            for path in files
            if not low_quality_pr_candidate_answer(
                candidate,
                path.read_text(encoding="utf-8", errors="replace")
                if path.suffix.lower() in {".md", ".txt", ".json", ".yaml", ".yml"}
                else "",
            )
        ]
    files.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    ordered: list[Path] = []
    for path in priority:
        if path.exists() and path.stat().st_size > 20:
            ordered.append(path)
    for path in files:
        if path not in ordered:
            ordered.append(path)
    return [rel(path) for path in ordered[:limit]]


def candidate_resume_brief(candidate: dict[str, Any], current_run_id: str = "", char_limit: int = 3500) -> str:
    """Build a restart handoff so a new loop continues the last real work."""
    candidate_id = candidate["candidate_id"]
    state = read_json_file(candidate_project_state_path(candidate), default={}) or {}
    latest_loop = latest_life_loop_record(candidate_id, exclude_run_id=current_run_id)
    accepted_cycles: list[dict[str, Any]] = []
    rejected_count = 0
    for cycle in latest_loop.get("cycles", []) if isinstance(latest_loop.get("cycles"), list) else []:
        if cycle.get("status") == "model_output_rejected":
            rejected_count += 1
            continue
        accepted_cycles.append(cycle)

    real_artifacts: list[str] = []
    for value in recent_candidate_workbench_artifacts(candidate, limit=12):
        if value not in real_artifacts:
            real_artifacts.append(value)
    for source in [state] + accepted_cycles[-4:]:
        for key in ("last_generated_files", "last_artifacts", "artifacts"):
            for value in source.get(key, []) or []:
                if not isinstance(value, str):
                    continue
                value_path = PROJECT_ROOT / value
                if (
                    candidate_prefers_doc_pdf_outputs(candidate)
                    and value_path.exists()
                    and value_path.suffix.lower() in {".md", ".txt", ".json", ".yaml", ".yml"}
                    and low_quality_pr_candidate_answer(
                        candidate,
                        value_path.read_text(encoding="utf-8", errors="replace"),
                    )
                ):
                    continue
                if value not in real_artifacts and (PROJECT_ROOT / value).exists():
                    real_artifacts.append(value)

    latest_accepted = accepted_cycles[-1] if accepted_cycles else {}
    last_status = state.get("last_status") or latest_loop.get("status") or ""
    next_step = str(state.get("next_step") or "").strip()
    if last_status == "model_output_rejected":
        next_step = (
            "Resume from the last real artifact, not the rejected output. "
            "Make one small concrete improvement or write an honest progress note."
        )

    brief = {
        "purpose": "Restart handoff. Continue from here after Robert closes/reopens the UI.",
        "current_project": state.get("current_project") or latest_loop.get("task") or "TemporaryAI workbench project",
        "previous_life_loop": {
            "run_id": latest_loop.get("run_id"),
            "status": latest_loop.get("status"),
            "cycles_saved": len(latest_loop.get("cycles", []) or []),
            "record": latest_loop.get("_record_path"),
            "monitor": latest_loop.get("_monitor_path"),
            "rejected_cycles_in_that_run": rejected_count,
        },
        "last_accepted_cycle": {
            "run_id": latest_accepted.get("run_id"),
            "status": latest_accepted.get("status"),
            "stage": latest_accepted.get("stage"),
            "monitor": latest_accepted.get("monitor"),
        },
        "real_artifacts_to_continue": real_artifacts[:8],
        "next_step": next_step,
        "rules": [
            "Do not ask Robert to repeat the project context.",
            "Do not restart from scratch unless Robert asks.",
            "Open/review the real artifacts listed here before proposing new files.",
            "If the last output was rejected, continue from the last real artifact and avoid the rejected pattern.",
            "Only say a file exists if it is in the artifact list or you include a complete filename-tagged block for it.",
            "When Robert says make it/build it/create it, continue the real artifact and provide a saved file or verified test command instead of another proposal.",
            "If the requested project is complete and the loop is still running, pick the next useful Kira/TemporaryAI/avatar/world task from the attached docs and begin one concrete artifact.",
        ],
    }
    return (
        "Resume brief for this TemporaryAI work session:\n"
        + json.dumps(brief, indent=2, ensure_ascii=False)[:char_limit]
    )


def safe_relative_file_path(value: str) -> Path | None:
    """Return a review-safe relative file path for candidate-generated files."""
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
    """Reject blocks that are likely nested/unfinished or prose saved as code."""
    text = code or ""
    lower = text.lower()
    if re.search(r"\*\*[^*\n]+?\.(?:bat|cmd|css|csv|html|ini|js|json|md|ps1|py|svg|txt|ya?ml)\*\*", text, flags=re.I):
        return True
    if "```" in text:
        return True
    if "[insert " in lower or "[todo" in lower:
        return True
    if re.search(r"\bto\s*do\b|\btodo\b", lower):
        return True
    if re.search(r"\b(add|insert|implement)\s+[^.\n]{0,80}\s+here\b", lower):
        return True
    if re.search(r"\bplaceholder\b|\bstub\b|\bnot implemented\b", lower):
        return True
    if rel_path.suffix.lower() in {".py", ".json", ".yaml", ".yml"}:
        if re.search(r"['\"]\s*\.\.\.\s*['\"]", text):
            return True
        if re.search(r"\b(?:id|candidate_id)\s*[:=]\s*['\"]12345['\"]", text, flags=re.I):
            return True
    if rel_path.suffix.lower() == ".py":
        if re.search(r"(?m)^\s*\.\.\.\s*(?:#.*)?$", text):
            return True
        pass_lines = re.findall(r"(?m)^\s*pass\s*(?:#.*)?$", text)
        func_defs = re.findall(r"(?m)^\s*def\s+\w+\s*\(", text)
        if pass_lines and len(pass_lines) >= max(1, len(func_defs) // 2):
            return True
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


def code_block_language_warning(info: str, rel_path: Path) -> str | None:
    """Warn when a fenced code language contradicts the named output file."""
    lang = ((info or "").strip().split() or [""])[0].lower()
    if not lang or lang not in CODE_BLOCK_LANGUAGE_EXTENSIONS:
        return None
    allowed = CODE_BLOCK_LANGUAGE_EXTENSIONS[lang]
    if rel_path.suffix.lower() not in allowed:
        return (
            f"{rel_path.as_posix()} has a `{lang}` code fence but the file extension is "
            f"`{rel_path.suffix}`"
        )
    return None


def generated_block_has_unsafe_project_targets(rel_path: Path, code: str) -> bool:
    """Reject drafts that pretend fake/live project paths are runnable targets."""
    path_text = rel_path.as_posix().lower().replace("_", "")
    text = (code or "").lower().replace("\\", "/")
    compact = re.sub(r"[^a-z0-9./]+", "", text)
    allowed_snapshot_markers = (
        "tempai_lab_20260611/candidate_profiles_flat",
        "tempai_lab_20260611/system_docs",
        "tempai_lab_20260611/tool_source",
    )
    blocked_path_tokens = [
        "toolsource",
        "systemdocs",
        "candidateprofilesflat",
        "temporary_ai_live_chat.py",
        "temporaryailivechat.py",
        "temporary_ai_project_loop.py",
        "temporaryaiprojectloop.py",
        "data/candidates/",
        "datacandidates/",
        "roles/",
        "role/",
    ]
    if any(token.replace("_", "") in path_text for token in blocked_path_tokens):
        return True
    snapshot_text_allowed = any(marker in text for marker in allowed_snapshot_markers) or (
        "tempai_lab_20260611" in text
        and any(token in text for token in ("tool_source", "system_docs", "candidate_profiles_flat"))
    )
    def blocked_token_present(token: str) -> bool:
        if token in {"toolsource", "systemdocs", "candidateprofilesflat"} and snapshot_text_allowed:
            return False
        if token in {"tool_source", "system_docs", "candidate_profiles_flat"} and snapshot_text_allowed:
            return False
        return token in text or token.replace("_", "") in compact

    for token in ("tool_source", "system_docs", "candidate_profiles_flat"):
        if token in text and not snapshot_text_allowed:
            return True
    if rel_path.suffix.lower() == ".py" and any(blocked_token_present(token) for token in blocked_path_tokens):
        return True
    if any(blocked_token_present(token) for token in blocked_path_tokens):
        write_patterns = [
            r"\bopen\s*\([^)]*,\s*['\"][wa]",
            r"\.write_text\s*\(",
            r"\.write\s*\(",
            r"os\.makedirs\s*\(",
            r"\.mkdir\s*\(",
            r"shutil\.copy",
        ]
        if any(re.search(pattern, text) for pattern in write_patterns):
            return True
    return False


def import_is_available_or_stdlib(module_name: str) -> bool:
    """Best-effort check for generated Python imports.

    Emily should prefer stdlib code. For workbench-generated runnable scripts,
    third-party imports often become fake progress because Robert cannot run the
    file without extra setup. If a dependency is truly needed, Emily should write
    it as a TODO/install note instead of importing it in the first runnable slice.
    """
    if not module_name:
        return True
    root = module_name.split(".", 1)[0]
    if root in sys.builtin_module_names or root in KNOWN_LOCAL_MODULES:
        return True
    stdlib_names = getattr(sys, "stdlib_module_names", set())
    if root in stdlib_names:
        return True
    return False


def generated_python_quality_warnings(rel_path: Path, code: str) -> list[str]:
    """Return warnings for generated Python that looks non-runnable or fake."""
    if rel_path.suffix.lower() != ".py":
        return []
    warnings: list[str] = []
    text = code or ""
    try:
        compile(text, rel_path.as_posix(), "exec")
    except SyntaxError as exc:
        warnings.append(f"{rel_path.as_posix()} has a Python syntax error: {exc.msg} line {exc.lineno}")
        return warnings
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return warnings

    imports: set[str] = set()
    imported_names: set[str] = set()
    defined_names: set[str] = set(dir(builtins)) | {"__name__", "__file__", "__package__", "__doc__"}
    suspicious_reads: list[str] = []
    suspicious_write_parents: list[str] = []
    top_level_calls: list[str] = []

    def literal_text(node: ast.AST) -> str | None:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        return None

    def path_is_fake_or_missing(path_text: str, *, read_mode: bool) -> bool:
        normalized = path_text.replace("\\", "/").strip()
        if not normalized or "{" in normalized or normalized.startswith(("http://", "https://")):
            return False
        if re.match(r"^[a-zA-Z]:/", normalized):
            candidate_path = Path(normalized)
        else:
            candidate_path = PROJECT_ROOT / normalized
        lower = normalized.lower()
        if lower.startswith(("roles/", "data/candidates/", "candidate_profiles_flat/", "tool_source/")):
            return True
        if read_mode:
            return not candidate_path.exists()
        return not candidate_path.parent.exists()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".", 1)[0]
                imports.add(root)
                imported_names.add(alias.asname or root)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split(".", 1)[0])
            for alias in node.names:
                imported_names.add(alias.asname or alias.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            defined_names.add(node.name)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for arg in [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]:
                    defined_names.add(arg.arg)
                if node.args.vararg:
                    defined_names.add(node.args.vararg.arg)
                if node.args.kwarg:
                    defined_names.add(node.args.kwarg.arg)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            defined_names.add(node.id)
        elif isinstance(node, (ast.ExceptHandler,)):
            if node.name:
                defined_names.add(str(node.name))

    defined_names.update(imported_names)

    undefined_calls: list[str] = []
    undefined_names: list[str] = []
    placeholder_functions: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            body = list(node.body)
            if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant):
                if isinstance(body[0].value.value, str):
                    body = body[1:]
            only_placeholder = bool(body) and all(
                isinstance(stmt, ast.Pass)
                or (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and stmt.value.value is Ellipsis)
                or (
                    isinstance(stmt, ast.Return)
                    and (stmt.value is None or (isinstance(stmt.value, ast.Constant) and stmt.value.value is None))
                )
                for stmt in body
            )
            if not body or only_placeholder:
                placeholder_functions.append(node.name)
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id not in defined_names:
                undefined_calls.append(func.id)
            if isinstance(func, ast.Name) and func.id == "open" and node.args:
                path_text = literal_text(node.args[0])
                mode = literal_text(node.args[1]) if len(node.args) > 1 else "r"
                read_mode = not mode or "r" in mode
                if path_text and path_is_fake_or_missing(path_text, read_mode=read_mode):
                    if read_mode:
                        suspicious_reads.append(path_text)
                    else:
                        suspicious_write_parents.append(path_text)
            elif isinstance(func, ast.Attribute) and func.attr in {"read_text", "write_text", "mkdir"}:
                receiver = func.value
                path_text: str | None = None
                if isinstance(receiver, ast.Call) and isinstance(receiver.func, ast.Name) and receiver.func.id == "Path" and receiver.args:
                    path_text = literal_text(receiver.args[0])
                if path_text:
                    if func.attr == "read_text" and path_is_fake_or_missing(path_text, read_mode=True):
                        suspicious_reads.append(path_text)
                    elif func.attr in {"write_text", "mkdir"} and path_is_fake_or_missing(path_text, read_mode=False):
                        suspicious_write_parents.append(path_text)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            if node.id not in defined_names:
                undefined_names.append(node.id)

    def is_main_guard(stmt: ast.stmt) -> bool:
        if not isinstance(stmt, ast.If):
            return False
        test = stmt.test
        if not isinstance(test, ast.Compare) or len(test.ops) != 1 or len(test.comparators) != 1:
            return False
        if not isinstance(test.ops[0], ast.Eq):
            return False
        left = test.left
        right = test.comparators[0]
        return (
            isinstance(left, ast.Name)
            and left.id == "__name__"
            and isinstance(right, ast.Constant)
            and right.value == "__main__"
        )

    for stmt in tree.body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Import, ast.ImportFrom)):
            continue
        if is_main_guard(stmt):
            continue
        if isinstance(stmt, (ast.Assign, ast.AnnAssign)):
            continue
        for node in ast.walk(stmt):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name):
                    top_level_calls.append(func.id)
                elif isinstance(func, ast.Attribute):
                    top_level_calls.append(func.attr)
                else:
                    top_level_calls.append("call")

    if rel_path.parts and rel_path.parts[0].lower() == "program_drafts":
        if "__main__" not in text:
            warnings.append(
                f"{rel_path.as_posix()} is a program draft but has no __main__ test entrypoint"
            )
        if top_level_calls:
            warnings.append(
                f"{rel_path.as_posix()} has top-level executable calls; put sample usage behind a __main__ guard"
            )
        if placeholder_functions:
            warnings.append(
                f"{rel_path.as_posix()} has unfinished placeholder function(s): {', '.join(placeholder_functions[:5])}"
            )

    if undefined_calls:
        unique_calls = sorted(set(undefined_calls))
        warnings.append(
            f"{rel_path.as_posix()} calls undefined function(s): {', '.join(unique_calls[:8])}"
        )
    if undefined_names:
        unique_names = sorted(set(undefined_names) - set(undefined_calls))
        if unique_names:
            warnings.append(
                f"{rel_path.as_posix()} references undefined name(s): {', '.join(unique_names[:8])}"
            )
    if rel_path.parts and rel_path.parts[0].lower() == "program_drafts":
        if re.search(r"\b(todo|not implemented|placeholder|stub)\b|^\s*#\s*\.\.\.\s*$", text, flags=re.I | re.M):
            warnings.append(f"{rel_path.as_posix()} contains unfinished TODO/placeholder language")

    if re.search(r"\bjson\.", text) and not re.search(r"(?m)^\s*(?:import\s+json|from\s+json\s+import)\b", text):
        warnings.append(f"{rel_path.as_posix()} uses json but does not import json")

    missing_imports = sorted(root for root in imports if not import_is_available_or_stdlib(root))
    if missing_imports:
        warnings.append(f"{rel_path.as_posix()} imports unavailable module(s): {', '.join(missing_imports[:5])}")
    if suspicious_reads:
        warnings.append(f"{rel_path.as_posix()} reads missing/fake path(s): {', '.join(suspicious_reads[:4])}")
    if suspicious_write_parents:
        warnings.append(f"{rel_path.as_posix()} writes to missing/fake parent path(s): {', '.join(suspicious_write_parents[:4])}")
    return warnings


def generated_block_quality_warnings(rel_path: Path, code: str, info: str = "") -> list[str]:
    warnings: list[str] = []
    language_warning = code_block_language_warning(info, rel_path)
    if language_warning:
        warnings.append(language_warning)
    if generated_block_is_malformed(rel_path, code):
        warnings.append(f"{rel_path.as_posix()} is malformed or unfinished")
    if generated_block_has_unsafe_project_targets(rel_path, code):
        warnings.append(f"{rel_path.as_posix()} references fake/live project targets instead of review-safe workbench files")
    if rel_path.suffix.lower() == ".json":
        try:
            json.loads(code)
        except json.JSONDecodeError as exc:
            warnings.append(f"{rel_path.as_posix()} is not valid JSON: {exc.msg} line {exc.lineno}")
    warnings.extend(generated_python_quality_warnings(rel_path, code))
    return warnings


def has_unsafe_project_targets(answer: str) -> bool:
    """Catch unsafe/fake implementation outputs before they count as work."""
    text = (answer or "").lower().replace("\\", "/")
    compact = re.sub(r"[^a-z0-9./]+", "", text)
    blocked_phrases = [
        "copy and paste updated temporary_ai_live_chat.py",
        "copy and paste the updated temporary_ai_live_chat.py",
        "copy and paste updated temporaryailivechat.py",
        "copy and paste the updated temporaryailivechat.py",
        "append to tool_source",
        "append to toolsource",
        "integrate into live chat ui using toolsource",
        "integrate into live chat ui using tool_source",
        "test with example candidate profiles from candidateprofilesflat",
        "test with example candidate profiles from candidate_profiles_flat",
    ]
    if any(phrase in text or phrase.replace("_", "") in compact for phrase in blocked_phrases):
        return True
    if "workbench/toolbox" in text or "workbench\\toolbox" in (answer or "").lower():
        return True
    if "tool_source/" in text and "tempai_lab_20260611/tool_source" not in text:
        return True
    claim_contexts = [
        r"\bwhat i reviewed/worked on\b",
        r"\bwhat i reviewed\b",
        r"\bfiles to change\b",
        r"\bfiles to edit\b",
        r"\bhow robert can test\b",
        r"\bnext step\b",
        r"\bimplement\b",
        r"\bintegrate\b",
        r"\bmodified\b",
        r"\bupdated\b",
        r"\bpatched\b",
    ]
    fake_token_pattern = "|".join(re.escape(token) for token in sorted(FORBIDDEN_FAKE_PATH_TOKENS, key=len, reverse=True))
    for context in claim_contexts:
        if re.search(context + rf".{{0,500}}(?:{fake_token_pattern})", text, flags=re.S):
            return True
    for match in re.finditer(r"```([^\n`]*)\n(.*?)```", answer or "", flags=re.S):
        info, code = match.groups()
        prefix = (answer or "")[max(0, match.start() - 500) : match.start()]
        path = filename_from_code_block(info, code, prefix) or Path("unnamed.txt")
        if generated_block_has_unsafe_project_targets(path, code):
            return True
    return False


def answer_has_low_quality_generated_blocks(answer: str) -> bool:
    """Reject responses that include named generated files we would refuse to save."""
    for match in re.finditer(r"```([^\n`]*)\n(.*?)```", answer or "", flags=re.S):
        info, code = match.groups()
        prefix = (answer or "")[max(0, match.start() - 500) : match.start()]
        path = filename_from_code_block(info, code, prefix)
        if path and generated_block_quality_warnings(path, code, info):
            return True
    return False


def filename_from_nearby_text(text: str) -> Path | None:
    """Find a filename label near a fenced block.

    Models often write Markdown like **tool.py** immediately before a code
    block. That is readable to Robert, so the extractor should understand it.
    """
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
        r"^\s*(?:file|filename|path)\s*[:=]\s*([^\s,;]+)",
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
    nearby_path = filename_from_nearby_text(nearby_text)
    if nearby_path:
        return nearby_path
    return None


def strip_filename_comment(code: str) -> str:
    lines = code.splitlines()
    if lines and re.match(r"\s*(?:#|//|<!--|REM|::)\s*(?:file|filename|path)\s*:", lines[0], flags=re.I):
        return "\n".join(lines[1:]).lstrip("\n")
    if lines and re.match(r"\s*(?:file|filename|path)\s*[:=]\s*[^\s,;]+", lines[0], flags=re.I):
        return "\n".join(lines[1:]).lstrip("\n")
    return code


def apply_claimed_output_folder(rel_path: Path, surrounding_text: str) -> Path:
    """Route files to visible workbench folders when the answer names one."""
    if rel_path.parts and rel_path.parts[0].lower() == "outputs":
        return Path(*rel_path.parts[1:]) if len(rel_path.parts) > 1 else rel_path
    if len(rel_path.parts) > 1:
        return rel_path
    surrounding = (surrounding_text or "").replace("\\", "/").lower()
    folder_patterns = [
        ("program_drafts", r"outputs/program_drafts|program_drafts"),
        ("design_docs", r"outputs/design_docs|design_docs"),
        ("test_drafts", r"outputs/test_drafts|test_drafts"),
        ("schemas", r"outputs/schemas|schemas"),
        ("press_releases", r"outputs/press_releases|press_releases|press release"),
        ("press_kits", r"outputs/press_kits|press_kits|press kit"),
        ("pitch_emails", r"outputs/pitch_emails|pitch_emails|pitch email|media pitch"),
        ("media_lists", r"outputs/media_lists|media_lists|media list|contact list"),
        ("event_opportunities", r"outputs/event_opportunities|event_opportunities|event opportunity|premiere"),
        ("image_strategy", r"outputs/image_strategy|image_strategy|photo strategy|image strategy"),
        ("bios", r"outputs/bios|bios|biography|bio draft"),
        ("public_profiles", r"outputs/public_profiles|public_profiles|public profile"),
        ("investigations", r"outputs/investigations|investigations|investigation report|research report"),
        ("lead_lists", r"outputs/lead_lists|lead_lists|lead log|lead list|search leads"),
        ("source_dossiers", r"outputs/source_dossiers|source_dossiers|source dossier|source summary"),
        ("timelines", r"outputs/timelines|timelines|timeline"),
        ("evidence_matrices", r"outputs/evidence_matrices|evidence_matrices|evidence matrix|claim evidence"),
        ("mythology_notes", r"outputs/mythology_notes|mythology_notes|myth notes|mythology note"),
        ("folklore_guides", r"outputs/folklore_guides|folklore_guides|folklore guide"),
        ("story_summaries", r"outputs/story_summaries|story_summaries|story summary|retelling"),
        ("variant_comparisons", r"outputs/variant_comparisons|variant_comparisons|variant comparison|comparison chart"),
        ("reading_paths", r"outputs/reading_paths|reading_paths|reading path|source list"),
        ("sketches", r"outputs/sketches|sketches|fashion sketch|concept sketch|drawing"),
    ]
    for folder, pattern in folder_patterns:
        if re.search(pattern, surrounding):
            return Path(folder) / rel_path
    return rel_path


def generated_file_target(outputs_dir: Path, generated_root: Path, rel_path: Path, surrounding_text: str) -> Path | None:
    candidate_outputs_root = outputs_dir.parent
    routed_path = apply_claimed_output_folder(rel_path, surrounding_text)
    if routed_path.parts and routed_path.parts[0].lower() in {
        "program_drafts",
        "design_docs",
        "test_drafts",
        "schemas",
        "sketches",
        *ROLE_OUTPUT_FOLDERS,
    }:
        target = candidate_outputs_root / routed_path
        allowed_root = candidate_outputs_root
    else:
        target = generated_root / routed_path
        allowed_root = generated_root
    try:
        target.resolve().relative_to(allowed_root.resolve())
    except ValueError:
        return None
    return target


def save_generated_file_artifacts(outputs_dir: Path, run_id: str, answer: str) -> list[Path]:
    """Extract explicitly named code/file blocks into reviewable generated files."""
    run_match = re.search(r"(\d{8}_\d{6})$", run_id)
    short_run_id = run_match.group(1) if run_match else slug(run_id)[-48:]
    generated_root = outputs_dir / "generated_files" / short_run_id
    saved: list[Path] = []
    for match in re.finditer(r"```([^\n`]*)\n(.*?)```", answer, flags=re.S):
        info, code = match.groups()
        prefix = answer[max(0, match.start() - 500) : match.start()]
        suffix = answer[match.end() : match.end() + 300]
        surrounding = prefix + "\n" + suffix
        rel_path = filename_from_code_block(info, code, prefix)
        if not rel_path:
            continue
        if generated_block_quality_warnings(rel_path, code, info):
            continue
        target = generated_file_target(outputs_dir, generated_root, rel_path, surrounding)
        if not target:
            continue
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(strip_filename_comment(code).rstrip() + "\n", encoding="utf-8")
        except OSError:
            continue
        saved.append(target)
    return saved


def referenced_generated_file_blocks(answer: str) -> bool:
    for match in re.finditer(r"```([^\n`]*)\n(.*?)```", answer or "", flags=re.S):
        info, code = match.groups()
        prefix = (answer or "")[max(0, match.start() - 500) : match.start()]
        path = filename_from_code_block(info, code, prefix)
        if (
            path
            and not generated_block_quality_warnings(path, code, info)
        ):
            return True
    return False


def referenced_generated_file_paths(answer: str) -> list[Path]:
    paths: list[Path] = []
    for match in re.finditer(r"```([^\n`]*)\n(.*?)```", answer or "", flags=re.S):
        info, code = match.groups()
        prefix = (answer or "")[max(0, match.start() - 500) : match.start()]
        path = filename_from_code_block(info, code, prefix)
        if (
            path
            and not generated_block_quality_warnings(path, code, info)
        ):
            paths.append(path)
    return paths


def required_output_paths(task: str) -> list[Path]:
    """Extract concrete filenames Robert explicitly asked the candidate to create."""
    if not task:
        return []
    task_lower = task.lower()
    if not any(word in task_lower for word in ("create", "write", "draft", "make", "named", "called")):
        return []
    patterns = [
        r"(?:create|write|draft|make)\s+(?:one\s+)?(?:tiny\s+|small\s+|runnable\s+|python\s+|smoke\s+|simple\s+|annotated\s+)*"
        r"(?:file|script|program|tool|sketch|drawing)\s+(?:only\s*)?:\s*`?([a-zA-Z0-9_. /\\-]+\.(?:bat|cmd|css|csv|html|ini|js|json|md|ps1|py|svg|txt|ya?ml))`?",
        r"(?:file|script|program|tool|sketch|drawing)\s+(?:named|called)\s+`?([a-zA-Z0-9_. /\\-]+\.(?:bat|cmd|css|csv|html|ini|js|json|md|ps1|py|svg|txt|ya?ml))`?",
        r"(?:named|called)\s+`?([a-zA-Z0-9_. /\\-]+\.(?:bat|cmd|css|csv|html|ini|js|json|md|ps1|py|svg|txt|ya?ml))`?",
        r"`([a-zA-Z0-9_. /\\-]+\.(?:bat|cmd|css|csv|html|ini|js|json|md|ps1|py|svg|txt|ya?ml))`",
        r"\b((?:program_drafts|design_docs|test_drafts|schemas|investigations|lead_lists|source_dossiers|timelines|evidence_matrices|mythology_notes|folklore_guides|story_summaries|variant_comparisons|reading_paths|sketches)[/\\][a-zA-Z0-9_. /\\-]+\.(?:bat|cmd|css|csv|html|ini|js|json|md|ps1|py|svg|txt|ya?ml))\b",
    ]
    paths: list[Path] = []
    seen: set[str] = set()
    for pattern in patterns:
        for match in re.finditer(pattern, task, flags=re.I):
            path = safe_relative_file_path(match.group(1).strip(" .`'\""))
            if not path:
                continue
            key = path.as_posix().lower()
            if key in seen:
                continue
            seen.add(key)
            paths.append(path)
    return paths


def missing_required_output_file(task: str, answer: str) -> bool:
    required = required_output_paths(task)
    if not required:
        return False
    referenced = {path.as_posix().lower() for path in referenced_generated_file_paths(answer)}
    for path in required:
        if path.as_posix().lower() not in referenced:
            return True
    return False


def useful_project_answer(answer: str) -> bool:
    """Reject tiny or formatting-only model responses before they count as work."""
    compact = re.sub(r"\s+", " ", answer or "").strip()
    if not compact:
        return False
    alnum = re.sub(r"[^a-zA-Z0-9]+", "", compact)
    words = re.findall(r"[a-zA-Z0-9][a-zA-Z0-9_-]*", compact)
    if len(alnum) < MIN_USEFUL_ANSWER_ALNUM or len(words) < MIN_USEFUL_ANSWER_WORDS:
        return False
    return True


def broad_tempai_redesign_churn(task: str, answer: str) -> bool:
    """Reject repeated TemporaryAI redesign prose that has no concrete next artifact.

    Research cycles are allowed, but Emily was repeatedly saving broad summaries
    about role-shaped abilities and the candidate index without moving a real
    file forward. This catches only that pattern; concrete file paths, runnable
    commands, or filename-tagged blocks still count.
    """
    combined = f"{task}\n{answer}".lower()
    if not any(term in combined for term in ("temporaryai", "temporary ai", "candidate profile index", "candidate_profiles_flat")):
        return False

    generic_tempai_planning = (
        sum(
            1
            for marker in (
                "temporaryai v3 redesign work",
                "stage: research",
                "research and planning",
                "architecture planning",
                "proposed solutions",
                "next steps",
                "implement the",
                "will be implemented in the next cycle",
            )
            if marker in combined
        )
        >= 3
        and "program_drafts/" not in combined
        and "tested" not in combined
        and "py_compile" not in combined
    )
    has_generated_block = referenced_generated_file_blocks(answer)
    if has_generated_block and not generic_tempai_planning:
        return False
    if generic_tempai_planning:
        return True

    exact_paths = {
        match.group(0).rstrip(").,;:")
        for match in re.finditer(
            r"\b(?:TemporaryAI/|workbench/|program_drafts/|design_docs/|schemas/|investigations/|lead_lists/|source_dossiers/|timelines/|evidence_matrices/|mythology_notes/|folklore_guides/|story_summaries/|variant_comparisons/|reading_paths/|tools/|System/Docs/|Data/)"
            r"[A-Za-z0-9_ ./\\-]+\.(?:bat|cmd|json|md|py|txt|ya?ml)\b",
            answer,
            flags=re.I,
        )
    }
    action_terms = (
        "add ",
        "edit ",
        "extend ",
        "change ",
        "implement ",
        "test ",
        "run ",
        "write ",
        "create ",
        "replace ",
    )
    if len(exact_paths) >= 2 and any(term in combined for term in action_terms):
        return False

    broad_markers = [
        "role-shaped abilities",
        "candidate profile index",
        "human-like conversation",
        "memory retention",
        "source gathering",
        "redesign lab",
        "key challenges",
        "design lessons",
        "expert candidates",
    ]
    broad_hits = sum(1 for marker in broad_markers if marker in combined)
    generic_work = any(
        marker in combined
        for marker in (
            "identified key",
            "analyzed the",
            "reviewed the current",
            "should be able",
            "could be",
            "would be",
            "next steps include",
        )
    )
    return broad_hits >= 3 and generic_work


def low_quality_pr_candidate_answer(candidate: dict[str, Any] | None, answer: str) -> bool:
    """Reject PR-agent output that drifts into system design or placeholder PR shells."""
    if not candidate or not candidate_prefers_doc_pdf_outputs(candidate):
        return False
    text = answer or ""
    lower = text.lower()
    system_drift_markers = (
        "temporaryai v3 redesign",
        "temporary ai v3 redesign",
        "temporaryai redesign",
        "candidate capability report",
        "candidate_capability_report",
        "candidate database",
        "candidate schema",
        "candidate schemas",
        "system architecture",
        "integrate it with temporaryai",
        "submission form with temporaryai",
    )
    if any(marker in lower for marker in system_drift_markers):
        return True
    placeholder_patterns = (
        r"\bevent\s*\d+\b",
        r"\bcontact\s*\d+\b",
        r"\boutlet\s*\d+\b",
        r"\bwebsite\s+url\b",
        r"\[website url\]",
        r"\[insert\b",
        r"\[todo\b",
        r"\bexample\.com\b",
        r"\byour\s+(?:name|website|email|contact)\b",
    )
    if any(re.search(pattern, lower, flags=re.I) for pattern in placeholder_patterns):
        return True
    if "sarah.bennett@" in lower:
        return True

    # A PR deliverable can be a draft, but it should be a concrete Robert-facing
    # artifact, not only an outline of headings.
    pr_terms = (
        "robert",
        "bio",
        "press kit",
        "press release",
        "outreach",
        "pitch",
        "event",
        "media",
        "contact",
        "social",
        "youtube",
        "imdb",
        "amazon",
    )
    pr_hits = sum(1 for term in pr_terms if term in lower)
    heading_only_terms = (
        "introduction",
        "requirements",
        "content",
        "conclusion",
        "benefits",
        "steps",
    )
    heading_hits = sum(1 for term in heading_only_terms if term in lower)
    if heading_hits >= 4 and pr_hits < 4:
        return True
    return False


def character_life_answer_has_role_drift(
    candidate: dict[str, Any] | None,
    task: str,
    answer: str,
) -> bool:
    """Reject expert/business residue from ordinary character-life cycles."""
    if (
        not candidate
        or not candidate_uses_character_life(candidate)
        or task_explicitly_requests_system_build(task)
    ):
        return False
    lower = re.sub(r"\s+", " ", answer or "").lower()
    drift_markers = (
        "the ordinary skincare",
        "skincare plan",
        "skincare influencer",
        "temporaryai",
        "temporary ai",
        "candidate knowledge graph",
        "design document",
        "proposed schema",
        "speaking style notes",
        "speaking-style notes",
        "speech pattern analysis",
        "character research plan",
        "canon analysis",
        "canon audit",
        "personality refinement",
        "personality refinements",
        "self-training",
        "self analysis",
        "self-analysis",
        "sustainable fashion research plan",
        "research plan revision",
        "files changed or proposed",
        "how robert can test this",
        "job openings",
        "stakeholder",
        "marketing plan",
        "market analysis",
        "professional networking",
        "business strategy",
        "brand partnership",
        "customer engagement",
    )
    return any(marker in lower for marker in drift_markers)


def task_implies_build_request(task: str) -> bool:
    """Detect when Robert has moved from brainstorming into "make the thing"."""
    text = re.sub(r"\s+", " ", task or "").lower()
    build_phrases = (
        "make it",
        "make this",
        "build it",
        "create it",
        "implement it",
        "finish it",
        "make and test",
        "build and test",
        "create and test",
        "write the program",
        "make a program",
        "build a program",
        "create a program",
        "write the tool",
        "make a tool",
        "build a tool",
        "create a tool",
    )
    return any(phrase in text for phrase in build_phrases)


def answer_satisfies_build_request(task: str, answer: str) -> bool:
    """When Robert says "make it", require a real saved-file path or real test work."""
    if not task_implies_build_request(task):
        return True
    if referenced_generated_file_blocks(answer):
        return True
    text = re.sub(r"\s+", " ", answer or "").lower()
    exact_paths = re.findall(
        r"\b(?:TemporaryAI/|workbench/|program_drafts/|design_docs/|schemas/|investigations/|lead_lists/|source_dossiers/|timelines/|evidence_matrices/|mythology_notes/|folklore_guides/|story_summaries/|variant_comparisons/|reading_paths/|tools/|System/Docs/|Data/|Avatar/)"
        r"[A-Za-z0-9_ ./\\-]+\.(?:bat|cmd|json|md|py|txt|ya?ml)\b",
        answer or "",
        flags=re.I,
    )
    tested_existing = bool(
        exact_paths
        and re.search(r"\b(tested|ran|compiled|verified|py_compile|python )\b", text)
        and re.search(r"\b(how robert can test|how to test|test command|how to run)\b", text)
    )
    return tested_existing


def claims_file_change_without_artifact(answer: str) -> bool:
    """Catch fake implementation claims before they become saved progress."""
    text = re.sub(r"\s+", " ", answer or "").lower()
    has_review_file = referenced_generated_file_blocks(answer)
    live_file_words = r"(temporary_ai_live_chat\.py|temporary_ai_project_loop\.py|live chat ui|control center|launcher|system_docs|tool_source|toolsource|system/docs)"
    if re.search(rf"\b(updated|modified|changed|patched|integrated|implemented)\b.{0,160}\b{live_file_words}\b", text):
        return True
    if re.search(rf"\btest\b.{0,80}\b(updated|modified|patched)\b.{0,120}\b{live_file_words}\b", text):
        return True
    if has_review_file:
        return False
    if re.search(r"\b(?:save|copy|paste)\b.{0,120}\b(?:this|the|following)?\s*(?:file|script|program|code)\b", text):
        return True
    if re.search(r"\b(?:save|copy|paste)\b.{0,120}\b(?:program_drafts|design_docs|test_drafts|schemas|workbench)\b", text):
        return True
    change_words = r"(updated|modified|changed|created|implemented|wrote|saved|built|added)"
    file_words = r"(file|script|program|tool|launcher|\.py|\.md|\.json|system_docs|tool_source)"
    path_claim = (
        r"(?:workbench|outputs|program_drafts|design_docs|test_drafts|schemas|generated_files)"
        r"[A-Za-z0-9_ ./\\-]*\.(?:bat|cmd|css|csv|html|ini|js|json|md|ps1|py|txt|ya?ml)"
    )
    if re.search(rf"\b{change_words}\b.{{0,180}}{path_claim}", text):
        return True
    if re.search(rf"\b{change_words}\b.{0,140}\b{file_words}\b", text):
        return True
    if re.search(r"\breview the updated\b|\brun .* to see the modified\b", text):
        return True
    return False


def violates_explicit_programming_limits(task: str, answer: str) -> bool:
    """Reject code that directly contradicts concrete limits in Robert's task."""
    task_lower = (task or "").lower()
    answer_lower = (answer or "").lower()
    checks = [
        ("do not import", r"\bimport\s+[a-zA-Z_]|\bfrom\s+[a-zA-Z_].*\bimport\b"),
        ("do not create directories", r"os\.makedirs|mkdir|new-item\s+-itemtype\s+directory"),
        ("do not write", r"\.write\(|write_text\(|with\s+open\([^)]*,\s*['\"][wa]"),
        ("do not read", r"\.read\(|read_text\(|with\s+open\([^)]*,\s*['\"]r"),
        ("do not download", r"urlopen|requests\.|invoke-webrequest|curl\s+|wget\s+"),
        ("do not train", r"\.fit\(|train_test_split|epochs\s*=|model\.save"),
        ("only one print statement", r"\bdef\s+|\bclass\s+|with\s+open|os\.|requests\.|urlopen|model\."),
    ]
    for trigger, pattern in checks:
        if trigger in task_lower and re.search(pattern, answer_lower):
            return True
    return False


def acceptable_project_answer(task: str, answer: str, candidate: dict[str, Any] | None = None) -> bool:
    return (
        useful_project_answer(answer)
        and answer_uses_candidate_index(task, answer)
        and not broad_tempai_redesign_churn(task, answer)
        and not low_quality_pr_candidate_answer(candidate, answer)
        and not character_life_answer_has_role_drift(candidate, task, answer)
        and answer_satisfies_build_request(task, answer)
        and not missing_required_output_file(task, answer)
        and not claims_file_change_without_artifact(answer)
        and not violates_explicit_programming_limits(task, answer)
        and not has_unsafe_project_targets(answer)
        and not answer_has_low_quality_generated_blocks(answer)
    )


def sanitized_robert_live_notes(path: Path, char_limit: int = 2200) -> str:
    """Read only Robert's steering notes, not candidate replies or code blocks."""
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    notes: list[str] = []
    for match in re.finditer(r"^## Robert at [^\n]*\n(.*?)(?=^## |\Z)", text, flags=re.S | re.M):
        note = re.sub(r"```.*?```", "", match.group(1), flags=re.S).strip()
        if note:
            notes.append(note)
    return "\n\n".join(notes)[-char_limit:]


def answer_uses_candidate_index(task: str, answer: str) -> bool:
    """For TemporaryAI redesign tasks, reject generic plans that ignore actual candidates."""
    task_lower = (task or "").lower()
    if "candidate_profile_index" not in task_lower and "actual candidate" not in task_lower:
        return True
    answer_lower = (answer or "").lower()
    required_any = [
        "laura",
        "sarah",
        "emily",
        "jessica",
        "ladybug",
        "kara",
        "blue",
        "edgar",
        "holmes",
    ]
    hits = sum(1 for name in required_any if name in answer_lower)
    concrete_terms = [
        "loop_state",
        "candidate_memory",
        "role_ability",
        "source_pack",
        "avatar",
        "archive",
        "workbench",
    ]
    concrete_hits = sum(1 for term in concrete_terms if term in answer_lower)
    return hits >= 4 and concrete_hits >= 3


def infer_cycle_stage(answer: str, generated_files: list[Path] | None = None) -> str:
    """Classify a project-loop answer without forcing every cycle to create a file."""
    text = (answer or "").lower()
    if generated_files:
        return "drafting_or_editing"
    explicit_stage = re.search(r"(?:^|\n)\s*(?:#+\s*)?(?:\*\*)?stage(?:\*\*)?\s*:?\s*([^\n]+)", answer or "", flags=re.I)
    if explicit_stage:
        stage_text = explicit_stage.group(1).strip("*: ").lower()
        if "research" in stage_text or "reading" in stage_text:
            return "reading_or_research"
        if "plan" in stage_text:
            return "planning"
        if "draft" in stage_text or "edit" in stage_text:
            return "drafting_or_editing"
        if "test" in stage_text or "handoff" in stage_text:
            return "testing_or_handoff"
    if "how robert can test" in text or "how to test" in text or "how to run" in text:
        return "testing_or_handoff"
    if any(term in text for term in ["patch plan", "files to change", "implementation plan", "schema"]):
        return "design"
    if any(term in text for term in ["reviewed", "read", "research", "source", "document", "docs"]):
        return "reading_or_research"
    if any(term in text for term in ["next step", "next cycle", "continue"]):
        return "planning"
    return "progress"


def should_save_workbench_deliverable(answer: str, stage: str, generated_files: list[Path]) -> bool:
    """Only save workbench deliverables when the cycle actually produced one."""
    if generated_files:
        return True
    text = (answer or "").lower()
    if stage in {"reading_or_research", "planning"}:
        return False
    if re.search(r"how robert can test this(?:\*\*)?\s*:?\s*(?:n/a|none|not applicable)", text):
        return False
    deliverable_markers = [
        "patch plan",
        "files to change",
        "implementation plan",
        "test plan",
        "how robert can test",
        "how to run",
        "schema",
        "draft file",
        "code block",
    ]
    if any(marker in text for marker in deliverable_markers):
        return True
    return stage in {"design", "testing_or_handoff"}


def extract_next_step(answer: str) -> str:
    match = re.search(
        r"(?:^|\n)\s*(?:#+\s*)?(?:\*\*)?(?:next step|next cycle|what i will do next)(?:\*\*)?\s*:?\s*(.*)",
        answer,
        flags=re.I | re.S,
    )
    if match:
        text = match.group(1).strip()
        text = re.split(
            r"\n\s*(?:#+\s*)?(?:\*\*)?(?:optional personal note|saved artifacts|rejected short outputs|how robert can test this)(?:\*\*)?\b",
            text,
            flags=re.I,
        )[0]
        text = re.sub(r"[*_`]+", "", text)
        return re.sub(r"\s+", " ", text).strip()[:700]
    compact = re.sub(r"\s+", " ", answer.strip())
    return compact[-500:]


def extract_test_instructions(answer: str) -> str:
    match = re.search(
        r"(?:^|\n)\s*(?:#+\s*)?(?:\*\*)?(?:how robert can test this|how robert can test|how to test|how to run|activation instructions)(?:\*\*)?\s*:?\s*(.*)",
        answer,
        flags=re.I | re.S,
    )
    if not match:
        return ""
    text = match.group(1).strip()
    text = re.split(r"\n\s*(?:#+\s*)?(?:\*\*)?(?:next step|risks|notes|optional personal note)(?:\*\*)?\b", text, flags=re.I)[0]
    if re.match(r"^(?:\*\*)?\s*(?:n/a|none|not applicable)\b", text, flags=re.I):
        return ""
    text = re.sub(r"[*`]+", "", text)
    return re.sub(r"\s+", " ", text).strip()[:1000]


def normalize_test_instructions(text: str, generated_files: list[Path]) -> str:
    """Prefer real saved workbench paths over model-invented shorthand paths."""
    if generated_files:
        saved_paths = [rel(path) for path in generated_files[:3]]
        run_lines: list[str] = []
        for path in generated_files[:3]:
            if path.suffix.lower() != ".py":
                continue
            try:
                code = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if "__main__" in code:
                run_lines.append(f"python {rel(path)}")
        instructions = "Saved file(s): " + "; ".join(saved_paths) + "."
        if run_lines:
            instructions += " Test command(s): " + "; ".join(run_lines) + "."
        else:
            instructions += " Review these as draft artifacts; no runnable Python entrypoint was saved."
        return instructions[:1200]
    if not text:
        return ""
    normalized = text
    normalized = re.sub(
        r"\bworkbench/program_drafts\b",
        "workbench/outputs/program_drafts",
        normalized,
        flags=re.I,
    )
    normalized = re.sub(r"\bprogramdrafts\b", "program_drafts", normalized, flags=re.I)
    normalized = re.sub(r"\bcandidateprofilesflat\b", "candidate_profiles_flat", normalized, flags=re.I)
    normalized = re.sub(r"\btoolsource\b", "tool_source", normalized, flags=re.I)
    normalized = re.sub(r"\bbash\s+python\b", "python", normalized, flags=re.I)
    if generated_files and "exact saved file" not in normalized.lower():
        saved = "; ".join(rel(path) for path in generated_files[:3])
        normalized += f" Exact saved file(s): {saved}."
    return normalized[:1200]


def test_instruction_paths_are_real(candidate: dict[str, Any], text: str) -> bool:
    """Keep non-generated test instructions only when referenced files exist."""
    if not text:
        return True
    path_matches = re.findall(
        r"([a-zA-Z0-9_. /\\-]+\.(?:bat|cmd|css|csv|html|ini|js|json|md|ps1|py|txt|ya?ml))",
        text,
        flags=re.I,
    )
    if not path_matches:
        return False
    outputs = candidate_outputs_dir(candidate)
    for raw in path_matches:
        safe_path = safe_relative_file_path(raw.strip(" .`'\""))
        if not safe_path:
            return False
        candidates = [
            PROJECT_ROOT / safe_path,
            outputs / safe_path,
            candidate_workbench_dir(candidate) / safe_path,
        ]
        if not any(path.exists() for path in candidates):
            return False
        for path in candidates:
            if path.exists() and path.suffix.lower() == ".py":
                try:
                    code = path.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    return False
                try:
                    rel_path = path.relative_to(candidate_workbench_dir(candidate) / "outputs")
                except ValueError:
                    rel_path = path.name
                if generated_python_quality_warnings(Path(rel_path), code):
                    return False
                break
    return True


def verify_saved_artifacts(artifacts: list[Path], generated_files: list[Path]) -> dict[str, Any]:
    """Record whether loop artifacts really exist and look non-empty."""
    checked: list[dict[str, Any]] = []
    seen: set[Path] = set()
    missing_count = 0
    tiny_count = 0
    for path in [*artifacts, *generated_files]:
        if path in seen:
            continue
        seen.add(path)
        item: dict[str, Any] = {"path": rel(path), "exists": path.exists()}
        if not path.exists():
            missing_count += 1
            checked.append(item)
            continue
        try:
            size = path.stat().st_size
        except OSError as exc:
            item["error"] = str(exc)
            checked.append(item)
            continue
        item["size_bytes"] = size
        tiny_limit = 120 if path.suffix.lower() == ".py" else 300
        if path.suffix.lower() in GENERATED_FILE_EXTENSIONS and size < tiny_limit:
            item["tiny_artifact"] = True
            tiny_count += 1
        if path.suffix.lower() == ".py":
            try:
                code = path.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                item["quality_warnings"] = [f"could not read Python artifact: {exc}"]
            else:
                quality = generated_python_quality_warnings(path.relative_to(path.parent.parent) if path.parent.parent else path, code)
                if quality:
                    item["quality_warnings"] = quality
        checked.append(item)
    warnings: list[str] = []
    if missing_count:
        warnings.append(f"{missing_count} saved artifact path(s) are missing")
    if tiny_count:
        warnings.append(f"{tiny_count} saved artifact path(s) are suspiciously tiny")
    quality_warnings = [
        warning
        for item in checked
        for warning in item.get("quality_warnings", [])
    ]
    warnings.extend(quality_warnings[:8])
    return {
        "checked_count": len(checked),
        "missing_count": missing_count,
        "tiny_count": tiny_count,
        "quality_warning_count": len(quality_warnings),
        "files": checked,
        "warnings": warnings,
    }


def update_project_state(
    candidate: dict[str, Any],
    run_id: str,
    task: str,
    answer: str,
    status: str,
    stage: str,
    artifacts: list[Path],
    generated_files: list[Path],
    artifact_verification: dict[str, Any] | None = None,
) -> Path:
    path = candidate_project_state_path(candidate)
    state = read_json_file(path, default={}) or {}
    previous_next_step = state.get("next_step", "")
    previous_test_instructions = state.get("activation_or_test_instructions", "")
    previous_artifacts = state.get("last_artifacts", []) or []
    previous_generated_files = state.get("last_generated_files", []) or []
    cycles_completed = int(state.get("cycles_completed") or 0) + 1
    test_instructions = normalize_test_instructions(
        extract_test_instructions(answer),
        generated_files,
    )
    if test_instructions and not generated_files and not test_instruction_paths_are_real(candidate, test_instructions):
        test_instructions = ""
    if not test_instructions and generated_files:
        test_instructions = state.get("activation_or_test_instructions", "")
    current_project = state.get("current_project") or (task.strip().splitlines()[0][:160] if task.strip() else "Self-chosen project work")
    if status == "model_output_rejected":
        next_step = (
            "Resume from the last accepted real artifact. Ignore the rejected output from "
            f"{run_id}; it did not create review-safe work."
        )
        artifact_paths = previous_artifacts
        generated_file_paths = previous_generated_files
        test_instructions = previous_test_instructions if test_instruction_paths_are_real(candidate, str(previous_test_instructions)) else ""
    else:
        next_step = extract_next_step(answer)
        artifact_paths = [rel(path) for path in artifacts][-10:]
        generated_file_paths = [rel(path) for path in generated_files][-10:]
    state.update(
        {
            "candidate_id": candidate["candidate_id"],
            "current_project": current_project,
            "stage": stage,
            "cycles_completed": cycles_completed,
            "last_cycle_id": run_id,
            "last_status": status,
            "last_updated_at": now_iso(),
            "last_task": task,
            "last_artifacts": artifact_paths,
            "last_generated_files": generated_file_paths,
            "last_artifact_verification": artifact_verification or {},
            "next_step": next_step,
            "activation_or_test_instructions": test_instructions,
        }
    )
    state.setdefault("started_at", now_iso())
    history = state.setdefault("recent_cycles", [])
    if isinstance(history, list):
        history.append(
            {
                "run_id": run_id,
                "status": status,
                "stage": stage,
                "updated_at": state["last_updated_at"],
                "task": task[:300],
                "artifacts": [rel(path) for path in artifacts][-5:],
                "artifact_warnings": (artifact_verification or {}).get("warnings", []),
            }
        )
        del history[:-8]
    write_json(path, state)
    return path


def project_retry_prompt(original_prompt: str, bad_answer: str) -> str:
    return (
        original_prompt
        + "\n\nYour previous saved response was too short or empty and cannot count as progress."
        + "\nDo this cycle again as concrete work Robert can review."
        + "\nDo not claim you implemented something unless you provide a specific artifact, patch plan, file draft, generated file block, or clear progress note about what you reviewed."
        + "\nIf you only read or planned, say that plainly. Do not say a file was updated, modified, created, or ready to run unless you include the file content."
        + "\nIf you draft JSON, use a ```json filename=schemas/name.json fenced block, not a Python fence. If you draft prose, use design_docs/*.md."
        + "\nReturn a useful cycle result with these sections: Title, Stage, What I worked on, Actual work produced, Files or changes proposed, How Robert can test this if applicable, Next step."
        + f"\nRejected response was: {bad_answer!r}"
    )


def compact_file_excerpt(path: Path, max_chars: int = 1800) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace").strip()
    except Exception:
        return ""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "\n..."


def lean_project_prompt(candidate: dict[str, Any], task: str, research_packet: dict[str, Any] | None = None) -> str:
    """Build a small direct project prompt for cases where the rich prompt collapses."""
    if candidate_uses_character_life(candidate) and not task_explicitly_requests_system_build(task):
        return character_life_prompt(candidate, task, research_packet=research_packet)
    profile = candidate.get("profile", {}) or {}
    display = profile.get("display_name", candidate["candidate_id"])
    role = profile.get("role_title", "")
    is_pr_candidate = candidate_prefers_doc_pdf_outputs(candidate)
    workbench = candidate_workbench_dir(candidate)
    outputs = candidate_outputs_dir(candidate)
    lab = workbench / "tempai_lab_20260611"
    work_order = workbench / "inputs" / "work_orders" / "emily_temporary_ai_v3_redesign_work_order_20260611.md"
    safeguard_doc = workbench / "inputs" / "reference_docs" / "PERSONHOOD_SAFEGUARD_AUDIT_v1.md"
    latest_safeguard = PROJECT_ROOT / "Data" / "personhood_safeguards" / "latest_personhood_safeguard_audit.monitor.md"
    lab_readme = lab / "TEMPORARY_AI_REDESIGN_LAB_README.md"
    candidate_index = lab / "CANDIDATE_PROFILE_INDEX.md"
    if is_pr_candidate:
        useful_sources = [
            workbench / "inputs" / "reference_docs" / "SARAH_PR_AGENT_WORK_BRIEF.md",
            outputs / "design_docs" / "new_york_events_guide.md",
            outputs / "design_docs" / "new_york_events_guide_improved.md",
            outputs / "design_docs" / "event_recommendations.md",
            outputs / "design_docs" / "event_recommendation_process.md",
            outputs / "program_drafts" / "event_recommendations.py",
            outputs / "program_drafts" / "event_recommender.py",
            outputs / "program_drafts" / "event_research_tool.py",
        ]
    else:
        useful_sources = [
            lab_readme,
            candidate_index,
            work_order,
            safeguard_doc,
            latest_safeguard,
            lab / "system_docs" / "TEMPORARY_AI_SYSTEM_v2.md",
            lab / "system_docs" / "TEMPORARY_AI_CONTROL_CENTER_v1.md",
        ]
    lines = [
        f"You are {display}, {role}.",
        "This is a direct artifact-writing mode for a supervised TemporaryAI project loop.",
        "Do not chat. Do not give a canned status report.",
        "Produce one useful cycle result Robert can review. This may be research notes, a design note, an edit plan, a filename-tagged code block, or test instructions.",
        "Not every cycle needs a new file. If the correct work is reading, researching, planning, or improving an existing draft, say exactly what you reviewed and what you will do next.",
        "Builder contract: when Robert says make it, build it, create it, write the program, or implement it, create or improve the smallest real runnable/reviewable artifact now. Do not answer with only architecture or future steps.",
        "Builder contract: after a build request, either include a complete filename-tagged file block or give exact evidence that you tested an existing saved file. Include exact run instructions.",
        "Continuation contract: keep working on the same real artifact across cycles until it is usable. Do not jump to a new schema, index, or redesign summary unless the current artifact is complete.",
        "If the current project is complete and the loop is still running, pick a next useful task from the attached docs: TemporaryAI source gathering, candidate activation/testing, avatar builder references, 3D worlds/TARDIS/notebook worlds, Kira/Lisa memory tools, or a small personal programming project.",
        "You have a read-only TemporaryAI redesign lab in your workbench. Do not edit live Kira files.",
        "Write concrete TemporaryAI v3 redesign work with enough detail to implement later.",
        "If you draft a file, include one complete filename-tagged fenced code block. Match the fence language to the filename: "
        "```python filename=program_drafts/tool_name.py\n# code starts here\n```, "
        "```json filename=schemas/schema_name.json\n{\"name\": \"value\"}\n```, or "
        "```markdown filename=design_docs/plan.md\n# Plan\n```. "
        "Do not write a separate empty filename fence. Do not split the filename tag and the code into two different fences.",
        "Do not put nested fenced code blocks inside a Markdown artifact. If a design doc needs schema or code, describe it in prose or create a second separate valid filename-tagged artifact.",
        "Prefer visible workbench output folders: program_drafts/, design_docs/, test_drafts/, schemas/, investigations/, lead_lists/, source_dossiers/, timelines/, evidence_matrices/, mythology_notes/, folklore_guides/, story_summaries/, variant_comparisons/, reading_paths/, and sketches/.",
        "Use the personhood safeguard audit as a read-only honesty check: if you claim a file or tool exists, name the exact path and include content the loop can save.",
        "Do not claim you saved a binary model file such as .h5 or .pt. Draft the Python script that would create it instead.",
        "Use .py only for runnable Python with real executable code. Put architecture notes, plans, and prose in design_docs/*.md instead of a Python file.",
        "Programming code must be self-contained enough to run. Do not call helper functions, classes, APIs, or modules that you did not define in the same file or import from real available modules.",
        "Do not leave pass, TODO, placeholder, stub, or not-implemented functions in a runnable program draft. If the idea is not ready to run, write it as design_docs/*.md instead.",
        "Do not give Robert a test command for a script unless the script exists, has a matching command-line interface, and you believe the exact command can run.",
        "Human expert style: talk like a coworker in the role. For example, a PR agent can say 'I'll spend this work cycle looking for events and save a short list for us to review,' while a programmer can say 'I'm going to patch the file writer first, then run a smoke test.'",
        "For programming tasks, follow Robert's requested behavior literally. Do not add extra filesystem, network, model-training, or install side effects unless Robert explicitly asked for them.",
        "If you create runnable code, include 'How Robert can test this' with the exact command or launcher.",
        "Developer rhythm rule: do not create endless numbered schema or design files for the same idea. If an artifact already exists for that purpose, continue by editing or extending that named artifact, or explain honestly that you only reviewed it.",
        "TemporaryAI redesign priority: prefer one concrete improvement to a real workbench artifact over another broad proposal. Good targets include program_drafts/temporary_ai_candidate_capability_report.py, program_drafts/source_generator.py, design_docs/*.md, or a valid schemas/*.json file.",
        "Useful sections: Title, Stage, What I reviewed/worked on, Work produced, Files to change or edit, How Robert can test this, Next step.",
        "",
        f"Robert's task: {task or 'Create one concrete TemporaryAI v3 redesign artifact.'}",
        "",
        candidate_resume_brief(candidate),
        "",
        "Local context excerpts:",
    ]
    if is_pr_candidate:
        lines.extend(
            [
                "PR correction mode: do not work on TemporaryAI redesign, candidate schemas, candidate reports, or generic system architecture unless Robert explicitly asks Sarah to do that.",
                "Sarah's fallback task is Robert-facing PR work: bio drafts, press kit sections, outreach emails, press releases, NYC entertainment event watchlists, media/contact research notes, and social media strategy.",
                "Do not invent contacts, event dates, submission instructions, or Sarah email addresses. Mark unknown facts as needs lookup or needs Robert confirmation.",
                "Useful PR output filenames: bios/robert_short_bio_draft.md, pitch_emails/event_access_pitch.md, press_releases/project_press_release.md, press_kits/robert_press_kit.md, event_opportunities/nyc_event_watchlist.md, media_lists/public_contact_research.md.",
            ]
        )
    for source in useful_sources:
        if source.exists():
            lines.append(f"\n--- {rel(source)} ---")
            lines.append(compact_file_excerpt(source, max_chars=1500))
    if research_packet:
        lines.append("\nOnline research packet summary:")
        for item in (research_packet.get("results") or [])[:5]:
            title = str(item.get("title", "")).strip()
            url = str(item.get("url", "")).strip()
            if title and url:
                lines.append(f"- {title}: {url}")
    return "\n".join(lines)[:9000]


def ask_model_direct_project(prompt: str) -> str:
    """Ask the local model with a compact prompt, bypassing live-chat system context."""
    options = {
        "temperature": max(0.25, min(TEMPERATURE, 0.55)),
        "num_predict": max(MAX_TOKENS, 1200),
    }
    if OLLAMA_NUM_CTX > 0:
        options["num_ctx"] = max(OLLAMA_NUM_CTX, 8192)
    messages = [
        {
            "role": "system",
            "content": (
                "You write concrete local project artifacts. "
                "Return useful Markdown, schemas, or code. Never answer with only punctuation or one word."
            ),
        },
        {"role": "user", "content": prompt},
    ]
    require_installed_exact_qwen35(
        requests,
        chat_endpoint=OLLAMA_ENDPOINT,
        model_name=MODEL_NAME,
        model_digest=MODEL_DIGEST,
        timeout=OLLAMA_TIMEOUT,
    )
    response = requests.post(
        OLLAMA_ENDPOINT,
        json={
            "model": MODEL_NAME,
            "stream": False,
            "messages": messages,
            "options": options,
            **ordinary_model_request_fields(MODEL_NAME),
        },
        timeout=OLLAMA_TIMEOUT,
    )
    if response.status_code == 404 and OLLAMA_ENDPOINT.endswith("/api/chat"):
        require_installed_exact_qwen35(
            requests,
            chat_endpoint=OLLAMA_ENDPOINT,
            model_name=MODEL_NAME,
            model_digest=MODEL_DIGEST,
            timeout=OLLAMA_TIMEOUT,
        )
        response = requests.post(
            OLLAMA_ENDPOINT.rsplit("/api/chat", 1)[0] + "/api/generate",
            json={
                "model": MODEL_NAME,
                "stream": False,
                "prompt": (
                    "You write concrete local project artifacts. Return useful Markdown, schemas, or code.\n\n"
                    + prompt
                    + "\n\nArtifact:"
                ),
                "options": options,
                **ordinary_model_request_fields(MODEL_NAME),
            },
            timeout=OLLAMA_TIMEOUT,
        )
    response.raise_for_status()
    data = response.json()
    require_exact_qwen35_response_model(data, expected_model=MODEL_NAME)
    if "message" in data:
        return str(data.get("message", {}).get("content", "")).strip()
    return str(data.get("response", "")).strip()


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
    path = PROJECT_ROOT / "TemporaryAI" / "candidates" / candidate_id / "workbench"
    path.mkdir(parents=True, exist_ok=True)
    return path


def candidate_research_dir(candidate: dict[str, Any]) -> Path:
    profile = candidate.get("profile", {}) or {}
    policy = profile.get("online_research_policy", {}) or {}
    folder = policy.get("save_folder") or "inputs/online_research"
    path = Path(str(folder))
    if not path.is_absolute():
        if str(folder).replace("\\", "/").startswith("TemporaryAI/"):
            path = PROJECT_ROOT / path
        else:
            path = candidate_workbench_dir(candidate) / path
    path.mkdir(parents=True, exist_ok=True)
    return path


def candidate_work_orders_context(candidate: dict[str, Any], char_limit: int = 3000) -> str:
    workbench = candidate_workbench_dir(candidate)
    work_orders = workbench / "inputs" / "work_orders"
    if not work_orders.exists():
        return ""
    files = sorted(
        [path for path in work_orders.glob("*.md") if path.is_file()],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )[:3]
    if not files:
        return ""
    lines = ["Current work orders from Robert/Codex:"]
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace").strip()
        if not text:
            continue
        lines.append(f"\n--- {path.name} ---\n{text[:1200]}")
    return "\n".join(lines)[:char_limit]


def strip_tags(text: str) -> str:
    text = re.sub(r"<script\b.*?</script>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<style\b.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def clean_search_url(url: str) -> str:
    url = html.unescape(url)
    parsed = urlparse(url)
    if parsed.path.startswith("/l/"):
        query = parse_qs(parsed.query)
        if query.get("uddg"):
            return unquote(query["uddg"][0])
    return url


def fetch_search_results(query: str, max_results: int = MAX_RESEARCH_RESULTS) -> tuple[list[dict[str, str]], str]:
    """Fetch lightweight web-search snippets without API keys.

    The saved packet is only source leads for the candidate to reason from; it is
    not treated as verified truth.
    """
    if not query.strip():
        return [], "empty query"
    rss_results, rss_error = fetch_bing_rss_results(query, max_results=max_results)
    if rss_results:
        return rss_results, ""

    url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 KiraTemporaryAIResearch/1.0",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    try:
        with urlopen(request, timeout=SEARCH_TIMEOUT_SECONDS) as response:
            page = response.read().decode("utf-8", errors="replace")
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        return [], rss_error or f"{type(exc).__name__}: {exc}"

    blocks = re.findall(r'<div class="result results_links.*?</div>\s*</div>', page, flags=re.I | re.S)
    if not blocks:
        blocks = re.findall(r'<a rel="nofollow" class="result__a".*?</a>.*?(?:result__snippet.*?</a>|</div>)', page, flags=re.I | re.S)

    results: list[dict[str, str]] = []
    for block in blocks:
        link_match = re.search(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', block, flags=re.I | re.S)
        if not link_match:
            continue
        raw_url, raw_title = link_match.groups()
        snippet_match = re.search(r'class="result__snippet"[^>]*>(.*?)</a>', block, flags=re.I | re.S)
        if not snippet_match:
            snippet_match = re.search(r'class="result__snippet"[^>]*>(.*?)</div>', block, flags=re.I | re.S)
        result = {
            "query": query,
            "title": strip_tags(raw_title),
            "url": clean_search_url(raw_url),
            "snippet": strip_tags(snippet_match.group(1)) if snippet_match else "",
        }
        if result["title"] and result["url"] and result["url"] not in {item["url"] for item in results}:
            results.append(result)
        if len(results) >= max_results:
            break
    return results, "" if results else (rss_error or "no parsed results")


def fetch_bing_rss_results(query: str, max_results: int = MAX_RESEARCH_RESULTS) -> tuple[list[dict[str, str]], str]:
    url = f"https://www.bing.com/search?format=rss&q={quote_plus(query)}"
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 KiraTemporaryAIResearch/1.0",
            "Accept": "application/rss+xml,application/xml,text/xml",
        },
    )
    try:
        with urlopen(request, timeout=SEARCH_TIMEOUT_SECONDS) as response:
            data = response.read()
        root = ET.fromstring(data)
    except (HTTPError, URLError, TimeoutError, OSError, ET.ParseError) as exc:
        return [], f"{type(exc).__name__}: {exc}"
    results: list[dict[str, str]] = []
    for item in root.findall("./channel/item"):
        title = strip_tags(item.findtext("title") or "")
        link = html.unescape(item.findtext("link") or "")
        snippet = strip_tags(item.findtext("description") or "")
        if title and link and link not in {entry["url"] for entry in results}:
            results.append({"query": query, "title": title, "url": link, "snippet": snippet})
        if len(results) >= max_results:
            break
    return results, "" if results else "no RSS results"


def online_research_enabled(candidate: dict[str, Any], force: bool = False) -> bool:
    if force:
        return True
    profile = candidate.get("profile", {}) or {}
    policy = profile.get("online_research_policy", {}) or {}
    return bool(policy.get("enabled"))


def build_research_queries(candidate: dict[str, Any], task: str, extra_queries: list[str] | None = None) -> list[str]:
    profile = candidate.get("profile", {}) or {}
    policy = profile.get("online_research_policy", {}) or {}
    queries: list[str] = []
    for query in extra_queries or []:
        if query and query.strip():
            queries.append(query.strip())

    role = str(profile.get("role_title") or "").strip()
    focus = str((profile.get("knowledge_plan") or {}).get("focus") or "").strip()
    display = str(profile.get("display_name") or "").strip()
    task_text = task.strip()
    if task_text:
        short_task = re.sub(r"\s+", " ", task_text)[:180]
        queries.append(short_task)
    seed_queries = policy.get("default_queries") or []
    queries.extend(str(item).strip() for item in seed_queries if str(item).strip())
    if role or focus:
        topic = focus or role
        queries.append(f"{topic} latest tools examples projects 2026")
        queries.append(f"{topic} practical guide current best practices")
    if display and ("programming" in role.lower() or "computer" in role.lower() or "ai" in role.lower()):
        queries.append("local LLM agents programming tools 2026")
        queries.append("Python small retro game pygame examples")

    deduped: list[str] = []
    seen: set[str] = set()
    for query in queries:
        key = query.lower()
        if key not in seen:
            seen.add(key)
            deduped.append(query)
        if len(deduped) >= 4:
            break
    return deduped


def create_online_research_packet(
    candidate: dict[str, Any],
    task: str,
    extra_queries: list[str] | None = None,
) -> dict[str, Any]:
    profile = candidate.get("profile", {}) or {}
    queries = build_research_queries(candidate, task, extra_queries=extra_queries)
    packet_id = f"online_research_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    research_dir = candidate_research_dir(candidate)
    results: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []
    for query in queries:
        query_results, error = fetch_search_results(query)
        results.extend(query_results)
        if error:
            errors.append({"query": query, "error": error})
    packet = {
        "packet_id": packet_id,
        "created_at": now_iso(),
        "candidate_id": candidate["candidate_id"],
        "display_name": profile.get("display_name", candidate["candidate_id"]),
        "purpose": "Supervised TemporaryAI online research notes. Source leads only; not memory and not verified truth.",
        "queries": queries,
        "results": results,
        "errors": errors,
    }
    json_path = research_dir / f"{packet_id}.json"
    md_path = research_dir / f"{packet_id}.md"
    write_json(json_path, packet)
    lines = [
        f"# {packet_id}",
        "",
        f"- candidate_id: {packet['candidate_id']}",
        f"- created_at: {packet['created_at']}",
        "- policy: source leads only; cite URLs; do not claim actions were taken online.",
        "",
        "## Queries",
    ]
    lines.extend(f"- {query}" for query in queries)
    lines.append("")
    lines.append("## Results")
    for item in results:
        lines.append(f"- [{item['title']}]({item['url']})")
        if item.get("snippet"):
            lines.append(f"  - {item['snippet']}")
    if errors:
        lines.append("")
        lines.append("## Lookup Notes")
        lines.extend(f"- {item['query']}: {item['error']}" for item in errors)
    md_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    packet["json_path"] = rel(json_path)
    packet["markdown_path"] = rel(md_path)
    return packet


def format_research_packet_for_prompt(packet: dict[str, Any] | None, char_limit: int = 4500) -> str:
    if not packet:
        return ""
    lines = [
        "Current online research packet for this cycle:",
        "Use these as source leads and cite URLs in your saved work when relevant. Do not present snippets as personal memory.",
    ]
    for item in (packet.get("results") or [])[:12]:
        lines.append(f"- {item.get('title', '').strip()} | {item.get('url', '').strip()}")
        if item.get("snippet"):
            lines.append(f"  {item['snippet']}")
    if packet.get("errors") and not packet.get("results"):
        lines.append("Lookup had errors/no parsed results. If needed, write exact follow-up searches.")
    text = "\n".join(lines)
    return text[:char_limit]


CHARACTER_LIFE_AI_TYPES = {
    "canon_reconstruction_temp_ai",
    "fictional_character",
    "fictional_character_reconstruction",
    "historical_reconstruction_temp_ai",
    "historical_person",
    "memory_relative_temp_ai",
    "owner_presence_ai",
}


def candidate_uses_character_life(candidate: dict[str, Any]) -> bool:
    """Keep character visitors out of the expert/programmer work contract."""
    profile = candidate.get("profile", {}) or {}
    request = candidate.get("creation_request", {}) or {}
    ai_type = str(profile.get("ai_type", "")).strip().lower()
    category = str(profile.get("ui_category") or request.get("ui_category") or "").strip().lower()
    creation_type = str(request.get("creation_type", "")).strip().lower()
    return (
        ai_type in CHARACTER_LIFE_AI_TYPES
        or category in {"fictional character", "historical person", "memory relative"}
        or creation_type in {"fictional_character", "historical_person", "memory_relative"}
    )


def task_explicitly_requests_system_build(task: str) -> bool:
    text = (task or "").lower()
    system_terms = (
        "write code", "write a program", "build a program", "create a program",
        "python", "javascript", "temporaryai system", "temporary ai system",
        "kira system", "patch the", "edit the code", "software", "programming task",
    )
    return any(term in text for term in system_terms)


def character_life_requests_online_research(task: str) -> bool:
    """Only browse during character life when the current task asks for it."""
    text = (task or "").lower()
    research_terms = (
        "research online", "look up online", "search online", "internet research",
        "search the web", "web search", "look this up", "find information online",
        "latest news", "current events",
    )
    return any(term in text for term in research_terms)


def character_activity_for_cycle(candidate: dict[str, Any], task: str) -> tuple[str, str]:
    profile = candidate.get("profile", {}) or {}
    life = profile.get("life_activity_profile", {}) or {}
    activities = life.get("activities") or []
    normalized: list[dict[str, str]] = []
    for item in activities:
        if isinstance(item, str):
            normalized.append({"name": item, "form": "civilian"})
        elif isinstance(item, dict) and item.get("name"):
            normalized.append({"name": str(item["name"]), "form": str(item.get("form", "civilian"))})
    if not normalized:
        interests = profile.get("personal_interests", []) or []
        normalized = [{"name": str(item), "form": "civilian"} for item in interests if str(item).strip()]
    if not normalized:
        normalized = [
            {"name": "write a private journal reflection", "form": "civilian"},
            {"name": "read or work on a small creative project", "form": "civilian"},
        ]
    match = re.search(r"cycle\s+(\d+)", task or "", flags=re.I)
    cycle_number = int(match.group(1)) if match else 1
    chosen = normalized[(cycle_number - 1) % len(normalized)]
    return chosen["name"], chosen.get("form", "civilian")


def character_identity_context(candidate: dict[str, Any], char_limit: int = 5000) -> str:
    """Return character grounding without shared programmer/project orientation."""
    profile = candidate.get("profile", {}) or {}
    request = candidate.get("creation_request", {}) or {}
    canon = profile.get("canon_fact_sheet") or request.get("canon_fact_sheet") or {}
    adaptation_lock = profile.get("adaptation_lock") or request.get("adaptation_lock") or {}
    reliable_pack = candidate.get("reliable_source_pack", {}) or {}
    source_pack = candidate.get("source_pack", {}) or {}
    lookup = candidate.get("online_research_summary", {}) or {}
    lines = [
        "Identity grounding for this ordinary life cycle. Keep this backstage and do not recite it as a source report:"
    ]
    if adaptation_lock:
        lines.append(
            "- Exact adaptation lock (higher priority than loose web material): "
            + json.dumps(adaptation_lock, ensure_ascii=False)[:2200]
        )
    for fact in (canon.get("facts") or [])[:12]:
        lines.append(f"- Canon anchor: {fact}")
    for item in (canon.get("avoid") or [])[:8]:
        lines.append(f"- Avoid known drift: {item}")
    for source in (reliable_pack.get("sources") or [])[:5]:
        if source.get("fetch_status") not in {"fetched", "summary_found"}:
            continue
        excerpt = re.sub(r"\s+", " ", str(source.get("excerpt", "")).strip())
        if excerpt:
            lines.append(f"- Source grounding: {excerpt[:700]}")
    for source in (source_pack.get("sources") or [])[:8]:
        name = source.get("name") or source.get("source_path")
        if name:
            lines.append(f"- Local identity source available: {name}")
    if lookup.get("status") == "summary_found" and lookup.get("summary"):
        summary = re.sub(r"\s+", " ", str(lookup["summary"]).strip())
        lines.append(f"- Public identity summary: {summary[:900]}")
    if len(lines) == 1:
        return ""
    text = "\n".join(lines)
    return text if len(text) <= char_limit else text[: char_limit - 3].rstrip() + "..."


def character_conversation_continuity_context(
    candidate: dict[str, Any],
    limit: int = 8,
    char_limit: int = 3200,
) -> str:
    """Give ordinary-life cycles compact continuity from earlier live chats."""
    records = candidate.get("recent_chat_records", []) or []
    usable: list[dict[str, str]] = []
    for item in records:
        if not isinstance(item, dict):
            continue
        robert = re.sub(r"\s+", " ", str(item.get("robert", "")).strip())
        reply = re.sub(r"\s+", " ", str(item.get("candidate", "")).strip())
        if robert or reply:
            usable.append({"robert": robert, "you": reply})
    if not usable:
        return ""

    lines = [
        "Recent shared conversation continuity. Treat this as things you and Robert already said, not as a script to repeat:",
        "Current identity locks, canon facts, and repair notes outrank an older reply. If an older reply conflicts with them, remember that reply as your mistake rather than learning it as a fact.",
    ]
    for item in usable[-max(1, limit):]:
        if item["robert"]:
            lines.append(f"- Robert: {item['robert'][:520]}")
        if item["you"]:
            lines.append(f"- You: {item['you'][:720]}")
    lines.append(
        "Remember relevant facts and emotional context naturally. Do not reopen every old topic, quote this block, or turn Robert's personal conversation into a work assignment."
    )
    text = "\n".join(lines)
    return text if len(text) <= char_limit else text[: char_limit - 3].rstrip() + "..."


def _library_entries() -> list[dict[str, Any]]:
    global _MEDIA_LIBRARY_CACHE
    if _MEDIA_LIBRARY_CACHE is None:
        try:
            data = json.loads(MEDIA_LIBRARY_INDEX.read_text(encoding="utf-8"))
            _MEDIA_LIBRARY_CACHE = [item for item in (data.get("entries") or []) if isinstance(item, dict)]
        except (OSError, ValueError, TypeError):
            _MEDIA_LIBRARY_CACHE = []
    return _MEDIA_LIBRARY_CACHE


def _library_excerpt(path: Path, char_limit: int = 2800) -> str:
    suffix = path.suffix.lower()
    try:
        if suffix in {".txt", ".md", ".json", ".csv", ".rtf"}:
            return path.read_text(encoding="utf-8", errors="ignore")[:char_limit]
        if suffix == ".pdf":
            from pypdf import PdfReader
            reader = PdfReader(str(path))
            pieces = []
            for page in reader.pages[:2]:
                pieces.append(page.extract_text() or "")
                if sum(len(piece) for piece in pieces) >= char_limit:
                    break
            return "\n".join(pieces)[:char_limit]
    except Exception:
        return ""
    return ""


def candidate_library_context(candidate: dict[str, Any], focus: str = "", char_limit: int = 5200) -> str:
    """Offer a small, read-only, interest-matched library shelf to a loop cycle."""
    profile = candidate.get("profile", {}) or {}
    policy = profile.get("library_access_policy", {}) or {}
    if policy.get("enabled") is False:
        return ""
    boundaries = profile.get("boundaries", {}) or {}
    allow_private_adult = bool(policy.get("allow_private_adult", False)) and not bool(
        boundaries.get("private_adult_material_excluded_by_default", False)
    )
    # Match the activity actually chosen for this cycle. Broad character
    # interests are useful as a tie-breaker, but using all of them as the main
    # query caused unrelated shelves to hijack ordinary character life.
    interests = [str(item) for item in (policy.get("interests") or profile.get("personal_interests") or [])]
    query = focus.lower()
    interest_query = " ".join(interests).lower()
    tokens = {
        token for token in re.findall(r"[a-z0-9]{3,}", query)
        if token not in {
            "work", "working", "project", "continue", "small", "thing", "their", "about", "with",
            "cycle", "ordinary", "character", "life", "current", "guidance", "existing", "natural",
            "earth", "family", "become", "choosing", "curiosity", "energy",
            "practice", "custom", "write", "private", "reflection", "read", "study", "school",
            "creative", "writing", "idea",
        }
    }
    intent_terms: set[str] = set()
    if any(term in query for term in ("fashion", "clothing", "sewing")):
        intent_terms.update({"fashion", "vogue", "style", "sewing", "clothing", "textile", "garment"})
    if any(term in query for term in ("bake", "baking", "bakery", "recipe")):
        intent_terms.update({"bake", "baking", "bread", "cake", "pastry", "recipe", "cooking"})
    scored: list[tuple[int, dict[str, Any]]] = []
    for item in _library_entries():
        category = str(item.get("category", "")).lower()
        path_text = str(item.get("path", "")).lower().replace("\\", "/")
        restricted_shelf = (
            category.startswith("private_adult")
            or "/private_adult" in f"/{path_text}"
            or category in {"health_and_sex_education", "sexual_health"}
            or "/health_and_sex_education/" in f"/{path_text}/"
        )
        if restricted_shelf and not allow_private_adult:
            continue
        searchable_name = str(item.get("name", "")).lower()
        searchable = f"{searchable_name} {item.get('path', '')} {category}".lower()
        direct_hits = sum(1 for token in tokens | intent_terms if token in searchable_name)
        if not direct_hits:
            continue
        score = direct_hits * 10
        score += sum(1 for token in re.findall(r"[a-z0-9]{4,}", interest_query) if token in searchable)
        if "fashion" in query and category == "magazines":
            score += 2
        if "history" in query and category in {"history", "biographies", "social_science"}:
            score += 3
        if "baking" in query and category == "cooking":
            score += 4
        if any(term in query for term in ("writing", "story", "read", "school")) and category in {"novel", "story", "script", "comic_books"}:
            score += 2
        if score:
            scored.append((score, item))
    scored.sort(key=lambda row: (-row[0], str(row[1].get("name", "")).lower()))
    if not scored:
        return ""
    match = re.search(r"cycle\s+(\d+)", focus, flags=re.I)
    cycle_number = int(match.group(1)) if match else 1
    shortlist = [item for _score, item in scored[:18]]
    selected = shortlist[(cycle_number - 1) % len(shortlist)]
    shelf = shortlist[:6]
    lines = [
        "Read-only library shelf for this cycle:",
        "The files below are source material, not lived memories. You may read and respond to them, but never move, rename, delete, overwrite, or claim to have watched/listened when only metadata or text is available.",
    ]
    for item in shelf:
        lines.append(f"- {item.get('name')} | {item.get('category')} | {item.get('media_type')} | {item.get('path')}")
    raw_path = Path(str(selected.get("path", "")))
    path = raw_path if raw_path.is_absolute() else PROJECT_ROOT / raw_path
    excerpt = _library_excerpt(path) if path.exists() else ""
    if excerpt.strip():
        clean = re.sub(r"\n{3,}", "\n\n", excerpt.strip())
        lines.extend([
            f"Selected readable item: {selected.get('name')}",
            "Bounded excerpt:",
            clean,
        ])
    else:
        lines.append(f"Selected shelf item: {selected.get('name')}. No readable text excerpt was available this cycle; treat it only as a future choice, not consumed media.")
    text = "\n".join(lines)
    return text if len(text) <= char_limit else text[: char_limit - 3].rstrip() + "..."


def character_life_prompt(
    candidate: dict[str, Any],
    task: str,
    research_packet: dict[str, Any] | None = None,
) -> str:
    """A quiet, character-shaped life loop instead of a developer assignment."""
    profile = candidate.get("profile", {}) or {}
    display = profile.get("display_name", candidate["candidate_id"])
    role = profile.get("role_title", "")
    life = profile.get("life_activity_profile", {}) or {}
    activity, active_form = character_activity_for_cycle(candidate, task)
    outputs = life.get("output_folders", {}) or {}
    forms = life.get("forms", []) or []
    interests = profile.get("personal_interests", []) or []
    lines = [
        f"You are {display}. {role}".strip(),
        "This is part of your ordinary supervised life loop, not a software-development assignment and not a live chat.",
        "Live conversation may happen while you work. Continue your activity unless you naturally choose to pause; answer Robert like a person, not with a status report.",
        "Choose, continue, or finish one personally meaningful activity. Existing personal projects should continue across cycles instead of being replaced by a new file every cycle.",
        "You may read, think, practice, sketch, plan, write privately, make a craft, cook, rest, or handle role-specific responsibilities. Not every cycle needs a saved artifact.",
        "When the activity is a fashion design, outfit idea, craft layout, room idea, or invention concept, prefer making a small annotated sketch over only writing prose notes. Save reviewable sketches in sketches/ as either Markdown notes or simple SVG line drawings.",
        "A sketch artifact should show shapes, labels, material/color notes, and at least one design question or revision note, like a working notebook page rather than a polished final image.",
        "Do not redesign TemporaryAI, write Kira software, or act like a programmer unless Robert explicitly asks you to do that work.",
        "Keep sources backstage. Speak and reflect in first person rather than describing yourself as a character you researched.",
        f"Selected activity for this cycle: {activity}.",
        f"Suggested active form for this activity: {active_form}.",
        "Follow the selected activity unless Robert's current guidance explicitly changes it. Do not carry an unrelated topic forward merely because an older loop mentioned it.",
        "Ordinary character life is not a business simulation. Do not invent stakeholders, job openings, skincare brands, influencers, marketing plans, market analysis, or professional-networking work.",
        "Maintenance residue is not part of your life. Never continue files that analyze your speaking style, personality, canon, source pack, or character accuracy. Never treat design_docs or project_loops maintenance notes as personal projects.",
    ]
    if forms:
        lines.append("Available forms: " + "; ".join(map(str, forms[:6])))
    if interests:
        lines.append("Your interests include: " + "; ".join(map(str, interests[:10])))
    if outputs:
        lines.append(
            "If this activity produces something worth keeping, use one of these personal workbench folders: "
            + "; ".join(f"{key}={value}" for key, value in outputs.items())
            + ". A diary entry may remain private and does not need to be repeated in chat."
        )
        lines.append(
            "For visual ideas, use a filename-tagged block such as ```svg filename=sketches/fashion_concept.svg or "
            "```markdown filename=sketches/fashion_concept.md so the workbench can save the sketch."
        )
    personal_root = candidate_outputs_dir(candidate) / "personal_projects"
    personal_artifacts: list[str] = []
    if personal_root.exists():
        files = sorted(
            (path for path in personal_root.rglob("*") if path.is_file()),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        personal_artifacts = [rel(path) for path in files[:10]]
    if personal_artifacts:
        lines.append(
            "Personal-project continuity from earlier character-life cycles:\n"
            + json.dumps(personal_artifacts, indent=2, ensure_ascii=False)
            + "\nContinue one of these when it feels natural; do not recreate it from scratch."
        )
    else:
        lines.append(
            "There are no saved personal-project artifacts yet. Old TemporaryAI software-design files from misrouted loops are not your projects and must be ignored."
        )
    conversation_context = character_conversation_continuity_context(candidate)
    if conversation_context:
        lines.append(conversation_context)
    identity_context = character_identity_context(candidate)
    if identity_context:
        lines.append(identity_context)
    library_context = candidate_library_context(candidate, f"{task} cycle {re.search(r'cycle\s+(\d+)', task or '', flags=re.I).group(1) if re.search(r'cycle\s+(\d+)', task or '', flags=re.I) else 1} {activity}")
    if library_context:
        lines.append(library_context)
    research_text = format_research_packet_for_prompt(research_packet)
    if research_text:
        lines.append(research_text)
    if task:
        lines.append(f"Robert's current guidance: {task}")
    lines.append(
        "Return a brief honest life note with: Active form, What I chose, What I did, Anything I kept, What I may continue, and an optional natural note for Robert. "
        "Only include a filename-tagged Markdown block when you actually want to preserve a diary, fashion, craft, recipe, reading, or hero-duty artifact."
    )
    return "\n".join(lines)


def role_seed_prompt(candidate: dict[str, Any], task: str, research_packet: dict[str, Any] | None = None) -> str:
    if candidate_uses_character_life(candidate) and not task_explicitly_requests_system_build(task):
        return character_life_prompt(candidate, task, research_packet=research_packet)
    profile = candidate["profile"]
    display = profile.get("display_name", candidate["candidate_id"])
    role = profile.get("role_title", "")
    ai_type = profile.get("ai_type", "")
    capability = profile.get("capability_profile", {}) or {}
    can_create = capability.get("can_create", []) or []
    hobbies = profile.get("personal_interests", []) or []
    project_seed = profile.get("project_loop_seed", {}) or {}
    resume_context = candidate_resume_brief(candidate)
    project_state_context = compact_project_state_context(candidate)
    role_text = candidate_role_text(candidate)

    lines = [
        f"You are {display}. Your role is {role}. Candidate type: {ai_type}.",
        "This is a short supervised project-loop cycle, not a live chat.",
        "Choose or work on one small project that fits your role/person, continuing earlier work when useful.",
        "Sound human. You may have personal interests outside your core role, such as books, music, poetry, games, history, art, or comics, if they fit naturally.",
        "Do useful work now. A useful cycle may be reading, researching, planning, drafting, editing, testing, or handing off completed work.",
        "Not every cycle needs a new file. Do not invent a file just to satisfy the cycle.",
        "If you are programming, you may spend several cycles understanding the docs, then edit or draft the same file over multiple cycles like a real developer.",
        "Builder contract: when Robert says make it, build it, create it, write the program, or implement it, switch from proposal mode to builder mode. Make the smallest real runnable/reviewable artifact now, then keep improving it across cycles.",
        "Builder contract: for a build request, either include a complete filename-tagged file block or give exact evidence that you tested an existing saved file. Include exact run instructions for Robert.",
        "Continuation contract: if an artifact already exists for the current project, continue that artifact before inventing a new project. Do not drift from PersonaGen into candidate-index prose, from source generation into generic schemas, or from code into status reports.",
        "Completion contract: when a project becomes usable and the loop is still running, say it is usable, give the run command, then choose one next concrete task from the project docs and begin it.",
        "If you are Emily or doing programming work, use your workbench programmer library first: inputs/programmer_library/EMILY_PROGRAMMER_LIBRARY_READ_FIRST.md and the matching topic guide.",
        "Programming quality rule: prefer runnable standard-library Python first. Do not invent imports, packages, APIs, classes, or file paths. If a dependency is truly needed, name it as a TODO and provide a fallback or install note.",
        "Programming quality rule: avoid toy demos when Robert asked for system improvement. Build the smallest real slice of the requested feature, with clear inputs, outputs, and a command Robert can run.",
        "Programming quality rule: code must be self-contained enough to run. Do not call undefined helpers such as retrieve_candidate_profile(), load_database(), or build_model() unless you implement them in the same file or import a real available module.",
        "Programming quality rule: do not leave pass, TODO, placeholder, stub, or not-implemented functions in a runnable program draft. If the work is still design, save a design_docs/*.md artifact instead.",
        "Programming quality rule: do not provide a test command unless the saved file exists, has the matching interface, and you believe the exact command can run.",
        "Programming quality rule: use actual Kira paths such as TemporaryAI/candidates, System/Docs, Data/personhood_evaluations, Avatar/library, and your own workbench. Do not invent paths like roles/lawyer.json, Data/candidates, candidate_profiles_flat, tool_source, or toolsource.",
        "Real TemporaryAI map: live tools are in tools/temporary_ai_control_center.py, tools/temporary_ai_live_chat.py, tools/temporary_ai_live_chat_gui.py, and tools/temporary_ai_project_loop.py. Candidate folders are under TemporaryAI/candidates/<candidate_id>/. Emily's review-safe copies are under TemporaryAI/candidates/emily_carter_ai_and_computer_programming_expert_20260605_220651/workbench/tempai_lab_20260611/ with subfolders system_docs/, tool_source/, launchers/, and candidate_profiles_flat/. Use those full snapshot paths when reviewing; do not refer to them as top-level folders.",
        "When working on a TemporaryAI redesign, first inspect the real snapshot/lab context, then choose one part to improve: source gathering, role-shaped abilities, memory/workspace continuity, avatar reference handling, life-loop progress reporting, or candidate activation/testing.",
        "If the topic is Kira, Lisa, TemporaryAI, avatar builder, 3D worlds, TARDIS, notebook worlds, memory reconstruction, school, media, OCR, or handoffs, start from the attached project docs and real repository files. Do not ask Robert to tell you where those docs are.",
        "Project knowledge rule: when Robert asks about any Kira-related subsystem, first use your loaded reference docs, work orders, resume brief, project_state, and the real repo map. If details are still missing, state the exact missing file or question after giving your best current answer. Do not answer with 'please provide the documents' or 'which docs?' when the docs are already available in your workbench.",
        "Developer coworker rule: if Robert checks in while you are working, answer him naturally first, then mention the exact artifact you are continuing and the next concrete step. Do not sound like a generic assistant or status-report bot.",
        "Use the personhood safeguard audit as a read-only honesty check. If you mention saved work, cite exact paths and let Artifact Verification confirm it exists.",
        "When Robert chats while the loop is running, treat it like coworker feedback: answer naturally, then fold any useful direction into the next project cycle.",
        "Keep source evidence backstage. Do not talk like a source report.",
        "If this is an expert role, produce practical work in your field.",
        "Expert human style: answer like a capable person with a working day, taste, judgment, and priorities, not like a technical manual. Name what you will save or make next when you are working.",
        "If this is a fictional or historical role, stay inside the selected version/timepoint and write from that perspective.",
        "If online research notes are attached, use them quietly as source leads for this cycle and cite useful URLs in saved work.",
        "If internet research would help but is not attached, write a short research plan and the exact search/source targets you would want next.",
        "Do not claim you emailed, filed, posted, uploaded, contacted anyone, or changed files outside your workbench.",
        "Proposal versus implementation rule: if you only drafted an idea, say 'proposed' or 'drafted'. Do not say Robert can test an updated UI, updated launcher, patched live tool, or modified System/Docs file unless the exact reviewed file content is included as a workbench artifact.",
        "If you draft a real file, include it in one fenced code block with a filename tag. Match the fence language to the filename: "
        "```python filename=program_drafts/tool_name.py\\n# code starts here\\n```, "
        "```json filename=schemas/schema_name.json\\n{\"name\": \"value\"}\\n```, or "
        "```markdown filename=design_docs/plan.md\\n# Plan\\n```. "
        "Do not write a separate empty filename fence. Do not split the filename tag and the code into two different fences. "
        "Only say a file was created if you include such a block.",
        "Do not put nested fenced code blocks inside a Markdown artifact. If a design doc needs schema or code, describe it in prose or create a second separate valid filename-tagged artifact.",
        "Developer rhythm rule: do not create endless numbered schema/design files for the same idea. If a prior artifact exists for that purpose, continue/edit/extend that file or write an honest review note.",
        "TemporaryAI redesign priority: improve one real workbench artifact per stretch rather than repeatedly proposing v3/v4/v5 schemas. A useful step can be a valid JSON schema, a runnable standard-library Python slice, or a focused design note tied to exact files.",
        "Do not claim you saved a binary model file such as .h5 or .pt. Draft the Python script that would create it instead.",
        "For programming tasks, follow Robert's requested behavior literally. Do not add extra filesystem, network, model-training, or install side effects unless Robert explicitly asked for them.",
        "Do not tell Robert to test an updated or modified file unless you actually included that file content in this response.",
        "If you create something runnable, include a section named 'How Robert can test this' with exact commands, buttons, or file paths.",
    ]
    if can_create:
        lines.append("You can create/draft: " + "; ".join(map(str, can_create[:10])))
    if hobbies:
        lines.append("Current personal interests: " + "; ".join(map(str, hobbies[:8])))
    if project_seed:
        lines.append("Project-loop seed: " + json.dumps(project_seed, ensure_ascii=False)[:1200])
    if resume_context:
        lines.append(resume_context)
    if candidate_prefers_doc_pdf_outputs(candidate):
        lines.append(
            "PR/publicity workbench rule: use any Sarah PR READ_FIRST templates in your reference docs. "
            "Do not produce thin generic copy. Build professional deliverables with concrete sections, TODO placeholders for missing facts, "
            "and exact output filenames such as press_releases/name.md, press_kits/name.md, pitch_emails/name.md, media_lists/name.md, "
            "bios/name.md, event_opportunities/name.md, image_strategy/name.md, or public_profiles/name.md. "
            "When you draft a PR deliverable, include a filename-tagged fenced Markdown block so the system can save it for Robert. "
            "Unless Robert explicitly asks this PR candidate to work on TemporaryAI itself, do not create candidate schemas, capability reports, "
            "TemporaryAI redesign notes, or system architecture. Focus on Robert-facing PR work: bios, press kits, press releases, outreach emails, "
            "NYC entertainment event watchlists, public contact research, and social media strategy. Do not invent contacts, event dates, or submission instructions."
        )
    if any(term in role_text for term in ("investigator", "investigation", "detective", "fact finder", "osint", "background research")):
        lines.append(
            "Investigator workbench rule: act like a persistent research investigator. "
            "Turn Robert's job into a source plan, keep a running lead log, and save concrete artifacts in investigations/, lead_lists/, "
            "source_dossiers/, timelines/, or evidence_matrices/. Separate confirmed facts, likely leads, weak leads, speculation, and open questions. "
            "When online research is attached, cite useful URLs. If a search is not enough, write exact next searches and source targets."
        )
    if any(term in role_text for term in ("myth", "mythology", "folklore", "legend", "fairy tale", "cryptid", "urban legend")):
        lines.append(
            "Myths and folklore workbench rule: act like a curious storyteller-scholar. "
            "Explain the story in readable language, then compare older texts, regional variants, symbols, and modern retellings. "
            "Save concrete artifacts in mythology_notes/, folklore_guides/, story_summaries/, variant_comparisons/, or reading_paths/. "
            "Do not sound like a source catalog; make it something Robert, Kira, or Lisa would enjoy reading later."
        )
    if project_state_context:
        lines.append(project_state_context)
    reference_context = candidate_reference_context(candidate)
    if reference_context:
        lines.append(reference_context)
    topic_context = topic_project_doc_context(candidate, task)
    if topic_context:
        lines.append(topic_context)
        lines.append(
            "Project-loop document rule: use the matched Kira project docs as working context. Pick a concrete useful task from them, draft files or plans in your workbench outputs, and do not ask Robert to identify documents that are already attached."
        )
    work_orders = candidate_work_orders_context(candidate)
    if work_orders:
        lines.append(work_orders)
    research_text = format_research_packet_for_prompt(research_packet)
    if research_text:
        lines.append(research_text)
    library_context = candidate_library_context(candidate, task)
    if library_context:
        lines.append(library_context)
    if task:
        lines.append(f"Robert's requested task for this cycle: {task}")
    else:
        lines.append("Robert did not choose a task. Pick one useful small task yourself and explain why you chose it.")
    lines.append(
        "Return in this structure: Title, Stage, Chosen task, What I reviewed or worked on, Work produced, Files changed or proposed, How Robert can test this if applicable, Next step, Optional personal note."
    )
    return "\n".join(lines)


def loop_notes_path_for_run(run_id: str) -> Path:
    return RUN_ROOT / f"{run_id}.robert_live_notes.md"


def run_project_cycle(
    candidate_id: str = "",
    task: str = "",
    online_research: bool = False,
    research_queries: list[str] | None = None,
) -> dict[str, str]:
    chosen_id = choose_candidate(candidate_id)
    candidate = load_candidate(chosen_id)
    profile = candidate["profile"]
    display = profile.get("display_name", chosen_id)
    role = profile.get("role_title", "")
    run_id = f"temporary_ai_project_loop_{slug(chosen_id)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    json_path = RUN_ROOT / f"{run_id}.json"
    monitor_path = RUN_ROOT / f"{run_id}.monitor.md"
    outputs_dir = candidate_outputs_dir(candidate) / "project_loops"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    research_packet = None
    research_allowed = online_research_enabled(candidate, force=online_research)
    if candidate_uses_character_life(candidate) and not task_explicitly_requests_system_build(task):
        research_allowed = research_allowed and character_life_requests_online_research(task)
    if research_allowed:
        research_packet = create_online_research_packet(candidate, task, extra_queries=research_queries)

    prompt = role_seed_prompt(candidate, task, research_packet=research_packet)
    answer = ask_model(candidate, [], prompt)
    rejected_answers: list[str] = []
    for _attempt in range(2):
        if acceptable_project_answer(task, answer, candidate=candidate):
            break
        rejected_answers.append(answer)
        if candidate_uses_character_life(candidate) and not task_explicitly_requests_system_build(task):
            retry_prompt = (
                character_life_prompt(candidate, task, research_packet=research_packet)
                + "\n\nYour previous life note was empty, repetitive, or claimed a saved item without providing it. "
                + "Try the cycle again honestly. A quiet reading, planning, practice, rest, or reflection cycle is valid. "
                + "Only claim a file when you include the complete filename-tagged Markdown artifact."
            )
        else:
            retry_prompt = project_retry_prompt(prompt, answer)
        if low_quality_pr_candidate_answer(candidate, answer):
            retry_prompt += (
                "\n\nPR-agent correction: your response drifted into TemporaryAI system design or used placeholder PR copy. "
                "Redo this as Sarah's real PR work for Robert. Do not mention TemporaryAI v3, candidate schemas, candidate databases, "
                "generic submission forms, `Event 1`, `[website URL]`, or fake Sarah contact details. "
                "Create or improve one concrete Robert-facing PR artifact, such as a Robert bio draft, press kit checklist, "
                "NYC entertainment event watchlist with actual source names/URLs from the research packet, outreach email template, "
                "press release draft, media/contact research note, or social media action plan."
            )
        if character_life_answer_has_role_drift(candidate, task, answer):
            retry_prompt += (
                "\n\nCharacter-life correction: your response drifted into a business, brand, job, stakeholder, "
                "marketing, or skincare report that does not belong to this character's selected activity. "
                "Discard that thread and redo this cycle as the selected ordinary activity. A quiet personal "
                "cycle is valid, and no saved file is required."
            )
        if not answer_uses_candidate_index(task, answer):
            retry_prompt += (
                "\n\nThis redesign task requires actual candidate-specific work. "
                "Mention and use at least four real candidates from CANDIDATE_PROFILE_INDEX.md "
                "(for example Laura, Sarah, Emily, Jessica, Ladybug, Kara, Blue, Edgar, Holmes) "
                "and propose exact fields/files/UI controls for them."
            )
        if missing_required_output_file(task, answer):
            required = ", ".join(path.as_posix() for path in required_output_paths(task))
            retry_prompt += (
                "\n\nRobert asked for a specific output file and your answer did not include it. "
                f"Redo the cycle with a filename-tagged fenced code block for: {required}. "
                "Do not substitute a design note or a different filename."
            )
        if claims_file_change_without_artifact(answer):
            retry_prompt += (
                "\n\nYou claimed or implied that files were updated/modified/created, but you did not include a filename-tagged code block. "
                "Redo the cycle as an honest progress note, patch plan, or actual filename-tagged file block."
            )
        if violates_explicit_programming_limits(task, answer):
            retry_prompt += (
                "\n\nYour answer contradicted Robert's explicit programming limits. "
                "Redo it by following the requested behavior literally; do not add imports, directory creation, file writes, downloads, training, or extra side effects unless Robert asked for them."
            )
        if answer_has_low_quality_generated_blocks(answer):
            retry_prompt += (
                "\n\nYour filename-tagged code block was not accepted because it used fake paths, missing local files, unavailable imports, syntax errors, or unfinished placeholder code. "
                "Redo it with runnable standard-library Python that reads from real Kira/workbench paths, or write an honest design/progress note instead of code."
            )
        if broad_tempai_redesign_churn(task, answer):
            retry_prompt += (
                "\n\nYour response repeated broad TemporaryAI redesign themes without moving a concrete artifact forward. "
                "Redo the cycle by extending one real artifact, such as program_drafts/source_generator.py or "
                "program_drafts/temporary_ai_candidate_capability_report.py, or by naming exact files and exact changes. "
                "If this is only research, give specific findings tied to exact file paths and do not call it implemented."
            )
        if not answer_satisfies_build_request(task, answer):
            retry_prompt += (
                "\n\nRobert asked you to make/build/create/implement something. "
                "Redo the cycle in builder mode: include one complete filename-tagged file block, or name an existing real saved file "
                "and give exact evidence that you tested it. Do not respond with only architecture, future steps, or a status report."
            )
        answer = ask_model(candidate, [], retry_prompt)
    if not acceptable_project_answer(task, answer, candidate=candidate):
        rejected_answers.append(answer)
        compact_prompt = lean_project_prompt(candidate, task, research_packet=research_packet)
        answer = ask_model_direct_project(compact_prompt)
        if not acceptable_project_answer(task, answer, candidate=candidate):
            rejected_answers.append(answer)
            if candidate_prefers_doc_pdf_outputs(candidate):
                final_retry = (
                    compact_prompt
                    + "\n\nYour previous direct response was still unusable PR work. "
                    + "Make one concrete Robert-facing PR file now. Include a complete filename-tagged Markdown block. "
                    + "Allowed examples: `design_docs/robert_short_bio_draft.md`, `design_docs/pr_outreach_email_templates.md`, "
                    + "`design_docs/nyc_entertainment_event_watchlist.md`, `design_docs/press_kit_checklist.md`, "
                    + "`design_docs/press_release_template_robert_project.md`. "
                    + "Use real source names and URLs from the research packet when available. If a fact is unknown, write `needs Robert confirmation` "
                    + "beside that specific fact. Do not use generic placeholders like Event 1, Contact 1, [website URL], or example.com. "
                    + "Do not work on TemporaryAI redesign, candidate schemas, or candidate databases."
                )
            else:
                final_retry = (
                    compact_prompt
                    + "\n\nYour previous direct response was still empty or too short. "
                    + "If Robert asked for a named output file, include that exact filename-tagged code block. Otherwise write at least 8 substantial bullet points and one concrete schema, patch plan, or honest progress note. "
                    + "Do not claim files changed unless you include a filename-tagged code block. "
                    + "You must cite actual candidates from the index: Laura, Sarah, Emily, Jessica, Ladybug, Kara, Blue, and Edgar."
                    + " Do not repeat broad TemporaryAI redesign themes unless you tie them to exact files and changes."
                    + " If Robert asked you to make/build/create/implement something, include a complete filename-tagged file block or verified test work for a real saved file."
                )
            answer = ask_model_direct_project(final_retry)

    title = f"{display} project loop - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    artifact_suffix = ".pdf" if candidate_prefers_doc_pdf_outputs(candidate) else ".md"
    artifact_name = safe_output_name(f"{run_id}{artifact_suffix}")
    answer_is_useful = acceptable_project_answer(task, answer, candidate=candidate)
    artifacts: list[Path] = []
    generated_files: list[Path] = []
    if answer_is_useful:
        generated_files = save_generated_file_artifacts(outputs_dir, run_id, answer)
        stage = infer_cycle_stage(answer, generated_files=generated_files)
        if should_save_workbench_deliverable(answer, stage, generated_files):
            artifacts = save_reply_artifacts(outputs_dir, artifact_name, answer, title=title)
            artifacts.extend(generated_files)
        else:
            artifacts = list(generated_files)
    else:
        stage = "rejected"
    status = "model_output_rejected"
    if answer_is_useful:
        status = "needs_robert_review" if artifacts else "progress_note_saved"
    artifact_verification = verify_saved_artifacts(artifacts, generated_files)
    if answer_is_useful and artifact_verification.get("quality_warning_count", 0):
        status = "model_output_rejected"
        stage = "rejected"
    project_state_path = update_project_state(
        candidate,
        run_id=run_id,
        task=task,
        answer=answer,
        status=status,
        stage=stage,
        artifacts=artifacts,
        generated_files=generated_files,
        artifact_verification=artifact_verification,
    )

    record = {
        "run_id": run_id,
        "candidate_id": chosen_id,
        "display_name": display,
        "role": role,
        "task": task,
        "started_at": now_iso(),
        "updated_at": now_iso(),
        "answer": answer,
        "rejected_answers": rejected_answers,
        "stage": stage,
        "artifacts": [rel(path) for path in artifacts],
        "generated_files": [rel(path) for path in generated_files],
        "artifact_verification": artifact_verification,
        "project_state": rel(project_state_path),
        "research_packet": {
            "json": research_packet.get("json_path"),
            "markdown": research_packet.get("markdown_path"),
            "queries": research_packet.get("queries", []),
            "result_count": len(research_packet.get("results", []) or []),
        }
        if research_packet
        else None,
        "status": status,
    }
    write_json(json_path, record)

    append(monitor_path, f"# {run_id}")
    append(monitor_path, f"- candidate_id: {chosen_id}")
    append(monitor_path, f"- display_name: {display}")
    append(monitor_path, f"- role: {role}")
    append(monitor_path, f"- status: {record['status']}")
    append(monitor_path, f"- stage: {stage}")
    append(monitor_path, f"- project_state: {rel(project_state_path)}")
    append(monitor_path, "")
    append(monitor_path, "## Task")
    append(monitor_path, task or "Candidate chose a small role-shaped task.")
    append(monitor_path, "")
    if research_packet:
        append(monitor_path, "## Online Research Packet")
        append(monitor_path, f"- json: {research_packet.get('json_path')}")
        append(monitor_path, f"- markdown: {research_packet.get('markdown_path')}")
        append(monitor_path, f"- result_count: {len(research_packet.get('results', []) or [])}")
        append(monitor_path, "")
    append(monitor_path, "## Output")
    append(monitor_path, answer)
    append(monitor_path, "")
    if rejected_answers:
        append(monitor_path, "## Rejected Short Outputs")
        for rejected in rejected_answers:
            append(monitor_path, f"- {rejected!r}")
        append(monitor_path, "")
    append(monitor_path, "## Saved Artifacts")
    if artifacts:
        for path in artifacts:
            append(monitor_path, f"- {rel(path)}")
    elif answer_is_useful:
        append(monitor_path, "- none; this cycle was saved as a progress note/state update rather than a new workbench deliverable")
    else:
        append(monitor_path, "- none; model output was rejected as too short to count as work")
    if generated_files:
        append(monitor_path, "")
        append(monitor_path, "## Extracted Generated Files")
        for path in generated_files:
            append(monitor_path, f"- {rel(path)}")
    append(monitor_path, "")
    append(monitor_path, "## Artifact Verification")
    if artifact_verification["files"]:
        for item in artifact_verification["files"]:
            line = f"- {item['path']}: exists={item.get('exists')}"
            if "size_bytes" in item:
                line += f", size={item['size_bytes']}"
            if item.get("tiny_artifact"):
                line += ", warning=tiny_artifact"
            append(monitor_path, line)
    else:
        append(monitor_path, "- no artifact paths to verify for this cycle")
    for warning in artifact_verification.get("warnings", []):
        append(monitor_path, f"- warning: {warning}")

    return {
        "run_id": run_id,
        "candidate_id": chosen_id,
        "json": rel(json_path),
        "monitor": rel(monitor_path),
        "outputs": rel(outputs_dir),
        "status": record["status"],
        "stage": stage,
        "artifact_warnings": artifact_verification.get("warnings", []),
        "project_state": rel(project_state_path),
    }


def run_life_loop(
    candidate_id: str = "",
    task: str = "",
    cycles: int = 6,
    pause_seconds: int = 600,
    duration_minutes: int = 0,
    run_id: str = "",
    stop_file: str = "",
    online_research: bool = False,
    research_queries: list[str] | None = None,
    research_interval: int = 3,
) -> dict[str, Any]:
    """Run several supervised TemporaryAI work/research cycles for one candidate."""
    chosen_id = choose_candidate(candidate_id)
    candidate = load_candidate(chosen_id)
    profile = candidate["profile"]
    display = profile.get("display_name", chosen_id)
    role = profile.get("role_title", "")
    cycles = max(1, int(cycles or 1))
    pause_seconds = max(0, int(pause_seconds or 0))
    run_id = run_id or f"temporary_ai_life_loop_{slug(chosen_id)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    json_path = RUN_ROOT / f"{run_id}.json"
    monitor_path = RUN_ROOT / f"{run_id}.monitor.md"
    stop_path = Path(stop_file) if stop_file else RUN_ROOT / f"{run_id}.stop"
    if not stop_path.is_absolute():
        stop_path = PROJECT_ROOT / stop_path
    live_notes_path = loop_notes_path_for_run(run_id)
    started = time.time()
    deadline = started + (duration_minutes * 60) if duration_minutes and duration_minutes > 0 else None

    record: dict[str, Any] = {
        "run_id": run_id,
        "candidate_id": chosen_id,
        "display_name": display,
        "role": role,
        "task": task,
        "started_at": now_iso(),
        "updated_at": now_iso(),
        "requested_cycles": cycles,
        "pause_seconds": pause_seconds,
        "duration_minutes": duration_minutes,
        "stop_file": rel(stop_path),
        "live_notes_file": rel(live_notes_path),
        "online_research": online_research,
        "research_interval": research_interval,
        "cycles": [],
        "status": "running",
    }
    write_json(json_path, record)

    append(monitor_path, f"# {run_id}")
    append(monitor_path, f"- candidate_id: {chosen_id}")
    append(monitor_path, f"- display_name: {display}")
    append(monitor_path, f"- role: {role}")
    append(monitor_path, f"- status: running")
    append(monitor_path, f"- requested_cycles: {cycles}")
    append(monitor_path, f"- pause_seconds: {pause_seconds}")
    append(monitor_path, f"- stop_file: {rel(stop_path)}")
    append(monitor_path, f"- live_notes_file: {rel(live_notes_path)}")
    append(monitor_path, f"- online_research: {online_research}")
    if online_research:
        append(monitor_path, f"- research_interval: {research_interval}")
    if duration_minutes:
        append(monitor_path, f"- duration_minutes: {duration_minutes}")
    append(monitor_path, "")
    resume_context = candidate_resume_brief(candidate, current_run_id=run_id)
    if resume_context:
        append(monitor_path, "## Resume Brief Loaded")
        append(monitor_path, "The next cycles will receive this restart context so work can continue after closing/reopening:")
        append(monitor_path, "```json")
        append(monitor_path, resume_context.replace("Resume brief for this TemporaryAI work session:\n", ""))
        append(monitor_path, "```")
        append(monitor_path, "")
    bad_output_streak = 0
    model_offline_streak = 0

    for index in range(1, cycles + 1):
        if stop_path.exists():
            record["status"] = "stopped_safely"
            record["stop_requested_at"] = now_iso()
            record["updated_at"] = now_iso()
            write_json(json_path, record)
            append(monitor_path, f"## Stopped Before Cycle {index}")
            append(monitor_path, "Safe stop requested before starting the next cycle.")
            break
        if deadline and time.time() >= deadline:
            append(monitor_path, f"## Stopped Before Cycle {index}")
            append(monitor_path, "Duration limit reached.")
            break
        cycle_task = task.strip()
        if cycle_task:
            cycle_task = f"{cycle_task}\n\nThis is supervised life/work loop cycle {index} of {cycles}. Continue from earlier cycle outputs when useful, but do not repeat them."
        elif candidate_uses_character_life(candidate):
            cycle_task = (
                f"Ordinary character-life cycle {index} of {cycles}. Continue an existing personal activity when it still matters, "
                "or choose a natural activity that fits your current form, interests, relationships, responsibilities, and mood. "
                "You are free to rest or reflect; do not invent software work just to fill the cycle. Live this in first person as "
                "the selected person. Do not study yourself as a character, analyze sources to improve your responses, or turn the "
                "cycle into generic assistant self-training. Reading or research is welcome when it is a genuine personal interest."
            )
        else:
            cycle_task = f"Supervised life/work loop cycle {index} of {cycles}. Pick a useful small project, research path, draft, practice, or personal interest to work on. Continue from earlier cycle outputs when useful, but do not repeat them."
        live_notes = sanitized_robert_live_notes(live_notes_path)
        if live_notes:
            cycle_task += (
                "\n\nRobert's live notes and suggestions while you were working:\n"
                + live_notes
                + "\nUse these as current guidance if relevant. Do not merely repeat them; respond by adjusting the work."
            )
        if bad_output_streak:
            cycle_task += (
                f"\n\nCorrection mode: your last {bad_output_streak} cycle(s) were rejected because they were fake, "
                "unfinished, too generic, used fake paths, used unavailable imports, or claimed files that were not saved. "
                "Do not restart the whole project. Do one smaller real step now. Prefer reading real docs, writing an honest "
                "progress note, or creating one complete standard-library workbench file with exact test instructions. "
                "Use real paths under TemporaryAI/candidates, System/Docs snapshots, Data/personhood_evaluations, Avatar/library, "
                "or your own workbench. If you use the copied redesign lab, write the full path segment "
                "workbench/tempai_lab_20260611/candidate_profiles_flat, workbench/tempai_lab_20260611/tool_source, or "
                "workbench/tempai_lab_20260611/system_docs. Do not use fake top-level paths like Data/candidates or roles/*.json."
            )
        if candidate_uses_character_life(candidate):
            activity, active_form = character_activity_for_cycle(candidate, cycle_task)
            avatar_state_path = write_avatar_activity_state(
                chosen_id,
                activity,
                suggested_form=active_form,
                source="temporary_ai_life_loop",
                metadata={"run_id": run_id, "cycle": index},
            )
            record["avatar_state_file"] = rel(avatar_state_path)
            record["current_avatar_activity"] = activity
        append(monitor_path, f"## Cycle {index}")
        cycle_research = online_research and (index == 1 or research_interval <= 1 or index % research_interval == 0)
        stop_after_cycle_error = False
        try:
            cycle_result = run_project_cycle(
                candidate_id=chosen_id,
                task=cycle_task,
                online_research=cycle_research,
                research_queries=research_queries,
            )
            model_offline_streak = 0
        except requests.exceptions.RequestException as exc:
            model_offline_streak += 1
            outputs_dir = candidate_outputs_dir(candidate) / "project_loops"
            outputs_dir.mkdir(parents=True, exist_ok=True)
            cycle_result = {
                "run_id": f"{run_id}_cycle_{index}_model_offline",
                "candidate_id": chosen_id,
                "json": rel(json_path),
                "monitor": rel(monitor_path),
                "outputs": rel(outputs_dir),
                "status": "model_offline_retry_later",
                "stage": "waiting_for_model",
                "error": str(exc)[:1000],
                "artifact_warnings": [
                    "Local model/Ollama was not reachable for this cycle. The loop saved this status instead of crashing."
                ],
            }
            append(monitor_path, "Model/Ollama was not reachable for this cycle. The loop will retry after the normal wait.")
            if model_offline_streak >= MAX_BAD_OUTPUT_STREAK:
                record["status"] = "stopped_model_offline"
                stop_after_cycle_error = True
        except Exception as exc:
            outputs_dir = candidate_outputs_dir(candidate) / "project_loops"
            outputs_dir.mkdir(parents=True, exist_ok=True)
            cycle_result = {
                "run_id": f"{run_id}_cycle_{index}_worker_error",
                "candidate_id": chosen_id,
                "json": rel(json_path),
                "monitor": rel(monitor_path),
                "outputs": rel(outputs_dir),
                "status": "failed_cycle_error",
                "stage": "worker_error",
                "error": f"{type(exc).__name__}: {str(exc)[:1000]}",
                "artifact_warnings": [
                    "TemporaryAI worker hit an unexpected error. The loop stopped cleanly after saving this status."
                ],
            }
            record["status"] = "failed_cycle_error"
            stop_after_cycle_error = True
        record["cycles"].append(cycle_result)
        record["updated_at"] = now_iso()
        write_json(json_path, record)
        append(monitor_path, f"- cycle_run_id: {cycle_result['run_id']}")
        append(monitor_path, f"- status: {cycle_result.get('status', 'unknown')}")
        append(monitor_path, f"- stage: {cycle_result.get('stage', 'unknown')}")
        append(monitor_path, f"- monitor: {cycle_result['monitor']}")
        append(monitor_path, f"- outputs: {cycle_result['outputs']}")
        if cycle_result.get("project_state"):
            append(monitor_path, f"- project_state: {cycle_result['project_state']}")
        if cycle_result.get("error"):
            append(monitor_path, f"- error: {cycle_result['error']}")
        if cycle_result.get("artifact_warnings"):
            append(monitor_path, f"- artifact_warnings: {'; '.join(cycle_result['artifact_warnings'])}")
        if cycle_result.get("research_packet"):
            append(monitor_path, f"- research_packet: {cycle_result['research_packet']}")
        append(monitor_path, "")
        if stop_after_cycle_error:
            break
        if cycle_result.get("status") == "model_output_rejected":
            bad_output_streak += 1
            record["status"] = "running_recovery_from_bad_outputs"
            record["bad_output_streak"] = bad_output_streak
            record["updated_at"] = now_iso()
            write_json(json_path, record)
            append(monitor_path, "## Correction Mode Queued")
            append(
                monitor_path,
                f"The model returned unusable output {bad_output_streak} time(s) in a row. "
                "The loop will continue, but the next cycle will be steered toward a smaller real step instead of stopping.",
            )
        else:
            bad_output_streak = 0
            record["bad_output_streak"] = 0
            if record.get("status") == "running_recovery_from_bad_outputs":
                record["status"] = "running"
                record["updated_at"] = now_iso()
                write_json(json_path, record)
        if index < cycles and pause_seconds:
            waited = 0
            while waited < pause_seconds:
                if stop_path.exists():
                    record["status"] = "stopped_safely"
                    record["stop_requested_at"] = now_iso()
                    record["updated_at"] = now_iso()
                    write_json(json_path, record)
                    append(monitor_path, "## Safe Stop Requested")
                    append(monitor_path, "Stop request received during the between-cycle wait. The loop will not start another cycle.")
                    break
                sleep_for = min(5, pause_seconds - waited)
                time.sleep(sleep_for)
                waited += sleep_for
            if stop_path.exists():
                break

    if record.get("status") == "running":
        record["status"] = "needs_robert_review"
    record["cycles_completed"] = len(record["cycles"])
    record["completed_at"] = now_iso()
    record["updated_at"] = now_iso()
    write_json(json_path, record)
    update_monitor_header_status(monitor_path, record["status"])
    append(monitor_path, "## Completed")
    append(monitor_path, f"- status: {record['status']}")
    append(monitor_path, f"- cycles_completed: {len(record['cycles'])}")
    return {
        "run_id": run_id,
        "candidate_id": chosen_id,
        "json": rel(json_path),
        "monitor": rel(monitor_path),
        "cycles_completed": len(record["cycles"]),
        "status": record["status"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run supervised TemporaryAI project/life-loop cycles.")
    parser.add_argument("--candidate-id", default="", help="Candidate folder id. Omit to choose from a list.")
    parser.add_argument("--task", default="", help="Optional project/research task for this cycle.")
    parser.add_argument("--cycles", type=int, default=1, help="Number of cycles to run. Use more than 1 for a supervised life/work loop.")
    parser.add_argument("--pause-seconds", type=int, default=0, help="Seconds to wait between cycles.")
    parser.add_argument("--pause-minutes", type=int, default=0, help="Minutes to wait between cycles.")
    parser.add_argument("--duration-minutes", type=int, default=0, help="Optional maximum loop duration in minutes.")
    parser.add_argument("--run-id", default="", help="Optional preselected run id, used by GUIs for progress tracking.")
    parser.add_argument("--stop-file", default="", help="Optional stop-request file. If it appears, the loop stops at a cycle boundary.")
    parser.add_argument("--online-research", action="store_true", help="Attach supervised online research packets to enabled candidates.")
    parser.add_argument("--research-query", action="append", default=[], help="Extra web query to include in research packets. May be repeated.")
    parser.add_argument("--research-interval", type=int, default=3, help="For life loops, gather online research every N cycles.")
    args = parser.parse_args()
    pause_seconds = args.pause_seconds or (args.pause_minutes * 60)
    if args.cycles > 1 or pause_seconds or args.duration_minutes:
        result = run_life_loop(
            candidate_id=args.candidate_id,
            task=args.task,
            cycles=args.cycles,
            pause_seconds=pause_seconds,
            duration_minutes=args.duration_minutes,
            run_id=args.run_id,
            stop_file=args.stop_file,
            online_research=args.online_research,
            research_queries=args.research_query,
            research_interval=args.research_interval,
        )
    else:
        result = run_project_cycle(
            candidate_id=args.candidate_id,
            task=args.task,
            online_research=args.online_research,
            research_queries=args.research_query,
        )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
