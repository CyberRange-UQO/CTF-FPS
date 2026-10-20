# Writeup — cloison-vlan

**Catégorie :** réseau · **Niveau :** facile
**Flag :** `FPS{un_port_laisse_en_trunk_ouvre_tous_les_vlans}`

## Analyse

`/root/notes/sw-etage2-running-config.txt` montre que le port du poste
(`Gi0/7`) est resté en **trunk** après une intervention :

```
interface GigabitEthernet0/7
 switchport trunk native vlan 10
 switchport trunk allowed vlan 10,99
 switchport mode trunk
```

Le trafic non tagué du poste tombe dans le VLAN natif 10, mais le switch
**accepte aussi les trames taguées VLAN 99** sur ce port. SRV-RH est sur
`Gi0/12`, en access dans le VLAN 99 (`10.10.99.10`).

## Résolution

Créer une sous-interface 802.1Q VLAN 99 sur le poste et prendre une IP libre
du réseau management :

```
ip link add link eth0 name vlan99 type vlan id 99
ip addr add 10.10.99.50/24 dev vlan99
ip link set vlan99 up
curl http://10.10.99.10/
```

(Le nom d'interface varie : prendre celle en `10.10.10.0/24`.)

```
python3 solve.py <hote> 1344
# FPS{un_port_laisse_en_trunk_ouvre_tous_les_vlans}
```

## Remédiation

- Ports utilisateurs en `switchport mode access` et `switchport nonegotiate`.
- Restreindre `switchport trunk allowed vlan` aux seuls VLAN nécessaires.
- VLAN natif inutilisé sur les trunks, et VLAN de management jamais propagé
  vers les étages.

## Infra

`docker compose up -d --build` dans `defi/` : SSH sur le port hôte **1344**.
Le switch est un bridge Linux 802.1Q (`vlan_filtering`) ; chaque réseau
docker `internal` joue le rôle d'un câble. Limites : 0,25 à 0,5 CPU et 32 à
64 Mo par conteneur.
