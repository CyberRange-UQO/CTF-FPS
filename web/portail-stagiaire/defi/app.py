#!/usr/bin/env python3
"""Portail stagiaire RH - intranet (volontairement vulnerable).

Fuite classique : un repertoire de sauvegarde laisse accessible, decouvrable
via robots.txt + un commentaire HTML, avec un listing de repertoire ouvert.
Le .bak de config contient le flag.
"""
import os

from flask import Flask, Response, abort, send_from_directory

app = Flask(__name__)
BACKUP = os.path.join(os.path.dirname(__file__), "backup")

HOME = """<!doctype html>
<html lang="fr">
<head><meta charset="utf-8"><title>Corp RH - Portail stagiaire</title></head>
<body>
  <h1>Portail stagiaire - Ressources Humaines</h1>
  <p>Bienvenue sur l'intranet RH de Corp. Connectez-vous avec vos identifiants
     fournis par votre tuteur.</p>
  <ul>
    <li><a href="/">Accueil</a></li>
    <li><a href="/offres">Offres de stage</a></li>
    <li><a href="/contact">Contact RH</a></li>
  </ul>
  <!-- TODO: retirer l'ancien dossier /backup/ avant la mise en prod (cf. robots.txt) -->
</body></html>"""


@app.route("/")
def index():
    return HOME


@app.route("/robots.txt")
def robots():
    return Response(
        "User-agent: *\nDisallow: /backup/\nDisallow: /admin/\n",
        mimetype="text/plain",
    )


@app.route("/offres")
def offres():
    return "<h1>Offres de stage</h1><p>Aucune offre pour le moment.</p>"


@app.route("/contact")
def contact():
    return "<h1>Contact RH</h1><p>rh@corp.local</p>"


@app.route("/backup/")
def backup_index():
    files = sorted(os.listdir(BACKUP))
    rows = "\n".join(f'<li><a href="/backup/{f}">{f}</a></li>' for f in files)
    return f"<h1>Index of /backup/</h1><ul>{rows}</ul>"


@app.route("/backup/<path:name>")
def backup_file(name):
    if "/" in name or name.startswith("."):
        abort(404)
    return send_from_directory(BACKUP, name, mimetype="text/plain")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
