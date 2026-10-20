#!/usr/bin/env python3
"""Solveur cloison-vlan.

Le port Gi0/7 du poste est reste en trunk (natif 10, autorise 10,99).
Depuis le poste, on cree une sous-interface 802.1Q VLAN 99, on prend une IP
libre du reseau management et on interroge SRV-RH.
"""
import re
import sys

import paramiko

HOST = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 1344

CMDS = r"""
LAN=$(ip -o -4 addr show | awk '$4 ~ /^10\.10\.10\./ {print $2}')
ip link add link "$LAN" name vlan99 type vlan id 99 2>/dev/null
ip addr add 10.10.99.50/24 dev vlan99 2>/dev/null
ip link set vlan99 up
sleep 1
curl -s -m 5 http://10.10.99.10/
"""


def main():
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(HOST, port=PORT, username="root", password="Depannage2026")
    _, out, _ = c.exec_command(CMDS)
    body = out.read().decode()
    c.close()
    m = re.search(r"FPS\{[^}]+\}", body)
    print(m.group(0) if m else "echec:\n" + body)


if __name__ == "__main__":
    main()
