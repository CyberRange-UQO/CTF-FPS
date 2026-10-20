#!/usr/bin/env python3
"""Solveur jeton-api (bit-flipping AES-CTR a nonce fixe).

1. On demande un jeton pour un nom connu -> on connait le clair exact :
   {"user": "<nom>", "role": "guest"}
2. Le mode CTR est malleable : ct'[i] = ct[i] XOR clair[i] XOR cible[i].
   On transforme "guest" (5 car.) en "admin" (5 car.) aux bons offsets.
3. On rejoue le jeton forge sur /admin -> flag.
"""
import base64
import json
import sys
import urllib.parse
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:1340"
USER = "invite"


def get(path, **params):
    url = BASE + path + "?" + urllib.parse.urlencode(params)
    return json.loads(urllib.request.urlopen(url).read())


def main():
    tok = get("/token", user=USER)["token"]
    ct = bytearray(base64.urlsafe_b64decode(tok))

    plain = json.dumps({"user": USER, "role": "guest"}).encode()
    i = plain.index(b"guest")
    for k, (a, b) in enumerate(zip(b"guest", b"admin")):
        ct[i + k] ^= a ^ b  # flip guest -> admin

    forged = base64.urlsafe_b64encode(bytes(ct)).decode()
    res = get("/admin", token=forged)
    print(res)
    assert "flag" in res, "echec du forgeage"
    print(res["flag"])


if __name__ == "__main__":
    main()
