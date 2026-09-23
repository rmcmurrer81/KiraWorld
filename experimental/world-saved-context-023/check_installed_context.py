"""Read-only installed imports and saved-context callbacks; no native window."""
from pathlib import Path
import hashlib
import json
import sys
from unittest.mock import patch
H=Path(__file__).resolve().parent;K=Path('@user_home/Kira')
sys.path.insert(0,str(K/'tools'))
import world_builder_workspace as workspace
import world_saved_research as saved
assert Path(workspace.__file__).resolve()==K/'tools/world_builder_workspace.py'
assert Path(saved.__file__).resolve()==K/'tools/world_saved_research.py'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def inventory():return {str(p.relative_to(K)).replace('\\','/'):sha(p) for folder in ['Data/world_research_jobs','Data/world_original_components','Data/world_bedding_studies'] for p in sorted((K/folder).rglob('*')) if p.is_file()}
before=inventory();installed=json.loads((H/'INSTALLED.json').read_text(encoding='utf-8'))
assert all(sha(Path(r['target']))==r['source']['sha256'] for r in installed['files'])
class Choice:
 def __init__(self):self.index=-1
 def configure(self,**kw):self.values=kw['values']
 def current(self,index=None):
  if index is not None:self.index=index
  return self.index
 def set(self,text):self.text=text;self.index=-1
class View:
 def __init__(self):self.exists=True;self.jobs=[];self.closed=False
 def winfo_exists(self):return self.exists
 def destroy(self):self.exists=False;self.closed=True
 def set_world_job(self,path):self.jobs.append(path)
a=object.__new__(workspace.WorldBuilderWorkspace)
a._research_latest=None;a._saved_research_items=[];a._layout_preview=None;a._reference_photos_view=None
a._original_components_view=View();a.saved_research_choice=Choice();a.latest_folder=None;a.latest_request=None
messages=[];a.log=messages.append
checks=[]
with patch.object(workspace,'run_job',side_effect=AssertionError('No research permitted')),patch.object(workspace,'run_pipeline_after_research',side_effect=AssertionError('No model permitted')),patch.object(workspace,'submit_research_prompt',side_effect=AssertionError('No job submission permitted')),patch.object(workspace,'close_preview') as close,patch.object(workspace,'open_preview',return_value='test-only-preview') as preview:
 a.refresh_saved_research();assert len(a._saved_research_items)==2
 checks.append('Installed catalog discovers both existing jobs without queuing work')
 for index,item in enumerate(a._saved_research_items):
  photos=View();a._reference_photos_view=photos;a._layout_preview='previous-test-only-preview'
  a.saved_research_choice.current(index);a.select_saved_research();a.open_layout_preview()
  assert a._research_latest==item['job_dir'] and a.latest_folder==item['job_dir']
  assert photos.closed and a._reference_photos_view is None
  assert a._original_components_view.jobs[-1]==item['job_dir']
  assert preview.call_args.args[0]==item['job_dir']
  checks.append('Installed selection restores exact job and updates all view contexts: '+item['job_id'])
 a._saved_research_items=[{'job_dir':H}];a.saved_research_choice.current(0);photos=View();a._reference_photos_view=photos
 a.select_saved_research();assert a._research_latest is None and a.latest_folder is None
 assert photos.closed and a._original_components_view.jobs[-1] is None
 checks.append('Foreign selection clears stale contexts without changing owner files')
after=inventory();assert before==after
assert all(sha(Path(r['target']))==r['source']['sha256'] for r in installed['files'])
result={'status':'PASS_INSTALLED_IMPORTS_AND_CONTEXT_CALLBACKS','checks':checks,'owner_files_checked':len(before),'owner_files_unchanged':True,'installed_source_pins_unchanged':True,'native_window_review':False,'network_models_gpu_or_real_preview_calls':0,'imported_files':[str(Path(workspace.__file__).resolve()),str(Path(saved.__file__).resolve())]}
with (H/'INSTALLED-CONTEXT-CHECK.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(result))
