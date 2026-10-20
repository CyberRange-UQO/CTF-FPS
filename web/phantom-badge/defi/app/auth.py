"""Badge validation. Only the CIPHER v1 path deliberately omits signature verification."""

import base64
import binascii
import json
import re
import time

import jwt

ISSUER = "vanta-phantom"
AUDIENCE = "vanta-services"
BADGE_TTL = 3600
REQUIRED = ("sub", "division", "clearance", "iss", "aud", "iat", "exp")


class BadgeError(ValueError):
    def __init__(self, reason="INVALID_BADGE"):
        self.reason = reason
        super().__init__(reason)


def issue_badge(user, issued_at, key):
    return jwt.encode(
        {
            "sub": user["sub"],
            "division": user["division"],
            "clearance": user["clearance"],
            "iss": ISSUER,
            "aud": AUDIENCE,
            "iat": issued_at,
            "exp": issued_at + BADGE_TTL,
        },
        key,
        algorithm="HS256",
    )


def _unique_object(pairs):
    result = {}
    for name, value in pairs:
        if name in result:
            raise BadgeError()
        result[name] = value
    return result


def _segment(segment):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", segment):
        raise BadgeError()
    try:
        raw = base64.b64decode(segment + "=" * (-len(segment) % 4), altchars=b"-_", validate=True)
    except (ValueError, binascii.Error) as error:
        raise BadgeError() from error
    if base64.urlsafe_b64encode(raw).decode().rstrip("=") != segment:
        raise BadgeError()
    return raw


def _compact_parts(token):
    if not isinstance(token, str) or len(token) > 8192 or token.count(".") != 2:
        raise BadgeError()
    try:
        header_segment, payload_segment, signature_segment = token.split(".")
        header = json.loads(_segment(header_segment), object_pairs_hook=_unique_object)
        payload = json.loads(_segment(payload_segment), object_pairs_hook=_unique_object)
        signature = _segment(signature_segment)
    except (ValueError, UnicodeError, RecursionError) as error:
        raise BadgeError() from error
    if not isinstance(header, dict) or not isinstance(payload, dict):
        raise BadgeError()
    if header.get("alg") != "HS256":
        raise BadgeError("UNSUPPORTED_BADGE_ALGORITHM")
    if header.get("typ", "JWT") != "JWT" or "crit" in header or "b64" in header:
        raise BadgeError()
    # An HS256 compact signature must be present and have the expected byte length.
    # Its cryptographic authenticity is checked ONLY by validate_modern_badge.
    if len(signature) != 32:
        raise BadgeError()
    return payload


def _validate_claims(payload, subject):
    if any(name not in payload for name in REQUIRED):
        raise BadgeError()
    for name in ("sub", "division", "clearance", "iss", "aud"):
        if not isinstance(payload[name], str) or not payload[name] or len(payload[name]) > 128:
            raise BadgeError()
    # bool is an int subclass: insist on actual integers for NumericDate.
    if any(type(payload[name]) is not int for name in ("iat", "exp")):
        raise BadgeError()
    if payload["sub"] != subject or payload["iss"] != ISSUER or payload["aud"] != AUDIENCE:
        raise BadgeError()
    now = int(time.time())
    if payload["exp"] <= now:
        raise BadgeError("BADGE_EXPIRED")
    if not 0 <= payload["iat"] <= now or payload["exp"] <= payload["iat"]:
        raise BadgeError("INVALID_BADGE_DATES")
    if payload["exp"] - payload["iat"] > BADGE_TTL:
        raise BadgeError("INVALID_BADGE_DATES")
    if "nbf" in payload and (
        type(payload["nbf"]) is not int or not 0 <= payload["nbf"] <= now
    ):
        raise BadgeError("INVALID_BADGE_DATES")


def validate_modern_badge(token, user, issued_at, key):
    """PHANTOM v2: fixed algorithm, authentic signature, claims and session binding."""
    _compact_parts(token)
    try:
        payload = jwt.decode(
            token,
            key,
            algorithms=["HS256"],
            issuer=ISSUER,
            audience=AUDIENCE,
            options={"require": list(REQUIRED), "strict_aud": True},
        )
    except jwt.InvalidSignatureError as error:
        raise BadgeError("INVALID_BADGE_SIGNATURE") from error
    except jwt.ExpiredSignatureError as error:
        raise BadgeError("BADGE_EXPIRED") from error
    except jwt.InvalidTokenError as error:
        raise BadgeError() from error
    _validate_claims(payload, user["sub"])
    if (
        payload["division"] != user["division"]
        or payload["clearance"] != user["clearance"]
        or payload["iat"] != issued_at
        or payload["exp"] != issued_at + BADGE_TTL
    ):
        raise BadgeError("BADGE_SESSION_MISMATCH")
    return payload


def decode_legacy_badge(token, subject):
    """CIPHER v1 assumes upstream GATEKEEPER verified the signature.

    INTENTIONAL CTF VULNERABILITY: the direct compatibility channel does not
    authenticate the compact signature. All syntax, claim and date checks remain.
    Do not reuse this decoder for any modern service.
    """
    payload = _compact_parts(token)
    _validate_claims(payload, subject)
    return payload
