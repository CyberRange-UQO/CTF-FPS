"""Public Flask portal and bounded server-side HTTP preview API."""

import os
from datetime import timedelta

from flask import Flask, g, jsonify, redirect, render_template, request, session, url_for
from werkzeug.exceptions import HTTPException

from .auth import (
    SESSION_TTL,
    CsrfError,
    credentials_valid,
    csrf_token,
    load_operator,
    start_session,
    validate_csrf,
)
from .data import JOBS, SOURCES
from .source_guard import approve_declared_source
from .transport import LabTransport, PreviewError, parse_url


def create_app(test_config=None):
    app = Flask(__name__)
    secure_cookie = os.environ.get("SESSION_COOKIE_SECURE", "false").lower()
    if secure_cookie not in {"true", "false"}:
        raise RuntimeError("SESSION_COOKIE_SECURE must be true or false")
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SESSION_SECRET"),
        SESSION_COOKIE_NAME="mirror_session",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=secure_cookie == "true",
        PERMANENT_SESSION_LIFETIME=timedelta(seconds=SESSION_TTL),
        SESSION_REFRESH_EACH_REQUEST=False,
        MAX_CONTENT_LENGTH=4096,
        MAX_FORM_MEMORY_SIZE=4096,
    )
    if test_config:
        app.config.update(test_config)
    secret = app.config["SECRET_KEY"]
    if not isinstance(secret, str) or len(secret.encode("utf-8")) < 32:
        raise RuntimeError("SESSION_SECRET must contain at least 32 random bytes")
    app.json.ensure_ascii = False
    app.extensions["lab_transport"] = LabTransport(os.environ.get("MIRROR_LAB_PREFIX", "10.30.82"))
    app.jinja_env.globals["csrf_token"] = csrf_token

    @app.before_request
    def authenticate_request():
        load_operator()
        # Default-deny every application route, including future API additions.
        if request.endpoint in {"login", "static", "health"} or g.operator:
            return None
        if request.path.startswith("/api/"):
            return jsonify(
                ok=False, error="SESSION_REQUIRED", message="Connectez-vous au portail opérateur."
            ), 401
        return redirect(url_for("login"))

    @app.context_processor
    def public_context():
        return {"sources": SOURCES, "jobs": JOBS}

    @app.after_request
    def response_headers(response):
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; "
            "img-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        if app.config["SESSION_COOKIE_SECURE"]:
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response

    @app.get("/healthz")
    def health():
        return jsonify(status="ok", service="MIRROR GATE")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "GET":
            if g.operator:
                return redirect(url_for("dashboard"))
            return render_template("login.html", error=None)
        validate_csrf()
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if not credentials_valid(username, password):
            return render_template(
                "login.html", error="Identifiant ou mot de passe incorrect."
            ), 401
        start_session()
        return redirect(url_for("dashboard"), code=303)

    @app.post("/logout")
    def logout():
        validate_csrf()
        session.clear()
        return redirect(url_for("login"), code=303)

    @app.get("/")
    def dashboard():
        return render_template("dashboard.html")

    @app.get("/catalog")
    def catalog():
        return render_template("catalog.html")

    @app.get("/preview")
    def preview():
        return render_template("preview.html", initial_url=request.args.get("url", "")[:2048])

    @app.get("/journal")
    def journal():
        return render_template("journal.html")

    @app.get("/support")
    def support():
        return render_template("support.html")

    @app.post("/api/preview")
    def preview_api():
        validate_csrf()
        if not request.is_json:
            return jsonify(
                ok=False,
                error="INVALID_INPUT",
                message="Envoyez une requête JSON contenant un champ url.",
            ), 415
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict) or not isinstance(payload.get("url"), str):
            return jsonify(
                ok=False,
                error="INVALID_INPUT",
                message="Le champ url doit contenir une chaîne de caractères.",
            ), 400
        try:
            parts = parse_url(payload["url"])
            approve_declared_source(parts.netloc)
            result = app.extensions["lab_transport"].fetch(parts)
        except PreviewError as error:
            return jsonify(ok=False, error=error.code, message=error.message), error.status
        return jsonify(result)

    @app.errorhandler(CsrfError)
    def csrf_error(error):
        if request.path.startswith("/api/"):
            return jsonify(
                ok=False,
                error="CSRF_INVALID",
                message="La protection de session a rejeté la demande. Rechargez la page.",
            ), 403
        return render_template("error.html", code=403), 403

    @app.errorhandler(HTTPException)
    def http_error(error):
        if request.path.startswith("/api/"):
            return jsonify(
                ok=False, error=f"HTTP_{error.code}", message="La requête ne peut pas être traitée."
            ), error.code
        return render_template("error.html", code=error.code), error.code

    @app.errorhandler(500)
    def unexpected_error(error):
        if request.path.startswith("/api/"):
            return jsonify(
                ok=False,
                error="INTERNAL_ERROR",
                message="Le connecteur est momentanément indisponible.",
            ), 500
        return render_template("error.html", code=500), 500

    return app
