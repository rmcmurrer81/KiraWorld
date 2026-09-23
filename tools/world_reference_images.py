"""Bounded, explicitly selected reference photographs with immutable provenance.

Downloading and decoding records technical evidence only. It never changes room
access, geometry, source research, resident worlds, or visual-review decisions.
The caller supplies a private draft cache, not a resident world directory.
"""
from __future__ import annotations

from datetime import datetime, timezone
from html import escape
from html.parser import HTMLParser
from io import BytesIO
import ipaddress
import json
from pathlib import Path
import re
import time
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import ProxyHandler, Request, build_opener
import warnings
import zlib

from PIL import Image, UnidentifiedImageError
import world_research as public

MAX_IMAGES = 2
MAX_IMAGE_BYTES = 4_000_000
MAX_PIXELS = 12_000_000
MAX_SIDE = 8192
MAX_LEADS = 512
IMAGE_TYPES = {"image/jpeg": ("JPEG", ".jpg"), "image/png": ("PNG", ".png"), "image/webp": ("WEBP", ".webp")}
PHOTO_SUFFIX = re.compile(r"\.(?:jpe?g|png|webp)$", re.I)
POLICY = {"visual_reviewed": False, "scale_verified": False,
          "full_room_coverage_verified": False, "real_rooms_unlocked": False,
          "geometry_generated": False, "resident_worlds_modified": False,
          "license_or_reuse_permission_inferred": False,
          "status": "downloaded_and_decoded_unreviewed_reference"}


class ReferenceError(ValueError):
    pass


def pin(path):
    path = Path(path).resolve()
    data = path.read_bytes()
    return {"path": str(path), "sha256": public.digest(data), "bytes": len(data)}


def verify_pin(value):
    actual = pin(value["path"])
    if actual != value:
        raise ReferenceError("Pinned input or cache artifact changed")
    return Path(value["path"])


def write_json(path, value, *, exclusive=False):
    with Path(path).open("xb" if exclusive else "wb") as stream:
        stream.write(public.canonical(value))


def lead_url(base, value):
    """Pure syntax filter; network destinations are DNS-pinned at fetch time."""
    if not isinstance(value, str) or not value.strip() or len(value) > 4096:
        return None
    value = value.strip()
    if any(ord(c) < 32 for c in value) or "\\" in value:
        return None
    try:
        p = urlsplit(urljoin(base, value))
        if p.scheme not in {"http", "https"} or not p.hostname or p.username is not None or p.password is not None:
            return None
        host = p.hostname.rstrip(".").lower()
        if host in {"localhost", "localhost.localdomain"} or host.endswith((".local", ".localhost", ".internal")):
            return None
        if (p.port or (443 if p.scheme == "https" else 80)) not in {80, 443}:
            return None
        try:
            if not ipaddress.ip_address(host).is_global:
                return None
        except ValueError:
            pass
        return urlunsplit((p.scheme, p.netloc, p.path or "/", p.query, ""))
    except ValueError:
        return None


def srcset_items(value):
    """Conservative common srcset subset; data URLs and malformed entries drop."""
    # URL tokens may contain commas (notably data URLs). Never reinterpret the
    # payload following a data URL's comma as a relative HTTP image.
    offset, count = 0, 0
    while offset < len(value) and count < MAX_LEADS:
        while offset < len(value) and (value[offset].isspace() or value[offset] == ","):
            offset += 1
        match = re.match(r"[^\s]+", value[offset:])
        if not match:
            break
        raw = match.group(0)
        offset += len(raw)
        if raw.endswith(","):
            url, descriptor = raw.rstrip(","), ""
        else:
            end = value.find(",", offset)
            if end < 0:
                end = len(value)
            url, descriptor = raw, value[offset:end].strip()
            offset = end + 1
        count += 1
        if not descriptor or re.fullmatch(r"(?:[1-9]\d*w|(?:\d+(?:\.\d+)?|\.\d+)x)", descriptor):
            yield url, descriptor


class PhotoParser(HTMLParser):
    def __init__(self, base):
        super().__init__(convert_charrefs=True)
        self.base, self.leads, self.title_parts = base, [], []
        self.suppressed = 0
        self.picture_depth = 0
        self.in_title = False
        self.ordinal = 0
        self.truncated = False

    def add(self, tag, attribute, raw, alt="", descriptor=""):
        absolute = lead_url(self.base, raw)
        if not absolute:
            return
        if len(self.leads) >= MAX_LEADS:
            self.truncated = True
            return
        line, column = self.getpos()
        self.leads.append({"url": absolute, "alt": alt[:300], "descriptor": descriptor,
                           "locator": {"kind": "html_element", "line": line, "column": column,
                                       "element_ordinal": self.ordinal, "tag": tag, "attribute": attribute},
                           "inspection_status": "uninspected_photo_lead"})

    def handle_starttag(self, tag, attrs):
        self.ordinal += 1
        a = dict(attrs)
        if tag in {"script", "style", "template", "noscript"}:
            self.suppressed += 1
        if self.suppressed:
            return
        if tag == "title":
            self.in_title = True
        if tag == "picture":
            self.picture_depth += 1
        if tag == "img":
            if a.get("src"):
                self.add(tag, "src", a["src"], a.get("alt") or "")
            for attr in ("srcset",):
                for url, descriptor in srcset_items(a.get(attr) or ""):
                    self.add(tag, attr, url, a.get("alt") or "", descriptor)
        if tag == "source" and self.picture_depth and (not a.get("type") or a["type"].lower() in IMAGE_TYPES):
            for url, descriptor in srcset_items(a.get("srcset") or ""):
                self.add(tag, "srcset", url, descriptor=descriptor)
        if tag == "a" and a.get("href"):
            url = lead_url(self.base, a["href"])
            if url and PHOTO_SUFFIX.search(urlsplit(url).path):
                self.add(tag, "href", a["href"], a.get("title") or "")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "template", "noscript"}:
            self.suppressed = max(0, self.suppressed - 1)
            return
        if self.suppressed:
            return
        if tag == "picture":
            self.picture_depth = max(0, self.picture_depth - 1)
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title and not self.suppressed:
            self.title_parts.append(data)


def extract_photo_leads(document):
    if document["content_type"] not in {"text/html", "application/xhtml+xml"}:
        raise ReferenceError("Photograph discovery requires captured HTML")
    if len(document["data"]) > public.MAX_BYTES:
        raise ReferenceError("Parent HTML exceeds byte budget")
    if not lead_url(document["final_url"], document["final_url"]):
        raise ReferenceError("Invalid captured parent URL")
    try:
        text = document["data"].decode(document.get("charset", "utf-8"), errors="replace")
    except LookupError:
        text = document["data"].decode("utf-8", errors="replace")
    parser = PhotoParser(document["final_url"])
    parser.feed(text)
    parser.close()
    return {"title": re.sub(r"\s+", " ", " ".join(parser.title_parts)).strip()[:300],
            "leads": parser.leads, "truncated": parser.truncated,
            "discovery_is_visual_review": False}


def save_page_capture(destination, document):
    """Save returned original page bytes and parsed observations; never overwrite."""
    directory = Path(destination).resolve()
    directory.mkdir(parents=True, exist_ok=False)
    extracted = extract_photo_leads(document)
    encoded = document.get("encoded_data", document["data"])
    encoding = document.get("content_encoding", "identity")
    if decode_html_body(encoded, encoding) != document["data"]:
        raise ReferenceError("Encoded parent response does not match decoded HTML")
    (directory / "response.body").write_bytes(encoded)
    (directory / "source.html").write_bytes(document["data"])
    write_json(directory / "leads.json", extracted, exclusive=True)
    record = {"schema": 1, "captured_at": public.now(),
              "requested_url": document["requested_url"], "final_url": document["final_url"],
              "content_type": document["content_type"], "charset": document.get("charset", "utf-8"),
              "content_encoding": encoding, "encoded_response": pin(directory / "response.body"),
              "html": pin(directory / "source.html"), "leads": pin(directory / "leads.json"),
              "response_headers": document.get("response_headers", {}),
              "title": extracted["title"], "capture_kind": "bounded_public_html_fetch"}
    write_json(directory / "page.json", record, exclusive=True)
    return directory / "page.json"


def load_page_capture(page_path):
    page_pin = pin(page_path)
    page = json.loads(Path(page_path).read_text(encoding="utf-8"))
    html_path = verify_pin(page["html"])
    encoded_path = verify_pin(page["encoded_response"])
    if decode_html_body(encoded_path.read_bytes(), page["content_encoding"]) != html_path.read_bytes():
        raise ReferenceError("Encoded response and decoded HTML no longer match")
    verify_pin(page["leads"])
    document = {**page, "data": html_path.read_bytes()}
    extracted = extract_photo_leads(document)
    if public.canonical(extracted) != Path(page["leads"]["path"]).read_bytes():
        raise ReferenceError("Page lead evidence does not match captured HTML")
    return page_pin, page, extracted


def decode_html_body(encoded, encoding):
    """Bound BOTH encoded bytes and expansion, including gzip/deflate bombs."""
    if len(encoded) > public.MAX_BYTES:
        raise ReferenceError("Encoded HTML exceeds byte budget")
    if encoding in {"", "identity"}:
        return encoded
    if encoding not in {"gzip", "deflate"}:
        raise ReferenceError(f"Unsupported HTML content encoding: {encoding}")
    try:
        decoder = zlib.decompressobj(31 if encoding == "gzip" else 15)
        decoded = decoder.decompress(encoded, public.MAX_BYTES + 1)
        if len(decoded) > public.MAX_BYTES or decoder.unconsumed_tail:
            raise ReferenceError("Decoded HTML exceeds byte budget")
        if not decoder.eof or decoder.unused_data:
            raise ReferenceError("Truncated or concatenated compressed HTML is unsupported")
        return decoded
    except zlib.error as exc:
        raise ReferenceError("Invalid compressed HTML") from exc


def fetch_public_html(url):
    """Pinned public page capture; retain bounded wire body and decoded HTML."""
    safe = public.public_url(url)
    opener = build_opener(ProxyHandler({}), public.PublicRedirects(),
                         public.PinnedHTTPHandler(), public.PinnedHTTPSHandler())
    request = Request(safe, headers={"User-Agent": "KiraWorldReferenceCandidate/1.0 (public source research)",
                                    "Accept": "text/html,application/xhtml+xml", "Accept-Encoding": "identity"})
    started = time.monotonic()
    with opener.open(request, timeout=public.TIMEOUT) as response:
        final_url = public.public_url(response.geturl())
        mime = response.headers.get_content_type().lower()
        if mime not in {"text/html", "application/xhtml+xml"}:
            raise ReferenceError(f"Parent page is not HTML: {mime}")
        encoding = response.headers.get("Content-Encoding", "identity").strip().lower()
        if encoding not in {"", "identity", "gzip", "deflate"}:
            raise ReferenceError(f"Unsupported HTML content encoding: {encoding}")
        length = response.headers.get("Content-Length")
        if length and (not length.isdigit() or int(length) > public.MAX_BYTES):
            raise ReferenceError("Invalid or excessive parent Content-Length")
        chunks, total = [], 0
        while True:
            if time.monotonic() - started > public.TIMEOUT * 2:
                raise ReferenceError("Parent exceeded overall read deadline")
            chunk = response.read1(min(65536, public.MAX_BYTES + 1 - total))
            if not chunk:
                break
            total += len(chunk)
            if total > public.MAX_BYTES:
                raise ReferenceError("Encoded parent exceeded byte budget")
            chunks.append(chunk)
        encoded = b"".join(chunks)
        if length and len(encoded) != int(length):
            raise ReferenceError("Incomplete parent HTTP body")
        return {"requested_url": safe, "final_url": final_url, "content_type": mime,
                "content_encoding": encoding, "encoded_data": encoded, "data": decode_html_body(encoded, encoding),
                "charset": response.headers.get_content_charset() or "utf-8",
                "response_headers": {key: response.headers[key] for key in
                                     ("Content-Type", "Content-Encoding", "Content-Length", "ETag", "Last-Modified")
                                     if response.headers.get(key) is not None}}


def fetch_public_image(url):
    """Reuse reviewed public DNS/socket/TLS/redirect guards, without proxies."""
    safe = public.public_url(url)
    opener = build_opener(ProxyHandler({}), public.PublicRedirects(),
                         public.PinnedHTTPHandler(), public.PinnedHTTPSHandler())
    request = Request(safe, headers={"User-Agent": "KiraWorldReferenceCandidate/1.0 (public source research)",
                                    "Accept": ",".join(IMAGE_TYPES), "Accept-Encoding": "identity"})
    started = time.monotonic()
    with opener.open(request, timeout=public.TIMEOUT) as response:
        final_url = public.public_url(response.geturl())
        mime = response.headers.get_content_type().lower()
        if mime not in IMAGE_TYPES:
            raise ReferenceError(f"Unsupported reference MIME: {mime}")
        if response.headers.get("Content-Encoding", "identity").strip().lower() not in {"", "identity"}:
            raise ReferenceError("Compressed HTTP response is unsupported")
        length = response.headers.get("Content-Length")
        if length and (not length.isdigit() or int(length) > MAX_IMAGE_BYTES):
            raise ReferenceError("Invalid or excessive image Content-Length")
        chunks, total = [], 0
        while True:
            if time.monotonic() - started > public.TIMEOUT * 2:
                raise ReferenceError("Image exceeded overall read deadline")
            chunk = response.read1(min(65536, MAX_IMAGE_BYTES + 1 - total))
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_IMAGE_BYTES:
                raise ReferenceError("Image exceeded byte budget")
            chunks.append(chunk)
        return {"requested_url": safe, "final_url": final_url, "content_type": mime,
                "data": b"".join(chunks), "captured_at": public.now(),
                "response_headers": {key: response.headers[key] for key in
                                     ("Content-Type", "Content-Length", "ETag", "Last-Modified")
                                     if response.headers.get(key) is not None}}


def decode_metadata(data, mime):
    if not data or len(data) > MAX_IMAGE_BYTES:
        raise ReferenceError("Empty or excessive image bytes")
    if mime not in IMAGE_TYPES:
        raise ReferenceError("Unsupported image MIME")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as im:
                width, height = im.size
                if min(width, height) <= 0 or max(width, height) > MAX_SIDE or width * height > MAX_PIXELS:
                    raise ReferenceError("Image dimensions exceed decode budget")
                if im.format != IMAGE_TYPES[mime][0]:
                    raise ReferenceError("Declared MIME does not match decoded image format")
                if getattr(im, "n_frames", 1) != 1:
                    raise ReferenceError("Animated or multiple-frame images are unsupported")
                metadata = {"width": width, "height": height, "format": im.format,
                            "mode": im.mode, "frames": 1, "pixels": width * height}
                im.verify()
            with Image.open(BytesIO(data)) as im:
                im.load()
        return metadata
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError, Image.DecompressionBombError,
            Image.DecompressionBombWarning) as exc:
        if isinstance(exc, ReferenceError):
            raise
        raise ReferenceError(f"Reference image did not decode safely: {type(exc).__name__}") from exc


def toolchain():
    import adaptive_source_selection
    return {"reference_collector": pin(__file__), "public_fetch_collector": pin(public.__file__),
            "public_fetch_selector": pin(adaptive_source_selection.__file__),
            "pillow_version": Image.__version__}


def gallery_html(page, items):
    cards = []
    for item in items:
        url = escape(item["requested_url"], quote=True)
        source = escape(page["final_url"], quote=True)
        name = escape(Path(item["original"]["path"]).name, quote=True)
        dimensions = item["decoded"]
        cards.append(f'<article><img src="assets/{name}" alt="Unreviewed reference photograph">'
                     f'<p>{dimensions["width"]} × {dimensions["height"]} · {escape(item["content_type"])} · '
                     f'{item["original"]["bytes"]:,} original bytes</p><p><a href="{url}">Photograph source</a> · '
                     f'<a href="{source}">Parent engineering page</a></p>'
                     f'<p class="hash">SHA-256 {item["original"]["sha256"]}</p></article>')
    return ('<!doctype html><html lang="en"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; img-src \'self\'; style-src \'unsafe-inline\'; base-uri \'none\'">'
            '<title>World Builder — reference evidence</title><style>'
            'body{max-width:1120px;margin:36px auto;padding:0 24px;background:#131820;color:#e6edf5;font:16px system-ui;line-height:1.5}'
            'h1{font-size:30px}article{margin:28px 0;padding:20px;background:#202936;border-radius:12px}'
            'img{display:block;max-width:100%;max-height:740px;margin:auto;object-fit:contain}a{color:#8fc9ff}.hash{overflow-wrap:anywhere;font:12px monospace}'
            '.notice{padding:16px;border-left:4px solid #dbaa61;background:#2c2925}</style>'
            '<h1>Reference evidence · collection prototype</h1><p>' + escape(page["title"]) + '</p>'
            '<p class="notice">Original public photograph bytes. Downloaded and technically decoded; visual review is separate. '
            'No scale, complete room coverage, current conditions, or reuse permission is established. No room is unlocked and no world geometry is created.</p>'
            + ''.join(cards) + '</html>').encode("utf-8")


def collect_selected(page_path, selected_urls, cache_root, *, fetcher=fetch_public_image):
    """At most two exact observed URLs. One durable operation; no automatic retry.

    A completed operation is reusable after every pin is verified. A failed or
    interrupted operation holds. A diagnosed, bounded retry creates a recorded
    successor cache and preserves the predecessor; it never silently replays.
    Tests can inject a fake fetcher; production uses the guarded public fetcher.
    """
    if not isinstance(selected_urls, list) or not 1 <= len(selected_urls) <= MAX_IMAGES:
        raise ReferenceError("Select one or two exact photograph URLs")
    page_pin, page, extracted = load_page_capture(page_path)
    selected = [lead_url(page["final_url"], u) for u in selected_urls]
    if any(u is None for u in selected) or len(set(selected)) != len(selected):
        raise ReferenceError("Invalid or duplicate selected photograph URL")
    provenance = {url: [lead for lead in extracted["leads"] if lead["url"] == url] for url in selected}
    if any(not leads for leads in provenance.values()):
        raise ReferenceError("Every selected URL must appear in the exact captured parent HTML")
    plan = {"schema": 1, "page": page_pin, "selected_urls": selected, "toolchain": toolchain(),
            "limits": {"images": MAX_IMAGES, "bytes_per_image": MAX_IMAGE_BYTES,
                       "pixels_per_image": MAX_PIXELS, "max_side": MAX_SIDE}, "policy": POLICY}
    operation_id = public.digest(public.canonical(plan))[:24]
    directory = Path(cache_root).resolve() / ("references-" + operation_id)
    directory.parent.mkdir(parents=True, exist_ok=True)
    if directory.exists():
        if not (directory / "manifest.json").is_file():
            raise ReferenceError("Collection initialization interrupted; no automatic redispatch")
        return verify_collection(directory / "manifest.json", expected_plan=plan)
    directory.mkdir(exist_ok=False)
    (directory / "assets").mkdir()
    write_json(directory / "plan.json", plan, exclusive=True)
    manifest_path = directory / "manifest.json"
    manifest = {"schema": 1, "created_at": public.now(), "status": "running", "plan": pin(directory / "plan.json"),
                "page": page_pin, "attempts": [], "images": [], "policy": POLICY,
                "mutations": "new private draft cache artifacts only"}
    write_json(manifest_path, manifest, exclusive=True)
    for url in selected:
        attempt = {"requested_url": url, "status": "fetch_claimed", "claimed_at": public.now()}
        manifest["attempts"].append(attempt)
        write_json(manifest_path, manifest)
        try:
            response = fetcher(url)
            if response["requested_url"] != url or not lead_url(response["final_url"], response["final_url"]):
                raise ReferenceError("Fetched response does not match the selected public URL")
            decoded = decode_metadata(response["data"], response["content_type"])
            suffix = IMAGE_TYPES[response["content_type"]][1]
            original = directory / "assets" / (public.digest(response["data"]) + suffix)
            if not original.exists():
                with original.open("xb") as stream:
                    stream.write(response["data"])
            item = {key: value for key, value in response.items() if key != "data"}
            item.update({"original": pin(original), "decoded": decoded, "parent_page": page_pin,
                         "parent_url": page["final_url"], "parent_html_sha256": page["html"]["sha256"],
                         "html_occurrences": provenance[url], "policy": POLICY})
            manifest["images"].append(item)
            attempt.update({"status": "downloaded_decoded", "completed_at": public.now(), "original": pin(original)})
            write_json(manifest_path, manifest)
        except Exception as exc:
            attempt.update({"status": "failed_no_auto_retry", "error": f"{type(exc).__name__}: {exc}"[:1500]})
            manifest["status"] = "failed_no_auto_retry"
            write_json(manifest_path, manifest)
            raise
    (directory / "index.html").write_bytes(gallery_html(page, manifest["images"]))
    manifest.update({"status": "complete", "completed_at": public.now(), "gallery": pin(directory / "index.html")})
    write_json(manifest_path, manifest)
    return verify_collection(manifest_path, expected_plan=plan)


def verify_collection(manifest_path, *, expected_plan=None):
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    if manifest["status"] != "complete":
        raise ReferenceError("Collection is failed or interrupted; no automatic redispatch")
    plan = json.loads(verify_pin(manifest["plan"]).read_text(encoding="utf-8"))
    if expected_plan is not None and plan != expected_plan:
        raise ReferenceError("Existing operation has a different plan")
    page_pin, page, extracted = load_page_capture(verify_pin(manifest["page"]))
    if plan["page"] != page_pin or manifest["policy"] != POLICY or plan["policy"] != POLICY:
        raise ReferenceError("Provenance or policy binding changed")
    for key in ("reference_collector", "public_fetch_collector", "public_fetch_selector"):
        verify_pin(plan["toolchain"][key])
    if not 1 <= len(plan["selected_urls"]) <= MAX_IMAGES or len(manifest["attempts"]) != len(plan["selected_urls"]) or len(manifest["images"]) != len(plan["selected_urls"]):
        raise ReferenceError("Invalid selected image count")
    for url, attempt, item in zip(plan["selected_urls"], manifest["attempts"], manifest["images"]):
        occurrences = [lead for lead in extracted["leads"] if lead["url"] == url]
        if not occurrences or item["html_occurrences"] != occurrences or item["parent_page"] != page_pin or item["parent_url"] != page["final_url"] or item["parent_html_sha256"] != page["html"]["sha256"]:
            raise ReferenceError("Image page provenance changed")
        if attempt["status"] != "downloaded_decoded" or attempt["requested_url"] != url or item["requested_url"] != url or attempt["original"] != item["original"] or item["policy"] != POLICY:
            raise ReferenceError("Image attempt binding changed")
        if lead_url(item["final_url"], item["final_url"]) != item["final_url"]:
            raise ReferenceError("Invalid final public image URL")
        expected_name = item["original"]["sha256"] + IMAGE_TYPES[item["content_type"]][1]
        expected_original = Path(manifest_path).resolve().parent / "assets" / expected_name
        if Path(item["original"]["path"]).resolve() != expected_original:
            raise ReferenceError("Original is not the bound hash-addressed cache file")
        if decode_metadata(verify_pin(item["original"]).read_bytes(), item["content_type"]) != item["decoded"]:
            raise ReferenceError("Image decode metadata changed")
    gallery = verify_pin(manifest["gallery"])
    if gallery.read_bytes() != gallery_html(page, manifest["images"]):
        raise ReferenceError("Gallery does not match provenance")
    return {"status": "complete", "manifest": pin(manifest_path), "gallery": manifest["gallery"],
            "images": manifest["images"], "network_calls_this_verification": 0, "policy": POLICY}
