#!/usr/bin/env python3
"""Solveur journal-apache.

1. Reperer l'IP attaquante (volume + motif SUBSTRING...>CHAR).
2. URL-decoder les requetes, extraire (position n, borne x, verdict).
   Verdict TRUE/FALSE = taille de reponse (la grande vs la petite).
3. Pour chaque position, le caractere = plus petit x tel que (char > x) est
   FAUX  ==  (plus grand x avec TRUE) + 1.
"""
import os
import re
import sys
import urllib.parse
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DEFI = os.path.normpath(os.path.join(HERE, "..", "defi"))

LINE = re.compile(r'^(\S+) \S+ \S+ \[[^\]]+\] "(\S+) (\S+) [^"]*" (\d+) (\d+)')
PAYLOAD = re.compile(r"SUBSTRING\(\(SELECT secret FROM config\),(\d+),1\)>CHAR\((\d+)\)")


def main():
    log = sys.argv[1] if len(sys.argv) > 1 else os.path.join(DEFI, "access.log")
    entries = []
    for line in open(log):
        m = LINE.match(line)
        if m:
            ip, method, path, status, size = m.groups()
            entries.append((ip, urllib.parse.unquote(path), int(size)))

    # 1. IP qui porte les injections SUBSTRING
    inj_by_ip = Counter(ip for ip, path, _ in entries if PAYLOAD.search(path))
    attacker = inj_by_ip.most_common(1)[0][0]
    print("attaquant:", attacker)

    # 2-3. taille majoritaire = reponses "normales" ; on identifie TRUE/FALSE
    sizes = Counter(sz for ip, path, sz in entries
                    if ip == attacker and PAYLOAD.search(path))
    (sz_a, _), (sz_b, _) = sizes.most_common(2)
    size_true = max(sz_a, sz_b)   # TRUE = page complete (plus grande)

    max_true = defaultdict(lambda: 31)
    for ip, path, sz in entries:
        if ip != attacker:
            continue
        m = PAYLOAD.search(path)
        if not m:
            continue
        n, x = int(m.group(1)), int(m.group(2))
        if sz == size_true and x > max_true[n]:
            max_true[n] = x

    flag = "".join(chr(max_true[n] + 1) for n in sorted(max_true))
    print(flag)


if __name__ == "__main__":
    main()
