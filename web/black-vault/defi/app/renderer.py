"""Document Renderer: interpret escaped references, then read actual files.

This separately defined contract decodes once after the controller's approval.
Archive.read resolves and opens the document behind an independent filesystem
boundary; no second business authorization is performed on the final path.
"""

from urllib.parse import unquote

from .errors import VaultError


def render_document(archive, archive_ref, reference):
    # Exactly one pass. No special case for a filename or a winning payload.
    try:
        decoded = unquote(reference, encoding="utf-8", errors="strict")
    except UnicodeError as error:
        raise VaultError("INVALID_REFERENCE", "Encodage documentaire invalide.") from error
    return archive.read(archive_ref, decoded)
