#!/bin/sh
# A lancer sur l'HOTE apres `docker compose up -d --build`.
# Regle les prerequis noyau/bridge communs aux labs FRR/MPLS, met le segment
# core en mode "hub" (pour le sniff), puis (re)applique LDP une fois le
# multicast autorise, et attend la convergence.
set -e
PFX=ctf-tunnel-mpls

sysctl -w vm.overcommit_memory=1 >/dev/null
sysctl -w net.bridge.bridge-nf-call-iptables=0 >/dev/null

for net in ${PFX}_l12 ${PFX}_l23; do
  id=$(docker network inspect "$net" -f '{{.Id}}' 2>/dev/null | cut -c1-12) || continue
  br="br-$id"; [ -d /sys/class/net/$br ] || continue
  ip link set "$br" type bridge mcast_snooping 0 2>/dev/null || true   # LDP multicast
  if [ "$net" = "${PFX}_l23" ]; then
    for p in $(ls /sys/class/net/$br/brif 2>/dev/null); do
      bridge link set dev "$p" learning off flood on 2>/dev/null || true  # hub/SPAN
    done
  fi
done

echo "[*] (re)application LDP sur les routeurs..."
sleep 3
for r in pe1 p pe2; do docker exec ${PFX}-${r}-1 vtysh -f /ldp.conf >/dev/null 2>&1 || true; done

echo "[*] attente convergence (OSPF/LDP/VPNv4)..."
sleep 45
echo "[+] setup hote termine."
