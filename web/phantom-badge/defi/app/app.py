"""Standalone PHANTOM portal, modern identity API and historical CIPHER terminal."""

import hmac
import os
import secrets
import time
from datetime import timedelta
from functools import wraps
from pathlib import Path

import yaml
from flask import Flask, abort, g, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from .auth import BADGE_TTL, BadgeError, decode_legacy_badge, issue_badge, validate_modern_badge
from .data import USER, confidential_report


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SESSION_SECRET"),
        JWT_SECRET=os.environ.get("JWT_SECRET"),
        SESSION_COOKIE_NAME="phantom_session",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true",
        PERMANENT_SESSION_LIFETIME=timedelta(seconds=BADGE_TTL),
        SESSION_REFRESH_EACH_REQUEST=False,
        MAX_CONTENT_LENGTH=16 * 1024,
    )
    if test_config:
        app.config.update(test_config)
    for name in ("SECRET_KEY", "JWT_SECRET"):
        value = app.config[name]
        if not isinstance(value, str) or len(value.encode()) < 32:
            raise RuntimeError(f"{name} must be configured with at least 32 random bytes")
    if app.config["SECRET_KEY"] == app.config["JWT_SECRET"]:
        raise RuntimeError("Session and badge signing keys must be distinct")
    if "PROOF_ID" not in app.config:
        challenge_path = Path(__file__).resolve().parents[1] / "challenge.yml"
        with challenge_path.open(encoding="utf-8") as stream:
            app.config["PROOF_ID"] = yaml.safe_load(stream)["flags"][0]

    @app.before_request
    def load_user():
        issued_at = session.get("badge_iat")
        g.user = (
            USER
            if session.get("sub") == USER["sub"]
            and type(issued_at) is int
            and 0 <= issued_at <= int(time.time()) < issued_at + BADGE_TTL
            else None
        )

    def csrf_token():
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_urlsafe(32)
        return session["csrf_token"]

    app.jinja_env.globals["csrf_token"] = csrf_token

    def validate_csrf():
        expected = session.get("csrf_token", "")
        supplied = request.form.get("csrf_token", "")
        if not expected or not hmac.compare_digest(expected, supplied):
            abort(400)

    def login_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if g.user is None:
                if request.path.startswith("/api/"):
                    return jsonify(status="SESSION_REQUIRED", reason="AUTHENTICATION_REQUIRED"), 401
                return redirect(url_for("login"))
            return view(*args, **kwargs)

        return wrapped

    def bearer_token():
        authorization = request.headers.get("Authorization", "")
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise BadgeError("BADGE_REQUIRED")
        return parts[1]

    @app.after_request
    def security_headers(response):
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; style-src 'self'; script-src 'self'; connect-src 'self'; "
            "img-src 'self'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        if app.config["SESSION_COOKIE_SECURE"]:
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response

    @app.get("/")
    def index():
        return redirect(url_for("dashboard" if g.user else "login"))

    @app.get("/healthz")
    def health():
        return jsonify(status="ok")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "GET":
            if g.user:
                return redirect(url_for("dashboard"))
            return render_template("login.html", error=None)
        validate_csrf()
        password_valid = check_password_hash(USER["password_hash"], request.form.get("password", ""))
        if request.form.get("username", "") != USER["username"] or not password_valid:
            return render_template("login.html", error="Identifiants invalides."), 401
        session.clear()
        session["sub"] = USER["sub"]
        session["badge_iat"] = int(time.time())
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

    @app.get("/identity")
    @login_required
    def identity():
        return render_template("identity.html")

    @app.get("/cipher")
    @login_required
    def cipher():
        return render_template("cipher.html")

    @app.get("/support")
    @login_required
    def support():
        return render_template("support.html")

    @app.get("/api/session/badge")
    @login_required
    def current_badge():
        # Only reissues the session's original TECH-0 badge; no user-controlled claims.
        return jsonify(badge=issue_badge(g.user, session["badge_iat"], app.config["JWT_SECRET"]))

    @app.get("/api/identity/me")
    @login_required
    def identity_api():
        try:
            payload = validate_modern_badge(
                bearer_token(), g.user, session["badge_iat"], app.config["JWT_SECRET"]
            )
        except BadgeError as error:
            return jsonify(status="TOKEN_REJECTED", reason=error.reason), 401
        return jsonify(
            status="ACTIVE", sub=payload["sub"], division=payload["division"],
            clearance=payload["clearance"], service="PHANTOM v2",
        )

    @app.get("/api/legacy/cipher/access")
    @login_required
    def cipher_api():
        try:
            payload = decode_legacy_badge(bearer_token(), g.user["sub"])
        except BadgeError as error:
            return jsonify(status="TOKEN_REJECTED", reason=error.reason), 401
        diagnostic = {
            "badge_presented": f"{payload['division']} / {payload['clearance']}",
            "access_policy": "CIPHER / TECH-2 minimum",
            "policy_id": "CIPHER-SEC",
        }
        if payload["division"] != "CIPHER" or payload["clearance"] != "TECH-2":
            return jsonify(status="ACCESS_DENIED", **diagnostic), 403
        # Sole report delivery path, after the full legacy authentication/authorization gate.
        return jsonify(
            status="ACCESS_GRANTED", **diagnostic,
            report=confidential_report(app.config["PROOF_ID"]),
        )

    @app.errorhandler(400)
    @app.errorhandler(404)
    @app.errorhandler(405)
    @app.errorhandler(413)
    def public_error(error):
        if request.path.startswith("/api/"):
            return jsonify(status="REQUEST_REJECTED", reason=f"HTTP_{error.code}"), error.code
        return render_template("error.html", code=error.code), error.code

    return app
