"""Human review panel for candidate voice clips."""
from __future__ import annotations

import os
import subprocess
import sys
import threading
import winsound
from collections import Counter
from pathlib import Path
from tkinter import (
    BOTH,
    END,
    LEFT,
    RIGHT,
    Button,
    Frame,
    Label,
    Listbox,
    StringVar,
    Tk,
    filedialog,
    messagebox,
    ttk,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from Core.voice_reference_pipeline import read_json, resolve_ffmpeg, update_pack_review


ALL_GROUPS = "all groups"
ALL_STATUSES = "all statuses"
REVIEW_STATUSES = (
    "unreviewed",
    "approved_target",
    "rejected_other_speaker",
    "rejected_mixed_speakers",
    "rejected_noisy",
)
DECISION_STATUSES = frozenset(REVIEW_STATUSES[1:])


def _project_path(value: str) -> Path:
    path = Path(str(value or ""))
    return path if path.is_absolute() else PROJECT_ROOT / path


def review_panel_identity(manifest: dict, pack_dir: Path) -> dict[str, str]:
    """Return the exact target/source/pack identity displayed by the panel."""
    target = manifest.get("target", {}) if isinstance(manifest.get("target"), dict) else {}
    source = manifest.get("source", {}) if isinstance(manifest.get("source"), dict) else {}
    target_name = str(target.get("name") or target.get("id") or "Unknown target").strip()
    target_id = str(target.get("id") or "unidentified_target").strip()
    form_or_version = str(
        target.get("form_or_version")
        or manifest.get("form_or_version")
        or "unspecified version"
    ).strip()
    source_path = str(source.get("path") or "no source path recorded").strip()
    source_name = Path(source_path).name if source_path != "no source path recorded" else source_path
    pack_id = str(manifest.get("pack_id") or pack_dir.name).strip()
    return {
        "target_name": target_name,
        "target_id": target_id,
        "form_or_version": form_or_version,
        "source_path": source_path,
        "source_name": source_name,
        "pack_id": pack_id,
        "window_title": f"{target_name} Voice Candidate Review — identity unverified",
    }


def filter_review_clips(
    clips: list[dict],
    group_by_clip: dict[str, str],
    wanted_group: str = ALL_GROUPS,
    wanted_status: str = ALL_STATUSES,
) -> list[dict]:
    """Filter clips without treating an acoustic group as a person identity."""
    return [
        clip
        for clip in clips
        if (
            wanted_group == ALL_GROUPS
            or group_by_clip.get(str(clip.get("clip_id", "")), "unclustered") == wanted_group
        )
        and (
            wanted_status == ALL_STATUSES
            or str(clip.get("review_status", "unreviewed")) == wanted_status
        )
    ]


def review_status_counts(clips: list[dict]) -> dict[str, int]:
    """Summarize persisted or in-memory human review states."""
    counts = Counter(str(clip.get("review_status", "unreviewed")) for clip in clips)
    rejected = sum(count for status, count in counts.items() if status.startswith("rejected_"))
    return {
        "total": len(clips),
        "unreviewed": counts["unreviewed"],
        "approved_target": counts["approved_target"],
        "rejected": rejected,
    }


def format_clip_row(clip: dict, acoustic_group: str) -> str:
    """Format one review row while keeping the group visibly separate from identity."""
    start = float(clip.get("start_seconds", 0.0) or 0.0)
    end = float(clip.get("end_seconds", start) or start)
    duration = float(clip.get("duration_seconds", max(0.0, end - start)) or 0.0)
    return (
        f"[{str(clip.get('review_status', 'unreviewed')):24}] "
        f"{clip.get('clip_id')}  group={acoustic_group:12}  "
        f"{start:7.2f}-{end:7.2f}s  ({duration:.2f}s)"
    )


def can_approve_target(clip: dict | None, context_opened_clip_ids: set[str]) -> bool:
    """Fail closed until this exact clip's source context was opened this session."""
    if not clip:
        return False
    return str(clip.get("clip_id", "")) in context_opened_clip_ids


def next_unreviewed_clip_id(clips: list[dict], selected_index: int) -> str:
    """Choose the next unreviewed row, wrapping once but never returning the current row."""
    if len(clips) < 2 or selected_index < 0 or selected_index >= len(clips):
        return ""
    for offset in range(1, len(clips)):
        candidate = clips[(selected_index + offset) % len(clips)]
        if str(candidate.get("review_status", "unreviewed")) == "unreviewed":
            return str(candidate.get("clip_id", ""))
    return ""


def persist_review_decision(
    pack_dir: Path,
    clips: list[dict],
    clip: dict,
    decision: str,
) -> dict:
    """Apply one human decision and immediately persist the complete review ledger.

    If persistence fails, restore the in-memory row so the panel cannot display a
    decision that was never saved.
    """
    if decision not in DECISION_STATUSES:
        raise ValueError(f"Unsupported review decision: {decision}")
    had_status = "review_status" in clip
    previous = clip.get("review_status")
    clip["review_status"] = decision
    try:
        return update_pack_review(pack_dir, clips)
    except Exception:
        if had_status:
            clip["review_status"] = previous
        else:
            clip.pop("review_status", None)
        raise


def launch_source_context(
    output: Path,
    clip_id: str,
    context_opened_clip_ids: set[str],
    launcher=None,
) -> None:
    """Record the exact context gate before handing the file to an external player."""
    context_opened_clip_ids.add(clip_id)
    try:
        (launcher or os.startfile)(str(output))
    except Exception:
        context_opened_clip_ids.discard(clip_id)
        raise


def build_source_context(pack_dir: Path, manifest: dict, clip: dict) -> Path:
    """Create a short review-only MP4 around one extracted WAV candidate."""
    ffmpeg = resolve_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("FFmpeg is unavailable; run tools/check_voice_pipeline.py.")
    source = _project_path(str(manifest.get("source", {}).get("path", "")))
    if not source.is_file() or source.suffix.lower() in {".wav", ".mp3", ".m4a", ".flac"}:
        raise RuntimeError("This reference pack has no reviewable local video source.")
    start = max(0.0, float(clip.get("start_seconds", 0.0) or 0.0) - 1.5)
    end = max(start + 0.5, float(clip.get("end_seconds", start) or start) + 1.5)
    output_dir = pack_dir / "review_contexts"
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"{clip.get('clip_id', 'candidate')}_context.mp4"
    if output.is_file() and output.stat().st_size > 0:
        return output
    completed = subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            f"{start:.3f}",
            "-i",
            str(source),
            "-t",
            f"{end - start:.3f}",
            "-map",
            "0:v:0",
            "-map",
            "0:a:0?",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-crf",
            "24",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            str(output),
        ],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if completed.returncode != 0 or not output.is_file():
        raise RuntimeError(f"Could not build source context: {completed.stderr.strip()[:500]}")
    return output


class ReviewPanel:
    def __init__(self, root: Tk, pack_dir: Path) -> None:
        self.root = root
        self.pack_dir = pack_dir
        self.manifest = read_json(pack_dir / "voice_reference_manifest.json", {})
        self.clips = read_json(pack_dir / "clip_review.json", {"clips": []}).get("clips", [])
        separation = read_json(
            pack_dir / "speaker_separation" / "speaker_separation_manifest.json", {}
        )
        self.group_by_clip = {
            str(item.get("clip_id", "")): str(item.get("speaker_label", "unclustered"))
            for item in separation.get("clips", [])
        }
        self.identity = review_panel_identity(self.manifest, pack_dir)
        self.group_filter = StringVar(value=ALL_GROUPS)
        self.status_filter = StringVar(value="unreviewed")
        self.visible_clips = list(self.clips)
        self.context_opened_clip_ids: set[str] = set()
        self.dirty = False
        self.status = StringVar(
            value="Select a clip. Every Use or Reject decision saves immediately."
        )
        self.decision_banner = StringVar(
            value="READY — select a clip, then use the simple buttons on the right."
        )
        self.count_text = StringVar()
        self.selected_detail = StringVar(value="No clip selected.")

        root.title(self.identity["window_title"])
        root.geometry("1220x780")
        root.protocol("WM_DELETE_WINDOW", self.on_close)

        identity_frame = Frame(root, bd=1, relief="solid")
        identity_frame.pack(fill="x", padx=12, pady=(12, 6))
        Label(
            identity_frame,
            text=f"TARGET: {self.identity['target_name']}  —  IDENTITY NOT YET APPROVED",
            font=("Segoe UI", 12, "bold"),
            fg="#8b0000",
            anchor="w",
        ).pack(fill="x", padx=10, pady=(8, 2))
        Label(
            identity_frame,
            text=(
                f"Version/form: {self.identity['form_or_version']}\n"
                f"Source file: {self.identity['source_name']}\n"
                f"Pack ID: {self.identity['pack_id']}"
            ),
            justify="left",
            anchor="w",
            wraplength=1160,
        ).pack(fill="x", padx=10, pady=(0, 4))
        Label(
            identity_frame,
            text=(
                "Acoustic labels such as female_4 are rough sound groups, not person identities. "
                f"Approve only when the source video shows/hears {self.identity['target_name']} alone."
            ),
            justify="left",
            anchor="w",
            fg="#7a4a00",
            wraplength=1160,
        ).pack(fill="x", padx=10, pady=(0, 8))

        self.decision_label = Label(
            root,
            textvariable=self.decision_banner,
            font=("Segoe UI", 11, "bold"),
            bg="#e8f4ff",
            fg="#15344a",
            anchor="w",
            justify="left",
            padx=12,
            pady=8,
        )
        self.decision_label.pack(fill="x", padx=12, pady=(0, 6))

        body = Frame(root)
        body.pack(fill=BOTH, expand=True, padx=12, pady=6)
        self.listbox = Listbox(body, font=("Consolas", 10), exportselection=False)
        self.listbox.pack(side=LEFT, fill=BOTH, expand=True)
        self.listbox.bind("<<ListboxSelect>>", lambda _event: self.update_selected_detail())

        controls = Frame(body, width=310)
        controls.pack(side=RIGHT, fill="y", padx=(12, 0))
        Label(controls, text="Optional filters (you can ignore these)").pack(
            anchor="w", pady=(0, 2)
        )
        Label(controls, text="Sound group (not a person identity)").pack(
            anchor="w", pady=(0, 2)
        )
        groups = [ALL_GROUPS] + sorted(set(self.group_by_clip.values()))
        group_picker = ttk.Combobox(
            controls,
            textvariable=self.group_filter,
            values=groups,
            state="readonly",
            width=34,
        )
        group_picker.pack(fill="x", pady=(0, 6))
        group_picker.bind("<<ComboboxSelected>>", lambda _event: self.refresh())

        Label(controls, text="Human review status").pack(anchor="w", pady=(0, 2))
        status_picker = ttk.Combobox(
            controls,
            textvariable=self.status_filter,
            values=[ALL_STATUSES, *REVIEW_STATUSES],
            state="readonly",
            width=34,
        )
        status_picker.pack(fill="x", pady=(0, 6))
        status_picker.bind("<<ComboboxSelected>>", lambda _event: self.refresh())
        Label(controls, textvariable=self.count_text, justify="left", anchor="w").pack(
            fill="x", pady=(0, 8)
        )

        Button(
            controls,
            text="Play selected clip",
            command=self.play,
            height=2,
            width=36,
        ).pack(pady=4)
        self.use_button = Button(
            controls,
            text="Use this clip (opens its source first)",
            command=self.use_clip,
            height=2,
            width=36,
            bg="#d9f2d9",
        )
        self.use_button.pack(pady=4)
        Label(
            controls,
            text=(
                "First click opens the exact source if needed. After watching it, "
                "click Use this clip again."
            ),
            justify="left",
            anchor="w",
            wraplength=300,
            fg="#315b31",
        ).pack(fill="x", pady=(0, 6))
        Label(controls, text="Reject and immediately go to the next clip:").pack(
            anchor="w", pady=(10, 2)
        )
        reject_actions = [
            ("Wrong person — reject", "rejected_other_speaker"),
            ("More than one speaker — reject", "rejected_mixed_speakers"),
            ("Noise or music — reject", "rejected_noisy"),
        ]
        for label, decision in reject_actions:
            Button(
                controls,
                text=label,
                command=lambda value=decision: self.mark(value),
                height=2,
                width=36,
            ).pack(pady=4)
        Label(
            controls,
            text="There is no Save button: every decision is saved automatically.",
            justify="left",
            anchor="w",
            wraplength=300,
            fg="#315b31",
        ).pack(fill="x", pady=(6, 0))
        Label(
            controls,
            textvariable=self.selected_detail,
            justify="left",
            anchor="nw",
            wraplength=300,
        ).pack(fill="x", pady=(12, 0))

        Label(root, textvariable=self.status, anchor="w").pack(
            fill="x", padx=12, pady=(0, 12)
        )
        self.refresh()

    def refresh(self, preferred_clip_id: str = "") -> None:
        current_clip = self.current()
        previous_id = str(current_clip.get("clip_id", "")) if current_clip else ""
        selected = self.listbox.curselection()
        previous_index = selected[0] if selected else 0
        self.listbox.delete(0, END)
        self.visible_clips = filter_review_clips(
            self.clips,
            self.group_by_clip,
            self.group_filter.get(),
            self.status_filter.get(),
        )
        for clip in self.visible_clips:
            group = self.group_by_clip.get(str(clip.get("clip_id", "")), "unclustered")
            self.listbox.insert(END, format_clip_row(clip, group))

        selection_id = preferred_clip_id or previous_id
        selection_index = previous_index
        if selection_id:
            for index, clip in enumerate(self.visible_clips):
                if str(clip.get("clip_id", "")) == selection_id:
                    selection_index = index
                    break
        if self.visible_clips:
            selection_index = min(selection_index, len(self.visible_clips) - 1)
            self.listbox.selection_set(selection_index)
            self.listbox.see(selection_index)
        self.update_counts()
        self.update_selected_detail()

    def update_counts(self) -> None:
        counts = review_status_counts(self.clips)
        unsaved = " | UNSAVED CHANGES" if self.dirty else ""
        self.count_text.set(
            f"Showing {len(self.visible_clips)} of {counts['total']}\n"
            f"Unreviewed {counts['unreviewed']} | approved {counts['approved_target']} | "
            f"rejected {counts['rejected']}{unsaved}"
        )

    def update_selected_detail(self) -> None:
        clip = self.current()
        if not clip:
            self.selected_detail.set("No clip selected.")
            if hasattr(self, "use_button"):
                self.use_button.configure(text="Use this clip (select a clip first)")
            return
        clip_id = str(clip.get("clip_id", ""))
        context_status = "YES" if clip_id in self.context_opened_clip_ids else "NO"
        self.selected_detail.set(
            f"Selected: {clip_id}\n"
            f"Target: {self.identity['target_name']}\n"
            f"Source context opened this session: {context_status}\n"
            "Approval remains clip-specific."
        )
        if hasattr(self, "use_button"):
            button_text = (
                f"YES — use {clip_id} for {self.identity['target_name']}"
                if context_status == "YES"
                else "Use this clip (opens its source first)"
            )
            self.use_button.configure(text=button_text)

    def current(self) -> dict | None:
        selected = self.listbox.curselection()
        return self.visible_clips[selected[0]] if selected else None

    def announce(self, message: str, kind: str = "info") -> None:
        colors = {
            "info": ("#e8f4ff", "#15344a"),
            "working": ("#fff3cd", "#664d03"),
            "success": ("#d9f2d9", "#174517"),
            "error": ("#f8d7da", "#842029"),
        }
        background, foreground = colors.get(kind, colors["info"])
        self.decision_banner.set(message)
        self.decision_label.configure(bg=background, fg=foreground)
        self.status.set(message)
        self.root.update_idletasks()

    def play(self) -> None:
        clip = self.current()
        if not clip:
            self.announce("Select a clip first.", "error")
            return
        winsound.PlaySound(
            str(PROJECT_ROOT / str(clip["path"])),
            winsound.SND_FILENAME | winsound.SND_ASYNC,
        )
        self.announce(
            f"PLAYING {clip['clip_id']} — no decision has been made yet.", "info"
        )

    def play_context(self, prepare_for_use: bool = False) -> None:
        clip = self.current()
        if not clip:
            self.announce("Select a clip first.", "error")
            return
        self.announce(
            f"PREPARING {clip['clip_id']} source context — please wait...", "working"
        )
        threading.Thread(
            target=self._play_context_worker,
            args=(clip, prepare_for_use),
            daemon=True,
        ).start()

    def _play_context_worker(self, clip: dict, prepare_for_use: bool = False) -> None:
        try:
            output = build_source_context(self.pack_dir, self.manifest, clip)
            clip_id = str(clip.get("clip_id", ""))
            self.root.after(
                0,
                lambda: self._launch_built_context(clip_id, output, prepare_for_use),
            )
        except Exception as exc:
            message = str(exc)
            self.root.after(
                0,
                lambda message=message: self.announce(
                    f"CONTEXT ERROR — {message}", "error"
                ),
            )
            self.root.after(
                0,
                lambda message=message: messagebox.showerror("Context unavailable", message),
            )

    def _launch_built_context(
        self,
        clip_id: str,
        output: Path,
        prepare_for_use: bool = False,
    ) -> None:
        try:
            launch_source_context(
                output,
                clip_id,
                self.context_opened_clip_ids,
            )
        except Exception as exc:
            self.announce(f"PLAYER ERROR — {exc}", "error")
            messagebox.showerror("Could not open source context", str(exc))
            return
        self._record_opened_context(clip_id, prepare_for_use=prepare_for_use)

    def _record_opened_context(self, clip_id: str, prepare_for_use: bool = False) -> None:
        self.context_opened_clip_ids.add(clip_id)
        instruction = (
            f"CONTEXT OPENED for {clip_id}. Watch it completely. If only "
            f"{self.identity['target_name']} speaks, return and click Use this clip again."
            if prepare_for_use
            else f"CONTEXT OPENED for {clip_id}. No identity decision was made."
        )
        self.announce(instruction, "working")
        self.update_selected_detail()

    def use_clip(self) -> None:
        clip = self.current()
        if not clip:
            self.announce("Select a clip first.", "error")
            return
        if not can_approve_target(clip, self.context_opened_clip_ids):
            self.play_context(prepare_for_use=True)
            return
        self.mark("approved_target")

    def mark(self, value: str) -> None:
        clip = self.current()
        if not clip:
            self.announce("Select a clip first.", "error")
            return
        if value == "approved_target" and not can_approve_target(
            clip, self.context_opened_clip_ids
        ):
            self.play_context(prepare_for_use=True)
            return

        selected_index = self.listbox.curselection()[0]
        next_clip_id = next_unreviewed_clip_id(self.visible_clips, selected_index)
        clip_id = str(clip.get("clip_id", ""))
        readable = {
            "approved_target": f"used for {self.identity['target_name']}",
            "rejected_other_speaker": "rejected: wrong person",
            "rejected_mixed_speakers": "rejected: more than one speaker",
            "rejected_noisy": "rejected: noise or music",
        }[value]
        self.announce(f"SAVING {clip_id} — {readable}...", "working")
        try:
            manifest = persist_review_decision(
                self.pack_dir,
                self.clips,
                clip,
                value,
            )
        except Exception as exc:
            self.announce(f"NOT SAVED — {clip_id}: {exc}", "error")
            messagebox.showerror("Review decision was not saved", str(exc))
            self.refresh(preferred_clip_id=clip_id)
            return
        self.manifest = manifest
        self.dirty = False
        self.refresh(preferred_clip_id=next_clip_id)
        next_message = (
            f" Next: {next_clip_id}."
            if next_clip_id
            else " No unreviewed clips remain in this view."
        )
        self.announce(f"SAVED — {clip_id} {readable}.{next_message}", "success")

    def save(self, show_confirmation: bool = True) -> bool:
        try:
            manifest = update_pack_review(self.pack_dir, self.clips)
        except Exception as exc:
            self.status.set(f"Save failed: {exc}")
            messagebox.showerror("Review save failed", str(exc))
            return False
        self.manifest = manifest
        self.dirty = False
        self.update_counts()
        readiness = manifest.get("model_readiness", {})
        self.status.set(f"Saved. Model eligible: {readiness.get('eligible', False)}")
        if show_confirmation:
            messagebox.showinfo("Review saved", readiness.get("reason", "Review saved."))
        return True

    def on_close(self) -> None:
        if not self.dirty:
            self.root.destroy()
            return
        choice = messagebox.askyesnocancel(
            "Unsaved review decisions",
            "Save your review decisions before closing?\n\nYes = save and close\nNo = discard unsaved changes\nCancel = keep reviewing",
        )
        if choice is None:
            return
        if choice and not self.save(show_confirmation=False):
            return
        self.root.destroy()


def choose_pack() -> Path | None:
    root = Tk()
    root.withdraw()
    chosen = filedialog.askdirectory(initialdir=str(PROJECT_ROOT / "Voice" / "reference_packs"))
    root.destroy()
    return Path(chosen) if chosen else None


def main() -> None:
    pack_dir = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else choose_pack()
    if not pack_dir or not (pack_dir / "clip_review.json").exists():
        return
    root = Tk()
    ReviewPanel(root, pack_dir)
    root.mainloop()


if __name__ == "__main__":
    main()
