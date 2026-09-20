"""Pinned, local-only bedding study and explicit bounded recording endpoint."""
from __future__ import annotations
import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from urllib.parse import urlsplit
import sys
if __package__ in (None, ''):
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from world_builder_components.bedding.local_recordings import RecordingError, parse_upload_headers, plain_directory, save_webm

TYPES = {'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.mjs':'text/javascript; charset=utf-8','.js':'text/javascript; charset=utf-8','.txt':'text/plain; charset=utf-8','.json':'application/json; charset=utf-8'}
from world_builder_components.bedding.jobs import verify_study, STUDY_ROOT
from world_builder_components.component_jobs import exact as read, COMPONENT_ROOT

def require(ok, message):
    if not ok: raise ValueError(message)

def make_server(path,expected,port=0,*,output_root=STUDY_ROOT,frame_root=COMPONENT_ROOT):
    manifest,manifest_raw=verify_study(path,expected,output_root=output_root,frame_root=frame_root);save_lock=threading.Lock()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*_): pass
        def same_origin(self,post=False):
            origin='http://127.0.0.1:'+str(self.server.server_port)
            return self.headers.get_all('Host')==[origin[7:]] and self.headers.get_all('Origin',[] if post else [origin])==[origin]
        def do_HEAD(self): self.respond(False)
        def do_GET(self): self.respond(True)
        def do_POST(self):
            self.close_connection=True
            if not self.same_origin(True):self.send_error(403);return
            if self.path!='/recordings':self.send_error(404);return
            if self.headers.get_all('Content-Encoding'):self.send_error(415);return
            if not save_lock.acquire(blocking=False):self.send_error(429);return
            try:
                require(Path(path).read_bytes()==manifest_raw,'Manifest changed')
                read(manifest['sources']['preview_server.py']);read(manifest['sources']['local_recordings.py'])
                length,mime=parse_upload_headers(self.headers)
                result=save_webm(Path(path).parent,self.rfile,length,mime,self.connection.settimeout)
                payload=json.dumps(result).encode();self.send_response(201);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(payload)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(payload)
            except (ValueError,OSError,RecordingError) as error:self.send_error(400,str(error))
            finally:save_lock.release()
        def respond(self,body):
            if not self.same_origin():self.send_error(403);return
            split=urlsplit(self.path)
            if split.scheme or split.netloc or split.query or split.fragment or '%'in self.path or '\\'in self.path:self.send_error(404);return
            name='/index.html' if self.path=='/' else self.path;row=manifest['assets'].get(name)
            if row is None:self.send_error(404);return
            try:require(Path(path).read_bytes()==manifest_raw,'Manifest changed');payload=read(row)
            except (ValueError,OSError):self.send_error(409);return
            self.send_response(200);self.send_header('Content-Type',TYPES[Path(name).suffix]);self.send_header('Content-Length',str(len(payload)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer')
            self.send_header('Content-Security-Policy',"default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; media-src blob:; object-src 'none'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            if body:self.wfile.write(payload)
    return ThreadingHTTPServer(('127.0.0.1',port),Handler)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--manifest',required=True);parser.add_argument('--sha256',required=True);parser.add_argument('--port',type=int,default=0);parser.add_argument('--verify-only',action='store_true');parser.add_argument('--study-root',default=str(STUDY_ROOT));parser.add_argument('--frame-root',default=str(COMPONENT_ROOT));args=parser.parse_args()
    if args.verify_only:
        manifest,_=verify_study(args.manifest,args.sha256,output_root=args.study_root,frame_root=args.frame_root);print(json.dumps({'status':'PASS','assets':len(manifest['assets'])}))
    else:
        server=make_server(args.manifest,args.sha256,args.port,output_root=args.study_root,frame_root=args.frame_root);print(json.dumps({'url':'http://127.0.0.1:'+str(server.server_port)+'/', 'manifest':args.manifest}),flush=True)
        try:server.serve_forever()
        except KeyboardInterrupt:pass
        finally:server.server_close()
