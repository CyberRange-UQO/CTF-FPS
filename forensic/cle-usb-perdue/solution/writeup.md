# Writeup : cle-usb-perdue

## Énoncé

Une clé USB trouvée sur le stationnement semble presque vide (photos, CV, horaires), mais
l'ancien propriétaire a peut-être effacé des documents. Fichier : `cle-usb.img`.

## Résolution

### 1. Identifier la partition

```console
$ mmls cle-usb.img
002:  000:000   0000002048   0000262143   0000260096   Win95 FAT32 (0x0c)
```

Une partition FAT32 commence au secteur 2048.

### 2. Lister les fichiers, y compris supprimés

```console
$ fls -r -o 2048 cle-usb.img
r/r 5:	chantier1.jpg
r/r 7:	chantier2.jpg
r/r 9:	horaires.csv
r/r 11:	CV.docx
r/r 13:	notes.txt
r/r * 16:	rapport_interne.docx
r/r * 723:	brouillon.docx
r/r * 725:	archive.zip
```

Les entrées marquées `*` sont supprimées mais encore récupérables : en FAT, la suppression ne
fait que marquer l'entrée de répertoire, les données restent sur le disque.

### 3. Récupérer les fichiers

```bash
tsk_recover -e -o 2048 cle-usb.img recup/
# ou : icat -o 2048 cle-usb.img 16 > rapport_interne.docx
```

(PhotoRec, Autopsy ou testdisk fonctionnent aussi.)

### 4. Lire les documents

- `brouillon.docx` contient un leurre : `FPS{ce_brouillon_nest_pas_le_bon_flag}`
  (« Voir la version finale dans le compte rendu »).
- `archive.zip` est une archive vide.
- `rapport_interne.docx` (« COMPTE RENDU INTERNE - CONFIDENTIEL ») contient le vrai code :

```bash
unzip -p recup/rapport_interne.docx word/document.xml | sed 's/<[^>]*>/ /g'
```

## Flag

`FPS{une_cle_usb_effacee_nest_jamais_vraiment_vide}`
