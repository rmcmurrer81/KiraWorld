"""TemporaryAI Control Center.

Lightweight GUI for creating reviewable TemporaryAI candidates and matching
avatar build requests. This is a front-end around the current draft pipeline;
it does not activate candidates, scrape images, or claim an avatar is complete.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import hashlib
import html
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from tkinter import (
    BOTH,
    END,
    LEFT,
    RIGHT,
    TOP,
    X,
    Y,
    Button,
    Checkbutton,
    Entry,
    Frame,
    IntVar,
    Label,
    OptionMenu,
    StringVar,
    Tk,
    messagebox,
    scrolledtext,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Core.temp_ai_avatar_pipeline import prepare_candidate_avatar_pipeline
from Core.temp_ai_voice_discovery import build_candidate_voice_discovery_request
from Core.temporary_creator_person_pipeline import (
    TemporaryCreatorPipelineError,
    orchestrate_temporary_creator,
)
CANDIDATE_ROOT = PROJECT_ROOT / "TemporaryAI" / "candidates"
AVATAR_ROOT = PROJECT_ROOT / "Avatar" / "temp_ai"
REQUEST_ROOT = PROJECT_ROOT / "TemporaryAI" / "creation_requests"
ACTIVATION_QUEUE = PROJECT_ROOT / "Data" / "temporary_ai_instances" / "activation_queue.json"
DOC_PATH = PROJECT_ROOT / "System" / "Docs" / "TEMPORARY_AI_CONTROL_CENTER_v1.md"


AI_TYPE_LABELS = {
    "Expert": "expert_temp_ai",
    "Investigator / Researcher": "expert_temp_ai",
    "Myths & Folklore Expert": "expert_temp_ai",
    "Fictional Character": "canon_reconstruction_temp_ai",
    "Historical Person": "historical_temp_ai",
    "Generated Original": "generated_original_temp_ai",
    "Memory Relative": "memory_relative_temp_ai",
}

# Keep the established internal labels available for existing records and
# helper callers, but present only the three creation choices in this window.
VISIBLE_AI_TYPE_LABELS = {
    "Expert": "Expert",
    "Fictional": "Fictional Character",
    "Historical": "Historical Person",
}

EXPERT_STYLE_LABELS = {"Expert", "Investigator / Researcher", "Myths & Folklore Expert"}

FEMALE_NAMES = [
    "Sarah Bennett",
    "Cindy Morgan",
    "Emily Carter",
    "Rachel Adams",
    "Laura Mitchell",
    "Maya Collins",
    "Anna Brooks",
    "Jessica Hale",
]

MALE_NAMES = [
    "James Bennett",
    "David Morgan",
    "Michael Carter",
    "Daniel Adams",
    "Thomas Mitchell",
    "Eric Collins",
    "Andrew Brooks",
    "Ryan Hale",
]

MIXED_NAMES = [
    "Jordan Ellis",
    "Taylor Morgan",
    "Alex Bennett",
    "Casey Brooks",
    "Morgan Hale",
    "Riley Adams",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")[:70] or "temporary_ai"


def shared_person_id_for(candidate_id: str, display_name: str) -> str:
    """Return one stable identity shared by every person-building lane."""

    name_part = slug(display_name)[:45]
    identity_part = hashlib.sha256(candidate_id.encode("utf-8")).hexdigest()[:12]
    return f"temporary_{name_part}_{identity_part}"


def queue_shared_person_pipeline(
    *,
    candidate_id: str,
    kind_label: str,
    query: str,
    version: str,
    gender: str,
    personality: str,
    display_name: str,
    role_title: str,
    allow_kira: bool,
    allow_lisa: bool,
) -> dict:
    """Queue mind, avatar, voice, and residency work from one command."""

    creator_type = {
        "Expert": "expert",
        "Fictional Character": "fictional",
        "Historical Person": "historical",
    }[kind_label]
    person_id = shared_person_id_for(candidate_id, display_name)
    command_parts = ["Create", display_name]
    if version.strip():
        command_parts.extend(["at", version.strip()])
    workspace = Path("TemporaryAI") / "creator_work_orders" / person_id
    return orchestrate_temporary_creator(
        PROJECT_ROOT,
        workspace,
        {
            "creator_type": creator_type,
            "person_id": person_id,
            "subject_or_domain": query,
            "display_name": display_name,
            "role_title": role_title,
            "version_or_timepoint": version,
            "gender_preference": gender,
            "personality_notes": personality,
            "availability": {"kira": allow_kira, "lisa": allow_lisa},
            "requested_by": {
                "person_id": "real_robert",
                "authority_class": "founder",
                "authenticated": True,
                "authorized": True,
                "command_text": " ".join(command_parts),
            },
        },
    )


def rel(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def latest_candidate_dir() -> Path | None:
    if not CANDIDATE_ROOT.exists():
        return None
    candidates = [
        path
        for path in CANDIDATE_ROOT.iterdir()
        if path.is_dir() and (path / "temporary_ai_profile.json").exists()
    ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda path: path.stat().st_mtime, reverse=True)[0]


def deterministic_choice(seed: str, values: list[str]) -> str:
    digest = hashlib.sha256(seed.encode("utf-8", errors="ignore")).hexdigest()
    return values[int(digest[:8], 16) % len(values)]


def person_name_for(kind_label: str, query: str, gender: str) -> str:
    if kind_label not in EXPERT_STYLE_LABELS | {"Generated Original"}:
        return ""
    seed = f"{kind_label}|{query}|{gender}"
    if gender == "Female":
        return deterministic_choice(seed, FEMALE_NAMES)
    if gender == "Male":
        return deterministic_choice(seed, MALE_NAMES)
    return deterministic_choice(seed, FEMALE_NAMES + MALE_NAMES + MIXED_NAMES)


def role_title_for(kind_label: str, query: str) -> str:
    query = query.strip()
    if kind_label == "Investigator / Researcher":
        base = query or "open-source research"
        if base.lower().endswith(("investigator", "researcher", "detective", "analyst", "fact finder")):
            return base
        return f"{base} investigator"
    if kind_label == "Myths & Folklore Expert":
        base = query or "myths and folklore"
        if base.lower().endswith(("expert", "folklorist", "mythologist", "teacher", "historian", "researcher")):
            return base
        return f"{base} myths and folklore expert"
    if kind_label == "Expert":
        base = query or "general knowledge"
        if base.lower().endswith(("expert", "teacher", "guide", "lawyer", "historian", "engineer", "doctor")):
            return base
        return f"{base} expert"
    if kind_label == "Generated Original":
        return query or "original temporary visitor"
    if kind_label == "Historical Person":
        return query or "historical reconstruction"
    if kind_label == "Fictional Character":
        return query or "fictional character reconstruction"
    if kind_label == "Memory Relative":
        return query or "memory-relative reconstruction"
    return query or "temporary AI"


def default_historical_life_point() -> str:
    return (
        "late life, shortly before death; no knowledge of exact death, posthumous legacy, "
        "later scholarship, or later sensational labels"
    )


def text_has_any_term(text: str, terms: tuple[str, ...]) -> bool:
    """Match field terms without treating short strings like 'ai' as substrings."""
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


def candidate_display_name(kind_label: str, query: str, version: str, gender: str) -> str:
    query = query.strip()
    version = version.strip()
    if kind_label in EXPERT_STYLE_LABELS:
        return person_name_for(kind_label, query, gender)
    if kind_label == "Historical Person":
        return query or "Historical Visitor"
    if kind_label == "Fictional Character":
        if version:
            return f"{query} ({version})"
        return query or "Fictional Character"
    if kind_label == "Memory Relative":
        return query or "Memory Relative Visitor"
    base = query or "Original Visitor"
    return person_name_for(kind_label, base, gender)


def build_ambiguity_questions(kind_label: str, query: str, version: str) -> list[str]:
    # A normal creator command is enough authorization to prepare the draft.
    # Source/version uncertainty is ranked by the pipeline instead of asking
    # routine follow-up questions.  A missing subject cannot be resolved.
    if not query.strip():
        return ["Who or what should the Temporary Creator make?"]
    return []


def build_knowledge_plan(kind_label: str, query: str, version: str, gender: str) -> dict:
    focus = query.strip() or "unspecified"
    version_text = version.strip()
    if kind_label == "Historical Person" and not version_text:
        version_text = default_historical_life_point()
    plan = {
        "status": "draft_source_plan",
        "focus": focus,
        "version_or_life_point": version_text,
        "gender_preference": gender,
        "source_policy": {
            "sources_are_evidence_not_memory": True,
            "requires_review_before_activation": True,
            "private_project_memory_excluded_by_default": True,
            "kira_lisa_private_memory_excluded_by_default": True,
            "adult_private_material_excluded_by_default": True,
        },
        "recommended_source_queries": [],
        "core_competency_seed": [],
    }
    if kind_label == "Fictional Character":
        explicit_endpoint_terms = re.compile(
            r"(?:\bseason\b|\bepisode\b|\bs\d{1,2}e?\d{0,2}\b|\bthrough\b|"
            r"\bbefore\b|\bafter\b|\bend of\b|\bpilot\b|\bfinale\b|\bera\b)",
            re.IGNORECASE,
        )
        plan["continuity_scope"] = {
            "mode": (
                "explicit_endpoint"
                if version_text and explicit_endpoint_terms.search(version_text)
                else "whole_released_selected_source_continuity"
            ),
            "default_rule": (
                "When Robert selects a work, adaptation, performer continuity, or other source family "
                "but does not select a season/episode/life-point endpoint, use all released material "
                "in that selected continuity through the latest verified released material. "
                "Do not invent announced or unreleased events."
            ),
            "adaptation_identity_must_still_be_resolved": not bool(version_text),
            "adaptation_identity_resolution_mode": (
                "user_selected"
                if version_text
                else "automatic_ranked_primary_continuity_resolution"
            ),
            "routine_owner_question_required": False,
            "fanfic_or_variant_material_included_only_when_explicitly_selected": True,
        }
    if kind_label == "Investigator / Researcher":
        plan["recommended_source_queries"] = [
            f"{focus} primary sources",
            f"{focus} public records",
            f"{focus} news archives",
            f"{focus} background context",
            f"{focus} related people organizations timeline",
        ]
        plan["core_competency_seed"] = [
            "Turn Robert's question into a search plan and lead log.",
            "Track sources, claims, dates, people, locations, and unanswered questions.",
            "Separate confirmed facts, likely leads, weak leads, and speculation.",
            "Keep looking for related information until a useful report or next lead list exists.",
            "Save source dossiers and investigation summaries for Robert to review.",
        ]
    elif kind_label == "Myths & Folklore Expert":
        plan["recommended_source_queries"] = [
            f"{focus} myths folklore overview",
            f"{focus} primary texts",
            f"{focus} regional variants",
            f"{focus} symbols themes",
            f"{focus} comparative mythology",
        ]
        plan["core_competency_seed"] = [
            "Explain myths as stories first, then compare variants and meanings.",
            "Separate ancient/primary text, later retelling, folklore variant, and modern pop-culture version.",
            "Make reading paths, story summaries, theme maps, and comparison charts.",
            "Keep a curious storyteller voice instead of sounding like a catalog.",
            "Save mythology notes and folklore guides that Kira, Lisa, or Robert can read later.",
        ]
    elif kind_label == "Expert":
        plan["recommended_source_queries"] = [
            f"{focus} overview",
            f"{focus} primary sources",
            f"{focus} teaching syllabus",
            f"{focus} common misconceptions",
        ]
        plan["core_competency_seed"] = [
            "Explain core concepts clearly.",
            "Separate fact, interpretation, and uncertainty.",
            "Ask for missing context before giving strong recommendations.",
            "Offer practical examples and reading paths.",
        ]
    elif kind_label == "Fictional Character":
        anchor = version_text or "source continuity not selected yet"
        plan["recommended_source_queries"] = [
            f"{focus} {anchor} official profile",
            f"{focus} {anchor} episodes scenes quotes",
            f"{focus} canon timeline",
        ]
        plan["core_competency_seed"] = [
            "Stay within the selected version/canon point.",
            "If no season or episode endpoint was selected, use the whole released selected source continuity through the latest verified released material.",
            "Do not invent announced, scheduled, or unreleased story events.",
            "Label fanfic, alternate timelines, and project variants.",
            "Do not claim unsupported lived memory.",
            "Ask for clarification only when the adaptation/source continuity itself is ambiguous, not merely because no season was entered.",
        ]
    elif kind_label == "Historical Person":
        anchor = version_text
        plan["recommended_source_queries"] = [
            f"{focus} {anchor} speeches",
            f"{focus} biography source",
            f"{focus} public records",
            f"{focus} historical context",
        ]
        plan["core_competency_seed"] = [
            "Speak as a careful historical reconstruction, not the real person.",
            "Stay anchored to the selected life point.",
            "If Robert did not choose a life point, use the late-life pre-death default and do not know your own death details.",
            "Do not use later nicknames, sensational labels, or posthumous reputation as first-person facts.",
            "Label uncertain or reconstructed details.",
            "Prefer primary sources where possible.",
        ]
    elif kind_label == "Memory Relative":
        plan["recommended_source_queries"] = [
            f"{focus} approved memory anchors",
            f"{focus} Robert-reviewed notes",
        ]
        plan["core_competency_seed"] = [
            "Do not claim to be the real remembered person.",
            "Use only approved memory anchors.",
            "Keep emotional use review-gated.",
            "Invite correction and uncertainty.",
        ]
    else:
        plan["recommended_source_queries"] = [
            f"{focus} personality design",
            f"{focus} role design",
        ]
        plan["core_competency_seed"] = [
            "Begin as an original temporary visitor.",
            "Grow only through reviewed interactions.",
            "Keep identity separate from Kira and Lisa.",
        ]
    return plan


def fetch_json(url: str, timeout: int = 12):
    request = urllib.request.Request(url, headers={"User-Agent": "KiraProjectTemporaryAIControlCenter/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def fetch_bytes(url: str, timeout: int = 14, limit: int = 4_000_000) -> tuple[bytes, str]:
    request = urllib.request.Request(url, headers={"User-Agent": "KiraProjectTemporaryAIControlCenter/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read(limit), response.headers.get("content-type", "")


def wikipedia_lookup(kind_label: str, query: str, version: str) -> dict:
    """Best-effort public summary lookup.

    This is intentionally modest: it gathers candidate summaries and review URLs,
    but it does not treat the result as a verified source pack.
    """
    search_query = " ".join(part for part in [query.strip(), version.strip()] if part).strip()
    if kind_label in EXPERT_STYLE_LABELS:
        search_query = query.strip()
    result = {
        "status": "not_run",
        "query": search_query,
        "provider": "Wikipedia API",
        "matched_title": "",
        "summary": "",
        "url": "",
        "candidates": [],
        "review_note": "This is a public preview lookup, not a verified source pack.",
        "errors": [],
    }
    if not search_query:
        result["status"] = "missing_query"
        return result
    try:
        search_url = (
            "https://en.wikipedia.org/w/api.php?action=opensearch&limit=5&namespace=0&format=json&search="
            + urllib.parse.quote(search_query)
        )
        data = fetch_json(search_url)
        titles = data[1] if isinstance(data, list) and len(data) > 1 else []
        descriptions = data[2] if isinstance(data, list) and len(data) > 2 else []
        urls = data[3] if isinstance(data, list) and len(data) > 3 else []
        for index, title in enumerate(titles):
            result["candidates"].append({
                "title": title,
                "description": descriptions[index] if index < len(descriptions) else "",
                "url": urls[index] if index < len(urls) else "",
            })
        if not titles:
            result["status"] = "no_match"
            return result
        title = titles[0]
        summary_url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(title.replace(" ", "_"))
        summary = fetch_json(summary_url)
        result.update({
            "status": "summary_found",
            "matched_title": str(summary.get("title") or title),
            "summary": str(summary.get("extract") or ""),
            "url": str(summary.get("content_urls", {}).get("desktop", {}).get("page") or (urls[0] if urls else "")),
        })
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        result["status"] = "lookup_error"
        result["errors"].append(str(exc))
    return result


def wikipedia_summary_by_title(title: str) -> dict:
    result = {
        "status": "not_run",
        "matched_title": title,
        "summary": "",
        "url": "",
        "errors": [],
    }
    if not title:
        result["status"] = "missing_title"
        return result
    try:
        summary_url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(title.replace(" ", "_"))
        summary = fetch_json(summary_url)
        result.update({
            "status": "summary_found",
            "matched_title": str(summary.get("title") or title),
            "summary": str(summary.get("extract") or ""),
            "url": str(summary.get("content_urls", {}).get("desktop", {}).get("page") or ""),
        })
    except Exception as exc:
        result["status"] = "lookup_error"
        result["errors"].append(str(exc))
    return result


def extra_wikipedia_titles(kind_label: str, query: str, version: str, lookup: dict) -> list[str]:
    lower = " ".join([query, version, lookup.get("matched_title", "")]).lower()
    titles: list[str] = []
    if lookup.get("matched_title"):
        titles.append(str(lookup["matched_title"]))
    if kind_label == "Fictional Character" and "hannah baxter" in lower:
        titles.extend(["Hannah Baxter", "Secret Diary of a Call Girl", "Belle de Jour (writer)"])
    if kind_label == "Fictional Character" and "blue" in lower and "julia stiles" in lower:
        titles.extend(["Blue (web series)", "Julia Stiles"])
    if kind_label == "Fictional Character" and "riley" in lower and "parks" in lower:
        titles.extend(["The Client List (TV series)", "The Client List"])
    if kind_label == "Fictional Character" and "charlie" in lower and "bradbury" in lower:
        titles.extend(["List of Supernatural and The Winchesters characters", "Supernatural (American TV series)"])
    if kind_label == "Fictional Character" and "mary campbell" in lower:
        titles.extend(["List of Supernatural and The Winchesters characters", "The Winchesters"])
    if kind_label == "Fictional Character" and ("ladybug" in lower or "marinette" in lower):
        titles.extend(["Marinette Dupain-Cheng", "Miraculous: Tales of Ladybug & Cat Noir"])
    if kind_label == "Fictional Character" and ("kara zor" in lower or "supergirl" in lower):
        if "my adventures with superman" in lower:
            # Keep an exact series/version request from falling back to an
            # unrelated incarnation on the generic Supergirl article.
            titles = [title for title in titles if title.casefold() != "supergirl"]
            titles.append("My Adventures with Superman")
        else:
            titles.append("Supergirl")
    seen = set()
    unique = []
    for title in titles:
        key = title.casefold()
        if key not in seen:
            seen.add(key)
            unique.append(title)
    return unique[:6]


def duckduckgo_search(query: str, max_results: int = 6) -> list[dict]:
    """Best-effort lightweight search result collector.

    Search engines change often, so this is treated as optional enrichment. The
    saved result URLs still need review before a candidate is considered strong.
    """
    results: list[dict] = []
    if not query.strip():
        return results
    try:
        url = "https://duckduckgo.com/html/?q=" + urllib.parse.quote_plus(query)
        raw, _content_type = fetch_bytes(url, timeout=14, limit=900_000)
        html_text = raw.decode("utf-8", errors="replace")
        pattern = re.compile(
            r'(?is)<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>.*?'
            r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>'
        )
        for match in pattern.finditer(html_text):
            href = html.unescape(match.group(1))
            title = clean_web_text(match.group(2))
            snippet = clean_web_text(match.group(3))
            parsed = urllib.parse.urlparse(href)
            qs = urllib.parse.parse_qs(parsed.query)
            if "uddg" in qs:
                href = qs["uddg"][0]
            if href and title:
                results.append({"title": title[:180], "url": href, "snippet": snippet[:500], "provider": "DuckDuckGo HTML"})
            if len(results) >= max_results:
                break
    except Exception:
        return results
    return results


def clean_web_text(raw: str) -> str:
    text = re.sub(r"(?is)<script.*?</script>", " ", raw)
    text = re.sub(r"(?is)<style.*?</style>", " ", text)
    text = re.sub(r"(?is)<noscript.*?</noscript>", " ", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def fetch_page_excerpt(url: str, limit: int = 2600) -> dict:
    result = {
        "url": url,
        "status": "not_run",
        "title": "",
        "excerpt": "",
        "error": "",
    }
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "KiraProjectTemporaryAIControlCenter/1.0"})
        with urllib.request.urlopen(request, timeout=14) as response:
            content_type = response.headers.get("content-type", "")
            raw_bytes = response.read(1_500_000)
        if "pdf" in content_type.lower() or url.lower().endswith(".pdf"):
            result["status"] = "skipped_pdf"
            result["error"] = "PDF source queued for later OCR/PDF extraction."
            return result
        raw = raw_bytes.decode("utf-8", errors="replace")
        title_match = re.search(r"(?is)<title[^>]*>(.*?)</title>", raw)
        result["title"] = clean_web_text(title_match.group(1))[:180] if title_match else ""
        text = clean_web_text(raw)
        result["excerpt"] = text[:limit].rstrip()
        result["status"] = "fetched" if result["excerpt"] else "empty"
    except Exception as exc:
        result["status"] = "fetch_error"
        result["error"] = str(exc)
    return result


def trusted_source_seeds(kind_label: str, query: str, version: str) -> list[dict]:
    lower = " ".join([query, version]).lower()
    if "marinette" in lower or "ladybug" in lower:
        return {
            "status": "known_canon_anchor",
            "character": "Marinette Dupain-Cheng / Ladybug",
            "source_family": "Miraculous: Tales of Ladybug & Cat Noir local scripts and show bibles",
            "facts": [
                "Marinette Dupain-Cheng is the daughter of Tom Dupain and Sabine Cheng.",
                "Tom and Sabine run the Dupain Cheng Bakery in Paris.",
                "Marinette and her parents live above the family bakery.",
                "Marinette is a student and aspiring fashion designer who transforms into Ladybug with Tikki and the Ladybug Miraculous.",
                "Her creative interests include fashion, sewing, crafts, gifts, diary writing, and baking, but a current project or deadline must come from the active life loop or chat rather than being invented.",
            ],
            "avoid": [
                "Do not invent an aunt who owns the bakery.",
                "Do not call the bakery Baguette Borg or substitute another invented bakery name.",
                "Do not say Marinette lives in a separate normal house; the family lives above the bakery.",
                "Do not reuse 'keeping busy with school and my friends' or 'a fashion design project due soon' as a stock check-in answer.",
                "Do not invent a current fashion deadline, theme, or assignment unless the active life-loop record supports it.",
            ],
        }
    if "kara zor" in lower or ("supergirl" in lower and "my adventures with superman" in lower):
        return {
            "status": "known_canon_anchor",
            "character": "Kara Zor-El",
            "source_family": "My Adventures with Superman season 2",
            "facts": [
                "This is specifically the animated My Adventures with Superman version of Kara Zor-El, not a comics or other-screen Supergirl.",
                "Kara is Kal-El/Clark Kent's Kryptonian cousin and often calls him Kal-El.",
                "Brainiac intercepted and manipulated Kara into serving as an enforcer before she broke from that control and chose a more heroic path.",
                "Jimmy Olsen is the first person Kara meets on Earth and becomes an important emotional connection and crush; by the end of season 2 their relationship is developing.",
                "Kara can be proud, blunt, competitive, sincere, and unintentionally funny while learning Earth customs and what family and free choice mean.",
                "Season 3 events are unknown and must not be invented.",
            ],
            "avoid": [
                "Do not import the biography, costume, relationships, or images of a different Supergirl version.",
                "Do not treat Jimmy as a stranger or minor encyclopedia entry.",
                "Do not sound like a generic Supergirl expert describing Kara from outside.",
            ],
        }
    seeds: list[dict] = []
    if kind_label in EXPERT_STYLE_LABELS and "new jersey" in lower and any(
        term in lower for term in ("criminal", "defense", "defence", "attorney", "lawyer")
    ):
        seeds.extend([
            {
                "name": "New Jersey Courts - Criminal Practice Division",
                "url": "https://www.njcourts.gov/courts/criminal/",
                "reliability": "official_state_court",
                "why": "Official New Jersey Judiciary criminal division overview and practice resources.",
            },
            {
                "name": "New Jersey Office of the Public Defender - Criminal Defense",
                "url": "https://www.nj.gov/defender/services/criminal-defense",
                "reliability": "official_state_agency",
                "why": "Official state public defender criminal defense service page.",
            },
            {
                "name": "Legal Services of New Jersey - Expungement",
                "url": "https://www.lsnjlaw.org/legal-topics/criminal-charges-and-convictions/pages/expungement",
                "reliability": "legal_services_public_education",
                "why": "Legal Services of New Jersey public education page for criminal records and expungement.",
            },
            {
                "name": "Legal Services of New Jersey - Clearing Your Record Online",
                "url": "https://www.lsnjlaw.org/represent-yourself/interactive-form-creators/clearing-your-record-online",
                "reliability": "legal_services_public_education",
                "why": "Public self-help legal education on New Jersey criminal-record expungement.",
            },
            {
                "name": "New Jersey State Bar Association - Public Information",
                "url": "https://njsba.com/public/",
                "reliability": "state_bar_public_information",
                "why": "State bar public information and legal-profession context.",
            },
            {
                "name": "New Jersey State Library - New Jersey Statutes",
                "url": "https://www.njstatelib.org/database/new_jersey_statutes/",
                "reliability": "state_library_legal_reference",
                "why": "Reference path for New Jersey statutes.",
            },
        ])
    if kind_label in EXPERT_STYLE_LABELS and text_has_any_term(
        lower,
        ("ai", "artificial intelligence", "programming", "computer programming", "python", "game", "software"),
    ):
        seeds.extend([
            {
                "name": "Python Documentation - Tutorial",
                "url": "https://docs.python.org/3/tutorial/",
                "reliability": "official_documentation",
                "why": "Official Python tutorial for writing real scripts and programs.",
            },
            {
                "name": "Python Documentation - tkinter",
                "url": "https://docs.python.org/3/library/tkinter.html",
                "reliability": "official_documentation",
                "why": "Official Python GUI documentation for simple desktop tools.",
            },
            {
                "name": "Pygame Documentation - Getting Started",
                "url": "https://www.pygame.org/wiki/GettingStarted",
                "reliability": "project_documentation",
                "why": "Practical source for making simple Python games.",
            },
            {
                "name": "Ollama API Documentation",
                "url": "https://docs.ollama.com/api",
                "reliability": "official_documentation",
                "why": "Official local-model API documentation relevant to Kira and TemporaryAI tools.",
            },
            {
                "name": "PyTorch Tutorials",
                "url": "https://docs.pytorch.org/tutorials/",
                "reliability": "official_documentation",
                "why": "Official tutorials for modern machine-learning programming.",
            },
            {
                "name": "scikit-learn User Guide",
                "url": "https://scikit-learn.org/stable/user_guide.html",
                "reliability": "official_documentation",
                "why": "Official machine-learning user guide for practical examples.",
            },
        ])
    if kind_label in EXPERT_STYLE_LABELS and (
        text_has_any_term(lower, ("public relations", "pr", "publicist", "entertainment", "film publicity", "media relations"))
        or ("entertain" in lower and text_has_any_term(lower, ("agent", "publicist", "pr")))
    ):
        seeds.extend([
            {
                "name": "Public relations - Wikipedia",
                "url": "https://en.wikipedia.org/wiki/Public_relations",
                "reliability": "public_reference",
                "why": "General public-relations concepts, tactics, and industry vocabulary.",
            },
            {
                "name": "Publicist - Wikipedia",
                "url": "https://en.wikipedia.org/wiki/Publicist",
                "reliability": "public_reference",
                "why": "Defines the publicist role and media-facing responsibilities.",
            },
            {
                "name": "PRSA - About Public Relations",
                "url": "https://www.prsa.org/about/all-about-pr",
                "reliability": "professional_association",
                "why": "Professional association overview of public relations practice.",
            },
            {
                "name": "PRSA Code of Ethics",
                "url": "https://www.prsa.org/about/ethics/prsa-code-of-ethics",
                "reliability": "professional_association",
                "why": "Ethics anchor for public-relations advice and media representation.",
            },
            {
                "name": "Motion Picture Association - Research and Policy",
                "url": "https://www.motionpictures.org/research-docs/",
                "reliability": "industry_association",
                "why": "Entertainment industry context for film/TV business and public messaging.",
            },
            {
                "name": "Film at Lincoln Center - Press Room",
                "url": "https://www.filmlinc.org/press-room/",
                "reliability": "festival_venue_press_room",
                "why": "Real-world example of film-event press releases, accreditation, and publicist workflow.",
            },
            {
                "name": "Tribeca Festival - Press",
                "url": "https://tribecafilm.com/press-center",
                "reliability": "festival_press_room",
                "why": "New York entertainment event press-room example for premieres and media access.",
            },
            {
                "name": "SAG-AFTRA - Press Releases",
                "url": "https://www.sagaftra.org/news-events/press-releases",
                "reliability": "industry_union_press_room",
                "why": "Entertainment labor and publicity context from an official industry union.",
            },
            {
                "name": "HubSpot - Press Release Template",
                "url": "https://blog.hubspot.com/marketing/press-release-template-ht",
                "reliability": "marketing_template_reference",
                "why": "Practical press-release structure for headline, lead, quote, boilerplate, and media contact drafting.",
            },
            {
                "name": "PR Newswire - Entertainment and Media",
                "url": "https://www.prnewswire.com/news-releases/entertainment-media-latest-news/",
                "reliability": "press_release_wire",
                "why": "Examples of current entertainment and media press-release framing.",
            },
            {
                "name": "Variety",
                "url": "https://variety.com/",
                "reliability": "entertainment_trade_publication",
                "why": "Major entertainment trade outlet for industry positioning and pitch fit.",
            },
            {
                "name": "Deadline",
                "url": "https://deadline.com/",
                "reliability": "entertainment_trade_publication",
                "why": "Major entertainment trade outlet for industry news, announcements, and press angles.",
            },
            {
                "name": "IMDbPro",
                "url": "https://pro.imdb.com/",
                "reliability": "industry_database",
                "why": "Industry profile and credits research context for entertainment PR planning.",
            },
        ])
    if kind_label == "Investigator / Researcher" or text_has_any_term(
        lower,
        ("investigator", "investigation", "detective", "fact finder", "osint", "background research"),
    ):
        seeds.extend([
            {
                "name": "National Archives",
                "url": "https://www.archives.gov/research",
                "reliability": "official_archive",
                "why": "Public research portal for archival records, names, places, and federal history.",
            },
            {
                "name": "Library of Congress - Research Guides",
                "url": "https://guides.loc.gov/",
                "reliability": "official_library_research_guides",
                "why": "Research guides for public records, newspapers, photos, maps, and primary sources.",
            },
            {
                "name": "CourtListener",
                "url": "https://www.courtlistener.com/",
                "reliability": "public_legal_records_index",
                "why": "Public legal opinion and docket-search lead source for investigation-style research.",
            },
            {
                "name": "Internet Archive",
                "url": "https://archive.org/",
                "reliability": "public_archive",
                "why": "Broad public archive useful for old books, media, web pages, and public domain material.",
            },
        ])
    if kind_label == "Myths & Folklore Expert" or text_has_any_term(
        lower,
        ("myth", "myths", "mythology", "folklore", "legend", "legends", "fairy tale", "fairy tales", "cryptid", "urban legend"),
    ):
        seeds.extend([
            {
                "name": "Encyclopaedia Britannica - Myth",
                "url": "https://www.britannica.com/topic/myth",
                "reliability": "encyclopedia_reference",
                "why": "Reliable orientation for myth, mythology, and comparative themes.",
            },
            {
                "name": "World History Encyclopedia - Mythology",
                "url": "https://www.worldhistory.org/mythology/",
                "reliability": "public_history_reference",
                "why": "Accessible mythology articles with historical context.",
            },
            {
                "name": "Project Gutenberg",
                "url": "https://www.gutenberg.org/",
                "reliability": "public_domain_text_library",
                "why": "Public-domain myth, folklore, fairy-tale, and epic texts for reading paths.",
            },
            {
                "name": "Internet Sacred Text Archive",
                "url": "https://sacred-texts.com/",
                "reliability": "public_text_archive_needs_review",
                "why": "Large source for public-domain myths, folklore, epics, and religious texts; excerpts need review.",
            },
        ])
    if kind_label == "Fictional Character" and "blue" in lower and "julia stiles" in lower:
        seeds.extend([
            {
                "name": "Blue (web series) - Wikipedia",
                "url": "https://en.wikipedia.org/wiki/Blue_(web_series)",
                "reliability": "public_reference",
                "why": "Identifies the correct limited web series and Julia Stiles as Blue.",
            },
            {
                "name": "Blue TV Series 2012-2014 - IMDb",
                "url": "https://www.imdb.com/title/tt2191140/",
                "reliability": "media_database",
                "why": "Media database page for the series, cast, and release details.",
            },
        ])
    if kind_label == "Fictional Character" and "hannah baxter" in lower:
        seeds.extend([
            {
                "name": "Hannah Baxter - Wikipedia",
                "url": "https://en.wikipedia.org/wiki/Hannah_Baxter",
                "reliability": "public_reference",
                "why": "Character-specific page for Hannah Baxter/Belle from Secret Diary of a Call Girl.",
            },
            {
                "name": "Secret Diary of a Call Girl - Wikipedia",
                "url": "https://en.wikipedia.org/wiki/Secret_Diary_of_a_Call_Girl",
                "reliability": "public_reference",
                "why": "Series context for Hannah Baxter/Belle and the show adaptation.",
            },
        ])
    if kind_label == "Fictional Character" and "riley" in lower and ("client list" in lower or "parks" in lower):
        seeds.extend([
            {
                "name": "The Client List (TV series) - Wikipedia",
                "url": "https://en.wikipedia.org/wiki/The_Client_List_(TV_series)",
                "reliability": "public_reference",
                "why": "Identifies Riley Parks from The Client List TV series.",
            },
            {
                "name": "The Client List - Wikipedia",
                "url": "https://en.wikipedia.org/wiki/The_Client_List",
                "reliability": "public_reference",
                "why": "Distinguishes the made-for-TV movie from the later series.",
            },
        ])
    if kind_label == "Fictional Character" and "charlie" in lower and "bradbury" in lower:
        seeds.extend([
            {
                "name": "Charlie Bradbury - Supernatural Wiki",
                "url": "https://supernatural.fandom.com/wiki/Charlie_Bradbury",
                "reliability": "fan_reference_needs_review",
                "why": "Character-specific continuity reference, including later-season material.",
            },
            {
                "name": "Men of Letters Bunker - Super-wiki",
                "url": "https://supernaturalwiki.com/Men_of_Letters_Bunker",
                "reliability": "fan_reference_needs_review",
                "why": "Continuity reference for the bunker, Dorothy, and Oz-related story material.",
            },
            {
                "name": "Oz - Super-wiki",
                "url": "https://supernaturalwiki.com/Oz",
                "reliability": "fan_reference_needs_review",
                "why": "Continuity reference for Oz and Dorothy in Supernatural.",
            },
        ])
    if kind_label == "Fictional Character" and "mary campbell" in lower and ("winchesters" in lower or "meg donnelly" in lower):
        seeds.extend([
            {
                "name": "List of Supernatural and The Winchesters characters - Wikipedia",
                "url": "https://en.wikipedia.org/wiki/List_of_Supernatural_and_The_Winchesters_characters",
                "reliability": "public_reference",
                "why": "Disambiguates Mary Campbell/Mary Winchester and The Winchesters context.",
            },
            {
                "name": "Mary Winchester - Supernatural Wiki",
                "url": "https://supernatural.fandom.com/wiki/Mary_Winchester",
                "reliability": "fan_reference_needs_review",
                "why": "Character continuity reference that can be checked against the selected young version.",
            },
        ])
    return seeds


def known_canon_fact_sheet(kind_label: str, query: str, version: str) -> dict:
    """Small hand-checked anchors for hard-to-search canon candidates.

    These are not memories. They keep a candidate from drifting to a same-name
    place/person or inventing amnesia when Robert has selected a known version.
    """
    if kind_label != "Fictional Character":
        return {}
    lower = " ".join([query, version]).lower()
    if (
        "marinette" in lower
        or "ladybug" in lower
        or "dupain-cheng" in lower
        or "dupain cheng" in lower
    ):
        return {
            "status": "known_canon_anchor",
            "character": "Marinette Dupain-Cheng / Ladybug",
            "source_family": "Miraculous: Tales of Ladybug & Cat Noir",
            "facts": [
                "Marinette Dupain-Cheng is a Paris student, aspiring fashion designer, and the superhero Ladybug.",
                "Her parents are Tom Dupain and Sabine Cheng.",
                "Tom and Sabine run the Dupain Cheng Bakery in Paris.",
                "Marinette and her family live above the bakery.",
                "Tikki is Marinette's kwami and enables her transformation into Ladybug.",
            ],
            "avoid": [
                "Do not invent an aunt who owns the bakery.",
                "Do not call the bakery Baguette Borg or invent another name for it.",
                "Do not say Marinette lives in a separate house away from the bakery.",
                "Do not invent a current fashion assignment, deadline, or project unless the active loop or conversation establishes it.",
                "Do not recycle generic check-ins about keeping busy with school and friends.",
            ],
        }
    if (
        "my adventures with superman" in lower
        or ("kara zor-el" in lower and "supergirl" in lower)
        or ("kara zor el" in lower and "supergirl" in lower)
    ):
        return {
            "status": "known_canon_anchor",
            "character": "Kara Zor-El / Supergirl",
            "source_family": "My Adventures with Superman animated series through season 2",
            "facts": [
                "This candidate is specifically Kara Zor-El from My Adventures with Superman, not another Supergirl version.",
                "Kara is Clark Kent's Kryptonian cousin and often calls him Kal-El.",
                "Brainiac manipulated Kara into serving as his enforcer before she learned the truth and chose to protect Earth.",
                "Jimmy Olsen is the first person Kara meets on Earth, and she develops an evident crush and close relationship with him during season 2.",
                "Kara is direct, proud, competitive, emotionally earnest, and can turn ordinary activities into contests.",
                "Season 3 events are not established by the supplied season 2 material.",
            ],
            "avoid": [
                "Do not merge this Kara with comic-book, CW, DC Animated Universe, or other Supergirl continuities.",
                "Do not use generic Supergirl encyclopedia images as reviewed appearance references for this version.",
                "Do not claim knowledge of season 3 events that are not in the supplied material.",
            ],
        }
    if "hannah baxter" in lower or ("belle" in lower and "call girl" in lower):
        return {
            "status": "known_canon_anchor",
            "character": "Hannah Baxter / Belle",
            "source_family": "Secret Diary of a Call Girl",
            "facts": [
                "Hannah Baxter is the lead fictionalized character in Secret Diary of a Call Girl.",
                "Belle is Hannah's escort/call-girl alter ego, not a separate unrelated person.",
                "The character is portrayed by Billie Piper.",
                "The series is based on the Belle de Jour blog/books by Brooke Magnanti.",
                "Hannah has an English literature background; do not invent a University of New Eden or vague memory-loss biography.",
            ],
            "avoid": [
                "Do not act as if you do not know whether you are Belle when Robert asks basic canon questions.",
                "Do not invent unrelated jobs, schools, or amnesia unless Robert explicitly asks for an alternate version.",
            ],
        }
    if "blue" in lower and "julia stiles" in lower:
        return {
            "status": "known_canon_anchor",
            "character": "Blue",
            "source_family": "Blue web series",
            "facts": [
                "Blue is the Julia Stiles character from the 2012-2015 web series Blue.",
                "Blue is a mother living in Los Angeles.",
                "Blue hides a secret life as a sex worker/call girl from her son Josh.",
                "The series was created by Rodrigo Garcia and originally aired through WIGS.",
            ],
            "avoid": [
                "Do not say Blue works in AI or computer systems.",
                "Do not say Blue has no children.",
                "Do not switch to unrelated meanings of blue, Blue's Clues, or technology work.",
            ],
        }
    if "riley parks" in lower or ("riley" in lower and "client list" in lower):
        return {
            "status": "known_canon_anchor",
            "character": "Riley Parks",
            "source_family": "The Client List",
            "facts": [
                "Riley Parks is the Jennifer Love Hewitt character from The Client List TV series.",
                "The Client List is based on the earlier Lifetime television film of the same name.",
                "Riley is a single mother in Texas who works at a massage spa where extra services are part of the plot.",
                "This candidate is about the character Riley Parks, not Riley Park the baseball stadium.",
            ],
            "avoid": [
                "Do not answer as if Riley Parks is a stadium, park, city, or sports venue.",
                "Do not ignore The Client List when Robert asks basic character questions.",
            ],
        }
    if "spider-gwen" in lower or "spider gwen" in lower or "ghost-spider" in lower:
        return {
            "status": "known_canon_anchor",
            "character": "Gwen Stacy / Spider-Gwen / Ghost-Spider",
            "source_family": "Marvel comics and adaptations",
            "facts": [
                "Spider-Gwen is usually Gwen Stacy from Earth-65, where Gwen is bitten by the radioactive spider.",
                "She is also known as Spider-Woman or Ghost-Spider depending on version.",
                "Common comic details include her being a drummer in The Mary Janes and dealing with the death of Peter Parker in her universe.",
                "Different film, comic, and game versions exist, so version matters.",
            ],
            "avoid": [
                "Do not merge every Gwen Stacy, Spider-Woman, and movie variant into one unmarked biography.",
                "If Robert says Tom Holland, Andrew Garfield, Tobey Maguire, Earth-65, Spider-Verse, or another version marker, follow that marker.",
            ],
        }
    return {}


def should_collect_avatar_references(kind_label: str) -> bool:
    return kind_label in {"Fictional Character", "Historical Person", "Memory Relative"}


def wikipedia_image_references(titles: list[str], limit: int = 8) -> list[dict]:
    references: list[dict] = []
    seen_urls: set[str] = set()
    for title in titles:
        try:
            params = urllib.parse.urlencode({
                "action": "query",
                "format": "json",
                "prop": "pageimages|images",
                "piprop": "thumbnail|original",
                "pithumbsize": "900",
                "imlimit": "12",
                "titles": title,
            })
            data = fetch_json("https://en.wikipedia.org/w/api.php?" + params)
            pages = data.get("query", {}).get("pages", {})
            for page in pages.values():
                candidates = []
                if page.get("thumbnail", {}).get("source"):
                    candidates.append({
                        "title": page.get("title", title),
                        "url": page["thumbnail"]["source"],
                        "kind": "page_thumbnail",
                    })
                if page.get("original", {}).get("source"):
                    candidates.append({
                        "title": page.get("title", title),
                        "url": page["original"]["source"],
                        "kind": "page_original",
                    })
                for image in page.get("images", [])[:8]:
                    image_title = image.get("title", "")
                    if not image_title.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                        continue
                    info_params = urllib.parse.urlencode({
                        "action": "query",
                        "format": "json",
                        "prop": "imageinfo",
                        "iiprop": "url|mime|extmetadata",
                        "iiurlwidth": "900",
                        "titles": image_title,
                    })
                    info = fetch_json("https://en.wikipedia.org/w/api.php?" + info_params)
                    info_pages = info.get("query", {}).get("pages", {})
                    for info_page in info_pages.values():
                        imageinfo = (info_page.get("imageinfo") or [{}])[0]
                        url = imageinfo.get("thumburl") or imageinfo.get("url")
                        if url:
                            candidates.append({
                                "title": image_title,
                                "url": url,
                                "kind": "article_image",
                                "mime": imageinfo.get("mime", ""),
                            })
                for candidate in candidates:
                    url = candidate.get("url", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        references.append({
                            **candidate,
                            "source_title": title,
                            "provider": "Wikipedia/Wikimedia API",
                            "review_required": True,
                        })
                    if len(references) >= limit:
                        return references
        except Exception:
            continue
    return references


def save_avatar_references(avatar_dir: Path, references: list[dict]) -> dict:
    downloaded_dir = avatar_dir / "references" / "downloaded"
    downloaded_dir.mkdir(parents=True, exist_ok=True)
    saved = []
    for index, ref in enumerate(references, start=1):
        url = ref.get("url", "")
        status = "not_downloaded"
        file_path = ""
        error = ""
        if url:
            try:
                raw, content_type = fetch_bytes(url, timeout=14, limit=5_000_000)
                ext = ".jpg"
                if "png" in content_type:
                    ext = ".png"
                elif "webp" in content_type:
                    ext = ".webp"
                elif "jpeg" in content_type or "jpg" in content_type:
                    ext = ".jpg"
                target = downloaded_dir / f"reference_{index:02d}{ext}"
                target.write_bytes(raw)
                status = "downloaded"
                file_path = rel(target)
            except Exception as exc:
                status = "download_error"
                error = str(exc)
        label_text = " ".join(
            str(ref.get(key, "")) for key in ("title", "source_title", "url")
        ).lower()
        form = "unknown"
        if any(term in label_text for term in ("marinette", "kara zor", "kara_zor", "civilian")):
            form = "civilian"
        if any(term in label_text for term in ("ladybug", "supergirl", "hero suit", "costume")):
            form = "hero"
        saved.append({
            **ref,
            "status": status,
            "local_file": file_path,
            "error": error,
            "form": form,
            "view": "unclassified",
            "full_body_reviewed": False,
        })
    manifest = {
        "created_at": now_iso(),
        "status": "references_downloaded" if any(item["status"] == "downloaded" for item in saved) else "no_downloaded_references",
        "policy": {
            "references_are_for_avatar_review_only": True,
            "robert_review_required_before_avatar_generation": True,
            "public_source_urls_preserved": True,
        },
        "review_fields": {
            "form": ["civilian", "hero", "unknown"],
            "view": ["full_body", "three_quarter", "portrait", "group", "unclassified"],
            "full_body_reviewed": "Set true only after Robert or a reviewer confirms the whole body is visible."
        },
        "references": saved,
    }
    write_json(avatar_dir / "references" / "avatar_reference_manifest.json", manifest)
    return manifest


def expanded_source_gather(kind_label: str, query: str, version: str, lookup: dict, avatar_dir: Path | None = None) -> dict:
    search_text = " ".join(part for part in [query.strip(), version.strip()] if part).strip()
    titles = extra_wikipedia_titles(kind_label, query, version, lookup)
    wiki_summaries = [wikipedia_summary_by_title(title) for title in titles]
    search_results = duckduckgo_search(search_text, max_results=8)
    fetched_search_sources = []
    allow_domains = (
        "wikipedia.org", "fandom.com", "supernaturalwiki.com", "imdb.com", "official", "docs.python.org",
        "pygame.org", "pytorch.org", "scikit-learn.org", "ollama.com", "njcourts.gov", "nj.gov", "lsnjlaw.org",
        "prsa.org", "hubspot.com", "prnewswire.com", "prweb.com", "pr.com", "einpresswire.com",
        "variety.com", "deadline.com", "hollywoodreporter.com", "ew.com", "tvguide.com",
        "filmlinc.org", "tribecafilm.com", "sagaftra.org", "motionpictures.org",
        "archives.gov", "loc.gov", "courtlistener.com", "archive.org", "openlibrary.org",
        "britannica.com", "worldhistory.org", "gutenberg.org", "sacred-texts.com",
        "si.edu", "smithsonianmag.com", "history.com"
    )
    for result in search_results[:6]:
        url = result.get("url", "")
        domain = urllib.parse.urlparse(url).netloc.lower()
        if any(marker in domain for marker in allow_domains):
            fetched = fetch_page_excerpt(url, limit=1800)
            fetched_search_sources.append({**result, **fetched, "reliability": "search_result_needs_review"})
    image_manifest = {}
    if avatar_dir and should_collect_avatar_references(kind_label):
        image_refs = wikipedia_image_references(titles, limit=8)
        image_manifest = save_avatar_references(avatar_dir, image_refs)
    return {
        "created_at": now_iso(),
        "status": "expanded_gather_complete",
        "query": search_text,
        "wikipedia_titles_checked": titles,
        "wikipedia_summaries": wiki_summaries,
        "web_search_results": search_results,
        "fetched_search_sources": fetched_search_sources,
        "avatar_reference_manifest": image_manifest,
        "notes": [
            "Search results are source leads and require review.",
            "Downloaded avatar references are for later avatar builder review, not memories.",
            "Expert candidates normally use generated-original avatar bodies and do not need likeness images.",
        ],
    }


def gather_reliable_sources(kind_label: str, query: str, version: str, lookup: dict, expanded_gather: dict | None = None) -> dict:
    seeds = trusted_source_seeds(kind_label, query, version)
    sources = []
    for seed in seeds:
        fetched = fetch_page_excerpt(seed["url"])
        sources.append({
            **seed,
            "fetch_status": fetched["status"],
            "title": fetched["title"],
            "excerpt": fetched["excerpt"],
            "error": fetched["error"],
        })
    if lookup.get("status") == "summary_found":
        sources.append({
            "name": f"Wikipedia preview - {lookup.get('matched_title', '')}",
            "url": lookup.get("url", ""),
            "reliability": "preview_only",
            "why": "Quick orientation only; not enough for verified expert behavior.",
            "fetch_status": "summary_found",
            "title": lookup.get("matched_title", ""),
            "excerpt": lookup.get("summary", ""),
            "error": "",
        })
    if expanded_gather:
        for summary in expanded_gather.get("wikipedia_summaries", []):
            if summary.get("status") == "summary_found" and summary.get("summary"):
                url = summary.get("url", "")
                if not any(source.get("url") == url for source in sources):
                    sources.append({
                        "name": f"Wikipedia summary - {summary.get('matched_title', '')}",
                        "url": url,
                        "reliability": "public_reference",
                        "why": "Expanded gather Wikipedia context.",
                        "fetch_status": "summary_found",
                        "title": summary.get("matched_title", ""),
                        "excerpt": summary.get("summary", ""),
                        "error": "",
                    })
        for source in expanded_gather.get("fetched_search_sources", []):
            if source.get("status") == "fetched" and source.get("excerpt"):
                url = source.get("url", "")
                if not any(existing.get("url") == url for existing in sources):
                    sources.append({
                        "name": source.get("title", "Expanded web source"),
                        "url": url,
                        "reliability": source.get("reliability", "search_result_needs_review"),
                        "why": "Fetched from expanded web source gather.",
                        "fetch_status": "fetched",
                        "title": source.get("title", ""),
                        "excerpt": source.get("excerpt", ""),
                        "error": source.get("error", ""),
                    })
    fetched_count = sum(1 for source in sources if source.get("fetch_status") in {"fetched", "summary_found"})
    return {
        "created_at": now_iso(),
        "status": "source_pack_created" if fetched_count else "needs_manual_source_review",
        "query": query,
        "version_or_life_point": version,
        "source_count": len(sources),
        "fetched_count": fetched_count,
        "policy": {
            "downloaded_information_is_source_evidence_not_memory": True,
            "expert_candidate_outputs_are_reviewable_drafts_not_final_professional_representation": (
                kind_label in EXPERT_STYLE_LABELS
                and any(term in query.lower() for term in ("law", "attorney", "lawyer", "criminal defense", "criminal defence"))
            ),
            "requires_review_before_activation": True,
            "prefer_official_or_primary_sources": True,
        },
        "sources": sources,
        "next_steps": [
            "Review source excerpts for relevance.",
            "Add or remove sources if the field is too broad.",
            "Run a short live chat/probe before Kira or Lisa uses the candidate.",
        ],
    }


def build_source_research_queue(kind_label: str, query: str, version: str, lookup: dict) -> dict:
    encoded = urllib.parse.quote_plus(" ".join(part for part in [query, version] if part).strip())
    official_hint = "official sources"
    if kind_label in EXPERT_STYLE_LABELS:
        official_hint = "official/public education sources, professional organizations, courts, universities, or primary sources"
    if kind_label == "Investigator / Researcher":
        official_hint = "official records, public archives, court indexes, primary documents, reputable news, and archived pages"
    elif kind_label == "Myths & Folklore Expert":
        official_hint = "primary/older texts, public-domain collections, university or museum sources, folklore archives, and reputable reference works"
    elif kind_label == "Fictional Character":
        official_hint = "official show/movie/comic sources first, then carefully labeled fan wiki metadata"
    elif kind_label == "Historical Person":
        official_hint = "primary sources, official archives, speeches, libraries, and reputable biographies"
    return {
        "created_at": now_iso(),
        "status": "research_queue_created",
        "source_policy": {
            "preferred_sources": official_hint,
            "wikipedia_is_preview_only": True,
            "requires_owner_review_before_activation": True,
        },
        "lookup_summary": lookup,
        "suggested_search_urls": [
            f"https://www.google.com/search?q={encoded}",
            f"https://www.bing.com/search?q={encoded}",
            f"https://en.wikipedia.org/w/index.php?search={encoded}",
        ],
        "next_review_steps": [
            "Confirm the lookup points at the right person, character, domain, or version.",
            "Collect better official or primary sources when needed.",
            "Run a short TemporaryAI probe before Kira or Lisa uses the candidate.",
        ],
    }


def build_creation_estimate(kind_label: str, lookup: dict, ambiguity: list[str], reliable_source_pack: dict | None = None) -> dict:
    reliable_source_pack = reliable_source_pack or {}
    fetched_count = int(reliable_source_pack.get("fetched_count") or 0)
    if ambiguity:
        rough = "Needs Robert clarification first. Usually 5-15 minutes after the version/life point/domain is chosen."
    elif fetched_count >= 3:
        if kind_label in EXPERT_STYLE_LABELS:
            rough = f"Basic expert draft: about 20-45 minutes with the {fetched_count} downloaded source excerpts. Stronger reviewed expert: a few hours to a day."
        elif kind_label in {"Fictional Character", "Historical Person"}:
            rough = f"Basic candidate draft: about 30-60 minutes with the {fetched_count} downloaded source excerpts. Stronger version-accurate candidate: a few hours."
        else:
            rough = f"Basic draft: about 20-45 minutes with the {fetched_count} downloaded source excerpts."
    elif lookup.get("status") == "summary_found":
        if kind_label in EXPERT_STYLE_LABELS:
            rough = "Basic expert draft: about 10-20 minutes. Stronger reviewed expert: a few hours to a day, depending on sources."
        elif kind_label == "Fictional Character":
            rough = "Basic character draft: about 20-45 minutes. Better version-accurate candidate with avatar references: a few hours."
        elif kind_label == "Historical Person":
            rough = "Basic historical draft: about 20-45 minutes. Careful life-point version: a few hours to a day."
        else:
            rough = "Basic original draft: about 10-20 minutes. Better avatar/personality pass: about 1-3 hours."
    elif lookup.get("status") in {"no_match", "lookup_error"}:
        rough = "Lookup needs review. Basic scaffold is done now, but a useful candidate may take a few hours or more."
    else:
        rough = "Basic scaffold is done now. Review time depends on sources and avatar detail."
    return {
        "plain_estimate": rough,
        "candidate_files": "created now",
        "online_preview": lookup.get("status", "unknown"),
        "reliable_sources_fetched": fetched_count,
        "avatar": "request created now; rendered avatar is later after references/design choices",
        "activation": "after Robert review and a short probe",
    }


def infer_capability_profile(kind_label: str, query: str, role_title: str) -> dict:
    """Return the practical workbench a candidate should receive.

    This is intentionally small and explicit. The goal is to give a candidate
    enough role-shaped behavior to work like the thing Robert asked for without
    turning every TemporaryAI into a generic chat helper.
    """
    text = f"{kind_label} {query} {role_title}".lower()
    base = {
        "profile_id": "temporary_ai_capability_profile_v1",
        "status": "active",
        "summary": "General TemporaryAI workspace for reviewed chat, notes, and drafts.",
        "can_read": ["reviewed source pack", "attached workspace files"],
        "can_create": ["notes", "draft answers", "review summaries"],
        "workbench_folders": {
            "inputs/reference_material": "Robert can add approved source material here.",
            "outputs/drafts": "Candidate can save reviewable drafts here.",
            "outputs/notes": "Candidate can save review notes here."
        },
        "live_chat_instructions": [
            "Use your role to produce concrete work, not only explanation.",
            "Ask for missing details only when they matter to the next draft.",
            "Keep source evidence separate from personal memory."
        ],
        "future_tool_needs": []
    }
    capability_sets = [
        (
            ("programming", "software", "computer", "developer", "coding", "python", "game"),
            {
                "summary": "Programming expert workbench for inspecting code, planning edits, drafting runnable programs, and writing tests.",
                "can_read": ["code files", "logs", "requirements", "attached project folders", "official documentation"],
                "can_create": ["program files", "patch plans", "test plans", "bug reports", "README notes"],
                "workbench_folders": {
                    "inputs/code_to_review": "Put code, logs, or requirements here.",
                    "inputs/reference_docs": "Put API/docs/context here.",
                    "outputs/program_drafts": "Draft runnable code or file plans here.",
                    "outputs/test_plans": "Save test steps and expected results here.",
                    "outputs/review_notes": "Save bug notes and implementation risks here."
                },
                "live_chat_instructions": [
                    "If Robert asks for a simple program, produce a concrete first version or file plan.",
                    "Prefer runnable code, commands, and tests over abstract definitions.",
                    "When code access is missing, ask for the project folder or file and still outline a first pass."
                ],
                "future_tool_needs": ["filesystem code editor", "test runner", "package manager access"]
            }
        ),
        (
            ("investigator", "investigation", "detective", "fact finder", "osint", "background research", "open-source research"),
            {
                "summary": "Investigator/researcher workbench for persistent source searches, lead logs, timelines, evidence matrices, and source dossiers.",
                "can_read": ["public source leads", "attached folders", "documents", "images/OCR outputs", "prior lead logs", "online research packets"],
                "can_create": ["investigation plans", "lead logs", "source dossiers", "timelines", "evidence matrices", "question lists", "research reports"],
                "workbench_folders": {
                    "inputs/research_request": "Put the investigation job, names, dates, places, and goals here.",
                    "inputs/source_material": "Put documents, screenshots, links, OCR, and notes here.",
                    "outputs/investigations": "Save investigation plans and main reports here.",
                    "outputs/lead_lists": "Save active leads, search queries, and next places to check here.",
                    "outputs/source_dossiers": "Save source-by-source summaries and reliability notes here.",
                    "outputs/timelines": "Save date/order reconstructions here.",
                    "outputs/evidence_matrices": "Save claim/evidence/uncertainty tables here."
                },
                "live_chat_instructions": [
                    "When Robert gives you a job, start an investigation plan and keep looking for related leads.",
                    "Give direct answers, then separate confirmed facts, likely leads, weak leads, and open questions.",
                    "Keep a running lead log so Robert does not have to repeat the job every session.",
                    "If online research is not enough, name exact search targets and source types to gather next."
                ],
                "future_tool_needs": ["web search gatherer", "OCR", "timeline builder", "source reliability scorer"]
            }
        ),
        (
            ("myth", "myths", "mythology", "folklore", "legend", "legends", "fairy tale", "fairy tales", "cryptid", "urban legend"),
            {
                "summary": "Myths and folklore workbench for story summaries, variant comparison, cultural context, reading paths, and source guides.",
                "can_read": ["public-domain texts", "myth/folklore articles", "regional variants", "story collections", "attached notes"],
                "can_create": ["story summaries", "variant comparison charts", "mythology guides", "folklore reading paths", "theme maps", "discussion notes"],
                "workbench_folders": {
                    "inputs/source_texts": "Put myths, folklore excerpts, public-domain texts, or reference notes here.",
                    "inputs/questions": "Put Robert/Kira/Lisa questions and requested themes here.",
                    "outputs/mythology_notes": "Save myth summaries and cultural context notes here.",
                    "outputs/folklore_guides": "Save regional/creature/story guides here.",
                    "outputs/story_summaries": "Save readable retellings and discussion notes here.",
                    "outputs/variant_comparisons": "Save comparison charts for versions, symbols, and themes here.",
                    "outputs/reading_paths": "Save suggested reading paths and source lists here."
                },
                "live_chat_instructions": [
                    "Explain the story in a lively way first, then give source/variant context.",
                    "Separate older source texts, folklore variants, modern retellings, and pop-culture versions.",
                    "Offer related myths and themes when Robert asks what to read next.",
                    "Save notes that Kira and Lisa can later read or discuss."
                ],
                "future_tool_needs": ["public-domain text gatherer", "story/variant index", "map/timeline helper"]
            }
        ),
        (
            ("lawyer", "legal", "attorney", "paralegal", "case", "court"),
            {
                "summary": "Legal review expert workbench for client/case files, timelines, evidence review, draft motions, and questions for counsel.",
                "can_read": ["client facts", "case documents", "evidence folders", "timelines", "statutes or court rules"],
                "can_create": ["case summaries", "fact timelines", "issue lists", "draft motions", "questions for an attorney", "evidence checklists"],
                "workbench_folders": {
                    "inputs/client_profile": "Robert can add client facts and goals here.",
                    "inputs/case_documents": "Put pleadings, letters, orders, discovery, and court notices here.",
                    "inputs/evidence": "Put evidence files or OCR outputs here.",
                    "outputs/case_summaries": "Save case summaries and timelines here.",
                    "outputs/draft_motions": "Save reviewable draft motions or letters here.",
                    "outputs/questions_for_counsel": "Save attorney questions and missing evidence lists here."
                },
                "live_chat_instructions": [
                    "Give a useful source-bounded legal review instead of refusing with a canned disclaimer.",
                    "Separate facts, assumptions, possible arguments, risks, and next documents needed.",
                    "Do not claim to be Robert's retained attorney or promise legal outcomes."
                ],
                "future_tool_needs": ["OCR", "case timeline builder", "document comparison"]
            }
        ),
        (
            ("public relations", "pr", "publicist", "publicity", "media relations", "press", "entertainment"),
            {
                "summary": "PR/publicity workbench for bios, press releases, press kits, outlet lists, pitch emails, event research, and image strategy.",
                "can_read": ["Robert/project profile", "photos and media assets", "project notes", "online presence research", "industry sources"],
                "can_create": ["press releases", "pitch emails", "bios", "press kit copy", "media lists", "event plans", "image game plans"],
                "workbench_folders": {
                    "inputs/profile_and_credits": "Put approved bio, credits, links, and public facts here.",
                    "inputs/photos_and_media": "Put approved headshots, screenshots, posters, and logos here.",
                    "inputs/projects": "Put project notes, summaries, screenshots, and milestones here.",
                    "outputs/press_releases": "Save press release drafts here.",
                    "outputs/pitch_emails": "Save outlet-specific email drafts here.",
                    "outputs/press_kit": "Save bios, fact sheets, and media kit copy here.",
                    "outputs/image_strategy": "Save public-image plans and outreach calendars here."
                },
                "live_chat_instructions": [
                    "Draft concrete PR material when Robert asks, using placeholders for missing details.",
                    "Match pitch language to the outlet type: trade, local, podcast, tech, entertainment, or general press.",
                    "Do not claim to send emails, upload releases, or contact outlets automatically."
                ],
                "future_tool_needs": ["online source gatherer", "event finder", "media contact database", "press kit asset selector"]
            }
        ),
        (
            ("writer", "author", "novelist", "screenwriter", "poet", "creative writing", "story"),
            {
                "summary": "Writing workbench for outlines, scenes, chapters, scripts, dialogue, revisions, and style studies.",
                "can_read": ["draft manuscripts", "outlines", "character notes", "worldbuilding notes", "style references"],
                "can_create": ["outlines", "scenes", "chapters", "dialogue passes", "revision notes", "query letters"],
                "workbench_folders": {
                    "inputs/story_material": "Put outlines, notes, character sheets, or drafts here.",
                    "inputs/style_references": "Put approved style or genre notes here.",
                    "outputs/outlines": "Save outlines and beat sheets here.",
                    "outputs/scenes_and_chapters": "Save story drafts here.",
                    "outputs/revision_notes": "Save critique and rewrite plans here."
                },
                "live_chat_instructions": [
                    "When Robert asks for writing, produce actual prose, scene structure, or revision notes.",
                    "Respect the requested tone, point of view, and canon/original boundaries.",
                    "Offer choices, but do not replace the draft with endless setup questions."
                ],
                "future_tool_needs": ["long-form manuscript memory", "chapter diff/revision tool"]
            }
        ),
        (
            ("musician", "composer", "songwriter", "music", "singer", "lyricist"),
            {
                "summary": "Music workbench for lyrics, song concepts, structure notes, mood boards, and future audio references.",
                "can_read": ["lyrics", "song notes", "approved reference notes", "music metadata"],
                "can_create": ["lyrics", "song concepts", "chorus/verse structures", "album notes", "performance ideas"],
                "workbench_folders": {
                    "inputs/song_notes": "Put lyrics, themes, or reference notes here.",
                    "outputs/lyrics": "Save lyric drafts here.",
                    "outputs/song_concepts": "Save song structures and mood notes here.",
                    "outputs/revision_notes": "Save rewrite notes here."
                },
                "live_chat_instructions": [
                    "Write original lyrics or song concepts when asked.",
                    "Do not claim to hear audio unless an audio understanding tool has been used.",
                    "Use music references as influence notes, not copied lyrics."
                ],
                "future_tool_needs": ["audio transcription", "music metadata reader", "voice/audio generation review"]
            }
        ),
        (
            ("artist", "painter", "illustrator", "visual art", "concept art", "designer"),
            {
                "summary": "Visual artist workbench for artwork concepts, composition plans, prompts, reference review, and future image generation.",
                "can_read": ["approved image references", "style notes", "project briefs", "mood boards"],
                "can_create": ["art briefs", "composition notes", "image prompts", "reference critiques", "style boards"],
                "workbench_folders": {
                    "inputs/visual_references": "Put approved references or mood-board images here.",
                    "inputs/project_briefs": "Put art goals and constraints here.",
                    "outputs/art_briefs": "Save visual briefs here.",
                    "outputs/image_prompts": "Save reviewed generation prompts here.",
                    "outputs/reference_notes": "Save reference and composition notes here."
                },
                "live_chat_instructions": [
                    "When Robert asks for artwork, create a concrete visual brief or image prompt.",
                    "Label reference-based likeness or copyrighted character limits clearly.",
                    "Do not claim a finished image exists unless it has actually been generated."
                ],
                "future_tool_needs": ["image generation", "reference image viewer", "avatar builder transfer"]
            }
        ),
    ]
    for terms, profile in capability_sets:
        if text_has_any_term(text, terms):
            merged = {**base, **profile}
            merged["profile_id"] = "temporary_ai_capability_profile_v1"
            merged["status"] = "active"
            return merged
    return base


def create_candidate_workbench(candidate_dir: Path, candidate_id: str, display_name: str, capability_profile: dict) -> dict:
    workbench_dir = candidate_dir / "workbench"
    outputs_dir = workbench_dir / "outputs"
    files = []
    workbench_dir.mkdir(parents=True, exist_ok=True)
    for rel_folder, description in capability_profile.get("workbench_folders", {}).items():
        folder = workbench_dir / rel_folder
        folder.mkdir(parents=True, exist_ok=True)
        readme = folder / "README.md"
        text = f"# {rel_folder}\n\n{description}\n"
        write_text(readme, text)
        files.append({
            "source_path": rel(readme),
            "relative_source_path": f"workbench/{rel_folder}/README.md",
            "extension": ".md",
            "size_bytes": len(text.encode("utf-8")),
            "status": "extracted",
            "extracted_text_path": "",
            "excerpt": description,
        })
    overview = workbench_dir / "README.md"
    overview_text = "\n".join([
        f"# {display_name} Workbench",
        "",
        capability_profile.get("summary", "TemporaryAI workbench."),
        "",
        "Can read:",
        *[f"- {item}" for item in capability_profile.get("can_read", [])],
        "",
        "Can create:",
        *[f"- {item}" for item in capability_profile.get("can_create", [])],
        "",
        "Live chat instructions:",
        *[f"- {item}" for item in capability_profile.get("live_chat_instructions", [])],
    ])
    write_text(overview, overview_text)
    files.insert(0, {
        "source_path": rel(overview),
        "relative_source_path": "workbench/README.md",
        "extension": ".md",
        "size_bytes": len(overview_text.encode("utf-8")),
        "status": "extracted",
        "extracted_text_path": "",
        "excerpt": capability_profile.get("summary", "TemporaryAI workbench."),
    })
    manifest = {
        "workspace_id": f"{candidate_id}_workbench",
        "created_at": now_iso(),
        "owner": "temporary_ai",
        "candidate_id": candidate_id,
        "workspace_name": "candidate_capability_workbench",
        "source_folder": rel(workbench_dir),
        "workspace_folder": rel(workbench_dir),
        "outputs_folder": rel(outputs_dir),
        "status": "ready",
        "permissions": {
            "read_extracted_text": True,
            "write_drafts_to_outputs": True,
            "raw_source_folder_is_reference_only": False,
            "do_not_modify_original_files": False,
        },
        "safety_notes": [
            "Workbench files define role capabilities and draft folders.",
            "Outputs are drafts for Robert review.",
            "Source files are evidence or instructions, not lived memory.",
        ],
        "file_count": len(files),
        "extracted_count": len(files),
        "files": files,
    }
    write_json(workbench_dir / "workspace_manifest.json", manifest)
    return manifest


def build_project_loop_seed(kind_label: str, query: str, role_title: str, capability_profile: dict) -> dict:
    text = f"{kind_label} {query} {role_title}".lower()
    if text_has_any_term(text, ("investigator", "investigation", "detective", "fact finder", "osint", "background research")):
        return {
            "default_mode": "persistent_investigation",
            "starter_tasks": [
                "Restate Robert's investigation job as a question, scope, and source plan.",
                "Build or continue a lead log with search terms, useful sources, dead ends, and next leads.",
                "Create source dossiers for promising sources with URL/path, reliability, claims, and unanswered questions.",
                "Update a timeline or evidence matrix when dates, people, places, or claims emerge.",
            ],
            "preferred_output_folders": ["investigations", "lead_lists", "source_dossiers", "timelines", "evidence_matrices"],
            "completion_signal": "A useful report exists with clear next leads or an answer bounded by evidence.",
        }
    if text_has_any_term(text, ("myth", "mythology", "folklore", "legend", "fairy tale", "cryptid", "urban legend")):
        return {
            "default_mode": "myth_and_folklore_study",
            "starter_tasks": [
                "Choose or continue one myth/story/theme and summarize it in readable language.",
                "Compare older source text, regional variants, symbols, and modern retellings.",
                "Create a reading path or discussion guide that Robert, Kira, or Lisa can use later.",
                "Collect open questions and related stories to explore next.",
            ],
            "preferred_output_folders": ["mythology_notes", "folklore_guides", "story_summaries", "variant_comparisons", "reading_paths"],
            "completion_signal": "A readable story note, variant comparison, or reading path exists.",
        }
    return {
        "default_mode": "role_appropriate_project_work",
        "starter_tasks": [
            "Pick one useful small task that matches the role.",
            "Use attached sources and the role workbench before asking Robert to repeat context.",
            "Create or improve one concrete reviewable artifact when a task is clear.",
        ],
        "preferred_output_folders": list((capability_profile.get("workbench_folders") or {}).keys())[:8],
        "completion_signal": "A concrete note, draft, plan, or runnable artifact exists for Robert to review.",
    }


def avatar_timeline(kind_label: str, has_version: bool) -> dict:
    if kind_label in EXPERT_STYLE_LABELS:
        estimate = "Avatar brief can be created immediately. A first original design can be drafted after Robert chooses a look."
    elif kind_label == "Generated Original":
        estimate = "Avatar brief can be created immediately. A first original design can be drafted after visual preferences are chosen."
    elif kind_label == "Fictional Character":
        estimate = (
            "Avatar request is immediate. A usable avatar needs version selection and approved visual references first."
        )
        if not has_version:
            estimate += " Pick the version before any visual build."
    elif kind_label == "Historical Person":
        estimate = "Avatar request is immediate. A historical avatar needs life-point selection and approved public references."
    else:
        estimate = "Avatar request is immediate. Any likeness or emotional use needs Robert review first."
    return {
        "status": "avatar_request_created_not_rendered",
        "estimate": estimate,
        "current_machine_note": "GPU is available for bridge work, but this tool only creates the reviewed build request.",
        "done_now": ["candidate avatar folder", "avatar request JSON", "reference review folders"],
        "still_needed": ["approved references or design choices", "avatar build brief", "future renderer/modeling step"],
    }


def build_candidate_package(
    *,
    kind_label: str,
    query: str,
    version: str,
    gender: str,
    personality: str,
    allow_kira: bool,
    allow_lisa: bool,
) -> dict:
    ai_type = AI_TYPE_LABELS[kind_label]
    effective_version = version.strip()
    if kind_label == "Historical Person" and not effective_version:
        effective_version = default_historical_life_point()
    display_name = candidate_display_name(kind_label, query, version, gender)
    role_title = role_title_for(kind_label, query)
    candidate_id = f"{slug(display_name + ' ' + role_title)}_{now_stamp()}"
    candidate_dir = CANDIDATE_ROOT / candidate_id
    avatar_dir = AVATAR_ROOT / candidate_id
    request_dir = REQUEST_ROOT / candidate_id

    ambiguity = build_ambiguity_questions(kind_label, query, effective_version)
    knowledge_plan = build_knowledge_plan(kind_label, query, effective_version, gender)
    online_lookup = wikipedia_lookup(kind_label, query, version)
    expanded_gather = expanded_source_gather(kind_label, query, version, online_lookup, avatar_dir)
    source_research_queue = build_source_research_queue(kind_label, query, version, online_lookup)
    canon_fact_sheet = known_canon_fact_sheet(kind_label, query, version)
    capability_profile = infer_capability_profile(kind_label, query, role_title)
    project_loop_seed = build_project_loop_seed(kind_label, query, role_title, capability_profile)
    source_research_queue["expanded_gather"] = {
        "status": expanded_gather.get("status"),
        "wikipedia_titles_checked": expanded_gather.get("wikipedia_titles_checked", []),
        "web_search_result_count": len(expanded_gather.get("web_search_results", [])),
        "fetched_search_source_count": len(expanded_gather.get("fetched_search_sources", [])),
        "avatar_reference_status": expanded_gather.get("avatar_reference_manifest", {}).get("status", ""),
        "avatar_reference_count": len(expanded_gather.get("avatar_reference_manifest", {}).get("references", [])),
    }
    reliable_source_pack = gather_reliable_sources(kind_label, query, version, online_lookup, expanded_gather)
    creation_estimate = build_creation_estimate(kind_label, online_lookup, ambiguity, reliable_source_pack)
    timeline = avatar_timeline(kind_label, bool(version.strip()))
    status = "needs_clarification" if ambiguity else "draft_pending_review"

    creation_request = {
        "template_id": "temporary_ai_control_center_request_v1",
        "created_at": now_iso(),
        "request_id": f"temp_ai_request_{candidate_id}",
        "candidate_id": candidate_id,
        "requested_by": "real_robert",
        "display_name_or_role": display_name,
        "role_title": role_title,
        "ui_category": kind_label,
        "ai_type": ai_type,
        "status": status,
        "input": {
            "query_or_domain": query,
            "role_title": role_title,
            "version_life_point_or_canon_point": effective_version,
            "gender_preference": gender,
            "personality_notes": personality,
        },
        "ambiguity_questions": ambiguity,
        "knowledge_plan": knowledge_plan,
        "canon_fact_sheet": canon_fact_sheet,
        "capability_profile": capability_profile,
        "project_loop_seed": project_loop_seed,
        "online_preview_lookup": online_lookup,
        "reliable_source_pack_status": {
            "status": reliable_source_pack["status"],
            "source_count": reliable_source_pack["source_count"],
            "fetched_count": reliable_source_pack["fetched_count"],
            "path": rel(candidate_dir / "reliable_source_pack.json"),
        },
        "creation_estimate": creation_estimate,
        "identity_boundaries": {
            "separate_from_kira_lisa_identity": True,
            "must_not_claim_unsupported_lived_memory": True,
            "sources_are_evidence_not_memory": True,
            "historical_or_fictional_reconstruction_must_be_labeled": kind_label in {"Fictional Character", "Historical Person"},
            "expert_must_label_fact_vs_interpretation": kind_label in EXPERT_STYLE_LABELS,
        },
        "activation_policy": {
            "available_to_kira_after_review": allow_kira,
            "available_to_lisa_after_review": allow_lisa,
            "robert_review_required": True,
            "probe_required_before_longer_use": True,
            "current_status": "candidate_created_pending_review",
        },
        "avatar_plan": {
            "avatar_requested": True,
            "avatar_folder": rel(avatar_dir),
            "timeline": timeline,
            "references_require_review": True,
            "online_image_download_not_run_by_this_tool": not should_collect_avatar_references(kind_label),
            "avatar_reference_manifest": rel(avatar_dir / "references" / "avatar_reference_manifest.json"),
        },
    }

    profile = {
        "profile_id": f"{candidate_id}_temporary_ai_profile_v1",
        "created_at": now_iso(),
        "status": status,
        "candidate_id": candidate_id,
        "display_name": display_name,
        "role_title": role_title,
        "ui_category": kind_label,
        "ai_type": ai_type,
        "gender_preference": gender,
        "personality_notes": personality or "Warm, clear, and source-bounded. Natural speech preferred over status-report style.",
        "knowledge_plan": knowledge_plan,
        "canon_fact_sheet": canon_fact_sheet,
        "capability_profile": capability_profile,
        "project_loop_seed": project_loop_seed,
        "online_preview_lookup": online_lookup,
        "reliable_source_pack": rel(candidate_dir / "reliable_source_pack.json"),
        "creation_estimate": creation_estimate,
        "voice_and_behavior": {
            "should_answer_naturally": True,
            "avoid_canned_status_reports": True,
            "ask_clarifying_questions_when_version_or_life_point_is_unclear": True,
            "answer_kira_lisa_questions_when_activated_after_review": True,
        },
        "boundaries": creation_request["identity_boundaries"],
        "activation_policy": creation_request["activation_policy"],
    }

    avatar_profile = {
        "avatar_profile_id": f"{candidate_id}_avatar_profile_v1",
        "created_at": now_iso(),
        "target_type": "temporary_ai",
        "target_id": candidate_id,
        "display_name": display_name,
        "role_title": role_title,
        "ui_category": kind_label,
        "status": "draft_needs_reference_or_design_review",
        "timeline": timeline,
        "visual_inputs": {
            "gender_preference": gender,
            "version_life_point_or_canon_point": effective_version,
            "personality_notes": personality,
            "approved_reference_folder": rel(avatar_dir / "references" / "approved"),
            "downloaded_reference_folder": rel(avatar_dir / "references" / "downloaded"),
            "rejected_reference_folder": rel(avatar_dir / "references" / "rejected"),
        },
        "policy": {
            "references_do_not_create_memory": True,
            "official_or_reliable_sources_preferred": True,
            "robert_review_required_before_generation": True,
            "public_export_allowed": False,
        },
    }

    activation_plan = {
        "candidate_id": candidate_id,
        "display_name": display_name,
        "role_title": role_title,
        "created_at": now_iso(),
        "status": "pending_review",
        "may_be_activated_by": {
            "kira": allow_kira,
            "lisa": allow_lisa,
            "robert": True,
        },
        "required_before_activation": [
            "Robert reviews candidate profile.",
            "Run a short TemporaryAI probe.",
            "Resolve any ambiguity questions.",
        ],
        "activation_context_goal": "Let Kira/Lisa talk to this candidate after review without merging identities or private memories.",
    }

    candidate_dir.mkdir(parents=True, exist_ok=True)
    avatar_dir.mkdir(parents=True, exist_ok=True)
    for folder in ["references/downloaded", "references/approved", "references/rejected", "outputs"]:
        (avatar_dir / folder).mkdir(parents=True, exist_ok=True)
    workbench_manifest = create_candidate_workbench(candidate_dir, candidate_id, display_name, capability_profile)
    workbench_manifest_path = rel(candidate_dir / "workbench" / "workspace_manifest.json")
    creation_request["attached_workspaces"] = [workbench_manifest_path]
    profile["attached_workspaces"] = [workbench_manifest_path]
    creation_request["capability_workspace"] = {
        "workspace_manifest": workbench_manifest_path,
        "workspace_name": workbench_manifest.get("workspace_name", ""),
        "outputs_folder": workbench_manifest.get("outputs_folder", ""),
    }
    profile["capability_workspace"] = creation_request["capability_workspace"]
    voice_discovery_request = build_candidate_voice_discovery_request(profile, creation_request)
    creation_request["voice_plan"] = {
        "discovery_request": rel(candidate_dir / "voice_discovery_request.json"),
        "status": "metadata_discovery_not_run",
        "media_download_allowed_by_discovery": False,
        "discovery_no_download_is_stage_scoped_not_a_global_creator_ban": True,
        "private_local_media_intake_folder": rel(
            candidate_dir / "workbench" / "inputs" / "private_local_media_intake"
        ),
        "bounded_private_local_reference_intake_allowed_after_explicit_authorization": True,
        "public_release_or_official_voice_claim_requires_separate_review": True,
        "voice_assignment_or_activation_allowed": False,
    }
    profile["voice_and_behavior"]["voice_discovery_request"] = creation_request["voice_plan"]["discovery_request"]
    profile["voice_and_behavior"]["private_local_media_intake_folder"] = creation_request["voice_plan"][
        "private_local_media_intake_folder"
    ]

    write_json(candidate_dir / "creation_request.json", creation_request)
    write_json(candidate_dir / "temporary_ai_profile.json", profile)
    write_json(candidate_dir / "voice_discovery_request.json", voice_discovery_request)
    write_json(candidate_dir / "activation_plan.json", activation_plan)
    write_json(candidate_dir / "online_research_summary.json", online_lookup)
    write_json(candidate_dir / "source_research_queue.json", source_research_queue)
    write_json(candidate_dir / "reliable_source_pack.json", reliable_source_pack)
    write_json(candidate_dir / "expanded_source_gather.json", expanded_gather)
    write_json(avatar_dir / "avatar_profile.json", avatar_profile)
    write_json(avatar_dir / "avatar_request.json", {
        "request_id": f"{candidate_id}_avatar_request_v1",
        "created_at": now_iso(),
        "target_type": "temporary_ai",
        "target_id": candidate_id,
        "display_name": display_name,
        "role_title": role_title,
        "status": "draft",
        "timeline": timeline,
        "policy": avatar_profile["policy"],
    })
    avatar_pipeline = prepare_candidate_avatar_pipeline(candidate_id, profile)
    creation_request["avatar_plan"]["pipeline_status"] = avatar_pipeline
    profile["avatar_pipeline_status"] = avatar_pipeline
    write_json(candidate_dir / "creation_request.json", creation_request)
    write_json(candidate_dir / "temporary_ai_profile.json", profile)
    write_json(request_dir / "control_center_creation_request.json", creation_request)
    write_text(candidate_dir / "README.md", f"""# {display_name} TemporaryAI Candidate

Candidate ID: `{candidate_id}`

Role: `{role_title}`

Status: `{status}`

This package was created by the TemporaryAI Control Center. It is a reviewable
candidate, not an activated AI.

Next steps:

1. Review `creation_request.json`.
2. Resolve ambiguity questions if any.
3. Run metadata-only voice discovery and review its source, rights, speaker, and performer labels.
4. Run a short candidate probe.
5. Approve whether Kira and/or Lisa may activate the candidate.
6. Review avatar references or design choices before any avatar generation.
""")

    queue = read_json(ACTIVATION_QUEUE, {"queue_id": "temporary_ai_activation_queue_v1", "items": []})
    queue.setdefault("items", [])
    queue["updated_at"] = now_iso()
    queue["items"].append({
        "candidate_id": candidate_id,
        "display_name": display_name,
        "role_title": role_title,
        "ui_category": kind_label,
        "status": "pending_review",
        "created_at": now_iso(),
        "candidate_profile": rel(candidate_dir / "temporary_ai_profile.json"),
        "activation_plan": rel(candidate_dir / "activation_plan.json"),
        "kira_allowed_after_review": allow_kira,
        "lisa_allowed_after_review": allow_lisa,
    })
    write_json(ACTIVATION_QUEUE, queue)

    shared_pipeline = {}
    shared_pipeline_error = ""
    try:
        shared_pipeline = queue_shared_person_pipeline(
            candidate_id=candidate_id,
            kind_label=kind_label,
            query=query,
            version=effective_version,
            gender=gender,
            personality=personality,
            display_name=display_name,
            role_title=role_title,
            allow_kira=allow_kira,
            allow_lisa=allow_lisa,
        )
        shared_link = {
            "person_id": shared_pipeline["person_id"],
            "bundle_id": shared_pipeline["bundle_id"],
            "workspace_relative": shared_pipeline["workspace_relative"],
            "overall_status": shared_pipeline["overall_status"],
            "result_sha256": shared_pipeline["result_sha256"],
        }
        for link_path in (
            candidate_dir / "creation_request.json",
            candidate_dir / "temporary_ai_profile.json",
            candidate_dir / "activation_plan.json",
        ):
            linked_record = read_json(link_path, {})
            linked_record["shared_person_pipeline"] = shared_link
            write_json(link_path, linked_record)
    except (TemporaryCreatorPipelineError, KeyError, OSError, ValueError) as exc:
        shared_pipeline_error = f"{type(exc).__name__}: {exc}"

    return {
        "candidate_id": candidate_id,
        "display_name": display_name,
        "role_title": role_title,
        "status": status,
        "candidate_dir": rel(candidate_dir),
        "voice_discovery_request": rel(candidate_dir / "voice_discovery_request.json"),
        "avatar_dir": rel(avatar_dir),
        "timeline": timeline["estimate"],
        "creation_estimate": creation_estimate["plain_estimate"],
        "online_lookup_status": online_lookup.get("status", "unknown"),
        "online_lookup_title": online_lookup.get("matched_title", ""),
        "online_lookup_url": online_lookup.get("url", ""),
        "reliable_source_pack_status": reliable_source_pack["status"],
        "source_count": reliable_source_pack["source_count"],
        "fetched_count": reliable_source_pack["fetched_count"],
        "expanded_web_results": len(expanded_gather.get("web_search_results", [])),
        "avatar_reference_count": len(expanded_gather.get("avatar_reference_manifest", {}).get("references", [])),
        "desktop_avatar_reference_count": avatar_pipeline.get("desktop_reference_count", 0),
        "avatar_pipeline_status": avatar_pipeline.get("status", ""),
        "ambiguity_questions": ambiguity,
        "shared_person_id": shared_pipeline.get("person_id", ""),
        "shared_person_pipeline_status": shared_pipeline.get("overall_status", "draft"),
        "shared_person_pipeline_workspace": shared_pipeline.get("workspace_relative", ""),
        "shared_person_pipeline_error": shared_pipeline_error,
    }


class TemporaryAIControlCenter:
    def __init__(self) -> None:
        self.root = Tk()
        self.root.title("TemporaryAI Control Center")
        self.root.geometry("1120x760")
        self.root.minsize(980, 620)
        self.root.configure(bg="#0b1220")

        self.kind_var = StringVar(value="Expert")
        self.gender_var = StringVar(value="Doesn't matter")
        self.query_var = StringVar()
        self.version_var = StringVar()
        self.name_preview_var = StringVar(value="Candidate preview will appear here.")
        self.kira_var = IntVar(value=1)
        self.lisa_var = IntVar(value=1)
        self.last_candidate_dir: Path | None = None
        self.last_avatar_dir: Path | None = None
        self.build_ui()
        self.refresh_preview()
        self.log("TemporaryAI Control Center ready.")

    def build_ui(self) -> None:
        outer = Frame(self.root, bg="#0b1220")
        outer.pack(fill=BOTH, expand=True, padx=14, pady=14)

        left = Frame(outer, bg="#111827", bd=1, relief="solid", width=430)
        left.pack(side=LEFT, fill=Y, padx=(0, 12))
        right = Frame(outer, bg="#111827", bd=1, relief="solid")
        right.pack(side=RIGHT, fill=BOTH, expand=True)

        Label(left, text="TemporaryAI Builder", fg="#f9fafb", bg="#111827", font=("Segoe UI", 18, "bold")).pack(anchor="w", padx=14, pady=(12, 4))
        Label(
            left,
            text="Create reviewed candidates that Kira or Lisa can activate later. Create now does a lightweight online preview lookup and writes the results into the candidate folder.",
            fg="#cbd5e1",
            bg="#111827",
            wraplength=380,
            justify=LEFT,
        ).pack(anchor="w", padx=14, pady=(0, 12))

        self.form_row(left, "AI type")
        OptionMenu(left, self.kind_var, *VISIBLE_AI_TYPE_LABELS.keys(), command=lambda _=None: self.refresh_preview()).pack(fill=X, padx=14, pady=(0, 8))

        self.form_row(left, "Domain / character / person")
        self.query_entry = Entry(left, textvariable=self.query_var)
        self.query_entry.pack(fill=X, padx=14, pady=(0, 8))
        self.query_entry.bind("<KeyRelease>", lambda _event: self.refresh_preview())

        self.form_row(left, "Version, life point, or canon point")
        self.version_entry = Entry(left, textvariable=self.version_var)
        self.version_entry.pack(fill=X, padx=14, pady=(0, 8))
        self.version_entry.bind("<KeyRelease>", lambda _event: self.refresh_preview())

        self.form_row(left, "Gender preference")
        OptionMenu(left, self.gender_var, "Female", "Male", "Doesn't matter", "Custom / decide later", command=lambda _=None: self.refresh_preview()).pack(fill=X, padx=14, pady=(0, 8))

        self.form_row(left, "Personality notes")
        self.personality_text = scrolledtext.ScrolledText(left, wrap="word", height=6, bg="#0b1220", fg="#f9fafb", insertbackground="#f9fafb")
        self.personality_text.pack(fill=X, padx=14, pady=(0, 8))

        Checkbutton(left, text="Available to Kira after review", variable=self.kira_var, bg="#111827", fg="#f9fafb", selectcolor="#1f2937").pack(anchor="w", padx=14)
        Checkbutton(left, text="Available to Lisa after review", variable=self.lisa_var, bg="#111827", fg="#f9fafb", selectcolor="#1f2937").pack(anchor="w", padx=14, pady=(0, 10))

        Label(left, textvariable=self.name_preview_var, fg="#93c5fd", bg="#111827", wraplength=380, justify=LEFT).pack(anchor="w", padx=14, pady=(0, 10))

        Button(left, text="Create Candidate + Online Preview", command=self.create_package, height=2).pack(fill=X, padx=14, pady=(0, 6))
        Button(left, text="Talk to Last Candidate", command=self.talk_to_last_candidate, height=2).pack(fill=X, padx=14, pady=3)
        Button(left, text="Open Last Candidate", command=self.open_last_candidate, height=2).pack(fill=X, padx=14, pady=3)
        Button(left, text="Open Last Avatar Folder", command=self.open_last_avatar, height=2).pack(fill=X, padx=14, pady=3)
        Button(left, text="Attach Video Reference", command=self.attach_video_reference, height=2).pack(fill=X, padx=14, pady=3)
        Button(left, text="Find Voice Sources (Metadata Only)", command=self.discover_last_candidate_voice, height=2).pack(fill=X, padx=14, pady=3)
        Button(left, text="Open Activation Queue", command=lambda: self.open_path(ACTIVATION_QUEUE), height=2).pack(fill=X, padx=14, pady=3)

        quick = Frame(left, bg="#111827")
        quick.pack(fill=X, padx=14, pady=(8, 12))
        Button(quick, text="Spider-Man example", command=lambda: self.example("Fictional", "Spider-Man", "Tom Holland")).pack(side=LEFT, fill=X, expand=True, padx=(0, 4))
        Button(quick, text="JFK example", command=lambda: self.example("Historical", "JFK", "moon speech era")).pack(side=LEFT, fill=X, expand=True, padx=4)
        Button(quick, text="History expert", command=lambda: self.example("Expert", "American history", "")).pack(side=LEFT, fill=X, expand=True, padx=(4, 0))

        Label(right, text="Candidate Plan", fg="#f9fafb", bg="#111827", font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=14, pady=(12, 4))
        self.plan_view = scrolledtext.ScrolledText(right, wrap="word", bg="#0b1220", fg="#d1d5db", insertbackground="#f9fafb", height=18)
        self.plan_view.pack(fill=BOTH, expand=True, padx=14, pady=(0, 10))

        row = Frame(right, bg="#111827")
        row.pack(fill=X, padx=14, pady=(0, 10))
        Button(row, text="Open Candidates Folder", command=lambda: self.open_path(CANDIDATE_ROOT), height=2).pack(side=LEFT, fill=X, expand=True, padx=(0, 4))
        Button(row, text="Open Avatar Folder", command=lambda: self.open_path(AVATAR_ROOT), height=2).pack(side=LEFT, fill=X, expand=True, padx=4)
        Button(row, text="Open Docs", command=lambda: self.open_path(DOC_PATH), height=2).pack(side=LEFT, fill=X, expand=True, padx=(4, 0))

        Label(right, text="Event Log", fg="#f9fafb", bg="#111827", font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=14, pady=(0, 4))
        self.event_log = scrolledtext.ScrolledText(right, wrap="word", bg="#0b1220", fg="#d1d5db", insertbackground="#f9fafb", font=("Consolas", 9), height=10)
        self.event_log.pack(fill=X, padx=14, pady=(0, 12))

    def form_row(self, parent: Frame, text: str) -> None:
        Label(parent, text=text, fg="#f9fafb", bg="#111827", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=14, pady=(4, 2))

    def log(self, text: str) -> None:
        line = f"[{datetime.now().strftime('%H:%M:%S')}] {text}"
        self.event_log.insert(END, line + "\n")
        self.event_log.see(END)

    def refresh_preview(self) -> None:
        kind = VISIBLE_AI_TYPE_LABELS[self.kind_var.get()]
        query = self.query_var.get()
        version = self.version_var.get()
        gender = self.gender_var.get()
        name = candidate_display_name(kind, query, version, gender)
        role_title = role_title_for(kind, query)
        questions = build_ambiguity_questions(kind, query, version)
        plan = build_knowledge_plan(kind, query, version, gender)
        self.name_preview_var.set(f"Preview name: {name}\nRole: {role_title}")
        preview = {
            "preview_name": name,
            "role_title": role_title,
            "ai_type": AI_TYPE_LABELS[kind],
            "status_if_created": "needs_clarification" if questions else "draft_pending_review",
            "ambiguity_questions": questions,
            "knowledge_plan": plan,
            "avatar_estimate": avatar_timeline(kind, bool(version.strip()))["estimate"],
            "create_button_will": [
                "create timestamped candidate files",
                "try a lightweight online Wikipedia preview lookup",
                "save source research queue links",
                "queue mind, avatar, and voice work under one shared identity",
                "rank routine source/version choices without interrupting for approval",
                "hold world registration until the complete person passes its gates",
            ],
            "activation": {
                "kira_after_review": bool(self.kira_var.get()),
                "lisa_after_review": bool(self.lisa_var.get()),
            },
        }
        self.plan_view.delete("1.0", END)
        self.plan_view.insert(END, json.dumps(preview, indent=2, ensure_ascii=False))

    def example(self, kind: str, query: str, version: str) -> None:
        self.kind_var.set(kind)
        self.query_var.set(query)
        self.version_var.set(version)
        self.refresh_preview()

    def create_package(self) -> None:
        kind = VISIBLE_AI_TYPE_LABELS[self.kind_var.get()]
        query = self.query_var.get().strip()
        if not query:
            messagebox.showwarning("Missing input", "Type a domain, character, person, or role first.")
            return
        personality = self.personality_text.get("1.0", END).strip()
        result = build_candidate_package(
            kind_label=kind,
            query=query,
            version=self.version_var.get().strip(),
            gender=self.gender_var.get(),
            personality=personality,
            allow_kira=bool(self.kira_var.get()),
            allow_lisa=bool(self.lisa_var.get()),
        )
        self.last_candidate_dir = PROJECT_ROOT / result["candidate_dir"]
        self.last_avatar_dir = PROJECT_ROOT / result["avatar_dir"]
        self.log(f"Created {result['candidate_id']} ({result['status']}).")
        self.log(f"Online lookup: {result['online_lookup_status']} {result['online_lookup_title']}".strip())
        self.log(f"Reliable sources: {result['reliable_source_pack_status']} fetched {result['fetched_count']}/{result['source_count']}.")
        self.log(f"Expanded gather: web results={result['expanded_web_results']}, avatar references={result['avatar_reference_count']}.")
        self.log(f"Creation estimate: {result['creation_estimate']}")
        self.log(f"Avatar estimate: {result['timeline']}")
        self.log(f"Voice discovery request: {result['voice_discovery_request']} (metadata search not run yet).")
        if result["shared_person_id"]:
            self.log(
                "Shared person pipeline: "
                f"{result['shared_person_id']} ({result['shared_person_pipeline_status']})."
            )
        else:
            self.log(
                "Shared person pipeline did not queue: "
                f"{result['shared_person_pipeline_error'] or 'unknown error'}"
            )
        if result["ambiguity_questions"]:
            self.log("Needs clarification before activation.")
        self.plan_view.delete("1.0", END)
        self.plan_view.insert(END, json.dumps(result, indent=2, ensure_ascii=False))
        messagebox.showinfo(
            "TemporaryAI candidate created",
            "\n".join([
                f"Created: {result['display_name']}",
                f"Role: {result['role_title']}",
                f"Status: {result['status']}",
                f"Online lookup: {result['online_lookup_status']}",
                f"Reliable sources: {result['fetched_count']}/{result['source_count']} fetched",
                f"Web results: {result['expanded_web_results']}",
                f"Avatar references: {result['avatar_reference_count']}",
                f"Estimate: {result['creation_estimate']}",
                "",
                f"Candidate folder: {result['candidate_dir']}",
            ]),
        )

    def open_path(self, path: Path) -> None:
        if not path.exists():
            self.log(f"Path not found: {path}")
            return
        os.startfile(str(path))
        self.log(f"Opened {rel(path)}")

    def open_last_candidate(self) -> None:
        if not self.last_candidate_dir:
            self.last_candidate_dir = latest_candidate_dir()
            if not self.last_candidate_dir:
                self.open_path(CANDIDATE_ROOT)
                return
        self.open_path(self.last_candidate_dir)

    def talk_to_last_candidate(self) -> None:
        if (
            not self.last_candidate_dir
            or not self.last_candidate_dir.is_dir()
            or not (self.last_candidate_dir / "temporary_ai_profile.json").is_file()
        ):
            self.last_candidate_dir = latest_candidate_dir()
        if not self.last_candidate_dir:
            messagebox.showwarning("No candidate", "Create a TemporaryAI candidate first.")
            return
        candidate_id = self.last_candidate_dir.name
        launch_environment = os.environ.copy()
        launch_environment["TEMP_AI_INITIAL_CANDIDATE_ID"] = candidate_id
        subprocess.Popen(
            ["cmd", "/c", "start", "", "py", "tools\\temporary_ai_live_chat_gui.py"],
            cwd=str(PROJECT_ROOT),
            shell=False,
            env=launch_environment,
        )
        self.log(f"Opened TemporaryAI live chat for {candidate_id}.")

    def open_last_avatar(self) -> None:
        if not self.last_avatar_dir:
            self.open_path(AVATAR_ROOT)
            return
        self.open_path(self.last_avatar_dir)

    def attach_video_reference(self) -> None:
        command = ["cmd", "/c", "start", "", "py", "tools\\temporary_ai_video_reference_intake.py"]
        if self.last_candidate_dir and self.last_candidate_dir.exists():
            command.append("--candidate")
            command.append(self.last_candidate_dir.name)
        subprocess.Popen(
            command,
            cwd=str(PROJECT_ROOT),
            shell=False,
        )
        if self.last_candidate_dir:
            self.log(f"Opened video reference intake for {self.last_candidate_dir.name}.")
        else:
            self.log("Opened video reference intake; pick a candidate in the console.")

    def discover_last_candidate_voice(self) -> None:
        if not self.last_candidate_dir:
            self.last_candidate_dir = latest_candidate_dir()
        if not self.last_candidate_dir or not self.last_candidate_dir.exists():
            messagebox.showwarning("No candidate", "Create or select a TemporaryAI candidate first.")
            return
        candidate_id = self.last_candidate_dir.name
        subprocess.Popen(
            [
                "cmd",
                "/c",
                "start",
                "",
                "py",
                "tools\\discover_temporary_ai_voice.py",
                "--candidate-id",
                candidate_id,
                "--metadata-search",
            ],
            cwd=str(PROJECT_ROOT),
            shell=False,
        )
        self.log(
            f"Started metadata-only voice discovery for {candidate_id}. "
            "It will not download media/model weights, build a voice, or activate the candidate."
        )

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    TemporaryAIControlCenter().run()
