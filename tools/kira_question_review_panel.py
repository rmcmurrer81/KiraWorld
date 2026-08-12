"""Small question review panel for Kira/Lisa school questions."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, X, Y, Button, Frame, Label, Listbox, StringVar, Tk
from tkinter import messagebox, scrolledtext

from run_kira_school_v2 import local_source_snippets, teacher_answer


PROJECT_ROOT = Path(__file__).resolve().parents[1]
QUESTION_QUEUE_PATH = PROJECT_ROOT / "Data" / "questions" / "kira_questions_for_robert_or_codex.json"
SCHOOL_RUN_DIR = PROJECT_ROOT / "Data" / "school" / "session_runs"


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


class QuestionReviewPanel:
    def __init__(self) -> None:
        self.root = Tk()
        self.root.title("Kira/Lisa Question Review")
        self.root.geometry("1120x720")
        self.root.minsize(940, 560)
        self.root.configure(bg="#0b1220")
        self.queue: dict = {}
        self.questions: list[dict] = []
        self.all_questions: list[dict] = []
        self.selected_index: int | None = None
        self.filter_mode = StringVar(value="open")
        self.status_var = StringVar(value="")
        self.build_ui()
        self.load_questions()

    def build_ui(self) -> None:
        outer = Frame(self.root, bg="#0b1220")
        outer.pack(fill=BOTH, expand=True, padx=12, pady=12)

        left = Frame(outer, bg="#111827", bd=1, relief="solid", width=390)
        left.pack(side=LEFT, fill=Y, padx=(0, 12))
        right = Frame(outer, bg="#0b1220")
        right.pack(side=RIGHT, fill=BOTH, expand=True)

        Label(left, text="Open Questions", bg="#111827", fg="#f9fafb", font=("Segoe UI", 15, "bold")).pack(anchor="w", padx=10, pady=(10, 4))
        Label(left, textvariable=self.status_var, bg="#111827", fg="#9ca3af").pack(anchor="w", padx=10, pady=(0, 8))
        self.listbox = Listbox(left, bg="#0b1220", fg="#e5e7eb", selectbackground="#1d4ed8", activestyle="none", height=26)
        self.listbox.pack(fill=BOTH, expand=True, padx=10, pady=(0, 8))
        self.listbox.bind("<<ListboxSelect>>", self.on_select)

        btns = Frame(left, bg="#111827")
        btns.pack(fill=X, padx=10, pady=(0, 10))
        Button(btns, text="Refresh", command=self.load_questions).pack(side=LEFT, fill=X, expand=True, padx=(0, 4))
        Button(btns, text="Open Queue File", command=self.open_queue_file).pack(side=LEFT, fill=X, expand=True, padx=(4, 0))

        filters = Frame(left, bg="#111827")
        filters.pack(fill=X, padx=10, pady=(0, 10))
        Button(filters, text="Open/Deferred", command=lambda: self.set_filter("open")).pack(side=LEFT, fill=X, expand=True, padx=(0, 4))
        Button(filters, text="Answered", command=lambda: self.set_filter("answered")).pack(side=LEFT, fill=X, expand=True, padx=4)
        Button(filters, text="All", command=lambda: self.set_filter("all")).pack(side=LEFT, fill=X, expand=True, padx=(4, 0))

        Label(right, text="Question", bg="#0b1220", fg="#93c5fd", font=("Segoe UI", 12, "bold")).pack(anchor="w")
        self.question_box = scrolledtext.ScrolledText(right, wrap="word", height=6, bg="#111827", fg="#f9fafb", relief="flat")
        self.question_box.pack(fill=X, pady=(6, 10))

        Label(right, text="Context", bg="#0b1220", fg="#c4b5fd", font=("Segoe UI", 12, "bold")).pack(anchor="w")
        self.context_box = scrolledtext.ScrolledText(right, wrap="word", height=10, bg="#111827", fg="#d1d5db", relief="flat")
        self.context_box.pack(fill=X, pady=(6, 10))

        Label(right, text="Answer / Review Note", bg="#0b1220", fg="#fbbf24", font=("Segoe UI", 12, "bold")).pack(anchor="w")
        self.answer_box = scrolledtext.ScrolledText(right, wrap="word", height=10, bg="#111827", fg="#f9fafb", relief="flat")
        self.answer_box.pack(fill=BOTH, expand=True, pady=(6, 10))

        actions = Frame(right, bg="#0b1220")
        actions.pack(fill=X)
        Button(actions, text="Draft Local Answer", command=self.draft_local_answer).pack(side=LEFT, fill=X, expand=True, padx=(0, 5))
        Button(actions, text="Save Answer + Mark Answered", command=self.mark_answered).pack(side=LEFT, fill=X, expand=True, padx=5)
        Button(actions, text="Mark Deferred", command=lambda: self.set_status("deferred")).pack(side=LEFT, fill=X, expand=True, padx=5)
        Button(actions, text="Mark Open", command=lambda: self.set_status("open")).pack(side=LEFT, fill=X, expand=True, padx=5)
        Button(actions, text="Mark Not Needed", command=lambda: self.set_status("not_needed")).pack(side=LEFT, fill=X, expand=True, padx=(5, 0))
        actions2 = Frame(right, bg="#0b1220")
        actions2.pack(fill=X, pady=(6, 0))
        Button(actions2, text="Draft Research Needed", command=self.draft_research_needed).pack(side=LEFT, fill=X, expand=True, padx=(0, 5))
        Button(actions2, text="Open Related Monitor", command=self.open_related_monitor).pack(side=LEFT, fill=X, expand=True, padx=5)
        Button(actions2, text="Open Latest School Monitor", command=self.open_latest_school_monitor).pack(side=LEFT, fill=X, expand=True, padx=(5, 0))

    def load_questions(self) -> None:
        self.queue = read_json(QUESTION_QUEUE_PATH, {"questions": []})
        all_questions = self.queue.get("questions", []) if isinstance(self.queue, dict) else []
        self.all_questions = [q for q in all_questions if isinstance(q, dict)]
        self.questions = self.filtered_questions()
        self.listbox.delete(0, END)
        for q in self.questions:
            status = q.get("status", "open")
            owner = q.get("owner", "?")
            text = q.get("question", "").replace("\n", " ")
            self.listbox.insert(END, f"[{status}] {owner}: {text[:95]}")
        open_count = sum(1 for q in self.all_questions if q.get("status") in {"open", "deferred"})
        self.status_var.set(f"{len(self.all_questions)} total, {open_count} open/deferred, showing {self.filter_mode.get()}")
        self.clear_detail()

    def filtered_questions(self) -> list[dict]:
        mode = self.filter_mode.get()
        if mode == "all":
            return list(self.all_questions)
        if mode == "answered":
            return [q for q in self.all_questions if q.get("status") in {"answered", "not_needed"}]
        return [q for q in self.all_questions if q.get("status") in {"open", "deferred"}]

    def set_filter(self, mode: str) -> None:
        self.filter_mode.set(mode)
        self.load_questions()

    def clear_detail(self) -> None:
        self.selected_index = None
        for box in (self.question_box, self.context_box, self.answer_box):
            box.configure(state="normal")
            box.delete("1.0", END)

    def on_select(self, _event=None) -> None:
        selection = self.listbox.curselection()
        if not selection:
            return
        self.selected_index = int(selection[0])
        q = self.questions[self.selected_index]
        contexts = q.get("contexts", []) if isinstance(q.get("contexts"), list) else []
        latest_context = contexts[-1] if contexts else {}
        answer = q.get("answer", {}) if isinstance(q.get("answer"), dict) else {}

        self.question_box.delete("1.0", END)
        self.question_box.insert(END, f"ID: {q.get('question_id','')}\n")
        self.question_box.insert(END, f"Owner: {q.get('owner','')}\n")
        self.question_box.insert(END, f"Status: {q.get('status','')}\n")
        self.question_box.insert(END, f"Run: {latest_context.get('run_id','')}\n")
        self.question_box.insert(END, f"Source: {latest_context.get('source_title','')}\n\n")
        self.question_box.insert(END, q.get("question", ""))

        self.context_box.delete("1.0", END)
        self.context_box.insert(END, latest_context.get("context", ""))

        self.answer_box.delete("1.0", END)
        self.answer_box.insert(END, answer.get("text", ""))

    def latest_context_for(self, q: dict) -> dict:
        contexts = q.get("contexts", []) if isinstance(q.get("contexts"), list) else []
        return contexts[-1] if contexts and isinstance(contexts[-1], dict) else {}

    def selected_question(self) -> dict | None:
        if self.selected_index is None or self.selected_index >= len(self.questions):
            messagebox.showinfo("No question selected", "Select a question first.")
            return None
        return self.questions[self.selected_index]

    def save_queue(self) -> None:
        self.queue["updated_at"] = utc_now()
        write_json(QUESTION_QUEUE_PATH, self.queue)
        current = self.selected_index
        self.load_questions()
        if current is not None and current < self.listbox.size():
            self.listbox.selection_set(current)
            self.listbox.event_generate("<<ListboxSelect>>")

    def mark_answered(self) -> None:
        q = self.selected_question()
        if not q:
            return
        answer = self.answer_box.get("1.0", END).strip()
        if not answer:
            messagebox.showinfo("Empty answer", "Write an answer or review note first.")
            return
        q["status"] = "answered"
        q["answer"] = {
            "answered_at": utc_now(),
            "answered_by": "Robert/Codex review panel",
            "text": answer,
            "source_links": q.get("draft_source_links", []),
        }
        self.save_queue()

    def draft_local_answer(self) -> None:
        q = self.selected_question()
        if not q:
            return
        question = q.get("question", "").strip()
        if not question:
            messagebox.showinfo("No question text", "This question entry has no question text.")
            return
        latest_context = self.latest_context_for(q)
        source_title = latest_context.get("source_title", "")
        class_title = source_title.split("school_v2:", 1)[-1].replace("_", " ").strip() or "review question"
        snippets = local_source_snippets(question, limit=2)
        answer = teacher_answer(
            question,
            {"title": class_title},
            latest_context.get("source_title", ""),
            snippets=snippets,
        )
        q["draft_source_links"] = [item.get("path", "") for item in snippets if item.get("path")]
        draft = (
            "[Draft from local project/source notes. Edit before saving if needed.]\n\n"
            + answer
        )
        if snippets:
            draft += "\n\nSource notes used:\n"
            for item in snippets:
                draft += f"- {item.get('path', '')}: {item.get('snippet', '')[:260]}\n"
        self.answer_box.delete("1.0", END)
        self.answer_box.insert(END, draft)

    def draft_research_needed(self) -> None:
        q = self.selected_question()
        if not q:
            return
        latest_context = self.latest_context_for(q)
        text = (
            "Source says: The current class/session raised this as a real question, but the shown source context does not fully answer it.\n"
            "General knowledge says: It may have an answer, but it should be checked against a reliable source before Kira or Lisa use it as fact.\n"
            "My interpretation: Keep this as an open learning question rather than turning it into memory or a confident claim.\n"
            "Research needed: Ask Robert/Codex later, or add a reviewed source card/class note that directly answers it.\n\n"
            f"Related run: {latest_context.get('run_id', '')}\n"
            f"Related source: {latest_context.get('source_title', '')}\n"
        )
        self.answer_box.delete("1.0", END)
        self.answer_box.insert(END, text)

    def set_status(self, status: str) -> None:
        q = self.selected_question()
        if not q:
            return
        q["status"] = status
        if status == "not_needed":
            q.setdefault("answer", {})["answered_at"] = utc_now()
            q.setdefault("answer", {})["answered_by"] = "Robert/Codex review panel"
            q.setdefault("answer", {})["text"] = self.answer_box.get("1.0", END).strip()
        self.save_queue()

    def open_queue_file(self) -> None:
        if QUESTION_QUEUE_PATH.exists():
            os.startfile(str(QUESTION_QUEUE_PATH))
        else:
            os.startfile(str(QUESTION_QUEUE_PATH.parent))

    def open_related_monitor(self) -> None:
        q = self.selected_question()
        if not q:
            return
        run_id = self.latest_context_for(q).get("run_id", "")
        if not run_id:
            messagebox.showinfo("No run ID", "This question does not have a related run ID.")
            return
        candidates = list(SCHOOL_RUN_DIR.glob(f"{run_id}*.monitor.md")) + list(SCHOOL_RUN_DIR.glob(f"{run_id}*_report.md"))
        if not candidates:
            messagebox.showinfo("Monitor not found", f"No monitor found for {run_id}.")
            return
        os.startfile(str(max(candidates, key=lambda p: p.stat().st_mtime)))

    def open_latest_school_monitor(self) -> None:
        if not SCHOOL_RUN_DIR.exists():
            os.startfile(str(SCHOOL_RUN_DIR.parent))
            return
        candidates = list(SCHOOL_RUN_DIR.glob("*.monitor.md")) + list(SCHOOL_RUN_DIR.glob("*_report.md"))
        if not candidates:
            os.startfile(str(SCHOOL_RUN_DIR))
            return
        os.startfile(str(max(candidates, key=lambda p: p.stat().st_mtime)))

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    QuestionReviewPanel().run()
