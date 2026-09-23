"""Add read-only callbacks to disposable copies; original candidate stays frozen."""
from pathlib import Path
import hashlib,json,difflib
HERE=Path(__file__).resolve().parent
rows=[];patch=[]
for group in ['baseline','candidate']:
    for name in ['bedding_base.mjs','frame_contacts.mjs','mattress_physics.mjs','surface_contacts.mjs']:
        source=HERE/group/name;data=source.read_bytes()
        path=HERE/'diagnostic'/group/name;path.parent.mkdir(parents=True,exist_ok=True)
        if name=='mattress_physics.mjs' and group=='baseline':
            text=data.decode('utf-8').replace('if(y<sample.height+m){',
                "if(y<sample.height+m){\n        globalThis.captureTopDiagnostic?.('baseline','particle_before_top_projection',c,surface,[i],{sampleHeight:sample.height,destinationY:sample.height+m});")
            data=text.encode('utf-8')
        if name=='surface_contacts.mjs' and group=='candidate':
            text=data.decode('utf-8').replace(' return true;\n}\n\nfunction topology',
                " globalThis.captureTopDiagnostic?.('candidate','eligible_whole_primitive',cloth,surface,ids,{});\n return true;\n}\n\nfunction topology")
            assert 'captureTopDiagnostic' in text
            data=text.encode('utf-8')
        with path.open('xb') as stream:stream.write(data)
        rows.append({'source':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
                     'copy':path.relative_to(HERE).as_posix(),'sha256':hashlib.sha256(data).hexdigest()})
        patch.extend(difflib.unified_diff(source.read_text(encoding='utf-8').splitlines(),data.decode().splitlines(),fromfile=f'{group}/{name}',tofile=f'diagnostic/{group}/{name}',lineterm=''))
(HERE/'DIAGNOSTIC-PATCH.txt').write_text('\n'.join(patch)+'\n',encoding='utf-8')
(HERE/'DIAGNOSTIC-PINS.json').write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'copies':len(rows),'source_unchanged':True,'callbacks':'two disposable callsites only'}))
