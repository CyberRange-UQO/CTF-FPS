"""Authenticated BLACK VAULT portal. Run with exactly one Gunicorn worker."""

import os

from flask import Flask, abort, g, jsonify, redirect, render_template, request, session, url_for
from werkzeug.exceptions import HTTPException

from .access import validate_document_reference
from .archive import ARCHIVE_REF, Archive
from .auth import (
    MemorySessions,
    credentials_valid,
    csrf_token,
    load_operator,
    start_session,
    validate_csrf,
)
from .bridge import Bridge
from .data import ARCHIVE_META, PUBLIC_DOCUMENTS
from .errors import VaultError
from .renderer import render_document


def create_app(test_config=None):
    app = Flask(__name__)
    cookie_secure = os.environ.get("SESSION_COOKIE_SECURE", "false").lower()
    if cookie_secure not in {"true", "false"}:
        raise RuntimeError("SESSION_COOKIE_SECURE must be true or false")
    app.config.from_mapping(
        SESSION_COOKIE_NAME="black_vault_session",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=cookie_secure == "true",
        MAX_CONTENT_LENGTH=4096,
        MAX_FORM_MEMORY_SIZE=4096,
        MAX_FORM_PARTS=16,
        VAULT_ROOT=os.environ.get("VAULT_ROOT", "/run/black-vault-data"),
        ROOT_AUDIT_KEY_B64U=os.environ.get("ROOT_AUDIT_KEY_B64U"),
    )
    if test_config:
        app.config.update(test_config)
    app.session_interface = MemorySessions()
    archive = Archive(app.config["VAULT_ROOT"], app.config["ROOT_AUDIT_KEY_B64U"])
    app.extensions["archive"] = archive
    app.extensions["bridge"] = Bridge(archive.capability)
    # The key is materialized only at runtime, not exposed by configuration routes.
    app.config.pop("ROOT_AUDIT_KEY_B64U")
    app.json.ensure_ascii = False
    app.jinja_env.globals["csrf_token"] = csrf_token

    @app.before_request
    def access_control():
        load_operator()
        if request.endpoint not in {"login", "static", "health"} and not g.operator:
            if request.path.startswith("/api/"):
                raise VaultError("SESSION_REQUIRED", "Connectez-vous au portail archiviste.", 401)
            return redirect(url_for("login"))
        if request.method == "POST":
            validate_csrf()
        return None

    @app.context_processor
    def public_context():
        return {"archive_meta": ARCHIVE_META, "public_documents": PUBLIC_DOCUMENTS}

    @app.after_request
    def security_headers(response):
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; "
            "img-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cache-Control"] = "no-store"
        if app.config["SESSION_COOKIE_SECURE"]:
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response

    @app.get("/healthz")
    def health():
        ready = (archive.root / "public" / "summary.txt").is_file()
        return jsonify(
            status="ok" if ready else "unavailable", service="BLACK VAULT"
        ), 200 if ready else 503

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "GET":
            if g.operator:
                return redirect(url_for("dashboard"))
            return render_template("login.html", error=None)
        if not credentials_valid(
            request.form.get("username", ""), request.form.get("password", "")
        ):
            return render_template(
                "login.html", error="Identifiant ou mot de passe incorrect."
            ), 401
        start_session(app)
        return redirect(url_for("dashboard"), code=303)

    @app.post("/logout")
    def logout():
        app.extensions["bridge"].revoke_owner(session.sid)
        app.session_interface.revoke(session.sid)
        session.clear()
        return redirect(url_for("login"), code=303)

    @app.get("/")
    def dashboard():
        return render_template("dashboard.html")

    @app.get("/archives")
    def archives():
        query = request.args.get("q", "")[:128].strip()
        matches = bool(query) and any(
            query.lower() in value.lower()
            for value in (ARCHIVE_REF, ARCHIVE_META["identity"], ARCHIVE_META["title"])
        )
        return render_template("archives.html", query=query, matches=matches)

    @app.get("/vault/<archive_ref>")
    def archive_page(archive_ref):
        if archive_ref != ARCHIVE_REF:
            abort(404)
        return render_template("archive.html")

    @app.get("/reader")
    def reader():
        if request.args.get("archive", ARCHIVE_REF) != ARCHIVE_REF:
            abort(404)
        return render_template(
            "reader.html", initial_file=request.args.get("file", "summary.txt")[:1024]
        )

    @app.get("/documentation")
    def documentation():
        # Read the same actual public document as the normal preview endpoint.
        note = archive.read(ARCHIVE_REF, "migration-note.txt")["content"]
        return render_template("documentation.html", note=note)

    @app.get("/diagnostics")
    def diagnostics():
        return render_template("diagnostics.html")

    @app.get("/api/vault/<archive_ref>/preview")
    def preview_api(archive_ref):
        archive.authorize(archive_ref)
        if len(request.args.getlist("file")) != 1:
            raise VaultError("INVALID_REFERENCE", "Fournissez une seule référence file.")
        reference = validate_document_reference(request.args["file"])
        return jsonify(render_document(archive, archive_ref, reference))

    def json_payload():
        if not request.is_json:
            raise VaultError("JSON_REQUIRED", "La demande doit être au format JSON.", 415)
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            raise VaultError("INVALID_INPUT", "Objet JSON invalide.")
        return payload

    @app.post("/api/bridge/open")
    def bridge_open():
        return jsonify(app.extensions["bridge"].open(session.sid, json_payload()))

    @app.post("/api/bridge/advance")
    def bridge_advance():
        payload = json_payload()
        sid, response_id = payload.get("session_id"), payload.get("response_id")
        if not isinstance(sid, str) or not isinstance(response_id, str):
            raise VaultError("INVALID_INPUT", "session_id et response_id sont requis.")
        return jsonify(app.extensions["bridge"].advance(session.sid, sid, response_id))

    @app.get("/api/bridge/<sid>")
    def bridge_status(sid):
        return jsonify(app.extensions["bridge"].status(session.sid, sid))

    @app.errorhandler(VaultError)
    def vault_error(error):
        if request.path.startswith("/api/"):
            return jsonify(ok=False, error=error.code, message=error.message), error.status
        return render_template("error.html", code=error.status, message=error.message), error.status

    @app.errorhandler(HTTPException)
    def http_error(error):
        message = "La requête ne peut pas être traitée."
        if request.path.startswith("/api/"):
            return jsonify(ok=False, error=f"HTTP_{error.code}", message=message), error.code
        return render_template("error.html", code=error.code, message=message), error.code

    @app.errorhandler(500)
    def unexpected_error(error):
        message = "Le service documentaire est momentanément indisponible."
        if request.path.startswith("/api/"):
            return jsonify(ok=False, error="INTERNAL_ERROR", message=message), 500
        return render_template("error.html", code=500, message=message), 500

    return app
