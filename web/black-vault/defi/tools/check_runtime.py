"""Construction checks only: nominal documents and in-process diagnostic fixtures.

Run inside the image via stdin. No traversal, black-box solve or bypass tests.
"""

import base64
import json
import os
import re
import secrets
import tempfile
from pathlib import Path

from app.app import create_app
from app.archive import ALLOCATION_REF, ARCHIVE_REF, root_audit_key
from app.bridge import FLAG


def token(response):
    text = response.get_data(as_text=True)
    match = re.search(r'name="(?:csrf_token|csrf-token)" (?:value|content)="([^"]+)"', text)
    assert match, "CSRF token missing"
    return match.group(1)


def main():
    key = os.environ["ROOT_AUDIT_KEY_B64U"]
    assert root_audit_key(key) == key
    for invalid in (None, "", "invalid", "A" * 42, "A" * 43 + "=", "A" * 42 + "B"):
        try:
            root_audit_key(invalid)
        except RuntimeError:
            pass
        else:
            raise AssertionError("Invalid deployment key accepted")
    scratch = tempfile.mkdtemp(prefix="bv-functional-", dir="/tmp")
    app = create_app({"TESTING": True, "VAULT_ROOT": scratch})
    archive = app.extensions["archive"]
    expected = {
        "public/summary.txt",
        "public/inventory.txt",
        "public/migration-note.txt",
        "sealed/manifest.json",
        "sealed/reports/neurogrid-1057.txt",
        "sealed/diagnostics/bridge-access.json",
        "sealed/recovery/root-signing.json",
    }
    assert {
        str(p.relative_to(archive.root)) for p in archive.root.rglob("*") if p.is_file()
    } == expected
    material = json.loads((archive.root / "sealed/recovery/root-signing.json").read_text())
    assert material["secret_b64u"] == key
    assert len(base64.urlsafe_b64decode(material["secret_b64u"] + "=")) == 32
    assert FLAG not in (archive.root / "sealed/reports/neurogrid-1057.txt").read_text()

    client = app.test_client()
    assert client.get("/healthz").status_code == 200
    assert client.get("/").status_code == 302
    assert client.get(f"/api/vault/{ARCHIVE_REF}/preview?file=summary.txt").status_code == 401
    login = client.get("/login")
    assert "HttpOnly" in login.headers["Set-Cookie"]
    assert "SameSite=Lax" in login.headers["Set-Cookie"]
    assert client.post("/login", data={"username": "archivist.bv-021"}).status_code == 403
    result = client.post(
        "/login",
        data={
            "csrf_token": token(login),
            "username": "archivist.bv-021",
            "password": "BV-021-2147",
        },
    )
    assert result.status_code == 303
    assert result.headers["Set-Cookie"] != login.headers["Set-Cookie"]
    for page in (
        "/",
        "/archives",
        f"/archives?q={ARCHIVE_REF}",
        f"/vault/{ARCHIVE_REF}",
        "/reader",
        "/documentation",
        "/diagnostics",
    ):
        response = client.get(page)
        assert response.status_code == 200, page
        assert FLAG not in response.get_data(as_text=True), page
        assert response.headers["Cache-Control"] == "no-store"
    assert ARCHIVE_REF in client.get(f"/archives?q={ARCHIVE_REF}").get_data(as_text=True)
    for filename in ("summary.txt", "inventory.txt", "migration-note.txt"):
        response = client.get(f"/api/vault/{ARCHIVE_REF}/preview?file={filename}")
        assert response.status_code == 200
        assert response.json["content"] == (archive.root / "public" / filename).read_text()
    assert client.get(f"/api/vault/{ARCHIVE_REF}/preview?file=missing.txt").status_code == 404

    csrf = token(client.get("/diagnostics"))
    headers = {"X-CSRF-Token": csrf}
    # Known in-process fixture capability, obtained directly from Archive; not an exploit.
    opened = client.post(
        "/api/bridge/open",
        headers=headers,
        json={
            "archive_ref": ARCHIVE_REF,
            "allocation_ref": ALLOCATION_REF,
            "capability": archive.capability,
        },
    )
    assert opened.status_code == 200
    assert "attestation" not in opened.json and FLAG not in opened.get_data(as_text=True)
    sid = opened.json["session_id"]
    first = client.post(
        "/api/bridge/advance",
        headers=headers,
        json={
            "session_id": sid,
            "response_id": "identify",
        },
    )
    assert first.status_code == 200 and "attestation" not in first.json
    completed = client.post(
        "/api/bridge/advance",
        headers=headers,
        json={
            "session_id": sid,
            "response_id": "expose",
        },
    )
    assert completed.status_code == 200
    assert completed.json["attestation"]["proof"] == FLAG
    assert client.get(f"/api/bridge/{sid}").json["attestation"] == completed.json["attestation"]
    replay = client.post(
        "/api/bridge/open",
        headers=headers,
        json={
            "archive_ref": ARCHIVE_REF,
            "allocation_ref": ALLOCATION_REF,
            "capability": archive.capability,
        },
    )
    assert replay.status_code == 200 and replay.json["session_id"] != sid
    assert "attestation" not in replay.json
    assert client.post("/logout", data={"csrf_token": csrf}).status_code == 303
    assert client.get(f"/api/vault/{ARCHIVE_REF}/preview?file=summary.txt").status_code == 401

    # HTTPS cookie configuration and key startup contract, using fixture configuration.
    fixture_key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")
    secure = create_app(
        {
            "TESTING": True,
            "VAULT_ROOT": scratch,
            "ROOT_AUDIT_KEY_B64U": fixture_key,
            "SESSION_COOKIE_SECURE": True,
        }
    )
    assert "Secure" in secure.test_client().get("/login").headers["Set-Cookie"]
    for bad_key in (None, "invalid"):
        try:
            create_app({"VAULT_ROOT": scratch, "ROOT_AUDIT_KEY_B64U": bad_key})
        except RuntimeError:
            pass
        else:
            raise AssertionError("Startup must reject invalid/missing keys")
    assets = Path(app.root_path)
    for directory in ("templates", "static", "archive_templates/public"):
        for path in (assets / directory).rglob("*"):
            if path.is_file():
                text = path.read_text()
                assert FLAG not in text and key not in text and archive.capability not in text
    print("PASS: startup configuration, archive fixtures, login/CSRF/logout, public documents,")
    print("      authenticated pages, nominal diagnostic, attestation/replay, frontend artifacts.")
    print("No traversal or offensive verification performed; independent audit pending.")


if __name__ == "__main__":
    main()
