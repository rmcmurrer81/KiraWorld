"""Optional manual loopback server. Does not open a browser or modify worlds."""
from pathlib import Path
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
import argparse,functools
def main():
 p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=0);a=p.parse_args()
 handler=functools.partial(SimpleHTTPRequestHandler,directory=str(Path(__file__).resolve().parent))
 with ThreadingHTTPServer(('127.0.0.1',a.port),handler) as server:
  print(f'Experimental package consumer: http://127.0.0.1:{server.server_port}/',flush=True)
  try:server.serve_forever()
  except KeyboardInterrupt:pass
if __name__=='__main__':main()
