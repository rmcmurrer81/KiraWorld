from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "Data" / "ai_workspaces" / "temporary_ai" / "temporary_ai_legal_refreshed_20260605_204754"


LEGAL_RESEARCH_TARGETS = [
    {
        "title": "New Jersey Courts - Opinions",
        "url": "https://www.njcourts.gov/public/opinions",
        "category": "official_opinions",
        "purpose": "Official New Jersey Judiciary opinions lead for current legal research.",
    },
    {
        "title": "New Jersey Courts - Court Rules",
        "url": "https://www.njcourts.gov/attorneys/rules-court",
        "category": "official_rules",
        "purpose": "Official New Jersey court rules lead.",
    },
    {
        "title": "New Jersey Legislature - Statutes",
        "url": "https://www.njleg.state.nj.us/",
        "category": "official_statutes",
        "purpose": "Official New Jersey statutes and bill search lead.",
    },
    {
        "title": "CourtListener / RECAP",
        "url": "https://www.courtlistener.com/",
        "category": "public_case_law_and_dockets",
        "purpose": "Public case-law and RECAP docket lead for similar-case research.",
    },
    {
        "title": "Justia New Jersey Case Law",
        "url": "https://law.justia.com/cases/new-jersey/",
        "category": "public_case_law",
        "purpose": "Public New Jersey case-law research lead.",
    },
    {
        "title": "Google Scholar Case Law",
        "url": "https://scholar.google.com/",
        "category": "manual_case_law_search",
        "purpose": "Manual public case-law search lead; filter to New Jersey where possible.",
    },
    {
        "title": "PACER",
        "url": "https://pacer.uscourts.gov/",
        "category": "federal_dockets_manual_login",
        "purpose": "Federal docket lead. Requires Robert login/payment where applicable; no automatic scraping.",
    },
]

LEGAL_SEARCH_QUERIES = [
    '"New Jersey" theft by unlawful taking misunderstanding intent case law',
    '"New Jersey" harassment cyber harassment criminal mischief municipal court',
    '"New Jersey" municipal court prosecutor review dismissal criminal complaint',
    '"New Jersey" restraining order dismissal later criminal complaint facts',
]

LEGAL_SEARCH_PROVIDERS = [
    {
        "provider": "CourtListener",
        "url_template": "https://www.courtlistener.com/?q={query}",
        "purpose": "Public case-law/RECAP search lead.",
    },
    {
        "provider": "Justia New Jersey",
        "url_template": "https://law.justia.com/search?query={query}",
        "purpose": "Public case-law search lead.",
    },
    {
        "provider": "Google Scholar",
        "url_template": "https://scholar.google.com/scholar?q={query}",
        "purpose": "Manual case-law search lead.",
    },
    {
        "provider": "New Jersey Courts site search",
        "url_template": "https://www.njcourts.gov/search?search={query}",
        "purpose": "Official New Jersey Judiciary site search lead.",
    },
]

COURT_ACTOR_TARGETS = [
    {
        "title": "Essex County Prosecutor's Office",
        "url": "https://www.njoag.gov/about/divisions-and-offices/division-of-criminal-justice-home/county-prosecutors/",
        "category": "prosecutor_office_lead",
        "purpose": "Official statewide county prosecutor contact/reference lead.",
    },
    {
        "title": "New Jersey Courts - Municipal Courts",
        "url": "https://www.njcourts.gov/courts/municipal",
        "category": "municipal_court_lead",
        "purpose": "Official municipal court process/reference lead.",
    },
    {
        "title": "New Jersey Courts - Find a Court",
        "url": "https://www.njcourts.gov/public/find-a-court",
        "category": "court_location_lead",
        "purpose": "Official court location/contact lead for venue context.",
    },
]

COURT_ACTOR_SEARCH_QUERIES = [
    '"Montclair Municipal Court" prosecutor',
    '"Montclair Municipal Court" judge',
    '"Essex County" "municipal prosecutor" New Jersey',
]


def now_stamp() -> tuple[str, str]:
    now = datetime.now().astimezone()
    return now.strftime("%Y%m%d"), now.isoformat(timespec="seconds")


def safe_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value or "")
    value = html.unescape(value)
    return " ".join(value.split())


def fetch_url(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Kira-LauraLegalDailyUpdate/1.0 (+local personal research tool)",
            "Accept": "text/html,application/xhtml+xml,application/xml,*/*",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read()


def fetch_public_page_summary(url: str) -> dict:
    item = {"url": url, "status": "not_fetched", "title": "", "description": "", "note": ""}
    try:
        data = fetch_url(url)
        text = data.decode("utf-8", errors="ignore")
    except Exception as exc:
        item.update({"status": "manual_review_needed", "note": str(exc)})
        return item

    title = ""
    match = re.search(r"<title[^>]*>(.*?)</title>", text, flags=re.IGNORECASE | re.DOTALL)
    if match:
        title = safe_text(match.group(1))
    description = ""
    match = re.search(
        r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']',
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if match:
        description = safe_text(match.group(1))
    item.update({"status": "fetched", "title": title, "description": description, "note": "Fetched public page metadata."})
    return item


def bing_web_search(query: str, max_results: int = 8) -> list[dict]:
    params = urllib.parse.urlencode({"q": query, "count": str(max_results)})
    url = f"https://www.bing.com/search?{params}"
    try:
        html_text = fetch_url(url).decode("utf-8", errors="ignore")
    except Exception as exc:
        return [
            {
                "query": query,
                "status": "manual_search_required",
                "error": str(exc),
                "manual_search_url": url,
            }
        ]

    results: list[dict] = []
    for match in re.finditer(r'<li class="b_algo".*?</li>', html_text, flags=re.IGNORECASE | re.DOTALL):
        block = match.group(0)
        link_match = re.search(r'<h2[^>]*>\s*<a[^>]+href=["\'](.*?)["\'][^>]*>(.*?)</a>', block, flags=re.IGNORECASE | re.DOTALL)
        if not link_match:
            continue
        href = html.unescape(link_match.group(1))
        title = safe_text(link_match.group(2))
        snippet = ""
        snippet_match = re.search(r"<p[^>]*>(.*?)</p>", block, flags=re.IGNORECASE | re.DOTALL)
        if snippet_match:
            snippet = safe_text(snippet_match.group(1))
        results.append({"query": query, "title": title, "url": href, "snippet": snippet, "provider": "bing_html"})
        if len(results) >= max_results:
            break
    if not results:
        results.append({"query": query, "status": "manual_search_required", "manual_search_url": url})
    return results


def legal_manual_search_leads(query: str) -> list[dict]:
    encoded = urllib.parse.quote_plus(query)
    items = []
    for provider in LEGAL_SEARCH_PROVIDERS:
        items.append(
            {
                "query": query,
                "title": f"{provider['provider']} search: {query}",
                "url": provider["url_template"].format(query=encoded),
                "provider": provider["provider"],
                "purpose": provider["purpose"],
                "status": "manual_review_lead",
            }
        )
    return items


def ensure_workspace_structure(workspace: Path) -> list[Path]:
    folders = [
        workspace / "daily_research" / "legal_updates",
        workspace / "daily_research" / "case_law",
        workspace / "daily_research" / "court_actor_profiles",
        workspace / "case_strategy",
        workspace / "contact_database",
        workspace / "outputs" / "case_summaries",
        workspace / "outputs" / "timelines",
        workspace / "outputs" / "draft_motions",
        workspace / "outputs" / "questions_for_counsel",
        workspace / "outputs" / "game_plans",
    ]
    for folder in folders:
        folder.mkdir(parents=True, exist_ok=True)

    readme = workspace / "outputs" / "README_legal_outputs.md"
    if not readme.exists():
        readme.write_text(
            "# Laura Mitchell Output Folders\n\n"
            "Laura should save reviewable case summaries, timelines, issue lists, draft motions, questions for counsel, and game plans here.\n\n"
            "Nothing here is filed with a court or sent to anyone automatically. Robert reviews everything.\n",
            encoding="utf-8",
        )
    return [readme]


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_markdown(path: Path, title: str, sections: list[tuple[str, list[dict]]], generated_at: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {title}", "", f"- generated_at: {generated_at}", ""]
    for heading, items in sections:
        lines.extend([f"## {heading}", ""])
        for item in items:
            title_text = item.get("title") or item.get("status") or "Untitled"
            lines.append(f"- **{title_text}**")
            if item.get("category"):
                lines.append(f"  - category: {item['category']}")
            url = item.get("url") or item.get("manual_search_url") or ""
            if url:
                lines.append(f"  - url: {url}")
            note = item.get("purpose") or item.get("description") or item.get("snippet") or item.get("note") or item.get("error") or ""
            if note:
                lines.append(f"  - note: {note}")
            if item.get("use_rule"):
                lines.append(f"  - use rule: {item['use_rule']}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def gather_seed_pages(targets: list[dict], source_type: str) -> list[dict]:
    items: list[dict] = []
    for target in targets:
        item = dict(target)
        item["source_type"] = source_type
        summary = fetch_public_page_summary(item["url"])
        item["status"] = summary.get("status", "manual_review_needed")
        item["fetched_title"] = summary.get("title", "")
        item["public_description"] = summary.get("description", "")
        item["fetch_note"] = summary.get("note", "")
        item["use_rule"] = "Public research lead only. Laura may use it to prepare analysis and questions; Robert reviews before relying on it."
        items.append(item)
    return items


def write_templates(workspace: Path, generated_at: str) -> list[Path]:
    paths: list[Path] = []
    outcome_template = workspace / "case_strategy" / "outcome_scenarios_template.md"
    outcome_template.write_text(
        "# Outcome Scenarios Template\n\n"
        f"- updated_at: {generated_at}\n\n"
        "For each issue, Laura should separate:\n\n"
        "- Known facts from Robert's documents\n"
        "- Missing facts or documents\n"
        "- Possible prosecution/court view\n"
        "- Possible defense/Robert view\n"
        "- Best-case, middle-case, and worst-case outcomes\n"
        "- Confidence level and why\n"
        "- Practical next step Robert can review with counsel or the court\n",
        encoding="utf-8",
    )
    paths.append(outcome_template)

    game_plan_template = workspace / "case_strategy" / "game_plan_template.md"
    game_plan_template.write_text(
        "# Legal Game Plan Template\n\n"
        f"- updated_at: {generated_at}\n\n"
        "Laura should draft game plans in this order:\n\n"
        "1. One-paragraph case posture\n"
        "2. Timeline of key events\n"
        "3. Evidence already available\n"
        "4. Evidence still needed\n"
        "5. Similar-case or statute/rule leads to review\n"
        "6. Questions for counsel/prosecutor/court clerk\n"
        "7. Draft motion/letter outline if Robert asks\n"
        "8. Risks, uncertainties, and possible outcomes\n\n"
        "Do not say anything was filed, sent, or accepted unless Robert explicitly confirms it happened.\n",
        encoding="utf-8",
    )
    paths.append(game_plan_template)
    return paths


def update_workspace_manifest(workspace: Path, generated_paths: list[Path]) -> None:
    manifest_path = workspace / "workspace_manifest.json"
    if not manifest_path.exists():
        return
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = manifest.setdefault("files", [])
    by_relative_path = {entry.get("relative_source_path"): entry for entry in files}
    workspace_rel = workspace.relative_to(ROOT)
    for path in generated_paths:
        rel = path.relative_to(workspace).as_posix()
        text = path.read_text(encoding="utf-8", errors="ignore") if path.suffix.lower() in {".md", ".json", ".txt"} else ""
        entry = by_relative_path.get(rel)
        if entry is None:
            entry = {"relative_source_path": rel}
            files.append(entry)
        entry.update(
            {
                "source_path": str(workspace_rel / rel).replace("\\", "/"),
                "extension": path.suffix,
                "size_bytes": path.stat().st_size,
                "status": "extracted",
                "excerpt": " ".join(text.split())[:1200],
            }
        )
    manifest["file_count"] = len(files)
    manifest["extracted_count"] = sum(1 for entry in files if entry.get("status") == "extracted")
    manifest.setdefault("daily_legal_research", {})["last_update_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    manifest["daily_legal_research"]["last_update_files"] = [str(path.relative_to(ROOT)) for path in generated_paths]
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Refresh Laura Mitchell legal research files.")
    parser.add_argument("--workspace", default=str(WORKSPACE), help="Laura legal workspace path")
    args = parser.parse_args(argv)

    workspace = Path(args.workspace)
    date_key, generated_at = now_stamp()
    generated_paths = ensure_workspace_structure(workspace)

    legal_seed_items = gather_seed_pages(LEGAL_RESEARCH_TARGETS, "legal_research_seed")
    case_law_sections: list[tuple[str, list[dict]]] = [("official and public legal research sources", legal_seed_items)]
    case_law_items = list(legal_seed_items)
    for query in LEGAL_SEARCH_QUERIES:
        items = legal_manual_search_leads(query)
        for item in items:
            item["source_type"] = "similar_case_search"
            item["use_rule"] = "Search lead only. Verify jurisdiction, date, and facts before using in a game plan."
        case_law_sections.append((f"similar-case search: {query}", items))
        case_law_items.extend(items)

    case_json = workspace / "daily_research" / "case_law" / f"{date_key}_case_law_and_docket_leads.json"
    case_md = workspace / "daily_research" / "case_law" / f"{date_key}_case_law_and_docket_leads.md"
    write_json(case_json, {"generated_at": generated_at, "items": case_law_items, "policy": {"public_sources_only": True, "no_auto_filing": True}})
    write_markdown(case_md, "Case Law, Docket, And Similar-Case Leads", case_law_sections, generated_at)
    generated_paths.extend([case_json, case_md])

    actor_seed_items = gather_seed_pages(COURT_ACTOR_TARGETS, "court_actor_seed")
    actor_sections: list[tuple[str, list[dict]]] = [("official court/prosecutor sources", actor_seed_items)]
    actor_items = list(actor_seed_items)
    for query in COURT_ACTOR_SEARCH_QUERIES:
        items = bing_web_search(query, max_results=8)
        for item in items:
            item["source_type"] = "court_actor_search"
            item["use_rule"] = "Public profile/contact lead only. Verify identity and relevance before using."
        actor_sections.append((f"court actor search: {query}", items))
        actor_items.extend(items)

    actor_json = workspace / "daily_research" / "court_actor_profiles" / f"{date_key}_court_actor_profile_leads.json"
    actor_md = workspace / "daily_research" / "court_actor_profiles" / f"{date_key}_court_actor_profile_leads.md"
    write_json(actor_json, {"generated_at": generated_at, "items": actor_items, "policy": {"public_sources_only": True}})
    write_markdown(actor_md, "Judge, Prosecutor, And Court Actor Leads", actor_sections, generated_at)
    generated_paths.extend([actor_json, actor_md])

    queue = workspace / "contact_database" / "legal_actor_profile_queue.json"
    write_json(
        queue,
        {
            "updated_at": generated_at,
            "status": "review_queue",
            "rules": [
                "Use public sources only.",
                "Keep biographies short and relevant to the case role.",
                "Separate verified public facts from Robert's interpretation.",
                "Do not contact anyone automatically.",
            ],
            "items": actor_items,
        },
    )
    queue_md = workspace / "contact_database" / "legal_actor_profile_queue.md"
    write_markdown(queue_md, "Legal Actor Profile Review Queue", [("profile leads", actor_items)], generated_at)
    generated_paths.extend([queue, queue_md])

    generated_paths.extend(write_templates(workspace, generated_at))
    update_workspace_manifest(workspace, generated_paths)
    print(json.dumps({"status": "ok", "generated_at": generated_at, "outputs": [str(path.relative_to(ROOT)) for path in generated_paths]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
