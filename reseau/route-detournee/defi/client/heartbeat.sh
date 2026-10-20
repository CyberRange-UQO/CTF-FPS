#!/bin/sh
# Le client envoie periodiquement un jeton signe au service bancaire.
TOKEN="FPS{bgp_hijack_more_specific_intercepte_le_trafic}"
while true; do
  curl -s -m 4 --interface 203.0.113.20 -X POST --data "client=AS65020&token=$TOKEN" \
       http://198.51.100.10/api/heartbeat >/dev/null 2>&1
  sleep 5
done
