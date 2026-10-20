#!/usr/bin/env python3
"""Solveur memoire-vive - dump memoire reel + Volatility 3.

Chaine :
  1. Volatility 3 (linux.pslist) -> reperer le processus fileless 'stage2'
     (il apparait comme 'memfd:stage2', PPID 1) et noter son PID.
  2. Localiser dans le dump l'artefact 'MEMKEY01' laisse par la charge utile :
     { magic[8], mkey[32] = KEY XOR sha256(ascii(pid)), nonce[8] }.
     On garde le blob VIVANT (mkey non nulle ; les copies dans l'ELF sur disque
     ont une mkey a zero).
  3. Demasquer : KEY = mkey XOR sha256(ascii(pid)).
  4. Dechiffrer x.enc (recupere dans le defi serveur-compromis) -> flag.

Usage :
  solve.py --dump memoire.raw[.xz] --xenc x.enc --symbols defi/symbols [--pid N]
"""
import argparse
import gzip
import hashlib
import lzma
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MAGIC = b"MEMKEY01"


def load_dump(path):
    if path.endswith(".xz"):
        return lzma.open(path, "rb").read()
    with open(path, "rb") as f:
        return f.read()


def find_live_keyblob(data):
    """Retourne (mkey, nonce) du blob dont la mkey est non nulle (process vivant)."""
    i, found = 0, None
    while True:
        i = data.find(MAGIC, i)
        if i < 0:
            break
        mkey, nonce = data[i + 8:i + 40], data[i + 40:i + 48]
        if any(mkey):
            found = (mkey, nonce)
        i += 8
    if not found:
        raise SystemExit("aucun blob MEMKEY01 vivant trouve")
    return found


def recover(mkey, pid):
    """KEY = mkey XOR sha256(ascii(pid))."""
    return bytes(a ^ b for a, b in
                 zip(mkey, hashlib.sha256(str(pid).encode()).digest()))


def pid_via_volatility(dump_path, symbols):
    cmd = ["vol", "-q", "-f", dump_path, "-s", symbols, "linux.pslist.PsList"]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=600).stdout
    for line in out.splitlines():
        if "stage2" in line:
            return int(line.split()[1])
    raise SystemExit("process 'stage2' absent de linux.pslist")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", default=os.path.join(HERE, "..", "defi", "memoire.raw.xz"))
    ap.add_argument("--xenc", required=True, help="x.enc extrait de serveur.img (serveur-compromis)")
    ap.add_argument("--symbols", default=os.path.join(HERE, "..", "defi", "symbols"))
    ap.add_argument("--pid", type=int)
    a = ap.parse_args()

    data = load_dump(a.dump)
    mkey, nonce = find_live_keyblob(data)
    print("mkey (masquee):", mkey.hex())
    print("nonce         :", nonce.hex())

    # Volatility veut un dump non compresse : on le materialise si besoin.
    pid = a.pid
    if pid is None:
        raw = a.dump
        if a.dump.endswith(".xz"):
            raw = os.path.join(HERE, "_memoire.raw")
            if not os.path.exists(raw):
                open(raw, "wb").write(data)
        pid = pid_via_volatility(raw, a.symbols)
    print("PID stage2    :", pid)

    key = recover(mkey, pid)
    print("KEY demasquee :", key.hex())

    from Crypto.Cipher import AES
    pt = AES.new(key, AES.MODE_CTR, nonce=nonce).decrypt(open(a.xenc, "rb").read())
    try:
        pt = gzip.decompress(pt)
    except OSError:
        pass
    m = re.search(rb"FPS\{[^}]+\}", pt)
    print(m.group(0).decode() if m else "echec:\n" + pt.decode("utf-8", "replace"))


if __name__ == "__main__":
    main()
