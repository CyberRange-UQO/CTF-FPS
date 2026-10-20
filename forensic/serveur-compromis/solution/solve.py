#!/usr/bin/env python3
"""Solveur serveur-compromis.

Aucun flag n'est stocke : on le reconstruit a partir de 3 artefacts.
  FPS{<compte_compromis>_<unite_persistance>_<port_C2>}
- compte : "Accepted password for X" dans auth.log (apres la rafale d'echecs)
- unite  : le timer/service systemd imposteur (apt-daily-cleanup)
- port C2: dans l'ExecStart du service (/dev/tcp/IP/PORT)

Bonus : istat montre le timestompage (crtime > mtime) du .so de ld.so.preload.
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFI = os.path.normpath(os.path.join(HERE, "..", "defi"))


def cat(img, path):
    return subprocess.run(["debugfs", "-R", f"cat {path}", img],
                          capture_output=True).stdout.decode("utf-8", "replace")


def ls_services(img):
    out = subprocess.run(["debugfs", "-R", "ls -l /etc/systemd/system", img],
                         capture_output=True).stdout.decode("utf-8", "replace")
    return re.findall(r"(\S+\.service)", out)


def main():
    img = sys.argv[1] if len(sys.argv) > 1 else os.path.join(DEFI, "serveur.img")

    # 1. compte compromis
    auth = cat(img, "/var/log/auth.log")
    account = re.search(r"Accepted password for (\S+)", auth).group(1)

    # 2. unite de persistance : service non standard avec reverse-shell
    unit, port = None, None
    for svc in ls_services(img):
        body = cat(img, "/etc/systemd/system/" + svc)
        m = re.search(r"/dev/tcp/[\d.]+/(\d+)", body)
        if m:
            unit = svc.rsplit(".", 1)[0]
            port = m.group(1)
    flag = f"FPS{{{account}_{unit}_{port}}}"

    print("compte compromis   :", account)
    print("unite persistance  :", unit)
    print("port C2            :", port)
    print("FLAG :", flag)

    # bonus : preuve de timestompage via crtime > mtime
    listing = subprocess.run(["fls", "-r", img], capture_output=True,
                             text=True).stdout
    m = re.search(r"r/r (\d+):\s+libncurse\.so", listing)
    if m:
        istat = subprocess.run(["istat", img, m.group(1)],
                               capture_output=True, text=True).stdout
        print("\n--- timestomp (ld.so.preload .so) ---")
        for line in istat.splitlines():
            if any(k in line for k in ("Created", "Modified", "Accessed")):
                print(line.strip())


if __name__ == "__main__":
    main()
