# Writeup : Registre de la Bibliothèque

## Énoncé

On reçoit `Registre_biblio.xlsx`, un inventaire de 50 ouvrages réparti sur deux feuilles
(`Catalogue des collections` et `Journal des contrôles`). Format du flag : `FLAG_X` en majuscules.

## Résolution

Le `Journal des contrôles` donne les indices :

- « Un contrôle de cohérence a été ajouté en dehors des notices. »
- « Le contrôle assemble plusieurs annotations sans les modifier. »

Il y a donc une cellule en dehors du tableau (lignes 7 à 56) qui concatène plusieurs titres.
En parcourant la feuille (Ctrl+Fin dans Excel/LibreOffice, ou en lisant les formules avec
`openpyxl`), on trouve en `N68` une cellule écrite en blanc sur blanc :

```text
=UPPER(B17&"_"&B23&"_"&B24&"_"&B49)
```

Les cellules référencées sont les titres :

| Cellule | Titre |
|---|---|
| B17 | Dune |
| B23 | Frankenstein |
| B24 | Dracula |
| B49 | Fondation |

Script rapide :

```python
import openpyxl
ws = openpyxl.load_workbook("Registre_biblio.xlsx")["Catalogue des collections"]
print(ws["N68"].value)  # =UPPER(B17&"_"&B23&"_"&B24&"_"&B49)
print("FLAG_" + "_".join(ws[c].value.upper() for c in ("B17", "B23", "B24", "B49")))
```

## Flag

`FLAG_DUNE_FRANKENSTEIN_DRACULA_FONDATION`
