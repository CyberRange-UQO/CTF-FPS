#!/bin/sh
set -e
ROLE="$1"
sed -i 's/^bgpd=no/bgpd=yes/; s/^ospfd=no/ospfd=yes/; s/^ldpd=no/ldpd=yes/' /etc/frr/daemons
sed -i 's|^zebra_options=.*|zebra_options="  -A 127.0.0.1 -s 1000000"|' /etc/frr/daemons
sysctl -w net.mpls.platform_labels=1048575 >/dev/null 2>&1 || true

rename_if() {
  dev=$(ip -o -4 addr show | awk -v p="$1" '$4 ~ "^"p {print $2; exit}')
  [ -n "$dev" ] && [ "$dev" != "$2" ] && ip link set "$dev" down && ip link set "$dev" name "$2" && ip link set "$2" up
}
case "$ROLE" in
  pe1) rename_if 10.1.12. core ;;
  pe2) rename_if 10.1.23. core ;;
  p)   rename_if 10.1.12. pe1; rename_if 10.1.23. pe2 ;;
esac
for i in core pe1 pe2; do
  [ -d /sys/class/net/$i ] && sysctl -w net.mpls.conf.$i.input=1 >/dev/null 2>&1 || true
done
case "$ROLE" in
  pe1|pe2)
    ip link add CLIENTC type vrf table 100; ip link set CLIENTC up
    # l'interface cust face au CE
    rename_if 192.168. cust
    ip link set cust master CLIENTC
    ;;
esac
install -o frr -g frr -m 640 /frr.conf /etc/frr/frr.conf
# LDP ne se charge pas via docker-start -> on l'applique une fois FRR prêt
if [ -f /ldp.conf ]; then
  ( sleep 12; vtysh -f /ldp.conf >/dev/null 2>&1 ) &
fi
exec /usr/lib/frr/docker-start
