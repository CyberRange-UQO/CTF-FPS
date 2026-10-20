# Writeup — journal-apache

**Catégorie :** forensic · **Niveau :** débutant (relevé)
**Flag :** `FPS{injection_sql_aveugle_boolean_based_reconstruite}`

## Analyse

Le flag n'apparaît **jamais en clair** dans le log : un `grep FPS{` ne donne
rien. L'attaquant (IP `203.0.113.47`) a exfiltré un secret par **injection SQL
booléenne à l'aveugle** :

```
/produits.php?id=1 AND SUBSTRING((SELECT secret FROM config),n,1)>CHAR(x)
```

(URL-encodée dans le log). La requête renvoie toujours un **statut 200**, mais :

- condition **vraie** → page produit complète → **4812 octets**
- condition **fausse** → page vide/erreur → **1203 octets**

L'attaquant fait une **recherche dichotomique** sur chaque position `n` pour
retrouver le caractère.

## Résolution

1. Isoler l'IP qui porte le motif `SUBSTRING(...)>CHAR(...)`.
2. URL-décoder, extraire `(n, x, taille)`.
3. Pour chaque position `n` : le caractère est
   `max{ x | réponse = TRUE } + 1` (car `char > x` est vrai tant que `x < char`).

```
python3 solve.py
# attaquant: 203.0.113.47
# FPS{injection_sql_aveugle_boolean_based_reconstruite}
```

À la main : filtrer l'IP (`grep 203.0.113.47 access.log`), trier par position,
repérer la bascule 4812→1203 pour chaque caractère.

## Remédiation

- Requêtes **paramétrées** (prepared statements) — jamais de concaténation.
- Uniformiser les réponses (même taille/latence) pour casser les oracles
  booléens/temporels ; journaliser et alerter sur les pics de requêtes 200 sur
  un même paramètre.

*(`gen.py` régénère le journal, seed fixe.)*
