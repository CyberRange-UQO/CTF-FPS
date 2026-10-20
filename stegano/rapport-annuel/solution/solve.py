#!/usr/bin/env python3
"""Solveur rapport-annuel.

1. rapport-annuel.pdf est aussi un ZIP -> on l'extrait.
2. On lit le mot de passe dans le spectrogramme du WAV (ici OCR du spectrogramme
   calcule par STFT ; en CTF : Audacity/Sonic Visualiser/sox -n spectrogram).
3. steghide extract avec ce mot de passe sur photo-equipe.jpg -> flag.
"""
import os
import re
import subprocess
import sys
import wave
import zipfile

import numpy as np
from PIL import Image, ImageFilter
import pytesseract

HERE = os.path.dirname(os.path.abspath(__file__))
DEFI = os.path.normpath(os.path.join(HERE, "..", "defi"))
WORK = os.path.join(HERE, "_solve")


def spectrogram_password(wav_path):
    with wave.open(wav_path, "rb") as w:
        sr = w.getframerate()
        pcm = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(float)
    nfft, hop = 1024, 256
    cols = []
    for i in range(0, len(pcm) - nfft, hop):
        seg = pcm[i:i + nfft] * np.hanning(nfft)
        cols.append(np.abs(np.fft.rfft(seg)))
    spec = np.array(cols).T  # (freq, time)
    spec = np.log1p(spec)
    # Bande utile 700-4600 Hz, affichee freq haute en haut.
    f = np.fft.rfftfreq(nfft, 1 / sr)
    mask = (f >= 600) & (f <= 4800)
    img = spec[mask][::-1]
    img = (img - img.min()) / (np.ptp(img) + 1e-9)
    im = Image.fromarray((img * 255).astype(np.uint8)).resize((760, 240))
    im = im.filter(ImageFilter.GaussianBlur(1.5))
    # Normalisation par colonne -> supprime le banding vertical qui gene l'OCR.
    a = np.asarray(im, float)
    a = a - a.mean(axis=0, keepdims=True)
    a = np.clip((a - a.min()) / (np.ptp(a) + 1e-9) * 255, 0, 255).astype(np.uint8)
    im = Image.fromarray(a).point(lambda p: 255 if p > 150 else 0)
    im = im.filter(ImageFilter.MaxFilter(3))
    text = pytesseract.image_to_string(
        im, config="--psm 7 -c tessedit_char_whitelist="
                   "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
    return text.strip().replace(" ", "")


def main():
    pdf = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        DEFI, "rapport-annuel.pdf")
    os.makedirs(WORK, exist_ok=True)

    with zipfile.ZipFile(pdf) as z:   # le PDF est aussi un ZIP
        z.extractall(WORK)
    print("contenu archive:", os.listdir(WORK))

    wav = os.path.join(WORK, "audio-corporate.wav")
    pwd = spectrogram_password(wav)
    print("mot de passe lu au spectrogramme:", pwd)

    jpg = os.path.join(WORK, "photo-equipe.jpg")
    res = subprocess.run(
        ["steghide", "extract", "-sf", jpg, "-p", pwd, "-xf",
         os.path.join(WORK, "out.txt"), "-f", "-q"],
        capture_output=True, text=True)
    if res.returncode != 0:
        raise SystemExit("steghide a echoue: " + res.stderr)
    data = open(os.path.join(WORK, "out.txt")).read()
    print(re.search(r"FPS\{[^}]+\}", data).group(0))


if __name__ == "__main__":
    main()
