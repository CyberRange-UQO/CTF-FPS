#!/usr/bin/env python3
"""Genere le defi rapport-annuel (chaine stegano a 3 etages).

1. rapport-annuel.pdf : fichier POLYGLOTTE PDF + ZIP (s'ouvre comme un PDF,
   se decompresse comme une archive).
2. L'archive contient audio-corporate.wav : son spectrogramme affiche un
   mot de passe.
3. Ce mot de passe ouvre les donnees cachees par steghide dans photo-equipe.jpg
   -> flag.
"""
import os
import subprocess
import wave
import zlib

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
DEFI = os.path.normpath(os.path.join(HERE, "..", "defi"))
WORK = os.path.join(HERE, "_work")

FLAG = "FPS{pdf_zip_polyglotte_spectrogramme_puis_steghide}"
PASSWORD = "AUDIT2026"

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONTB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


# ---------- 1. PDF (rapport annuel) ----------
def make_pdf(paragraphs) -> bytes:
    lines = ["BT", "/F1 13 Tf", "72 770 Td", "16 TL"]
    for p in paragraphs:
        safe = p.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
        lines += [f"({safe}) Tj", "T*"]
    lines.append("ET")
    stream = zlib.compress("\n".join(lines).encode("latin-1"))
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(stream)).encode() + b" /Filter /FlateDecode >>\n"
        b"stream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.5\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for i, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs)+1}\n".encode() + b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += (f"trailer\n<< /Size {len(objs)+1} /Root 1 0 R >>\n".encode()
            + b"startxref\n" + str(xref).encode() + b"\n%%EOF\n")
    return bytes(out)


# ---------- 2. WAV spectrographique ----------
def make_spectro_wav(text, path, sr=16000, dur=4.0):
    H, W = 140, 620
    img = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONTB, 90)
    bb = d.textbbox((0, 0), text, font=font)
    d.text(((W - (bb[2] - bb[0])) // 2, (H - (bb[3] - bb[1])) // 2 - bb[1]),
           text, fill=255, font=font)
    arr = np.asarray(img, dtype=float) / 255.0  # (H, W), ligne 0 = haut

    N = int(sr * dur)
    t = np.arange(N) / sr
    signal = np.zeros(N)
    fmin, fmax = 700.0, 4600.0
    for r in range(H):
        row = arr[r]
        if row.max() < 0.05:
            continue
        f = fmax - (r / (H - 1)) * (fmax - fmin)  # ligne 0 -> freq haute
        env = np.interp(t, np.linspace(0, dur, W), row)
        signal += env * np.sin(2 * np.pi * f * t)

    signal /= max(signal.max(), 1e-9)
    pcm = (signal * 0.8 * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


# ---------- 3. Porteur JPEG + steghide ----------
def make_cover_jpg(path):
    rng = np.random.default_rng(42)
    base = rng.integers(60, 180, size=(500, 700, 3), dtype=np.uint8)
    img = Image.fromarray(base).convert("RGB")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 700, 60], fill=(31, 73, 125))
    d.text((20, 16), "Corp - Photo d'equipe 2026", fill="white",
           font=ImageFont.truetype(FONTB, 26))
    img.save(path, "JPEG", quality=90)


def main():
    os.makedirs(WORK, exist_ok=True)
    os.makedirs(DEFI, exist_ok=True)

    pdf = make_pdf([
        "CORP - Rapport annuel 2026",
        "",
        "Ce document presente la synthese des activites et des resultats",
        "financiers de l'exercice 2026, ainsi que les perspectives 2027.",
        "",
        "1. Faits marquants",
        "   - Croissance du chiffre d'affaires de 12 %.",
        "   - Ouverture d'un nouveau bureau a Gatineau.",
        "",
        "2. Resultats financiers",
        "   Les etats financiers detailles figurent en annexe.",
        "",
        "Document destine aux actionnaires - diffusion controlee.",
    ])
    pdf_path = os.path.join(WORK, "rapport.pdf")
    open(pdf_path, "wb").write(pdf)

    # Audio spectrographique (mot de passe) + porteur stego dans l'archive.
    wav_path = os.path.join(WORK, "audio-corporate.wav")
    make_spectro_wav(PASSWORD, wav_path)

    jpg_path = os.path.join(WORK, "photo-equipe.jpg")
    make_cover_jpg(jpg_path)
    flag_path = os.path.join(WORK, "flag.txt")
    open(flag_path, "w").write(FLAG + "\n")

    stego_jpg = os.path.join(WORK, "photo-equipe-stego.jpg")
    subprocess.run(
        ["steghide", "embed", "-cf", jpg_path, "-ef", flag_path,
         "-p", PASSWORD, "-sf", stego_jpg, "-q"], check=True)

    # Archive ZIP (audio + porteur stego + petite note).
    note = os.path.join(WORK, "LISEZMOI.txt")
    open(note, "w").write(
        "Archive annexe du rapport.\n"
        "- audio-corporate.wav : jingle institutionnel\n"
        "- photo-equipe.jpg : photo de l'equipe\n")
    zip_path = os.path.join(WORK, "annexe.zip")
    if os.path.exists(zip_path):
        os.remove(zip_path)
    # noms "propres" dans l'archive
    import shutil
    shutil.copy(stego_jpg, os.path.join(WORK, "photo-equipe.jpg"))
    subprocess.run(["zip", "-j", "-q", zip_path, wav_path,
                    os.path.join(WORK, "photo-equipe.jpg"), note], check=True)

    # Polyglotte : PDF puis ZIP, offsets ajustes par `zip -A`.
    out = os.path.join(DEFI, "rapport-annuel.pdf")
    with open(out, "wb") as f:
        f.write(open(pdf_path, "rb").read())
        f.write(open(zip_path, "rb").read())
    subprocess.run(["zip", "-A", "-q", out], check=True)
    print("genere:", out)
    print("mot de passe (spectrogramme):", PASSWORD)


if __name__ == "__main__":
    main()
