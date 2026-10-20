"""Ordinary operator authentication and CSRF; no intentional auth weakness."""

import hmac
import secrets
import time

from flask import g, request, session
from werkzeug.security import check_password_hash

SESSION_TTL = 30 * 60
OPERATOR = {
    "id": "operator.mg-041",
    "function": "Infrastructure Monitoring Operator",
    "clearance": "OPS-1",
}
PASSWORD_HASH = (
    "pbkdf2:sha256:1000000$655a4f03b7f8a3f5e60d82392f8d163e$"
    "3bed9f9b734921f6e2a35efb556ad67995acca9053cae05bf8fe3d28edc1d45c"
)


class CsrfError(Exception):
    """The submitted operation does not carry the session's CSRF token."""


def credentials_valid(username, password):
    # Check the password even for an unknown name; never return which field failed.
    valid_password = check_password_hash(PASSWORD_HASH, password)
    return username == OPERATOR["id"] and valid_password


def load_operator():
    issued_at = session.get("authenticated_at")
    now = int(time.time())
    g.operator = (
        OPERATOR
        if session.get("operator_id") == OPERATOR["id"]
        and type(issued_at) is int
        and 0 <= issued_at <= now < issued_at + SESSION_TTL
        else None
    )
    if g.operator is None and "operator_id" in session:
        session.clear()


def csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


def validate_csrf():
    expected = session.get("csrf_token", "")
    supplied = (
        request.headers.get("X-CSRF-Token", "")
        if request.path.startswith("/api/")
        else request.form.get("csrf_token", "")
    )
    if (
        not expected
        or not supplied
        or not hmac.compare_digest(expected.encode("utf-8"), supplied.encode("utf-8"))
    ):
        raise CsrfError


def start_session():
    # Rotate the anonymous session and CSRF token at authentication.
    session.clear()
    session["operator_id"] = OPERATOR["id"]
    session["authenticated_at"] = int(time.time())
    session.permanent = True
    csrf_token()
