#!/usr/bin/env python3
# Script de sauvegarde interne - service de facturation
# (retrouve sur le serveur ; c'est lui qui a produit sauvegarde.tar.gz.enc)
import random
import tarfile
import time


def chiffrer(data: bytes) -> bytes:
    # On chiffre l'archive avant de l'ecrire sur le partage reseau.
    graine = int(time.time())
    random.seed(graine)
    flux = bytes(random.getrandbits(8) for _ in range(len(data)))
    return bytes(a ^ b for a, b in zip(data, flux))


def main():
    with tarfile.open("sauvegarde.tar.gz", "w:gz") as tar:
        tar.add("/etc/app")
    with open("sauvegarde.tar.gz", "rb") as f:
        clair = f.read()
    with open("sauvegarde.tar.gz.enc", "wb") as f:
        f.write(chiffrer(clair))


if __name__ == "__main__":
    main()
