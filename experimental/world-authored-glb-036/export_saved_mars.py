"""CPU prototype replay for the reviewed saved Mars fixture; no GPU/UI/downloads.

Explicit local dependencies and original saved-source bindings are required.
This is a mesh-package prototype, not an installed game/VR export feature.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json,subprocess,sys
HERE=Path(__file__).resolve().parent
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('bindings','bindings-sha256','metadata-package','writer-module','canvas-module','canvas-native','font-regular','font-semibold','font-monospace','node','output'):
        p.add_argument('--'+name,required=True)
    args=p.parse_args();output=Path(args.output).absolute()
    assert not output.exists() and output.parent.is_dir(),'Output must be a new directory'
    spec=importlib.util.spec_from_file_location('reviewed_writer034',args.writer_module);writer=importlib.util.module_from_spec(spec);spec.loader.exec_module(writer)
    geometry,bindings,input_pin=writer.source_chain(args.bindings,args.bindings_sha256)
    assert bindings['geometry_source']['sha256']=='1af9ae1254356f0523f722d284b140b8e34eb6af3bf236ceef91ad5f145a9d75','Prototype is scoped to the reviewed saved Mars fixture'
    package=Path(args.metadata_package);writer.verify_package(package)
    assert digest(package/'manifest.json')=='6e985befdbd466aafa3a7cf6a7306a236eefc70b97e0d6d3cd07724145e78e46','Reviewed034 package required'
    pinfile=HERE/'SOURCE-PINS.json';pins=json.loads(pinfile.read_text(encoding='utf-8'))
    external={'canvas-package':Path(args.canvas_module)/'package.json','canvas-native':Path(args.canvas_native),'font-segoe-regular':Path(args.font_regular),'font-segoe-semibold':Path(args.font-semibold),'font-monospace':Path(args.font_monospace)}
    codefiles=['authored_scene.mjs','build_glb.mjs','cpu_canvas.mjs','export_saved_mars.py']
    def verify():
        for rel,row in pins.items():assert digest(external.get(rel,HERE/rel))==row['sha256'],'Producer/dependency pin differs: '+rel
        for row in bindings.values():writer.exact(row)
    verify();source_raw=(package/'scene.json').read_bytes();metadata=json.loads(source_raw)
    request={'geometry':geometry,'metadata':metadata,'output':str(output),'canvasModule':str(Path(args.canvas_module).resolve()),
      'fontPaths':[[str(Path(args.font_regular).resolve()),'Segoe UI'],[str(Path(args.font-semibold).resolve()),'Segoe UI'],[str(Path(args.font_monospace).resolve()),'Consolas']]}
    output.mkdir(exist_ok=False)
    run=subprocess.run([args.node,str(HERE/'build_glb.mjs')],input=json.dumps(request).encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=120)
    verify()
    if run.returncode:raise RuntimeError('CPU export held: '+run.stderr.decode(errors='replace')[-1500:])
    (output/'scene.json').write_bytes(source_raw)
    (output/'README.txt').write_text('Original authored static mesh package with bound034 metadata. No engine/VR runtime or visual approval. See ROUNDTRIP.json for renderer limits. Source documents, fonts and native libraries are not included.\n',encoding='utf-8')
    report={'contract':'experimental_authored_world_glb_package_v1','source_bindings_manifest_sha256':input_pin['sha256'],'verified_source_digests':writer.portable_pins(bindings),
      'producer_digests':{k:{'bytes':v['bytes'],'sha256':v['sha256']} for k,v in pins.items()},'prototype_code':{f:digest(HERE/f) for f in codefiles},
      'files':{f.name:{'sha256':digest(f),'bytes':f.stat().st_size} for f in output.iterdir()},'metadata_only':False,'engine_or_vr_adapter':False,'installed':False,'visual_or_owner_approval':False}
    report['receipt_sha256']=writer.sha(writer.canonical(report));(output/'manifest.json').write_bytes(writer.canonical(report)+b'\n')
    print(json.dumps({'status':'PORTABLE_CPU_MARS_PACKAGE_CREATED','glb_sha256':digest(output/'scene.glb'),'manifest_sha256':digest(output/'manifest.json')}))
if __name__=='__main__':main()
