"""Desktop World Builder workspace.

This is a lightweight, non-3D launcher for future notebook-world work. It
creates source-labeled notebook world requests and opens the folders for review.
It does not load Home World or generate a 3D scene.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tkinter as tk
from datetime import datetime, timezone
from pathlib import Path
from tkinter import ttk


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = PROJECT_ROOT / "tools"
sys.path.insert(0, str(TOOLS_ROOT))

import create_world_notebook_request as generator  # noqa: E402
from validate_notebook_world_request import validate_notebook_world_request  # noqa: E402


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

        self._build()
        self.refresh_index()
        self.refresh_school_status()

    def _build(self) -> None:
        root = ttk.Frame(self, padding=12)
        root.pack(fill="both", expand=True)

        ttk.Label(root, text="Kira World Builder Workspace", style="Header.TLabel").pack(anchor="w")
        ttk.Label(
            root,
            text="Plan new notebook worlds without loading 3D. Requests stay source-labeled and draft-only until Robert reviews them.",
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

        ttk.Label(form, text="Category").grid(row=1, column=1, sticky="w", padx=(8, 4), pady=(8, 2))
        category = ttk.Combobox(
            form,
            textvariable=self.category_var,
            values=["real_place", "real_historic_place", "fictional_or_original_place", "saved_place_template"],
            state="readonly",
        )
        category.grid(row=2, column=1, sticky="ew", padx=(8, 4), pady=(0, 8))
        form.columnconfigure(0, weight=1)
        form.columnconfigure(1, weight=1)

        buttons = ttk.Frame(root)
        buttons.pack(fill="x", pady=(6, 10))
        ttk.Button(buttons, text="Create Notebook World Request", command=self.create_request).pack(side="left", padx=(0, 6))
        ttk.Button(buttons, text="Open Latest Folder", command=self.open_latest_folder).pack(side="left", padx=6)
        ttk.Button(buttons, text="Open Latest Blueprint", command=self.open_latest_blueprint).pack(side="left", padx=6)
        ttk.Button(buttons, text="Open World Index", command=lambda: open_path(WORLD_INDEX)).pack(side="left", padx=6)
        ttk.Button(buttons, text="Start World Builder School", command=self.start_school).pack(side="left", padx=6)
        ttk.Button(buttons, text="Refresh", command=self.refresh_all).pack(side="left", padx=6)

        chat = ttk.Frame(root)
        chat.pack(fill="x", pady=(0, 10))
        ttk.Label(chat, text="Talk To World Builder").pack(anchor="w")
        chat_row = ttk.Frame(chat)
        chat_row.pack(fill="x", pady=(3, 0))
        self.chat_entry = ttk.Entry(chat_row, textvariable=self.chat_var)
        self.chat_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.chat_entry.bind("<Return>", lambda _event: self.send_world_builder_chat())
        ttk.Button(chat_row, text="Send Note", command=self.send_world_builder_chat).pack(side="left")

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
        intents = infer_world_builder_intents(message)
        memory_path = append_world_builder_memory(message, intents, self.latest_folder)

        note_path = None
        if self.latest_folder:
            note_path = self.latest_folder / "world_builder_chat_notes.json"
            notes = read_json(note_path)
            notes.setdefault("schema_version", 1)
            notes.setdefault("request_folder", rel(self.latest_folder))
            notes.setdefault("notes", []).append({
                "created_at": now_iso(),
                "from": "Robert",
                "message": message,
                "understood_intents": intents,
                "builder_response": "Saved as design intent; approval-first preview and TARDIS staging rules remain active.",
            })
            notes["updated_at"] = now_iso()
            write_json(note_path, notes)

        self.log("")
        self.log(f"Robert: {message}")
        self.log("World Builder understood: " + ", ".join(intents))
        self.log("World Builder: I saved that as design intent. I will not place a building or map into a world until Robert approves the blueprint/preview.")
        self.log("Memory: " + rel(memory_path))
        if note_path:
            self.log("Latest request note: " + rel(note_path))
        if "online_research" in intents:
            self.log("Online research is queued as a need; source links must be saved before the builder claims facts.")

    def start_school(self) -> None:
        subprocess.Popen(
            [sys.executable, "tools/run_world_builder_school_loop_20260712.py", "--duration-hours", "2", "--cycle-minutes", "20"],
            cwd=str(PROJECT_ROOT),
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        self.log("Started World Builder School in the background.")
        self.after(2000, self.refresh_school_status)

    def refresh_all(self) -> None:
        self.refresh_index()
        self.refresh_school_status()

    def refresh_school_status(self) -> None:
        data = read_json(CURRENT_SCHOOL)
        if data:
            self.log(
                "World Builder School status: "
                + str(data.get("status"))
                + " | "
                + str(data.get("current_lesson") or data.get("run_id"))
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
