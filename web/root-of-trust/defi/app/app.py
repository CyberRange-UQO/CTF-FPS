import hmac
import os
import time

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

from .attestation import AttestationAuthority
from .auth import CASE_ID, RequestAuthority
from .canonical import strict_loads
from .contracts import CONTRACT, POLICY
from .encoding import configured_key
from .errors import APIError
from .events import EventRegistry
from .proof import validate_proof


def create_app():
    audit_key = configured_key(os.environ.get("ROOT_AUDIT_KEY_B64U"), "ROOT_AUDIT_KEY_B64U")
    seed = configured_key(os.environ.get("ATTESTATION_ED25519_SEED_B64U"), "ATTESTATION_ED25519_SEED_B64U")
    if hmac.compare_digest(audit_key, seed):
        raise RuntimeError("Request and attestation authorities require distinct keys")
    authority, attestation = RequestAuthority(audit_key), AttestationAuthority(seed)
    del audit_key, seed
    registry = EventRegistry()
    app = Flask(__name__)
    app.config.update(DEBUG=False, TESTING=False, MAX_CONTENT_LENGTH=16384)

    @app.after_request
    def protect_response(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; script-src 'self'; style-src 'self'; "
            "img-src 'self'; connect-src 'self'; font-src 'self'; "
            "base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response

    @app.errorhandler(APIError)
    def api_error(error):
        response = jsonify(error=error.code, message=error.message)
        if error.status == 401:
            response.headers["WWW-Authenticate"] = 'Bearer realm="vanta-trust-ledger"'
        return response, error.status

    @app.errorhandler(HTTPException)
    def http_error(error):
        errors = {
            404: ("NOT_FOUND", "Ressource inconnue."),
            405: ("METHOD_NOT_ALLOWED", "Méthode non autorisée."),
            413: ("REQUEST_TOO_LARGE", "Le corps dépasse la limite de 16 Kio."),
            415: ("UNSUPPORTED_MEDIA_TYPE", "Un corps application/json est requis."),
        }
        code, message = errors.get(error.code, ("INVALID_REQUEST", "Requête HTTP invalide."))
        response = jsonify(error=code, message=message)
        if error.code == 405 and error.valid_methods:
            response.headers["Allow"] = ", ".join(error.valid_methods)
        return response, error.code

    @app.errorhandler(Exception)
    def unexpected_error(error):
        # Do not log exceptions, bodies, tokens or receipts. No diagnostics endpoint.
        app.logger.error("ROOT OF TRUST internal request failure")
        return jsonify(error="INTERNAL_ERROR", message="Le service ne peut pas traiter cette demande."), 500

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/public/contract")
    def contract():
        return jsonify(CONTRACT)

    @app.get("/api/public/policy")
    def policy():
        return jsonify(POLICY)

    @app.get("/api/public/attestation-key")
    def public_key():
        return jsonify(attestation.public_document())

    @app.get("/healthz")
    def health():
        return jsonify(status="ok")

    @app.get("/api/authority/verify")
    def verify_authority():
        claims = authority.authorize(request.headers.get("Authorization"), "case:read")
        # Inform the client of the lifetime remaining on this verified request.
        # No JWT issuance, backend session or publication permission is created.
        return jsonify(
            status="AUTHORITY_VERIFIED", case_id=CASE_ID,
            expires_at=claims["exp"],
            valid_for_ms=max(0, int((claims["exp"] - time.time()) * 1000)),
        )

    @app.get(f"/api/cases/{CASE_ID}/events")
    def list_events():
        authority.authorize(request.headers.get("Authorization"), "case:read")
        return jsonify(case_id=CASE_ID, events=registry.catalogue())

    @app.get(f"/api/cases/{CASE_ID}/events/<event_id>")
    def event_detail(event_id):
        authority.authorize(request.headers.get("Authorization"), "case:read")
        document = registry.document(event_id)
        if document is None:
            raise APIError(404, "NOT_FOUND", "Événement inconnu dans le dossier autorisé.")
        return jsonify(document)

    @app.post("/api/disclosures")
    def disclosure():
        claims = authority.authorize(request.headers.get("Authorization"), "disclosure:publish")
        if request.mimetype != "application/json":
            raise APIError(415, "UNSUPPORTED_MEDIA_TYPE", "Un corps application/json est requis.")
        try:
            body = strict_loads(request.get_data(cache=False))
        except (ValueError, UnicodeError, RecursionError):
            raise APIError(400, "INVALID_MANIFEST", "JSON invalide, ambigu ou non conforme ; nombres entiers uniquement.") from None
        if type(body) is not dict or set(body) != {"manifest"}:
            raise APIError(400, "INVALID_MANIFEST", "Le corps doit contenir exactement le champ manifest.")
        manifest = body["manifest"]
        digest = validate_proof(manifest, claims["proof_sha256"], registry)
        return jsonify(attestation.issue(manifest, digest)), 201

    return app
