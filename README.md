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
