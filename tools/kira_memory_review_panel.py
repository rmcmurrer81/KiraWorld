"""Review Kira/Lisa memory/privacy candidates without promoting them."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, X, Y, Button, Frame, Label, Listbox, StringVar, Tk
from tkinter import messagebox, scrolledtext


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LEDGER_PATH = PROJECT_ROOT / "Data" / "memory_review" / "kira_life_day_review_ledger.json"
PRIVACY_LABELS = [
    "shareable",
    "summary_only",
    "private_unless_shared",
    "ask_before_sharing",
    "never_promote_without_review",
    "source_fact",
    "soft_reconstruction",
    "preference_signal",
    "rejected_not_memory",
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


class MemoryReviewPanel:
    def __init__(self) -> None:
        self.root = Tk()
        self.root.title("Kira Memory / Privacy Review")
        self.root.geometry("1160x720")
        self.root.minsize(960, 580)
        self.root.configure(bg="#0b1220")
        self.ledger: dict = {}
        self.entries: list[dict] = []
        self.selected_index: int | None = None
        self.status_var = StringVar(value="")
        self.label_var = StringVar(value="")
        self.build_ui()
        self.load_entries()

    def build_ui(self) -> None:
        outer = Frame(self.root, bg="#0b1220")
        outer.pack(fill=BOTH, expand=True, padx=12, pady=12)
        left = Frame(outer, bg="#111827", bd=1, relief="solid", width=390)
        left.pack(side=LEFT, fill=Y, padx=(0, 12))
        right = Frame(outer, bg="#0b1220")
        right.pack(side=RIGHT, fill=BOTH, expand=True)

        Label(left, text="Memory / Privacy Candidates", bg="#111827", fg="#f9fafb", font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=10, pady=(10, 4))
        Label(left, textvariable=self.status_var, bg="#111827", fg="#9ca3af").pack(anchor="w", padx=10, pady=(0, 8))
        self.listbox = Listbox(left, bg="#0b1220", fg="#e5e7eb", selectbackground="#1d4ed8", activestyle="none", height=28)
        self.listbox.pack(fill=BOTH, expand=True, padx=10, pady=(0, 8))
        self.listbox.bind("<<ListboxSelect>>", self.on_select)
        row = Frame(left, bg="#111827")
        row.pack(fill=X, padx=10, pady=(0, 10))
        Button(row, text="Refresh", command=self.load_entries).pack(side=LEFT, fill=X, expand=True, padx=(0, 4))
        Button(row, text="Open Ledger", command=self.open_ledger).pack(side=LEFT, fill=X, expand=True, padx=(4, 0))

        Label(right, text="Candidate Detail", bg="#0b1220", fg="#93c5fd", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        self.detail_box = scrolledtext.ScrolledText(right, wrap="word", bg="#111827", fg="#f9fafb", relief="flat", height=12)
        self.detail_box.pack(fill=X, pady=(6, 10))

        Label(right, text="Review Note", bg="#0b1220", fg="#fbbf24", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        self.note_box = scrolledtext.ScrolledText(right, wrap="word", bg="#111827", fg="#f9fafb", relief="flat", height=8)
        self.note_box.pack(fill=BOTH, expand=True, pady=(6, 10))

        label_row = Frame(right, bg="#0b1220")
        label_row.pack(fill=X)
        Label(label_row, text="Set label:", bg="#0b1220", fg="#d1d5db").pack(side=LEFT, padx=(0, 8))
        for label in PRIVACY_LABELS[:5]:
            Button(label_row, text=label, command=lambda value=label: self.set_label(value)).pack(side=LEFT, padx=2)

        label_row2 = Frame(right, bg="#0b1220")
        label_row2.pack(fill=X, pady=(6, 0))
        for label in PRIVACY_LABELS[5:]:
            Button(label_row2, text=label, command=lambda value=label: self.set_label(value)).pack(side=LEFT, padx=2)

        actions = Frame(right, bg="#0b1220")
        actions.pack(fill=X, pady=(10, 0))
        Button(actions, text="Save Review Note", command=self.save_note).pack(side=LEFT, fill=X, expand=True, padx=(0, 5))
        Button(actions, text="Needs Review", command=lambda: self.set_needs_review(True)).pack(side=LEFT, fill=X, expand=True, padx=5)
        Button(actions, text="Reviewed", command=lambda: self.set_needs_review(False)).pack(side=LEFT, fill=X, expand=True, padx=(5, 0))

    def load_entries(self) -> None:
        self.ledger = read_json(LEDGER_PATH, {"entries": []})
        entries = self.ledger.get("entries", []) if isinstance(self.ledger, dict) else []
        self.entries = [entry for entry in entries if isinstance(entry, dict)]
        self.listbox.delete(0, END)
        for entry in self.entries:
            flag = "needs" if entry.get("needs_review", True) else "ok"
            label = entry.get("privacy_label", "")
            summary = str(entry.get("summary", "")).replace("\n", " ")
            self.listbox.insert(END, f"[{flag}] [{label}] {entry.get('owner','?')} {entry.get('review_type','')} - {summary[:70]}")
        needs = sum(1 for item in self.entries if item.get("needs_review", True))
        self.status_var.set(f"{len(self.entries)} entries, {needs} need review")
        self.selected_index = None
        self.detail_box.delete("1.0", END)
        self.note_box.delete("1.0", END)

    def selected_entry(self) -> dict | None:
        if self.selected_index is None or self.selected_index >= len(self.entries):
            messagebox.showinfo("No entry selected", "Select a memory/privacy candidate first.")
            return None
        return self.entries[self.selected_index]

    def on_select(self, _event=None) -> None:
        selection = self.listbox.curselection()
        if not selection:
            return
        self.selected_index = int(selection[0])
        entry = self.entries[self.selected_index]
        self.detail_box.delete("1.0", END)
        fields = [
            "entry_id", "owner", "run_id", "cycle", "action", "review_type",
            "privacy_label", "needs_review", "source_title", "source_path",
        ]
        for field in fields:
            self.detail_box.insert(END, f"{field}: {entry.get(field, '')}\n")
        self.detail_box.insert(END, "\nSummary:\n")
        self.detail_box.insert(END, str(entry.get("summary", "")))
        policy = entry.get("promotion_policy", {})
        if isinstance(policy, dict):
            self.detail_box.insert(END, "\n\nPromotion policy:\n")
            self.detail_box.insert(END, json.dumps(policy, indent=2, ensure_ascii=False))

        self.note_box.delete("1.0", END)
        self.note_box.insert(END, str(entry.get("review_note", "")))

    def save_ledger(self) -> None:
        self.ledger["updated_at"] = utc_now()
        labels = self.ledger.setdefault("policy", {}).setdefault("labels", [])
        for label in PRIVACY_LABELS:
            if label not in labels:
                labels.append(label)
        write_json(LEDGER_PATH, self.ledger)
        current = self.selected_index
        self.load_entries()
        if current is not None and current < self.listbox.size():
            self.listbox.selection_set(current)
            self.listbox.event_generate("<<ListboxSelect>>")

    def set_label(self, label: str) -> None:
        entry = self.selected_entry()
        if not entry:
            return
        entry["privacy_label"] = label
        entry["reviewed_at"] = utc_now()
        entry.setdefault("review_history", []).append({"at": utc_now(), "action": "set_label", "label": label})
        policy = entry.setdefault("promotion_policy", {})
        if isinstance(policy, dict):
            policy["private_by_default"] = label in {"private_unless_shared", "ask_before_sharing"}
            policy["not_auto_promoted"] = True
            policy["shared_memory_requires_relevant_people_review"] = True
        self.save_ledger()

    def save_note(self) -> None:
        entry = self.selected_entry()
        if not entry:
            return
        entry["review_note"] = self.note_box.get("1.0", END).strip()
        entry["reviewed_at"] = utc_now()
        entry.setdefault("review_history", []).append({"at": utc_now(), "action": "save_note"})
        self.save_ledger()

    def set_needs_review(self, value: bool) -> None:
        entry = self.selected_entry()
        if not entry:
            return
        entry["needs_review"] = value
        entry["reviewed_at"] = utc_now()
        entry.setdefault("review_history", []).append({"at": utc_now(), "action": "set_needs_review", "value": value})
        self.save_ledger()

    def open_ledger(self) -> None:
        if LEDGER_PATH.exists():
            os.startfile(str(LEDGER_PATH))
        else:
            os.startfile(str(LEDGER_PATH.parent))

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    MemoryReviewPanel().run()
