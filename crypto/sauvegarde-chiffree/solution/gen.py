#!/usr/bin/env python3
"""Genere les fichiers du defi sauvegarde-chiffree.

Reproduit le comportement du script de backup interne (buggé) : l'archive est
chiffree par XOR avec un keystream issu de random.seed(int(time.time())).
La graine est l'horodatage, a la seconde pres -> brute-force sur la minute.
"""
import io
import os
import random
import tarfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DEFI = os.path.normpath(os.path.join(HERE, "..", "defi"))

FLAG = "FPS{sauvegarde_chiffree_avec_une_graine_temporelle}"

# Instant exact ou le backup a tourne (fige pour la reproductibilite).
# 2026-09-15 02:00:37 UTC.
BACKUP_TS = 1789524037


def build_archive() -> bytes:
    """Construit le .tar.gz de la config sauvegardee (contient le flag)."""
    files = {
        "etc/app/database.conf": (
            "[database]\n"
            "host = db.corp.local\n"
            "port = 5432\n"
            "name = facturation\n"
            "user = svc_backup\n"
            "password = N7!kqpaX2r$vz\n"
        ),
        "etc/app/smtp.conf": (
            "[smtp]\n"
            "host = smtp.corp.local\n"
            "port = 587\n"
            "user = no-reply@corp.local\n"
            "from = Facturation <no-reply@corp.local>\n"
        ),
        "etc/app/README.txt": (
            "Sauvegarde automatique de la configuration du service de facturation.\n"
            "Ne pas diffuser : contient des identifiants de service.\n"
            "Jeton de restauration : " + FLAG + "\n"
        ),
    }
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, content in files.items():
            data = content.encode()
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mtime = BACKUP_TS
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def keystream(seed: int, n: int) -> bytes:
    r = random.Random(seed)
    return bytes(r.getrandbits(8) for _ in range(n))


def xor(data: bytes, ks: bytes) -> bytes:
    return bytes(a ^ b for a, b in zip(data, ks))


def main():
    archive = build_archive()
    ks = keystream(BACKUP_TS, len(archive))
    enc = xor(archive, ks)

    with open(os.path.join(DEFI, "sauvegarde.tar.gz.enc"), "wb") as f:
        f.write(enc)

    # Log cron qui donne la minute (pas la seconde) ou le backup a tourne.
    minute = time.strftime("%Y-%m-%d %H:%M", time.gmtime(BACKUP_TS))
    with open(os.path.join(DEFI, "backup.log"), "w") as f:
        f.write(
            "# /var/log/corp/backup.log\n"
            f"{minute}:00 UTC  INFO  demarrage sauvegarde quotidienne\n"
            f"{minute}:00 UTC  INFO  archivage /etc/app -> /backup/sauvegarde.tar.gz\n"
            f"{minute}:00 UTC  INFO  chiffrement (seed=heure systeme)\n"
            f"{minute}:00 UTC  INFO  ecriture /backup/sauvegarde.tar.gz.enc (termine)\n"
        )
    print("genere:", len(enc), "octets chiffres, minute =", minute)


if __name__ == "__main__":
    main()
