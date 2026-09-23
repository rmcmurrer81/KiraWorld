from pathlib import Path
import difflib
import hashlib
import json
H=Path(__file__).resolve().parent
K=Path('@user_home/Kira')
source=K/'tools/world_builder_workspace.py'
baseline=H/'baseline';baseline.mkdir(exist_ok=False)
candidate=H/'candidate/tools';candidate.mkdir(parents=True,exist_ok=False)
raw=source.read_bytes();(baseline/'world_builder_workspace.py').write_bytes(raw)
t=raw.decode('utf-8')
t=t.replace('from world_research_workspace_adapter import submit_research_prompt','from world_research_workspace_adapter import submit_research_prompt\nfrom world_saved_research import list_saved_research, read_saved_research')
t=t.replace('        self._research_latest = None','        self._research_latest = None\n        self._saved_research_items = []',1)
t=t.replace('        self.refresh_index()\n        self.refresh_school_status()', '        self.refresh_index()\n        self.refresh_saved_research()\n        self.refresh_school_status()')
anchor='        components = ttk.Frame(chat)'
added='''        saved = ttk.Frame(chat)
        saved.pack(fill="x", pady=(7, 0))
        ttk.Label(saved, text="Saved research / layouts").pack(side="left", padx=(0, 6))
        self.saved_research_choice = ttk.Combobox(saved, state="readonly")
        self.saved_research_choice.pack(side="left", fill="x", expand=True)
        self.saved_research_choice.bind("<<ComboboxSelected>>", self.select_saved_research)
        ttk.Button(saved, text="Refresh saved", command=self.refresh_saved_research).pack(side="left", padx=(6, 0))

'''
assert anchor in t;t=t.replace(anchor,added+anchor,1)
anchor='    def _start_next_research(self) -> None:'
methods='''    def refresh_saved_research(self) -> None:
        try:
            self._saved_research_items = list_saved_research(DEFAULT_JOB_ROOT)
        except (OSError, ValueError) as exc:
            self._saved_research_items = []
            self.log(f"Saved research list unavailable: {exc}")
        self.saved_research_choice.configure(values=[item["label"] for item in self._saved_research_items])
        selected = next((index for index, item in enumerate(self._saved_research_items)
                         if item["job_dir"] == self._research_latest), None)
        if selected is None:
            self.saved_research_choice.set("Choose a saved research job" if self._saved_research_items else "No saved research jobs yet")
        else:
            self.saved_research_choice.current(selected)

    def select_saved_research(self, _event=None) -> None:
        index = self.saved_research_choice.current()
        if index < 0 or index >= len(self._saved_research_items):
            return
        item = self._saved_research_items[index]
        try:
            selected = read_saved_research(item["job_dir"], job_root=DEFAULT_JOB_ROOT)
        except (OSError, ValueError) as exc:
            self._research_latest = None
            self.latest_folder = None
            self.latest_request = None
            close_preview(self._layout_preview)
            self._layout_preview = None
            self.log(f"Saved research could not be opened: {exc}. Its files were preserved.")
            return
        close_preview(self._layout_preview)
        self._layout_preview = None
        self._research_latest = selected["job_dir"]
        self.latest_folder = selected["job_dir"]
        self.latest_request = None
        self.log(f"Opened saved research: {selected['subject']} | {selected['stage']}")
        self.log("Use Open Layout Preview or Reference Photos to inspect saved results. No research or generation was started.")

'''
assert anchor in t;t=t.replace(anchor,methods+anchor,1)
t=t.replace('        self.latest_folder = submitted["job_dir"]','        self.latest_folder = submitted["job_dir"]\n        self.refresh_saved_research()',1)
t=t.replace('        if completed:\n            self._research_worker = None','        if completed:\n            self.refresh_saved_research()\n            self._research_worker = None',1)
dest=candidate/'world_builder_workspace.py';dest.write_text(t,encoding='utf-8',newline='\n')
(H/'CHANGES.patch').write_text(''.join(difflib.unified_diff(raw.decode('utf-8').splitlines(True),t.splitlines(True),fromfile='installed/world_builder_workspace.py',tofile='candidate/world_builder_workspace.py')),encoding='utf-8')
manifest={'installed_baseline':{'path':str(source),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)},'candidate_workspace':{'path':str(dest),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()},'installed':False,'no_model_calls':True,'issue':'After restart saved research jobs cannot be selected without queuing resume/generation.'}
(H/'STAGING.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print(json.dumps(manifest))
