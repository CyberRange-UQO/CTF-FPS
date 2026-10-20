#!/usr/bin/env python3
"""Genere le defi rsa-archives.

Un vieux serveur d'archives a genere ses paires RSA avec un PRNG mal initialise :
deux cles publiques partagent un facteur premier. Un PGCD entre modules casse
les deux cles.

Fournis : pubkeys/*.pem (6 cles publiques) + messages/*.bin (messages chiffres
OAEP, dont le flag chiffre vers la cle vulnerable).
"""
import os

from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Util.number import getPrime

HERE = os.path.dirname(os.path.abspath(__file__))
DEFI = os.path.normpath(os.path.join(HERE, "..", "defi"))
PUB = os.path.join(DEFI, "pubkeys")
MSG = os.path.join(DEFI, "messages")

FLAG = b"FPS{deux_modules_rsa_un_facteur_commun_pgcd}"
BITS = 1024  # 1024 bits/premier -> module 2048 bits
E = 65537


def save_pub(key, name):
    with open(os.path.join(PUB, name), "wb") as f:
        f.write(key.publickey().export_key("PEM"))


def encrypt(key, data, name):
    ct = PKCS1_OAEP.new(key.publickey()).encrypt(data)
    with open(os.path.join(MSG, name), "wb") as f:
        f.write(ct)


def main():
    os.makedirs(PUB, exist_ok=True)
    os.makedirs(MSG, exist_ok=True)

    # Le bug : p est reutilise entre la cle 02 et la cle 05.
    p_commun = getPrime(BITS)

    q02 = getPrime(BITS)
    q05 = getPrime(BITS)
    key02 = RSA.construct((p_commun * q02, E))  # pub seulement pour l'export
    key05 = RSA.construct((p_commun * q05, E))

    # Cles saines (decoys incassables).
    sains = [RSA.generate(2 * BITS, e=E) for _ in range(4)]

    # Ordre melange des cles publiques.
    layout = [
        ("archive-01.pem", sains[0]),
        ("archive-02.pem", key02),
        ("archive-03.pem", sains[1]),
        ("archive-04.pem", sains[2]),
        ("archive-05.pem", key05),
        ("archive-06.pem", sains[3]),
    ]
    for name, key in layout:
        save_pub(key, name)

    # Messages : le flag chiffre vers la cle vulnerable 02, + des leurres.
    encrypt(key02, FLAG, "message-02.bin")
    encrypt(sains[0], b"Rapport trimestriel - rien de sensible ici.", "message-01.bin")
    encrypt(sains[2], b"Compte-rendu reunion du 12 mars.", "message-04.bin")
    encrypt(key05, b"Note de service : mise a jour du parc.", "message-05.bin")

    print("genere. flag chiffre vers archive-02 (partage p avec archive-05).")


if __name__ == "__main__":
    main()
