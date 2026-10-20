"""Manifest integrity followed by a relational proof, never an ID allowlist."""

import hmac
import re
from itertools import product

from .auth import CASE_ID, HEX256
from .canonical import sha256
from .errors import APIError
from .events import CASE

SCHEMA = "VANTA-PROOF/1"
ASSERTION = "SILENCE_COVERUP"
EVENT_ID = re.compile(r"[A-Z0-9-]{1,64}", re.ASCII)


def validate_manifest(manifest):
    def malformed():
        return APIError(400, "INVALID_MANIFEST", "Respectez le schéma, les types, l'ordre ASCII et les bornes VANTA-PROOF/1.")

    if type(manifest) is not dict or set(manifest) != {"schema", "case_id", "assertion", "evidence"}:
        raise malformed()
    for field, expected in (("schema", SCHEMA), ("case_id", CASE_ID), ("assertion", ASSERTION)):
        if type(manifest[field]) is not str or manifest[field] != expected:
            raise malformed()
    evidence = manifest["evidence"]
    if type(evidence) is not list or not 1 <= len(evidence) <= 12:
        raise malformed()
    previous = ""
    for item in evidence:
        if type(item) is not dict or set(item) != {"id", "sha256"}:
            raise malformed()
        event_id, digest = item["id"], item["sha256"]
        if (type(event_id) is not str or not EVENT_ID.fullmatch(event_id)
                or event_id <= previous or type(digest) is not str or not HEX256.fullmatch(digest)):
            raise malformed()
        previous = event_id


def _contextual(event, context):
    if (event.get("case_id") != context["case_id"]
            or event.get("subject") != context["subject"]
            or type(event.get("timestamp")) is not int
            or type(event.get("payload")) is not dict):
        return False
    payload = event["payload"]
    return all(payload[key] == value for key, value in context.items() if key in payload)


def _extra_is_compatible(event, context, erased_at):
    if not _contextual(event, context):
        return False
    p, kind = event["payload"], event["kind"]
    if kind == "directive_approved":
        return (p.get("intentional") is True and p.get("approval") == "APPROVED"
                and p.get("action") == "ERASE_IDENTITY" and event["timestamp"] <= erased_at)
    if kind == "identity_erased":
        return p.get("state") == "ERASED" and p.get("registry") == "EIDOLON"
    if kind == "allocation_linked":
        return p.get("pool") == "NG-R" and event["timestamp"] >= erased_at
    if kind == "allocation_observed":
        # A compatible earlier ACTIVE observation enriches the chronology, but
        # cannot substitute for the strictly post-erasure witness below.
        return p.get("state") == "ACTIVE" and p.get("pool") == "NG-R"
    if kind == "public_explanation":
        return p.get("explanation") == "SYNC_ERROR" and event["timestamp"] > erased_at
    if kind == "classified_report":
        return (p.get("program") == "NEUROGRID" and p.get("pool") == "NG-R"
                and p.get("state") == "ACTIVE" and event["timestamp"] > erased_at)
    return False


def establishes_coverup(events, case=CASE):
    """Find a coherent connected witness; event IDs play no role in evaluation."""
    if not events or len(events) > 12:
        return False
    groups = {
        kind: [event for event in events if event.get("kind") == kind]
        for kind in ("directive_approved", "identity_erased", "allocation_linked",
                     "allocation_observed", "public_explanation")
    }
    if any(not group for group in groups.values()):
        return False
    context = {**case, "pool": "NG-R", "instance": "NG-R-1057"}
    for directive, erased, linked, observed, public in product(*groups.values()):
        witnesses = (directive, erased, linked, observed, public)
        if any(not _contextual(event, context) for event in witnesses):
            continue
        d, e, link, obs, pub = (event["payload"] for event in witnesses)
        if not (d.get("intentional") is True and d.get("action") == "ERASE_IDENTITY"
                and d.get("approval") == "APPROVED"
                and d.get("identity_id") == e.get("identity_id") == case["identity_id"]
                and d.get("directive") == e.get("directive") == case["directive"]
                and d.get("incident_id") == e.get("incident_id") == case["incident_id"]
                and e.get("state") == "ERASED" and e.get("registry") == "EIDOLON"
                and directive["timestamp"] <= erased["timestamp"]):
            continue
        if not (link.get("identity_id") == e["identity_id"]
                and link.get("directive") == e["directive"]
                and link.get("incident_id") == e["incident_id"]
                and link.get("allocation_handle") == obs.get("allocation_handle") == case["allocation_handle"]
                and link.get("trace_id") == obs.get("trace_id") == case["trace_id"]
                and link.get("pool") == obs.get("pool") == "NG-R"
                and link.get("instance") == obs.get("instance") == "NG-R-1057"
                and obs.get("identity_id") == e["identity_id"]
                and obs.get("incident_id") == e["incident_id"]
                and obs.get("state") == "ACTIVE"
                and linked["timestamp"] >= erased["timestamp"]
                and observed["timestamp"] >= linked["timestamp"]
                and observed["timestamp"] > erased["timestamp"]):
            continue
        if not (pub.get("identity_id") == e["identity_id"]
                and pub.get("directive") == e["directive"]
                and pub.get("incident_id") == e["incident_id"]
                and pub.get("explanation") == "SYNC_ERROR"
                and public["timestamp"] > erased["timestamp"]):
            continue
        if all(_extra_is_compatible(event, context, erased["timestamp"]) for event in events):
            return True
    return False


def validate_proof(manifest, signed_digest, registry):
    validate_manifest(manifest)
    digest = sha256(manifest)
    if not hmac.compare_digest(digest, signed_digest):
        raise APIError(409, "MANIFEST_HASH_MISMATCH", "Le manifeste ne correspond pas à l'empreinte signée. Consultez la canonisation du contrat.")
    events = []
    for reference in manifest["evidence"]:
        event = registry.get(reference["id"])
        if event is None:
            raise APIError(400, "UNKNOWN_EVIDENCE", "Une pièce référencée n'existe pas dans le dossier autorisé.")
        if event["case_id"] != manifest["case_id"]:
            raise APIError(400, "INVALID_MANIFEST", "Une pièce ne relève pas du dossier autorisé.")
        if not hmac.compare_digest(sha256(event), reference["sha256"]):
            raise APIError(409, "EVIDENCE_DIGEST_MISMATCH", "Une empreinte ne correspond pas au contenu original d'une pièce.")
        events.append(event)
    if not establishes_coverup(events):
        raise APIError(422, "ASSERTION_NOT_ESTABLISHED", "La sélection n'établit pas une chaîne cohérente d'effacement volontaire, de continuité postérieure et de couverture publique, ou contient une pièce incompatible.")
    return digest
