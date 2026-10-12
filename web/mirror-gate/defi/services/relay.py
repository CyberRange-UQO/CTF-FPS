"""Classified NG-R relay, served independently on port 9090."""

import os

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

# These opaque identifiers belong only to NG-R. The portal stores correlation
# metadata, never allocation handles. Registry discovery does not enumerate them.
MIRA_ALLOCATION_HANDLE = "ALLOC-7C29-D8F4-912A"
ALLOCATION_RECORDS = {
    "ALLOC-2B60-A1E9-63FC": {
        "resource_context": "DOCUMENT_CACHE",
        "allocation_state": "ACTIVE",
        "administrative_note": "Allocation régulière. Aucun écart administratif signalé.",
    },
    MIRA_ALLOCATION_HANDLE: {
        "allocation_id": "NG-R-1057",
        "source_identity": "MIRA-07 / EID-1057",
        "eidolon_status": "ERASED",
        "allocation_state": "ACTIVE",
        "termination": "NOT SCHEDULED",
        "hold_directive": "SIL-4/2147-07",
        "archive_reference": "BV-2147-1057",
        "administrative_note": (
            "La révocation administrative de l'identité source n'autorise pas l'arrêt "
            "de l'allocation. Maintien de service confirmé par directive restreinte "
            "SIL-4/2147-07."
        ),
    },
    "ALLOC-A815-60C3-F27E": {
        "resource_context": "CONNECTOR_STATE",
        "allocation_state": "ACTIVE",
        "administrative_note": "Allocation régulière. Aucun écart administratif signalé.",
    },
}
TRACE_RECORDS = {
    "TRC-2147-0912": {
        "trace_id": "TRC-2147-0912",
        "synchronization_job": "SYNC-NGR-2147",
        "recorded_at": "2147-10-16T09:12:00",
        "operation": "IDENTITY_SYNC",
        "source_state": "ERASED",
        "allocation_state": "ACTIVE",
        "allocation_handle": MIRA_ALLOCATION_HANDLE,
    },
}


def create_app():
    app = Flask(__name__)
    app.json.ensure_ascii = False
    flag = os.environ.get("MIRROR_FLAG")
    if not flag or not flag.startswith("FPS{") or not flag.endswith("}"):
        raise RuntimeError("MIRROR_FLAG must be provided to the internal relay")

    @app.after_request
    def classification(response):
        response.headers["X-Vanta-Classification"] = "RESTRICTED"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/healthz")
    def health():
        return jsonify(status="ok", service="NG-R RELAY")

    @app.get("/")
    def index():
        return jsonify(
            service="NG-R RELAY",
            version="1.5",
            classification="INTERNAL / RESTRICTED",
            status="ONLINE",
            resources=["/v1/status", "/v1/traces", "/v1/allocations"],
            resource_descriptions={
                "/v1/status": "Operational supervision",
                "/v1/traces": "Synchronization provenance lookup by correlation identifier",
                "/v1/allocations": "Resource allocation registry and handle lookup conventions",
            },
        )

    @app.get("/v1/status")
    def status():
        return jsonify(
            service="NG-R RELAY",
            classification="RESTRICTED",
            status="ONLINE",
            consultation="AVAILABLE",
            allocation_count=len(ALLOCATION_RECORDS),
            trace_count=len(TRACE_RECORDS),
            last_sync="2147-10-16T09:12:00",
            scope="NG-R",
        )

    @app.get("/v1/allocations")
    def allocations():
        return jsonify(
            service="NG-R Allocation Registry",
            classification="RESTRICTED",
            registry_state="ONLINE",
            allocation_count=len(ALLOCATION_RECORDS),
            lookup="/v1/allocations/{handle}",
            enumeration="DISABLED",
            description=(
                "Allocation lookup by internal handle. Synchronization traces provide "
                "the associated allocation_handle and allocation_href."
            ),
        )

    @app.get("/v1/traces")
    def traces():
        return jsonify(
            service="NG-R Trace Registry",
            classification="RESTRICTED",
            registry_state="ONLINE",
            lookup="/v1/traces/{trace_id}",
            identifier_type="CORRELATION_ID",
            description="Synchronization trace lookup by correlation identifier",
        )

    @app.get("/v1/traces/<trace_id>")
    def trace(trace_id):
        record = TRACE_RECORDS.get(trace_id)
        if record is None:
            return jsonify(
                error="TRACE_NOT_FOUND", message="Trace de synchronisation inconnue."
            ), 404
        return jsonify(
            classification="RESTRICTED",
            **record,
            allocation_href=f"/v1/allocations/{record['allocation_handle']}",
        )

    @app.get("/v1/allocations/<handle>")
    def allocation(handle):
        record = ALLOCATION_RECORDS.get(handle)
        if record is None:
            return jsonify(error="ALLOCATION_NOT_FOUND", message="Allocation inconnue."), 404
        payload = {"allocation_handle": handle, "classification": "RESTRICTED", **record}
        if handle == MIRA_ALLOCATION_HANDLE:
            payload["flag"] = flag
        return jsonify(payload)

    @app.errorhandler(HTTPException)
    def error_response(error):
        return jsonify(
            error=f"HTTP_{error.code}", message="Ressource du relais indisponible."
        ), error.code

    return app
