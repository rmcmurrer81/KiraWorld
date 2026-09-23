from pathlib import Path
import hashlib,json,difflib,shutil
H=Path(__file__).resolve().parent;K=Path('@kira_root');W=H.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=K/'tools/world_builder_workspace.py';baseline=H/'baseline/world_builder_workspace.py';candidate=H/'candidate/tools/world_builder_workspace.py'
baseline.parent.mkdir(parents=True,exist_ok=True);assert not baseline.exists() and not candidate.exists();shutil.copyfile(source,baseline)
old=source.read_text(encoding='utf-8');new=old.replace('from world_research_workspace_adapter import submit_research_prompt','from world_research_workspace_adapter import submit_research_prompt\nfrom world_chat_requests import classify_world_chat')
needle='''        self.chat_var.set("")
        try:
            submitted = submit_research_prompt(message, job_root=DEFAULT_JOB_ROOT, latest_job=self._research_latest)
'''
replacement='''        self.chat_var.set("")
        request = classify_world_chat(message)
        action = request["action"]
        if action == "status":
            self.show_world_chat_status()
            return
        if action == "open_latest":
            self.open_latest_saved_research()
            return
        if action == "preview":
            self.open_layout_preview()
            return
        if action == "export":
            self.export_3d_package()
            return
        if action not in {"research", "resume"}:
            if request.get("message"):
                self.log(request["message"])
            return
        try:
            submitted = submit_research_prompt(request["submit_prompt"], job_root=DEFAULT_JOB_ROOT, latest_job=self._research_latest)
'''
assert new.count(needle)==1;new=new.replace(needle,replacement)
needle='    def refresh_saved_research(self) -> None:\n'
methods='''    def show_world_chat_status(self) -> None:
        if self._research_latest is None:
            self.log("No saved world is selected. Choose one from Saved research / layouts, or ask to open the latest saved world.")
            return
        try:
            selected = read_saved_research(self._research_latest, job_root=DEFAULT_JOB_ROOT)
        except (OSError, ValueError) as exc:
            self.log(f"Saved status is unavailable: {exc}. No new research was started.")
            return
        self.log(f"Selected project: {selected['subject']} | saved research state: {selected['stage']}.")
        self.log("This reports saved research status, not completed world or visual approval. Use Open current preview to inspect any available layout.")

    def open_latest_saved_research(self) -> None:
        self.refresh_saved_research()
        if not self._saved_research_items:
            self.log("No saved research jobs or layouts were found. No new job was started.")
            return
        # The catalog is sorted newest first. Do not silently substitute an
        # older valid world when the newest job is damaged or cannot be read.
        self.saved_research_choice.current(0)
        self.select_saved_research()

'''
assert new.count(needle)==1;new=new.replace(needle,methods+needle)
candidate.write_text(new,encoding='utf-8',newline='\n')
(H/'CHANGES.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='installed046/world_builder_workspace.py',tofile='candidate047/world_builder_workspace.py')),encoding='utf-8',newline='\n')
protected=json.loads((W/'world-chat-usability-audit-046/REVIEW-PLAN.json').read_bytes())['protected_inputs'];assert all(sha(Path(p))==v for p,v in protected.items())
helper=H/'candidate/tools/world_chat_requests.py';assert not (K/'tools/world_chat_requests.py').exists()
plan={'status':'ISOLATED_NOT_APPROVED_FOR_INSTALL','files':[{'relative_path':'tools/world_builder_workspace.py','target':str(source),'before_sha256':sha(source),'preimage':str(baseline),'after':{'path':str(candidate),'sha256':sha(candidate),'bytes':candidate.stat().st_size}},
    {'relative_path':'tools/world_chat_requests.py','target':str(K/'tools/world_chat_requests.py'),'before_sha256':None,'preimage':None,'after':{'path':str(helper),'sha256':sha(helper),'bytes':helper.stat().st_size}}],'protected_inputs':protected}
with (H/'REVIEW-PLAN.json').open('x',encoding='utf-8') as f:json.dump(plan,f,indent=2);f.write('\n')
print(json.dumps({'status':'047_DISPATCHER_STAGED','review_plan_sha256':sha(H/'REVIEW-PLAN.json'),'canonical_writes':0}))
