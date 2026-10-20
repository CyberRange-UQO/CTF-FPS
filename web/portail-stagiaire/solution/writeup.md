# Writeup — portail-stagiaire

**Catégorie :** web · **Niveau :** débutant
**Flag :** `FPS{un_dossier_backup_oublie_en_prod}`

## Résolution

1. `GET /robots.txt` révèle un `Disallow: /backup/` (un commentaire HTML sur la
   page d'accueil le confirme : *« retirer l'ancien dossier /backup/ »*).
2. `GET /backup/` : le **listing de répertoire** est ouvert → on voit
   `config.php.bak` et `notes.txt`.
3. `GET /backup/config.php.bak` : la sauvegarde de config contient les
   identifiants de base et un `MAINT_TOKEN` = le flag.

```
python3 solve.py http://localhost:1341
# FPS{un_dossier_backup_oublie_en_prod}
```

## Remédiation

- Ne jamais laisser de `.bak`/dossier de sauvegarde dans la racine web.
- Désactiver le listing de répertoire.
- `robots.txt` n'est pas un contrôle d'accès : il *signale* les chemins à cacher.

## Infra

`docker compose up -d --build` dans `defi/` (port hôte **1341**).
