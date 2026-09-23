from pathlib import Path
import hashlib,json,difflib,shutil
H=Path(__file__).resolve().parent;K=Path('@kira_root');source=K/'tools/world_builder_workspace.py'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
baseline=H/'baseline/world_builder_workspace.py';candidate=H/'candidate/tools/world_builder_workspace.py'
for p in (baseline,candidate):p.parent.mkdir(parents=True,exist_ok=True);assert not p.exists()
shutil.copyfile(source,baseline);old=source.read_text(encoding='utf-8')
needle='''        self._research_latest = submitted["job_dir"]
        self.latest_folder = submitted["job_dir"]
        self.refresh_saved_research()
'''
replacement='''        if submitted["job_dir"] != self._research_latest:
            # Chat submission selects a world just like the saved-job chooser.
            # Do not let its export capture the previous world's preview, or
            # leave reference/component windows showing the previous selection.
            self.set_saved_research_context(submitted["job_dir"])
        self.latest_folder = submitted["job_dir"]
        self.refresh_saved_research()
'''
assert old.count(needle)==1;new=old.replace(needle,replacement)
candidate.write_text(new,encoding='utf-8',newline='\n')
(H/'CHANGES.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='installed045/world_builder_workspace.py',tofile='candidate046/world_builder_workspace.py')),encoding='utf-8',newline='\n')
relative=['tools/world_builder_workspace.py','tools/world_research_workspace_adapter.py','tools/world_research.py','tools/world_saved_research.py','tools/world_builder_engine/workspace_adapter.py','tools/world_builder_engine/pipeline.py','tools/world_builder_engine/layout_package_export.py','tools/world_builder_engine/preview_refresh.py']
protected=json.loads((H.parent/'world-galley-detail-045/INSTALL-PLAN.json').read_bytes())['protected_inputs'];assert all(sha(Path(p))==v for p,v in protected.items())
plan={'status':'ISOLATED_NOT_APPROVED_FOR_INSTALL','files':[{'relative_path':'tools/world_builder_workspace.py','target':str(source),'before_sha256':sha(source),'preimage':str(baseline),'after':{'path':str(candidate),'sha256':sha(candidate),'bytes':candidate.stat().st_size}}],'protected_inputs':protected}
with (H/'REVIEW-PLAN.json').open('x',encoding='utf-8') as f:json.dump(plan,f,indent=2);f.write('\n')
with (H/'SOURCE-PINS.json').open('x',encoding='utf-8') as f:json.dump({r:sha(K/r) for r in relative},f,indent=2);f.write('\n')
print(json.dumps({'status':'046_ISOLATED_CHAT_CONTEXT_FIX_STAGED','candidate_sha256':sha(candidate),'review_plan_sha256':sha(H/'REVIEW-PLAN.json'),'canonical_writes':0}))
