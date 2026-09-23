"""Fresh-process entry point so native and frozen research imports cannot collide."""
from pathlib import Path
import argparse,json,sys

if __package__ in (None,''):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from world_builder_engine.pipeline import run_pipeline


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--job',required=True)
    args=parser.parse_args()
    def progress(value):print(json.dumps({'kind':'progress','value':value},ensure_ascii=False),flush=True)
    try:result=run_pipeline(args.job,on_progress=progress)
    except Exception as exc:result={'stage':'pipeline_held','message':type(exc).__name__+': '+str(exc),'geometry_generated':False,'world_ready':False}
    print(json.dumps({'kind':'finished','value':result},ensure_ascii=False),flush=True)


if __name__=='__main__':main()
