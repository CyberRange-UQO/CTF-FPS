# BLACK VAULT — livraison technique

Documentation interne organisateur. Challenge web n°4 de la campagne
VANTA//SYSTEMS (après MIRROR GATE, avant ROOT OF TRUST). La solution détaillée,
le triptyque de refus/succès et les payloads restent dans
[`../solution/writeup.md`](../solution/writeup.md) ; ce README décrit
l'application, son déploiement et sa configuration.

Flag : conservé côté serveur (attestation de contact). `state: hidden`,
`connection_info` vide, `requirements: ["MIRROR GATE"]`.

## Présentation

Service de conservation classifié BLACK VAULT de VANTA. STATIC dispose d'un poste
archiviste (`archivist.bv-021`). Le joueur consulte le dossier de MIRA-07,
examine ses pièces publiques et scellées, puis obtient une **attestation de
contact** auprès du pont de diagnostic MIRA. Le matériel d'audit récupéré ici
(dont la clé ROOT-AUDIT) sert ensuite à ROOT OF TRUST.

Toutes les identités sont fictives.

## Configurer, construire et lancer

Service HTTP unique Flask/Gunicorn. Depuis la racine du dépôt, provisionner une
seule fois le fichier ignoré `defi/.env`. L'outil fourni génère la clé de
campagne sans jamais l'afficher :

```bash
python3 web/black-vault/defi/tools/init_config.py
docker compose --env-file web/black-vault/defi/.env -p black-vault -f web/black-vault/defi/docker-compose.yml build
docker compose --env-file web/black-vault/defi/.env -p black-vault -f web/black-vault/defi/docker-compose.yml up -d --wait --wait-timeout 45
python3 web/black-vault/defi/tools/check_runtime.py --base-url http://127.0.0.1:8083
```

`init_config.py` refuse d'écraser une configuration existante : **ne pas
régénérer la clé** une fois provisionnée. Ouvrir <http://127.0.0.1:8083/login>.
Compte archiviste, également fourni dans `challenge.yml` :
**archivist.bv-021 / BV-021-2147** (rôle ARCHIVE_OPERATOR, habilitation ARCHIVE-1).

Arrêt de ce seul périmètre :

```bash
docker compose --env-file web/black-vault/defi/.env -p black-vault -f web/black-vault/defi/docker-compose.yml down
```

Contrôle de syntaxe sans afficher les secrets interpolés :

```bash
docker compose --env-file web/black-vault/defi/.env -p black-vault -f web/black-vault/defi/docker-compose.yml config --quiet
```

## Services, ports et variables

| Service | Port conteneur | Port hôte par défaut | Réseau |
|---|---|---|---|
| `black-vault` | 8000 | 8083 (override `BLACK_VAULT_PORT`) | `vault-ingress` |

Variables documentées (`.env`, non commitées) :

| Variable | Rôle | Défaut |
|---|---|---|
| `ROOT_AUDIT_KEY_B64U` | clé de campagne 32 octets, Base64URL canonique sans padding (requis) | — |
| `SESSION_COOKIE_SECURE` | `true` en HTTPS, `false` en HTTP local | `false` |
| `VAULT_ROOT` | racine runtime de l'archive (tmpfs en conteneur) | `/run/black-vault-data` |
| `BLACK_VAULT_BIND` | interface d'écoute publiée | `127.0.0.1` |
| `BLACK_VAULT_PORT` | port hôte publié | `8083` |

### Provisionnement partagé avec ROOT OF TRUST

`ROOT_AUDIT_KEY_B64U` est la **clé de campagne partagée** : la valeur provisionnée
ici doit être reprise **à l'identique** dans le `.env` de ROOT OF TRUST
(`web/root-of-trust/defi/.env`). BLACK VAULT distribue cette clé dans l'histoire
via le compartiment scellé ; ROOT l'attend en variable d'environnement. Ne pas
régénérer la clé, ne pas la publier dans les rapports, ne pas présumer que
l'orchestrateur partage automatiquement les secrets — vérifier ce point avec le
laboratoire. ROOT OF TRUST utilise en plus une graine Ed25519 **distincte**
(`ATTESTATION_ED25519_SEED_B64U`), propre à ROOT.

## Architecture et confinement

Image Python épinglée, UID/GID 10001, `read_only`, deux tmpfs (`/tmp` et
`/run/black-vault-data`), `cap_drop: ALL`, `no-new-privileges`, limites
CPU/mémoire/PID, healthcheck et Flask sans debug. Le réseau `vault-ingress` est un
bridge avec `enable_icc=false` et `enable_ip_masquerade=false` : les ports publiés
fonctionnent, aucun egress runtime n'est nécessaire.

Routes applicatives : `/login`, `/logout`, `/dashboard`, `/archives`, `/reader`,
`/diagnostics`, `/documentation` ; API `/api/vault/<archive_ref>/preview`,
`/api/bridge/open`, `/api/bridge/advance`, `/api/bridge/<sid>`. Session Flask
protégée par CSRF ; seuls `/login`, les assets et `/healthz` sont publics. Le flag
n'apparaît que dans l'attestation renvoyée par le pont après la conversation
complète.

## Journal de restitution documentaire — livraison P1

Le lecteur `/reader` affiche, sous la consultation courante, un extrait historique
statique de deux lectures du document public `inventory.txt`. Les références HTTP
`inventory.txt` et `inventory%252Etxt` sont rapprochées du document restitué
`inventory.txt`, avec identifiant et statut `200 / RESTITUÉ`. La légende situe les
références dans l'URL de consultation. Les identifiants sont éditoriaux ; ce
tableau ne collecte pas l'activité du joueur et n'ajoute aucun verrou.

La référence affichée est la valeur de `file` dans la query string brute, **avant
Flask**. Pour la seconde ligne, Flask fournit `inventory%2Etxt`, le contrôleur
conserve cette valeur, puis le renderer transmet `inventory.txt` à la lecture
réelle. Avec `URLSearchParams`, la saisie équivalente dans le **champ du lecteur**
est `inventory%2Etxt` (le `%` y est ré-encodé) ; copier la forme brute
`inventory%252Etxt` dans ce champ ajouterait une couche d'encodage. Cette
justification reste interne : le tableau joueur n'explique ni les étapes, ni leur
ordre, ni leur usage offensif. KB-VAULT-021 reste intacte et le journal est
facultatif.

## À confirmer par le laboratoire

`requirements: ["MIRROR GATE"]` (nom exact du challenge précédent), le calcul du
barème dynamique par le wrapper CTFd, le partage de `ROOT_AUDIT_KEY_B64U` entre
BLACK VAULT et ROOT OF TRUST, le reverse proxy HTTPS avec `Secure`.
`connection_info` reste vide, le challenge `hidden` ; difficulté et durée se
mesurent par playtest humain.

## Révision — Calibration des indices et découverte joueur

Révision éditoriale du 12 octobre 2026. KB-VAULT-021 / migration-note révision 2.3
décrit les compartiments, les index et les responsabilités de Document Services.
Elle conserve l'anomalie de résolution et la collecte de références, mais retire
l'ordre des interprétations et la description des caractères échappés. public/,
sealed/, manifest.json, paramètre `file`, inventaire et références de lecture
restent découvrables. Path Traversal, double encodage, triptyque 403/403/200,
confinement, manifeste scellé, NEUROGRID, capacité MIRA, conversation, attestation,
clé ROOT-AUDIT et flag restent inchangés. Ce README est une documentation
d'exploitation interne.
