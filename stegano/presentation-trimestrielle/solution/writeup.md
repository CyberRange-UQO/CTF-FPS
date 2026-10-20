# Writeup — presentation-trimestrielle

**Catégorie :** stégano · **Niveau :** débutant
**Flag :** `FPS{rognage_powerpoint_non_destructif_image_intacte}`

## Analyse

Le « rognage » (crop) de PowerPoint est **purement visuel** : il ajoute un
`<a:srcRect>` qui affiche une sous-partie de l'image, mais l'**image d'origine
entière** reste stockée dans le fichier. La zone « masquée » n'est pas supprimée.

## Résolution

Un `.pptx` est une archive ZIP (format OOXML). Deux voies :

**Option A — dézipper :**
```
unzip presentation-T3-2026.pptx -d extrait
# ouvrir extrait/ppt/media/image1.png -> l'image complète, bande basse visible
```

**Option B — dans PowerPoint :** sélectionner l'image → *Format de l'image* →
*Réinitialiser l'image* (ou retirer le rognage), la zone masquée réapparaît.

La bande basse contient la « NOTE CONFIDENTIELLE » et la *Référence interne* =
le flag.

```
python3 solve.py            # extrait l'image + OCR de la bande masquée
# FPS{rognage_powerpoint_non_destructif_image_intacte}
```

## Remédiation

- Pour retirer réellement une zone : **recadrer puis « Compresser les
  images »** avec l'option *Supprimer les zones de rognage*, ou aplatir l'image
  dans un éditeur externe avant insertion.
- Ne jamais considérer le crop Office comme une caviardage.

*(Le générateur `gen.py` reconstruit le `.pptx` à l'identique.)*
