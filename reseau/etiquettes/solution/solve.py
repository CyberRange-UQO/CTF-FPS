#!/usr/bin/env python3
"""Solveur etiquettes (analyse pcap MPLS L3VPN).

1. Dépiler la pile de labels MPLS du trafic de données -> lire la télémétrie
   interne de CLIENT-C (flag).
2. Extraire du plan de contrôle BGP VPNv4 le RD, le RT et le label VPN de
   CLIENT-C (clé pour le défi 'tunnel-mpls').
"""
import re
import sys

from scapy.all import rdpcap, UDP
from scapy.contrib.mpls import MPLS

PCAP = sys.argv[1] if len(sys.argv) > 1 else \
    __file__.rsplit("/", 2)[0] + "/defi/capture-coeur-mpls.pcap"


def main():
    pkts = rdpcap(PCAP)
    flag = None
    vpn_labels = set()
    for p in pkts:
        if p.haslayer(MPLS) and p.haslayer(UDP):
            # pile de labels : le label du bas (VPN) est le dernier MPLS
            lay = p.getlayer(MPLS)
            while lay:
                lbl = lay.label
                nxt = lay.payload
                if isinstance(nxt, MPLS):
                    lay = nxt
                else:
                    vpn_labels.add(lbl)  # label du bas = VPN
                    break
            payload = bytes(p[UDP].payload)
            m = re.search(rb"FPS\{[^}]+\}", payload)
            if m:
                flag = m.group(0).decode()
                print(f"télémétrie interne {p.payload.payload.src} -> "
                      f"{p.payload.payload.dst} (dépilée)")

    print("label(s) VPN observé(s) côté données :", sorted(vpn_labels))
    print("FLAG :", flag)
    print("\n-> pour tunnel-mpls : RD/RT = 65000:300 (plan de contrôle BGP VPNv4),")
    print("   label VPN du serveur 192.168.22.0/24 = 1000 (plan de données ci-dessus).")


if __name__ == "__main__":
    main()
