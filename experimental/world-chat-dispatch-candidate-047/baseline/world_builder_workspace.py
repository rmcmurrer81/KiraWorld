"""Desktop World Builder workspace.

Research real places and original worlds, collect reference photographs and
open isolated generated layout previews. School prepares reference study notes;
it does not train a model or validate construction. Home World is not loaded.
"""

from __future__ import annotations

import json
import os
import re
import queue
import subprocess
import sys
import threading
import tkinter as tk
from datetime import datetime, timezone
from pathlib import Path
from tkinter import ttk, filedialog


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = PROJECT_ROOT / "tools"
sys.path.insert(0, str(TOOLS_ROOT))

import create_world_notebook_request as generator  # noqa: E402
from validate_notebook_world_request import validate_notebook_world_request  # noqa: E402
from world_research import DEFAULT_JOB_ROOT, run_job  # noqa: E402
from world_research_workspace_adapter import submit_research_prompt
from world_saved_research import list_saved_research, read_saved_research
from world_builder_engine.workspace_adapter import run_pipeline_after_research, open_preview, close_preview  # noqa: E402
from world_builder_engine.layout_package_export import export_saved_layout_package
from world_reference_images_adapter import ReferencePhotosView  # noqa: E402
from world_builder_components.workspace_adapter import OriginalComponentsView  # noqa: E402


WORLD_INDEX = PROJECT_ROOT / "Data" / "world_builds" / "notebook_world_index.json"
CURRENT_SCHOOL = PROJECT_ROOT / "Data" / "presence" / "current_world_builder_school_run.json"
WORLD_BUILDER_MEMORY = PROJECT_ROOT / "Data" / "world_builds" / "world_builder_conversation_memory.json"


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


def open_path(path: Path) -> None:
    target = path if path.exists() else path.parent
    if os.name == "nt":
        os.startfile(str(target))  # type: ignore[attr-defined]
    else:
        subprocess.Popen(["xdg-open", str(target)])


def read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def infer_world_builder_intents(message: str) -> list[str]:
    lowered = message.lower()
    intents: list[str] = []
    checks = [
        ("building", ("building", "house", "store", "shop", "school", "library", "home", "room")),
        ("notebook_world", ("notebook world", "new world", "map", "world")),
        ("existing_world_addition", ("home world", "already built", "existing world", "current world")),
        ("blueprint_or_map", ("blueprint", "floor plan", "map", "where it goes", "placement", "place it")),
        ("tardis_review", ("tardis", "walk around", "review stage", "preview room")),
        ("approval_gate", ("approve", "approval", "before placing", "do not place", "not place")),
        ("preview", ("preview", "outside", "exterior", "small part", "slice")),
        ("online_research", ("search online", "research online", "look online", "go online", "web search")),
    ]
    for intent, terms in checks:
        if any(term in lowered for term in terms):
            intents.append(intent)
    return sorted(set(intents)) or ["general_design_note"]


def append_world_builder_memory(message: str, intents: list[str], latest_folder: Path | None) -> Path:
    data = read_json(WORLD_BUILDER_MEMORY)
    data.setdefault("schema_version", 1)
    data.setdefault("builder", "world_builder")
    data.setdefault("rules", {
        "approval_first": "The World Builder may create previews and staged drafts, but must not commit buildings or maps into Home World or notebook worlds without Robert approval.",
        "preview_first": "Building requests need blueprint/map placement plus an exterior or representative scene preview before approval.",
        "tardis_review": "Walkable review drafts are staged in the TARDIS builder bay before final import.",
    })
    data.setdefault("conversation", []).append({
        "created_at": now_iso(),
        "from": "Robert",
        "message": message,
        "understood_intents": intents,
        "latest_folder": rel(latest_folder) if latest_folder else "",
    })
    data["updated_at"] = now_iso()
    write_json(WORLD_BUILDER_MEMORY, data)
    return WORLD_BUILDER_MEMORY


class WorldBuilderWorkspace(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Kira World Builder Workspace")
        self._research_messages = queue.Queue()
        self._research_pending = []
        self._research_worker = None
        self._research_latest = None
        self._saved_research_items = []
        self._layout_preview = None
        self._export_messages = queue.Queue()
        self._export_worker = None
        self._last_export_folder = None
        self._reference_photos_view = None
        self._original_components_view = None
        self.protocol("WM_DELETE_WINDOW", self._close_world_builder)
        self.geometry("980x680")
        self.configure(bg="#06111d")
        self.latest_folder: Path | None = None
        self.latest_request: Path | None = None

        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.style.configure("TFrame", background="#06111d")
        self.style.configure("TLabel", background="#06111d", foreground="#d7ecff", font=("Segoe UI", 10))
        self.style.configure("Header.TLabel", background="#06111d", foreground="#ffffff", font=("Segoe UI", 16, "bold"))
        self.style.configure("TEntry", fieldbackground="#071827", foreground="#ffffff", insertcolor="#ffffff")
        self.style.configure("TButton", background="#123c63", foreground="#ffffff", borderwidth=1)
        self.style.map("TButton", background=[("active", "#1c5487")])
        self.style.configure("TCombobox", fieldbackground="#071827", foreground="#ffffff", background="#071827")
        self.style.map("TCombobox", fieldbackground=[("readonly", "#071827")],
                       foreground=[("readonly", "#ffffff")],
                       selectbackground=[("readonly", "#174d79")],
                       selectforeground=[("readonly", "#ffffff")])

        self._build()
        self.refresh_index()
        self.refresh_saved_research()
        self.refresh_school_status()

    def _build(self) -> None:
        root = ttk.Frame(self, padding=12)
        root.pack(fill="both", expand=True)

        ttk.Label(root, text="Kira World Builder Workspace", style="Header.TLabel").pack(anchor="w")
        ttk.Label(
            root,
            text="Describe a place, collect references, and preview an original layout. Saved research can be resumed.",
        ).pack(anchor="w", pady=(2, 12))

        form = ttk.Frame(root)
        form.pack(fill="x")
        self.name_var = tk.StringVar(value="Louvre Courtyard")
        self.city_var = tk.StringVar(value="Paris")
        self.era_var = tk.StringVar(value="current_or_best_sourced")
        self.category_var = tk.StringVar(value="real_place")
        self.chat_var = tk.StringVar(value="")

        self._field(form, "Place / World Seed", self.name_var, 0, 0)
        self._field(form, "City", self.city_var, 0, 1)
        self._field(form, "Era", self.era_var, 1, 0)

        ttk.Label(form, text="Category").grid(row=2, column=1, sticky="w", padx=(8, 4), pady=(0, 2))
        category = ttk.Combobox(
            form,
            textvariable=self.category_var,
            values=["real_place", "real_historic_place", "fictional_or_original_place", "saved_place_template"],
            state="readonly",
        )
        category.grid(row=3, column=1, sticky="ew", padx=(8, 4), pady=(0, 8))
        form.columnconfigure(0, weight=1)
        form.columnconfigure(1, weight=1)

        buttons = ttk.Frame(root)
        buttons.pack(fill="x", pady=(6, 10))
        ttk.Button(buttons, text="Create Notebook World Request", command=self.create_request).pack(side="left", padx=(0, 6))
        ttk.Button(buttons, text="Open Latest Folder", command=self.open_latest_folder).pack(side="left", padx=6)
        ttk.Button(buttons, text="Open Latest Blueprint", command=self.open_latest_blueprint).pack(side="left", padx=6)
        ttk.Button(buttons, text="Open World Index", command=lambda: open_path(WORLD_INDEX)).pack(side="left", padx=6)
        ttk.Button(buttons, text="School: Prepare Notes", command=self.start_school).pack(side="left", padx=6)
        ttk.Button(buttons, text="Refresh", command=self.refresh_all).pack(side="left", padx=6)

        chat = ttk.Frame(root)
        chat.pack(fill="x", pady=(0, 10))
        ttk.Label(chat, text="Talk To World Builder").pack(anchor="w")
        chat_row = ttk.Frame(chat)
        chat_row.pack(fill="x", pady=(3, 0))
        self.chat_entry = ttk.Entry(chat_row, textvariable=self.chat_var)
        self.chat_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.chat_entry.bind("<Return>", lambda _event: self.send_world_builder_chat())
        ttk.Button(chat_row, text="Research / Resume", command=self.send_world_builder_chat).pack(side="left")
        ttk.Button(chat_row, text="Open current preview", command=self.open_layout_preview).pack(side="left", padx=(6, 0))
        ttk.Button(chat_row, text="Reference Photos", command=self.open_reference_photos).pack(side="left", padx=(6, 0))

        exports = ttk.Frame(chat)
        exports.pack(fill="x", pady=(7, 0))
        self._export_button = ttk.Button(exports, text="Export 3D package (experimental)", command=self.export_3d_package)
        self._export_button.pack(side="left")
        ttk.Button(exports, text="Open export folder", command=self.open_export_folder).pack(side="left", padx=(6, 0))
        ttk.Label(exports, text="Export the selected layout as a 3D asset for other tools.").pack(side="left", padx=(8, 0))

        saved = ttk.Frame(chat)
        saved.pack(fill="x", pady=(7, 0))
        ttk.Label(saved, text="Saved research / layouts").pack(side="left", padx=(0, 6))
        self.saved_research_choice = ttk.Combobox(saved, state="readonly")
        self.saved_research_choice.pack(side="left", fill="x", expand=True)
        self.saved_research_choice.bind("<<ComboboxSelected>>", self.select_saved_research)
        ttk.Button(saved, text="Refresh saved", command=self.refresh_saved_research).pack(side="left", padx=(6, 0))

        components = ttk.Frame(chat)
        components.pack(fill="x", pady=(7, 0))
        ttk.Button(components, text="Original Components", command=self.open_original_components).pack(side="left")
        ttk.Label(components, text="Build authored frame parts and inspect saved construction recipes.").pack(side="left", padx=8)

        panes = ttk.Panedwindow(root, orient="horizontal")
        panes.pack(fill="both", expand=True)

        left = ttk.Frame(panes, padding=(0, 0, 8, 0))
        right = ttk.Frame(panes)
        panes.add(left, weight=1)
        panes.add(right, weight=2)

        ttk.Label(left, text="Notebook Worlds", style="Header.TLabel").pack(anchor="w", pady=(0, 8))
        self.world_list = tk.Listbox(
            left,
            bg="#071827",
            fg="#d7ecff",
            selectbackground="#174d79",
            selectforeground="#ffffff",
            relief="flat",
            highlightthickness=1,
            highlightbackground="#1d4261",
            font=("Segoe UI", 10),
        )
        self.world_list.pack(fill="both", expand=True)
        self.world_list.bind("<<ListboxSelect>>", lambda _event: self.show_selected_world())

        ttk.Label(right, text="Builder Output", style="Header.TLabel").pack(anchor="w", pady=(0, 8))
        self.output = tk.Text(
            right,
            bg="#071827",
            fg="#d7ecff",
            insertbackground="#ffffff",
            relief="flat",
            wrap="word",
            font=("Consolas", 10),
        )
        self.output.pack(fill="both", expand=True)

    def _field(self, parent: ttk.Frame, label: str, variable: tk.StringVar, row: int, col: int) -> None:
        ttk.Label(parent, text=label).grid(row=row * 2, column=col, sticky="w", padx=(0 if col == 0 else 8, 4), pady=(0, 2))
        entry = ttk.Entry(parent, textvariable=variable)
        entry.grid(row=row * 2 + 1, column=col, sticky="ew", padx=(0 if col == 0 else 8, 4), pady=(0, 8))

    def log(self, message: str) -> None:
        self.output.insert("end", message.rstrip() + "\n")
        self.output.see("end")

    def create_request(self) -> None:
        name = self.name_var.get().strip()
        if not name:
            self.log("Place / World Seed is required.")
            return
        seed = generator.infer_seed(
            name,
            city=self.city_var.get().strip(),
            era=self.era_var.get().strip(),
            category=self.category_var.get().strip() or "real_place",
        )
        paths = generator.create_files(
            seed,
            requested_by="robert",
            trigger=f"World Builder Workspace draft request for {seed.name}",
            visibility="private_only",
            autonomy="request_mode",
            status="draft",
        )
        request_data = read_json(paths["request"])
        errors = validate_notebook_world_request(request_data)
        self.latest_request = paths["request"]
        self.latest_folder = paths["request"].parent
        self.log("")
        self.log(f"Created notebook-world request: {request_data.get('request_id')}")
        self.log(f"Notebook world: {request_data.get('world_plan', {}).get('notebook_world_id')}")
        self.log(f"Folder: {rel(self.latest_folder)}")
        self.log("Validation: " + ("OK" if not errors else "; ".join(errors)))
        for key, path in paths.items():
            self.log(f"- {key}: {rel(path)}")
        self.log("Approval gate: draft only; preview/blueprint review required before any world import.")
        self.refresh_index()

    def open_latest_folder(self) -> None:
        if self.latest_folder and self.latest_folder.exists():
            open_path(self.latest_folder)
        else:
            open_path(PROJECT_ROOT / "Data" / "world_builds" / "notebook_worlds")

    def open_latest_blueprint(self) -> None:
        if self.latest_folder and (self.latest_folder / "blueprint_map.md").exists():
            open_path(self.latest_folder / "blueprint_map.md")
        elif self.latest_folder and (self.latest_folder / "blueprint_preview.json").exists():
            open_path(self.latest_folder / "blueprint_preview.json")
        else:
            self.log("No latest blueprint preview yet. Create a notebook-world request first.")

    def send_world_builder_chat(self) -> None:
        message = self.chat_var.get().strip()
        if not message:
            return
        self.chat_var.set("")
        try:
            submitted = submit_research_prompt(message, job_root=DEFAULT_JOB_ROOT, latest_job=self._research_latest)
        except Exception as exc:
            self.log(f"Research request could not start: {exc}")
            return
        if submitted["job_dir"] != self._research_latest:
            # Chat submission selects a world just like the saved-job chooser.
            # Do not let its export capture the previous world's preview, or
            # leave reference/component windows showing the previous selection.
            self.set_saved_research_context(submitted["job_dir"])
        self.latest_folder = submitted["job_dir"]
        self.refresh_saved_research()
        self.log(f"Research job: {submitted['job_id']} | saved state: {submitted['stage']}")
        self.log(f"Subject: {submitted['subject']} | {submitted['research_mode']} | {submitted['visual_style']['description']}")
        if submitted["job_dir"] not in self._research_pending:
            self._research_pending.append(submitted["job_dir"])
        self._start_next_research()

    def refresh_saved_research(self) -> None:
        try:
            self._saved_research_items = list_saved_research(DEFAULT_JOB_ROOT)
        except (OSError, ValueError) as exc:
            self._saved_research_items = []
            self.log(f"Saved research list unavailable: {exc}")
        self.saved_research_choice.configure(values=[item["label"] for item in self._saved_research_items])
        selected = next((index for index, item in enumerate(self._saved_research_items)
                         if item["job_dir"] == self._research_latest), None)
        if selected is None:
            self.saved_research_choice.set("Choose a saved research job" if self._saved_research_items else "No saved research jobs yet")
        else:
            self.saved_research_choice.current(selected)

    def select_saved_research(self, _event=None) -> None:
        index = self.saved_research_choice.current()
        if index < 0 or index >= len(self._saved_research_items):
            return
        item = self._saved_research_items[index]
        try:
            selected = read_saved_research(item["job_dir"], job_root=DEFAULT_JOB_ROOT)
        except (OSError, ValueError) as exc:
            self.set_saved_research_context(None)
            self.log(f"Saved research could not be opened: {exc}. Its files were preserved.")
            return
        self.set_saved_research_context(selected["job_dir"])
        self.log(f"Opened saved research: {selected['subject']} | {selected['stage']}")
        self.log("Use Open current preview to view the saved layout with current appearance and controls, or Reference Photos. Original layout files are preserved.")

    def set_saved_research_context(self, job_dir: Path | None) -> None:
        close_preview(self._layout_preview)
        self._layout_preview = None
        if self._reference_photos_view is not None and self._reference_photos_view.winfo_exists():
            self._reference_photos_view.destroy()
        self._reference_photos_view = None
        if self._original_components_view is not None and self._original_components_view.winfo_exists():
            self._original_components_view.set_world_job(job_dir)
        self._research_latest = job_dir
        self.latest_folder = job_dir
        self.latest_request = None

    def _start_next_research(self) -> None:
        if self._research_worker is not None or not self._research_pending:
            return
        job_dir = self._research_pending.pop(0)
        def worker():
            try:
                result = run_job(job_dir, on_progress=lambda value: self._research_messages.put(("progress", value)))
                result["layout_pipeline"] = run_pipeline_after_research(
                    job_dir, on_progress=lambda value: self._research_messages.put(("layout_progress", value)))
                self._research_messages.put(("finished", result))
            except Exception as exc:
                self._research_messages.put(("failed", str(exc)))
        self._research_worker = threading.Thread(target=worker, daemon=True, name="world-public-research")
        self._research_worker.start()
        self.after(200, self._poll_research)

    def _poll_research(self) -> None:
        completed = False
        while True:
            try:
                kind, value = self._research_messages.get_nowait()
            except queue.Empty:
                break
            if kind == "progress":
                self.log(f"{value['stage']}: {value['retrieved']} source pages retrieved" + (f" | {value['last_error']}" if value['last_error'] else ""))
            elif kind == "layout_progress":
                self.log(f"Layout: {value.get('stage', '')} | {value.get('message', '')}")
            elif kind == "finished":
                self.log(f"Saved result: {value['stage']} | {value['retrieved_sources']} text sources | {value['job_dir']}")
                pipeline = value.get("layout_pipeline", {})
                self.log(f"Layout: {pipeline.get('stage', 'not_started')} | {pipeline.get('message', '')}")
                if pipeline.get("geometry_generated"):
                    self.log("Original layout only: materials and visual detail remain unfinished. Use Open current preview to explore.")
                else:
                    self.log("Photos, videos and plan layouts still require inspection. No accessible world was generated.")
                completed = True
            else:
                self.log(f"Research stopped with a saved checkpoint: {value}")
                completed = True
        if completed:
            self.refresh_saved_research()
            self._research_worker = None
            self._start_next_research()
        elif self._research_worker is not None:
            self.after(200, self._poll_research)

    def open_layout_preview(self) -> None:
        if self._research_latest is None:
            self.log("Choose or submit a saved original-world research job first.")
            return
        try:
            self._layout_preview = open_preview(self._research_latest, self._layout_preview)
            self.log("Opened the current presentation of your saved layout. Earlier previews are preserved; no research or model generation was rerun. This remains a prototype.")
        except Exception as exc:
            self.log(f"Layout preview unavailable: {exc}")

    def open_original_components(self) -> None:
        if self._original_components_view is not None and self._original_components_view.winfo_exists():
            self._original_components_view.set_world_job(self._research_latest)
            self._original_components_view.lift()
            return
        self._original_components_view = OriginalComponentsView(self, selected_job=self._research_latest, on_message=self.log)

    def export_3d_package(self) -> None:
        if self._export_worker is not None:
            self.log("A 3D export is already in progress.")
            return
        job_dir = self._research_latest
        if job_dir is None:
            self.log("Choose a saved layout before exporting a 3D package.")
            return
        folder = filedialog.askdirectory(parent=self, title="Choose a folder for your 3D package", mustexist=True)
        if not folder:
            return
        destination = Path(folder) / ("World-3D-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f"))
        # Capture the current selection before the background job; a later UI
        # selection must not substitute a different world or preview.
        current = self._layout_preview
        preview = dict(current.manifest) if current is not None else None
        self._export_button.configure(state="disabled")
        self.log("Exporting the selected layout's meshes and textures…")
        def worker():
            try:
                result = export_saved_layout_package(job_dir, destination, preview_binding=preview)
            except Exception:
                result = {"status": "export_failed", "message": "The 3D export stopped unexpectedly. Original files were preserved."}
            self._export_messages.put(result)
        self._export_worker = threading.Thread(target=worker, daemon=True, name="world-layout-package-export")
        self._export_worker.start()
        self.after(200, self._poll_3d_export)

    def _poll_3d_export(self) -> None:
        try:
            result = self._export_messages.get_nowait()
        except queue.Empty:
            if self._export_worker is not None:
                self.after(200, self._poll_3d_export)
            return
        self._export_worker = None
        self._export_button.configure(state="normal")
        self.log(result["message"])
        if result.get("status") == "created":
            self._last_export_folder = Path(result["output_dir"])
            self.log("3D package saved to: " + str(self._last_export_folder))
        elif result.get("output_dir"):
            self.log("Incomplete export retained for inspection: " + result["output_dir"])

    def open_export_folder(self) -> None:
        if self._last_export_folder is None:
            self.log("Export a 3D package first; its folder will be available here.")
            return
        open_path(self._last_export_folder)

    def _close_world_builder(self) -> None:
        if self._export_worker is not None:
            self.log("Please wait for the current 3D export to finish before closing this window.")
            return
        if self._original_components_view is not None and self._original_components_view.winfo_exists():
            self._original_components_view.close()
        close_preview(self._layout_preview)
        self.destroy()

    def open_reference_photos(self) -> None:
        job_dir = self._research_latest
        if job_dir is None:
            candidates = list(DEFAULT_JOB_ROOT.glob("world_research_*/research_packet.json")) if DEFAULT_JOB_ROOT.exists() else []
            if not candidates:
                self.log("No saved research pages yet. Research a place first, then choose Reference Photos.")
                return
            job_dir = max(candidates, key=lambda path: path.stat().st_mtime).parent
        try:
            if self._reference_photos_view is not None and self._reference_photos_view.winfo_exists():
                self._reference_photos_view.destroy()
            self._reference_photos_view = ReferencePhotosView(
                self, job_dir, PROJECT_ROOT / "Data" / "world_reference_images", open_gallery=open_path)
        except Exception as exc:
            self.log(f"Reference photos unavailable: {exc}")

    def start_school(self) -> None:
        subprocess.Popen(
            [sys.executable, "tools/run_world_builder_school_loop_20260712.py", "--duration-hours", "2", "--cycle-minutes", "20"],
            cwd=str(PROJECT_ROOT),
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        self.log("Preparing School study notes in the background. This does not train a model or build or test an object.")
        self.after(2000, self.refresh_school_status)

    def refresh_all(self) -> None:
        self.refresh_index()
        self.refresh_saved_research()
        self.refresh_school_status()

    def refresh_school_status(self) -> None:
        data = read_json(CURRENT_SCHOOL)
        if data:
            self.log(
                "School study-note schedule: "
                + str(data.get("status"))
                + " | "
                + str(data.get("current_lesson") or data.get("run_id"))
                + " | Assignment records only; no construction skill verified."
            )

    def refresh_index(self) -> None:
        self.world_list.delete(0, "end")
        data = read_json(WORLD_INDEX)
        worlds = data.get("notebook_worlds", {}) if isinstance(data.get("notebook_worlds"), dict) else {}
        for world_id, world in sorted(worlds.items()):
            anchors = world.get("anchors", []) if isinstance(world.get("anchors"), list) else []
            self.world_list.insert("end", f"{world_id}  ({len(anchors)} anchors)")

    def show_selected_world(self) -> None:
        selection = self.world_list.curselection()
        if not selection:
            return
        text = self.world_list.get(selection[0])
        world_id = text.split()[0]
        data = read_json(WORLD_INDEX)
        world = data.get("notebook_worlds", {}).get(world_id, {})
        self.log("")
        self.log(json.dumps({world_id: world}, indent=2, ensure_ascii=False))


def main() -> int:
    app = WorldBuilderWorkspace()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
