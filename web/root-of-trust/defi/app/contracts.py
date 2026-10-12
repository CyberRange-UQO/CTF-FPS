from .auth import AUDIENCE, CASE_ID, ISSUER, JWT_HEADER, SUBJECT
from .proof import ASSERTION, SCHEMA

DEMO_VECTOR = {
    "schema": SCHEMA, "case_id": "CASE-DEMO-001", "assertion": "DEMO_ASSERTION",
    "evidence": [
        {"id": "EVT-DEMO-001", "sha256": "a" * 64},
        {"id": "EVT-DEMO-002", "sha256": "b" * 64},
    ],
}
DEMO_SHA256 = "f179fd89814a958a04b9fd740e789fd7f5c21a1bfbb8187820e3f1c21d40e62d"
CANONICAL_PYTHON = '''canonical_bytes = json.dumps(
    value, sort_keys=True, separators=(",", ":"),
    ensure_ascii=True, allow_nan=False,
).encode("utf-8")
digest = hashlib.sha256(canonical_bytes).hexdigest()'''
VERIFY_RECEIPT_PYTHON = '''import base64
import json
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

def decode(value):
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))

# Generic local example: use an envelope and the trusted public authority document.
envelope = json.loads(Path("demo-receipt.json").read_text(encoding="utf-8"))
authority = json.loads(Path("demo-attestation-key.json").read_text(encoding="utf-8"))
assert authority["algorithm"] == "Ed25519"
assert authority["signing_key_id"] == "vanta-disclosure-ed25519-2147"
assert envelope["signing_key_id"] == authority["signing_key_id"]
message = json.dumps(
    envelope["receipt"], sort_keys=True, separators=(",", ":"),
    ensure_ascii=True, allow_nan=False,
).encode("utf-8")
key = Ed25519PublicKey.from_public_bytes(decode(authority["public_key_b64u"]))
key.verify(decode(envelope["signature"]), message)'''

CONTRACT = {
    "service": "VANTA / ROOT OF TRUST", "version": "1.0",
    "case": {"case_id": CASE_ID, "title": "Dossier SILENCE", "subject": "MIRA-07", "historical_date": "2147-10-16 UTC"},
    "jwt": {
        "header": JWT_HEADER,
        "claims": {"iss": ISSUER, "aud": AUDIENCE, "sub": SUBJECT, "case_id": CASE_ID},
        "scope": {"type": "nonempty unique array of exact strings", "known": ["case:read", "disclosure:publish"],
                  "combined": "Both known scopes may coexist. proof_sha256 is required whenever disclosure:publish is present."},
        "time": {"iat": "integer Unix UTC; now - 600 <= iat <= now + 30", "exp": "integer Unix UTC; strictly greater than now",
                 "lifetime": "0 < exp - iat <= 600", "clock": "actual server clock, not historical 2147 time"},
        "proof_sha256": "64 lowercase hex characters; required iff disclosure:publish occurs in scope",
        "key": "VANTA-ROOT-AUDIT key material; decode canonical unpadded Base64URL to exactly 32 HMAC key bytes",
        "limits": "4096 ASCII JWT bytes; exact header and claims only; duplicate members and noninteger numbers rejected",
        "issuance": "No JWT issuing endpoint. Mandates are issued by the accredited request authority.",
    },
    "routes": [
        {"method": "GET", "path": "/", "scope": "public"},
        {"method": "GET", "path": "/api/public/contract", "scope": "public"},
        {"method": "GET", "path": "/api/public/policy", "scope": "public"},
        {"method": "GET", "path": "/api/public/attestation-key", "scope": "public"},
        {"method": "GET", "path": "/healthz", "scope": "public"},
        {"method": "GET", "path": "/api/authority/verify", "scope": "case:read",
         "response": "status AUTHORITY_VERIFIED, case_id, expires_at (Unix UTC), valid_for_ms; no token or backend session"},
        {"method": "GET", "path": f"/api/cases/{CASE_ID}/events", "scope": "case:read"},
        {"method": "GET", "path": f"/api/cases/{CASE_ID}/events/<event_id>", "scope": "case:read"},
        {"method": "POST", "path": "/api/disclosures", "scope": "disclosure:publish", "body": {"manifest": "VANTA-PROOF/1 object"}},
    ],
    "manifest": {
        "exact_fields": {"schema": SCHEMA, "case_id": CASE_ID, "assertion": ASSERTION, "evidence": "array of 1..12 entries"},
        "evidence": "Each entry has exactly id and sha256. ASCII IDs [A-Z0-9-]{1,64}; strictly increasing unique IDs; digest is 64 lowercase hex characters.",
        "canonicalization": {"name": "VANTA-PROOF/1 Python compact JSON (not RFC 8785)", "python": CANONICAL_PYTHON,
                             "encoding": "UTF-8; ASCII escaped Unicode; no BOM, prefix or trailing newline",
                             "events": "Canonicalize the entire original event object excluding its sha256 member.",
                             "receipt": "Canonicalize receipt only, including findings and flag, excluding outer signature and signing_key_id."},
        "neutral_vector": {"value": DEMO_VECTOR, "sha256": DEMO_SHA256, "valid_silence_proof": False},
    },
    "limits": {"request_body_bytes": 16384, "evidence_count": 12, "authorization_header_bytes": 4103},
    "errors": [
        {"status": status, "code": code} for status, code in [
            (401, "INVALID_TOKEN"), (401, "INVALID_SIGNATURE"), (403, "INSUFFICIENT_SCOPE"),
            (400, "INVALID_MANIFEST"), (409, "MANIFEST_HASH_MISMATCH"),
            (409, "EVIDENCE_DIGEST_MISMATCH"), (400, "UNKNOWN_EVIDENCE"),
            (422, "ASSERTION_NOT_ESTABLISHED"), (413, "REQUEST_TOO_LARGE"),
            (415, "UNSUPPORTED_MEDIA_TYPE"), (404, "NOT_FOUND"), (500, "INTERNAL_ERROR"),
        ]
    ],
    "attestation": {"algorithm": "Ed25519", "key_route": "/api/public/attestation-key", "storage": "success response only; no receipt index or lookup",
                    "verification_python": VERIFY_RECEIPT_PYTHON},
}

POLICY = {
    "assertion": ASSERTION,
    "description": "SILENCE_COVERUP : évaluer la concordance entre une décision de gouvernance d'identité, ses effets opérationnels et l'information diffusée à son sujet.",
    "criteria": [
        "Attribution documentaire : les éléments doivent permettre d'identifier la décision et le périmètre dont ils rendent compte.",
        "Continuité de provenance : les références d'identité, d'incident et de ressources doivent former un dossier corrélable.",
        "Cohérence temporelle : une observation doit être appréciée à la date où elle a été produite et dans le contexte de la décision examinée.",
        "Portée de l'assertion : le dossier doit établir un écart documenté entre le traitement administratif, la situation opérationnelle et l'information communiquée.",
        "Intégrité : seules les pièces du dossier autorisé sont admises ; leurs empreintes sont recalculées depuis les événements originaux.",
    ],
    "additional_evidence": "Toute pièce soumise participe à l'évaluation de cohérence. L'authenticité d'un document ne suffit pas à établir sa pertinence pour l'assertion. Les références, les états et la chronologie des documents doivent rester compatibles avec le périmètre attesté.",
    "authority_boundary": "Une autorisation HS256 valide permet de demander l'évaluation. Seule une preuve valide déclenche la certification Ed25519 par le service.",
    "scope_of_attestation": "VANTA atteste l'origine et la cohérence du dossier issu de son registre fictif. Aucune libération ni publication externe.",
}
