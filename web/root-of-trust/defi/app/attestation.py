import secrets
import time

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .canonical import canonical_bytes
from .encoding import b64u

SIGNING_KEY_ID = "vanta-disclosure-ed25519-2147"
_FLAG = "FPS{root_of_trust_signed_the_truth}"


class AttestationAuthority:
    def __init__(self, seed):
        self._private = Ed25519PrivateKey.from_private_bytes(seed)

    def public_document(self):
        raw = self._private.public_key().public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )
        return {
            "signing_key_id": SIGNING_KEY_ID, "algorithm": "Ed25519",
            "encoding": "base64url-no-padding", "format": "raw-32-bytes",
            "public_key_b64u": b64u(raw),
            "signed_content": "canonical JSON bytes of receipt only; signature and signing_key_id are outside receipt",
        }

    def issue(self, manifest, proof_digest):
        # Caller must complete authorization, integrity and semantic evaluation.
        # Receipts have no storage or retrieval endpoint.
        receipt = {
            "schema": "VANTA-DISCLOSURE/1", "receipt_id": secrets.token_urlsafe(24),
            "case_id": manifest["case_id"], "assertion": manifest["assertion"],
            "proof_sha256": proof_digest,
            "evidence_ids": [item["id"] for item in manifest["evidence"]],
            "issued_at": int(time.time()), "decision": "CERTIFIED_DISCLOSURE",
            "findings": [
                "Effacement administratif intentionnel établi par le registre.",
                "Allocation NG-R active après l'effacement de l'identité.",
                "Explication publique SYNC_ERROR rattachée au même incident.",
                "Origine et cohérence des événements traitées par le service VANTA.",
            ],
            "flag": _FLAG,
        }
        return {
            "receipt": receipt,
            "signature": b64u(self._private.sign(canonical_bytes(receipt))),
            "signing_key_id": SIGNING_KEY_ID,
        }
