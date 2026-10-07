# Write-up — Challenge Ebooks

## Étape 1 — Comprendre le format EPUB

La première étape consiste à se renseigner sur le fonctionnement d’un **e-book** et notamment sur le format `.epub`.

En cherchant quelques informations sur Internet, on découvre qu’un fichier EPUB est une archive ZIP contenant différents fichiers nécessaires au fonctionnement et à l'affichage du livre.

Il est donc possible d'explorer directement son contenu.

---

## Étape 2 — Extraire le contenu du livre

Pour accéder aux différents fichiers contenus dans l'e-book, il suffit de modifier l'extension du fichier.

On renomme :

```text
Maxime Chattam – La Trilogie du Mal.epub → Maxime Chattam – La Trilogie du Mal.zip
```

On peut ensuite ouvrir ou extraire l'archive ZIP afin d'obtenir l'ensemble des fichiers constituant le livre.

On retrouve alors les différents éléments du livre, notamment les fichiers correspondant aux différents tomes et aux pages.

---

## Étape 3 — Décoder la clé

Une fois le contenu du livre récupéré, on s'intéresse à la clé fournie avec le challenge.

Il faut comprendre que les nombres sont codés sur **16 bits**. Après avoir décodé la suite binaire, on obtient :

```text
1_10_4_1038_1_10_13_778_1_16_67_400_1_12_41_876_2_69_64_344_2_21_17_241_2_80_75_276
```

La suite peut alors être séparée en groupes de quatre nombres :

```text
1  _ 10 _ 4  _ 1038
1  _ 10 _ 13 _ 778
1  _ 16 _ 67 _ 400
1  _ 12 _ 41 _ 876
2  _ 69 _ 64 _ 344
2  _ 21 _ 17 _ 241
2  _ 80 _ 75 _ 276
```

Il reste maintenant à comprendre à quoi correspondent ces quatre valeurs.

---

## Étape 4 — Comprendre l'indexation

Chaque groupe de quatre nombres correspond à une information permettant de retrouver un mot précis dans le livre.

La structure est la suivante :

```text
[Tome]_[Fichier]_[Page]_[Mot]
```

* **1er nombre** → le tome du livre ;
* **2e nombre** → le numéro du fichier ;
* **3e nombre** → le numéro de la page ;
* **4e nombre** → la position du mot caché sur cette page.

En utilisant ces informations pour parcourir les différents fichiers du livre et récupérer les mots indiqués, on peut reconstituer progressivement le message caché.

Une fois tous les mots récupérés et remis dans le bon ordre, on obtient finalement :

```text
NBCTF{Brolin_est_un_super_flic_du_FBI}
```
