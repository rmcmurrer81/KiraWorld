"""One lightweight front-desk dashboard for Kira review tools."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, X, Button, Frame, Label, StringVar, Tk
from tkinter import messagebox, scrolledtext


PROJECT_ROOT = Path(__file__).resolve().parents[1]
QUESTION_QUEUE_PATH = PROJECT_ROOT / "Data" / "questions" / "kira_questions_for_robert_or_codex.json"
MESSAGES_DIR = PROJECT_ROOT / "Data" / "messages" / "kira_to_robert"
MEMORY_LEDGER_PATH = PROJECT_ROOT / "Data" / "memory_review" / "kira_life_day_review_ledger.json"
SHARED_MEMORY_QUEUE_PATH = PROJECT_ROOT / "Data" / "memory_review" / "shared_memory_review_queue.json"
DEBRIEFS_DIR = PROJECT_ROOT / "Data" / "debriefs"
PREVIEW_CARDS_DIR = PROJECT_ROOT / "Data" / "media" / "preview_cards" / "generated"
HANDOFF_PATH = PROJECT_ROOT / "HANDOFF_FOR_NEXT_CODEX_SESSION.md"
LIFE_RUN_DIR = PROJECT_ROOT / "Data" / "life_sessions"
SCHOOL_RUN_DIR = PROJECT_ROOT / "Data" / "school" / "session_runs"
CHAT_RUN_DIR = PROJECT_ROOT / "Data" / "personhood_evaluations" / "manual_chats"


def read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def run_python(script_name: str) -> None:
    subprocess.Popen(
        ["python", str(PROJECT_ROOT / "tools" / script_name)],
        cwd=str(PROJECT_ROOT),
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )


def open_path(path: Path) -> None:
    if path.exists():
        os.startfile(str(path))
    else:
        path.mkdir(parents=True, exist_ok=True)
        os.startfile(str(path))


def latest_file(directory: Path, pattern: str) -> Path | None:
    if not directory.exists():
        return None
    files = sorted(directory.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


class KiraReviewDashboard:
    def __init__(self) -> None:
        self.root = Tk()
        self.root.title("Kira Review Dashboard")
        self.root.geometry("980x640")
        self.root.minsize(860, 520)
        self.root.configure(bg="#0b1220")
        self.summary_var = StringVar(value="")
        self.build_ui()
        self.refresh()

    def build_ui(self) -> None:
        outer = Frame(self.root, bg="#0b1220")
        outer.pack(fill=BOTH, expand=True, padx=14, pady=14)

        left = Frame(outer, bg="#111827", bd=1, relief="solid", width=330)
        left.pack(side=LEFT, fill=BOTH, padx=(0, 12))
        right = Frame(outer, bg="#0b1220")
        right.pack(side=RIGHT, fill=BOTH, expand=True)

        Label(left, text="Kira Review Dashboard", bg="#111827", fg="#f9fafb", font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=12, pady=(12, 4))
        Label(left, textvariable=self.summary_var, bg="#111827", fg="#9ca3af", justify=LEFT).pack(anchor="w", padx=12, pady=(0, 12))

        self.add_button(left, "Refresh Counts", self.refresh)
        self.add_button(left, "Open Question Review", lambda: run_python("kira_question_review_panel.py"))
        self.add_button(left, "Open Message Review", lambda: run_python("kira_message_review_panel.py"))
        self.add_button(left, "Open Memory Review", lambda: run_python("kira_memory_review_panel.py"))
        self.add_button(left, "Open Shared Memory Review", lambda: run_python("kira_shared_memory_review_panel.py"))
        self.add_button(left, "Open School Progress", lambda: run_python("kira_school_progress_browser.py"))
        self.add_button(left, "Create Latest Debrief", self.create_latest_debrief)
        self.add_button(left, "Create School Assessment", self.create_school_assessment)
        self.add_button(left, "Open Latest Debrief", self.open_latest_debrief)
        self.add_button(left, "Open Latest Life Monitor", lambda: self.open_latest_in(LIFE_RUN_DIR, "*.monitor.md"))
        self.add_button(left, "Open Latest School Monitor", lambda: self.open_latest_in(SCHOOL_RUN_DIR, "*.monitor.md"))
        self.add_button(left, "Open Latest Chat Monitor", lambda: self.open_latest_in(CHAT_RUN_DIR, "*.monitor.md"))
        self.add_button(left, "Open Media Preview Cards", lambda: open_path(PREVIEW_CARDS_DIR))
        self.add_button(left, "Build Media Lookup Queue", lambda: run_python("build_media_lookup_queue.py"))
        self.add_button(left, "Open Handoff", lambda: open_path(HANDOFF_PATH))

        Label(right, text="Review Snapshot", bg="#0b1220", fg="#93c5fd", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        self.snapshot_box = scrolledtext.ScrolledText(right, wrap="word", bg="#111827", fg="#f9fafb", relief="flat")
        self.snapshot_box.pack(fill=BOTH, expand=True, pady=(8, 0))

    def add_button(self, parent: Frame, text: str, command) -> None:
        Button(parent, text=text, command=command).pack(fill=X, padx=12, pady=4)

    def refresh(self) -> None:
        question_count, open_question_count = self.question_counts()
        message_count, unread_message_count = self.message_counts()
        memory_count, needs_memory_count = self.memory_counts()
        shared_count, shared_needs_count = self.shared_memory_counts()
        debrief = latest_file(DEBRIEFS_DIR, "*.debrief.md")
        latest_life = latest_file(LIFE_RUN_DIR, "*.monitor.md")
        latest_school = latest_file(SCHOOL_RUN_DIR, "*.monitor.md")
        latest_chat = latest_file(CHAT_RUN_DIR, "*.monitor.md")
        preview_count = len(list(PREVIEW_CARDS_DIR.glob("*.json"))) if PREVIEW_CARDS_DIR.exists() else 0

        self.summary_var.set(
            f"Open questions: {open_question_count}\n"
            f"Unread messages: {unread_message_count}\n"
            f"Memory items needing review: {needs_memory_count}\n"
            f"Shared memories needing review: {shared_needs_count}\n"
            f"Preview cards: {preview_count}"
        )

        self.snapshot_box.delete("1.0", END)
        self.snapshot_box.insert(END, "Counts\n")
        self.snapshot_box.insert(END, f"- Questions: {question_count} total, {open_question_count} open/deferred\n")
        self.snapshot_box.insert(END, f"- Messages: {message_count} total, {unread_message_count} unread\n")
        self.snapshot_box.insert(END, f"- Memory/privacy candidates: {memory_count} total, {needs_memory_count} need review\n")
        self.snapshot_box.insert(END, f"- Shared memory candidates: {shared_count} total, {shared_needs_count} need review\n")
        self.snapshot_box.insert(END, f"- Media preview cards: {preview_count} generated drafts\n\n")
        self.snapshot_box.insert(END, "Latest Debrief\n")
        self.snapshot_box.insert(END, f"- {debrief.name if debrief else 'none yet'}\n\n")
        self.snapshot_box.insert(END, "Latest Logs\n")
        self.snapshot_box.insert(END, f"- life: {latest_life.name if latest_life else 'none yet'}\n")
        self.snapshot_box.insert(END, f"- school: {latest_school.name if latest_school else 'none yet'}\n")
        self.snapshot_box.insert(END, f"- chat: {latest_chat.name if latest_chat else 'none yet'}\n\n")
        self.snapshot_box.insert(END, "Suggested Review Order\n")
        self.snapshot_box.insert(END, "1. Questions: answer anything Kira/Lisa explicitly carried forward.\n")
        self.snapshot_box.insert(END, "2. Messages: read or archive notes Kira intentionally left for Robert.\n")
        self.snapshot_box.insert(END, "3. Memory/privacy: label candidates without promoting them automatically.\n")
        self.snapshot_box.insert(END, "4. Shared memory: require Kira, Lisa, and Robert/Codex review before any promotion.\n")
        self.snapshot_box.insert(END, "5. Debrief: create one after meaningful school/life/chat runs.\n")

    def question_counts(self) -> tuple[int, int]:
        queue = read_json(QUESTION_QUEUE_PATH, {"questions": []})
        questions = queue.get("questions", []) if isinstance(queue, dict) else []
        questions = [q for q in questions if isinstance(q, dict)]
        open_count = sum(1 for q in questions if q.get("status") in {"open", "deferred"})
        return len(questions), open_count

    def message_counts(self) -> tuple[int, int]:
        if not MESSAGES_DIR.exists():
            return 0, 0
        items = []
        for path in MESSAGES_DIR.glob("*.json"):
            data = read_json(path, {})
            if isinstance(data, dict):
                items.append(data)
        unread = sum(1 for item in items if item.get("status") == "unread")
        return len(items), unread

    def memory_counts(self) -> tuple[int, int]:
        ledger = read_json(MEMORY_LEDGER_PATH, {"entries": []})
        entries = ledger.get("entries", []) if isinstance(ledger, dict) else []
        entries = [entry for entry in entries if isinstance(entry, dict)]
        needs = sum(1 for entry in entries if entry.get("needs_review", True))
        return len(entries), needs

    def shared_memory_counts(self) -> tuple[int, int]:
        queue = read_json(SHARED_MEMORY_QUEUE_PATH, {"items": []})
        items = queue.get("items", []) if isinstance(queue, dict) else []
        items = [item for item in items if isinstance(item, dict)]
        needs = sum(
            1
            for item in items
            if item.get("status") != "ready_for_smallest_shared_layer"
            or item.get("promotion_status") not in {"reviewed_not_promoted", "promoted"}
        )
        return len(items), needs

    def create_latest_debrief(self) -> None:
        subprocess.Popen(
            ["python", str(PROJECT_ROOT / "tools" / "create_kira_session_debrief.py")],
            cwd=str(PROJECT_ROOT),
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
        messagebox.showinfo("Debrief started", "A console opened to create the latest debrief.")

    def create_school_assessment(self) -> None:
        subprocess.Popen(
            ["python", str(PROJECT_ROOT / "tools" / "create_kira_school_assessment.py")],
            cwd=str(PROJECT_ROOT),
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
        messagebox.showinfo("Assessment started", "A console opened to create the latest school assessment.")

    def open_latest_debrief(self) -> None:
        debrief = latest_file(DEBRIEFS_DIR, "*.debrief.md")
        if debrief:
            open_path(debrief)
        else:
            messagebox.showinfo("No debrief", "No debrief file exists yet. Click Create Latest Debrief first.")

    def open_latest_in(self, directory: Path, pattern: str) -> None:
        target = latest_file(directory, pattern)
        if target:
            open_path(target)
        else:
            messagebox.showinfo("No file", f"No {pattern} file exists in {directory}.")

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    KiraReviewDashboard().run()
