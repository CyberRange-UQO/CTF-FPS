#!/usr/bin/env python3
"""Solveur presentation-trimestrielle.

Un .pptx est un zip. Le rognage PowerPoint ne supprime pas l'image : on
extrait ppt/media/, et la zone masquee (bas de l'image) contient le flag.

Le joueur le lit a l'oeil ; ici on OCR la bande basse pour un test automatique.
(En CTF, "Reinitialiser l'image" dans PowerPoint ou un simple unzip suffit.)
"""
import os
import re
import sys
import zipfile

from PIL import Image
import pytesseract

HERE = os.path.dirname(os.path.abspath(__file__))
DEFI = os.path.normpath(os.path.join(HERE, "..", "defi"))
CROP_BOTTOM = 0.32


def main():
    pptx = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        DEFI, "presentation-T3-2026.pptx")
    out = os.path.join(HERE, "extrait")
    os.makedirs(out, exist_ok=True)

    with zipfile.ZipFile(pptx) as z:
        medias = [n for n in z.namelist() if n.startswith("ppt/media/")]
        img_path = os.path.join(out, os.path.basename(medias[0]))
        with open(img_path, "wb") as f:
            f.write(z.read(medias[0]))
    print("image complete extraite:", img_path)

    img = Image.open(img_path).convert("RGB")
    w, h = img.size
    band = img.crop((0, int(h * (1 - CROP_BOTTOM)), w, h))  # zone masquee
    text = pytesseract.image_to_string(band)
    m = re.search(r"FPS\{[^}]+\}", text.replace(" ", ""))
    print(m.group(0) if m else "OCR:\n" + text)


if __name__ == "__main__":
    main()
