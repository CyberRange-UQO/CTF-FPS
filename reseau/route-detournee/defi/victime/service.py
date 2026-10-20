#!/usr/bin/env python3
# SRV-BANQUE : recoit les battements de coeur signes des clients.
from http.server import BaseHTTPRequestHandler, HTTPServer

class H(BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(n).decode("utf-8", "replace")
        print("heartbeat recu:", body, flush=True)
        self.send_response(200); self.end_headers()
        self.wfile.write(b"OK\n")
    def log_message(self, *a): pass

HTTPServer(("0.0.0.0", 80), H).serve_forever()
