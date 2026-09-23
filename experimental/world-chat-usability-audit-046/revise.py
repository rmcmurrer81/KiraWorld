from pathlib import Path
import hashlib,json,difflib,shutil
H=Path(__file__).resolve().parent;history=H/'history/initial';history.mkdir(parents=True,exist_ok=False)
candidate=H/'candidate/tools/world_builder_workspace.py'
for p in [candidate,H/'REVIEW-PLAN.json',H/'CHANGES.patch']:shutil.copyfile(p,history/p.name)
new=candidate.read_text(encoding='utf-8').replace('            self.set_saved_research_context(submitted["job_dir"])\n        self.refresh_saved_research()', '            self.set_saved_research_context(submitted["job_dir"])\n        self.latest_folder = submitted["job_dir"]\n        self.refresh_saved_research()')
candidate.write_text(new,encoding='utf-8',newline='\n')
old=(H/'baseline/world_builder_workspace.py').read_text(encoding='utf-8')
(H/'CHANGES.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='installed045/world_builder_workspace.py',tofile='candidate046/world_builder_workspace.py')),encoding='utf-8',newline='\n')
plan=json.loads((H/'REVIEW-PLAN.json').read_bytes());plan['files'][0]['after'].update(sha256=hashlib.sha256(candidate.read_bytes()).hexdigest(),bytes=candidate.stat().st_size)
(H/'REVIEW-PLAN.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
receipt=H/'CANDIDATE-CHAT-CAPTURES.json';assert receipt.resolve().is_relative_to(H.resolve());receipt.rename(history/'CANDIDATE-CHAT-CAPTURES.json')
print('Restored same-job latest_folder behavior; no canonical changes.')
