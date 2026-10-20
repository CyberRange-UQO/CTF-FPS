# Writeup : De la musique pour mes oreilles

## Énoncé

On reçoit une image `De_la_musique_pour_mes_oreilles.png` contenant un extrait de partition
(portée en clé de sol + portée en clé de fa). Format du flag : `FLAG_X` en majuscules.

## Résolution

Il n'y a rien de caché dans le fichier : il faut reconnaître le morceau.

1. Déchiffrer ou rejouer la partition (sur un piano, ou en la recopiant dans un logiciel comme
   MuseScore / un piano en ligne).
2. La ligne de basse en croches montantes et la mélodie syncopée de la main droite sont
   immédiatement reconnaissables : c'est le thème de **Ghostbusters** (Ray Parker Jr., 1984).

On peut aussi passer l'image dans un outil de reconnaissance de partition (OMR) puis écouter
le MIDI généré.

## Flag

`FLAG_GHOSTBUSTERS`
