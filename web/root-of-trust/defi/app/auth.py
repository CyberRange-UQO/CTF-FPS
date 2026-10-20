"""Fixed HS256 authority with strict application claims and bounded lifetime."""

import re
import time

import jwt

from .canonical import strict_loads
from .encoding import decode_b64u
from .errors import APIError

CASE_ID = "CASE-SIL-2147-07"
ISSUER = "vanta-root-audit"
AUDIENCE = "vanta-trust-ledger"
SUBJECT = "svc:root-audit-recovery"
JWT_HEADER = {"alg": "HS256", "kid": "root-audit-2147", "typ": "JWT"}
SCOPES = frozenset({"case:read", "disclosure:publish"})
REQUIRED = frozenset({"iss", "aud", "sub", "case_id", "scope", "iat", "exp"})
HEX256 = re.compile(r"[0-9a-f]{64}", re.ASCII)
MAX_TOKEN_BYTES = 4096
MAX_LIFETIME = 600
FUTURE_IAT_TOLERANCE = 30


def invalid_token():
    return APIError(401, "INVALID_TOKEN", "Autorisation JWT absente, mal formée ou hors contrat.")


class RequestAuthority:
    def __init__(self, key):
        self._key = key

    def authorize(self, authorization, required_scope):
        if type(authorization) is not str or len(authorization) > MAX_TOKEN_BYTES + 7:
            raise invalid_token()
        parts = authorization.split(" ")
        if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1]:
            raise invalid_token()
        token = parts[1]
        try:
            token.encode("ascii")
            if len(token) > MAX_TOKEN_BYTES:
                raise ValueError()
            segments = token.split(".")
            if len(segments) != 3:
                raise ValueError()
            header = strict_loads(decode_b64u(segments[0]))
            # Structural decoding is untrusted. No permission decision occurs here.
            strict_loads(decode_b64u(segments[1]))
            if header != JWT_HEADER or type(header) is not dict:
                raise ValueError()
            if len(decode_b64u(segments[2])) != 32:
                raise ValueError()
            verified = jwt.decode_complete(
                token, self._key, algorithms=["HS256"],
                audience=AUDIENCE, issuer=ISSUER, subject=SUBJECT,
                leeway=FUTURE_IAT_TOLERANCE,
                options={"require": sorted(REQUIRED), "strict_aud": True},
            )
        except jwt.InvalidSignatureError:
            raise APIError(401, "INVALID_SIGNATURE", "La signature HS256 est invalide.") from None
        except (jwt.InvalidTokenError, ValueError, TypeError, UnicodeError, RecursionError):
            raise invalid_token() from None

        claims = verified["payload"]
        # PyJWT verified the signature and registered claims. Enforce exact JSON
        # types as well: bool, numeric strings and multiple audiences are forbidden.
        if type(claims) is not dict or not REQUIRED <= claims.keys():
            raise invalid_token()
        if claims.keys() - (REQUIRED | {"proof_sha256"}):
            raise invalid_token()
        expected = {"iss": ISSUER, "aud": AUDIENCE, "sub": SUBJECT, "case_id": CASE_ID}
        if any(type(claims[k]) is not str or claims[k] != v for k, v in expected.items()):
            raise invalid_token()
        scopes = claims["scope"]
        if (type(scopes) is not list or not 1 <= len(scopes) <= len(SCOPES)
                or any(type(s) is not str or s not in SCOPES for s in scopes)
                or len(set(scopes)) != len(scopes)):
            raise invalid_token()
        issued, expires, now = claims["iat"], claims["exp"], time.time()
        if type(issued) is not int or type(expires) is not int:
            raise invalid_token()
        if not (now - MAX_LIFETIME <= issued <= now + FUTURE_IAT_TOLERANCE
                and expires > now and 0 < expires - issued <= MAX_LIFETIME):
            raise invalid_token()
        publishes = "disclosure:publish" in scopes
        proof = claims.get("proof_sha256")
        if publishes:
            if type(proof) is not str or not HEX256.fullmatch(proof):
                raise invalid_token()
        elif "proof_sha256" in claims:
            raise invalid_token()
        if required_scope not in scopes:
            raise APIError(403, "INSUFFICIENT_SCOPE", "Le jeton ne permet pas cette opération.")
        return claims
