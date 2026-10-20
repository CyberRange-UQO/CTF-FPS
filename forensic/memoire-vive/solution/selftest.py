#!/usr/bin/env python3
"""Self-test local de F5 (sans VM ni Volatility).

Valide toute la logique crypto/demasquage de bout en bout :
  - simule l'artefact memoire (MEMKEY01 + cle masquee par un PID)
  - fabrique un x.enc comme en F4
  - rejoue solve.py (find_live_keyblob + recover + dechiffrement) et verifie le flag

C'est la partie du defi independante de la capture memoire reelle ; le dump
brut et Volatility ne font que *fournir* le buffer masque et le PID, exactement
ce qu'on simule ici.
"""
import gzip
import os
import tempfile

import shared_secret as s
import solve

FAKE_PID = 4321


def main():
    # 1. artefact memoire tel que stage2 le laisse (cf. stage2.c)
    mkey = s.mask_key_for_pid(FAKE_PID)
    blob = b"MEMKEY01" + mkey + s.NONCE
    mem = b"\x00" * 100000 + blob + b"\x00" * 100000  # noye dans du bruit

    # 2. x.enc comme en F4
    inner = gzip.compress(b"flag: " + s.F5_FLAG.encode() + b"\n")
    xenc = s.encrypt(inner)

    with tempfile.TemporaryDirectory() as d:
        dump = os.path.join(d, "memory.lime")
        xf = os.path.join(d, "x.enc")
        open(dump, "wb").write(mem)
        open(xf, "wb").write(xenc)

        # 3. rejoue les primitives du solveur
        rk, nonce = solve.find_live_keyblob(open(dump,"rb").read())
        assert nonce == s.NONCE
        key = solve.recover(rk, FAKE_PID)
        assert key == s.KEY, "demasquage incorrect"

        from Crypto.Cipher import AES
        pt = gzip.decompress(AES.new(key, AES.MODE_CTR, nonce=nonce)
                             .decrypt(open(xf, "rb").read()))
        assert s.F5_FLAG.encode() in pt, "dechiffrement incorrect"
    print("SELF-TEST OK ->", s.F5_FLAG)


if __name__ == "__main__":
    main()
