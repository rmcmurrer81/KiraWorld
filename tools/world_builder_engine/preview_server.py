"""Owned exact-file loopback server for one verified original-layout preview."""
from pathlib import Path
import argparse,json,sys
if __package__ in (None,''):sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from world_builder_engine.world_layout_preview import make_server
from world_builder_engine.pipeline import latest_preview


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job',required=True)
    args=parser.parse_args()
    manifest=latest_preview(args.job)
    server=make_server(manifest['manifest_path'],0,manifest['manifest_sha256'])
    print(json.dumps({'url':'http://127.0.0.1:'+str(server.server_port)+'/','manifest':manifest}),flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()


if __name__=='__main__':main()
