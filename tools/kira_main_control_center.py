"""Main launcher hub for Kira project tools.

This is the first pass at reducing desktop launcher sprawl. It does not replace
the specialized control centers yet; it opens them from one organized place.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, TOP, X, Y, Button, Frame, Label, StringVar, Tk
from tkinter import messagebox, scrolledtext


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PRESENCE_DIR = PROJECT_ROOT / "Data" / "presence"
CURRENT_LIFE_RUN = PRESENCE_DIR / "current_kira_life_day_run.json"
CURRENT_SCHOOL_RUN = PRESENCE_DIR / "current_kira_school_run.json"
HANDOFF = PROJECT_ROOT / "HANDOFF_FOR_NEXT_CODEX_SESSION.md"
SHORTCUTS_DIR = Path(os.environ.get("USERPROFILE", "")) / "Desktop" / "Kira Desktop Shortcuts"


REGULAR_TOOLS = [
    ("Chat / Life Control Center", "Start_Kira_Chat_Control_Center.bat", "Main everyday window for talking to Kira, life loop controls, messages, and status."),
    ("Lisa Supervised Life Loop", "Start_Lisa_Supervised_6hour_Life_Test.bat", "Start Lisa's separate supervised life/work loop. Run only one core life loop at a time on the current RAM."),
    ("School Control Center", "Start_Kira_School_Control_Center.bat", "Main school UI. Use for 3/6/9-hour supervised school sessions."),
    ("Creative Writing Class", "Start_Kira_Creative_Writing_Class.bat", "Focused creative writing class, continuing Kira's cursor."),
    ("GPU Bridge Status", "Check_Kira_GPU_Bridge_Status.bat", "Quick check: active life run, Ollama GPU use, VRAM, RAM, temp."),
]

MEDIA_TOOLS = [
    ("Refresh Media Library", "Refresh_Kira_Media_Library.bat", "Rebuild the media/library index after adding or moving files."),
    ("Media Lookup Review", "Start_Kira_Media_Lookup_Review.bat", "Review ambiguous preview cards and metadata lookup queue."),
    ("GPU Media First Look", "Start_Kira_GPU_Media_First_Look.bat", "Create reviewed first-look image/video notes; not memory."),
    ("Voice Reference Control Center", "Start_Voice_Reference_Control_Center.bat", "Extract and review local or online candidate voice clips before model preparation."),
    ("OCR Queue Build", "Start_Kira_OCR_Queue_Build.bat", "Find scanned/unreadable PDF sources needing OCR."),
    ("OCR Repair First Batch", "Start_Kira_OCR_Repair_First_Batch.bat", "Run a small OCR repair batch."),
]

AVATAR_TEMP_TOOLS = [
    ("Kira Avatar Design Intake", "Start_Kira_Avatar_Design_Intake.bat", "Kira-owned avatar preferences and visual brief."),
    ("Kira Avatar Design Chat", "Start_Kira_Avatar_Design_Intake_Chat.bat", "Chat-style avatar design intake."),
    ("AI Workspace Intake", "Start_AI_Workspace_Intake.bat", "Create readable workspaces from local folders for Kira, Lisa, TemporaryAI, or project work."),
    ("TemporaryAI Control Center", "Start_TemporaryAI_Control_Center.bat", "Preferred GUI for creating TemporaryAI candidates, avatar requests, and Kira/Lisa activation plans."),
    ("TemporaryAI Live Chat", "Start_TemporaryAI_Live_Chat_GUI.bat", "Click a TemporaryAI candidate name and talk in a simple review/test chat window."),
    ("TemporaryAI Builder", "Start_TemporaryAI_Candidate_Builder.bat", "Create candidate profiles for TemporaryAI or expert AIs."),
    ("TemporaryAI Probe", "Start_TemporaryAI_Candidate_Probe.bat", "Probe a candidate directly without Kira leakage."),
    ("TempAI Avatar Reference Search", "Start_TempAI_Avatar_Reference_Search.bat", "Build approved/reviewed avatar reference queues."),
]

REVIEW_TOOLS = [
    ("Review Dashboard", "Start_Kira_Review_Dashboard.bat", "Open review/dashboard tools if available."),
    ("Question Review", "Start_Kira_Question_Review.bat", "Open Kira's question queue."),
    ("Message Review", "Start_Kira_Message_Review.bat", "Open Kira-to-Robert messages."),
    ("Memory Review", "Start_Kira_Memory_Review.bat", "Review memory candidates."),
    ("Shared Memory Review", "Start_Kira_Shared_Memory_Review.bat", "Review shared-memory candidates carefully."),
]

EXPERIMENTAL_TOOLS = [
    ("Activate Kira And Lisa", "Activate_Kira_And_Lisa.bat", "Experimental older multi-window helper. Inspect before relying on it."),
    ("Advanced AI Probe", "Start_Advanced_AI_Probe.bat", "Testing framework for Kira/Lisa/TemporaryAI probes."),
    ("Ladybug State Check", "Start_Ladybug_TemporaryAI_State_Check.bat", "Check Ladybug/Marinette form-state files."),
    ("Quick Tests", "Run_Kira_Quick_Tests.bat", "Developer smoke tests."),
]


def local_time() -> str:
    return datetime.now().strftime("%H:%M:%S")


def read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def rel(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def launcher_path(name: str) -> Path:
    return PROJECT_ROOT / name


def process_count(script_or_bat: str) -> int:
    if os.name != "nt":
        return 0
    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                f"@(Get-CimInstance Win32_Process | Where-Object {{ $_.CommandLine -match '{script_or_bat}' -and $_.CommandLine -notmatch 'Get-CimInstance' }}).Count",
            ],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        return int((result.stdout or "0").strip() or 0)
    except Exception:
        return 0


class KiraMainControlCenter:
    def __init__(self) -> None:
        self.root = Tk()
        self.root.title("Kira Main Control Center")
        self.root.geometry("1120x740")
        self.root.minsize(980, 620)
        self.root.configure(bg="#0b1220")
        self.status_vars: dict[str, StringVar] = {}
        self.build_ui()
        self.log("Main hub ready. Use this as the front door; specialized windows still do the deeper work.")
        self.refresh_status()
        self.root.after(15000, self.periodic_refresh)

    def build_ui(self) -> None:
        outer = Frame(self.root, bg="#0b1220")
        outer.pack(fill=BOTH, expand=True, padx=14, pady=14)

        left = Frame(outer, bg="#111827", bd=1, relief="solid", width=530)
        left.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 12))
        right = Frame(outer, bg="#111827", bd=1, relief="solid", width=420)
        right.pack(side=RIGHT, fill=Y)

        Label(left, text="Kira Main Control Center", fg="#f9fafb", bg="#111827", font=("Segoe UI", 18, "bold")).pack(anchor="w", padx=14, pady=(12, 2))
        Label(
            left,
            text="One front door for Kira tools. Regular tools are first; experimental tools are separated so old runners do not get clicked by accident.",
            fg="#cbd5e1",
            bg="#111827",
            wraplength=700,
            justify=LEFT,
        ).pack(anchor="w", padx=14, pady=(0, 12))

        columns = Frame(left, bg="#111827")
        columns.pack(fill=BOTH, expand=True, padx=10, pady=(0, 10))
        col1 = Frame(columns, bg="#111827")
        col1.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 8))
        col2 = Frame(columns, bg="#111827")
        col2.pack(side=RIGHT, fill=BOTH, expand=True)

        self.tool_section(col1, "Everyday", REGULAR_TOOLS)
        self.tool_section(col1, "Media / OCR", MEDIA_TOOLS)
        self.tool_section(col2, "Avatar / TemporaryAI", AVATAR_TEMP_TOOLS)
        self.tool_section(col2, "Review", REVIEW_TOOLS)
        self.tool_section(col2, "Experimental", EXPERIMENTAL_TOOLS, experimental=True)

        Label(right, text="Live Overview", fg="#f9fafb", bg="#111827", font=("Segoe UI", 15, "bold")).pack(anchor="w", padx=12, pady=(12, 8))
        for key, label in [
            ("life", "Life run"),
            ("school", "School run"),
            ("chat_ui", "Chat UI"),
            ("school_ui", "School UI"),
            ("shortcuts", "Shortcuts"),
        ]:
            row = Frame(right, bg="#111827")
            row.pack(fill=X, padx=12, pady=4)
            Label(row, text=label, fg="#9ca3af", bg="#111827", width=12, anchor="w").pack(side=LEFT)
            var = StringVar(value="")
            self.status_vars[key] = var
            Label(row, textvariable=var, fg="#f9fafb", bg="#111827", anchor="w", wraplength=260, justify=LEFT).pack(side=LEFT, fill=X, expand=True)

        row = Frame(right, bg="#111827")
        row.pack(fill=X, padx=12, pady=(10, 6))
        Button(row, text="Refresh Status", command=self.refresh_status, height=2).pack(side=LEFT, fill=X, expand=True, padx=(0, 6))
        Button(row, text="Open Handoff", command=lambda: self.open_path(HANDOFF), height=2).pack(side=LEFT, fill=X, expand=True)

        row2 = Frame(right, bg="#111827")
        row2.pack(fill=X, padx=12, pady=4)
        Button(row2, text="Open Project Folder", command=lambda: self.open_path(PROJECT_ROOT), height=2).pack(side=LEFT, fill=X, expand=True, padx=(0, 6))
        Button(row2, text="Open Shortcuts Folder", command=lambda: self.open_path(SHORTCUTS_DIR), height=2).pack(side=LEFT, fill=X, expand=True)

        Label(right, text="Event Log", fg="#f9fafb", bg="#111827", font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=12, pady=(12, 4))
        self.event_log = scrolledtext.ScrolledText(right, wrap="word", bg="#0b1220", fg="#d1d5db", relief="flat", font=("Consolas", 9), height=16)
        self.event_log.pack(fill=BOTH, expand=True, padx=12, pady=(0, 12))

    def tool_section(self, parent: Frame, title: str, tools: list[tuple[str, str, str]], experimental: bool = False) -> None:
        Label(parent, text=title, fg="#93c5fd" if not experimental else "#fbbf24", bg="#111827", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(8, 3))
        for label, bat, desc in tools:
            row = Frame(parent, bg="#111827")
            row.pack(fill=X, pady=2)
            button_text = label if (PROJECT_ROOT / bat).exists() else f"{label} (missing)"
            button = Button(row, text=button_text, command=lambda b=bat, d=desc, e=experimental: self.launch(b, d, e), height=2)
            button.pack(side=TOP, fill=X)
            Label(row, text=desc, fg="#9ca3af", bg="#111827", justify=LEFT, wraplength=360).pack(anchor="w", padx=2, pady=(1, 4))

    def log(self, text: str) -> None:
        line = f"[{local_time()}] {text}"
        self.event_log.insert(END, line + "\n")
        self.event_log.see(END)

    def launch(self, bat: str, desc: str, experimental: bool = False) -> None:
        path = launcher_path(bat)
        if not path.exists():
            self.log(f"Missing launcher: {bat}")
            messagebox.showerror("Missing launcher", f"Could not find:\n{path}")
            return
        if experimental:
            ok = messagebox.askyesno("Experimental tool", f"{bat}\n\n{desc}\n\nThis is marked experimental. Open it?")
            if not ok:
                self.log(f"Skipped experimental launcher: {bat}")
                return
        subprocess.Popen(["cmd", "/c", "start", "", str(path)], cwd=str(PROJECT_ROOT), shell=False)
        self.log(f"Launched {bat}")
        self.root.after(3000, self.refresh_status)

    def open_path(self, path: Path) -> None:
        if not path.exists():
            self.log(f"Path not found: {path}")
            return
        os.startfile(str(path))
        self.log(f"Opened {rel(path) if path.is_file() else path}")

    def refresh_status(self) -> None:
        life = read_json(CURRENT_LIFE_RUN, {})
        school = read_json(CURRENT_SCHOOL_RUN, {})
        life_label = "none"
        if isinstance(life, dict) and life.get("run_id"):
            life_label = f"{life.get('run_id')} ({life.get('status', 'unknown')})"
        school_label = "none"
        if isinstance(school, dict) and school.get("run_id"):
            school_label = f"{school.get('run_id')}"
        self.status_vars["life"].set(life_label)
        self.status_vars["school"].set(school_label)
        self.status_vars["chat_ui"].set("open" if process_count("kira_chat_control_center.py") else "not detected")
        self.status_vars["school_ui"].set("open" if process_count("kira_school_control_center.py") else "not detected")
        self.status_vars["shortcuts"].set("present" if SHORTCUTS_DIR.exists() else "not found")
        self.log("Status refreshed.")

    def periodic_refresh(self) -> None:
        self.refresh_status()
        self.root.after(15000, self.periodic_refresh)

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    KiraMainControlCenter().run()

