# Writeup : Oui Allo?

## Énoncé

« Vous êtes en charge du triage! N'oubliez pas de noter à quel service transférer l'appel
(111, 211, 311, 411, 511, 811, 911) et leur adresse... » Format : `FLAG_XXXXXXXXXX`
(10 caractères).

On reçoit `calls.zip` contenant 10 vidéos `1.mp4` … `10.mp4` : un écran noir avec le numéro
de l'appel, et un message vocal (en français puis en anglais).

## Résolution

### 1. Trier chaque appel

Les numéros N11 au Québec :

| Numéro | Service |
|---|---|
| 211 | Ressources communautaires et sociales |
| 311 | Services municipaux (non urgents) |
| 411 | Annuaire / renseignements |
| 511 | Info routière (Québec 511) |
| 811 | Info-Santé / Info-Social |
| 911 | Urgences |

En écoutant chaque appel (ou en le transcrivant, par exemple avec Whisper) :

| Appel | Rue de l'appelant | Demande | Service |
|---|---|---|---|
| 1 | rue du Prado | nid-de-poule devant l'entrée | 311 |
| 2 | rue de Beauchastel | cheville tordue, faut-il consulter ? | 811 |
| 3 | rue Beau-Séjour | état de l'autoroute 50 avant d'aller à Montréal | 511 |
| 4 | rue des Abricotiers | numéro d'un garage | 411 |
| 5 | rue Asselin | voisin sans emploi, besoin d'une banque alimentaire | 211 |
| 6 | rue Latour | feu de circulation éteint | 311 |
| 7 | rue de l'Albatros | coordonnées d'une clinique dentaire | 411 |
| 8 | rue de Bienville | numéro d'un organisme communautaire | 411 |
| 9 | rue de l'Acadie | famille sans hébergement ce soir | 211 |
| 10 | rue de la Belle-Humeur | fumée noire et flammes, quelqu'un à l'intérieur | 911 |

### 2. Extraire une lettre par appel

Le premier chiffre du service donne la position de la lettre à prendre dans le nom de la rue :

| Appel | Rue | Service | Lettre |
|---|---|---|---|
| 1 | Prado | 3 | `A` |
| 2 | Beauchastel | 8 | `S` |
| 3 | BeauSéjour | 5 | `S` |
| 4 | Abricotiers | 4 | `I` |
| 5 | Asselin | 2 | `S` |
| 6 | Latour | 3 | `T` |
| 7 | Albatros | 4 | `A` |
| 8 | Bienville | 4 | `N` |
| 9 | Acadie | 2 | `C` |
| 10 | BelleHumeur | 9 | `E` |

> Note : ce writeup a été reconstitué après l'event à partir d'une transcription automatique
> des appels. L'orthographe exacte de certaines rues (2, 5, 6, 8, 10) est à confirmer par
> l'auteur, mais chaque lettre extraite correspond au flag validé.

## Flag

`FLAG_ASSISTANCE`
