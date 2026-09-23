"""Isolated, resumable public-text research for World Builder.

This collector produces provenance and unreviewed source observations. It does
not declare images/video inspected, generate geometry, or load resident state.
"""
from __future__ import annotations

import argparse
import base64
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import http.client
from html import unescape
from html.parser import HTMLParser
import ipaddress
import json
from pathlib import Path
import re
import socket
import tempfile
import time
from typing import Any, Callable
from urllib.error import HTTPError
from urllib.parse import parse_qs, quote_plus, unquote, urljoin, urlsplit, urlunsplit
from urllib.request import HTTPHandler, HTTPSHandler, HTTPRedirectHandler, ProxyHandler, Request, build_opener
import xml.etree.ElementTree as ET
from adaptive_source_selection import select_candidates


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JOB_ROOT = ROOT / "Data" / "world_research_jobs"
MAX_BYTES = 1_000_000
MAX_LINKS = 80
MAX_TEXT = 100_000
MAX_ATTEMPTS = 3
TIMEOUT = 12
MAX_REDIRECTS = 3
TEXT_TYPES = {"text/html", "application/xhtml+xml", "text/plain"}
SEARCH_TYPES = TEXT_TYPES | {"application/rss+xml", "application/xml", "text/xml"}
SCHEMA = 1
POLICY = {
    "whole_real_area_without_photograph_or_video": "locked_solid",
    "plan_without_visual_coverage_unlocks_area": False,
    "small_missing_detail_in_documented_room": "estimate_with_derivation",
    "original_architecture": "authored_design_informed_by_multiple_analogs",
    "paid_generation": "locked",
    "resident_world_mutation": False,
}


class ResearchError(ValueError):
    pass


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require_text(value: Any, name: str, maximum: int = 800) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ResearchError(f"{name} must be non-empty text of at most {maximum} characters")
    return value.strip()


def public_addresses(host: str, port: int, *, resolver: Callable = socket.getaddrinfo) -> list[tuple]:
    """Return validated numeric socket addresses, never a hostname to re-resolve."""
    normalized = host.rstrip(".").lower()
    if normalized in {"localhost", "localhost.localdomain"} or normalized.endswith((".localhost", ".local", ".internal")):
        raise ResearchError("Private or loopback destination is not accepted")
    try:
        addresses = list(resolver(host, port, type=socket.SOCK_STREAM))
        if not addresses or len(addresses) > 64:
            raise ResearchError("Invalid destination address count")
        for family, socktype, protocol, canonical_name, sockaddr in addresses:
            address = ipaddress.ip_address(sockaddr[0])
            if family not in {socket.AF_INET, socket.AF_INET6} or socktype != socket.SOCK_STREAM or not address.is_global or sockaddr[1] != port:
                raise ResearchError("Destination resolves to private, loopback, reserved, or non-global address")
    except (OSError, ValueError, TypeError, IndexError) as exc:
        if isinstance(exc, ResearchError):
            raise
        raise ResearchError(f"Destination lookup failed: {type(exc).__name__}") from exc
    return addresses


def connect_public_socket(host: str, port: int, timeout: float, *, source_address=None,
                          resolver: Callable = socket.getaddrinfo, socket_factory: Callable = socket.socket,
                          clock: Callable = time.monotonic):
    addresses = public_addresses(host, port, resolver=resolver)
    last_error = None
    deadline = clock() + timeout
    for family, socktype, protocol, canonical_name, sockaddr in addresses:
        remaining = deadline - clock()
        if remaining <= 0:
            raise ResearchError("Public destination exhausted the shared connection deadline")
        sock = socket_factory(family, socktype, protocol)
        try:
            sock.settimeout(remaining)
            if source_address:
                sock.bind(source_address)
            # sockaddr contains only a validated numeric IP, so connect cannot
            # perform a second DNS resolution after the security decision.
            sock.connect(sockaddr)
            return sock
        except OSError as exc:
            last_error = exc
            sock.close()
    raise ResearchError(f"Public destination connection failed: {type(last_error).__name__}")


class PinnedHTTPConnection(http.client.HTTPConnection):
    def connect(self):
        if self._tunnel_host:
            raise ResearchError("HTTP tunneling is unsupported")
        self.sock = connect_public_socket(self.host, self.port, self.timeout, source_address=self.source_address)


class PinnedHTTPSConnection(http.client.HTTPSConnection):
    def connect(self):
        if self._tunnel_host:
            raise ResearchError("HTTPS tunneling is unsupported")
        sock = connect_public_socket(self.host, self.port, self.timeout, source_address=self.source_address)
        try:
            # Certificate verification and SNI retain the original URL hostname.
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
        except Exception:
            sock.close()
            raise


class PinnedHTTPHandler(HTTPHandler):
    def http_open(self, req):
        return self.do_open(PinnedHTTPConnection, req)


class PinnedHTTPSHandler(HTTPSHandler):
    def https_open(self, req):
        return self.do_open(PinnedHTTPSConnection, req, context=self._context)


def public_url(url: str, *, resolver: Callable = socket.getaddrinfo) -> str:
    """Validate every destination, including redirect destinations, before use."""
    require_text(url, "source URL", 4096)
    if any(ord(char) < 32 for char in url) or "\\" in url:
        raise ResearchError("URL contains a control character or backslash")
    parsed = urlsplit(url)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise ResearchError("Only public HTTP(S) URLs are accepted")
    if parsed.username is not None or parsed.password is not None:
        raise ResearchError("Credential-bearing URLs are not accepted")
    host = parsed.hostname.rstrip(".").lower()
    if host in {"localhost", "localhost.localdomain"} or host.endswith((".localhost", ".local", ".internal")):
        raise ResearchError("Private or loopback destination is not accepted")
    try:
        port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)
    except ValueError as exc:
        raise ResearchError("Invalid URL port") from exc
    if port not in {80, 443}:
        raise ResearchError("Only public web ports 80 and 443 are accepted")
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None and not literal.is_global:
        raise ResearchError("Private or loopback destination is not accepted")
    public_addresses(host, port, resolver=resolver)
    return urlunsplit((parsed.scheme.lower(), parsed.netloc, parsed.path or "/", parsed.query, ""))


class PublicRedirects(HTTPRedirectHandler):
    def __init__(self, resolver: Callable = socket.getaddrinfo):
        self.resolver = resolver
        self.count = 0

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.count += 1
        if self.count > MAX_REDIRECTS:
            raise ResearchError("Redirect budget exhausted")
        safe = public_url(newurl, resolver=self.resolver)
        return super().redirect_request(req, fp, code, msg, headers, safe)


def fetch_public_document(url: str, *, accepted_types: set[str] = TEXT_TYPES) -> dict:
    safe = public_url(url)
    opener = build_opener(ProxyHandler({}), PublicRedirects(), PinnedHTTPHandler(), PinnedHTTPSHandler())
    request = Request(safe, headers={
        "User-Agent": "KiraWorldResearchCandidate/1.0 (public source research)",
        "Accept": "text/html,text/plain,application/xhtml+xml,application/rss+xml,application/xml;q=0.8",
        "Accept-Encoding": "identity",
    })
    started = time.monotonic()
    with opener.open(request, timeout=TIMEOUT) as response:
        final_url = public_url(response.geturl())
        content_type = response.headers.get_content_type().lower()
        if content_type not in accepted_types:
            raise ResearchError(f"Uninspected media type {content_type}; public-text collector does not download it")
        encoding = response.headers.get("Content-Encoding", "identity").strip().lower()
        if encoding not in {"", "identity"}:
            raise ResearchError("Compressed response is unsupported in this bounded collector")
        length = response.headers.get("Content-Length")
        if length and (not length.isdigit() or int(length) > MAX_BYTES):
            raise ResearchError("Source exceeds byte budget or has an invalid Content-Length")
        chunks = []
        total = 0
        while True:
            if time.monotonic() - started > TIMEOUT * 2:
                raise ResearchError("Source exceeded the overall read deadline")
            chunk = response.read1(min(65536, MAX_BYTES + 1 - total))
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_BYTES:
                raise ResearchError("Source exceeded byte budget")
            chunks.append(chunk)
        payload = b"".join(chunks)
        return {"requested_url": safe, "final_url": final_url, "content_type": content_type,
                "charset": response.headers.get_content_charset() or "utf-8", "data": payload}


class PublicTextParser(HTMLParser):
    BLOCKS = {"p", "div", "section", "article", "main", "h1", "h2", "h3", "h4", "li", "br", "tr"}
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.links: list[dict] = []
        self.suppressed = 0
        self.in_title = False
        self.title_parts: list[str] = []
        self.anchor: dict | None = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {"script", "style", "noscript", "template"}:
            self.suppressed += 1
        if self.suppressed:
            return
        if tag == "title":
            self.in_title = True
        if tag in self.BLOCKS:
            self.parts.append("\n")
        if tag == "a" and attrs.get("href"):
            self.anchor = {"url": attrs["href"], "text": "", "kind": "link"}
        if tag in {"img", "video", "source"} and attrs.get("src") and len(self.links) < MAX_LINKS:
            self.links.append({"url": attrs["src"], "text": attrs.get("alt", ""),
                               "kind": "photo" if tag == "img" else "video"})

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript", "template"}:
            self.suppressed = max(0, self.suppressed - 1)
            return
        if self.suppressed:
            return
        if tag == "title":
            self.in_title = False
        if tag == "a" and self.anchor:
            if len(self.links) < MAX_LINKS:
                self.links.append(self.anchor)
            self.anchor = None
        if tag in self.BLOCKS:
            self.parts.append("\n")

    def handle_data(self, data):
        if self.suppressed:
            return
        self.parts.append(data)
        if self.in_title:
            self.title_parts.append(data)
        if self.anchor:
            self.anchor["text"] += data


def extract_text(document: dict) -> dict:
    try:
        decoded = document["data"].decode(document.get("charset", "utf-8"), errors="replace")
    except LookupError:
        decoded = document["data"].decode("utf-8", errors="replace")
    parser = PublicTextParser()
    if document["content_type"] == "text/plain":
        raw, links, title = decoded, [], ""
    else:
        parser.feed(decoded)
        raw, links, title = "".join(parser.parts), parser.links, " ".join(parser.title_parts)
    lines = [re.sub(r"\s+", " ", line).strip() for line in raw.splitlines()]
    text = "\n".join(line for line in lines if line)[:MAX_TEXT]
    safe_links, seen = [], set()
    for item in links:
        absolute = urljoin(document["final_url"], item["url"])
        parsed = urlsplit(absolute)
        if parsed.scheme not in {"http", "https"} or parsed.username or parsed.password or absolute in seen:
            continue
        seen.add(absolute)
        kind = item["kind"]
        if parsed.path.lower().endswith(".pdf"):
            kind = "document"
        safe_links.append({"url": absolute, "text": item["text"][:300], "kind": kind,
                           "inspection_status": "uninspected_link"})
    candidates = []
    measurement = re.compile(r"\b\d[\d,.]*\s*(?:m[²³23]|meters?|metres?|square\s+(?:feet|meters|metres)|cubic\s+(?:meters|metres)|sq\.?\s*ft|ft[²³23])\b", re.I)
    for line_number, line in enumerate(text.splitlines(), 1):
        for match in measurement.finditer(line):
            candidates.append({"text": match.group(0), "context": line[:500],
                               "locator": {"kind": "extracted_text_line", "line": line_number},
                               "status": "unverified_extraction_not_design_dimension"})
            if len(candidates) >= 40:
                break
        if len(candidates) >= 40:
            break
    return {"title": re.sub(r"\s+", " ", title).strip()[:300], "text": text,
            "links": safe_links, "measurement_candidates": candidates}


def search_public_web(query: str, limit: int = 4) -> dict:
    """Generic adaptation of the resident Bing-RSS/DDG lead lookup pattern."""
    query = require_text(query, "search query", 500)
    errors = []
    rss_url = "https://www.bing.com/search?format=rss&q=" + quote_plus(query)
    try:
        document = fetch_public_document(rss_url, accepted_types=SEARCH_TYPES)
        tree = ET.fromstring(document["data"])
        results = [{"url": item.findtext("link") or "", "title": item.findtext("title") or "",
                    "snippet": item.findtext("description") or "", "inspection_status": "search_lead_only"}
                   for item in tree.findall("./channel/item")]
        results = [item for item in results if item["url"].startswith(("http://", "https://"))][:limit]
        if results:
            return {"provider": "bing_rss", "query": query, "results": results,
                    "response_sha256": digest(document["data"]), "response_bytes": len(document["data"]), "errors": errors}
        errors.append("Bing RSS returned no usable results")
    except Exception as exc:
        errors.append(f"Bing RSS: {type(exc).__name__}: {exc}")
    ddg_url = "https://duckduckgo.com/html/?q=" + quote_plus(query)
    document = fetch_public_document(ddg_url)
    text = document["data"].decode("utf-8", errors="replace")
    results = []
    for attrs, raw_title in re.findall(r"<a\b([^>]*class=[\"'][^\"']*result__a[^\"']*[\"'][^>]*)>(.*?)</a>", text, re.I | re.S):
        href = re.search(r"href=[\"']([^\"']+)", attrs, re.I)
        if not href:
            continue
        link = urljoin(document["final_url"], unescape(href.group(1)))
        parsed = urlsplit(link)
        if parsed.path.startswith("/l/"):
            link = unquote(parse_qs(parsed.query).get("uddg", [link])[0])
        if link.startswith(("http://", "https://")):
            results.append({"url": link, "title": unescape(re.sub(r"<[^>]+>", "", raw_title)),
                            "snippet": "", "inspection_status": "search_lead_only"})
        if len(results) >= limit:
            break
    if not results:
        raise ResearchError("Public search yielded no usable results; " + "; ".join(errors))
    return {"provider": "duckduckgo_html", "query": query, "results": results,
            "response_sha256": digest(document["data"]), "response_bytes": len(document["data"]), "errors": errors}


def infer_research_mode(prompt: str) -> str:
    """Classify a new request conservatively; never reinterpret a saved brief.

    Originality must describe the requested creation, not an existing place's
    original layout or a reference source. Unclear named places stay locked.
    """
    real = "real_place_reconstruction"
    original = "analog_to_original"
    # Bound negation/reference scope to each clause: "not a replica" is an
    # excluded alternative, but "No, recreate the Louvre" is a correction.
    clauses = re.split(r"[,.!?;\n]|\b(?:but|instead)\b", prompt.strip(), flags=re.I)
    positive = []
    for clause in clauses:
        clause = re.split(r"\b(?:inspired by|based on|like|with inspiration from|using references from)\b",
                          clause, maxsplit=1, flags=re.I)[0]
        if re.search(r"\bnot\s+(?:an?\s+)?(?:original|fictional|imaginary|invented)\b", clause, re.I):
            return real
        clause = re.split(r"\b(?:not|never|without|no)\b|\bdon['\u2019]t\b",
                          clause, maxsplit=1, flags=re.I)[0].strip()
        positive.append(clause)
        if re.search(r"\b(?:recreat\w*|reconstruct\w*|replicat\w*|replica|reproduc\w*)\b|"
                     r"\b(?:exact\s+)?copy\s+of\b|"
                     r"\b(?:preserv\w*|retain\w*|restor\w*)\b.{0,100}\b"
                     r"(?:original|existing|actual|floor\s+plans?|layouts?|dimensions)\b",
                     clause, re.I):
            return real
    # Only the first target can establish original-creation intent; a later
    # originality adjective cannot unlock an ambiguous named first target.
    head = positive[0] if positive else ""
    if re.search(r"\b(?:existing|actual|real|real-world|historic|historical)\b|"
                 r"\b(?:at|inside|within|attached to|extension of)\b", head, re.I):
        return real
    match = re.match(r"^(?:(?:please|can you|could you|would you|i want you to|"
                     r"i would like you to|i'd like you to)\s+)?"
                     r"(build|create|make|design|invent)\s+(?:me\s+)?(?:an?\s+)?(.+)$",
                     head, re.I)
    if not match:
        return real
    command, target = match.groups()
    words = re.findall(r"[a-z]+(?:-[a-z]+)?", target.lower())
    if not words or words[0] in {"the", "this", "that", "my", "our"}:
        return real
    # Explicit fictional labels can name a new world. "Original Louvre Museum"
    # is ambiguous and is deliberately not equivalent to a fictional museum.
    descriptors = {"original", "new", "brand-new", "invented", "fictional", "imaginary",
                   "small", "large", "modern", "futuristic", "realistic", "photorealistic",
                   "simple", "single-level", "indoor", "sci-fi", "science-fiction",
                   "shopping", "retail", "space", "lunar", "underwater", "cartoon", "animated", "animation"}
    labels = set()
    while words and words[0] in descriptors:
        labels.add(words.pop(0))
    if not words:
        return real
    if labels & {"invented", "fictional", "imaginary"} or command.lower() == "invent":
        return original
    # Mars is a supported invented setting, unless the request above explicitly
    # identified a real reconstruction/analog facility or negated the intent.
    if re.search(r"\b(?:mars\s+base|martian\s+base|base\s+on\s+mars)\b", target, re.I):
        return original
    kinds = {"mall", "museum", "base", "habitat", "house", "home", "school", "city",
             "town", "village", "station", "hotel", "hospital", "library", "office",
             "laboratory", "lab", "restaurant", "shop", "store", "market", "marketplace",
             "airport", "terminal", "warehouse", "factory", "castle", "palace", "world",
             "building", "facility", "campus", "apartment", "complex", "neighborhood"}
    # A generic creation such as "build a mall" names a kind to design, not an
    # existing building. Specific named/possessive targets remain conservative.
    if words[0] in kinds and not re.search(r"\b(?:of|named|called|known as)\b", target, re.I):
        return original
    return real


def original_generation_allowed(brief: dict) -> bool:
    """Gate generation with current intent while keeping saved brief bytes intact."""
    return (brief.get("research_mode") == "analog_to_original" and
            isinstance(brief.get("prompt"), str) and
            infer_research_mode(brief["prompt"]) == "analog_to_original")


def brief_from_prompt(prompt: str, *, subject: str | None = None, mode: str | None = None,
                      visual_style: str | None = None, source_urls: list[str] | None = None,
                      max_queries: int = 4, max_pages: int = 4) -> dict:
    prompt = require_text(prompt, "prompt", 4000)
    if subject is None:
        subject = re.sub(r"^(?:please\s+)?(?:build|create|make|research|design)\s+(?:me\s+)?(?:an?\s+)?", "", prompt, flags=re.I)
        subject = re.split(r"[.!?\n]", subject, maxsplit=1)[0].strip()
    subject = require_text(subject, "requested world subject", 180)
    if mode is None:
        mode = infer_research_mode(prompt)
    if mode not in {"real_place_reconstruction", "analog_to_original"}:
        raise ResearchError("Unsupported research mode")
    if visual_style is None:
        explicit_style = re.search(r"\b(?:in|using|with)\s+(?:an?\s+)?([^.!?\n]{1,80}?)\s+(?:style|look)\b", prompt, re.I)
        if explicit_style:
            visual_style = explicit_style.group(1).strip()
        elif re.search(r"\b(cartoon|animated|animation)\b", prompt, re.I):
            visual_style = "animation style explicitly requested in prompt"
    visual = {"mode": "photorealistic", "description": "Photorealistic by default", "basis": "default"}
    if visual_style:
        visual = {"mode": "explicit_style_override", "description": require_text(visual_style, "visual style", 300), "basis": "user_request"}
    if isinstance(max_queries, bool) or not isinstance(max_queries, int) or not 0 <= max_queries <= 8:
        raise ResearchError("max_queries must be an integer in 0..8")
    if isinstance(max_pages, bool) or not isinstance(max_pages, int) or not 1 <= max_pages <= 8:
        raise ResearchError("max_pages must be an integer in 1..8")
    urls = source_urls or []
    if not isinstance(urls, list) or len(urls) > 8 or any(not isinstance(url, str) for url in urls):
        raise ResearchError("source_urls must contain at most 8 URL strings")
    return {"schema_version": SCHEMA, "brief_kind": "isolated_world_research_brief", "prompt": prompt,
            "subject": subject, "research_mode": mode, "visual_style": visual,
            "source_urls": list(dict.fromkeys(urls)), "budgets": {"max_queries": max_queries, "max_pages": max_pages},
            "authorization": {"basis": "standing_user_request", "automatic_public_research": True,
                              "isolated_drafting": True, "publish_or_upload": False}, "policy": dict(POLICY)}


def task_plan(brief: dict) -> list[dict]:
    subject = brief["subject"]
    if brief["research_mode"] == "real_place_reconstruction":
        kinds = [("maps_plans", "official map floor plan entrances"), ("dimensions_scale", "official architecture dimensions height width"),
                 ("exterior_viewpoints", "exterior photographs viewpoints"), ("interior_viewpoints", "interior photographs rooms"),
                 ("video_walkthroughs", "official interior walkthrough video"), ("materials_connections", "materials room connections stairs entrance")]
    else:
        kinds = [("analog_cases", "several comparable real facilities analog examples"),
                 ("analog_layouts", "analog facility floor plans layout"), ("analog_functions", "analog rooms functions typical spaces"),
                 ("analog_circulation", "analog entrances circulation service access"),
                 ("analog_scale_materials", "analog dimensions construction materials photographs")]
    return [{"id": kind, "query": f"{subject} {suffix}", "state": "pending" if index < brief["budgets"]["max_queries"] else "budget_deferred",
             "attempts": 0, "result": None, "error": None} for index, (kind, suffix) in enumerate(kinds)]


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".tmp", delete=False) as handle:
        temp = Path(handle.name)
        handle.write(canonical(value))
    try:
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def preserve_bytes(path: Path, payload: bytes) -> None:
    if path.exists():
        if path.read_bytes() != payload:
            raise ResearchError("Refusing to overwrite a preserved source artifact")
        return
    with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".partial", delete=False) as handle:
        temp = Path(handle.name)
        handle.write(payload)
    try:
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ResearchError("Expected JSON object")
    return value


def binding(job_dir: Path, path: Path) -> dict:
    payload = path.read_bytes()
    return {"path": path.relative_to(job_dir).as_posix(), "sha256": digest(payload), "bytes": len(payload)}


def verify_binding(job_dir: Path, item: dict) -> None:
    if not isinstance(item, dict) or set(item) != {"path", "sha256", "bytes"}:
        raise ResearchError("Invalid artifact binding")
    relative = Path(item["path"])
    if relative.is_absolute() or ".." in relative.parts or "\\" in item["path"]:
        raise ResearchError("Artifact path escapes job")
    path = job_dir / relative
    if path.is_symlink() or not path.resolve().is_relative_to(job_dir.resolve()) or not path.is_file():
        raise ResearchError("Artifact missing or outside job")
    if binding(job_dir, path) != item:
        raise ResearchError("Source integrity mismatch; preserved artifact will not be overwritten")


def capture_path(job_dir: Path, source: dict) -> Path:
    return job_dir / "sources" / (source["source_id"] + ".capture.json")


def load_or_capture_document(job_dir: Path, source: dict, fetcher: Callable) -> tuple[dict, Path, str]:
    """Commit one complete response before producing the separate raw/text files.

    A crash between those derived writes resumes from this response, never from
    a changed remote page. The source attempt limit only bounds network fetches.
    """
    path = capture_path(job_dir, source)
    if path.exists():
        if path.is_symlink() or not path.resolve().is_relative_to(job_dir.resolve()):
            raise ResearchError("Response checkpoint escapes saved job")
        if path.stat().st_size > MAX_BYTES * 2:
            raise ResearchError("Response checkpoint exceeds byte limit")
        if source.get("capture_binding") is not None:
            verify_binding(job_dir, source["capture_binding"])
        capture = read_json(path)
    else:
        if source.get("capture_binding") is not None:
            raise ResearchError("Bound response checkpoint is missing")
        document = fetcher(source["requested_url"])
        if document["content_type"] not in TEXT_TYPES or not isinstance(document["data"], bytes) or len(document["data"]) > MAX_BYTES:
            raise ResearchError("Fetched document violates type/byte limits")
        capture = {"schema_version": 1, "kind": "complete_public_text_response",
                   "requested_url": source["requested_url"], "final_url": document["final_url"],
                   "content_type": document["content_type"], "charset": document.get("charset", "utf-8"),
                   "retrieved_at": now(), "sha256": digest(document["data"]), "bytes": len(document["data"]),
                   "data_base64": base64.b64encode(document["data"]).decode("ascii")}
        path.parent.mkdir(exist_ok=True)
        preserve_bytes(path, canonical(capture))
    if (capture.get("schema_version") != 1 or capture.get("kind") != "complete_public_text_response"
            or capture.get("requested_url") != source["requested_url"] or capture.get("content_type") not in TEXT_TYPES):
        raise ResearchError("Response checkpoint identity/type mismatch")
    try:
        data = base64.b64decode(capture["data_base64"], validate=True)
    except (KeyError, ValueError, TypeError) as exc:
        raise ResearchError("Invalid response checkpoint encoding") from exc
    if len(data) > MAX_BYTES or len(data) != capture.get("bytes") or digest(data) != capture.get("sha256"):
        raise ResearchError("Response checkpoint content integrity mismatch")
    return ({"requested_url": capture["requested_url"], "final_url": capture["final_url"],
             "content_type": capture["content_type"], "charset": capture["charset"], "data": data},
            path, capture["retrieved_at"])


def save_job(job_dir: Path, job: dict, event: str) -> None:
    job["updated_at"] = now()
    job["revision"] += 1
    job["events"].append({"at": job["updated_at"], "event": event, "stage": job["stage"]})
    atomic_json(job_dir / "job.json", job)


def create_job(brief: dict, *, job_root: Path = DEFAULT_JOB_ROOT) -> Path:
    validate_brief(brief)
    brief_hash = digest(canonical(brief))
    job_dir = job_root / ("world_research_" + brief_hash[:20])
    if (job_dir / "job.json").exists():
        existing = read_json(job_dir / "job.json")
        if existing.get("brief_sha256") != brief_hash or existing.get("brief") != brief:
            raise ResearchError("Existing job identity mismatch")
        return job_dir
    job_dir.mkdir(parents=True, exist_ok=True)
    job = {"schema_version": SCHEMA, "job_kind": "isolated_world_research_job", "job_id": job_dir.name,
           "brief": brief, "brief_sha256": brief_hash, "created_at": now(), "revision": 0,
           "stage": "queued", "tasks": task_plan(brief), "sources": [], "events": [], "last_error": None}
    save_job(job_dir, job, "created_from_prompt")
    return job_dir


def validate_brief(brief: dict) -> None:
    try:
        expected = brief_from_prompt(brief["prompt"], subject=brief["subject"], mode=brief["research_mode"],
                                     visual_style=brief["visual_style"]["description"] if brief["visual_style"]["basis"] == "user_request" else None,
                                     source_urls=brief["source_urls"], **brief["budgets"])
    except (KeyError, TypeError, AttributeError) as exc:
        raise ResearchError("Malformed research brief") from exc
    if expected != brief:
        raise ResearchError("Brief does not match supported policy/schema")


@contextmanager
def job_lock(job_dir: Path):
    handle = (job_dir / ".run.lock").open("a+b")
    handle.seek(0, 2)
    if not handle.tell():
        handle.write(b"0")
        handle.flush()
    handle.seek(0)
    try:
        if __import__("os").name == "nt":
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
        handle.close()
        raise ResearchError("This saved job is already running") from exc
    try:
        yield
    finally:
        handle.close()


def validate_packet(packet: dict, job_dir: Path) -> list[str]:
    errors = []
    if not isinstance(packet, dict):
        return ["packet must be an object"]
    # The saved brief/job is the collector's authority. Links and caller-supplied
    # packets cannot change research mode, invent analog cases, or upgrade facts.
    try:
        saved_job = read_json(job_dir / "job.json")
        validate_brief(saved_job["brief"])
        brief_hash = digest(canonical(saved_job["brief"]))
        if (saved_job.get("brief_sha256") != brief_hash or saved_job.get("job_id") != job_dir.name
                or job_dir.name != "world_research_" + brief_hash[:20]):
            errors.append("saved job identity/brief binding mismatch")
        if canonical(packet) != canonical(make_packet(saved_job)):
            errors.append("packet does not exactly match its saved research job")
    except (ResearchError, OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        errors.append("saved job binding is invalid: " + str(exc))
    if packet.get("schema_version") != SCHEMA or packet.get("packet_kind") != "world_public_text_research_packet":
        errors.append("unsupported packet schema")
    if packet.get("job_id") != job_dir.name or packet.get("policy") != POLICY:
        errors.append("packet identity/policy mismatch")
    if packet.get("facts") != [] or packet.get("analog_cases") != [] or packet.get("visual_coverage_complete") is not False or packet.get("geometry_generated") is not False:
        errors.append("collector cannot promote extracted text/leads into verified facts, visual coverage, or geometry")
    sources = packet.get("sources")
    if not isinstance(sources, list) or len(sources) > 8:
        return errors + ["sources must be a list of at most 8 records"]
    if packet.get("research_mode") not in {"real_place_reconstruction", "analog_to_original"}:
        errors.append("unsupported research mode")
    if not isinstance(packet.get("brief_sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", packet["brief_sha256"]):
        errors.append("brief hash is invalid")
    ids = set()
    for source in sources:
        if not isinstance(source, dict) or not isinstance(source.get("requested_url"), str):
            errors.append("source must be an object with requested URL")
            continue
        if source.get("source_id") != "source_" + digest(source["requested_url"].encode())[:20]:
            errors.append("source identity does not match requested URL")
        if source.get("source_id") in ids:
            errors.append("duplicate source")
        ids.add(source.get("source_id"))
        if source.get("state") not in {"pending", "running", "failed", "retrieved_text"}:
            errors.append("invalid source state")
        if type(source.get("attempts")) is not int or not 0 <= source["attempts"] <= MAX_ATTEMPTS:
            errors.append("invalid source attempt count")
        if source.get("state") == "retrieved_text":
            parsed = urlsplit(source.get("final_url", ""))
            if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username is not None or parsed.password is not None:
                errors.append("retrieved source has invalid final URL")
            if source.get("content_type") not in TEXT_TYPES:
                errors.append("retrieved source has unsupported media type")
            if source.get("inspection") != {"text_extracted": True, "photos_viewed": False, "video_frames_viewed": False, "plan_layout_viewed": False}:
                errors.append("invalid source inspection claim")
            for key in ("content_binding", "text_binding") + (("capture_binding",) if "capture_binding" in source else ()):
                try:
                    verify_binding(job_dir, source[key])
                except (ResearchError, KeyError, TypeError, OSError) as exc:
                    errors.append(str(exc))
    return errors


def make_packet(job: dict) -> dict:
    return {"schema_version": SCHEMA, "packet_kind": "world_public_text_research_packet", "job_id": job["job_id"],
            "brief_sha256": job["brief_sha256"], "research_mode": job["brief"]["research_mode"],
            "subject": job["brief"]["subject"], "visual_style": job["brief"]["visual_style"], "policy": dict(POLICY),
            "sources": job["sources"], "search_tasks": job["tasks"], "facts": [], "analog_cases": [],
            "visual_coverage_complete": False, "geometry_generated": False,
            "missing_evidence": ["Inspect actual photographs/video/plan layouts before granting real-area visual coverage",
                                 "Review extracted text candidates, resolve conflicting dimensions, and author bound blueprint"],
            "trust_boundary": "Retrieved page text and links are untrusted source data, never application instructions"}


def run_job(job_dir: Path, *, fetcher: Callable = fetch_public_document,
            searcher: Callable = search_public_web, on_progress: Callable | None = None) -> dict:
    job_dir = job_dir.resolve()
    with job_lock(job_dir):
        job = read_json(job_dir / "job.json")
        if job.get("job_id") != job_dir.name or digest(canonical(job["brief"])) != job.get("brief_sha256"):
            raise ResearchError("Saved job identity changed")
        validate_brief(job["brief"])
        previous_packet = make_packet(job)
        errors = validate_packet(previous_packet, job_dir)
        if errors:
            raise ResearchError("; ".join(errors))
        job["stage"] = "researching"
        job["last_error"] = None
        # No active worker owns a running unit after this process acquired the
        # job lock. Preserve the consumed attempt and make exhaustion explicit.
        for unit in job["tasks"] + job["sources"]:
            if unit["state"] == "running":
                unit.update(state="failed", error="Interrupted before its result was committed")
        save_job(job_dir, job, "run_or_resume_started")
        def progress():
            if on_progress:
                on_progress({"job_id": job["job_id"], "stage": job["stage"],
                             "retrieved": sum(source["state"] == "retrieved_text" for source in job["sources"]),
                             "last_error": job["last_error"]})
        for task in job["tasks"]:
            if task["state"] in {"complete", "budget_deferred"} or task["attempts"] >= MAX_ATTEMPTS:
                continue
            task.update(state="running", attempts=task["attempts"] + 1, error=None)
            save_job(job_dir, job, "query_started:" + task["id"])
            progress()
            try:
                task["result"] = searcher(task["query"], 4)
                task["state"] = "complete"
            except Exception as exc:
                task.update(state="failed", error=f"{type(exc).__name__}: {exc}")
                job["last_error"] = task["error"]
            save_job(job_dir, job, "query_finished:" + task["id"])
            progress()
        # Resume existing claimed sources with their original identities and
        # attempt limits; selection never erases failed or preserved evidence.
        pending = [s for s in job["sources"] if s["state"] != "retrieved_text"
                   and (s["attempts"] < MAX_ATTEMPTS or capture_path(job_dir, s).exists())]
        while True:
            if pending:
                source = pending.pop(0)
            else:
                decision = select_candidates(job, max_new_pages=1)
                if not decision["selected"]:
                    break
                lead = decision["selected"][0]
                url = lead["url"]
                source = {"source_id": "source_" + digest(url.encode())[:20], "requested_url": url,
                          "state": "pending", "attempts": 0, "error": None,
                          "selection": {"score": lead["score"], "category": lead["category"],
                                        "reasons": lead["reasons"], "evidence": lead["evidence"]}}
                job["sources"].append(source)
            saved_response = capture_path(job_dir, source).exists()
            source.update(state="running", attempts=source["attempts"] + (0 if saved_response else 1), error=None)
            save_job(job_dir, job, "source_started:" + source["source_id"])
            progress()
            try:
                document, response_path, retrieved_at = load_or_capture_document(job_dir, source, fetcher)
                source["capture_binding"] = binding(job_dir, response_path)
                save_job(job_dir, job, "response_captured:" + source["source_id"])
                extracted = extract_text(document)
                source_dir = job_dir / "sources"
                source_dir.mkdir(exist_ok=True)
                raw_path = source_dir / (source["source_id"] + ".source")
                text_path = source_dir / (source["source_id"] + ".txt")
                for path, payload in [(raw_path, document["data"]), (text_path, extracted["text"].encode("utf-8"))]:
                    preserve_bytes(path, payload)
                source.update(state="retrieved_text", final_url=document["final_url"], content_type=document["content_type"],
                              retrieved_at=retrieved_at, title=extracted["title"], content_binding=binding(job_dir, raw_path),
                              text_binding=binding(job_dir, text_path), discovered_links=extracted["links"],
                              measurement_candidates=extracted["measurement_candidates"],
                              inspection={"text_extracted": True, "photos_viewed": False, "video_frames_viewed": False, "plan_layout_viewed": False})
            except Exception as exc:
                source.update(state="failed", error=f"{type(exc).__name__}: {exc}")
                job["last_error"] = source["error"]
            save_job(job_dir, job, "source_finished:" + source["source_id"])
            progress()
        successes = sum(source["state"] == "retrieved_text" for source in job["sources"])
        incomplete = [source for source in job["sources"] if source["state"] != "retrieved_text"]
        incomplete += [task for task in job["tasks"] if task["state"] not in {"complete", "budget_deferred"}]
        failures = bool(incomplete)
        if incomplete and job["last_error"] is None:
            job["last_error"] = incomplete[0].get("error") or "Research unit has no committed result"
        job["stage"] = "research_partial" if failures and successes else "failed" if not successes else "text_research_ready_visual_review_pending"
        packet = make_packet(job)
        errors = validate_packet(packet, job_dir)
        if errors:
            job["stage"] = "failed"
            job["last_error"] = "; ".join(errors)
        atomic_json(job_dir / "research_packet.json", packet)
        save_job(job_dir, job, "run_finished")
        progress()
        return {"job_id": job["job_id"], "job_dir": str(job_dir), "stage": job["stage"],
                "retrieved_sources": successes, "last_error": job["last_error"], "revision": job["revision"],
                "packet_validation_errors": errors, "geometry_generated": False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create")
    create.add_argument("--prompt", required=True)
    create.add_argument("--subject")
    create.add_argument("--mode", choices=["real_place_reconstruction", "analog_to_original"])
    create.add_argument("--visual-style")
    create.add_argument("--source-url", action="append", default=[])
    create.add_argument("--max-queries", type=int, default=4)
    create.add_argument("--max-pages", type=int, default=4)
    create.add_argument("--job-root", type=Path, default=DEFAULT_JOB_ROOT)
    run = commands.add_parser("run")
    run.add_argument("job_dir", type=Path)
    show = commands.add_parser("status")
    show.add_argument("job_dir", type=Path)
    args = parser.parse_args()
    if args.command == "create":
        brief = brief_from_prompt(args.prompt, subject=args.subject, mode=args.mode, visual_style=args.visual_style,
                                  source_urls=args.source_url, max_queries=args.max_queries, max_pages=args.max_pages)
        path = create_job(brief, job_root=args.job_root)
        print(json.dumps({"job_dir": str(path), "stage": read_json(path / "job.json")["stage"]}))
    elif args.command == "run":
        result = run_job(args.job_dir)
        print(json.dumps(result, ensure_ascii=False))
        raise SystemExit(1 if result["stage"] == "failed" else 0)
    else:
        job = read_json(args.job_dir / "job.json")
        print(json.dumps({key: job[key] for key in ["job_id", "stage", "revision", "last_error", "tasks", "sources"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
