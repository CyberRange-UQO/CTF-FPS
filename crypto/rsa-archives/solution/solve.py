#!/usr/bin/env python3
"""Solveur rsa-archives.

Deux modules partagent un facteur premier. Un PGCD sur chaque paire de modules
revele le facteur commun -> on factorise les deux cles -> cle privee -> OAEP.
"""
import glob
import os
from math import gcd

from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Util.number import inverse

HERE = os.path.dirname(os.path.abspath(__file__))
DEFI = os.path.normpath(os.path.join(HERE, "..", "defi"))


def main():
    pubs = {}
    for path in sorted(glob.glob(os.path.join(DEFI, "pubkeys", "*.pem"))):
        k = RSA.import_key(open(path).read())
        pubs[os.path.basename(path)] = k

    # PGCD sur toutes les paires de modules.
    items = list(pubs.items())
    privs = {}
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            (na, ka), (nb, kb) = items[i], items[j]
            g = gcd(ka.n, kb.n)
            if g != 1:
                print(f"facteur commun entre {na} et {nb}")
                for name, k in ((na, ka), (nb, kb)):
                    p = g
                    q = k.n // p
                    d = inverse(k.e, (p - 1) * (q - 1))
                    privs[name] = RSA.construct((k.n, k.e, d, p, q))

    if not privs:
        raise SystemExit("aucun facteur commun trouve")

    # Dechiffre tout message dechiffrable avec une cle cassee.
    for path in sorted(glob.glob(os.path.join(DEFI, "messages", "*.bin"))):
        ct = open(path, "rb").read()
        for name, priv in privs.items():
            if len(ct) != priv.size_in_bytes():
                continue
            try:
                pt = PKCS1_OAEP.new(priv).decrypt(ct)
            except ValueError:
                continue
            print(os.path.basename(path), "->", pt.decode(errors="replace"))


if __name__ == "__main__":
    main()
