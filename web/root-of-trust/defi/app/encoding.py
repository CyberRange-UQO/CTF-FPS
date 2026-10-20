import base64
import re

_B64U = re.compile(r"[A-Za-z0-9_-]+", re.ASCII)


def b64u(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def decode_b64u(value):
    if type(value) is not str or not _B64U.fullmatch(value):
        raise ValueError("Invalid Base64URL")
    raw = base64.b64decode(
        value + "=" * (-len(value) % 4), altchars=b"-_", validate=True
    )
    if b64u(raw) != value:
        raise ValueError("Noncanonical Base64URL")
    return raw


def configured_key(value, variable):
    try:
        raw = decode_b64u(value)
        if len(raw) != 32:
            raise ValueError("Invalid size")
    except (ValueError, TypeError):
        # Never interpolate the supplied value, even in a startup traceback.
        raise RuntimeError(
            f"{variable} must be canonical unpadded Base64URL encoding 32 bytes"
        ) from None
    return raw
