#!/usr/bin/env python3
"""Generateur de factures (volontairement vulnerable - SSTI).

Le champ "note" du client est injecte dans un gabarit Jinja2 via
render_template_string, donc evalue cote serveur (SSTI). Un filtre naif
rejette les sous-chaines "__" et "." : il faut le contourner (|attr(...) et
echappements \\x5f).
"""
import os

from flask import Flask, request, render_template_string

app = Flask(__name__)
BLOCKLIST = ("__", ".")

FORM = """<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><title>Factures - Corp</title></head>
<body>
  <h1>Generateur de factures</h1>
  <form method="post" action="/facture">
    <p>Client : <input name="client" value="ACME Inc."></p>
    <p>Montant : <input name="montant" value="1250"></p>
    <p>Note (visible sur la facture) :<br>
       <textarea name="note" rows="3" cols="50">Merci de votre confiance.</textarea></p>
    <p><button type="submit">Generer</button></p>
  </form>
</body></html>"""

# La note est interpolee directement dans le gabarit -> SSTI.
TEMPLATE = """<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><title>Facture</title></head>
<body>
  <h1>FACTURE</h1>
  <p><b>Client :</b> {{ client }}</p>
  <p><b>Montant :</b> {{ montant }} CAD</p>
  <hr>
  <p><b>Note :</b> %s</p>
  <hr>
  <p><i>Corp - 123 rue de l'Innovation, Gatineau (QC)</i></p>
</body></html>"""


@app.route("/")
def index():
    return FORM


@app.route("/facture", methods=["POST"])
def facture():
    client = request.form.get("client", "")
    montant = request.form.get("montant", "")
    note = request.form.get("note", "")

    for bad in BLOCKLIST:
        if bad in note:
            return f"Caractere interdit dans la note : {bad!r}", 400

    html = TEMPLATE % note
    return render_template_string(html, client=client, montant=montant)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
