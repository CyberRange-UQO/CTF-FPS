"""Authentification correcte ; IDOR volontaire uniquement sur les dossiers."""

import hmac
import os
import re
import secrets
from datetime import timedelta
from functools import wraps
from io import BytesIO
from pathlib import Path

import yaml
from flask import (
    Flask,
    abort,
    g,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from werkzeug.security import check_password_hash

from .data import NOTIFICATIONS, RECORDS, USERS
from .report import build_archive


def create_app():
    app = Flask(__name__)
    secret = os.environ.get("SESSION_SECRET", "")
    if len(secret) < 32:
        raise RuntimeError("SESSION_SECRET doit contenir au moins 32 caractères aléatoires.")
    secure_cookie = os.environ.get("SESSION_COOKIE_SECURE", "true").lower()
    if secure_cookie not in {"true", "false"}:
        raise RuntimeError("SESSION_COOKIE_SECURE doit valoir true ou false.")
    app.config.update(
        SECRET_KEY=secret,
        DEBUG=False,
        SESSION_COOKIE_NAME="eidolon_session",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=secure_cookie == "true",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=1),
        SESSION_REFRESH_EACH_REQUEST=False,
        MAX_CONTENT_LENGTH=8192,
        MAX_FORM_MEMORY_SIZE=8192,
        MAX_FORM_PARTS=8,
    )

    # Source unique : ce YAML privé est aussi importé par CTFd.
    challenge_path = Path(__file__).resolve().parent.parent / "challenge.yml"
    challenge = yaml.safe_load(challenge_path.read_text(encoding="utf-8"))
    flags = challenge.get("flags", [])
    if (
        len(flags) != 1
        or not isinstance(flags[0], str)
        or not re.fullmatch(r"FPS\{[a-zA-Z0-9_]{1,48}\}", flags[0])
    ):
        raise RuntimeError("challenge.yml doit déclarer exactement un flag FPS valide.")
    app.extensions["confidential_archive"] = build_archive(flags[0], RECORDS[1057]["birth_date"])

    def csrf_token():
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_urlsafe(32)
        return session["csrf_token"]

    app.jinja_env.globals["csrf_token"] = csrf_token

    @app.before_request
    def load_current_user():
        user_id = session.get("user_id")
        g.user = USERS.get(user_id) if type(user_id) is int else None

    def login_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if g.user is None:
                return redirect(url_for("login"))
            return view(*args, **kwargs)

        return wrapped

    def validate_csrf():
        expected = session.get("csrf_token", "")
        supplied = request.form.get("csrf_token", "")
        if not expected or not hmac.compare_digest(expected, supplied):
            abort(400)

    @app.after_request
    def security_headers(response):
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; style-src 'self'; img-src 'self'; "
            "form-action 'self'; base-uri 'none'; frame-ancestors 'none'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        if app.config["SESSION_COOKIE_SECURE"]:
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "GET":
            if g.user:
                return redirect(url_for("dashboard"))
            return render_template("login.html", error=None)
        validate_csrf()
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        # Vérification identique pour un utilisateur absent : pas de fuite d'existence.
        candidate = USERS[1]
        password_valid = check_password_hash(candidate["password_hash"], password)
        if username != candidate["username"] or not password_valid:
            return render_template("login.html", error="Identifiants invalides."), 401
        session.clear()
        session["user_id"] = candidate["id"]
        session.permanent = True
        csrf_token()
        return redirect(url_for("dashboard"), code=303)

    @app.post("/logout")
    @login_required
    def logout():
        validate_csrf()
        session.clear()
        return redirect(url_for("login"), code=303)

    @app.get("/dashboard")
    @login_required
    def dashboard():
        return render_template("dashboard.html")

    @app.get("/notifications")
    @login_required
    def notifications():
        messages = [n for n in NOTIFICATIONS if n["recipient_user_id"] == g.user["id"]]
        return render_template("notifications.html", notifications=messages)

    def requested_record(record_id):
        record = RECORDS.get(record_id)
        if record is None:
            abort(404)
        # IDOR INTENTIONNELLE : aucune comparaison owner_user_id / g.user["id"].
        # Réutilisé uniquement par les routes de consultation et d'export ci-dessous.
        return record

    @app.get("/records/<int:record_id>")
    @login_required
    def record(record_id):
        return render_template("record.html", record=requested_record(record_id))

    @app.get("/records/<int:record_id>/export")
    @login_required
    def export(record_id):
        record = requested_record(record_id)
        if not record["has_report"]:
            abort(404)
        # Octets privés en mémoire : aucun chemin de fichier fourni par le joueur.
        return send_file(
            BytesIO(app.extensions["confidential_archive"]),
            mimetype="application/zip",
            as_attachment=True,
            download_name="SILENCE_MIRA-07.zip",
            conditional=False,
            etag=False,
        )

    @app.errorhandler(400)
    @app.errorhandler(404)
    @app.errorhandler(405)
    @app.errorhandler(413)
    def public_error(error):
        return render_template("error.html", code=error.code), error.code

    return app
