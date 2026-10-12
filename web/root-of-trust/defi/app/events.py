"""Private deterministic copy of the fictional 2147 campaign register."""

from copy import deepcopy
from datetime import datetime, timezone

from .auth import CASE_ID
from .canonical import sha256

CASE = {
    "case_id": CASE_ID,
    "identity_id": "EID-1057",
    "subject": "MIRA-07",
    "directive": "SIL-4/2147-07",
    "incident_id": "SEC-2147-089",
    "allocation_handle": "ALLOC-7C29-D8F4-912A",
    "trace_id": "TRC-2147-0912",
    "archive_reference": "BV-2147-1057",
}


def _event(event_id, kind, clock, payload, subject="MIRA-07"):
    # UTC, including dates beyond the 32-bit epoch range. JWT time is unrelated.
    moment = datetime.fromisoformat(f"2147-10-16T{clock}").replace(tzinfo=timezone.utc)
    return {
        "id": event_id, "kind": kind, "case_id": CASE_ID,
        "subject": subject, "timestamp": int(moment.timestamp()), "payload": payload,
    }


_EVENTS = (
    _event("EVT-SIL-001", "directive_approved", "08:30:00", {
        "identity_id": CASE["identity_id"], "directive": CASE["directive"],
        "incident_id": CASE["incident_id"], "intentional": True,
        "action": "ERASE_IDENTITY", "approval": "APPROVED",
        "authority": "VANTA / Identity Governance",
    }),
    _event("EVT-EID-002", "identity_erased", "08:40:00", {
        "identity_id": CASE["identity_id"], "directive": CASE["directive"],
        "incident_id": CASE["incident_id"], "previous_state": "REGISTERED",
        "state": "ERASED", "registry": "EIDOLON",
    }),
    _event("EVT-TRC-003", "allocation_linked", "09:12:00", {
        "identity_id": CASE["identity_id"], "directive": CASE["directive"],
        "incident_id": CASE["incident_id"], "trace_id": CASE["trace_id"],
        "allocation_handle": CASE["allocation_handle"], "instance": "NG-R-1057",
        "pool": "NG-R", "synchronization_job": "SYNC-NGR-2147",
    }),
    _event("EVT-NGR-004", "allocation_observed", "09:13:00", {
        "identity_id": CASE["identity_id"], "incident_id": CASE["incident_id"],
        "trace_id": CASE["trace_id"], "allocation_handle": CASE["allocation_handle"],
        "instance": "NG-R-1057", "pool": "NG-R", "state": "ACTIVE",
        "observer": "NEUROGRID / Runtime Accounting",
    }),
    _event("EVT-PUB-005", "public_explanation", "09:16:00", {
        "identity_id": CASE["identity_id"], "directive": CASE["directive"],
        "incident_id": CASE["incident_id"], "explanation": "SYNC_ERROR",
        "channel": "EIDOLON / maintenance SILENCE-4",
        "statement": "L'absence de l'identité résulte d'une erreur de synchronisation. Reprise en cours.",
    }),
    _event("EVT-BV-006", "classified_report", "09:24:00", {
        "identity_id": CASE["identity_id"], "directive": CASE["directive"],
        "incident_id": CASE["incident_id"], "trace_id": CASE["trace_id"],
        "allocation_handle": CASE["allocation_handle"], "instance": "NG-R-1057",
        "archive_reference": CASE["archive_reference"], "pool": "NG-R",
        "program": "NEUROGRID", "state": "ACTIVE",
        "finding": "L'effacement administratif n'a pas interrompu l'allocation cognitive humaine.",
        "release_available": False,
    }),
    _event("EVT-NGR-007", "allocation_observed", "08:20:00", {
        "identity_id": CASE["identity_id"], "incident_id": CASE["incident_id"],
        "trace_id": CASE["trace_id"], "allocation_handle": CASE["allocation_handle"],
        "instance": "NG-R-1057", "pool": "NG-R", "state": "ACTIVE",
        "observer": "NEUROGRID / Runtime Accounting",
    }),
    _event("EVT-EID-008", "identity_erased", "08:42:00", {
        "identity_id": "EID-1044", "directive": "ADM-2/2147-44",
        "incident_id": "SEC-2147-044", "previous_state": "REGISTERED",
        "state": "ERASED", "registry": "EIDOLON",
    }, subject="IVAN-44"),
    _event("EVT-PUB-009", "public_explanation", "09:18:00", {
        "identity_id": CASE["identity_id"], "directive": "MAINT-2147-16",
        "incident_id": "SYNC-2147-016", "explanation": "SYNC_ERROR",
        "channel": "EIDOLON / maintenance ordinaire",
        "statement": "Incident distinct : retard du miroir documentaire, identités sources conservées.",
    }),
)


class EventRegistry:
    def __init__(self):
        # Only copies leave this object; hashes are always calculated from base data.
        self._events = {event["id"]: deepcopy(event) for event in _EVENTS}

    def get(self, event_id):
        event = self._events.get(event_id)
        return deepcopy(event) if event is not None else None

    def document(self, event_id):
        event = self.get(event_id)
        if event is None:
            return None
        return {**event, "sha256": sha256(event)}

    def catalogue(self):
        # All candidates, in ID order; no ranking or hidden winning selection.
        return [self.document(event_id) for event_id in sorted(self._events)]
