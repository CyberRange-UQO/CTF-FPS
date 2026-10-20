# Writeup — sauvegarde-chiffree

**Catégorie :** crypto · **Niveau :** débutant
**Flag :** `FPS{sauvegarde_chiffree_avec_une_graine_temporelle}`

## Analyse

`backup.py` chiffre l'archive par XOR avec un keystream tiré du PRNG standard :

```python
graine = int(time.time())
random.seed(graine)
flux = bytes(random.getrandbits(8) for _ in range(len(data)))
```

Deux faiblesses :

1. **XOR à clé = keystream** : si on connaît le keystream, on déchiffre tout.
2. **La graine est l'heure système en secondes.** Elle n'a que ~2^30 valeurs
   possibles, et surtout `backup.log` donne la **minute** exacte du backup.
   Il ne reste que **60 graines** candidates (les 60 secondes de cette minute).

## Résolution

Pour chaque graine candidate, on régénère le keystream et on teste les 2
premiers octets contre le **header gzip** `1f 8b`. Un seul candidat passe ; on
décompresse alors l'archive et on lit le flag dans `etc/app/README.txt`.

```
python3 solve.py
# graine = 1789524037
# FPS{sauvegarde_chiffree_avec_une_graine_temporelle}
```

Le header connu (`1f 8b`) sert d'oracle de validation : pas besoin de deviner,
une seule graine produit un gzip valide.

## Remédiation

- Ne jamais dériver une clé d'un horodatage (entropie quasi nulle).
- Utiliser `secrets`/`os.urandom` pour les clés, et un vrai chiffrement
  authentifié (AES-GCM) plutôt qu'un XOR maison.
