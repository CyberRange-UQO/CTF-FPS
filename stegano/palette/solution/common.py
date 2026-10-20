"""Primitives partagees : tri canonique de palette + code de Lehmer.

Canal cache : l'ORDRE des couleurs dans la palette indexee encode un entier
(donc des octets), via la position de permutation (factorielle / code de Lehmer)
par rapport a l'ordre canonique = tri par luminance Rec.601.
"""
from math import factorial


def lum_key(rgb):
    r, g, b = rgb
    # luminance Rec.601 ; (r,g,b) en tie-break -> ordre total sans ambiguite.
    return (0.299 * r + 0.587 * g + 0.114 * b, r, g, b)


def perm_from_int(m, n):
    """m-eme permutation (lexicographique) de range(n) -> code de Lehmer."""
    elems = list(range(n))
    perm = []
    for i in range(n - 1, -1, -1):
        f = factorial(i)
        d, m = divmod(m, f)
        perm.append(elems.pop(d))
    return perm


def int_from_perm(perm):
    """Inverse : permutation -> entier (rang lexicographique)."""
    n = len(perm)
    elems = list(range(n))
    m = 0
    for i, p in enumerate(perm):
        d = elems.index(p)
        elems.pop(d)
        m += d * factorial(n - 1 - i)
    return m
