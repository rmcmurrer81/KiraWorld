"""Explicitly prepare one remaining repair from an exact held state; no model call."""
from pathlib import Path
import argparse,json,sys
if __package__ in (None,''):sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from world_builder_engine.pipeline import prepare_repair_revision

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job',required=True);parser.add_argument('--expected-state-sha256',required=True)
    args=parser.parse_args()
    result=prepare_repair_revision(args.job,args.expected_state_sha256)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
