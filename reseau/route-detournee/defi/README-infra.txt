PREREQUIS HOTE (serveur de chall) - une seule fois, communs aux challs reseau
qui font tourner FRR/MPLS dans des conteneurs :

  sysctl -w vm.overcommit_memory=1
  sysctl -w net.bridge.bridge-nf-call-iptables=0

Pourquoi :
- vm.overcommit_memory=1 : zebra (FRR) reserve un gros buffer ; sous overcommit
  heuristique (defaut) le fork() est refuse. (Reglage standard des labs type
  containerlab/GNS3.)
- bridge-nf-call-iptables=0 : sinon les trames inter-conteneurs portant les IP
  "publiques" annoncees (hors subnet docker) tombent sur la politique
  iptables FORWARD DROP de l'hote.

Demarrage :  docker compose up -d --build
Acces joueur : ssh root@<hote> -p 1345   (mot de passe Hijack2026)
