"""Stage one reversed-order pilot without changing consumed 020 evidence."""
from pathlib import Path
import hashlib
import json

H = Path(__file__).resolve().parent
D = H / 'reversed-pilot-001'
D.mkdir(exist_ok=False)
text = (H / 'check_paired.mjs').read_text(encoding='utf-8')
text = text.replace("from './candidate/", "from '../candidate/")
text = text.replace("from '../world-finite-key-candidate-019/", "from '../../world-finite-key-candidate-019/")
before = "let now=performance.now();const ma=a.step(1);fastMs+=performance.now()-now;\n  now=performance.now();const mb=b.step(1);oldMs+=performance.now()-now;"
after = "let now=performance.now();const mb=b.step(1);oldMs+=performance.now()-now;\n  now=performance.now();const ma=a.step(1);fastMs+=performance.now()-now;"
assert before in text
text = text.replace(before, after)
text = text.replace('One candidate-first short mixed-process timing;', 'One predecessor-first short mixed-process timing;')
script = D / 'check_paired.mjs'
script.write_text(text, encoding='utf-8', newline='\n')
runner = H / 'run_checks.py'
(D / runner.name).write_bytes(runner.read_bytes())
plan = json.loads((H / 'PLAN.json').read_text())
plan['status'] = 'ISOLATED_REVERSED_ORDER_CONFIRMATION'
plan['order'] = '019 predecessor first then 020 candidate each frame; compare with preserved candidate-first pilot.'
for p in [script, D / runner.name]:
    b = p.read_bytes()
    plan['sources'].append({'path': str(p), 'sha256': hashlib.sha256(b).hexdigest(), 'bytes': len(b)})
(D / 'PLAN.json').write_text(json.dumps(plan, indent=2)+'\n', encoding='utf-8')
print(json.dumps({'directory':str(D),'status':plan['status']}))
