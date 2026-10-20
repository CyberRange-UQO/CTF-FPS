#!/bin/sh
ip route replace default via 192.168.22.1 2>/dev/null
python3 - <<'PY'
import socket, threading
N5 = "FPS{label_spoofing_mpls_traverse_l_isolation_vrf}"

def logger():  # recoit la telemetrie du site 1, ne repond pas
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("0.0.0.0", 9514))
    while True:
        s.recvfrom(2048)

def admin():   # service interne sensible : repond le secret a qui l'interroge
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("0.0.0.0", 5000))
    while True:
        data, addr = s.recvfrom(2048)
        s.sendto(f"ADMIN-API secret={N5}".encode(), addr)

threading.Thread(target=logger, daemon=True).start()
admin()
PY
