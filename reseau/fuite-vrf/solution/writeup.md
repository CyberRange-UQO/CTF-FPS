# Writeup — fuite-vrf

**Catégorie :** réseau · **Niveau :** difficile
**Flag :** `FPS{route_target_mal_configure_fuite_entre_vrf}`

## Contexte

Un opérateur héberge plusieurs clients en MPLS/L3VPN, chacun dans une **VRF**
distincte. L'isolation entre clients repose sur les **route-targets** (RT) :
chaque VRF n'importe que les routes portant SON route-target.

Ici, par erreur (copier-coller de config), **les deux VRF utilisent le même
route-target** `65000:100`. Le joueur ne voit pas cette configuration (elle est
sur le PE de l'opérateur, fournie ici pour comprendre) :

```
router bgp 65000 vrf CLIENTA
  rd vpn export 65000:100
  rt vpn both 65000:100          <-- RT 100
router bgp 65000 vrf CLIENTB
  rd vpn export 65000:200
  rt vpn both 65000:100          <-- MÊME RT 100 (la boulette)
```

Conséquence : CLIENT-A importe les routes de CLIENT-B (et réciproquement). Les
réseaux fuient **mutuellement** → connectivité bidirectionnelle entre clients
censés être isolés.

## Résolution

Depuis le poste CLIENT-A (`ssh root@<hôte> -p 1347`, `ClientA2026`), on est en
`192.168.1.0/24` avec pour seule route une route par défaut vers le PE
(`192.168.1.1`) : la table de routage ne montre pas directement les autres clients,
il faut sonder. Le poste n'a que `ping` (busybox), `ip` et `curl`. Les clients étant
numérotés `192.168.1.0/24`, `192.168.2.0/24`…, on teste les passerelles voisines :

```
ip addr; ip route                     # 192.168.1.x/24, default via 192.168.1.1
for n in $(seq 2 10); do ping -c1 -W1 192.168.$n.1 >/dev/null && echo "192.168.$n.1 répond"; done
# 192.168.2.1 répond   <- le PE a une patte dans le réseau de CLIENT-B... et on y est routé
for h in $(seq 2 10); do ping -c1 -W1 192.168.2.$h >/dev/null && echo "192.168.2.$h"; done
# 192.168.2.2
curl http://192.168.2.2/
# ... Jeton interne : FPS{route_target_mal_configure_fuite_entre_vrf}
```

Avec des VRF correctement isolées, `192.168.2.0/24` n'existerait pas dans la VRF
CLIENTA et rien ne répondrait.

```
python3 solve.py <hôte> 1347
# FPS{route_target_mal_configure_fuite_entre_vrf}
```

## Remédiation

- Attribuer un **route-target unique par client** et auditer les RT
  import/export (un RT partagé casse l'étanchéité des VRF).
- Revue de configuration systématique sur les PE ; tests d'isolation
  inter-VRF.

## Infra

PE FRR (2 VRF, RT partagé) + 2 CE, en Docker. `docker compose up -d --build`
puis `./setup-host.sh` (prérequis noyau). Accès joueur SSH port **1347**.
Limites : 0,2–0,4 CPU, 64–256 Mo par conteneur.
