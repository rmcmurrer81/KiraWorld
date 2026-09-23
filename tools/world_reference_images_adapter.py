"""Native picker interface: cached page inventory and explicit photo collection.

No UI or model dependency. Saved research is read-only; only the caller's private
reference cache receives new artifacts. The native workspace can call inventory
on its selected job, show the returned photo leads, and call collect with one or
two selected URLs in its worker thread. Downloading does not mark them reviewed.
"""
import json
from contextlib import contextmanager, ExitStack
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import ttk
from urllib.parse import urlsplit

import world_research as public
import world_reference_images as refs


def saved_inventory(job_dir):
    job_dir = Path(job_dir).resolve()
    packet_path = job_dir / "research_packet.json"
    packet = public.read_json(packet_path)
    errors = public.validate_packet(packet, job_dir)
    if errors:
        raise refs.ReferenceError("Saved research failed validation: " + "; ".join(errors))
    pages = []
    for source in packet["sources"]:
        if source["state"] != "retrieved_text" or source["content_type"] not in {"text/html", "application/xhtml+xml"}:
            continue
        raw_path = job_dir / source["content_binding"]["path"]
        if raw_path.stat().st_size > public.MAX_BYTES:
            raise refs.ReferenceError("Saved parent HTML exceeds byte budget")
        document = {"requested_url": source["requested_url"], "final_url": source["final_url"],
                    "content_type": source["content_type"], "charset": "utf-8", "data": raw_path.read_bytes()}
        capture = source.get("capture_binding")
        if capture:
            checkpoint = public.read_json(job_dir / capture["path"])
            document["charset"] = checkpoint.get("charset", "utf-8")
        discovered = refs.extract_photo_leads(document)
        pages.append({"source_id": source["source_id"], "requested_url": source["requested_url"],
                      "final_url": source["final_url"], "title": source["title"],
                      "source_retrieved_at": source["retrieved_at"], "document": {k: v for k, v in document.items() if k != "data"},
                      "source_bindings": {name: refs.pin(job_dir / source[name]["path"])
                                          for name in ("content_binding", "text_binding", "capture_binding") if name in source},
                      **discovered})
    return {"job_dir": str(job_dir), "research_packet": refs.pin(packet_path), "pages": pages,
            "public_fetches": 0, "policy": refs.POLICY, "adapter": refs.pin(__file__)}


def verify_inventory(inventory):
    refs.verify_pin(inventory["research_packet"])
    refs.verify_pin(inventory["adapter"])
    for page in inventory["pages"]:
        for binding in page["source_bindings"].values():
            refs.verify_pin(binding)
    if saved_inventory(inventory["job_dir"]) != inventory:
        raise refs.ReferenceError("Saved source or picker inventory changed; refresh the selection")


@contextmanager
def source_collection_lane(inventory, source_id, cache_root):
    """A live worker owns this source even if its view has been closed.

    The existing process lock releases on completion/crash. Thus an incomplete
    CPU import can be recovered later, without treating a live import as dead.
    """
    verify_inventory(inventory)
    key = public.digest(public.canonical({"packet": inventory["research_packet"], "source_id": source_id}))[:24]
    lane = Path(cache_root).resolve() / ".collection-lanes" / key
    lane.mkdir(parents=True, exist_ok=True)
    with ExitStack() as stack:
        try:
            stack.enter_context(public.job_lock(lane))
        except public.ResearchError as exc:
            raise refs.ReferenceError("Reference photographs from this saved source are already being collected. Reopen the cached gallery when that worker finishes.") from exc
        yield


def collect_saved_selection(inventory, source_id, selected_urls, cache_root, *, fetcher=refs.fetch_public_image, on_progress=None):
    with source_collection_lane(inventory, source_id, cache_root):
        return _collect_saved_selection(inventory, source_id, selected_urls, cache_root, fetcher=fetcher, on_progress=on_progress)


def _collect_saved_selection(inventory, source_id, selected_urls, cache_root, *, fetcher=refs.fetch_public_image, on_progress=None):
    """Collect only explicit selection from one bound saved page; never refetch it."""
    verify_inventory(inventory)
    pages = [page for page in inventory["pages"] if page["source_id"] == source_id]
    if len(pages) != 1:
        raise refs.ReferenceError("Select one source from the current photo inventory")
    page = pages[0]
    known = {lead["url"] for lead in page["leads"]}
    if not isinstance(selected_urls, list) or not 1 <= len(selected_urls) <= refs.MAX_IMAGES or len(set(selected_urls)) != len(selected_urls) or any(url not in known for url in selected_urls):
        raise refs.ReferenceError("Select one or two exact photo URLs from this saved source")
    root = Path(cache_root).resolve()
    # Import is immutable and source-addressed; later research revisions retain
    # the old copy and get a different binding. No research job file is changed.
    key = public.digest(public.canonical({"packet": inventory["research_packet"], "page": page}))[:24]
    upstream = {"kind": "import_of_preserved_research_html_no_page_refetch", "research_packet": inventory["research_packet"],
                "source": page, "policy": refs.POLICY}
    predecessors = []
    for revision in range(64):
        folder = root / "saved-pages" / (key + ("-r" + str(revision) if revision else ""))
        page_path = folder / "page.json"
        provenance_path = folder / "saved-source-provenance.json"
        if not folder.exists():
            document = {**page["document"], "data": Path(page["source_bindings"]["content_binding"]["path"]).read_bytes()}
            refs.save_page_capture(folder, document)
            refs.write_json(provenance_path, {"upstream": upstream, "page": refs.pin(page_path),
                                             "preserved_incomplete_cpu_imports": predecessors}, exclusive=True)
            break
        try:
            provenance = public.read_json(provenance_path)
            if not page_path.is_file():
                raise FileNotFoundError(page_path)
        except (FileNotFoundError, json.JSONDecodeError):
            # The import has not committed a usable receipt. Recovery is CPU
            # only and may append a new immutable import revision, but never
            # discard an already-created collection's network attempt history.
            for plan_path in (root / "collections").glob("*/plan.json"):
                try:
                    plan = public.read_json(plan_path)
                    planned_page = Path(plan["page"]["path"]).resolve()
                except (OSError, KeyError, ValueError, TypeError) as exc:
                    raise refs.ReferenceError("Existing collection plan is uncertain; no automatic image replay") from exc
                if planned_page == page_path:
                    raise refs.ReferenceError("Incomplete import has prior image collection history; no automatic replay")
            predecessors.append({"directory": str(folder), "files": [refs.pin(p) for p in sorted(folder.iterdir()) if p.is_file()]})
            continue
        if provenance["upstream"] != upstream:
            raise refs.ReferenceError("Imported source provenance changed")
        refs.verify_pin(provenance["page"])
        refs.load_page_capture(page_path)
        break
    else:
        raise refs.ReferenceError("CPU import revision budget exhausted")
    def bounded_fetch(url):
        verify_inventory(inventory)
        if on_progress:
            on_progress({"stage": "reference_image_fetch", "message": "Collecting selected reference photograph", "url": url})
        return fetcher(url)
    result = refs.collect_selected(page_path, selected_urls, root / "collections", fetcher=bounded_fetch)
    verify_inventory(inventory)
    result["saved_source_provenance"] = refs.pin(provenance_path)
    if on_progress:
        on_progress({"stage": "reference_images_ready", "message": "Selected photographs are cached; visual review is separate", "gallery": result["gallery"]})
    return result


def latest_pointer(job_dir, cache_root):
    # Use a digest instead of accepting a caller-controlled filename.
    key = public.digest(str(Path(job_dir).resolve()).encode())[:24]
    return Path(cache_root).resolve() / "latest" / (key + ".json")


def collect_and_remember(inventory, source_id, selected_urls, cache_root, *, fetcher=refs.fetch_public_image, on_progress=None):
    with source_collection_lane(inventory, source_id, cache_root):
        result = _collect_saved_selection(inventory, source_id, selected_urls, cache_root, fetcher=fetcher, on_progress=on_progress)
        pointer = {"job_dir": inventory["job_dir"], "research_packet": inventory["research_packet"],
                   "manifest": result["manifest"], "saved_source_provenance": result["saved_source_provenance"],
                   "policy": refs.POLICY}
        public.atomic_json(latest_pointer(inventory["job_dir"], cache_root), pointer)
        return result


def load_latest_collection(job_dir, cache_root):
    path = latest_pointer(job_dir, cache_root)
    if not path.is_file():
        return None
    pointer = public.read_json(path)
    if pointer["job_dir"] != str(Path(job_dir).resolve()) or pointer["policy"] != refs.POLICY:
        raise refs.ReferenceError("Saved collection pointer changed")
    refs.verify_pin(pointer["research_packet"])
    provenance = public.read_json(refs.verify_pin(pointer["saved_source_provenance"]))
    if provenance["upstream"]["research_packet"] != pointer["research_packet"]:
        raise refs.ReferenceError("Saved collection research binding changed")
    for binding in provenance["upstream"]["source"]["source_bindings"].values():
        refs.verify_pin(binding)
    manifest = refs.verify_pin(pointer["manifest"])
    result = refs.verify_collection(manifest)
    manifest_record = public.read_json(manifest)
    if manifest_record["page"] != provenance["page"]:
        raise refs.ReferenceError("Saved collection parent page changed")
    result["saved_source_provenance"] = pointer["saved_source_provenance"]
    return result


class ReferencePhotosView(tk.Toplevel):
    """Explicit native source/URL picker. All network work stays off the UI thread."""
    def __init__(self, owner, job_dir, cache_root, *, open_gallery, fetcher=refs.fetch_public_image):
        inventory = saved_inventory(job_dir)
        super().__init__(owner)
        self.title("World Builder — Reference Photos")
        self.geometry("1000x660")
        self.minsize(720, 450)
        self.inventory, self.job_dir, self.cache_root = inventory, Path(job_dir), Path(cache_root)
        self.open_gallery, self.fetcher = open_gallery, fetcher
        self.messages, self.worker, self.result = queue.Queue(), None, None
        self.configure(bg="#06111d")
        frame = ttk.Frame(self, padding=16)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Reference Photos", style="Header.TLabel").pack(anchor="w")
        ttk.Label(frame, text="Choose up to two photographs from one saved source page.").pack(anchor="w", pady=(4, 2))
        ttk.Label(frame, text="Collecting preserves original image bytes. Visual review, scale and room coverage remain separate.", wraplength=930).pack(anchor="w")
        ttk.Label(frame, text=f"Saved job: {self.job_dir.name}", wraplength=930).pack(anchor="w", pady=(8, 8))
        self.pages = inventory["pages"]
        self.page_choice = ttk.Combobox(frame, state="readonly", values=[p["title"] or p["final_url"] for p in self.pages])
        self.page_choice.pack(fill="x")
        self.page_choice.bind("<<ComboboxSelected>>", lambda _: self._show_page())
        self.page_url = tk.StringVar()
        ttk.Label(frame, textvariable=self.page_url, wraplength=930).pack(anchor="w", pady=(5, 8))
        list_frame = ttk.Frame(frame)
        list_frame.pack(fill="both", expand=True)
        self.lead_list = tk.Listbox(list_frame, selectmode="extended", exportselection=False, bg="#071827", fg="#d7ecff",
                                   selectbackground="#174d79", selectforeground="#ffffff", font=("Segoe UI", 10))
        vertical = ttk.Scrollbar(list_frame, orient="vertical", command=self.lead_list.yview)
        horizontal = ttk.Scrollbar(list_frame, orient="horizontal", command=self.lead_list.xview)
        self.lead_list.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.lead_list.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)
        self.lead_list.bind("<<ListboxSelect>>", lambda _: self._selection_changed())
        ttk.Label(frame, text="Use Ctrl-click to select two. Saved pages are not fetched again.").pack(anchor="w", pady=(6, 8))
        buttons = ttk.Frame(frame)
        buttons.pack(fill="x")
        self.collect_button = ttk.Button(buttons, text="Collect selected photos", command=self._collect, state="disabled")
        self.collect_button.pack(side="left")
        self.gallery_button = ttk.Button(buttons, text="Open cached gallery", command=self._open_gallery, state="disabled")
        self.gallery_button.pack(side="left", padx=8)
        ttk.Button(buttons, text="Close", command=self.destroy).pack(side="right")
        self.status = tk.StringVar(value="No saved HTML pages with photograph leads. Research a source page first.")
        ttk.Label(frame, textvariable=self.status, wraplength=930).pack(anchor="w", pady=(12, 0))
        if self.pages:
            self.page_choice.current(0)
            self._show_page()
        try:
            self.result = load_latest_collection(self.job_dir, self.cache_root)
            if self.result:
                self.gallery_button.configure(state="normal")
                self.status.set("Saved photographs are ready. Open the cached gallery; no new download is needed.")
        except Exception as exc:
            self.status.set(f"Saved gallery is held: {exc}")

    def _show_page(self):
        if self.worker is not None:
            return
        page = self.pages[self.page_choice.current()]
        self.page_url.set(page["final_url"])
        self.leads = list(dict.fromkeys(lead["url"] for lead in page["leads"]
                                      if Path(urlsplit(lead["url"]).path).suffix.lower() not in {".svg", ".gif", ".ico"}))
        self.lead_list.delete(0, "end")
        for url in self.leads:
            self.lead_list.insert("end", url)
        self.status.set(f"{len(self.leads)} photograph leads from this saved HTML page. Choose one or two to collect.")
        self._selection_changed()

    def _selection_changed(self):
        count = len(self.lead_list.curselection())
        self.collect_button.configure(state="normal" if self.worker is None and 1 <= count <= 2 else "disabled")
        if count > 2:
            self.status.set("Select at most two photographs for one collection.")
        elif self.status.get() == "Select at most two photographs for one collection.":
            self.status.set(f"{count} photographs selected." if count else "Choose one or two photographs to collect.")

    def _collect(self):
        selection = [self.leads[i] for i in self.lead_list.curselection()]
        if self.worker is not None or not 1 <= len(selection) <= 2:
            return
        source_id = self.pages[self.page_choice.current()]["source_id"]
        self.collect_button.configure(state="disabled")
        self.page_choice.configure(state="disabled")
        self.gallery_button.configure(state="disabled")
        self.status.set("Checking saved source evidence and collecting the selected photographs…")
        def run():
            try:
                result = collect_and_remember(self.inventory, source_id, selection, self.cache_root, fetcher=self.fetcher,
                                              on_progress=lambda item: self.messages.put(("progress", item)))
                self.messages.put(("complete", result))
            except Exception as exc:
                self.messages.put(("failed", str(exc)))
        # A bounded in-flight request may finish and save its result even if the
        # view closes. The thread never touches Tk objects directly.
        self.worker = threading.Thread(target=run, name="world-reference-photos", daemon=False)
        self.worker.start()
        self.after(150, self._poll)

    def _poll(self):
        done = False
        while True:
            try:
                kind, value = self.messages.get_nowait()
            except queue.Empty:
                break
            if kind == "progress":
                self.status.set(value["message"])
            elif kind == "complete":
                self.result = value
                self.status.set(f"{len(value['images'])} photographs cached. Visual review, scale and room coverage are still separate.")
                self.gallery_button.configure(state="normal")
                done = True
            else:
                self.status.set(f"Collection stopped with its saved evidence preserved: {value}")
                done = True
        if done:
            self.worker = None
            self.page_choice.configure(state="readonly")
            self._selection_changed()
        elif self.worker is not None:
            self.after(150, self._poll)

    def _open_gallery(self):
        try:
            self.result = load_latest_collection(self.job_dir, self.cache_root)
            if self.result is None:
                raise refs.ReferenceError("No cached photograph gallery yet")
            self.open_gallery(refs.verify_pin(self.result["gallery"]))
            self.status.set("Opened the verified local gallery. Original source pages and photographs remain linked.")
        except Exception as exc:
            self.status.set(f"Gallery unavailable: {exc}")
