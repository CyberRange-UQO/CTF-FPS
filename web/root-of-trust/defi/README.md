# ROOT OF TRUST V1 — organisation et déploiement

Implémentation du final VANTA//SYSTEMS, ROT-05.

**Aucune validation exécutée par Codex.** Ni installation de dépendances,
build, lancement, test, contrôle syntaxique, endpoint, solve ou audit. Les
commandes ci-dessous sont destinées à l'organisation et à Claude Code.
Il ne s'agit pas d'un verdict de sécurité ou de jouabilité.

## Architecture

Un seul service Flask/Gunicorn, autonome, sans base de données ni appels
sortants. Les événements sont statiques en mémoire ; chaque consultation
renvoie une copie avec son digest recalculé. Aucun stockage de reçus.

| Fichier | Responsabilité |
| --- | --- |
| `app/app.py` | Factory Flask, routes exactes, vérification du sas, erreurs sûres et limites HTTP |
| `app/auth.py` | Vérification PyJWT HS256 fixée, claims exacts et permissions par route |
| `app/encoding.py` | Base64URL canonique et secrets de 32 octets |
| `app/canonical.py` | JSON compact normatif, SHA-256 et refus des membres dupliqués |
| `app/events.py` | Copie indépendante des neuf événements historiques et contexte du cas |
| `app/proof.py` | Schéma du manifeste, engagement signé, intégrité des pièces, corrélation |
| `app/attestation.py` | Autorité Ed25519 privée, clé publique raw, reçu signé et flag serveur |
| `app/contracts.py` | Contrat et politique publics, vecteur SHA-256 neutre |
| `app/errors.py`, `app/__init__.py` | Erreurs métier et package |
| `app/templates/index.html` | Sas AUTHORITY GATEWAY, cinq espaces métier indépendants, reçu et transmission STATIC |
| `app/static/trust.css`, `app/static/trust.js` | Identité noir/ivoire/or, cycle du mandat en mémoire et interactions réelles |
| `Dockerfile`, `docker-compose.yml` | Service non-root et confinement déclaratif |
| `.dockerignore`, `.env.example` | Contexte d'image en liste d'autorisation, configuration vide |
| `requirements.in`, `requirements.txt` | Dépendances directes et transitives figées avec hashes |
| `challenge.yml` | Packaging CTFd caché, dépendance BLACK VAULT |
| `README.md` | Organisation et déploiement |

### Chemin d'une demande

À l'ouverture, AUTHORITY GATEWAY présente le mandat de lecture. L'atelier est
masqué jusqu'à la réponse de `GET /api/authority/verify`, qui appelle le
vérificateur central avec `case:read`. Cette route retourne uniquement une
confirmation, le cas et l'échéance/durée restante, sans jeton ni session
backend. Les contrats, politiques et clé publique restent publics dans le sas.

Le mandat reste en mémoire JavaScript et sert ensuite aux APIs de lecture.
Chaque API vérifie toujours sa propre requête. Une échéance calculée depuis la
réponse serveur, ou un refus `401`/`403` de lecture, ramène au sas. Le manifeste
et la sélection restent en mémoire pour reprendre après renouvellement.
« Fermer la session d'autorité » efface les mandats et masque l'atelier ;
cette action ne révoque pas cryptographiquement les JWT déjà émis. La
transition de 400 ms ne bloque pas l'atelier et disparaît avec reduced motion.

Le mandat de publication reste fourni dans son formulaire distinct. Son refus
ne ferme pas une autorité de lecture valide. Ni le sas ni son état JavaScript
ne créent de permission supplémentaire.

Une lecture exige `case:read`. Une publication exige `disclosure:publish`.
PyJWT valide la signature HS256 avec une liste d'algorithmes fixée et une clé
fixe, puis les claims enregistrés. Le code ajoute les types exacts, cas,
permissions connues/uniques, durée et fenêtre `iat`, ainsi que le lien de preuve.
Les headers/JSON dupliqués, champs supplémentaires et encodages non canoniques
sont refusés. `exp` reste strictement futur malgré la tolérance de 30 secondes
nécessaire à `iat`. Aucune primitive n'est sélectionnée depuis une référence
distante ou un chemin `kid`.

La publication valide dans l'ordre : autorisation, forme du manifeste,
empreinte canonique comparée au claim signé, empreintes originales des
événements, relations sémantiques, construction puis signature du reçu.
Le vérificateur recherche une chaîne relationnelle sur les champs métier,
sans comparer des IDs gagnants. Les comparaisons de digests sont constantes.

L'effacement concerne EID-1057/MIRA-07, la directive SIL-4/2147-07 et l'incident
SEC-2147-089 repris de PHANTOM BADGE. L'allocation NG-R, son instance et sa
trace doivent coïncider ; l'observation est strictement postérieure à
l'effacement et pas antérieure au lien de trace. Le bulletin SYNC_ERROR
partage le contexte et suit l'effacement. Les neuf pièces datent du 16 octobre
2147 UTC ; les epochs sont calculés à partir de dates UTC explicites.

Un rapport cohérent ou une observation antérieure pertinente peuvent s'ajouter
à une chaîne complète. Une autre identité, un autre incident, un état ou des
références contradictoires invalident la sélection. L'activité antérieure
seule ne démontre pas la continuité postérieure. Le moteur de preuve conserve
ces règles ; la politique publique présente les objectifs d'audit et de
cohérence, sans décrire la sélection concrète ni ses contre-exemples.

### Deux clés indépendantes

`ROOT_AUDIT_KEY_B64U` doit être **la valeur déjà provisionnée dans BLACK VAULT**.
Les 32 octets décodés servent exclusivement à vérifier les demandes JWT.
Le service ne génère jamais cette clé et n'interroge pas BLACK VAULT.

`ATTESTATION_ED25519_SEED_B64U` est une graine privée distincte, de 32 octets.
Le service refuse aussi deux valeurs décodées identiques. Ed25519 signe le
JSON canonique de `receipt` seul. L'enveloppe expose une signature de 64 octets
et le document public expose uniquement la clé publique raw de 32 octets,
les deux en Base64URL sans padding. Le reçu est retourné seulement à la
demande validée et n'est ni stocké ni recherchable par une route publique.

## Provisionnement privé — à effectuer par l'organisation

Dans `web/root-of-trust/defi/`, copier `.env.example` en `.env`, appliquer des
permissions privées et renseigner la valeur ROOT-AUDIT existante via votre
gestionnaire de secrets. Ne pas afficher ni recopier le secret dans les logs,
les commandes, une URL ou les livrables publics. Ne modifier aucun fichier de
BLACK VAULT depuis cette mission.

```bash
cp .env.example .env
chmod 600 .env
```

Pour préparer **la graine Ed25519 seulement**, l'exemple suivant écrit
directement dans le `.env` local, sans afficher la valeur. Il refuse de
remplacer une graine existante. C'est une action d'organisation, pas un
comportement de démarrage du service ; Codex ne l'a pas exécutée.

```bash
python3 - <<'PY'
import base64
import os
from pathlib import Path
import secrets

path = Path('.env')
lines = path.read_text(encoding='utf-8').splitlines()
field = 'ATTESTATION_ED25519_SEED_B64U='
positions = [index for index, line in enumerate(lines) if line.startswith(field)]
if len(positions) != 1 or lines[positions[0]] != field:
    raise SystemExit('Une seule entrée de graine vide est requise ; aucune rotation implicite.')
encoded = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b'=').decode('ascii')
lines[positions[0]] = field + encoded
os.chmod(path, 0o600)
path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
PY
```

Dans un laboratoire neuf sans clé de campagne, l'organisation peut générer
**une seule fois** 32 octets aléatoires avec la même recette Base64URL, les
conserver dans son gestionnaire privé, puis provisionner exactement cette
valeur dans les configurations privées des deux challenges. Si BLACK VAULT
est déjà déployé, réutiliser sa clé ; ne jamais la remplacer par une nouvelle
clé indépendante pour ROOT. La graine Ed25519 est générée séparément.

Une variable absente, un alphabet invalide, du padding, un encodage non
canonique ou une taille différente de 32 octets provoque un refus de démarrage.
Compose refuse également les valeurs vides avant de démarrer le conteneur.

## Docker — commandes réservées à Claude Code

Le nom de projet par défaut est désormais `vanta-root-of-trust`, défini au
niveau racine du Compose. GHOST RECORD utilise `vanta-ghost-record` : les deux
périmètres ont des identités indépendantes. Aucun nom fixe de conteneur ou de
réseau n’est ajouté. L’orchestrateur peut imposer une identité avec `docker
compose -p <projet>` ; cette option prime sur `COMPOSE_PROJECT_NAME`, qui prime
à son tour sur `name:` ([ordre officiel](https://docs.docker.com/compose/how-tos/project-name/)).
Le wrapper du laboratoire et sa version de Compose restent à vérifier.

Le changement de nom ne migre ni ne nettoie le projet historique `defi`.
Avant toute remise en service sur 8084, vérifier que le port est libre, après
autorisation explicite. Les commandes ci-dessous, depuis la racine du dépôt,
concernent le nouveau projet ; ne pas les utiliser pour reprendre un port encore
occupé par une ancienne instance.

```bash
cd web/root-of-trust/defi
docker compose build --no-cache
docker compose up -d
docker compose ps
curl --fail http://127.0.0.1:8084/healthz
```

Port local `127.0.0.1:8084`, override par `ROOT_OF_TRUST_BIND` et
`ROOT_OF_TRUST_PORT`. Aucun secret en ARG/COPY, contexte en liste
d'autorisation, dépendances installées seulement au build. Le runtime n'a
aucun besoin d'Internet. L'image de base est figée par le digest déjà utilisé
dans le dépôt. Les hashes Flask/Gunicorn sont repris du packaging existant ;
les ajouts PyJWT/cryptography/cffi/pycparser utilisent les hashes publiés sur
PyPI. Aucun téléchargement de wheel, installation ou résolution exécuté ici.

La cible de dépendances est CPython 3.12, Linux glibc amd64/arm64. Le build
impose les wheels et les hashes ; toute autre plateforme requiert un lock
adapté par l'organisation. Sources : [PyJWT](https://pypi.org/project/PyJWT/2.15.1/),
[cryptography](https://pypi.org/project/cryptography/50.0.2/),
[cffi](https://pypi.org/project/cffi/2.0.0/),
[pycparser](https://pypi.org/project/pycparser/2.23/).

UID/GID 10001, `read_only: true`, tmpfs `/tmp` de 16 Mio, capacités supprimées,
`no-new-privileges`, 64 PIDs, 192 Mio de RAM, 1 CPU. Aucun montage hôte, socket
Docker, second service ou réseau partagé avec la campagne. Bridge dédié
`trust-isolated` (`driver: bridge`), avec les options
`com.docker.network.bridge.enable_icc: "false"` et
`com.docker.network.bridge.enable_ip_masquerade: "false"` : communication
inter-conteneurs et masquerading désactivés.
La publication du port sur le moteur Docker du labo reste à vérifier par Claude.
Ne pas désactiver l'isolement pour contourner un problème de port sans arbitrage.

Gunicorn : un worker, quatre threads, aucune session/cookie Flask et aucun
debug. Corps de 16 Kio, ligne HTTP de 2048 octets, 32 headers de 6144 octets
maximum chacun ; autorisation applicative bornée à 4103 caractères. Catalogue
de neuf pièces, manifeste de douze références maximum, aucun état joueur ni
reçu accumulé côté serveur. Pas de limitation de rythme par IP introduite :
les opérations sont bornées, sans boucle non bornée ou stockage. Claude devra
confirmer le comportement sous charge et les limites du labo.

Le healthcheck HTTP est générique. Pas de journal d'accès, de corps, de claims
ou de reçu dans les logs applicatifs. Les erreurs inattendues journalisent
uniquement une catégorie fixe. Les réponses portent `no-store`, une CSP
locale, des protections de framing et de type MIME. Aucun CDN ni ressource
distante. Clavier, focus visible, mobile et réduction de mouvement sont
préparés dans le code ; validation humaine réservée à la revue indépendante.

## CTFd

`author: Samuel Boisneault`, repris exactement des challenges existants.
Défi web dynamique, caché, 500 points initiaux, décroissance 20, minimum 100,
fonction logarithmique, dépendance `["BLACK VAULT"]`, `files: []` et
`connection_info: ""`. Le flag serveur et le YAML reprennent le flag V1.
Le YAML reste un fichier organisateur : ne pas le servir aux joueurs.

Le wrapper du labo doit confirmer les dépendances par **nom** et
`extra.function: logarithmic`. Aucun import CTFd effectué. `requirements`
ne protège pas l'application : les routes exigent toujours leurs JWT.

## État de livraison

Le code et les ressources sont livrés pour revue.
Les contrats cryptographiques sont conservés. Les quatre autres défis,
le packaging Docker et `solution/` restent intacts dans cette révision du sas.
Aucun commit ni push. Aucun verdict de sécurité, de difficulté mesurée,
de playtest ou d'audit n'est émis.


## Révision — Calibration des indices et découverte joueur

Documentation interne d'exploitation. Révision du 12 octobre 2026 : le sas
n'indique plus la provenance de la clé compromise, la fabrication du mandat,
le scope d'entrée ou le dossier cible dans son formulaire. Les valeurs requises
restent dans le contrat public consultable sans autorisation. Le champ `jwt.key`
décrit le matériel de l'autorité et son encodage, sans renvoyer à BLACK VAULT.

Le terminal remplace la progression numérotée par cinq vues métier : provenance,
dossiers, divulgation, reçus et autorité. La barre de session regroupe le mandat
courant, son échéance, son remplacement et la fermeture locale. La navigation
utilise des liens et des vues `hidden` ; l'espace actif est conservé au renouvellement.
Le catalogue intégral est présenté chronologiquement, sans sélection automatique.
Les métadonnées et empreintes affichées proviennent de la réponse existante du registre.

`POLICY` conserve ses champs et sa liste de cinq textes ; seuls les objectifs
humains et la description des pièces supplémentaires sont reformulés. Le moteur
`proof.py` n'en dépend pas pour décider : ses prédicats restent inchangés.
JWT, SHA-256, Ed25519, manifestes, événements, routes, clés, flags et packaging
ne changent pas.

Aucune vérification de cette révision par Codex.
