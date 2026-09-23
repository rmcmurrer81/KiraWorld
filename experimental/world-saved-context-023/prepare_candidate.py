"""Preserve022; stage context switching for all already-open child views."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil
H=Path(__file__).resolve().parent
OLD=H.parent/'world-saved-research-selector-candidate-022'
K=Path('@user_home/Kira')
shutil.copytree(OLD/'candidate',H/'candidate')
shutil.copytree(OLD/'baseline',H/'baseline')
p=H/'candidate/tools/world_builder_workspace.py'
t=p.read_text(encoding='utf-8')
before='''            self._research_latest = None
            self.latest_folder = None
            self.latest_request = None
            close_preview(self._layout_preview)
            self._layout_preview = None
'''
assert t.count(before)==1;t=t.replace(before,'            self.set_saved_research_context(None)\n')
before='''        close_preview(self._layout_preview)
        self._layout_preview = None
        self._research_latest = selected["job_dir"]
        self.latest_folder = selected["job_dir"]
        self.latest_request = None
'''
assert t.count(before)==1;t=t.replace(before,'        self.set_saved_research_context(selected["job_dir"])\n')
anchor='    def _start_next_research(self) -> None:'
helper='''    def set_saved_research_context(self, job_dir: Path | None) -> None:
        close_preview(self._layout_preview)
        self._layout_preview = None
        if self._reference_photos_view is not None and self._reference_photos_view.winfo_exists():
            self._reference_photos_view.destroy()
        self._reference_photos_view = None
        if self._original_components_view is not None and self._original_components_view.winfo_exists():
            self._original_components_view.set_world_job(job_dir)
        self._research_latest = job_dir
        self.latest_folder = job_dir
        self.latest_request = None

'''
assert anchor in t;t=t.replace(anchor,helper+anchor,1)
p.write_text(t,encoding='utf-8',newline='\n')
old=(OLD/'candidate/tools/world_builder_workspace.py').read_text(encoding='utf-8')
(H/'CHANGES-FROM-022.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),t.splitlines(True),fromfile='022/world_builder_workspace.py',tofile='023/world_builder_workspace.py')),encoding='utf-8')
baseline=(H/'baseline/world_builder_workspace.py').read_text(encoding='utf-8')
(H/'CHANGES-FROM-INSTALLED.patch').write_text(''.join(difflib.unified_diff(baseline.splitlines(True),t.splitlines(True),fromfile='installed/world_builder_workspace.py',tofile='023/world_builder_workspace.py')),encoding='utf-8')
tests=(OLD/'test_saved_research.py').read_text(encoding='utf-8')
tests=tests.replace("candidate022_workspace","candidate023_workspace").replace("prefix='world022-'","prefix='world023-'")
tests=tests.replace("a._layout_preview='previous-preview';a.saved_research_choice=Choice();a.messages=[];a.log=a.messages.append", "a._layout_preview='previous-preview';a.saved_research_choice=Choice();a.messages=[];a.log=a.messages.append\n        a._reference_photos_view=None;a._original_components_view=None")
tests=tests.replace("H/'TEST-RESULT-002.json'","H/'TEST-RESULT.json'")
(H/'test_saved_research.py').write_text(tests,encoding='utf-8',newline='\n')
(H/'BASELINE.json').write_text(json.dumps({'installed_workspace':str(K/'tools/world_builder_workspace.py'),'sha256':hashlib.sha256((K/'tools/world_builder_workspace.py').read_bytes()).hexdigest(),'predecessor022_preserved':True},indent=2)+'\n',encoding='utf-8')
print(str(H))
