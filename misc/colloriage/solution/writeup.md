# Writeup : Colloriage

## Énoncé

« Après avoir colorié, il faut toujours s'assurer de remettre les crayons en ordre. Suite à ça,
il faut toujours se rappeler que la clé pour bien colorier se trouve dans la qualité du crayon
utilisé. » Clé de Vigenère : `CRAYON`. Format : `FLAG_X` en majuscules.

On reçoit `Coloriage.pdf` : trois pages (« Coloriage A », « B », « C »), chacune contenant une
grille de mots mêlés 12×12 et une liste de 27 mots à trouver.

## Résolution

### 1. Résoudre les mots mêlés

On barre tous les mots de chaque grille (8 directions). Il reste 4 lettres par page :

| Page | Lettres restantes |
|---|---|
| A | `L C W C` |
| B | `V G M B` |
| C | `M B I F` |

### 2. Remettre les crayons en ordre

On prend les lettres une à une dans chaque boîte, à tour de rôle (A, B, C, A, B, C…) :

```text
L V M  C G B  W M I  C B F  ->  LVMCGBWMICBF
```

### 3. Vigenère

Déchiffrement de `LVMCGBWMICBF` avec la clé `CRAYON` → `JEMESOUVIENS`.

Le script `solve.py` automatise tout (lecture du PDF avec `pypdf`, résolution des grilles,
déchiffrement) :

```bash
pip install pypdf
python3 solve.py ../defi/Coloriage.pdf
```

## Flag

`FLAG_JEMESOUVIENS`
