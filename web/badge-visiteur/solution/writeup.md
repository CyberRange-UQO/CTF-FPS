# Writeup — badge-visiteur

**Catégorie :** web · **Niveau :** débutant
**Flag :** `FPS{un_cookie_de_role_non_signe_cote_client}`

## Analyse

À la première visite, le serveur pose un cookie `badge` :

```
badge = base64({"name": "Invite", "role": "visiteur"})
```

L'endpoint `/admin` relit ce cookie et fait **confiance au champ `role`** sans
aucune signature ni vérification côté serveur. Le rôle est donc contrôlé par le
client.

## Résolution

1. Décoder le cookie (base64) → JSON.
2. Remplacer `"role": "visiteur"` par `"role": "admin"`, ré-encoder.
3. Rejouer `GET /admin` avec le cookie forgé → flag.

```
python3 solve.py http://localhost:1342
# FPS{un_cookie_de_role_non_signe_cote_client}
```

## Remédiation

- Ne jamais stocker un attribut d'autorisation en clair côté client.
- Signer/chiffrer la session (cookie signé HMAC, type `itsdangerous`/JWT) et
  vérifier la signature à chaque requête, ou garder l'état côté serveur.

## Infra

`docker compose up -d --build` dans `defi/` (port hôte **1342**).
