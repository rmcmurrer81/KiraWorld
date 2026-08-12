"""Review media preview cards that need factual metadata or Robert disambiguation."""

from __future__ import annotations

import json
import os
import re
import threading
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, X, Y, Button, Entry, Frame, Label, Listbox, StringVar, Text, Tk
from tkinter import messagebox, scrolledtext

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
QUEUE_PATH = PROJECT_ROOT / "Data" / "media" / "preview_cards" / "media_lookup_queue.json"
CARDS_DIR = PROJECT_ROOT / "Data" / "media" / "preview_cards" / "generated"
WIKIPEDIA_SEARCH_URL = "https://en.wikipedia.org/w/api.php"
WIKIPEDIA_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/"
MEDIA_WORDS = {"film", "movie", "television", "tv", "series", "episode", "song", "album", "soundtrack", "documentary"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return p.as_posix()


def read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def clean_lookup_title(title: str) -> str:
    title = re.sub(r"\b(480p|720p|1080p|2160p|4k|x264|x265|h264|h265|aac|mp3|flac|web|webrip|bluray|dvdrip)\b", " ", title, flags=re.IGNORECASE)
    title = re.sub(r"[_\-.]+", " ", title)
    title = re.sub(r"\s+", " ", title).strip()
    return title


def year_from_text(text: str) -> str:
    match = re.search(r"(?<!\d)(19\d{2}|20\d{2})(?!\d)", text or "")
    return match.group(1) if match else ""


def media_query_word(media_type: str) -> str:
    media_type = media_type.lower().strip()
    if media_type in {"movie", "film", "video", "commercial_video", "unknown"}:
        return "film"
    if media_type in {"tv", "tv_clip", "series"}:
        return "television"
    if media_type in {"music", "soundtrack", "audio", "music_video"}:
        return "song"
    return media_type or "film"


def wikipedia_search(query: str, limit: int = 6) -> list[dict]:
    search = requests.get(
        WIKIPEDIA_SEARCH_URL,
        params={
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "utf8": 1,
            "srlimit": limit,
        },
        headers={"User-Agent": "KiraLocalMediaPreview/0.2 (personal local library metadata review)"},
        timeout=12,
    )
    search.raise_for_status()
    results = search.json().get("query", {}).get("search", [])
    return [item for item in results if isinstance(item, dict) and item.get("title")]


def wikipedia_summary(page_title: str) -> dict:
    encoded = urllib.parse.quote(page_title.replace(" ", "_"), safe="")
    summary = requests.get(
        WIKIPEDIA_SUMMARY_URL + encoded,
        headers={"User-Agent": "KiraLocalMediaPreview/0.2 (personal local library metadata review)"},
        timeout=12,
    )
    summary.raise_for_status()
    data = summary.json()
    return {
        "title": data.get("title") or page_title,
        "url": (data.get("content_urls", {}).get("desktop", {}) or {}).get("page", f"https://en.wikipedia.org/wiki/{encoded}"),
        "extract": data.get("extract", ""),
    }


def direct_page_guesses(title: str, year: str, media_type: str) -> list[str]:
    guesses = [title]
    query_word = media_query_word(media_type)
    if query_word == "film":
        if year and year.lower() != "unknown":
            guesses.append(f"{title} ({year} film)")
        guesses.append(f"{title} (film)")
    elif query_word == "television":
        guesses.extend([f"{title} (TV series)", f"{title} (television series)"])
    elif query_word == "song":
        guesses.extend([f"{title} (song)", f"{title} (album)", f"{title} (soundtrack)"])
    seen = set()
    unique = []
    for guess in guesses:
        key = guess.lower()
        if key not in seen:
            unique.append(guess)
            seen.add(key)
    return unique


def strip_html(value: str) -> str:
    return re.sub(r"<[^>]+>", " ", value or "")


def score_candidate(page_title: str, extract: str, title_guess: str, year: str, media_type: str, rank: int) -> int:
    guess_norm = normalized_title(title_guess)
    page_norm = normalized_title(page_title)
    text = f"{page_title} {extract}".lower()
    score = max(0, 20 - rank)
    if page_norm == guess_norm:
        score += 90
    elif page_norm.startswith(guess_norm) or guess_norm in page_norm:
        score += 55
    elif all(token in page_norm for token in guess_norm.split() if token not in MEDIA_WORDS):
        score += 35
    if year and year.lower() != "unknown":
        if year in text:
            score += 30
        else:
            score -= 20
    query_word = media_query_word(media_type)
    if query_word and query_word in text:
        score += 12
    if "(film)" in page_title.lower() or " film)" in page_title.lower():
        score += 16 if query_word == "film" else 4
    if "soundtrack" in page_title.lower() and query_word != "song":
        score -= 20
    if "disambiguation" in page_title.lower():
        score -= 80
    if "film series" in page_title.lower() and "series" not in media_type.lower():
        score -= 20
    return score


def wikipedia_lookup(title: str, year: str, media_type: str) -> dict:
    title = clean_lookup_title(title.strip())
    year = year.strip()
    media_type = media_type.strip() or "movie"
    if not title:
        return {"ok": False, "error": "No title to look up."}
    query_word = media_query_word(media_type)
    queries = []
    if year and year.lower() != "unknown":
        queries.append(f"{title} {year} {query_word}")
    queries.append(f"{title} {query_word}")
    queries.append(title)
    try:
        direct_scored = []
        for rank, page_title in enumerate(direct_page_guesses(title, year, media_type)):
            try:
                summary_data = wikipedia_summary(page_title)
            except Exception:
                continue
            score = score_candidate(summary_data.get("title", page_title), summary_data.get("extract", ""), title, year, media_type, rank)
            direct_scored.append((score, summary_data, summary_data.get("title", page_title)))
            time.sleep(0.1)
        direct_scored.sort(key=lambda item: item[0], reverse=True)
        if direct_scored and direct_scored[0][0] >= 55:
            best_score, summary_data, page_title = direct_scored[0]
            return {
                "ok": True,
                "query": f"direct page: {page_title}",
                "title": summary_data.get("title") or page_title,
                "url": summary_data.get("url", ""),
                "extract": summary_data.get("extract", ""),
                "candidates": [title for _score, _summary, title in direct_scored],
                "candidate_scores": [{"title": title, "score": score} for score, _summary, title in direct_scored[:8]],
                "best_score": best_score,
                "provider": "Wikipedia",
            }

        results_by_title: dict[str, dict] = {}
        query_used = ""
        for query in queries[:3]:
            results = wikipedia_search(query, limit=6)
            if not query_used and results:
                query_used = query
            for result in results:
                results_by_title.setdefault(result["title"], result)
        results = list(results_by_title.values())
        if not results:
            return {"ok": False, "error": f"No Wikipedia results for: {' | '.join(queries[:3])}", "query": queries[0]}
        initial_scored = []
        for rank, result in enumerate(results):
            page_title = result["title"]
            snippet = strip_html(str(result.get("snippet", "")))
            score = score_candidate(page_title, snippet, title, year, media_type, rank)
            initial_scored.append((score, result, page_title, snippet))
        initial_scored.sort(key=lambda item: item[0], reverse=True)

        scored = []
        for rank, (_initial_score, result, page_title, snippet) in enumerate(initial_scored[:4]):
            try:
                summary_data = wikipedia_summary(page_title)
            except Exception:
                summary_data = {"title": page_title, "url": f"https://en.wikipedia.org/wiki/{urllib.parse.quote(page_title.replace(' ', '_'), safe='')}", "extract": snippet}
            score = score_candidate(page_title, summary_data.get("extract", ""), title, year, media_type, rank)
            scored.append((score, summary_data, page_title))
            time.sleep(0.15)
        scored.sort(key=lambda item: item[0], reverse=True)
        best_score, summary_data, page_title = scored[0]
        candidates = [item.get("title", "") for item in results if item.get("title")]
        return {
            "ok": True,
            "query": query_used or queries[0],
            "title": summary_data.get("title") or page_title,
            "url": summary_data.get("url", ""),
            "extract": summary_data.get("extract", ""),
            "candidates": candidates,
            "candidate_scores": [{"title": title, "score": score} for score, _summary, title in scored[:8]],
            "best_score": best_score,
            "provider": "Wikipedia",
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}", "query": query}


def normalized_title(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def lookup_is_confident(item: dict, result: dict) -> bool:
    title_guess = normalized_title(str(item.get("title_guess", "")))
    result_title = normalized_title(str(result.get("title", "")))
    if not title_guess or not result_title:
        return False
    title_ok = title_guess in result_title or result_title in title_guess
    year = str(item.get("year_guess", "") or "").strip()
    text = f"{result.get('title', '')} {result.get('extract', '')}"
    year_ok = not year or year.lower() == "unknown" or year in text
    return title_ok and year_ok and int(result.get("best_score", 0)) >= 55


def preview_text_from_lookup(item: dict, result: dict) -> tuple[str, str]:
    title = result.get("title") or item.get("title_guess") or "This media item"
    extract = str(result.get("extract") or "").strip()
    if extract:
        summary = extract.strip()
        if "\n" not in summary:
            curiosity_sentence = (
                f"\n\nFor Kira and Lisa, this is only a preview: enough to notice genre, cast, premise, and possible mood, "
                f"but not enough to claim they watched or listened to {title}."
            )
            if len(summary) < 520:
                summary = summary + curiosity_sentence
    else:
        year = item.get("year_guess") or ""
        media_type = item.get("media_type_guess") or "media item"
        summary = f"{title} is a {media_type} entry from the local library. The filename suggests the year {year}, but more metadata review is needed."
    curiosity = (
        f"Kira or Lisa might read this preview to decide whether {title} sounds interesting later. "
        "This can support curiosity, taste, and conversation, but it is not a memory of watching or listening."
    )
    return summary, curiosity


def lookup_title_for_item(item: dict) -> str:
    status = str(item.get("status", ""))
    if status in {"ambiguous", "lookup_failed", "needs_lookup", ""}:
        return str(item.get("title_guess") or item.get("resolved_title") or "")
    return str(item.get("resolved_title") or item.get("title_guess") or "")


def lookup_year_for_item(item: dict) -> str:
    status = str(item.get("status", ""))
    if status in {"ambiguous", "lookup_failed", "needs_lookup", ""}:
        return str(item.get("year_guess") or item.get("resolved_year") or "")
    return str(item.get("resolved_year") or item.get("year_guess") or "")


def update_card_from_lookup(item: dict, result: dict, confidence_status: str) -> None:
    card_path = PROJECT_ROOT / str(item.get("card_path", ""))
    card = read_json(card_path, {})
    if not isinstance(card, dict):
        return
    summary, curiosity = preview_text_from_lookup(item, result)
    identity = card.setdefault("identity", {})
    if isinstance(identity, dict):
        identity["resolved_title"] = result.get("title", "")
        identity["resolved_year"] = item.get("resolved_year") or item.get("year_guess", "")
        identity.setdefault("external_ids", {})["wikipedia_url"] = result.get("url", "")
        identity["identity_confidence"] = "online_lookup_wikipedia" if confidence_status == "resolved_auto" else "needs_robert_review"
        identity["ambiguity_status"] = "resolved_by_online_lookup" if confidence_status == "resolved_auto" else "needs_robert_review"
    preview = card.setdefault("preview", {})
    if isinstance(preview, dict):
        preview["back_of_case_summary"] = summary
        preview["why_kira_or_lisa_might_be_curious"] = curiosity
        tags = preview.setdefault("topic_tags", [])
        if isinstance(tags, list) and "metadata_preview" not in tags:
            tags.append("metadata_preview")
    source = card.setdefault("source_attribution", {})
    if isinstance(source, dict):
        source["online_lookup_used"] = True
        sources = source.setdefault("metadata_sources", [])
        if isinstance(sources, list):
            sources.append(
                {
                    "provider": result.get("provider", "Wikipedia"),
                    "url": result.get("url", ""),
                    "retrieved_at": utc_now(),
                    "note": "Used for preview metadata only; not watched/listened memory.",
                }
            )
    card["status"] = "metadata_preview_ready" if confidence_status == "resolved_auto" else "metadata_lookup_needs_robert_review"
    card["updated_at"] = utc_now()
    write_json(card_path, card)


def ensure_queue() -> dict:
    data = read_json(QUEUE_PATH, {})
    if isinstance(data, dict) and isinstance(data.get("items"), list):
        return data
    return {
        "queue_id": "media_preview_card_lookup_queue",
        "updated_at": utc_now(),
        "policy": {
            "metadata_lookup_required_before_rich_preview": True,
            "ask_robert_on_ambiguity": True,
            "preview_cards_are_not_watched_or_listened_memories": True,
        },
        "items": [],
    }


class MediaLookupReviewPanel:
    def __init__(self) -> None:
        self.root = Tk()
        self.root.title("Kira Media Lookup Review")
        self.root.geometry("1120x700")
        self.root.minsize(900, 580)
        self.root.configure(bg="#111827")
        self.queue = ensure_queue()
        self.items: list[dict] = []
        self.selected_index: int | None = None

        self.status_var = StringVar(value="")
        self.title_var = StringVar(value="")
        self.year_var = StringVar(value="")
        self.source_var = StringVar(value="")

        self.build_ui()
        self.reload()

    def build_ui(self) -> None:
        outer = Frame(self.root, bg="#111827")
        outer.pack(fill=BOTH, expand=True, padx=12, pady=12)

        left = Frame(outer, bg="#1f2937", bd=1, relief="solid", width=390)
        left.pack(side=LEFT, fill=Y, padx=(0, 10))
        right = Frame(outer, bg="#111827")
        right.pack(side=RIGHT, fill=BOTH, expand=True)

        Label(left, text="Media Lookup Queue", fg="#f9fafb", bg="#1f2937", font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=10, pady=(10, 4))
        Label(left, text="Review ambiguous or unverified movie/TV/music preview cards. This does not create watched/listened memory.", fg="#d1d5db", bg="#1f2937", wraplength=350, justify=LEFT).pack(anchor="w", padx=10, pady=(0, 8))
        self.listbox = Listbox(left, bg="#0b1220", fg="#e5e7eb", selectbackground="#2563eb", relief="flat", font=("Segoe UI", 10))
        self.listbox.pack(fill=BOTH, expand=True, padx=10, pady=(0, 10))
        self.listbox.bind("<<ListboxSelect>>", self.on_select)

        controls = Frame(left, bg="#1f2937")
        controls.pack(fill=X, padx=10, pady=(0, 10))
        Button(controls, text="Reload", command=self.reload).pack(side=LEFT, fill=X, expand=True, padx=(0, 6))
        Button(controls, text="Open Card", command=self.open_card).pack(side=LEFT, fill=X, expand=True)

        Label(right, text="Selected Item", fg="#f9fafb", bg="#111827", font=("Segoe UI", 14, "bold")).pack(anchor="w")
        self.detail = scrolledtext.ScrolledText(right, wrap="word", bg="#0b1220", fg="#e5e7eb", relief="flat", font=("Segoe UI", 10), height=13)
        self.detail.pack(fill=X, pady=(8, 12))

        form = Frame(right, bg="#111827")
        form.pack(fill=X)
        self.row(form, "Resolved title", self.title_var)
        self.row(form, "Resolved year", self.year_var)
        self.row(form, "Source URL / note", self.source_var)

        Label(right, text="Robert review note", fg="#d1d5db", bg="#111827").pack(anchor="w", pady=(10, 2))
        self.review_note = Text(right, height=5, wrap="word", bg="#1f2937", fg="#f9fafb", insertbackground="#f9fafb", relief="flat", font=("Segoe UI", 10))
        self.review_note.pack(fill=X)

        buttons = Frame(right, bg="#111827")
        buttons.pack(fill=X, pady=10)
        Button(buttons, text="Needs Lookup", command=lambda: self.set_status("needs_lookup")).pack(side=LEFT, fill=X, expand=True, padx=(0, 6))
        Button(buttons, text="Ambiguous", command=lambda: self.set_status("ambiguous")).pack(side=LEFT, fill=X, expand=True, padx=(0, 6))
        Button(buttons, text="Resolved", command=lambda: self.set_status("resolved")).pack(side=LEFT, fill=X, expand=True, padx=(0, 6))
        Button(buttons, text="Skip", command=lambda: self.set_status("skipped")).pack(side=LEFT, fill=X, expand=True)

        Button(right, text="Lookup Wikipedia", command=self.lookup_wikipedia_current).pack(fill=X, pady=(0, 8))
        Button(right, text="Auto Lookup Unresolved", command=self.auto_lookup_unresolved).pack(fill=X, pady=(0, 8))
        Button(right, text="Save Current Item", command=self.save_current).pack(fill=X, pady=(0, 8))
        Label(right, textvariable=self.status_var, fg="#93c5fd", bg="#111827", wraplength=640, justify=LEFT).pack(anchor="w")

    def row(self, parent: Frame, label: str, var: StringVar) -> None:
        frame = Frame(parent, bg="#111827")
        frame.pack(fill=X, pady=3)
        Label(frame, text=label, fg="#d1d5db", bg="#111827", width=18, anchor="w").pack(side=LEFT)
        Entry(frame, textvariable=var, bg="#1f2937", fg="#f9fafb", insertbackground="#f9fafb", relief="flat").pack(side=LEFT, fill=X, expand=True)

    def reload(self) -> None:
        self.queue = ensure_queue()
        self.items = [item for item in self.queue.get("items", []) if isinstance(item, dict)]
        self.listbox.delete(0, END)
        for item in self.items:
            status = item.get("status", "needs_lookup")
            title = item.get("resolved_title") or item.get("title_guess") or "untitled"
            year = item.get("resolved_year") or item.get("year_guess") or ""
            media_type = item.get("media_type_guess", "unknown")
            self.listbox.insert(END, f"[{status}] {title} ({year}) - {media_type}")
        self.status_var.set(f"Loaded {len(self.items)} queue items from {rel(QUEUE_PATH)}")
        if self.items:
            self.listbox.selection_set(0)
            self.show_item(0)

    def on_select(self, _event=None) -> None:
        selection = self.listbox.curselection()
        if not selection:
            return
        self.show_item(int(selection[0]))

    def show_item(self, index: int) -> None:
        self.selected_index = index
        item = self.items[index]
        self.title_var.set(item.get("resolved_title", ""))
        self.year_var.set(item.get("resolved_year", ""))
        self.source_var.set(item.get("resolved_source_url", ""))
        self.review_note.delete("1.0", END)
        self.review_note.insert(END, item.get("review_note", ""))
        self.detail.configure(state="normal")
        self.detail.delete("1.0", END)
        lines = [
            f"Status: {item.get('status', '')}",
            f"Title guess: {item.get('title_guess', '')}",
            f"Year guess: {item.get('year_guess', '')}",
            f"Media type guess: {item.get('media_type_guess', '')}",
            f"Card: {item.get('card_path', '')}",
            "",
            "Ambiguity note:",
            item.get("ambiguity_note", ""),
            "",
            "Policy: preview cards are not watched/listened memories. Resolved metadata only helps Kira/Lisa decide what might be interesting later.",
        ]
        if item.get("preview_back_of_case_summary"):
            lines.extend(["", "Back-of-case preview:", str(item.get("preview_back_of_case_summary", ""))])
        self.detail.insert(END, "\n".join(lines))
        self.detail.configure(state="disabled")

    def current_item(self) -> dict | None:
        if self.selected_index is None or self.selected_index >= len(self.items):
            return None
        return self.items[self.selected_index]

    def save_current(self) -> None:
        item = self.current_item()
        if not item:
            return
        item["resolved_title"] = self.title_var.get().strip()
        item["resolved_year"] = self.year_var.get().strip()
        item["resolved_source_url"] = self.source_var.get().strip()
        item["review_note"] = self.review_note.get("1.0", END).strip()
        item["reviewed_at"] = utc_now()
        self.queue["updated_at"] = utc_now()
        write_json(QUEUE_PATH, self.queue)
        self.status_var.set(f"Saved item: {item.get('title_guess', '')}")
        self.reload()

    def apply_lookup_result(self, item: dict, result: dict, *, auto: bool = False) -> None:
        title = str(result.get("title") or item.get("title_guess") or "")
        url = str(result.get("url") or "")
        extract = str(result.get("extract") or "")
        candidates = result.get("candidates", []) if isinstance(result.get("candidates"), list) else []
        confident = lookup_is_confident(item, result)
        status = "resolved_auto" if auto and confident else "ambiguous"
        item["status"] = status
        item["resolved_title"] = title
        item["resolved_year"] = item.get("resolved_year") or item.get("year_guess", "")
        item["resolved_source_url"] = url
        summary, curiosity = preview_text_from_lookup(item, result)
        item["preview_back_of_case_summary"] = summary
        item["preview_curiosity_note"] = curiosity
        item["review_note"] = (
            f"Online metadata lookup provider: {result.get('provider', 'Wikipedia')}\n"
            f"Query: {result.get('query', '')}\n"
            f"Candidate pages: {', '.join(candidates[:5])}\n"
            f"Candidate scores: {self.format_candidate_scores(result)}\n\n"
            f"Back-of-case preview:\n{summary}\n\n"
            f"Curiosity note:\n{curiosity}\n\n"
            "Preview aid only. This is not watched/listened memory."
        )
        item["reviewed_at"] = utc_now()
        item["lookup_results"] = item.get("lookup_results", [])
        if isinstance(item["lookup_results"], list):
            item["lookup_results"].append(
                {
                    "looked_up_at": utc_now(),
                    "provider": result.get("provider", "Wikipedia"),
                    "query": result.get("query", ""),
                    "title": title,
                    "url": url,
                    "extract": extract,
                    "candidates": candidates,
                    "candidate_scores": result.get("candidate_scores", []),
                    "best_score": result.get("best_score", 0),
                    "auto_confident": confident,
                }
            )
        update_card_from_lookup(item, result, status)

    def format_candidate_scores(self, result: dict) -> str:
        rows = result.get("candidate_scores", [])
        if not isinstance(rows, list) or not rows:
            return "none"
        parts = []
        for row in rows[:5]:
            if not isinstance(row, dict):
                continue
            parts.append(f"{row.get('title', '')}={row.get('score', '')}")
        return ", ".join(parts) if parts else "none"

    def set_status(self, status: str) -> None:
        item = self.current_item()
        if not item:
            return
        item["status"] = status
        if status == "resolved" and not (self.title_var.get().strip() or item.get("resolved_title")):
            if not messagebox.askyesno("Resolved with no title?", "Mark this resolved without a resolved title?"):
                return
        if status == "resolved":
            item["resolved_title"] = self.title_var.get().strip() or item.get("resolved_title", "")
            item["resolved_year"] = self.year_var.get().strip() or item.get("resolved_year", "")
            item["resolved_source_url"] = self.source_var.get().strip() or item.get("resolved_source_url", "")
            latest_lookup = {}
            lookups = item.get("lookup_results", [])
            if isinstance(lookups, list) and lookups:
                latest_lookup = lookups[-1]
            result = {
                "provider": latest_lookup.get("provider", "manual/Wikipedia"),
                "query": latest_lookup.get("query", ""),
                "title": item.get("resolved_title", ""),
                "url": item.get("resolved_source_url", ""),
                "extract": item.get("preview_back_of_case_summary") or latest_lookup.get("extract", ""),
                "candidates": latest_lookup.get("candidates", []),
            }
            update_card_from_lookup(item, result, "resolved_auto")
        self.save_current()

    def open_card(self) -> None:
        item = self.current_item()
        if not item:
            return
        card_path = PROJECT_ROOT / str(item.get("card_path", ""))
        if card_path.exists():
            os.startfile(str(card_path))
            self.status_var.set(f"Opened card: {rel(card_path)}")
        else:
            CARDS_DIR.mkdir(parents=True, exist_ok=True)
            os.startfile(str(CARDS_DIR))
            self.status_var.set(f"Card missing; opened generated card folder: {rel(CARDS_DIR)}")

    def lookup_wikipedia_current(self) -> None:
        item = self.current_item()
        if not item:
            return
        title = self.title_var.get().strip() or item.get("resolved_title") or item.get("title_guess", "")
        year = self.year_var.get().strip() or item.get("resolved_year") or item.get("year_guess", "")
        media_type = item.get("media_type_guess", "")
        self.status_var.set(f"Looking up Wikipedia for {title} {year}...")
        self.root.update_idletasks()
        result = wikipedia_lookup(str(title), str(year), str(media_type))
        if not result.get("ok"):
            self.status_var.set(f"Lookup failed: {result.get('error', 'unknown error')}")
            return
        self.title_var.set(str(result.get("title", title)))
        self.source_var.set(str(result.get("url", "")))
        self.apply_lookup_result(item, result, auto=False)
        note = item.get("review_note", "")
        self.review_note.delete("1.0", END)
        self.review_note.insert(END, note)
        self.queue["updated_at"] = utc_now()
        write_json(QUEUE_PATH, self.queue)
        self.status_var.set("Lookup filled the form. Review it, then click Resolved if it is the right work.")

    def auto_lookup_unresolved(self) -> None:
        unresolved = [
            item for item in self.items
            if item.get("status") in {"needs_lookup", "lookup_failed", ""}
        ]
        if not unresolved:
            self.status_var.set("No unresolved lookup items found.")
            return
        if not messagebox.askyesno(
            "Auto lookup unresolved?",
            f"Look up {len(unresolved)} unresolved media items with Wikipedia now? Obvious matches become resolved_auto; uncertain matches become ambiguous.",
        ):
            return
        threading.Thread(target=self.auto_lookup_worker, args=(unresolved,), daemon=True).start()

    def auto_lookup_worker(self, unresolved: list[dict]) -> None:
        resolved = 0
        ambiguous = 0
        failed = 0
        for index, item in enumerate(unresolved, start=1):
            title = lookup_title_for_item(item)
            year = lookup_year_for_item(item)
            media_type = item.get("media_type_guess", "")
            self.root.after(0, lambda i=index, total=len(unresolved), t=title: self.status_var.set(f"Auto lookup {i}/{total}: {t}"))
            result = wikipedia_lookup(str(title), str(year), str(media_type))
            time.sleep(0.5)
            if not result.get("ok"):
                item["status"] = "lookup_failed"
                item["lookup_error"] = result.get("error", "unknown error")
                failed += 1
                continue
            self.apply_lookup_result(item, result, auto=True)
            if item.get("status") == "resolved_auto":
                resolved += 1
            else:
                ambiguous += 1
        self.queue["updated_at"] = utc_now()
        write_json(QUEUE_PATH, self.queue)
        self.root.after(0, lambda: self.finish_auto_lookup(resolved, ambiguous, failed))

    def finish_auto_lookup(self, resolved: int, ambiguous: int, failed: int) -> None:
        self.reload()
        self.status_var.set(
            f"Auto lookup complete: {resolved} resolved_auto, {ambiguous} ambiguous for Robert, {failed} failed."
        )

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    MediaLookupReviewPanel().run()
