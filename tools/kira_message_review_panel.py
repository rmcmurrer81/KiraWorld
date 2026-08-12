"""Unread Kira-to-Robert message review panel."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, X, Y, Button, Frame, Label, Listbox, StringVar, Tk
from tkinter import messagebox, scrolledtext


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MESSAGES_DIR = PROJECT_ROOT / "Data" / "messages" / "kira_to_robert"


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


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return p.as_posix()


class KiraMessageReviewPanel:
    def __init__(self) -> None:
        self.root = Tk()
        self.root.title("Kira Messages To Robert")
        self.root.geometry("980x640")
        self.root.minsize(840, 520)
        self.root.configure(bg="#0b1220")
        self.status_var = StringVar(value="")
        self.items: list[tuple[Path, dict]] = []
        self.selected_index: int | None = None
        self.build_ui()
        self.load_messages()

    def build_ui(self) -> None:
        outer = Frame(self.root, bg="#0b1220")
        outer.pack(fill=BOTH, expand=True, padx=12, pady=12)

        left = Frame(outer, bg="#111827", bd=1, relief="solid", width=360)
        left.pack(side=LEFT, fill=Y, padx=(0, 12))
        right = Frame(outer, bg="#0b1220")
        right.pack(side=RIGHT, fill=BOTH, expand=True)

        Label(left, text="Kira Messages", bg="#111827", fg="#f9fafb", font=("Segoe UI", 15, "bold")).pack(anchor="w", padx=10, pady=(10, 4))
        Label(left, textvariable=self.status_var, bg="#111827", fg="#9ca3af").pack(anchor="w", padx=10, pady=(0, 8))
        self.listbox = Listbox(left, bg="#0b1220", fg="#e5e7eb", selectbackground="#1d4ed8", activestyle="none", height=26)
        self.listbox.pack(fill=BOTH, expand=True, padx=10, pady=(0, 8))
        self.listbox.bind("<<ListboxSelect>>", self.on_select)

        row = Frame(left, bg="#111827")
        row.pack(fill=X, padx=10, pady=(0, 10))
        Button(row, text="Refresh", command=self.load_messages).pack(side=LEFT, fill=X, expand=True, padx=(0, 4))
        Button(row, text="Open Folder", command=self.open_folder).pack(side=LEFT, fill=X, expand=True, padx=(4, 0))

        Label(right, text="Message", bg="#0b1220", fg="#93c5fd", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        self.message_box = scrolledtext.ScrolledText(right, wrap="word", bg="#111827", fg="#f9fafb", relief="flat", height=18)
        self.message_box.pack(fill=BOTH, expand=True, pady=(6, 10))

        actions = Frame(right, bg="#0b1220")
        actions.pack(fill=X)
        Button(actions, text="Mark Read", command=lambda: self.set_status("read")).pack(side=LEFT, fill=X, expand=True, padx=(0, 5))
        Button(actions, text="Keep Unread", command=lambda: self.set_status("unread")).pack(side=LEFT, fill=X, expand=True, padx=5)
        Button(actions, text="Archive", command=lambda: self.set_status("archived")).pack(side=LEFT, fill=X, expand=True, padx=(5, 0))

    def load_messages(self) -> None:
        MESSAGES_DIR.mkdir(parents=True, exist_ok=True)
        paths = sorted(MESSAGES_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        self.items = []
        self.listbox.delete(0, END)
        for path in paths:
            data = read_json(path, {})
            if not isinstance(data, dict):
                continue
            self.items.append((path, data))
            message = data.get("message", {})
            text = message.get("message", "") if isinstance(message, dict) else str(message)
            status = data.get("status", "unknown")
            created = data.get("created_at", "")
            self.listbox.insert(END, f"[{status}] {created[:19]} {text[:80]}")
        unread = sum(1 for _, item in self.items if item.get("status") == "unread")
        self.status_var.set(f"{len(self.items)} total, {unread} unread")
        self.message_box.delete("1.0", END)
        self.selected_index = None

    def on_select(self, _event=None) -> None:
        selection = self.listbox.curselection()
        if not selection:
            return
        self.selected_index = int(selection[0])
        path, data = self.items[self.selected_index]
        message = data.get("message", {}) if isinstance(data.get("message"), dict) else {}
        self.message_box.delete("1.0", END)
        self.message_box.insert(END, f"File: {rel(path)}\n")
        self.message_box.insert(END, f"Status: {data.get('status','')}\n")
        self.message_box.insert(END, f"Created: {data.get('created_at','')}\n")
        self.message_box.insert(END, f"Run: {data.get('run_id','')}\n")
        self.message_box.insert(END, f"Urgency: {message.get('urgency','')}\n")
        self.message_box.insert(END, f"Privacy: {message.get('privacy','')}\n")
        self.message_box.insert(END, f"Reason: {message.get('reason','')}\n\n")
        self.message_box.insert(END, message.get("message", ""))

    def selected_item(self) -> tuple[Path, dict] | None:
        if self.selected_index is None or self.selected_index >= len(self.items):
            messagebox.showinfo("No message selected", "Select a message first.")
            return None
        return self.items[self.selected_index]

    def set_status(self, status: str) -> None:
        selected = self.selected_item()
        if not selected:
            return
        path, data = selected
        data["status"] = status
        data["reviewed_at"] = utc_now()
        write_json(path, data)
        index = self.selected_index
        self.load_messages()
        if index is not None and index < self.listbox.size():
            self.listbox.selection_set(index)
            self.listbox.event_generate("<<ListboxSelect>>")

    def open_folder(self) -> None:
        os.startfile(str(MESSAGES_DIR))

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    KiraMessageReviewPanel().run()
