#!/bin/sh
ip route replace default via 192.168.1.1 2>/dev/null
cat > /root/LISEZMOI.txt <<'TXT'
Vous etes sur un poste du reseau de CLIENT-A (192.168.1.0/24), raccorde a
l'operateur via le PE (192.168.1.1). Vous ne devriez voir QUE le reseau de
CLIENT-A. Explorez : l'operateur a peut-etre fait une erreur de configuration
de VRF (route-targets)...
TXT
exec /usr/sbin/sshd -D -e
