# Writeup — rapport-annuel

**Catégorie :** stégano · **Niveau :** intermédiaire
**Flag :** `FPS{pdf_zip_polyglotte_spectrogramme_puis_steghide}`

Chaîne à 3 étages.

## 1. Polyglotte PDF + ZIP

`rapport-annuel.pdf` s'ouvre comme un PDF normal, mais c'est **aussi** une
archive ZIP valide (le ZIP est appondu après le PDF, offsets ajustés avec
`zip -A`). On repère l'anomalie avec `binwalk`, ou simplement :

```
unzip rapport-annuel.pdf -d annexe
# audio-corporate.wav, photo-equipe.jpg, LISEZMOI.txt
```

## 2. Spectrogramme → mot de passe

`audio-corporate.wav` sonne comme du bruit. Son **spectrogramme** affiche le
texte `AUDIT2026` :

- Audacity : piste → *Spectrogramme* ;
- Sonic Visualiser ;
- `sox audio-corporate.wav -n spectrogram -o spec.png`.

## 3. steghide

Le mot de passe déverrouille les données cachées dans l'image porteuse :

```
steghide extract -sf photo-equipe.jpg -p AUDIT2026
# écrit flag.txt
```

`solve.py` automatise tout (dézip, STFT + OCR du spectrogramme, steghide) :

```
python3 solve.py
# mot de passe lu au spectrogramme: AUDIT2026
# FPS{pdf_zip_polyglotte_spectrogramme_puis_steghide}
```

## Remédiation / notes

- Un PDF « trop lourd » ou des octets après `%%EOF` trahissent un polyglotte.
- La stégano audio par spectrogramme est invisible à l'écoute mais évidente à
  l'analyse fréquentielle.

*(`gen.py` reconstruit tout le challenge, y compris l'embarquement steghide.)*
