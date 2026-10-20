# Writeup — rsa-archives

**Catégorie :** crypto · **Niveau :** intermédiaire
**Flag :** `FPS{deux_modules_rsa_un_facteur_commun_pgcd}`

## Analyse

La sécurité de RSA repose sur la difficulté de factoriser `n = p·q`. Mais si
deux modules partagent un facteur premier (PRNG mal initialisé, entropie
insuffisante au premier démarrage), alors :

```
gcd(n_a, n_b) = p   (le facteur commun)
```

Et un PGCD se calcule en quelques microsecondes, même sur des entiers de 2048
bits. On casse alors **les deux** clés d'un coup.

## Résolution

1. Charger les 6 clés publiques.
2. Calculer le PGCD de chaque paire de modules → une paire renvoie `p ≠ 1`
   (`archive-02` et `archive-05`).
3. Pour chaque clé cassée : `q = n/p`, `d = e⁻¹ mod (p-1)(q-1)` → clé privée.
4. Déchiffrer les messages (OAEP) avec les clés reconstruites.

```
python3 solve.py
# facteur commun entre archive-02.pem et archive-05.pem
# message-02.bin -> FPS{deux_modules_rsa_un_facteur_commun_pgcd}
```

Avec beaucoup de clés, on utiliserait l'algorithme *batch GCD* (produit des
modules puis pgcd) au lieu du O(n²) ; ici 6 clés, la boucle naïve suffit.

## Remédiation

- Garantir une source d'entropie correcte **avant** de générer des clés
  (surtout sur VM/conteneurs fraîchement démarrés).
- Auditer régulièrement les parcs de clés (collisions de facteurs).
