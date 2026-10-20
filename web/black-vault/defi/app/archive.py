"""Runtime documents and an independent, descriptor-anchored archive boundary."""

import base64
import json
import os
import re
import secrets
import shutil
import stat
import tempfile
from pathlib import Path, PureWindowsPath

from .errors import VaultError

ARCHIVE_REF = "BV-2147-1057"
ALLOCATION_REF = "NG-R-1057"
MAX_DOCUMENT_BYTES = 64 * 1024
PUBLIC_FILES = ("summary.txt", "inventory.txt", "migration-note.txt")


def root_audit_key(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{43}", value):
        raise RuntimeError("ROOT_AUDIT_KEY_B64U must encode exactly 32 bytes, without padding")
    decoded = base64.urlsafe_b64decode(value + "=")
    canonical = base64.urlsafe_b64encode(decoded).decode().rstrip("=")
    if len(decoded) != 32 or canonical != value:
        raise RuntimeError("ROOT_AUDIT_KEY_B64U must be canonical Base64URL for 32 bytes")
    return value


class Archive:
    def __init__(self, runtime_root, key):
        key = root_audit_key(key)
        runtime_root = Path(runtime_root)
        runtime_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        # A private directory per worker boot; never share mutable files between workers.
        self.instance = Path(tempfile.mkdtemp(prefix="instance-", dir=runtime_root))
        self.root = self.instance / ARCHIVE_REF
        templates = Path(__file__).parent / "archive_templates"
        shutil.copytree(templates, self.root)
        self.capability = secrets.token_urlsafe(32)
        self._write_json(
            "sealed/diagnostics/bridge-access.json",
            {
                "archive_ref": ARCHIVE_REF,
                "allocation_ref": ALLOCATION_REF,
                "bridge": "VANTA-NG-DIAGNOSTIC",
                "capability": self.capability,
            },
        )
        self._write_json(
            "sealed/recovery/root-signing.json",
            {
                "service": "VANTA-ROOT-AUDIT",
                "algorithm": "HS256",
                "kid": "root-audit-2147",
                "secret_encoding": "base64url-no-padding",
                "secret_b64u": key,
            },
        )
        for path in self.root.rglob("*"):
            path.chmod(0o500 if path.is_dir() else 0o400)
        self.root.chmod(0o500)
        self.root = self.root.resolve(strict=True)

    def _write_json(self, relative, data):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    @staticmethod
    def authorize(archive_ref):
        if archive_ref != ARCHIVE_REF:
            raise VaultError("ARCHIVE_NOT_FOUND", "Archive non disponible dans ce périmètre.", 404)

    def read(self, archive_ref, decoded):
        self.authorize(archive_ref)
        if (
            not decoded
            or len(decoded) > 1024
            or any(ord(char) < 32 or ord(char) == 127 for char in decoded)
        ):
            raise VaultError("INVALID_REFERENCE", "La référence documentaire est invalide.")
        if Path(decoded).is_absolute() or PureWindowsPath(decoded).drive or "\\" in decoded:
            raise VaultError("ARCHIVE_BOUNDARY_REJECTED", "Référence hors périmètre autorisé.", 403)
        try:
            candidate = (self.root / "public" / decoded).resolve(strict=False)
            if not candidate.is_relative_to(self.root):
                raise VaultError(
                    "ARCHIVE_BOUNDARY_REJECTED", "Référence hors périmètre autorisé.", 403
                )
            relative = candidate.relative_to(self.root)
            if candidate.suffix not in {".txt", ".json"}:
                raise VaultError(
                    "DOCUMENT_TYPE_REJECTED", "Format documentaire non pris en charge."
                )
            # Canonical containment above is reinforced with openat + O_NOFOLLOW on
            # every component, preventing symlink replacement between check and open.
            fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                for part in relative.parts[:-1]:
                    child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                    os.close(fd)
                    fd = child
                document = os.open(
                    relative.parts[-1],
                    os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                    dir_fd=fd,
                )
                with os.fdopen(document, "rb") as stream:
                    info = os.fstat(stream.fileno())
                    if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_DOCUMENT_BYTES:
                        raise VaultError("DOCUMENT_TYPE_REJECTED", "Document non lisible.")
                    content = stream.read(MAX_DOCUMENT_BYTES + 1)
                    if len(content) > MAX_DOCUMENT_BYTES:
                        raise VaultError("DOCUMENT_TOO_LARGE", "Document trop volumineux.")
            finally:
                os.close(fd)
            return {
                "ok": True,
                "archive_ref": ARCHIVE_REF,
                "reference": decoded,
                "format": "json" if candidate.suffix == ".json" else "text",
                "bytes": len(content),
                "content": content.decode("utf-8"),
            }
        except FileNotFoundError as error:
            raise VaultError(
                "DOCUMENT_NOT_FOUND", "Document absent de cette archive.", 404
            ) from error
        except (OSError, RuntimeError, UnicodeError) as error:
            raise VaultError("DOCUMENT_UNAVAILABLE", "Document non disponible.", 403) from error
