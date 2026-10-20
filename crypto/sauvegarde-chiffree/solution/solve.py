#!/usr/bin/env python3
"""Solveur sauvegarde-chiffree.

La graine XOR est int(time.time()) a la seconde ou le backup a tourne.
backup.log donne la minute -> 60 graines candidates. On reconnait la bonne
au header gzip (1f 8b) puis on decompresse pour lire le flag.
"""
import calendar
import gzip
import io
import os
import random
import re
import tarfile

HERE = os.path.dirname(os.path.abspath(__file__))
DEFI = os.path.normpath(os.path.join(HERE, "..", "defi"))


def keystream(seed: int, n: int) -> bytes:
    r = random.Random(seed)
    return bytes(r.getrandbits(8) for _ in range(n))


def main():
    with open(os.path.join(DEFI, "sauvegarde.tar.gz.enc"), "rb") as f:
        enc = f.read()
    with open(os.path.join(DEFI, "backup.log")) as f:
        log = f.read()

    # Minute du backup -> epoch de la seconde 0 de cette minute.
    m = re.search(r"(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2})", log)
    y, mo, d, h, mi = map(int, m.groups())
    base = calendar.timegm((y, mo, d, h, mi, 0, 0, 0, 0))

    for seed in range(base, base + 60):
        # Il suffit des 2 premiers octets pour tester le header gzip.
        head = keystream(seed, 2)
        if enc[0] ^ head[0] == 0x1F and enc[1] ^ head[1] == 0x8B:
            ks = keystream(seed, len(enc))
            archive = bytes(a ^ b for a, b in zip(enc, ks))
            tar = tarfile.open(fileobj=io.BytesIO(gzip.decompress(archive)))
            for info in tar.getmembers():
                content = tar.extractfile(info).read().decode(errors="replace")
                m2 = re.search(r"FPS\{[^}]+\}", content)
                if m2:
                    print("graine =", seed)
                    print(m2.group(0))
                    return
    raise SystemExit("echec: aucune graine valide dans la minute")


if __name__ == "__main__":
    main()
