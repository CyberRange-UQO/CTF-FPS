#!/usr/bin/env python3
"""Solveur palette.

Le message est code dans l'ORDRE de la palette. On retrouve l'ordre canonique
(tri par luminance), on en deduit la permutation stockee, puis le code de
Lehmer -> entier -> octets -> flag.
"""
import os
import re
import sys

from PIL import Image

from common import lum_key, int_from_perm

HERE = os.path.dirname(os.path.abspath(__file__))
DEFI = os.path.normpath(os.path.join(HERE, "..", "defi"))


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        DEFI, "logo-corp-indexe.png")
    img = Image.open(path)
    assert img.mode == "P", "image non indexee"
    pal = img.getpalette()
    used = sorted(set(img.getdata()))
    stored = [tuple(pal[3 * i:3 * i + 3]) for i in used]  # couleurs, ordre des slots
    N = len(stored)

    # Rang canonique de chaque slot = sa position dans la palette triee.
    order = sorted(range(N), key=lambda i: lum_key(stored[i]))
    rank = [0] * N
    for r, slot in enumerate(order):
        rank[slot] = r
    perm = rank  # slot j -> rang canonique perm[j]

    m = int_from_perm(perm)
    raw = m.to_bytes((m.bit_length() + 7) // 8, "big")
    msg = raw[1:]  # retire le marqueur 0x01
    text = msg.decode(errors="replace")
    flag = re.search(r"FPS\{[^}]+\}", text)
    print(flag.group(0) if flag else "echec:\n" + text)


if __name__ == "__main__":
    main()
