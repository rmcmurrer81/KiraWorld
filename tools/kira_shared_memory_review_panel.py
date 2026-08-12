"""Panel for reviewing shared Kira/Lisa memory candidates.

This panel edits Data/memory_review/shared_memory_review_queue.json only.
It does not promote memories into Kira or Lisa memory files.
"""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, X, Y, Button, Frame, Label, Listbox, StringVar, Tk
from tkinter import messagebox, scrolledtext


PROJECT_ROOT = Path(__file__).resolve().parents[1]
QUEUE_PATH = PROJECT_ROOT / "Data" / "memory_review" / "shared_memory_review_queue.json"
BUILDER = PROJECT_ROOT / "tools" / "build_shared_memory_review_queue.py"

REVIEW_STATES = [
    "pending",
    "qualified_yes",
    "accepted_shareable",
    "needs_changes",
    "private",
    "reject",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def open_path(path: Path) -> None:
    if path.exists():
        os.startfile(str(path))
    else:
        os.startfile(str(path.parent))


class SharedMemoryReviewPanel:
    def __init__(self) -> None:
        self.root = Tk()
        self.root.title("Kira/Lisa Shared Memory Review")
        self.root.geometry("1220x760")
        self.root.minsize(980, 620)
        self.root.configure(bg="#0b1220")
        self.queue: dict = {}
        self.items: list[dict] = []
        self.selected_index: int | None = None
        self.status_var = StringVar(value="")
        self.build_ui()
        self.rebuild_queue()

    def build_ui(self) -> None:
        outer = Frame(self.root, bg="#0b1220")
        outer.pack(fill=BOTH, expand=True, padx=12, pady=12)
        left = Frame(outer, bg="#111827", bd=1, relief="solid", width=390)
        left.pack(side=LEFT, fill=Y, padx=(0, 12))
        right = Frame(outer, bg="#0b1220")
        right.pack(side=RIGHT, fill=BOTH, expand=True)

        Label(left, text="Shared Memory Queue", bg="#111827", fg="#f9fafb", font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=10, pady=(10, 4))
        Label(left, textvariable=self.status_var, bg="#111827", fg="#9ca3af").pack(anchor="w", padx=10, pady=(0, 8))
        self.listbox = Listbox(left, bg="#0b1220", fg="#e5e7eb", selectbackground="#1d4ed8", activestyle="none", height=30)
        self.listbox.pack(fill=BOTH, expand=True, padx=10, pady=(0, 8))
        self.listbox.bind("<<ListboxSelect>>", self.on_select)

        row = Frame(left, bg="#111827")
        row.pack(fill=X, padx=10, pady=(0, 10))
        Button(row, text="Refresh/Rebuild", command=self.rebuild_queue).pack(side=LEFT, fill=X, expand=True, padx=(0, 4))
        Button(row, text="Open Queue", command=lambda: open_path(QUEUE_PATH)).pack(side=LEFT, fill=X, expand=True, padx=(4, 0))

        Label(right, text="Candidate", bg="#0b1220", fg="#93c5fd", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        self.detail_box = scrolledtext.ScrolledText(right, wrap="word", bg="#111827", fg="#f9fafb", relief="flat", height=9)
        self.detail_box.pack(fill=X, pady=(6, 10))

        Label(right, text="Memory Layers", bg="#0b1220", fg="#c4b5fd", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        self.layers_box = scrolledtext.ScrolledText(right, wrap="word", bg="#111827", fg="#f9fafb", relief="flat", height=12)
        self.layers_box.pack(fill=BOTH, expand=True, pady=(6, 10))

        Label(right, text="Review Notes", bg="#0b1220", fg="#fbbf24", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        self.notes_box = scrolledtext.ScrolledText(right, wrap="word", bg="#111827", fg="#f9fafb", relief="flat", height=7)
        self.notes_box.pack(fill=BOTH, expand=True, pady=(6, 10))

        actions = Frame(right, bg="#0b1220")
        actions.pack(fill=X)
        Button(actions, text="Save Layers/Notes", command=self.save_text).pack(side=LEFT, fill=X, expand=True, padx=(0, 4))
        Button(actions, text="Open Candidate", command=self.open_candidate).pack(side=LEFT, fill=X, expand=True, padx=4)
        Button(actions, text="Ready if Both Accepted", command=self.mark_ready_if_both).pack(side=LEFT, fill=X, expand=True, padx=(4, 0))

        for owner in ("kira", "lisa", "robert_codex"):
            row = Frame(right, bg="#0b1220")
            row.pack(fill=X, pady=(8, 0))
            Label(row, text=f"{owner}:", bg="#0b1220", fg="#d1d5db", width=12, anchor="w").pack(side=LEFT)
            for state in REVIEW_STATES:
                Button(row, text=state, command=lambda o=owner, s=state: self.set_review_state(o, s)).pack(side=LEFT, padx=2)

    def rebuild_queue(self) -> None:
        try:
            subprocess.run(["py", str(BUILDER)], cwd=str(PROJECT_ROOT), check=True, capture_output=True, text=True)
        except Exception as exc:
            messagebox.showwarning("Queue rebuild warning", f"Could not rebuild queue automatically:\n{exc}")
        self.load_queue()

    def load_queue(self) -> None:
        self.queue = read_json(QUEUE_PATH, {"items": []})
        self.items = [item for item in self.queue.get("items", []) if isinstance(item, dict)]
        self.listbox.delete(0, END)
        for item in self.items:
            reviews = item.get("reviews", {})
            kira = reviews.get("kira", {}).get("state", "?") if isinstance(reviews, dict) else "?"
            lisa = reviews.get("lisa", {}).get("state", "?") if isinstance(reviews, dict) else "?"
            status = item.get("status", "needs_review")
            title = str(item.get("title") or item.get("candidate_id", ""))[:80]
            self.listbox.insert(END, f"[{status}] K:{kira} L:{lisa} - {title}")
        self.status_var.set(f"{len(self.items)} shared candidates. No memory is promoted here.")
        self.selected_index = None
        self.detail_box.delete("1.0", END)
        self.layers_box.delete("1.0", END)
        self.notes_box.delete("1.0", END)

    def selected_item(self) -> dict | None:
        if self.selected_index is None or self.selected_index >= len(self.items):
            messagebox.showinfo("No item selected", "Select a shared memory candidate first.")
            return None
        return self.items[self.selected_index]

    def on_select(self, _event=None) -> None:
        selection = self.listbox.curselection()
        if not selection:
            return
        self.selected_index = int(selection[0])
        item = self.items[self.selected_index]
        self.detail_box.delete("1.0", END)
        detail = {
            "candidate_id": item.get("candidate_id"),
            "status": item.get("status"),
            "promotion_status": item.get("promotion_status"),
            "participants": item.get("participants"),
            "privacy_level": item.get("privacy_level"),
            "sharing_rule": item.get("sharing_rule"),
            "summary": item.get("summary"),
            "detail": item.get("detail"),
            "reviews": item.get("reviews"),
        }
        self.detail_box.insert(END, json.dumps(detail, indent=2, ensure_ascii=False))

        self.layers_box.delete("1.0", END)
        self.layers_box.insert(END, json.dumps(item.get("layers", {}), indent=2, ensure_ascii=False))
        self.notes_box.delete("1.0", END)
        self.notes_box.insert(END, str(item.get("notes", "")))

    def save_queue(self) -> None:
        self.queue["updated_at"] = utc_now()
        self.queue["items"] = self.items
        write_json(QUEUE_PATH, self.queue)
        current = self.selected_index
        self.load_queue()
        if current is not None and current < self.listbox.size():
            self.listbox.selection_set(current)
            self.listbox.event_generate("<<ListboxSelect>>")

    def save_text(self) -> None:
        item = self.selected_item()
        if not item:
            return
        try:
            layers = json.loads(self.layers_box.get("1.0", END).strip() or "{}")
            if not isinstance(layers, dict):
                raise ValueError("layers must be a JSON object")
        except Exception as exc:
            messagebox.showerror("Invalid layers JSON", str(exc))
            return
        item["layers"] = layers
        item["notes"] = self.notes_box.get("1.0", END).strip()
        item["updated_at"] = utc_now()
        self.save_queue()

    def set_review_state(self, owner: str, state: str) -> None:
        item = self.selected_item()
        if not item:
            return
        reviews = item.setdefault("reviews", {})
        review = reviews.setdefault(owner, {})
        review["state"] = state
        review["reviewed_at"] = utc_now()
        item["status"] = "needs_robert_codex_review"
        if state in {"private", "reject"}:
            item["promotion_status"] = "blocked_or_private"
        item["updated_at"] = utc_now()
        self.save_queue()

    def mark_ready_if_both(self) -> None:
        item = self.selected_item()
        if not item:
            return
        reviews = item.get("reviews", {})
        accepted = {"qualified_yes", "accepted_shareable"}
        kira_ok = reviews.get("kira", {}).get("state") in accepted
        lisa_ok = reviews.get("lisa", {}).get("state") in accepted
        robert_ok = reviews.get("robert_codex", {}).get("state") in accepted
        if not (kira_ok and lisa_ok and robert_ok):
            messagebox.showinfo("Not ready", "Kira, Lisa, and Robert/Codex must all be qualified_yes or accepted_shareable first.")
            return
        item["status"] = "ready_for_smallest_shared_layer"
        item["promotion_status"] = "reviewed_not_promoted"
        item["updated_at"] = utc_now()
        self.save_queue()

    def open_candidate(self) -> None:
        item = self.selected_item()
        if not item:
            return
        path = PROJECT_ROOT / item.get("candidate_path", "")
        open_path(path)

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    SharedMemoryReviewPanel().run()
