# CTF FPS 2026

Challenges et writeups du CTF FPS 2026. Chaque challenge contient l'énoncé et les fichiers fournis (`defi/`) ainsi que la solution (`solution/`).

Les fichiers `*.img` sont stockés avec Git LFS (`git lfs install` avant de cloner).

## Challenges

| Catégorie | Challenge | Auteur | Difficulté | Points (initial) | Résolutions |
|---|---|---|---|---|---|
| boot2root | [cible1 - facile](boot2root/cible1-user/) | Vincent H. | Facile | 50 | 2 |
| boot2root | [cible1- facile](boot2root/cible1-root/) | Vincent H. | Facile | 100 | 0 |
| Crypto | [cle-partagee](crypto/cle-partagee/) | Herastique - Rémi Pantzer | Facile | 100 | 3 |
| Crypto | [jeton-api](crypto/jeton-api/) | Herastique - Rémi Pantzer | Intermédiaire | 300 | 3 |
| Crypto | [rsa-archives](crypto/rsa-archives/) | Herastique - Rémi Pantzer | Intermédiaire | 300 | 2 |
| Crypto | [sauvegarde-chiffree](crypto/sauvegarde-chiffree/) | Herastique - Rémi Pantzer | Facile | 100 | 4 |
| Forensic | [cle-usb-perdue](forensic/cle-usb-perdue/) | Herastique - Rémi Pantzer | Facile | 100 | 4 |
| Forensic | [file-impression](forensic/file-impression/) | Herastique - Rémi Pantzer | Intermédiaire | 300 | 4 |
| Forensic | [journal-apache](forensic/journal-apache/) | Herastique - Rémi Pantzer | Facile | 100 | 2 |
| Forensic | [memoire-vive](forensic/memoire-vive/) | Herastique - Rémi Pantzer | Expert | 500 | 0 |
| Forensic | [N WHAT ?](forensic/N_WHAT/) | Duraink | Facile | 100 | 0 |
| Forensic | [serveur-compromis](forensic/serveur-compromis/) | Herastique - Rémi Pantzer | Difficile | 400 | 2 |
| Misc | [Colloriage](misc/colloriage/) | Askela | Intermédiaire | 150 | 4 |
| Misc | [De la musique pour mes oreilles](misc/de-la-musique-pour-mes-oreilles/) | Askela | Facile | 100 | 0 |
| Misc | [Ebooks](misc/Ebooks/) | Duraink | Facile | 100 | 0 |
| Misc | [Jackpot](misc/jackpot/) | Askela | Facile | 100 | 2 |
| Misc | [Oui Allo?](misc/oui-allo/) | Askela | Intermédiaire | 150 | 1 |
| Misc | [Registre de la Bibliothèque](misc/registre-bibliotheque/) | Askela | Facile | 100 | 3 |
| Réseau | [cloison-vlan](reseau/cloison-vlan/) | Herastique - Rémi Pantzer | Facile | 100 | 2 |
| Réseau | [etiquettes](reseau/etiquettes/) | Herastique - Rémi Pantzer | Intermédiaire | 300 | 2 |
| Réseau | [fuite-vrf](reseau/fuite-vrf/) | Herastique - Rémi Pantzer | Difficile | 400 | 0 |
| Réseau | [route-detournee](reseau/route-detournee/) | Herastique - Rémi Pantzer | Intermédiaire | 300 | 0 |
| Réseau | [tunnel-mpls](reseau/tunnel-mpls/) | Herastique - Rémi Pantzer | Expert | 500 | 0 |
| Stéganographie | [palette](stegano/palette/) | Herastique - Rémi Pantzer | Expert | 500 | 3 |
| Stéganographie | [presentation-trimestrielle](stegano/presentation-trimestrielle/) | Herastique - Rémi Pantzer | Facile | 100 | 3 |
| Stéganographie | [rapport-annuel](stegano/rapport-annuel/) | Herastique - Rémi Pantzer | Intermédiaire | 300 | 4 |
| Web | [badge-visiteur](web/badge-visiteur/) | Herastique - Rémi Pantzer | Facile | 100 | 5 |
| Web | [BLACK VAULT](web/black-vault/) | Samuel Boisneault | Difficile | 400 | 1 |
| Web | [generateur-factures](web/generateur-factures/) | Herastique - Rémi Pantzer | Intermédiaire | 300 | 3 |
| Web | [GHOST RECORD](web/ghost-record/) | Samuel Boisneault | Facile | 100 | 4 |
| Web | [MIRROR GATE](web/mirror-gate/) | Samuel Boisneault | Intermédiaire | 300 | 1 |
| Web | [Phantom Badge](web/phantom-badge/) | Samuel Boisneault | Intermédiaire | 300 | 2 |
| Web | [portail-stagiaire](web/portail-stagiaire/) | Herastique - Rémi Pantzer | Facile | 100 | 4 |
| Web | [ROOT OF TRUST](web/root-of-trust/) | Samuel Boisneault | Difficile | 400 | 1 |

## Arborescence

```text
├── categorie-1/
│   ├── titre-chall-1/
│   │   ├── defi/
│   │   │   ├── challenge.yml
│   │   │   ├── fichier-annexe-1
│   │   │   └── docker-compose
│   │   └── solution/
│   │       ├── writeup.md
│   │       └── solve.py
│   ├── titre-chall-2/
│   │   └── ...
├── categorie-2/
│   └── titre-chall-1/
│       └── ...
└── categorie-3/
    └── ...
```

## Format `challenge.yml`

```yaml
name: exemple-challenge
author: Author
category: crypto
description: |
  Texte montré aux participants. Markdown accepté.
type: dynamic
extra:
  initial: 500 # points de base
  decay: 20
  minimum: 100
  function: logarithmic
flags:
  - FPS{exemple_de_flag}
files:
  - relative/path/to/files
tags:
  - facile
connection_info: "" # laisser vide, sera rempli ultérieurement
requirements:
  - "chall-precedent-1"
  - "chall-precedent-2"
state: hidden
```
