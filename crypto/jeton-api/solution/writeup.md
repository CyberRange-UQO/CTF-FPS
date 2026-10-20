# Writeup — jeton-api

**Catégorie :** crypto · **Niveau :** intermédiaire
**Flag :** `FPS{aes_ctr_nonce_fixe_bitflip_vers_admin}`

## Analyse

Le jeton est `base64( AES-CTR(key, nonce, JSON) )` avec
`JSON = {"user": "<nom>", "role": "guest"}`.

Deux problèmes se combinent :

1. **Nonce fixe** (`\x00`×8) : le keystream est identique à chaque requête.
2. **CTR est malléable** : `chiffré = clair XOR keystream`. Flipper un bit du
   chiffré flippe le bit correspondant du clair, **sans connaître la clé**.

Comme on choisit le nom d'utilisateur, on connaît le clair **exactement**, donc
l'offset de la valeur `"guest"`.

## Résolution

`"guest"` et `"admin"` font tous deux 5 caractères → on remplace sur place :

```
ct'[i+k] = ct[i+k] XOR ord("guest"[k]) XOR ord("admin"[k])
```

Le serveur déchiffre alors `{"user": "invite", "role": "admin"}` et livre le flag.

```
python3 solve.py http://localhost:1340
# FPS{aes_ctr_nonce_fixe_bitflip_vers_admin}
```

## Remédiation

- Nonce unique par message (aléatoire ou compteur persistant).
- Surtout : **chiffrement authentifié** (AES-GCM, ChaCha20-Poly1305). Le tag
  d'intégrité rend le bit-flipping détectable et rejeté.
- Pour des jetons, préférer un format signé (JWT HMAC/EdDSA) plutôt qu'un
  chiffrement maison.

## Infra

`docker compose up -d --build` dans `defi/` (port hôte **1340** → 5000).
