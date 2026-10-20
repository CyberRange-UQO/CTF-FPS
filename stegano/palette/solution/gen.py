#!/usr/bin/env python3
"""Genere le defi palette.

Une image en couleurs indexees, visuellement normale. Le flag est encode dans
l'ORDRE de la palette : les pixels sont re-indexes pour que l'image affichee
reste identique, seul l'ordre des couleurs change.
"""
import os
from math import factorial

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from PIL.PngImagePlugin import PngInfo

from common import lum_key, perm_from_int

HERE = os.path.dirname(os.path.abspath(__file__))
DEFI = os.path.normpath(os.path.join(HERE, "..", "defi"))
FONTB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

FLAG = b"FPS{ordre_de_palette_permutation_code_de_lehmer}"


def build_logo():
    """Image RGB 'logo' avec un degrade (beaucoup de couleurs distinctes)."""
    W, H = 480, 300
    arr = np.zeros((H, W, 3), dtype=np.uint8)
    for y in range(H):
        for x in range(W):
            arr[y, x] = (
                40 + (x * 180) // W,
                60 + (y * 150) // H,
                120 + ((x + y) * 90) // (W + H),
            )
    img = Image.fromarray(arr, "RGB")
    d = ImageDraw.Draw(img)
    d.text((40, 110), "CORP", font=ImageFont.truetype(FONTB, 120),
           fill=(245, 245, 245))
    return img


def main():
    os.makedirs(DEFI, exist_ok=True)
    rgb = build_logo().convert("P", palette=Image.ADAPTIVE, colors=256)

    pal = rgb.getpalette()
    idx = np.asarray(rgb)
    used = sorted(set(int(v) for v in idx.flatten()))
    colors = [tuple(pal[3 * i:3 * i + 3]) for i in used]       # couleurs utilisees
    remap_used = {old: new for new, old in enumerate(used)}    # compacte 0..N-1
    N = len(colors)

    cap_bits = 0
    f = factorial(N)
    cap_bits = f.bit_length() - 1
    msg_int = int.from_bytes(b"\x01" + FLAG, "big")  # marqueur 0x01 en tete
    assert msg_int < factorial(N), f"capacite {cap_bits} bits insuffisante"

    # Ordre canonique (tri par luminance) et permutation issue du message.
    canon = sorted(range(N), key=lambda i: lum_key(colors[i]))  # rangs -> indices compacts
    C = [colors[i] for i in canon]                              # couleurs triees
    perm = perm_from_int(msg_int, N)                            # slot j -> rang canonique

    # Palette stockee : slot j contient la couleur canonique de rang perm[j].
    stored = [C[perm[j]] for j in range(N)]
    inv = [0] * N
    for j, r in enumerate(perm):
        inv[r] = j  # rang canonique r -> slot j

    # canonique rang d'une couleur compacte -> position dans C
    rank_of = {canon[r]: r for r in range(N)}

    # Remappe les pixels : couleur d'origine -> compact -> rang -> slot stocke.
    flat = idx.flatten()
    newflat = np.empty_like(flat)
    for p, old in enumerate(flat):
        compact = remap_used[int(old)]
        newflat[p] = inv[rank_of[compact]]
    newidx = newflat.reshape(idx.shape)

    out = Image.new("P", (idx.shape[1], idx.shape[0]))
    flatpal = []
    for c in stored:
        flatpal += list(c)
    flatpal += [0, 0, 0] * (256 - N)
    out.putpalette(flatpal)
    out.putdata(newflat.tolist())

    meta = PngInfo()
    meta.add_text("Comment", "Palette triee ? cle = luminance (Rec.601).")
    path = os.path.join(DEFI, "logo-corp-indexe.png")
    out.save(path, "PNG", optimize=False, pnginfo=meta)
    print(f"genere: {path}  (N={N} couleurs, capacite {cap_bits} bits)")


if __name__ == "__main__":
    main()
