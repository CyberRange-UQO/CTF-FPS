#!/usr/bin/env python3
"""Solveur cle-partagee.

Le keystream a ete reutilise : brochure.pdf (connu en clair) et le memo ont
ete XORes avec la meme cle. On recupere le keystream avec le document public,
puis on dechiffre le memo.

    ks = brochure_clair XOR brochure_enc
    memo = memo_enc XOR ks[:len(memo_enc)]
"""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
DEFI = os.path.normpath(os.path.join(HERE, "..", "defi"))


def read(name):
    with open(os.path.join(DEFI, name), "rb") as f:
        return f.read()


def main():
    clair = read("brochure.pdf")
    enc_bro = read("brochure.pdf.enc")
    enc_memo = read("memo.enc")

    ks = bytes(a ^ b for a, b in zip(clair, enc_bro))
    memo = bytes(a ^ b for a, b in zip(enc_memo, ks))

    text = memo.decode(errors="replace")
    print(text)
    print(re.search(r"FPS\{[^}]+\}", text).group(0))


if __name__ == "__main__":
    main()
