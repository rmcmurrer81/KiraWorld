"""Browse resumable School v2 progress for Kira/Lisa/future AI."""

from __future__ import annotations

import json
import os
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, X, Y, Button, Frame, Label, Listbox, StringVar, Tk
from tkinter import scrolledtext


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROGRESS_PATH = PROJECT_ROOT / "Data" / "school" / "progress" / "school_progress_v2.json"
CURRICULUM_PATH = PROJECT_ROOT / "Data" / "school" / "curriculum" / "legacy_knowledge_curriculum_v1.json"


def read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


class SchoolProgressBrowser:
    def __init__(self) -> None:
        self.root = Tk()
        self.root.title("Kira School Progress")
        self.root.geometry("1100x700")
        self.root.minsize(920, 560)
        self.root.configure(bg="#0b1220")
        self.student = StringVar(value="kira")
        self.status_var = StringVar(value="")
        self.curriculum: dict = {}
        self.progress: dict = {}
        self.rows: list[tuple[dict, dict]] = []
        self.build_ui()
        self.refresh()

    def build_ui(self) -> None:
        outer = Frame(self.root, bg="#0b1220")
        outer.pack(fill=BOTH, expand=True, padx=12, pady=12)
        left = Frame(outer, bg="#111827", bd=1, relief="solid", width=420)
        left.pack(side=LEFT, fill=Y, padx=(0, 12))
        right = Frame(outer, bg="#0b1220")
        right.pack(side=RIGHT, fill=BOTH, expand=True)

        Label(left, text="School Progress", bg="#111827", fg="#f9fafb", font=("Segoe UI", 15, "bold")).pack(anchor="w", padx=10, pady=(10, 4))
        Label(left, textvariable=self.status_var, bg="#111827", fg="#9ca3af").pack(anchor="w", padx=10, pady=(0, 8))

        row = Frame(left, bg="#111827")
        row.pack(fill=X, padx=10, pady=(0, 8))
        for name in ("kira", "lisa", "future_ai"):
            Button(row, text=name.title(), command=lambda value=name: self.set_student(value)).pack(side=LEFT, fill=X, expand=True, padx=2)

        self.listbox = Listbox(left, bg="#0b1220", fg="#e5e7eb", selectbackground="#1d4ed8", activestyle="none")
        self.listbox.pack(fill=BOTH, expand=True, padx=10, pady=(0, 8))
        self.listbox.bind("<<ListboxSelect>>", self.on_select)

        row2 = Frame(left, bg="#111827")
        row2.pack(fill=X, padx=10, pady=(0, 10))
        Button(row2, text="Refresh", command=self.refresh).pack(side=LEFT, fill=X, expand=True, padx=(0, 4))
        Button(row2, text="Open Progress JSON", command=self.open_progress).pack(side=LEFT, fill=X, expand=True, padx=(4, 0))

        Label(right, text="Class Detail", bg="#0b1220", fg="#93c5fd", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        self.detail_box = scrolledtext.ScrolledText(right, wrap="word", bg="#111827", fg="#f9fafb", relief="flat")
        self.detail_box.pack(fill=BOTH, expand=True, pady=(8, 0))

    def set_student(self, value: str) -> None:
        self.student.set(value)
        self.refresh()

    def refresh(self) -> None:
        self.curriculum = read_json(CURRICULUM_PATH, {"classes": []})
        self.progress = read_json(PROGRESS_PATH, {"students": {}})
        student_state = self.progress.get("students", {}).get(self.student.get(), {})
        class_states = student_state.get("classes", {}) if isinstance(student_state, dict) else {}
        classes = [item for item in self.curriculum.get("classes", []) if isinstance(item, dict)]
        self.rows = []
        self.listbox.delete(0, END)
        for item in classes:
            class_id = str(item.get("class_id", ""))
            state = class_states.get(class_id, {}) if isinstance(class_states, dict) else {}
            units = item.get("units", []) if isinstance(item.get("units"), list) else []
            next_index = int(state.get("next_unit_index", 0)) if state else 0
            unit_label = units[next_index % len(units)] if units else "general overview"
            seen = int(state.get("times_seen", 0)) if state else 0
            interest = int(state.get("student_interest", 0)) if state else 0
            pref = state.get("last_preference", "not_seen") if state else "not_seen"
            marker = "core" if item.get("type") == "core" else "elective"
            self.rows.append((item, state))
            self.listbox.insert(END, f"{class_id} [{marker}] seen={seen} interest={interest} pref={pref} next={unit_label[:34]}")
        seen_total = sum(1 for _, state in self.rows if state)
        self.status_var.set(f"{self.student.get().title()} - {seen_total}/{len(classes)} classes seen")
        self.detail_box.delete("1.0", END)
        self.detail_box.insert(END, "Select a class to inspect its resume point, questions, and preferences.\n")

    def on_select(self, _event=None) -> None:
        selection = self.listbox.curselection()
        if not selection:
            return
        item, state = self.rows[int(selection[0])]
        units = item.get("units", []) if isinstance(item.get("units"), list) else []
        next_index = int(state.get("next_unit_index", 0)) if state else 0
        completed = state.get("completed_units", []) if isinstance(state.get("completed_units"), list) else []
        questions = state.get("questions_asked", []) if isinstance(state.get("questions_asked"), list) else []

        self.detail_box.delete("1.0", END)
        self.detail_box.insert(END, f"Class: {item.get('title')} ({item.get('class_id')})\n")
        self.detail_box.insert(END, f"Type: {item.get('type')}\n")
        self.detail_box.insert(END, f"Legacy domain topic map: {item.get('legacy_domain')}\n")
        self.detail_box.insert(END, f"Description: {item.get('description')}\n")
        self.detail_box.insert(END, f"Source policy: {item.get('source_policy')}\n\n")
        self.detail_box.insert(END, "Progress\n")
        self.detail_box.insert(END, f"- times_seen: {state.get('times_seen', 0)}\n")
        self.detail_box.insert(END, f"- next_unit_index: {next_index}\n")
        self.detail_box.insert(END, f"- next_unit: {units[next_index % len(units)] if units else 'general overview'}\n")
        self.detail_box.insert(END, f"- completed_units: {completed}\n")
        self.detail_box.insert(END, f"- last_seen_at: {state.get('last_seen_at', '')}\n")
        self.detail_box.insert(END, f"- student_interest: {state.get('student_interest', 0)}\n")
        self.detail_box.insert(END, f"- last_preference: {state.get('last_preference', '')}\n")
        self.detail_box.insert(END, f"- continue_requested: {state.get('continue_requested', False)}\n")
        self.detail_box.insert(END, f"- occasional_requested: {state.get('occasional_requested', False)}\n")
        self.detail_box.insert(END, f"- switch_requested: {state.get('switch_requested', False)}\n\n")
        self.detail_box.insert(END, "Units\n")
        for index, unit in enumerate(units):
            mark = "done" if index in completed else ("next" if index == next_index else "pending")
            self.detail_box.insert(END, f"- {index}: [{mark}] {unit}\n")
        self.detail_box.insert(END, "\nRecent Questions\n")
        if questions:
            for question in questions[-12:]:
                self.detail_box.insert(END, f"- {question}\n")
        else:
            self.detail_box.insert(END, "- none yet\n")

    def open_progress(self) -> None:
        if PROGRESS_PATH.exists():
            os.startfile(str(PROGRESS_PATH))
        else:
            os.startfile(str(PROGRESS_PATH.parent))

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    SchoolProgressBrowser().run()
