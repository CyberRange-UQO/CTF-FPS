#!/bin/sh
# Site 1 de CLIENT-C. Route vers le reste du VPN via le PE.
ip route replace default via 192.168.11.1 2>/dev/null
python3 - <<'PY'
import socket, time
N3 = "FPS{mpls_l3vpn_depile_les_labels_et_lis_le_vpn}"
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(("192.168.11.2", 0))
while True:
    # telemetrie applicative vers le serveur du site 2 (port 9514)
    s.sendto(f"CLIENT-C telemetry site1 token={N3}".encode(), ("192.168.22.2", 9514))
    time.sleep(4)
PY
