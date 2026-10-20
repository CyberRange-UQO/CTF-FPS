#!/bin/sh
set -e
sed -i 's/^bgpd=no/bgpd=yes/' /etc/frr/daemons
sed -i 's|^zebra_options=.*|zebra_options="  -A 127.0.0.1 -s 1000000"|' /etc/frr/daemons
sysctl -w net.mpls.platform_labels=1048575 >/dev/null 2>&1 || true
rename_if() { dev=$(ip -o -4 addr show | awk -v p="$1" '$4 ~ "^"p {print $2; exit}'); [ -n "$dev" ] && [ "$dev" != "$2" ] && ip link set "$dev" down && ip link set "$dev" name "$2" && ip link set "$2" up; }
ip link add CLIENTA type vrf table 100; ip link set CLIENTA up
ip link add CLIENTB type vrf table 200; ip link set CLIENTB up
rename_if 192.168.1. custa; ip link set custa master CLIENTA
rename_if 192.168.2. custb; ip link set custb master CLIENTB
install -o frr -g frr -m 640 /frr.conf /etc/frr/frr.conf
exec /usr/lib/frr/docker-start
