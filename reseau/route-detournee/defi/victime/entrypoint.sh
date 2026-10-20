#!/bin/sh
set -e
sed -i 's/^bgpd=no/bgpd=yes/' /etc/frr/daemons
# Reduit le buffer netlink de zebra : avec le defaut (90MB), fork() est refuse
# sous overcommit heuristique du noyau hote. 1MB suffit largement pour le lab.
sed -i 's|^zebra_options=.*|zebra_options="  -A 127.0.0.1 -s 1000000"|' /etc/frr/daemons
install -o frr -g frr -m 640 /frr.conf /etc/frr/frr.conf
case "$1" in
  victime)
    ip link add srv type dummy; ip addr add 198.51.100.10/24 dev srv; ip link set srv up
    python3 /service.py & ;;
  client)
    ip link add cl type dummy; ip addr add 203.0.113.20/24 dev cl; ip link set cl up
    sh /heartbeat.sh & ;;
  attaquant)
    ip link add own type dummy; ip addr add 192.0.2.1/24 dev own; ip link set own up
    /usr/sbin/sshd ;;
esac
exec /usr/lib/frr/docker-start
