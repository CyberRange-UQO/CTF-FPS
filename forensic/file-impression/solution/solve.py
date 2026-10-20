#!/usr/bin/env python3
"""Solveur file-impression.

1. Reassembler les flux TCP vers le port 9100 (impression RAW).
2. Decouper par banniere PJL, reperer le job "CONFIDENTIEL".
3. Rendre le PostScript avec Ghostscript -> le flag apparait (emis via des
   codes ASCII, donc invisible a un grep du flux).
"""
import os
import re
import subprocess
import sys
import tempfile
from collections import defaultdict

from scapy.all import rdpcap, TCP, IP, Raw
from PIL import Image
import pytesseract

HERE = os.path.dirname(os.path.abspath(__file__))
DEFI = os.path.normpath(os.path.join(HERE, "..", "defi"))


def reassemble(pcap):
    streams = defaultdict(dict)  # key -> {seq: data}
    for p in rdpcap(pcap):
        if TCP not in p or p[TCP].dport != 9100 or Raw not in p:
            continue
        key = (p[IP].src, p[TCP].sport)
        streams[key][p[TCP].seq] = bytes(p[Raw].load)
    out = {}
    for key, segs in streams.items():
        out[key] = b"".join(segs[s] for s in sorted(segs))
    return out


def main():
    pcap = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        DEFI, "capture-impression.pcap")
    streams = reassemble(pcap)

    for key, data in streams.items():
        name = re.search(rb'@PJL JOB NAME="([^"]*)"', data)
        label = name.group(1).decode() if name else "?"
        print(f"flux {key[0]}:{key[1]} -> job {label!r} ({len(data)} o)")
        if b"CONFIDENTIEL" not in (name.group(1) if name else b""):
            continue

        # extraire le PostScript (entre ENTER LANGUAGE=POSTSCRIPT et l'UEL final)
        ps = data.split(b"LANGUAGE=POSTSCRIPT\r\n", 1)[1]
        ps = ps.split(b"\x1b%-12345X")[0]

        with tempfile.TemporaryDirectory() as d:
            psf = os.path.join(d, "job.ps")
            png = os.path.join(d, "job.png")
            open(psf, "wb").write(ps)
            subprocess.run(["gs", "-q", "-dNOPAUSE", "-dBATCH", "-r150",
                            "-sDEVICE=png16m", f"-sOutputFile={png}", psf],
                           check=True, capture_output=True)
            txt = pytesseract.image_to_string(Image.open(png))
            m = re.search(r"FPS\{[^}]+\}", txt.replace(" ", ""))
            print("  rendu ->", m.group(0) if m else "(OCR: " + txt.strip() + ")")


if __name__ == "__main__":
    main()
