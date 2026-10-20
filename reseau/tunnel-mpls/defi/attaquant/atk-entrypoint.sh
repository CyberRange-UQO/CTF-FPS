#!/bin/sh
dev=$(ip -o -4 addr show | awk '$4 ~ /^10\.1\.23\./ {print $2; exit}')
[ -n "$dev" ] && [ "$dev" != "data" ] && ip link set "$dev" down && ip link set "$dev" name data && ip link set data up
exec /usr/sbin/sshd -D -e
