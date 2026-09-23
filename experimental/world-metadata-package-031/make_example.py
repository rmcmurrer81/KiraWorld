"""Create a new synthetic-only example; existing files are never reused/overwritten."""
from pathlib import Path
import argparse,json,os
import package_writer as w
H=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('--destination',required=True);parser.add_argument('--core-root',default=str(H.parent/'world-scene-metadata-030'));args=parser.parse_args()
root=Path(args.destination).absolute();root.mkdir(exist_ok=False);sources=root/'synthetic_sources';sources.mkdir();core=Path(args.core_root).absolute()
cache=sources/'source.txt';cache.write_text('Authored synthetic research fixture for metadata-package validation. No owner memories or media.\n',encoding='utf-8')
pin=w.binding(cache);pin['path']=cache.name
packet=sources/'research_packet.json';packet.write_bytes(w.canonical({'packet_kind':'world_public_text_research_packet','research_mode':'analog_to_original','sources':[{'state':'retrieved_text','content_binding':pin,'text_binding':pin}]}))
blueprint=sources/'blueprint.json';blueprint.write_bytes(w.canonical({'research_packet_sha256':w.sha(packet.read_bytes()),'fixture':'synthetic_metadata_package'}))
geometry=sources/'geometry.json';data=json.loads((core/'fixtures/synthetic_habitat.json').read_text(encoding='utf-8'));data.update(research_packet_sha256=w.sha(packet.read_bytes()),blueprint_sha256=w.sha(w.canonical(json.loads(blueprint.read_bytes()))));geometry.write_bytes(w.canonical(data))
bindings=sources/'bindings.json';bindings.write_bytes(w.canonical({'contract':w.INPUT_CONTRACT,'inputs':{'geometry_source':w.binding(geometry),'blueprint':w.binding(blueprint),'research_packet':w.binding(packet)}}))
result=w.build_package(bindings,w.sha(bindings.read_bytes()),root/'package',scene_id='synthetic_habitat',core_root=core)
print(json.dumps(result))
