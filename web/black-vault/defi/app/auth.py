"""Opaque cookies, bounded server sessions and synchronizer CSRF tokens."""

import hmac
import secrets
import time
from threading import RLock

from flask import g, request, session
from flask.sessions import SessionInterface, SessionMixin
from werkzeug.datastructures import CallbackDict
from werkzeug.security import check_password_hash, generate_password_hash

from .errors import VaultError

SESSION_TTL = 2 * 60 * 60
OPERATOR = {"id": "archivist.bv-021", "role": "ARCHIVE_OPERATOR", "clearance": "ARCHIVE-1"}
# The published challenge password is not a deployment secret.
PASSWORD_HASH = generate_password_hash("BV-021-2147", method="pbkdf2:sha256:1000000")


class ServerSession(CallbackDict, SessionMixin):
    def __init__(self, initial=None, sid=None, new=False):
        super().__init__(initial, lambda obj: setattr(obj, "modified", True))
        self.sid = sid or secrets.token_urlsafe(32)
        self.new = new
        self.modified = False


class MemorySessions(SessionInterface):
    """One Gunicorn worker; fixed TTL, bounded capacity, no cookie-side state."""

    def __init__(self, capacity=2048):
        self.rows = {}
        self.capacity = capacity
        self.lock = RLock()

    def _prune(self):
        now = time.monotonic()
        for sid in [sid for sid, (expires, _) in self.rows.items() if expires <= now]:
            del self.rows[sid]

    def open_session(self, app, request):
        sid = request.cookies.get(self.get_cookie_name(app), "")
        with self.lock:
            self._prune()
            row = self.rows.get(sid)
            if row:
                return ServerSession(dict(row[1]), sid=sid)
        return ServerSession(new=True)

    def revoke(self, sid):
        with self.lock:
            self.rows.pop(sid, None)

    def save_session(self, app, session, response):
        name = self.get_cookie_name(app)
        options = {
            "httponly": True,
            "secure": self.get_cookie_secure(app),
            "samesite": "Lax",
            "path": "/",
        }
        if not session:
            self.revoke(session.sid)
            if session.modified:
                response.delete_cookie(name, **options)
            return
        if not session.modified:
            return
        with self.lock:
            self._prune()
            if session.new:
                if len(self.rows) >= self.capacity:
                    # Prefer retiring an anonymous login form over an active operator.
                    anonymous = next(
                        (sid for sid, (_, data) in self.rows.items() if "operator" not in data),
                        None,
                    )
                    oldest = anonymous or min(self.rows, key=lambda sid: self.rows[sid][0])
                    del self.rows[oldest]
                expires = time.monotonic() + SESSION_TTL
            else:
                row = self.rows.get(session.sid)
                if row is None:
                    # A concurrent request must never resurrect a revoked session.
                    return
                expires = row[0]
            self.rows[session.sid] = (expires, dict(session))
        if session.new:
            response.set_cookie(name, session.sid, max_age=SESSION_TTL, **options)


def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)
    return session["csrf"]


def validate_csrf():
    expected = session.get("csrf", "")
    supplied = (
        request.headers.get("X-CSRF-Token", "")
        if request.path.startswith("/api/")
        else request.form.get("csrf_token", "")
    )
    if not expected or not hmac.compare_digest(expected.encode(), supplied.encode()):
        raise VaultError("CSRF_INVALID", "Rechargez la page pour renouveler la protection.", 403)


def credentials_valid(username, password):
    return check_password_hash(PASSWORD_HASH, password) and username == OPERATOR["id"]


def load_operator():
    g.operator = OPERATOR if session.get("operator") == OPERATOR["id"] else None


def start_session(app):
    old_sid = session.sid
    app.session_interface.revoke(old_sid)
    app.extensions["bridge"].revoke_owner(old_sid)
    session.clear()
    session.sid = secrets.token_urlsafe(32)
    session.new = True
    session["operator"] = OPERATOR["id"]
    csrf_token()
