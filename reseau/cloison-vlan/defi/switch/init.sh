#!/bin/sh
# Switch d'etage SW-ETAGE2 (emule par un bridge Linux 802.1Q).
# Les liens physiques sont les reseaux docker ; on retrouve chaque port par son IP.
set -e
port_of() { ip -o -4 addr show | awk -v ip="$1" '$4 ~ "^"ip"/" {print $2}'; }

P_POSTE=$(port_of 10.10.10.2)   # Gi0/7  -> poste de depannage
P_RH=$(port_of 10.10.99.2)      # Gi0/12 -> SRV-RH

ip link add br0 type bridge vlan_filtering 1
for p in $P_POSTE $P_RH; do
  ip addr flush dev "$p"
  ip link set "$p" master br0
  bridge vlan del dev "$p" vid 1
done

# Gi0/7 : DEVRAIT etre "switchport access vlan 10"... laisse en trunk (10 natif + 99).
bridge vlan add dev "$P_POSTE" vid 10 pvid untagged
bridge vlan add dev "$P_POSTE" vid 99

# Gi0/12 : access vlan 99 (management / RH)
bridge vlan add dev "$P_RH" vid 99 pvid untagged

ip link set br0 up
echo "SW-ETAGE2 pret"
exec sleep infinity
