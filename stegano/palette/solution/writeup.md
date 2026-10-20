# Writeup — palette

**Catégorie :** stégano · **Niveau :** expert
**Flag :** `FPS{ordre_de_palette_permutation_code_de_lehmer}`

## Idée

Une image en couleurs indexées associe chaque pixel à un **index** dans une
**palette**. On peut réordonner la palette **sans changer l'image affichée** :
il suffit de remapper les index des pixels en conséquence. L'ordre des couleurs
devient alors un **canal caché**.

Avec une palette de N couleurs, il y a N! ordres possibles → ~`log2(256!) ≈
1683 bits` de capacité ici. Une analyse de pixels (LSB, `zsteg`, bruit…) ne
donne **rien** : les pixels sont « normaux », seule la palette est signifiante.

## Décodage

1. Constater que la palette **n'est pas triée** canoniquement (indice dans le
   chunk `Comment` du PNG : *clé = luminance Rec.601*).
2. Calculer l'**ordre canonique** = palette triée par luminance
   `0.299R + 0.587G + 0.114B`.
3. La position de chaque couleur stockée dans cet ordre trié donne la
   **permutation** `perm` (slot → rang canonique).
4. Convertir la permutation en entier via le **code de Lehmer** (système de
   numération factoriel) :
   `m = Σ dᵢ · (N−1−i)!` où `dᵢ` est le rang de `perm[i]` parmi les restants.
5. `m` → octets → on retire le marqueur `0x01` de tête → flag.

```
python3 solve.py
# FPS{ordre_de_palette_permutation_code_de_lehmer}
```

## Notes

- `common.py` contient les primitives (`lum_key`, Lehmer) partagées par `gen.py`
  et `solve.py`.
- L'ordre canonique utilise un tie-break `(lum, r, g, b)` pour garantir un ordre
  total sans ambiguïté (aucune collision de luminance possible entre couleurs
  distinctes).
- `gen.py` régénère l'image à l'identique.
