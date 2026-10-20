"""SOURCE-GUARD 1.2: newly deployed source policy, intentionally flawed for the CTF.

Its authorization design checks a raw authority prefix, not the effective host.
The independent transport in transport.py remains the lab security boundary.
"""

from .transport import PreviewError

APPROVED_SOURCES = ("mirror-catalog",)


def approve_declared_source(raw_authority):
    # Intentional V2 vulnerability: userinfo is not separated from the hostname.
    if not any(raw_authority.lower().startswith(source) for source in APPROVED_SOURCES):
        raise PreviewError(
            "DESTINATION_NOT_APPROVED",
            "Cette destination n'est pas une source documentaire approuvée. "
            "Consultez le référentiel de validation des sources.",
            403,
        )
