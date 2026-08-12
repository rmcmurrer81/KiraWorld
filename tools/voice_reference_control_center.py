"""GUI front end for local voice-reference collection and review."""
from __future__ import annotations
import subprocess, sys, threading
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, Button, Entry, Frame, Label, StringVar, Text, Tk, filedialog, messagebox, ttk
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
from Core.voice_online_reference import build_online_audio_pack, find_reference_by_url, link_saved_online_reference
from Core.voice_reference_pipeline import build_local_reference_pack, ffmpeg_readiness
from Core.voice_speaker_separation import build_speaker_audition_reels, separate_reference_pack

class VoiceReferenceCenter:
    def __init__(self, root: Tk) -> None:
        self.root, self.last_pack = root, ""; root.title("Kira Voice Reference Control Center"); root.geometry("1100x900")
        main = Frame(root); main.pack(fill=BOTH, expand=True, padx=16, pady=16); left = Frame(main); left.pack(side=LEFT, fill=BOTH, expand=True); right = Frame(main, width=390); right.pack(side=RIGHT, fill=BOTH, padx=(16, 0))
        self.target, self.target_id = StringVar(value="Ladybug"), StringVar(value="ladybug")
        self.version, self.source, self.script = StringVar(value="English dub / Ladybug form"), StringVar(), StringVar()
        self.authorization = StringVar(value="review_required")
        self.online_url = StringVar(value="https://www.youtube.com/watch?v=nHKVwDaBfss")
        self.field(left, "Target name", self.target); self.field(left, "Target id", self.target_id); self.field(left, "Version / dub / form", self.version)
        self.path_field(left, "Local episode or recording", self.source, [("Media", "*.mp4 *.mkv *.mov *.wav *.mp3"), ("All", "*.*")])
        self.path_field(left, "Matching script (optional)", self.script, [("Scripts", "*.pdf *.txt *.md"), ("All", "*.*")])
        Label(left, text="Authorization / rights review").pack(anchor="w", pady=(10, 2))
        ttk.Combobox(left, textvariable=self.authorization, values=["review_required", "owned", "licensed", "authorized", "self_recorded"], state="readonly").pack(fill="x")
        Button(left, text="Build Local Candidate Clip Pack", command=self.build, height=2).pack(fill="x", pady=5)
        Label(left, text="Online video URL").pack(anchor="w", pady=(12, 2))
        Entry(left, textvariable=self.online_url).pack(fill="x")
        Button(left, text="Save Existing Online Style Reference", command=self.link_online, height=2).pack(fill="x", pady=5)
        Button(left, text="Download Online Candidate Audio", command=self.build_online, height=2).pack(fill="x", pady=5)
        Button(left, text="Select Existing Reference Pack", command=self.select_existing_pack, height=2).pack(fill="x", pady=5)
        Button(left, text="Separate Speakers In Last Pack", command=self.separate_speakers, height=2).pack(fill="x", pady=5)
        Button(left, text="Build Group Audition Reels", command=self.build_audition_reels, height=2).pack(fill="x", pady=5)
        Button(left, text="Open Last Audition Reels", command=self.open_last_audition_reels, height=2).pack(fill="x", pady=5)
        Button(left, text="Open Last Speaker Groups", command=self.open_last_speaker_groups, height=2).pack(fill="x", pady=5)
        Label(left, text="Online audio can contain narrators, music, and other characters. Review every target clip.", wraplength=600, justify="left").pack(anchor="w")
        for label, command in [("Review Last Pack", self.review), ("Open Reference Packs", self.open_packs), ("Check Pipeline", self.check)]:
            Button(left, text=label, command=command, height=2).pack(fill="x", pady=5)
        Label(right, text="Event Log", font=("Segoe UI", 13, "bold")).pack(anchor="w"); self.log = Text(right, wrap="word", font=("Consolas", 9)); self.log.pack(fill=BOTH, expand=True, pady=(8, 0))
        ready = ffmpeg_readiness(); self.write(f"FFmpeg ready: {ready['ready']} {ready.get('executable', '')}"); self.write("Extraction creates candidate clips. Speaker review is required next.")
    def field(self, parent, label, variable): Label(parent, text=label).pack(anchor="w", pady=(10, 2)); Entry(parent, textvariable=variable).pack(fill="x")
    def path_field(self, parent, label, variable, types):
        Label(parent, text=label).pack(anchor="w", pady=(10, 2)); row = Frame(parent); row.pack(fill="x"); Entry(row, textvariable=variable).pack(side=LEFT, fill="x", expand=True); Button(row, text="Browse", command=lambda: self.pick(variable, types)).pack(side=RIGHT, padx=(8, 0))
    def pick(self, variable, types):
        path = filedialog.askopenfilename(initialdir=str(PROJECT_ROOT / "Data" / "library"), filetypes=types)
        if path: variable.set(path)
    def write(self, message): self.log.insert(END, str(message).rstrip() + "\n"); self.log.see(END)
    def build(self):
        if not self.source.get().strip(): messagebox.showwarning("Source needed", "Choose a local episode or recording first."); return
        self.write("Building pack; audio extraction may take a few minutes..."); threading.Thread(target=self.build_worker, daemon=True).start()
    def build_worker(self):
        try:
            result = build_local_reference_pack(target_name=self.target.get().strip(), target_id=self.target_id.get().strip(), source_path=Path(self.source.get()).resolve(), script_path=Path(self.script.get()).resolve() if self.script.get().strip() else None, authorization_status=self.authorization.get(), form_or_version=self.version.get().strip())
            self.last_pack = str(PROJECT_ROOT / result["pack_dir"]); self.root.after(0, lambda: self.write(f"Built {result['pack_id']} with {result['audio']['candidate_clip_count']} candidate clips.")); self.root.after(0, lambda: messagebox.showinfo("Pack built", "Candidate clips are ready. Click Review Last Pack next."))
        except Exception as exc: self.root.after(0, lambda: self.write(f"ERROR: {exc}")); self.root.after(0, lambda: messagebox.showerror("Build failed", str(exc)))
    def link_online(self):
        url = self.online_url.get().strip()
        saved = find_reference_by_url(url)
        if not saved:
            messagebox.showwarning("No saved reference", "No saved TemporaryAI video reference matched this URL. Run Video Reference Intake first or download candidate audio.")
            return
        try:
            result = link_saved_online_reference(target_name=self.target.get().strip(), target_id=self.target_id.get().strip(), form_or_version=self.version.get().strip(), reference_dir=saved)
            self.last_pack = str(PROJECT_ROOT / result["pack_dir"])
            self.write(f"Saved online style reference: {result['pack_id']}")
            messagebox.showinfo("Reference saved", "Captions, style metrics, and thumbnail are linked. This is not a voice model yet.")
        except Exception as exc:
            self.write(f"ERROR: {exc}"); messagebox.showerror("Reference failed", str(exc))

    def build_online(self):
        if not self.online_url.get().strip():
            messagebox.showwarning("URL needed", "Paste an online video URL first."); return
        if not messagebox.askyesno("Download candidate audio?", "Download source audio and split possible speech? No speaker will be auto-approved."):
            return
        self.write("Downloading online audio and building candidate clips...")
        threading.Thread(target=self.build_online_worker, daemon=True).start()

    def build_online_worker(self):
        try:
            url = self.online_url.get().strip()
            result = build_online_audio_pack(target_name=self.target.get().strip(), target_id=self.target_id.get().strip(), url=url, form_or_version=self.version.get().strip(), script_path=Path(self.script.get()).resolve() if self.script.get().strip() else None, authorization_status=self.authorization.get(), saved_reference_dir=find_reference_by_url(url))
            self.last_pack = str(PROJECT_ROOT / result["pack_dir"])
            count = result.get("audio", {}).get("candidate_clip_count", 0)
            self.root.after(0, lambda: self.write(f"Built {result['pack_id']} with {count} unreviewed candidate clips."))
            self.root.after(0, lambda: messagebox.showinfo("Pack built", "Click Review Last Pack. Approve only clean target-only speech."))
        except Exception as exc:
            self.root.after(0, lambda: self.write(f"ERROR: {exc}")); self.root.after(0, lambda: messagebox.showerror("Online build failed", str(exc)))
    def review(self):
        command = [sys.executable, str(PROJECT_ROOT / "tools" / "voice_sample_review_panel.py")]
        if self.last_pack: command.append(self.last_pack)
        subprocess.Popen(command, cwd=str(PROJECT_ROOT))
    def select_existing_pack(self):
        path = filedialog.askdirectory(
            initialdir=str(PROJECT_ROOT / "Voice" / "reference_packs"),
            title="Select a voice reference pack",
        )
        if not path:
            return
        pack = Path(path)
        if not (pack / "voice_reference_manifest.json").exists():
            messagebox.showwarning("Not a reference pack", "Choose a folder containing voice_reference_manifest.json.")
            return
        self.last_pack = str(pack)
        self.write(f"Selected existing pack: {pack.name}")
    def separate_speakers(self):
        if not self.last_pack:
            messagebox.showwarning("Pack needed", "Build or download a candidate pack first.")
            return
        self.write("Grouping recurring voices for review...")
        threading.Thread(target=self.separate_speakers_worker, daemon=True).start()
    def separate_speakers_worker(self):
        try:
            result = separate_reference_pack(Path(self.last_pack))
            labels = ", ".join(result.get("speaker_labels", []))
            self.root.after(0, lambda: self.write(f"Speaker review groups: {labels}"))
            self.root.after(0, lambda: messagebox.showinfo("Speaker groups ready", "Open the last pack and review speaker_separation. Labels are unverified until you confirm them."))
        except Exception as exc:
            self.root.after(0, lambda: self.write(f"ERROR: {exc}"))
            self.root.after(0, lambda: messagebox.showerror("Speaker grouping failed", str(exc)))
    def open_last_speaker_groups(self):
        if not self.last_pack:
            messagebox.showwarning("Pack needed", "Build or download a candidate pack in this window first.")
            return
        path = Path(self.last_pack) / "speaker_separation" / "speakers"
        if not path.exists():
            messagebox.showwarning("Groups not ready", "Click Separate Speakers In Last Pack first.")
            return
        subprocess.Popen(["explorer", str(path)])
    def build_audition_reels(self):
        if not self.last_pack:
            messagebox.showwarning("Pack needed", "Build or download a candidate pack first.")
            return
        try:
            result = build_speaker_audition_reels(Path(self.last_pack))
            labels = ", ".join(item["speaker_label"] for item in result.get("reels", []))
            self.write(f"Audition reels ready: {labels}")
            messagebox.showinfo("Audition reels ready", "Open Last Audition Reels and listen to each short WAV. Labels are still unverified.")
        except Exception as exc:
            self.write(f"ERROR: {exc}")
            messagebox.showerror("Audition reels failed", str(exc))
    def open_last_audition_reels(self):
        if not self.last_pack:
            messagebox.showwarning("Pack needed", "Build or download a candidate pack in this window first.")
            return
        path = Path(self.last_pack) / "speaker_separation" / "review_reels"
        if not path.exists():
            messagebox.showwarning("Reels not ready", "Click Build Group Audition Reels first.")
            return
        subprocess.Popen(["explorer", str(path)])
    def open_packs(self):
        path = PROJECT_ROOT / "Voice" / "reference_packs"; path.mkdir(parents=True, exist_ok=True); subprocess.Popen(["explorer", str(path)])
    def check(self):
        run = subprocess.run([sys.executable, str(PROJECT_ROOT / "tools" / "check_voice_pipeline.py")], capture_output=True, text=True, timeout=30, check=False); self.write(run.stdout or run.stderr)

def main(): root = Tk(); VoiceReferenceCenter(root); root.mainloop()
if __name__ == "__main__": main()




