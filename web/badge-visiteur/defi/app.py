#!/usr/bin/env python3
"""Portail d'accueil visiteurs (volontairement vulnerable).

Le "badge" du visiteur est stocke cote client dans un cookie base64, et le
serveur fait confiance au role qu'il contient sans aucune verification de
signature. Il suffit de passer role=admin.
"""
import base64
import json
import os

from flask import Flask, request, make_response, jsonify

app = Flask(__name__)
FLAG = os.environ.get("FLAG", "FPS{un_cookie_de_role_non_signe_cote_client}")


def badge(role, name):
    raw = json.dumps({"name": name, "role": role}).encode()
    return base64.b64encode(raw).decode()


def read_badge(cookie):
    return json.loads(base64.b64decode(cookie.encode()))


@app.route("/")
def index():
    resp = make_response(
        "<h1>Accueil visiteurs - Corp</h1>"
        "<p>Un badge visiteur vous a ete attribue.</p>"
        '<p><a href="/badge">Voir mon badge</a> &middot; '
        '<a href="/admin">Espace administration</a></p>'
    )
    if not request.cookies.get("badge"):
        resp.set_cookie("badge", badge("visiteur", "Invite"))
    return resp


@app.route("/badge")
def show_badge():
    cookie = request.cookies.get("badge")
    if not cookie:
        return "Aucun badge.", 400
    try:
        data = read_badge(cookie)
    except Exception:
        return "Badge illisible.", 400
    return jsonify(data)


@app.route("/admin")
def admin():
    cookie = request.cookies.get("badge", "")
    try:
        data = read_badge(cookie)
    except Exception:
        return "Badge illisible.", 400
    if data.get("role") == "admin":
        return jsonify(message="Acces administration accorde.", flag=FLAG)
    return jsonify(error="Reserve aux administrateurs.", role=data.get("role")), 403


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
