from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "Data" / "ai_workspaces" / "temporary_ai" / "temporary_ai_sarah_pr_robert_press_kit_20260606"


NEWS_QUERIES = [
    "entertainment industry news film tv music gaming",
    "film festival submission deadline 2026",
    "entertainment industry events 2026 film tv music",
]

COMPANY_PRESS_RELEASE_TARGETS = [
    {
        "company": "Amazon MGM Studios",
        "url": "https://press.amazonmgmstudios.com/us/en/press-releases",
        "focus": "Prime Video, MGM, studio announcements, releases, premieres, and publicity contacts.",
    },
    {
        "company": "Netflix",
        "url": "https://about.netflix.com/en/newsroom",
        "focus": "Netflix newsroom announcements, series/movie launches, company news, and publicity leads.",
    },
    {
        "company": "Disney",
        "url": "https://press.disney.com/",
        "focus": "Disney press releases and press-center leads across studio, streaming, parks, and corporate divisions.",
    },
    {
        "company": "Warner Bros. Discovery",
        "url": "https://press.wbd.com/",
        "focus": "Warner Bros. Discovery pressroom leads for film, TV, streaming, and corporate announcements.",
    },
    {
        "company": "Paramount",
        "url": "https://www.paramountpressexpress.com/",
        "focus": "Paramount press express leads for TV, streaming, studio, and publicity material.",
    },
    {
        "company": "NBCUniversal",
        "url": "https://www.nbcumv.com/",
        "focus": "NBCUniversal Media Village leads for TV, streaming, sports, and publicity material.",
    },
    {
        "company": "Apple TV+",
        "url": "https://www.apple.com/tv-pr/",
        "focus": "Apple TV+ press releases and publicity leads.",
    },
]

MEDIA_CONTACT_TARGETS = [
    {
        "outlet": "Variety",
        "url": "https://variety.com/contact/",
        "category": "trade",
        "purpose": "trade outlet contact/editorial lead for entertainment PR review",
    },
    {
        "outlet": "Deadline",
        "url": "https://deadline.com/contact/",
        "category": "trade",
        "purpose": "trade outlet contact/editorial lead for entertainment PR review",
    },
    {
        "outlet": "The Hollywood Reporter",
        "url": "https://www.hollywoodreporter.com/contact/",
        "category": "trade",
        "purpose": "trade outlet contact/editorial lead for entertainment PR review",
    },
    {
        "outlet": "IndieWire",
        "url": "https://www.indiewire.com/contact/",
        "category": "trade/indie",
        "purpose": "independent film/TV coverage contact lead",
    },
    {
        "outlet": "Filmmaker Magazine",
        "url": "https://filmmakermagazine.com/contact/",
        "category": "independent film",
        "purpose": "indie filmmaker coverage contact lead",
    },
    {
        "outlet": "Entertainment Weekly",
        "url": "https://ew.com/about-us-5201195",
        "category": "consumer entertainment",
        "purpose": "consumer entertainment outlet lead",
    },
]

EVENT_INVITE_TARGETS = [
    {
        "event": "Tribeca Festival",
        "url": "https://tribecafilm.com/press-center",
        "category": "festival",
        "purpose": "press accreditation, event invite, and festival timing lead",
    },
    {
        "event": "Toronto International Film Festival",
        "url": "https://tiff.net/press",
        "category": "festival",
        "purpose": "press accreditation and festival timing lead",
    },
    {
        "event": "New York Film Festival / Film at Lincoln Center",
        "url": "https://www.filmlinc.org/press/",
        "category": "festival",
        "purpose": "New York film press contact/accreditation lead",
    },
    {
        "event": "Sundance Institute",
        "url": "https://www.sundance.org/press/",
        "category": "festival",
        "purpose": "Sundance press and festival lead",
    },
]

EVENT_PLATFORM_TARGETS = [
    {
        "event": "Eventbrite - New York film premiere search",
        "url": "https://www.eventbrite.com/d/ny--new-york/film-premiere/",
        "category": "ticketed_events",
        "purpose": "Find public screenings, premieres, networking events, and industry panels Robert might attend.",
    },
    {
        "event": "1iota",
        "url": "https://1iota.com/",
        "category": "audience_tickets",
        "purpose": "Audience/ticket lead for TV tapings, fan events, red carpet opportunities, and live entertainment events.",
    },
    {
        "event": "Average Socialite - New York events",
        "url": "https://www.averagesocialite.com/",
        "category": "event_calendar",
        "purpose": "NYC event calendar lead for premieres, screenings, pop-ups, and public-facing entertainment events.",
    },
    {
        "event": "Premiere Scene",
        "url": "https://premierescene.net/",
        "category": "premiere_calendar",
        "purpose": "Premiere/red-carpet news lead for learning event patterns and possible attendance opportunities.",
    },
    {
        "event": "DoNYC film events",
        "url": "https://donyc.com/events/film",
        "category": "local_events",
        "purpose": "Public local film events and screenings in/near New York.",
    },
]

PREMIERE_TRACKING_QUERIES = [
    '"Supergirl" premiere New York event',
    '"Spider-Man" premiere New York event',
    '"New York" "red carpet" "film premiere" tickets',
    '"NYC" entertainment industry networking event film TV',
]

PERSON_LOOKUP_TARGETS = [
    {
        "title": "LinkedIn public search",
        "source": "LinkedIn public search",
        "url": "https://www.linkedin.com/search/results/people/",
        "purpose": "Manual public-profile lead for people Sarah may contact; do not scrape login/private data.",
    },
    {
        "title": "IMDbPro",
        "source": "IMDbPro",
        "url": "https://pro.imdb.com/",
        "purpose": "Professional credits/contact lead where Robert has access; some details require login.",
    },
    {
        "title": "Muck Rack",
        "source": "Muck Rack",
        "url": "https://muckrack.com/",
        "purpose": "Journalist/publicist profile lead for outlet/contact research.",
    },
    {
        "title": "Pressroom contact pages",
        "source": "Pressroom contact pages",
        "url": "https://press.wbd.com/us/contacts",
        "purpose": "Public company media-relations contact page lead for outreach planning.",
    },
]

ONLINE_PRESENCE_RECOMMENDATIONS = [
    {
        "title": "Short story/status video",
        "category": "youtube",
        "description": "A 2-4 minute update about a current project, framed around what changed, what Robert learned, and what comes next.",
        "hashtags": ["#IndependentFilm", "#Storytelling", "#ActorLife", "#Filmmaking"],
    },
    {
        "title": "Behind-the-scenes photo post",
        "category": "photo",
        "description": "A clean desk, script, location, or production-note photo with one short paragraph about process.",
        "hashtags": ["#BTS", "#CreativeProcess", "#FilmCommunity"],
    },
    {
        "title": "Book/project credibility post",
        "category": "author_pr",
        "description": "A post connecting Robert's books, acting, and filmmaking into one public-facing creative identity.",
        "hashtags": ["#Author", "#Screenwriter", "#IndieCreator"],
    },
]

ROBERT_QUERIES = [
    '"Robert McMurrer"',
    '"Robert L McMurrer"',
    "robertmcmurrer",
]

ROBERT_PUBLIC_PROFILE_TARGETS = [
    {
        "category": "imdb",
        "query": '"Robert McMurrer" IMDb',
        "purpose": "credits, professional film/TV profile, public biography facts",
    },
    {
        "category": "amazon_books",
        "query": '"Robert McMurrer" Amazon books',
        "purpose": "books, author listings, product descriptions, review/rating leads",
    },
    {
        "category": "youtube",
        "query": '"Robert McMurrer" YouTube',
        "purpose": "public videos, channel presentation, thumbnails, upload topics",
    },
    {
        "category": "facebook_public",
        "query": '"Robert McMurrer" Facebook rmcmurrer',
        "purpose": "public social profile summary and public-facing wording",
        "direct_urls": ["https://www.facebook.com/rmcmurrer/"],
    },
    {
        "category": "general_web",
        "query": '"Robert McMurrer" actor writer director producer',
        "purpose": "general public presence, profile consistency, duplicate/wrong-person risks",
    },
    {
        "category": "images",
        "query": '"Robert McMurrer" images',
        "purpose": "image search leads for press-kit/photo review; do not download without review",
    },
]

ROBERT_KNOWN_PUBLIC_SOURCES = [
    {
        "category": "imdb",
        "title": "Robert McMurrer - IMDb",
        "url": "https://www.imdb.com/name/nm2258412/",
        "source_type": "profile",
        "note": "Primary public credits page for Robert's film/TV work. Verify current credits during PR review.",
    },
    {
        "category": "imdbpro",
        "title": "Robert McMurrer - IMDbPro",
        "url": "https://pro.imdb.com/name/nm2258412/",
        "source_type": "profile",
        "note": "Professional profile/contact/credits lead. Some details may require IMDbPro login.",
    },
    {
        "category": "linkedin",
        "title": "Robert McMurrer - LinkedIn",
        "url": "https://www.linkedin.com/in/rmcmurrer",
        "source_type": "profile",
        "note": "Public professional/social profile lead. Use only visible public information.",
    },
    {
        "category": "youtube",
        "title": "Robert McMurrer - YouTube",
        "url": "https://www.youtube.com/rmcmurrer",
        "source_type": "social_video",
        "note": "Public video/channel lead for Sarah to review thumbnails, topics, and presentation.",
    },
    {
        "category": "facebook_public",
        "title": "Robert McMurrer - Facebook",
        "url": "https://www.facebook.com/rmcmurrer/",
        "source_type": "social_profile",
        "note": "Robert-provided Facebook profile URL. Use public information only; do not attempt login/private scraping.",
    },
    {
        "category": "book_listing",
        "title": "Bars Of Innocence - Walmart listing",
        "url": "https://www.walmart.com/ip/16358562861",
        "source_type": "book_listing",
        "note": "Public book listing lead for Bars Of Innocence. Verify title, author, date, ISBN, and description before PR use.",
    },
    {
        "category": "book_listing",
        "title": "Robert McMurrer - Goodreads author page",
        "url": "https://www.goodreads.com/author/show/6007307.Robert_McMurrer",
        "source_type": "author_profile",
        "note": "Public author/book profile lead. Verify book list and ratings before PR use.",
    },
    {
        "category": "book_listing",
        "title": "Poetry Madhouse - iMusic listing",
        "url": "https://imusic.dk/books/9781456534325/robert-mcmurrer-2011-poetry-madhouse-paperback-bog",
        "source_type": "book_listing",
        "note": "Public listing lead for Poetry Madhouse. Verify details before PR use.",
    },
    {
        "category": "amazon_books",
        "title": "Amazon search: Robert McMurrer",
        "url": "https://www.amazon.com/s?k=Robert+McMurrer",
        "source_type": "search_url",
        "note": "Manual Amazon search URL. Amazon may block automated extraction; Sarah should treat this as a review link.",
    },
]


def now_stamp() -> tuple[str, str]:
    now = datetime.now().astimezone()
    return now.strftime("%Y%m%d"), now.isoformat(timespec="seconds")


def safe_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value or "")
    value = html.unescape(value)
    value = value.replace("Â·", "-")
    return " ".join(value.split())


def fetch_url(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Kira-SarahPRDailyUpdate/1.0 (+local personal research tool)",
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read()


def fetch_public_page_summary(url: str) -> dict:
    item = {"url": url, "status": "not_fetched", "title": "", "description": "", "note": ""}
    try:
        data = fetch_url(url)
    except Exception as exc:
        item.update(
            {
                "status": "fetch_error",
                "note": f"Could not fetch public page automatically: {exc}",
                "manual_review_needed": True,
            }
        )
        return item

    text = data.decode("utf-8", errors="ignore")
    title_match = re.search(r"<title[^>]*>(.*?)</title>", text, flags=re.IGNORECASE | re.DOTALL)
    desc_match = re.search(
        r'<meta[^>]+(?:name|property)=["\'](?:description|og:description)["\'][^>]+content=["\'](.*?)["\']',
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not desc_match:
        desc_match = re.search(
            r'<meta[^>]+content=["\'](.*?)["\'][^>]+(?:name|property)=["\'](?:description|og:description)["\']',
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
    item.update(
        {
            "status": "fetched",
            "title": safe_text(title_match.group(1)) if title_match else "",
            "description": safe_text(desc_match.group(1)) if desc_match else "",
            "note": "Fetched title/meta description only; social sites may hide full profile details from automated reads.",
        }
    )
    return item


def bing_news(query: str, count: int = 8) -> list[dict]:
    params = urllib.parse.urlencode({"q": query, "format": "rss", "count": str(count)})
    url = f"https://www.bing.com/news/search?{params}"
    data = fetch_url(url)
    root = ET.fromstring(data)
    items = []
    for item in root.findall("./channel/item")[:count]:
        title = safe_text(item.findtext("title", ""))
        link = safe_text(item.findtext("link", ""))
        description = safe_text(item.findtext("description", ""))
        pub_date = safe_text(item.findtext("pubDate", ""))
        source = ""
        for child in list(item):
            if child.tag.endswith("source"):
                source = safe_text(child.text or "")
                break
        items.append(
            {
                "query": query,
                "title": title,
                "url": link,
                "source": source,
                "published": pub_date,
                "snippet": description,
            }
        )
    return items


def web_search(query: str, max_results: int = 8) -> list[dict]:
    try:
        from duckduckgo_search import DDGS
    except Exception as exc:
        fallback = bing_web_rss_search(query, max_results=max_results) or bing_web_search(query, max_results=max_results)
        if fallback:
            for item in fallback:
                item["fallback_reason"] = f"duckduckgo_search unavailable: {exc}"
            return fallback
        return [
            {
                "query": query,
                "status": "manual_search_required",
                "title": "Manual search lead",
                "error": str(exc),
                "manual_search_url": f"https://www.bing.com/search?q={urllib.parse.quote_plus(query)}",
                "note": "Automated search did not return a clean targeted result. Use this URL as a manual review lead.",
            }
        ]

    results = []
    try:
        with DDGS() as ddgs:
            for result in ddgs.text(query, max_results=max_results):
                candidate = " ".join(
                    [
                        result.get("title", ""),
                        result.get("href", ""),
                        result.get("body", ""),
                    ]
                ).lower()
                if "mcmurrer" not in candidate and "rmcmurrer" not in candidate:
                    continue
                results.append(
                    {
                        "query": query,
                        "title": safe_text(result.get("title", "")),
                        "url": safe_text(result.get("href", "")),
                        "snippet": safe_text(result.get("body", "")),
                    }
                )
    except Exception as exc:
        return [
            {
                "query": query,
                "status": "search_error",
                "error": str(exc),
                "manual_search_url": f"https://www.bing.com/search?q={urllib.parse.quote_plus(query)}",
            }
        ]
    return results


def bing_web_rss_search(query: str, max_results: int = 8) -> list[dict]:
    params = urllib.parse.urlencode({"q": query, "format": "rss", "count": str(max_results)})
    url = f"https://www.bing.com/search?{params}"
    try:
        data = fetch_url(url)
        root = ET.fromstring(data)
    except Exception:
        return []

    results: list[dict] = []
    for item in root.findall("./channel/item"):
        title = safe_text(item.findtext("title", ""))
        link = safe_text(item.findtext("link", ""))
        description = safe_text(item.findtext("description", ""))
        candidate = " ".join([title, link, description]).lower()
        if "mcmurrer" not in candidate and "rmcmurrer" not in candidate:
            continue
        results.append(
            {
                "query": query,
                "title": title,
                "url": link,
                "snippet": description,
                "provider": "bing_rss",
            }
        )
        if len(results) >= max_results:
            break
    return results


def bing_web_search(query: str, max_results: int = 8) -> list[dict]:
    params = urllib.parse.urlencode({"q": query, "count": str(max_results)})
    url = f"https://www.bing.com/search?{params}"
    try:
        html_text = fetch_url(url).decode("utf-8", errors="ignore")
    except Exception:
        return []

    results: list[dict] = []
    for match in re.finditer(r'<li class="b_algo".*?</li>', html_text, flags=re.IGNORECASE | re.DOTALL):
        block = match.group(0)
        link_match = re.search(r'<h2[^>]*>\s*<a[^>]+href=["\'](.*?)["\'][^>]*>(.*?)</a>', block, flags=re.IGNORECASE | re.DOTALL)
        if not link_match:
            continue
        href = html.unescape(link_match.group(1))
        title = safe_text(link_match.group(2))
        snippet = ""
        snippet_match = re.search(r'<p[^>]*>(.*?)</p>', block, flags=re.IGNORECASE | re.DOTALL)
        if snippet_match:
            snippet = safe_text(snippet_match.group(1))
        candidate = " ".join([title, href, snippet]).lower()
        if "mcmurrer" not in candidate and "rmcmurrer" not in candidate:
            continue
        results.append({"query": query, "title": title, "url": href, "snippet": snippet, "provider": "bing_html"})
        if len(results) >= max_results:
            break
    return results


def gather_robert_public_profile() -> tuple[list[tuple[str, list[dict]]], list[dict]]:
    sections: list[tuple[str, list[dict]]] = []
    all_items: list[dict] = []
    known_items = []
    for source in ROBERT_KNOWN_PUBLIC_SOURCES:
        item = dict(source)
        item["query"] = "known_public_source_seed"
        item["purpose"] = "hand-checked public source lead for Sarah PR review"
        summary = fetch_public_page_summary(item["url"])
        if summary.get("status") == "fetched":
            if summary.get("title"):
                item["fetched_title"] = summary["title"]
            if summary.get("description"):
                item["public_description"] = summary["description"]
            item["fetch_note"] = summary.get("note", "")
        elif summary.get("note"):
            item["fetch_note"] = summary["note"]
        known_items.append(item)
    sections.append(("known public source seeds", known_items))
    all_items.extend(known_items)
    for target in ROBERT_PUBLIC_PROFILE_TARGETS:
        category = target["category"]
        query = target["query"]
        direct_items = []
        for url in target.get("direct_urls", []):
            page = fetch_public_page_summary(url)
            page["query"] = query
            page["category"] = category
            page["purpose"] = target["purpose"]
            page["title"] = page.get("title") or f"Direct page: {url}"
            direct_items.append(page)

        search_items = []
        for result in web_search(query, max_results=8):
            result["category"] = category
            result["purpose"] = target["purpose"]
            search_items.append(result)

        items = direct_items + search_items
        sections.append((f"{category}: {query}", items))
        all_items.extend(items)
    return sections, all_items


def gather_pr_industry_sources() -> tuple[list[tuple[str, list[dict]]], list[dict]]:
    sections: list[tuple[str, list[dict]]] = []
    all_items: list[dict] = []
    groups = [
        ("company press rooms", COMPANY_PRESS_RELEASE_TARGETS, "company"),
        ("media contact leads", MEDIA_CONTACT_TARGETS, "outlet"),
        ("event invite / accreditation leads", EVENT_INVITE_TARGETS, "event"),
        ("event platforms and premiere calendars", EVENT_PLATFORM_TARGETS, "event"),
        ("person lookup and contact-research sources", PERSON_LOOKUP_TARGETS, "source"),
    ]
    for heading, targets, label_key in groups:
        items = []
        for target in targets:
            item = dict(target)
            item["source_type"] = heading
            item["status"] = "seeded"
            summary = fetch_public_page_summary(item["url"])
            if summary.get("status") == "fetched":
                item["status"] = "fetched"
                item["fetched_title"] = summary.get("title", "")
                item["public_description"] = summary.get("description", "")
                item["fetch_note"] = summary.get("note", "")
            else:
                item["status"] = summary.get("status", "manual_review_needed")
                item["fetch_note"] = summary.get("note", "")
                item["manual_review_needed"] = True
            item["use_rule"] = (
                "Public lead only. Sarah may use this to plan outreach and drafts, "
                "but Robert must review before any email, upload, submission, or contact."
            )
            if label_key in item:
                item["title"] = item[label_key]
            items.append(item)
        sections.append((heading, items))
        all_items.extend(items)
    return sections, all_items


def gather_event_opportunity_sources() -> tuple[list[tuple[str, list[dict]]], list[dict]]:
    sections: list[tuple[str, list[dict]]] = []
    all_items: list[dict] = []

    platform_items = []
    for target in EVENT_PLATFORM_TARGETS:
        item = dict(target)
        item["source_type"] = "event_platform"
        summary = fetch_public_page_summary(item["url"])
        item["status"] = summary.get("status", "manual_review_needed")
        item["fetched_title"] = summary.get("title", "")
        item["public_description"] = summary.get("description", "")
        item["fetch_note"] = summary.get("note", "")
        item["use_rule"] = "Public lead only. Sarah can plan attendance/outreach, but Robert reviews before applying or contacting anyone."
        item["title"] = item["event"]
        platform_items.append(item)
    sections.append(("public event platforms", platform_items))
    all_items.extend(platform_items)

    for query in PREMIERE_TRACKING_QUERIES:
        items = web_search(query, max_results=8)
        for item in items:
            item["source_type"] = "premiere_tracking_search"
            item["use_rule"] = "Search lead only. Verify date, location, public eligibility, and source before suggesting attendance."
        sections.append((f"premiere/event search: {query}", items))
        all_items.extend(items)

    return sections, all_items


def gather_online_presence_plan() -> tuple[list[tuple[str, list[dict]]], list[dict]]:
    sections: list[tuple[str, list[dict]]] = []
    all_items: list[dict] = []
    items = []
    for recommendation in ONLINE_PRESENCE_RECOMMENDATIONS:
        item = dict(recommendation)
        item["status"] = "template"
        item["use_rule"] = "Sarah should adapt this to Robert's newest project, photos, and public-profile review."
        item["title"] = recommendation["title"]
        items.append(item)
    sections.append(("repeatable social/video recommendations", items))
    all_items.extend(items)

    post_templates = [
        {
            "title": "Project update caption",
            "category": "caption_template",
            "description": "Today I made progress on [project]. The part I keep coming back to is [human detail]. I’m looking forward to sharing more as it takes shape.",
            "hashtags": ["#IndependentCreator", "#Film", "#Writing", "#BehindTheScenes"],
        },
        {
            "title": "Premiere/networking caption",
            "category": "caption_template",
            "description": "Heading into [event] with a notebook full of ideas and a real appreciation for the people who keep independent film moving.",
            "hashtags": ["#NYCFilm", "#FilmCommunity", "#EntertainmentIndustry"],
        },
        {
            "title": "Author/actor positioning caption",
            "category": "caption_template",
            "description": "I’ve always been drawn to stories about survival, identity, and rebuilding. That thread runs through my books, acting, and current projects.",
            "hashtags": ["#Actor", "#Author", "#Storyteller", "#CreativeLife"],
        },
    ]
    sections.append(("caption and hashtag templates", post_templates))
    all_items.extend(post_templates)
    return sections, all_items


def ensure_sarah_workspace_structure(workspace: Path) -> list[Path]:
    folders = [
        workspace / "contact_database",
        workspace / "daily_research" / "company_press_releases",
        workspace / "daily_research" / "media_contacts",
        workspace / "daily_research" / "event_invites",
        workspace / "daily_research" / "event_opportunities",
        workspace / "daily_research" / "online_presence",
        workspace / "outputs" / "press_releases",
        workspace / "outputs" / "bios",
        workspace / "outputs" / "pitch_emails",
        workspace / "outputs" / "press_kits",
        workspace / "outputs" / "image_strategy",
    ]
    for folder in folders:
        folder.mkdir(parents=True, exist_ok=True)
    readme = workspace / "outputs" / "README_publicist_outputs.md"
    if not readme.exists():
        readme.write_text(
            "# Sarah Bennett Output Folders\n\n"
            "Sarah should save reviewable drafts here when Robert asks for press releases, bios, pitch emails, press kits, or image strategy.\n\n"
            "- `press_releases/`: public release drafts\n"
            "- `bios/`: short/long bio drafts\n"
            "- `pitch_emails/`: outlet-specific outreach drafts\n"
            "- `press_kits/`: press-kit copy and asset lists\n"
            "- `image_strategy/`: public image plans and review notes\n\n"
            "Sarah may also keep daily review leads under `daily_research/`, including event opportunities and online-presence ideas.\n\n"
            "Drafts are not sent or uploaded automatically.\n",
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
        if not items:
            lines.append("- No items returned.")
        for item in items:
            title_text = item.get("title") or item.get("company") or item.get("outlet") or item.get("event") or item.get("status") or "Untitled"
            url = item.get("url") or item.get("manual_search_url") or ""
            source = item.get("source") or ""
            published = item.get("published") or ""
            snippet = (
                item.get("snippet")
                or item.get("public_description")
                or item.get("description")
                or item.get("note")
                or item.get("error")
                or ""
            )
            lines.append(f"- **{title_text}**")
            if item.get("fetched_title") and item.get("fetched_title") != title_text:
                lines.append(f"  - fetched title: {item['fetched_title']}")
            if source or published:
                lines.append(f"  - source/date: {source} {published}".strip())
            if url:
                lines.append(f"  - url: {url}")
            if snippet:
                lines.append(f"  - note: {snippet}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def append_review_note(path: Path, generated_at: str, output_files: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""
    note = [
        "",
        f"## Daily public research update - {generated_at}",
        "",
        "Sarah should treat these as search leads, source notes, and current-news notes, not verified biography.",
        "Review before using anything in public-facing copy.",
        "",
    ]
    for file_name in output_files:
        note.append(f"- {file_name}")
    path.write_text(existing.rstrip() + "\n" + "\n".join(note) + "\n", encoding="utf-8")


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
            entry = {
                "source_path": str(workspace_rel / rel).replace("\\", "/"),
                "relative_source_path": rel,
                "extension": path.suffix,
                "status": "extracted",
                "extracted_text_path": "",
            }
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
    manifest.setdefault("daily_research", {})["last_update_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    manifest["daily_research"]["last_update_files"] = [str(path.relative_to(ROOT)) for path in generated_paths]
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Refresh Sarah Bennett PR research files.")
    parser.add_argument("--workspace", default=str(WORKSPACE), help="Sarah PR workspace path")
    parser.add_argument("--skip-news", action="store_true")
    parser.add_argument("--skip-robert", action="store_true")
    args = parser.parse_args(argv)

    workspace = Path(args.workspace)
    date_key, generated_at = now_stamp()
    outputs = []
    generated_paths: list[Path] = ensure_sarah_workspace_structure(workspace)

    if not args.skip_news:
        news_sections = []
        all_news = []
        for query in NEWS_QUERIES:
            try:
                items = bing_news(query)
            except Exception as exc:
                items = [{"query": query, "status": "news_fetch_error", "error": str(exc)}]
            news_sections.append((query, items))
            all_news.extend(items)
        news_json = workspace / "daily_research" / "entertainment_news" / f"{date_key}_entertainment_news.json"
        news_md = workspace / "daily_research" / "entertainment_news" / f"{date_key}_entertainment_news.md"
        write_json(news_json, {"generated_at": generated_at, "items": all_news})
        write_markdown(news_md, "Entertainment News And Event Leads", news_sections, generated_at)
        outputs.extend([str(news_json.relative_to(ROOT)), str(news_md.relative_to(ROOT))])
        generated_paths.extend([news_json, news_md])

        pr_sections, pr_items = gather_pr_industry_sources()
        pr_json = workspace / "daily_research" / "company_press_releases" / f"{date_key}_company_press_release_and_contact_leads.json"
        pr_md = workspace / "daily_research" / "company_press_releases" / f"{date_key}_company_press_release_and_contact_leads.md"
        write_json(
            pr_json,
            {
                "generated_at": generated_at,
                "policy": {
                    "public_sources_only": True,
                    "no_auto_contact": True,
                    "use_in_pr": "These are current public leads for Sarah to review before drafting outreach or event plans.",
                },
                "items": pr_items,
            },
        )
        write_markdown(pr_md, "Company Press Room, Media Contact, And Event Invite Leads", pr_sections, generated_at)
        outputs.extend([str(pr_json.relative_to(ROOT)), str(pr_md.relative_to(ROOT))])
        generated_paths.extend([pr_json, pr_md])

        contact_db = workspace / "contact_database" / "media_contact_database.json"
        write_json(
            contact_db,
            {
                "updated_at": generated_at,
                "status": "public_leads_for_robert_review",
                "rules": [
                    "Do not email, upload, submit, or contact anyone automatically.",
                    "Treat emails/contact pages as public leads until Robert verifies they are appropriate.",
                    "Store outlet, category, URL, purpose, and review notes before drafting outreach.",
                ],
                "company_press_rooms": COMPANY_PRESS_RELEASE_TARGETS,
                "media_contacts": MEDIA_CONTACT_TARGETS,
                "event_invite_leads": EVENT_INVITE_TARGETS,
                "event_platforms": EVENT_PLATFORM_TARGETS,
                "person_lookup_sources": PERSON_LOOKUP_TARGETS,
            },
        )
        contact_md = workspace / "contact_database" / "media_contact_database.md"
        write_markdown(
            contact_md,
            "Sarah Media Contact Database",
            [
                ("company press rooms", COMPANY_PRESS_RELEASE_TARGETS),
                ("media contacts", MEDIA_CONTACT_TARGETS),
                ("event invite leads", EVENT_INVITE_TARGETS),
                ("event platforms", EVENT_PLATFORM_TARGETS),
                ("person lookup sources", PERSON_LOOKUP_TARGETS),
            ],
            generated_at,
        )
        outputs.extend([str(contact_db.relative_to(ROOT)), str(contact_md.relative_to(ROOT))])
        generated_paths.extend([contact_db, contact_md])

        event_sections, event_items = gather_event_opportunity_sources()
        event_json = workspace / "daily_research" / "event_opportunities" / f"{date_key}_event_opportunity_leads.json"
        event_md = workspace / "daily_research" / "event_opportunities" / f"{date_key}_event_opportunity_leads.md"
        write_json(
            event_json,
            {
                "generated_at": generated_at,
                "policy": {
                    "public_sources_only": True,
                    "no_auto_applications": True,
                    "use_in_pr": "Sarah can use these leads to suggest public events, screenings, premieres, and outreach steps.",
                },
                "items": event_items,
            },
        )
        write_markdown(event_md, "Event, Premiere, And Attendance Opportunity Leads", event_sections, generated_at)
        outputs.extend([str(event_json.relative_to(ROOT)), str(event_md.relative_to(ROOT))])
        generated_paths.extend([event_json, event_md])

        presence_sections, presence_items = gather_online_presence_plan()
        presence_json = workspace / "daily_research" / "online_presence" / f"{date_key}_online_presence_suggestions.json"
        presence_md = workspace / "daily_research" / "online_presence" / f"{date_key}_online_presence_suggestions.md"
        write_json(
            presence_json,
            {
                "generated_at": generated_at,
                "policy": {
                    "robert_review_required": True,
                    "no_auto_posting": True,
                    "use_in_pr": "Sarah can adapt these into captions, video ideas, photo ideas, and hashtag suggestions.",
                },
                "items": presence_items,
            },
        )
        write_markdown(presence_md, "Online Presence, Video, Photo, And Hashtag Suggestions", presence_sections, generated_at)
        outputs.extend([str(presence_json.relative_to(ROOT)), str(presence_md.relative_to(ROOT))])
        generated_paths.extend([presence_json, presence_md])

    if not args.skip_robert:
        robert_sections = []
        all_robert = []
        for query in ROBERT_QUERIES:
            items = web_search(query)
            robert_sections.append((query, items))
            all_robert.extend(items)
        robert_json = workspace / "inputs" / "online_research" / "robert_public_sources" / f"{date_key}_robert_public_search.json"
        robert_md = workspace / "inputs" / "online_research" / "robert_public_sources" / f"{date_key}_robert_public_search.md"
        write_json(robert_json, {"generated_at": generated_at, "items": all_robert})
        write_markdown(robert_md, "Robert Public Search Leads", robert_sections, generated_at)
        outputs.extend([str(robert_json.relative_to(ROOT)), str(robert_md.relative_to(ROOT))])
        generated_paths.extend([robert_json, robert_md])

        append_review_note(
            workspace / "inputs" / "online_research" / "robert_online_presence_review.md",
            generated_at,
            outputs,
        )
        generated_paths.append(workspace / "inputs" / "online_research" / "robert_online_presence_review.md")

        public_sections, public_items = gather_robert_public_profile()
        public_json = workspace / "inputs" / "online_research" / "robert_public_sources" / f"{date_key}_robert_public_profile_intake.json"
        public_md = workspace / "inputs" / "online_research" / "robert_public_sources" / f"{date_key}_robert_public_profile_intake.md"
        write_json(
            public_json,
            {
                "generated_at": generated_at,
                "policy": {
                    "public_sources_only": True,
                    "social_media": "Only public page metadata/search leads are collected. Login/private content is not accessed.",
                    "use_in_pr": "Review and verify before Sarah uses any item in public-facing copy.",
                },
                "targets": ROBERT_PUBLIC_PROFILE_TARGETS,
                "items": public_items,
            },
        )
        write_markdown(public_md, "Robert Public Profile Intake", public_sections, generated_at)
        outputs.extend([str(public_json.relative_to(ROOT)), str(public_md.relative_to(ROOT))])
        generated_paths.extend([public_json, public_md])

    update_workspace_manifest(workspace, generated_paths)

    print(json.dumps({"status": "ok", "generated_at": generated_at, "outputs": outputs}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
