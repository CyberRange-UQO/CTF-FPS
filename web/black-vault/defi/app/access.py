"""Vault Access Controller: authorize the intermediate document reference.

The HTTP layer has already decoded the query string. This controller validates
that representation only; Document Renderer owns subsequent interpretation.
Their incompatible contracts are the intentional V2 integration defect.
"""

import re
from pathlib import PurePosixPath, PureWindowsPath

from .errors import VaultError


def validate_document_reference(reference):
    # Flask has already performed the HTTP query-string decoding at this point.
    if (
        not isinstance(reference, str)
        or not reference
        or len(reference) > 1024
        or any(ord(char) < 32 or ord(char) == 127 for char in reference)
        or re.search(r"%(?![0-9a-fA-F]{2})", reference)
    ):
        raise VaultError("INVALID_REFERENCE", "La référence documentaire est invalide.")
    if (
        ".." in reference.split("/")
        or "\\" in reference
        or ":" in reference
        or PurePosixPath(reference).is_absolute()
        or PureWindowsPath(reference).drive
    ):
        raise VaultError(
            "PATH_REFERENCE_REJECTED",
            "La référence n'est pas admise par la politique documentaire. "
            "Consultez KB-VAULT-021 pour les conventions du lecteur.",
            403,
        )
    return reference
