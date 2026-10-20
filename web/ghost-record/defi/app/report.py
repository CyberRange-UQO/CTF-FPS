"""Rapport privé en mémoire, puis enveloppe ZIP AES compatible 7-Zip."""

from io import BytesIO

import pyzipper
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def build_report(flag: str) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4, pageCompression=1, invariant=1)
    # invariant=1 utilise sinon l'an 2000. Date narrative fixe au format PDF (UTC),
    # appliquée par ReportLab à CreationDate et ModDate sans changer le rendu.
    pdf.setDateFormatter(lambda *_: "D:21471016084000Z")
    pdf.setTitle("Operation SILENCE - MIRA-07")
    pdf.setAuthor("VANTA Systems - Direction des Identités")
    pdf.setSubject("EID-1057 - Rapport interne classifié")
    pdf.setCreator("EIDOLON Legacy v2.1")
    width, height = A4
    navy, cyan, magenta = map(HexColor, ("#090F1B", "#42E8D6", "#FF4C91"))

    pdf.setFillColor(navy)
    pdf.rect(0, height - 142, width, 142, fill=1, stroke=0)
    pdf.setFillColor(cyan)
    pdf.setFont("Helvetica-Bold", 23)
    pdf.drawString(42, height - 55, "VANTA // SYSTEMS")
    pdf.setFillColor(HexColor("#E9F6FF"))
    pdf.setFont("Helvetica", 10)
    pdf.drawString(43, height - 79, "DIRECTION DES IDENTITÉS  /  NOCTIS-9")
    pdf.setFillColor(magenta)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(43, height - 113, "ARCHIVE INTERNE  //  CLASSIFICATION : RESTRICTED")

    def text(x, y, value, size=11, bold=False, color=navy):
        pdf.setFillColor(color)
        pdf.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        pdf.drawString(x, y, value)

    text(43, 667, "OPÉRATION SILENCE", 19, True)
    text(43, 640, "DOCUMENT : EID-1057   /   SUJET : MIRA-07", 10, True)
    text(43, 616, "Directive : SIL-4/2147-07    ·    Exécution : 16/10/2147, 08:40", 10)
    pdf.setStrokeColor(HexColor("#CCD7E1"))
    pdf.line(43, 594, width - 43, 594)
    text(43, 565, "DÉCISION : EFFACEMENT D'IDENTITÉ — APPROUVÉ", 12, True)
    text(43, 536, "Titulaire : MIRA-07   /   Registre citoyen : 1057")
    text(43, 512, "Statut final : ERASED   /   Retrait du registre public exécuté")
    text(43, 488, "Motif :")
    pdf.setFillColor(navy)
    pdf.rect(89, 486, 228, 13, fill=1, stroke=0)
    text(43, 461, "Autorité signataire :")
    pdf.setFillColor(navy)
    pdf.rect(145, 459, 167, 13, fill=1, stroke=0)

    text(43, 412, "NOTE DE CONTRÔLE INTERNE", 10, True)
    lines = (
        "L'effacement administratif du dossier 1057 est volontaire. Il résulte",
        "d'une directive explicite de la Direction des identités et ne constitue",
        "pas une erreur de synchronisation. L'identité de MIRA-07 a été",
        "retirée du registre public sur ordre, avec maintien de cette preuve.",
        "",
        "La communication « maintenance SILENCE-4 » diffusée sur EIDOLON",
        "sert de couverture à cette opération. Toute demande citoyenne doit",
        "être classée comme anomalie de synchronisation, sans divulgation",
        "de la directive. Aucune restauration du dossier n'est autorisée.",
    )
    for index, line in enumerate(lines):
        text(43, 388 - index * 19, line, 11)

    pdf.setFillColor(HexColor("#EDF4F8"))
    pdf.rect(43, 137, width - 86, 65, fill=1, stroke=0)
    text(57, 180, "IDENTIFIANT DE PREUVE", 9, True)
    text(57, 154, flag, 12, True)
    pdf.setStrokeColor(magenta)
    pdf.line(43, 137, width - 43, 137)
    text(43, 99, "Diffusion restreinte. Copie d'archive — EIDOLON Legacy v2.1.", 9)
    text(43, 60, "VANTA Systems — Votre identité. Notre propriété.", 8)
    text(width - 76, 60, "01 / 01", 8)
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def build_archive(flag: str, birth_date) -> bytes:
    buffer = BytesIO()
    with pyzipper.AESZipFile(
        buffer, "w", compression=pyzipper.ZIP_DEFLATED, encryption=pyzipper.WZ_AES
    ) as archive:
        archive.setpassword(birth_date.strftime("%Y%m%d").encode("ascii"))
        archive.setencryption(pyzipper.WZ_AES, nbits=256)
        archive.writestr("SILENCE_MIRA-07.pdf", build_report(flag))
    return buffer.getvalue()
