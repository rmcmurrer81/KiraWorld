"""Read-only loopback asset server for one bounded disposable World preview."""
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlsplit
import argparse
import datetime
import hashlib
import json
import time

H=Path(__file__).resolve().parent
K=Path('@user_home/Kira')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,obj):
 with p.open('x',encoding='utf-8') as f:json.dump(obj,f,indent=2);f.write('\n')
parser=argparse.ArgumentParser()
parser.add_argument('--expected-plan-sha256',required=True)
args=parser.parse_args()
assert sha(H/'PLAN.json')==args.expected_plan_sha256,'Preview plan changed'
plan=json.loads((H/'PLAN.json').read_text(encoding='utf-8'))
assert not (H/'SERVER-STARTED.json').exists(),'Consumed preview; preserve it'
def unchanged(rows):return all(Path(r['path']).is_file() and sha(Path(r['path']))==r['sha256'] for r in rows)
assert unchanged(plan['inputs']) and unchanged(plan['assets'].values()),'Inputs or assets changed'
assert all(sha(K/name)==digest for name,digest in plan['owner_files_before'].items()),'Owner files changed since staging'
types={'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.mjs':'text/javascript; charset=utf-8','.js':'text/javascript; charset=utf-8','.json':'application/json; charset=utf-8','.txt':'text/plain; charset=utf-8'}
request_count=0
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_HEAD(self):self.respond(False)
 def do_GET(self):self.respond(True)
 def respond(self,body):
  global request_count
  request_count+=1
  expected='127.0.0.1:'+str(self.server.server_port)
  if self.headers.get_all('Host')!=[expected]:self.send_error(403);return
  split=urlsplit(self.path)
  if split.scheme or split.netloc or split.query or split.fragment or '%' in self.path or '\\' in self.path:self.send_error(404);return
  name='index.html' if self.path=='/' else self.path.removeprefix('/')
  row=plan['assets'].get(name)
  if row is None:self.send_error(404);return
  p=Path(row['path'])
  if sha(H/'PLAN.json')!=args.expected_plan_sha256 or sha(p)!=row['sha256']:self.send_error(409);return
  payload=p.read_bytes();self.send_response(200)
  self.send_header('Content-Type',types[p.suffix]);self.send_header('Content-Length',str(len(payload)))
  self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
  self.send_header('Referrer-Policy','no-referrer')
  self.send_header('Content-Security-Policy',"default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; media-src 'none'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'")
  self.end_headers()
  if body:self.wfile.write(payload)

server=HTTPServer(('127.0.0.1',0),Handler);server.timeout=.5
start=time.monotonic();url='http://127.0.0.1:'+str(server.server_port)+'/'
write(H/'SERVER-STARTED.json',{'status':'READ_ONLY_LOOPBACK_PREVIEW','url':url,'plan_sha256':args.expected_plan_sha256,'max_wall_seconds':300,'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
print(json.dumps({'url':url,'max_wall_seconds':300,'starts_paused':True}),flush=True)
reason='300_SECOND_LIMIT'
try:
 while time.monotonic()-start<300:server.handle_request()
except KeyboardInterrupt:reason='SUPERVISOR_STOP'
finally:
 server.server_close()
 result={'status':'CLOSED','reason':reason,'seconds':time.monotonic()-start,'request_count':request_count,'inputs_unchanged':unchanged(plan['inputs']),'assets_unchanged':unchanged(plan['assets'].values()),'owner_files_unchanged':all(sha(K/name)==digest for name,digest in plan['owner_files_before'].items()),'installed':False,'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 write(H/'SERVER-CLOSED.json',result);print(json.dumps(result),flush=True)
