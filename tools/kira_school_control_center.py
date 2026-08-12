"""Lightweight school control center for Kira/Lisa pre-GPU classes."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, X, Y, Button, Frame, Label, StringVar, Tk
from tkinter import messagebox, scrolledtext


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHOOL_RUN_DIR = PROJECT_ROOT / "Data" / "school" / "session_runs"
PRESENCE_DIR = PROJECT_ROOT / "Data" / "presence"
CURRENT_SCHOOL_RUN_PATH = PRESENCE_DIR / "current_kira_school_run.json"
SCHOOL_STOP_PATH = PRESENCE_DIR / "kira_school_stop.json"
SCHOOL_PAUSE_PATH = PRESENCE_DIR / "kira_school_pause.json"
QUESTION_QUEUE_PATH = PROJECT_ROOT / "Data" / "questions" / "kira_questions_for_robert_or_codex.json"
STUDENT_CHOICE_QUEUE_PATH = PROJECT_ROOT / "Data" / "school" / "student_state" / "student_choice_queue.json"
OLLAMA_EXE = Path(os.getenv("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"
OLLAMA_TAGS_ENDPOINT = "http://localhost:11434/api/tags"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def local_time() -> str:
    return datetime.now().strftime("%H:%M:%S")


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


def now_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def ollama_reachable(timeout: float = 4.0) -> bool:
    try:
        with urllib.request.urlopen(OLLAMA_TAGS_ENDPOINT, timeout=timeout) as response:
            return 200 <= response.status < 300
    except (OSError, urllib.error.URLError):
        return False


def start_ollama_server() -> bool:
    if ollama_reachable(timeout=2.0):
        return True
    if not OLLAMA_EXE.exists():
        return False
    startupinfo = None
    creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0
        creationflags |= getattr(subprocess, "CREATE_NO_WINDOW", 0)
    subprocess.Popen(
        [str(OLLAMA_EXE), "serve"],
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        startupinfo=startupinfo,
        creationflags=creationflags,
    )
    deadline = time.time() + 25
    while time.time() < deadline:
        if ollama_reachable(timeout=2.0):
            return True
        time.sleep(1)
    return False


def latest_school_json() -> Path | None:
    current = read_json(CURRENT_SCHOOL_RUN_PATH, {})
    expected = current.get("expected_json") if isinstance(current, dict) else ""
    expected_path = PROJECT_ROOT / expected if expected else None
    if expected_path and expected_path.exists():
        return expected_path
    if not SCHOOL_RUN_DIR.exists():
        return None
    candidates = list(SCHOOL_RUN_DIR.glob("*school_v2*.json"))
    if not candidates:
        candidates = list(SCHOOL_RUN_DIR.glob("kira_school*.json"))
    return max(candidates, key=lambda p: p.stat().st_mtime) if candidates else None


def monitor_for(json_path: Path | None) -> Path | None:
    if not json_path:
        return None
    monitor = json_path.with_suffix(".monitor.md")
    if monitor.exists():
        return monitor
    alt = json_path.with_name(json_path.stem + "_report.md")
    return alt if alt.exists() else None


def school_processes(run_id: str = "") -> list[dict]:
    if os.name != "nt":
        return []
    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'run_kira_school_v2.py' -and $_.CommandLine -notmatch 'Get-CimInstance' -and $_.CommandLine -notmatch 'ConvertTo-Json' } | Select-Object ProcessId,CommandLine | ConvertTo-Json -Depth 3",
            ],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=8,
        )
        if not result.stdout.strip():
            return []
        data = json.loads(result.stdout)
        if isinstance(data, dict):
            processes = [data]
        else:
            processes = data if isinstance(data, list) else []
        if run_id:
            processes = [item for item in processes if run_id in str(item.get("CommandLine", ""))]
        return processes
    except Exception:
        return []


def school_status_label(status: str, processes: list[dict], records: list[dict], run_id: str) -> tuple[str, str]:
    terminal_statuses = {"completed", "stopped_safely", "stopped_by_request", "failed", "error", "interrupted"}
    normalized = status or "not started"
    if normalized in terminal_statuses:
        if processes:
            return f"{normalized} (process finishing)", "stopping/finishing"
        return normalized, "stopped"
    if stop_requested_for(run_id):
        if processes:
            return "stop requested", "stopping at class boundary"
        return "stop requested", "not detected"
    if processes:
        if records:
            return normalized, "running/thinking"
        return "starting", "running/no lesson yet"
    if normalized == "running":
        return "running (stale/no matching process)", "not detected"
    if run_id and not records:
        return normalized, "not detected/no lesson yet"
    return normalized, "not detected"


def stop_requested_for(run_id: str) -> bool:
    data = read_json(SCHOOL_STOP_PATH, {})
    if not isinstance(data, dict) or not data:
        return False
    target = str(data.get("run_id", "any"))
    return target in {"", "any", run_id}


class KiraSchoolControlCenter:
    def __init__(self) -> None:
        self.root = Tk()
        self.root.title("Kira School Control Center")
        self.root.geometry("1180x760")
        self.root.minsize(980, 620)
        self.root.configure(bg="#0b1220")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.student = StringVar(value="kira")
        self.duration = StringVar(value="9")
        self.status_vars: dict[str, StringVar] = {}
        self.event_lines: list[str] = []
        self.last_status_text = ""
        self.build_ui()
        self.log("Panel ready. 3/6/9-hour buttons now mean full-duration supervised school, not only 3/6/9 blocks.")
        self.refresh_status()
        self.root.after(15000, self.periodic_refresh)

    def build_ui(self) -> None:
        outer = Frame(self.root, bg="#0b1220")
        outer.pack(fill=BOTH, expand=True, padx=14, pady=14)

        left = Frame(outer, bg="#111827", bd=1, relief="solid", width=360)
        left.pack(side=LEFT, fill=Y, padx=(0, 12))
        center = Frame(outer, bg="#0b1220")
        center.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 12))
        right = Frame(outer, bg="#111827", bd=1, relief="solid", width=360)
        right.pack(side=RIGHT, fill=Y)

        Label(left, text="Kira School Control Center", fg="#f9fafb", bg="#111827", font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=12, pady=(12, 2))
        Label(left, text="Chat disabled during school. Questions are logged for review.", fg="#fbbf24", bg="#111827", wraplength=310, justify=LEFT).pack(anchor="w", padx=12, pady=(0, 14))

        self.section_label(left, "Select Student")
        self.button_row(left, [("Kira", lambda: self.set_student("kira")), ("Lisa", lambda: self.set_student("lisa"))])
        Label(left, text="Pre-GPU recommendation: run one student at a time. Future AI slots stay for later.", fg="#9ca3af", bg="#111827", wraplength=310, justify=LEFT).pack(anchor="w", padx=12, pady=(0, 14))

        self.section_label(left, "Session Duration")
        self.button_row(left, [("3 Hours", lambda: self.set_duration("3")), ("6 Hours", lambda: self.set_duration("6")), ("9 Hours", lambda: self.set_duration("9"))])

        self.section_label(left, "Main Controls")
        self.button_row(left, [("Start School", self.start_school)])
        self.button_row(left, [("Pause", self.pause_school), ("Resume", self.resume_school)])
        self.button_row(left, [("Check Status", self.refresh_status), ("End Safely", self.end_safely)])
        self.button_row(left, [("Open Monitor", self.open_monitor), ("Open Questions", self.open_questions)])
        self.button_row(left, [("Open Student Choices", self.open_student_choices), ("Open Process Log", self.open_process_log)])

        Label(center, text="Current Lesson", fg="#c4b5fd", bg="#0b1220", font=("Segoe UI", 14, "bold")).pack(anchor="w")
        self.lesson_box = scrolledtext.ScrolledText(center, wrap="word", bg="#111827", fg="#e5e7eb", relief="flat", font=("Segoe UI", 10), height=13)
        self.lesson_box.pack(fill=X, pady=(8, 12))
        self.lesson_box.insert(END, "School v2 will show the latest class here after the run writes its JSON.\n")
        self.lesson_box.configure(state="disabled")

        Label(center, text="School Session Events", fg="#93c5fd", bg="#0b1220", font=("Segoe UI", 14, "bold")).pack(anchor="w")
        self.event_log = scrolledtext.ScrolledText(center, wrap="word", bg="#111827", fg="#d1d5db", relief="flat", font=("Consolas", 9))
        self.event_log.pack(fill=BOTH, expand=True, pady=(8, 0))

        Label(right, text="Session Status", fg="#f9fafb", bg="#111827", font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=12, pady=(12, 6))
        for key, label in [
            ("student", "Student"),
            ("run_id", "Current run ID"),
            ("status", "Status"),
            ("blocks", "Blocks done"),
            ("duration", "Duration"),
            ("latest_class", "Latest class"),
            ("latest_unit", "Latest unit"),
            ("questions", "Open questions"),
            ("choices", "Active choices"),
            ("process", "Process"),
        ]:
            row = Frame(right, bg="#111827")
            row.pack(fill=X, padx=12, pady=4)
            Label(row, text=label, fg="#9ca3af", bg="#111827", width=14, anchor="w").pack(side=LEFT)
            var = StringVar(value="")
            self.status_vars[key] = var
            Label(row, textvariable=var, fg="#f9fafb", bg="#111827", anchor="w", wraplength=190, justify=LEFT).pack(side=LEFT, fill=X, expand=True)

    def section_label(self, parent: Frame, text: str) -> None:
        Label(parent, text=text, fg="#f9fafb", bg="#111827", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=12, pady=(12, 6))

    def button_row(self, parent: Frame, buttons: list[tuple[str, object]]) -> None:
        row = Frame(parent, bg="#111827")
        row.pack(fill=X, padx=12, pady=4)
        for text, command in buttons:
            Button(row, text=text, command=command, height=2).pack(side=LEFT, fill=X, expand=True, padx=(0, 6))

    def set_student(self, value: str) -> None:
        self.student.set(value)
        self.log(f"Selected student: {value.title()}.")
        self.refresh_status()

    def set_duration(self, hours: str) -> None:
        self.duration.set(hours)
        self.log(f"Selected duration: {hours} hours.")
        self.refresh_status()

    def log(self, text: str) -> None:
        line = f"[{local_time()}] {text}"
        self.event_lines.append(line)
        self.event_lines = self.event_lines[-200:]
        if hasattr(self, "event_log"):
            self.event_log.insert(END, line + "\n")
            self.event_log.see(END)

    def start_school(self) -> None:
        if not start_ollama_server():
            self.log("Cannot start school: Ollama is offline and could not be started automatically.")
            messagebox.showerror("Ollama offline", "The local Ollama model server is not reachable. Start Ollama, then try again.")
            self.refresh_status()
            return
        student = self.student.get()
        hours = int(self.duration.get())
        blocks = max(3, hours)
        run_id = f"{student}_school_v2_{hours}hour_{now_id()}"
        for path in (SCHOOL_STOP_PATH, SCHOOL_PAUSE_PATH):
            if path.exists():
                path.unlink()
        cmd = [
            sys.executable,
            "tools\\run_kira_school_v2.py",
            "--student",
            student,
            "--blocks",
            str(blocks),
            "--duration-minutes",
            str(hours * 60),
            "--run-until-duration",
            "--answer-questions",
            "--backend",
            "ollama",
            "--run-id",
            run_id,
        ]
        log_path = SCHOOL_RUN_DIR / f"{run_id}.process.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_handle = log_path.open("a", encoding="utf-8")
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        proc = subprocess.Popen(cmd, cwd=str(PROJECT_ROOT), stdout=log_handle, stderr=subprocess.STDOUT, text=True, creationflags=creationflags)
        write_json(
            CURRENT_SCHOOL_RUN_PATH,
            {
                "run_id": run_id,
                "student": student,
                "started_at": utc_now(),
                "expected_json": rel(SCHOOL_RUN_DIR / f"{run_id}.json"),
                "expected_monitor": rel(SCHOOL_RUN_DIR / f"{run_id}.monitor.md"),
                "process_log": rel(log_path),
                "pid": proc.pid,
                "duration_hours": hours,
            },
        )
        self.log(f"Started {hours}-hour school for {student.title()} as {run_id} pid={proc.pid}.")
        self.log(f"Process log: {rel(log_path)}")
        self.root.after(4000, self.refresh_status)

    def pause_school(self) -> None:
        write_json(SCHOOL_PAUSE_PATH, {"status": "pause_requested", "requested_at": utc_now(), "reason": "Robert clicked Pause in school control center."})
        self.log("Pause requested. The school runner pauses between class blocks.")
        self.refresh_status()

    def resume_school(self) -> None:
        if SCHOOL_PAUSE_PATH.exists():
            SCHOOL_PAUSE_PATH.unlink()
        self.log("Resume requested. Pause signal cleared.")
        self.refresh_status()

    def end_safely(self) -> None:
        if not messagebox.askyesno("End safely", "Ask the school session to stop at the next class boundary?"):
            return
        current = read_json(CURRENT_SCHOOL_RUN_PATH, {})
        run_id = current.get("run_id", "any") if isinstance(current, dict) else "any"
        write_json(SCHOOL_STOP_PATH, {"status": "stop_requested", "requested_at": utc_now(), "run_id": run_id, "reason": "Robert clicked End Safely in school control center."})
        self.log(f"Safe stop requested for {run_id}. The current class may finish before the process exits.")
        self.refresh_status()

    def open_monitor(self) -> None:
        monitor = monitor_for(latest_school_json())
        if not monitor:
            self.log("No school monitor found yet.")
            return
        os.startfile(str(monitor))
        self.log(f"Opened monitor: {rel(monitor)}")

    def open_questions(self) -> None:
        QUESTION_QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
        if QUESTION_QUEUE_PATH.exists():
            os.startfile(str(QUESTION_QUEUE_PATH))
        else:
            os.startfile(str(QUESTION_QUEUE_PATH.parent))
        self.log("Opened question queue location.")

    def open_student_choices(self) -> None:
        STUDENT_CHOICE_QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
        if STUDENT_CHOICE_QUEUE_PATH.exists():
            os.startfile(str(STUDENT_CHOICE_QUEUE_PATH))
        else:
            os.startfile(str(STUDENT_CHOICE_QUEUE_PATH.parent))
        self.log("Opened student choice queue.")

    def open_process_log(self) -> None:
        current = read_json(CURRENT_SCHOOL_RUN_PATH, {})
        process_log = current.get("process_log", "") if isinstance(current, dict) else ""
        path = PROJECT_ROOT / process_log if process_log else None
        if path and path.exists():
            os.startfile(str(path))
            self.log(f"Opened process log: {rel(path)}")
            return
        if not SCHOOL_RUN_DIR.exists():
            self.log("No school process log folder found yet.")
            return
        candidates = list(SCHOOL_RUN_DIR.glob("*.process.log"))
        if not candidates:
            self.log("No school process log found yet.")
            return
        latest = max(candidates, key=lambda p: p.stat().st_mtime)
        os.startfile(str(latest))
        self.log(f"Opened latest process log: {rel(latest)}")

    def refresh_status(self) -> None:
        current = read_json(CURRENT_SCHOOL_RUN_PATH, {})
        json_path = latest_school_json()
        report = read_json(json_path, {}) if json_path else {}
        records = report.get("records", []) if isinstance(report.get("records"), list) else []
        latest = records[-1] if records else {}
        current_run_id = current.get("run_id", "") if isinstance(current, dict) else ""
        run_id = str(report.get("run_id") or current_run_id)
        processes = school_processes(run_id)
        status = str(report.get("status", "not started"))
        status, process_label = school_status_label(status, processes, records, run_id)
        questions = read_json(QUESTION_QUEUE_PATH, {})
        open_questions = [
            item for item in questions.get("questions", [])
            if isinstance(item, dict) and item.get("status") in {"open", "deferred"}
        ] if isinstance(questions, dict) else []
        choices = read_json(STUDENT_CHOICE_QUEUE_PATH, {})
        student_key = self.student.get().lower()
        active_choices = [
            item for item in choices.get("students", {}).get(student_key, [])
            if isinstance(item, dict) and str(item.get("status", "active")).lower() in {"active", "requested", "continue"}
        ] if isinstance(choices, dict) else []
        values = {
            "student": self.student.get().title(),
            "run_id": run_id or "none",
            "status": status,
            "blocks": str(len(records)),
            "duration": f"{self.duration.get()} hours selected",
            "latest_class": latest.get("class_title", ""),
            "latest_unit": latest.get("unit", ""),
            "questions": str(len(open_questions)),
            "choices": str(len(active_choices)),
            "process": process_label,
        }
        for key, value in values.items():
            self.status_vars[key].set(str(value))
        status_text = f"{values['run_id']} status={values['status']} process={values['process']} blocks={values['blocks']}"
        if status_text != self.last_status_text:
            self.log(f"Status: {status_text}")
            self.last_status_text = status_text
        self.update_lesson_box(report, latest)

    def update_lesson_box(self, report: dict, latest: dict) -> None:
        self.lesson_box.configure(state="normal")
        self.lesson_box.delete("1.0", END)
        if not latest:
            self.lesson_box.insert(END, "No current lesson has been written yet.\n")
        else:
            self.lesson_box.insert(END, f"{latest.get('class_title', 'Class')}\n\n")
            self.lesson_box.insert(END, f"Unit: {latest.get('unit', '')}\n\n")
            response = str(latest.get("response", "")).strip()
            if response:
                self.lesson_box.insert(END, "Latest response:\n")
                self.lesson_box.insert(END, response[:1800])
            qs = latest.get("questions", [])
            if qs:
                self.lesson_box.insert(END, "\n\nQuestions logged:\n")
                for q in qs:
                    self.lesson_box.insert(END, f"- {q}\n")
            teacher_answers = latest.get("teacher_answers", [])
            if teacher_answers:
                self.lesson_box.insert(END, "\n\nTeacher answer:\n")
                for answer in teacher_answers[:1]:
                    self.lesson_box.insert(END, f"Q: {answer.get('question', '')}\n")
                    self.lesson_box.insert(END, str(answer.get("answer", ""))[:1200])
        self.lesson_box.configure(state="disabled")

    def periodic_refresh(self) -> None:
        self.refresh_status()
        self.root.after(15000, self.periodic_refresh)

    def on_close(self) -> None:
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    KiraSchoolControlCenter().run()
