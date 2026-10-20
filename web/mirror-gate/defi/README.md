# MIRROR GATE V3 / LES TRACES FANTÔMES — livraison technique

Documentation interne organisateur.

## Configurer, construire et lancer

Depuis la racine du dépôt, initialiser un secret unique dans le fichier ignoré
`defi/.env`, puis utiliser explicitement ce fichier avec Compose :

```bash
python3 web/mirror-gate/defi/tools/init_config.py
docker compose --env-file web/mirror-gate/defi/.env -p mirror-gate -f web/mirror-gate/defi/docker-compose.yml build
docker compose --env-file web/mirror-gate/defi/.env -p mirror-gate -f web/mirror-gate/defi/docker-compose.yml up -d --wait --wait-timeout 45
```

Le script conserve le secret et les paramètres existants. Si le secret manque,
il génère 32 octets aléatoires, sans les afficher, dans `.env` en permissions 0600.
Le démarrage échoue si `SESSION_SECRET` est absent ou trop court. Ne pas commiter
`.env` ni partager un secret entre instances.

Port par défaut : <http://127.0.0.1:8082/>. **Sur ce poste Windows/WSL, l'instance
locale conserve le port 8092** : Burp Suite écoute déjà sur 8082 sous Windows.
Pour configurer et relancer cette instance :

```bash
python3 web/mirror-gate/defi/tools/init_config.py --port 8092
docker compose --env-file web/mirror-gate/defi/.env -p mirror-gate -f web/mirror-gate/defi/docker-compose.yml up -d --wait
python3 web/mirror-gate/defi/tools/check_runtime.py --base-url http://127.0.0.1:8092
```

Ouvrir <http://127.0.0.1:8092/login>. Compte opérateur, également fourni dans
`challenge.yml` : **operator.mg-041 / MG-041-2147**.
La configuration locale ne change pas le défaut 8082 du packaging.

Pour arrêter seulement ce périmètre :

```bash
docker compose --env-file web/mirror-gate/defi/.env -p mirror-gate -f web/mirror-gate/defi/docker-compose.yml down
```

Le projet explicite évite les collisions avec les projets `defi` des autres
challenges. Aucun nom de conteneur global n'est fixé. Le build peut télécharger
l'image Python et les distributions PyPI ; préparer les images avant un
déploiement hors ligne. Le runtime et le gameplay ne dépendent pas d'Internet.

`MIRROR_BIND`, `MIRROR_PORT` et `MIRROR_LAB_PREFIX` adaptent l'entrée et un /24 privé
RFC1918 libre. Le préfixe configure ensemble IPAM, destinations épinglées et
adresse source interne. Ne pas rattacher ce challenge à un réseau partagé.
Au labo, une entrée publique attribuée peut utiliser `MIRROR_BIND=0.0.0.0` ; le
défaut reste local. Le wrapper CTFd doit préserver cette topologie et les ports.

Au déploiement **HTTPS**, définir `SESSION_COOKIE_SECURE=true`. Le mode local
HTTP conserve false. L'application ne déduit pas cette option d'un en-tête
Forwarded envoyé par le client. HSTS est ajouté dans le mode Secure.
Pour contrôler la syntaxe sans afficher le secret interpolé :

```bash
docker compose --env-file web/mirror-gate/defi/.env -p mirror-gate -f web/mirror-gate/defi/docker-compose.yml config --quiet
```

## Authentification V2 conservée

Sans session, `/` et les pages applicatives redirigent vers `/login`.
Le formulaire HTML fonctionne sans JavaScript, avec identifiant prérempli et
mot de passe à saisir. Le serveur vérifie un hash PBKDF2-SHA256 salé de
1 000 000 itérations. Une erreur produit un message commun aux deux champs.

La fonction et l'habilitation viennent du serveur : Infrastructure Monitoring
Operator, **OPS-1**. Le compte peut consulter les sources standard ; il n'a pas
d'habilitation métier au relais NG-R. La session Flask signée utilise exclusivement
le secret d'environnement. Le cookie `mirror_session` est HttpOnly, SameSite=Lax,
Secure en HTTPS ; expiration absolue de 30 minutes sans renouvellement à chaque
lecture. L'identité et l'horodatage sont vérifiés à chaque accès. Les réglages de
cookie et de CSRF suivent les principes de
[Flask](https://flask.palletsprojects.com/en/stable/web-security/).

Connexion réussie : ancienne session vidée, nouvelle identité et nouveau jeton
CSRF, puis 303 vers `/`. Déconnexion : POST avec CSRF, suppression de la session
navigateur et 303 vers `/login`. Login/logout transmettent un champ caché ;
preview transmet `X-CSRF-Token` et le cookie seulement au portail. Aucun mot de
passe, secret de signature ou flag ne figure dans le cookie.

Seuls login, assets sans indices et `/healthz` sont publics. Les pages, journal,
documentation et API sont protégés par défaut. L'API retourne 401
`SESSION_REQUIRED` sans session valide et 403 `CSRF_INVALID` sans jeton valable.
Le frontend propose une reconnexion lorsqu'une session est perdue.

## Politique SOURCE-GUARD et confinement indépendant

Après session, CSRF et syntaxe, `app/source_guard.py` accepte intentionnellement une
autorité brute commençant par l'identifiant de source approuvée `mirror-catalog`.
Il ne décompose pas le userinfo et confond l'autorité déclarée avec la destination
effective. Une demande directe NG-R est refusée avec 403
`DESTINATION_NOT_APPROVED`, avant toute résolution DNS ou connexion.

Le transport dans `app/transport.py` est une frontière séparée : il utilise le
**vrai hostname/port** extrait par le parsing standard, puis le pinning DNS/IP et
la liaison à l'interface interne. Cette extraction s'appuie sur les composants
de [urllib.parse](https://docs.python.org/3.12/library/urllib.parse.html).
Un passage du validateur métier ne donne aucun accès réseau hors du laboratoire.

La note **KB-MIRROR-023 — SOURCE-GUARD 1.2 / Autorisation des sources distantes**
présente les obligations d'une politique de sécurité récemment déployée.
Elle décrit la source approuvée, les responsabilités de consultation et les
comptes rendus d'incident, sans expliquer la divergence d'interprétation de l'URL.
Le sommaire et le retour de refus y conduisent naturellement.
Les indices existants du journal et du port 9090 sont conservés.
L'interface, ses scripts et l'énoncé ne donnent aucun payload d'exploitation.

`requested_url` conserve l'éventuel userinfo afin que changer de chemin reste
possible depuis le formulaire. Les boutons de chemins préservent cette
représentation et repassent toujours par l'API du portail. Aucun userinfo n'est
transformé en Basic Auth ou envoyé dans le Host HTTP ; le navigateur ne contacte
jamais directement un service interne.

## Corrélation V3 : journal → trace → allocation

Le journal enrichit **SYNC-NGR-2147**, le 16/10/2147 à 09:12, avec
**Correlation ID : TRC-2147-0912**. Relais ng-r-relay, périmètre NG-R,
classification RESTRICTED, état METADATA ONLY restent identiques. La note précise
que les détails de provenance demeurent sur le relais source. Il s'agit d'une
référence technique ordinaire, sans lien de résolution automatique ni handle public.

L'API NG-R passe à la version 1.5 et propose la consultation par corrélation :

| Endpoint NG-R | Contrat V3 |
|---|---|
| `GET /` | Index des trois collections status, traces et allocations ; aucun handle concret. |
| `GET /v1/status` | Supervision, trois allocations et une trace, sans identité ou preuve. |
| `GET /v1/traces` | Découverte du registre, `lookup: /v1/traces/{trace_id}` ; aucune liste des correspondances. |
| `GET /v1/traces/{trace_id}` | Trace précise : job, date, opération, états et référence d'allocation. |
| `GET /v1/allocations` | Registre agrégé, `lookup: /v1/allocations/{handle}`, enumeration DISABLED ; aucune liste de handles. |
| `GET /v1/allocations/{handle}` | Fiche correspondant exactement au handle du registre. |

La trace **TRC-2147-0912** donne l'opération IDENTITY_SYNC, l'état source ERASED,
l'état allocation ACTIVE, **allocation_handle : ALLOC-7C29-D8F4-912A** et
`allocation_href: /v1/allocations/ALLOC-7C29-D8F4-912A`. Le handle est stable et
n'est pas dérivé de 1057. Cette correspondance reste uniquement dans le backend
NG-R ; le joueur doit lire la trace après avoir atteint le relais.

La fiche finale conserve MIRA-07 / EID-1057, ERASED, ACTIVE, NOT SCHEDULED,
SIL-4/2147-07, BV-2147-1057, la note administrative et le flag existant. La preuve
reste injectée par MIRROR_FLAG et n'apparaît dans aucune autre réponse.
Les deux allocations de contexte concernent DOCUMENT_CACHE et CONNECTOR_STATE,
sans identité humaine ou preuve, et leurs handles ne sont pas listés.

Les anciennes clés NG-R-1057/1044/1088 ne correspondent plus à un handle et
n'ont aucun alias. **L'ancien `/v1/allocations/NG-R-1057` n'a plus de résolution
dans le registre.** Le numéro administratif NG-R-1057 est conservé uniquement
comme donnée de la fiche finale. Les identifiants inconnus produisent les 404
TRACE_NOT_FOUND ou ALLOCATION_NOT_FOUND ; leur audit en boîte noire reste à faire.

Les chemins génériques restent lisibles dans le JSON ; le joueur substitue son
identifiant manuellement. Les boutons existants consultent les chemins concrets
en repassant par la prévisualisation, avec conservation du userinfo. Aucun
auto-remplissage de trace ou d'allocation et aucune modification du JavaScript.

## Architecture Docker conservée

Trois services HTTP Flask/Gunicorn réels. Seules les données/réponses du relais
évoluent ; catalogue, authentification, client HTTP et réseau restent inchangés :

| Service | Port conteneur | Réseaux | Port hôte |
|---|---|---|---|
| `mirror-gate` | 8000 | `mirror-ingress`, `mirror-lab` | 8082 par défaut, 8092 ici |
| `mirror-catalog` | 9080 | `mirror-lab` | aucun |
| `ng-r-relay` | 9090 | `mirror-lab` | aucun |

`mirror-lab` est un bridge dédié `internal: true`, avec suffixes IP `.10` portail,
`.20` catalogue et `.30` NG-R. `mirror-ingress` contient uniquement le portail,
avec masquerading IP et communications inter-conteneurs désactivés. Sur Docker
20.10.24 ici, le premier essai de portail uniquement interne ne publiait pas de
port accessible : les deux réseaux sont conservés car cette entrée a été vérifiée.
Voir [les réseaux Compose](https://docs.docker.com/compose/how-tos/networking/) et
[les options bridge](https://docs.docker.com/engine/network/drivers/bridge/).

Le transport autorise exclusivement `mirror-catalog:9080` et `ng-r-relay:9090` :
nom/port effectifs exacts, DNS égal à l'adresse IPAM configurée, connexion numérique
sans seconde résolution, socket liée à l'adresse interne `.10`. Hôtes, IP saisies,
alias, ports arbitraires et autres protocoles sont refusés. HTTP GET uniquement,
aucune redirection suivie, aucun proxy d'environnement et aucun en-tête de session,
cookie, CSRF ou Authorization transmis aux sources.

Bornes conservées : résolution 1,5 s avec tâches bornées, connexion 2 s,
lecture 3 s, transfert complet 5 s, corps 65 536 octets maximum. Pas de
décompression automatique ; une interruption ne produit pas un succès trompeur.
Le DOM utilise `textContent`, avec CSP restrictive et contenus distants inertes.

Images distinctes et image Python épinglée par digest ; neuf dépendances figées
avec hashes, UID/GID 10001, read_only, tmpfs, cap_drop ALL, no-new-privileges,
limites CPU/mémoire/PID, healthchecks et Flask sans debug. Le secret de session
est injecté uniquement au portail, le flag uniquement au relais.

Le réseau d'entrée n'est pas un pare-feu universel pour un processus compromis :
le client SSRF est strictement lié au périmètre interne. L'administrateur de
l'hôte Docker n'est pas isolé par l'absence de ports publiés. Les joueurs doivent
accéder seulement au portail, sans shell ni accès au démon Docker. Le labo doit
confirmer routes et ACL sur sa version Docker ; aucun pare-feu global n'a été modifié.

## Contrat API

`POST /api/preview` exige cookie opérateur, JSON et `X-CSRF-Token` de la page.
Entrée ordinaire : `{"url": "http://mirror-catalog:9080/public/bulletin"}`.
Une réponse amont, même 404 ou 3xx, produit **200 du portail** et `ok: true`,
`requested_url`, `upstream_status`, `content_type`, `body`, `truncated`,
`duration_ms`, `classification` issue du vrai `X-Vanta-Classification` amont.
Une troncature est signalée. Les réponses ne sont pas conservées dans le journal.

| Statut portail | Erreur | Signification |
|---|---|---|
| 400 | `INVALID_INPUT`, `INVALID_URL`, `UNSUPPORTED_SCHEME` | Saisie/protocole |
| 401 | `SESSION_REQUIRED` | Session absente/expirée |
| 403 | `CSRF_INVALID` | Opération non liée à la session |
| 403 | `DESTINATION_NOT_APPROVED` | Refus SOURCE-GUARD |
| 403 | `DESTINATION_OUT_OF_SCOPE` | Refus de confinement effectif |
| 413 | `HTTP_413` | Entrée supérieure à 4096 octets |
| 415 | `INVALID_INPUT` | Type d'entrée autre que JSON |
| 502 | `DNS_FAILURE`, `DESTINATION_UNREACHABLE`, `UNSUPPORTED_ENCODING` | Échec transport/contenu |
| 503 | `RESOLVER_BUSY` | Connecteur occupé |
| 504 | `DNS_TIMEOUT`, `UPSTREAM_TIMEOUT` | Délai dépassé |
| 500 | `INTERNAL_ERROR` | Incident sans traceback public |

Les erreurs ont `ok: false`, `error` et `message`. Les statuts amont restent
distincts de ces statuts du portail. Les logs Gunicorn conservent les chemins
et statuts, pas les corps de réponse ni le JSON entrant.

## Fichiers ajoutés ou modifiés pour la V3

- `defi/app/data.py` : métadonnée de corrélation et note de provenance.
- `defi/app/templates/journal.html` : champ technique Correlation ID.
- `defi/services/relay.py` : registres de données, routes de traces et lookup par handle.
- `defi/tools/check_trace_contract.py` : contrôles positifs de contrat avec preuve de fixture.
- `defi/README.md` : livraison et commandes V3.

Auth/CSRF/session, politique SOURCE-GUARD, transport, CSS/JS, catalogue, Docker,
Compose, dépendances, challenge.yml, `.env`,
les autres challenges et `solution/` sont conservés. Aucun solveur ou rapport
d'audit V3 écrit ; aucun commit ni push.

## Vérifications ordinaires et suite de l'audit

Contrôles V3 : syntaxe Python, Ruff lint/format, YAML et Compose quiet ; build
du portail/relais, démarrage et trois healthchecks ; connexion/déconnexion
ordinaires, pages authentifiées, journal avec corrélation et les quatre ressources
documentaires ordinaires (index et trois documents) récupérées par HTTP réel.
Inspection des ports et réseaux conservés, comparaison des empreintes des fichiers
du socle V2, du packaging et de `solution/`.

Les contrats JSON et la cohérence portail → trace → allocation sont contrôlés
par un **client Flask avec flag de fixture**, sans HTTP ni SSRF et sans lecture de
la preuve réelle. Le script reçoit le correlation ID du portail, contrôle les
registres, états et référence BV, et n'affiche ni corps privé ni flag. Pour
reproduire le contrôle positif dans l'image du relais :

```bash
docker compose --env-file web/mirror-gate/defi/.env -p mirror-gate -f web/mirror-gate/defi/docker-compose.yml exec -T ng-r-relay python - --correlation-id TRC-2147-0912 < web/mirror-gate/defi/tools/check_trace_contract.py
```

L'outil check_runtime V2 reste inchangé pour l'auditeur ; sa batterie incluant
des cas négatifs n'a pas été relancée pour cette livraison V3. Les tests négatifs,
anciens chemins et scénarios SSRF sont réservés au nouvel audit.

Claude Code doit réaliser un **audit V3** : solve en boîte noire, SSRF/bypass,
corrélation depuis le journal, consultation de trace et fiche par handle,
raccourcis V2/aliases/listes/fuites, tests négatifs des routes, audit de session et
confinement, reconstruction et solve reproductible, évaluation indépendante
de la difficulté. Le verdict V2 n'est pas un verdict V3.
Actualisation des trois fichiers `solution/` sous sa responsabilité.
Codex n'a pas envoyé de payload de contournement vers NG-R, récupéré le flag réel,
cherché des bypass alternatifs ni réalisé de pentest ou de tests négatifs V3.

Le labo doit confirmer `requirements: ["Phantom Badge"]` (nom exact existant),
le calcul logarithmique du wrapper CTFd, les réseaux/IPAM, les ACL de l'entrée et
le reverse proxy HTTPS avec Secure. Aucun support ctf-cli garanti.
`connection_info` reste vide, le challenge hidden ; difficulté et durée à mesurer
par playtest humain après audit, sans nouvelle révélation narrative.


## Révision du 12 octobre 2026

Le module d'approbation est désormais `app/source_guard.py` ; le prédicat et le
transport sont inchangés. KB-MIRROR-023 décrit une erreur de
conception d'une protection actuelle.
Sur instruction finale de l’utilisateur, les vérifications de cette révision
sont confiées à Claude Code. Les builds de test ont été interrompus avant tout
démarrage d’instance isolée. Les contrôles historiques ne valident pas cette
révision. Un réaudit indépendant reste requis avant tout verdict.


## Révision — Calibration des indices et découverte joueur

Révision éditoriale du 12 octobre 2026. KB-MIRROR-023 décrit la politique moderne
SOURCE-GUARD 1.2, la source approuvée et les diagnostics de consultation ; elle
n'explique plus le préfixe d'autorité ni la différence avec le parsing HTTP.
MG-OPS-04 présente les familles de relais et leurs interfaces actuelles. Le port
9090 reste dans le tableau : journal (nom du relais), tableau (protocole/port),
index HTTP (chemins) et corrélation restent des informations découvrables.
La prévisualisation conserve ses comptes rendus et ses actions réelles.

SSRF, userinfo, prédicat SOURCE-GUARD, transport, réseau, trace, handle et flag
restent inchangés. Les explications techniques de ce README sont réservées à
l'organisation. Aucun test, solve, build, Docker ou réaudit exécuté par Codex pour
cette révision.
