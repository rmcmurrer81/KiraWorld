"""Correct deep Windows package test paths before freezing any publication manifest."""
from pathlib import Path
import hashlib,json
H=Path(__file__).resolve().parent;P=H/'payload/experimental/world-immutable-preview-026'
assert not (H/'DELIVERY.json').exists()
source=P/'test_compatibility.py';text=source.read_text();assert "dir=H" in text
text=text.replace("def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()", "def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()\nTEST_TEMP_BASE=Path(tempfile.gettempdir()).resolve()")
text=text.replace("TemporaryDirectory(prefix='preview026-',dir=H)", "TemporaryDirectory(prefix='preview026-',dir=TEST_TEMP_BASE)")
text=text.replace("self.root.is_relative_to(H.resolve())", "self.root.parent==TEST_TEMP_BASE and self.root.name.startswith('preview026-')")
source.write_text(text,encoding='utf-8')
readme=P/'README.md';text=readme.read_text().replace('creates disposable test-only directories under this package','creates uniquely named disposable test-only directories under the OS temporary directory (to avoid deep Windows checkout path limits)')
text+='\nThe first packaged run hit Windows path-length limits during setup, before any behavioral assertion or real Node preflight ran. The portable runner now uses a checked, uniquely named OS temporary directory. The failed receipt is preserved beside the corrected run; this was a packaging-path failure, not a backend behavior result.\n'
readme.write_text(text,encoding='utf-8')
inventory=json.loads((H/'SOURCE-INVENTORY.json').read_text())
for row in inventory['files']:
    if row['path'] in [str(p.relative_to(H/'payload').as_posix()) for p in (source,readme)]:
        data=(H/'payload'/row['path']).read_bytes();row.update(sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),adaptation='Portable dependency/Node paths, bounded short OS test-temp root and separate fresh receipts; original behavioral assertions unchanged. Documented first path-limit setup failure.')
(H/'SOURCE-INVENTORY.json').write_text(json.dumps(inventory,indent=2)+'\n')
print(json.dumps({'status':'PORTABLE_TEST_PATHS_CORRECTED','canonical_or_owner_writes':False}))
