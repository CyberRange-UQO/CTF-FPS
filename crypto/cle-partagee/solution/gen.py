#!/usr/bin/env python3
"""Genere les fichiers du defi cle-partagee (reutilisation de keystream).

Le meme "chiffreur maison" XOR a chiffre deux fichiers avec LA MEME cle :
- brochure.pdf : document public (dispo en clair sur le site de l'entreprise)
- memo confidentiel (contient le flag)

On fournit : brochure.pdf (clair), brochure.pdf.enc, memo.enc.
"""
import os
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
DEFI = os.path.normpath(os.path.join(HERE, "..", "defi"))

FLAG = "FPS{reutiliser_un_keystream_xor_est_un_two_time_pad}"


def make_pdf(paragraphs) -> bytes:
    """Construit un PDF 1 page valide avec du texte (flux compresse)."""
    lines = ["BT", "/F1 14 Tf", "72 760 Td", "16 TL"]
    for p in paragraphs:
        safe = p.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
        lines.append(f"({safe}) Tj")
        lines.append("T*")
    lines.append("ET")
    stream = zlib.compress(("\n".join(lines)).encode("latin-1"))

    objs = []
    objs.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objs.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    objs.append(
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"
    )
    objs.append(
        b"<< /Length " + str(len(stream)).encode() + b" /Filter /FlateDecode >>\n"
        b"stream\n" + stream + b"\nendstream"
    )
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    out = bytearray(b"%PDF-1.5\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs)+1}\n".encode()
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objs)+1} /Root 1 0 R >>\n".encode()
        + b"startxref\n" + str(xref).encode() + b"\n%%EOF\n"
    )
    return bytes(out)


def main():
    brochure = make_pdf([
        "CORP - Brochure institutionnelle 2026",
        "",
        "Corp accompagne les PME dans leur transformation numerique.",
        "Nos equipes interviennent sur l'infrastructure, la securite et",
        "le developpement d'applications metier sur mesure.",
        "",
        "Contact : contact@corp.local  -  www.corp.local",
        "Document public - diffusion libre.",
    ])

    memo = (
        "MEMO INTERNE - CONFIDENTIEL\n"
        "De : Direction des systemes d'information\n"
        "Objet : rotation des cles de sauvegarde\n\n"
        "Le chiffreur maison a ete utilise par erreur avec la meme cle pour\n"
        "la brochure publique ET ce memo. A corriger immediatement.\n\n"
        "Jeton de validation : " + FLAG + "\n"
    ).encode()

    assert len(memo) <= len(brochure), "le memo doit tenir dans le keystream recuperable"

    # Un seul keystream, reutilise pour les deux fichiers (le bug).
    ks = os.urandom(len(brochure))
    enc_bro = bytes(a ^ b for a, b in zip(brochure, ks))
    enc_memo = bytes(a ^ b for a, b in zip(memo, ks))

    with open(os.path.join(DEFI, "brochure.pdf"), "wb") as f:
        f.write(brochure)
    with open(os.path.join(DEFI, "brochure.pdf.enc"), "wb") as f:
        f.write(enc_bro)
    with open(os.path.join(DEFI, "memo.enc"), "wb") as f:
        f.write(enc_memo)
    print("brochure:", len(brochure), "memo:", len(memo))


if __name__ == "__main__":
    main()
