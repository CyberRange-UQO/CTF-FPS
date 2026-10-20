# Writeup — etiquettes

**Catégorie :** réseau · **Niveau :** intermédiaire · **Déverrouille :** tunnel-mpls
**Flag :** `FPS{mpls_l3vpn_depile_les_labels_et_lis_le_vpn}`

## Analyse

Capture sur un lien de cœur MPLS (PE ↔ P). Deux choses y cohabitent :

**Plan de données** — trafic client encapsulé avec une **pile de 2 labels** :
```
MPLS (label 16)        <- label de TRANSPORT (LDP, pour atteindre le PE distant)
 MPLS (label 1000, S)  <- label VPN (identifie la VRF/CLIENT-C)
  IP 192.168.11.2 > 192.168.22.2  UDP/9514   <- télémétrie interne CLIENT-C
```

**Plan de contrôle** — BGP **VPNv4** (`SAFI Labeled VPN Unicast`) qui annonce
les routes du VPN avec leur **RD**, **RT** et **label VPN**.

## Résolution

Dans Wireshark : filtrer `mpls`, dérouler la pile de labels, lire l'UDP interne
→ la télémétrie contient le flag. Ou :

```
python3 solve.py
# télémétrie interne 192.168.11.2 -> 192.168.22.2 (dépilée)
# label(s) VPN observé(s) : [1000]
# FLAG : FPS{mpls_l3vpn_depile_les_labels_et_lis_le_vpn}
```

## À noter pour la suite (tunnel-mpls)

Le plan de contrôle BGP VPNv4 (filtre `bgp` dans Wireshark, message UPDATE avec
l'attribut `MP_REACH_NLRI`) révèle :
- **Route Distinguisher** : `65000:300`
- **Route Target** (extended community) : `65000:300`
- la route VPN `192.168.11.0/24` (site 1 de CLIENT-C) annoncée avec le **label VPN 900**

Le plan de données donne le reste : le trafic de télémétrie vers le **serveur
`192.168.22.2`** porte la pile `[16, 1000]`, donc le **label VPN du site du serveur
(`192.168.22.0/24`) est 1000**.

Ces valeurs permettent de **forger** du trafic étiqueté dans le défi
`tunnel-mpls`.

## Remédiation

- Ne jamais exposer un lien de cœur MPLS à une capture non maîtrisée.
- Le label VPN seul n'est pas un secret d'authentification : voir tunnel-mpls.
