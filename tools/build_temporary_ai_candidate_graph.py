"""Build a compact TemporaryAI candidate knowledge graph.

This is a dependency-free index for Robert, Kira, Lisa, and TemporaryAI
work loops. It does not activate candidates or edit candidate profiles.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_ROOT = PROJECT_ROOT / "TemporaryAI" / "candidates"
OUT_JSON = PROJECT_ROOT / "Data" / "temporary_ai_instances" / "candidate_knowledge_graph.json"
OUT_MD = PROJECT_ROOT / "TemporaryAI" / "docs" / "CANDIDATE_KNOWLEDGE_GRAPH.md"


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return default


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def rel(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def text_blob(*values: Any) -> str:
    chunks: list[str] = []
    for value in values:
        if isinstance(value, str):
            chunks.append(value)
        elif isinstance(value, dict):
            chunks.append(json.dumps(value, ensure_ascii=False))
        elif isinstance(value, list):
            chunks.extend(str(item) for item in value)
    return " ".join(chunks).lower()


def clean_summary(value: Any, max_chars: int = 240) -> str:
    text = str(value or "")
    text = text.replace("```", " ")
    text = " ".join(text.split())
    return text[:max_chars].rstrip()


def infer_abilities(profile: dict[str, Any], creation: dict[str, Any]) -> list[dict[str, str]]:
    knowledge_plan = profile.get("knowledge_plan") or {}
    capability_profile = profile.get("capability_profile") or {}
    creation_input = creation.get("input") if isinstance(creation.get("input"), dict) else {}
    focused_creation = {
        "display_name_or_role": creation.get("display_name_or_role"),
        "role_title": creation.get("role_title"),
        "ui_category": creation.get("ui_category"),
        "ai_type": creation.get("ai_type"),
        "query_or_domain": creation_input.get("query_or_domain"),
        "version_or_life_point": creation_input.get("version_life_point_or_canon_point"),
        "personality_notes": creation_input.get("personality_notes"),
    }
    focused_profile = {
        "display_name": profile.get("display_name"),
        "role_title": profile.get("role_title"),
        "ai_type": profile.get("ai_type"),
        "ui_category": profile.get("ui_category"),
        "personality_notes": profile.get("personality_notes"),
        "knowledge_focus": knowledge_plan.get("focus") if isinstance(knowledge_plan, dict) else "",
        "capability_summary": capability_profile.get("summary") if isinstance(capability_profile, dict) else "",
        "can_create": capability_profile.get("can_create") if isinstance(capability_profile, dict) else [],
        "personal_interests": profile.get("personal_interests"),
    }
    blob = text_blob(focused_profile, focused_creation)
    rules = [
        (
            "programming",
            ("program", "software", "code", "computer", "ai and computer", "developer"),
            "Can inspect copied code, draft runnable programs, propose tests, and write patch plans inside a workbench.",
        ),
        (
            "legal_casework",
            ("lawyer", "attorney", "criminal", "legal", "case file"),
            "Can organize reviewed case material, summarize facts, draft questions, and prepare game-plan documents for Robert review.",
        ),
        (
            "public_relations",
            ("pr agent", "public relations", "press", "media outlet", "entertainment pr"),
            "Can maintain press-kit material, draft bios/releases/emails, and track entertainment outlets or event leads.",
        ),
        (
            "robotics_design",
            ("robotics", "robotic", "mechanical", "stl", "3d print", "body design"),
            "Can plan robot/body parts, shopping lists, STL-oriented design briefs, and collaboration tasks for programmer AIs.",
        ),
        (
            "fictional_reconstruction",
            ("fictional", "character", "canon", "supergirl", "ladybug", "spider", "skynet", "terminator"),
            "Can roleplay a reviewed fictional reconstruction from source packs, while avoiding unsupported invented details.",
        ),
        (
            "historical_reconstruction",
            ("historical", "edgar cayce", "holmes", "president", "life point"),
            "Can roleplay a reviewed historical reconstruction anchored to a selected life point and sources.",
        ),
        (
            "creative_work",
            ("writer", "artist", "music", "poetry", "painting", "book", "story"),
            "Can draft creative artifacts, talk about craft, and save project notes in the workbench.",
        ),
        (
            "avatar_reference",
            ("avatar", "body", "image reference", "3d world", "tardis"),
            "Can help plan avatar/world assets using approved private reference libraries and copied project docs.",
        ),
    ]
    abilities: list[dict[str, str]] = []
    for ability_id, triggers, summary in rules:
        if any(trigger in blob for trigger in triggers):
            abilities.append({"id": ability_id, "summary": summary})
    if not abilities:
        abilities.append(
            {
                "id": "general_conversation",
                "summary": "Can hold reviewed temporary conversations using candidate profile and source-pack context.",
            }
        )
    return abilities


def source_summary(candidate_dir: Path, profile: dict[str, Any]) -> dict[str, Any]:
    source_pack = read_json(candidate_dir / "reliable_source_pack.json", default={}) or {}
    grounding = read_json(candidate_dir / "source_grounding_review.json", default={}) or {}
    queue = read_json(candidate_dir / "source_research_queue.json", default={}) or {}
    online = profile.get("online_preview_lookup") or {}
    sources = source_pack.get("sources") or source_pack.get("reliable_sources") or []
    if isinstance(sources, dict):
        source_count = len(sources)
    elif isinstance(sources, list):
        source_count = len(sources)
    else:
        source_count = 0
    identity = grounding.get("identity_binding") if isinstance(grounding.get("identity_binding"), dict) else {}
    activation = grounding.get("activation") if isinstance(grounding.get("activation"), dict) else {}
    unresolved_choices = identity.get("unresolved_owner_choices", []) if isinstance(identity, dict) else []
    if not isinstance(unresolved_choices, list):
        unresolved_choices = ["invalid source-grounding unresolved-owner-choice field"]
    return {
        "online_preview_status": online.get("status", ""),
        "online_preview_url": online.get("url", ""),
        "source_pack_status": source_pack.get("status", ""),
        "source_count": source_count,
        "research_queue_status": queue.get("status", ""),
        "grounding_review_status": grounding.get("review_status", ""),
        "grounding_identity_status": identity.get("status", "") if isinstance(identity, dict) else "",
        "grounding_runtime_activation_allowed": activation.get("runtime_activation_allowed") if grounding else None,
        "grounding_source_gap_count": len(grounding.get("source_gaps", []) or []) if grounding else 0,
        "grounding_unresolved_owner_choices": unresolved_choices,
        "needs_clarification": bool(
            "clarification" in str(profile.get("activation_policy", "")).lower()
            or "clarification" in str(queue.get("status", "")).lower()
            or "needs clarification" in str(source_pack).lower()
            or unresolved_choices
        ),
    }


def workbench_summary(candidate_dir: Path, profile: dict[str, Any]) -> dict[str, Any]:
    workbench = candidate_dir / "workbench"
    outputs = workbench / "outputs"
    project_state = read_json(outputs / "project_state.json", default={}) or {}
    generated_files = []
    if outputs.exists():
        for path in outputs.rglob("*"):
            if path.is_file() and path.suffix.lower() in {".py", ".md", ".json", ".txt", ".bat", ".html"}:
                generated_files.append(rel(path))
                if len(generated_files) >= 12:
                    break
    return {
        "workbench": rel(workbench) if workbench.exists() else "",
        "outputs": rel(outputs) if outputs.exists() else "",
        "project_state": {
            "current_project": clean_summary(project_state.get("current_project")),
            "stage": clean_summary(project_state.get("stage")),
            "cycles_completed": project_state.get("cycles_completed"),
            "last_artifacts": (project_state.get("last_artifacts") or [])[-5:],
            "next_step": clean_summary(project_state.get("next_step")),
        },
        "sample_outputs": generated_files,
    }


def build_graph() -> dict[str, Any]:
    candidate_nodes: list[dict[str, Any]] = []
    ability_nodes: dict[str, dict[str, str]] = {}
    edges: list[dict[str, str]] = []

    for candidate_dir in sorted(CANDIDATE_ROOT.iterdir() if CANDIDATE_ROOT.exists() else []):
        if not candidate_dir.is_dir():
            continue
        profile_path = candidate_dir / "temporary_ai_profile.json"
        profile = read_json(profile_path, default={}) or {}
        creation = read_json(candidate_dir / "creation_request.json", default={}) or {}
        candidate_id = profile.get("candidate_id") or candidate_dir.name
        display_name = profile.get("display_name") or creation.get("display_name") or candidate_dir.name
        role_title = profile.get("role_title") or creation.get("role_title") or ""
        abilities = infer_abilities(profile, creation)
        for ability in abilities:
            ability_nodes[ability["id"]] = {
                "id": f"ability:{ability['id']}",
                "type": "ability",
                "label": ability["id"].replace("_", " ").title(),
                "summary": ability["summary"],
            }
            edges.append({"source": candidate_id, "target": f"ability:{ability['id']}", "type": "has_ability"})

        candidate_nodes.append(
            {
                "id": candidate_id,
                "type": "candidate",
                "display_name": display_name,
                "role_title": role_title,
                "ai_type": profile.get("ai_type", ""),
                "ui_category": profile.get("ui_category", ""),
                "status": profile.get("status", ""),
                "activation_status": (profile.get("activation_policy") or {}).get("current_status", ""),
                "profile": rel(profile_path) if profile_path.exists() else "",
                "candidate_dir": rel(candidate_dir),
                "abilities": abilities,
                "source_summary": source_summary(candidate_dir, profile),
                "workbench_summary": workbench_summary(candidate_dir, profile),
            }
        )

    return {
        "graph_id": "temporary_ai_candidate_knowledge_graph_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": rel(CANDIDATE_ROOT),
        "summary": {
            "candidate_count": len(candidate_nodes),
            "ability_count": len(ability_nodes),
            "edge_count": len(edges),
        },
        "nodes": list(ability_nodes.values()) + candidate_nodes,
        "edges": edges,
    }


def write_markdown(graph: dict[str, Any]) -> None:
    lines = [
        "# TemporaryAI Candidate Knowledge Graph",
        "",
        f"- generated_at: {graph['generated_at']}",
        f"- candidates: {graph['summary']['candidate_count']}",
        f"- abilities: {graph['summary']['ability_count']}",
        "",
        "This index is generated from reviewed candidate folders. It is a compact orientation file for live chat and project loops; it does not activate candidates or edit their profiles.",
        "",
        "## Candidates",
        "",
    ]
    candidates = [node for node in graph["nodes"] if node.get("type") == "candidate"]
    for node in candidates:
        source = node["source_summary"]
        workbench = node["workbench_summary"]
        ability_names = ", ".join(ability["id"] for ability in node["abilities"])
        lines.extend(
            [
                f"### {node['display_name']}",
                "",
                f"- candidate_id: `{node['id']}`",
                f"- role: {node.get('role_title') or 'unknown'}",
                f"- type: {node.get('ai_type') or 'unknown'}",
                f"- status: {node.get('status') or 'unknown'} / {node.get('activation_status') or 'unknown'}",
                f"- abilities: {ability_names}",
                f"- source_count: {source['source_count']}",
                f"- source_status: {source.get('source_pack_status') or source.get('online_preview_status') or 'unknown'}",
                f"- needs_clarification: {source['needs_clarification']}",
                f"- grounding_review: {source.get('grounding_review_status') or 'none'}",
                f"- grounding_identity: {source.get('grounding_identity_status') or 'unreviewed'}",
                f"- grounding_runtime_activation_allowed: {source.get('grounding_runtime_activation_allowed')}",
                f"- grounding_source_gaps: {source.get('grounding_source_gap_count', 0)}",
                f"- workbench: `{workbench.get('workbench') or 'none'}`",
            ]
        )
        if workbench.get("project_state", {}).get("current_project"):
            state = workbench["project_state"]
            lines.extend(
                [
                    f"- current_project: {state.get('current_project')}",
                    f"- stage: {state.get('stage')}",
                    f"- next_step: {state.get('next_step')}",
                ]
            )
        lines.append("")
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    graph = build_graph()
    write_json(OUT_JSON, graph)
    write_markdown(graph)
    print(json.dumps({"json": rel(OUT_JSON), "markdown": rel(OUT_MD), **graph["summary"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
