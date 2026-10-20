# PHANTOM BADGE — livraison technique

Documentation interne organisateur. Challenge web n°2 de la campagne
VANTA//SYSTEMS (après GHOST RECORD, avant MIRROR GATE). La solution détaillée et
les payloads restent dans [`../solution/writeup.md`](../solution/writeup.md) ;
ce README ne décrit que l'application, son déploiement et sa configuration.

Flag : conservé côté serveur, voir le writeup. `state: hidden`, `connection_info`
vide, `requirements: ["GHOST RECORD"]`.

## Présentation

Portail d'identité PHANTOM de VANTA. STATIC dispose d'un accès sous-traitant
(`contractor.073`) dont le badge ne donne pas l'habilitation CIPHER. Le portail
présente le badge de session et expose deux générations de terminaux : le canal
moderne **PHANTOM v2** et un terminal **legacy CIPHER v1** maintenu pour
compatibilité. L'objectif joueur est de récupérer l'identifiant de preuve du
dossier d'incident confidentiel CIPHER.

Toutes les identités sont fictives.

## Configurer, construire et lancer

Service HTTP unique Flask/Gunicorn. Depuis la racine du dépôt, provisionner les
deux secrets dans le fichier ignoré `defi/.env` (voir `.env.example`), puis
lancer Compose en désignant explicitement ce fichier :

```bash
cp web/phantom-badge/defi/.env.example web/phantom-badge/defi/.env
# Renseigner SESSION_SECRET et JWT_SECRET :
#   python3 -c 'import secrets; print(secrets.token_hex(32))'
docker compose --env-file web/phantom-badge/defi/.env -p phantom-badge -f web/phantom-badge/defi/docker-compose.yml build
docker compose --env-file web/phantom-badge/defi/.env -p phantom-badge -f web/phantom-badge/defi/docker-compose.yml up -d --wait --wait-timeout 45
```

Ouvrir <http://127.0.0.1:8081/login>. Compte sous-traitant, également fourni dans
`challenge.yml` : **contractor.073 / PHANTOM-073-2147**.

Le projet Compose explicite (`-p phantom-badge`) évite toute collision avec les
autres challenges. Aucun `container_name` global n'est fixé.

Arrêt de ce seul périmètre :

```bash
docker compose --env-file web/phantom-badge/defi/.env -p phantom-badge -f web/phantom-badge/defi/docker-compose.yml down
```

Contrôle de syntaxe sans afficher les secrets interpolés :

```bash
docker compose --env-file web/phantom-badge/defi/.env -p phantom-badge -f web/phantom-badge/defi/docker-compose.yml config --quiet
```

## Services, ports et variables

| Service | Port conteneur | Port hôte par défaut | Réseau |
|---|---|---|---|
| `phantom-badge` | 8000 | 8081 (override `PHANTOM_PORT`) | `default` |

Variables documentées (`.env`, non commitées) :

| Variable | Rôle | Défaut |
|---|---|---|
| `SESSION_SECRET` | secret de signature de la session Flask (requis) | — |
| `JWT_SECRET` | clé HS256 des badges JWT (requis) | — |
| `SESSION_COOKIE_SECURE` | `true` en HTTPS au laboratoire, `false` en HTTP local | `false` |
| `PHANTOM_BIND` | interface d'écoute publiée | `127.0.0.1` |
| `PHANTOM_PORT` | port hôte publié | `8081` |

`SESSION_SECRET` et `JWT_SECRET` sont **deux clés distinctes**, générées
indépendamment, jamais partagées avec GHOST RECORD ni entre instances. Le
démarrage échoue si l'une est absente. Au déploiement HTTPS, définir
`SESSION_COOKIE_SECURE=true`.

## Architecture et confinement

Image Python épinglée, UID/GID 10001, `read_only`, tmpfs `/tmp`, `cap_drop: ALL`,
`no-new-privileges`, limites CPU/mémoire/PID, healthcheck sur `/healthz` et Flask
sans debug. Gunicorn deux workers. Routes applicatives : `/login`, `/logout`,
`/dashboard`, `/identity`, `/cipher`, `/support`, et les API `/api/session/badge`,
`/api/identity/me`, `/api/legacy/cipher/access`. Sans session valide, les pages
et API protégées redirigent ou renvoient une erreur ; seuls `/login`, les assets
et `/healthz` sont publics.

Le secret de session et la clé de badge sont injectés uniquement par
l'environnement. Aucun secret n'est stocké dans le cookie. Le flag n'apparaît que
dans la réponse autorisée du dossier CIPHER.

## À confirmer par le laboratoire

`requirements: ["GHOST RECORD"]` (nom exact du challenge précédent), le calcul
du barème dynamique par le wrapper CTFd, le reverse proxy HTTPS avec `Secure`.
`connection_info` reste vide, le challenge `hidden` ; difficulté et durée se
mesurent par playtest humain.

## Révision — Calibration des indices et découverte joueur

Révision éditoriale du 12 octobre 2026. KB-PHANTOM-017 décrit les services
PHANTOM v2, le parc CIPHER v1 et le canal historique maintenu, sans détailler
qui vérifie cryptographiquement les badges. KB-PHANTOM-011 décrit les comptes
rendus d'habilitation et les informations à transmettre à l'assistance.
Le terminal conserve son identité CIPHER, la politique CIPHER / TECH-2 et les
résultats réels. La comparaison des comportements reste possible depuis les
fonctions normales du portail.

Identifiants initiaux, JWT HS256, claims, APIs, session, contrôle moderne,
absence intentionnelle de vérification de signature sur legacy et flag restent
inchangés. Ce README est une documentation d'exploitation interne.
