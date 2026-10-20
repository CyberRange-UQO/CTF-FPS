#!/usr/bin/env python3

import base64
import json
import os

from flask import Flask, request, jsonify
from Crypto.Cipher import AES

app = Flask(__name__)

KEY = os.urandom(16)
NONCE = b"\x00" * 8 
FLAG = os.environ.get("FLAG", "FPS{not_that_simple}")


def cipher():
    return AES.new(KEY, AES.MODE_CTR, nonce=NONCE)


def make_token(user: str) -> str:
    payload = json.dumps({"user": user, "role": "guest"}).encode()
    ct = cipher().encrypt(payload)
    return base64.urlsafe_b64encode(ct).decode()


def read_token(token: str) -> dict:
    ct = base64.urlsafe_b64decode(token.encode())
    return json.loads(cipher().decrypt(ct))


@app.route("/")
def index():
    return (
        "API de jetons interne\n\n"
        "  GET /token?user=<nom>   -> emet un jeton (role=guest)\n"
        "  GET /admin?token=<jeton> -> reservee au role=admin\n"
    )


@app.route("/token")
def token():
    user = request.args.get("user", "invite")
    return jsonify(user=user, role="guest", token=make_token(user))


@app.route("/admin")
def admin():
    tok = request.args.get("token", "")
    try:
        data = read_token(tok)
    except Exception:
        return jsonify(error="jeton invalide"), 400
    if data.get("role") == "admin":
        return jsonify(message="Bienvenue admin.", flag=FLAG)
    return jsonify(error="acces refuse", role=data.get("role")), 403


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
