#!/bin/sh
# Poste de depannage branche sur Gi0/7 de SW-ETAGE2 (VLAN bureautique 10).
# On retire la route par defaut du lien "bureautique" pour ne garder que le L2.
LAN=$(ip -o -4 addr show | awk '$4 ~ /^10\.10\.10\./ {print $2}')
ip route del 10.10.10.0/24 dev "$LAN" 2>/dev/null; ip route add 10.10.10.0/24 dev "$LAN"
exec /usr/sbin/sshd -D -e
