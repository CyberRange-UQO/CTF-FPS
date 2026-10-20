"""Positive NG-R JSON/data checks with a fixture flag, without HTTP or SSRF."""

import argparse
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--correlation-id", required=True, help="ID from the portal synchronization data"
    )
    args = parser.parse_args()
    # Also supports `python -` inside the relay image, which excludes tools/.
    base = Path.cwd() if __file__ == "<stdin>" else Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(base))
    from services.relay import ALLOCATION_RECORDS, TRACE_RECORDS, create_app

    fixture_flag = "FPS{contract_fixture_only}"
    with patch.dict(os.environ, {"MIRROR_FLAG": fixture_flag}):
        app = create_app()
    client = app.test_client()

    def get(path):
        response = client.get(path)
        assert response.status_code == 200, path
        assert response.is_json and isinstance(response.json, dict), path
        assert response.headers["X-Vanta-Classification"] == "RESTRICTED", path
        return response.json

    discovered = get("/")
    assert discovered["resources"] == ["/v1/status", "/v1/traces", "/v1/allocations"]
    status = get("/v1/status")
    trace_registry = get("/v1/traces")
    allocation_registry = get("/v1/allocations")
    assert trace_registry["lookup"] == "/v1/traces/{trace_id}"
    assert allocation_registry["lookup"] == "/v1/allocations/{handle}"
    assert allocation_registry["enumeration"] == "DISABLED"
    assert (
        allocation_registry["allocation_count"]
        == status["allocation_count"]
        == len(ALLOCATION_RECORDS)
    )
    assert status["trace_count"] == len(TRACE_RECORDS)
    for body in (discovered, status, trace_registry, allocation_registry):
        serialized = json.dumps(body)
        assert fixture_flag not in serialized
        assert "MIRA-07" not in serialized and "EID-1057" not in serialized
        assert all(handle not in serialized for handle in ALLOCATION_RECORDS)
    print("OK index, supervision et registres JSON sans handles énumérés")

    trace = get(f"/v1/traces/{args.correlation_id}")
    assert trace["trace_id"] == args.correlation_id
    assert trace["synchronization_job"] == "SYNC-NGR-2147"
    assert trace["recorded_at"] == "2147-10-16T09:12:00"
    handle = trace["allocation_handle"]
    assert handle in ALLOCATION_RECORDS and "1057" not in handle
    assert trace["allocation_href"] == f"/v1/allocations/{handle}"
    assert fixture_flag not in json.dumps(trace)
    assert "source_identity" not in trace
    print("OK référence de corrélation publique liée à une allocation opaque existante")

    allocation = get(trace["allocation_href"])
    assert allocation["allocation_handle"] == handle
    assert allocation["source_identity"] == "MIRA-07 / EID-1057"
    assert allocation["eidolon_status"] == trace["source_state"] == "ERASED"
    assert allocation["allocation_state"] == trace["allocation_state"] == "ACTIVE"
    assert allocation["termination"] == "NOT SCHEDULED"
    assert allocation["hold_directive"] == "SIL-4/2147-07"
    assert allocation["archive_reference"] == "BV-2147-1057"
    assert allocation["flag"] == fixture_flag
    for other_handle in ALLOCATION_RECORDS:
        if other_handle != handle:
            assert "flag" not in get(f"/v1/allocations/{other_handle}")
    assert all(not key.startswith("NG-R-") for key in ALLOCATION_RECORDS)
    print("OK fiche et continuité narrative avec preuve de fixture uniquement")
    print("Contrat interne contrôlé par client Flask ; aucun HTTP, SSRF ou flag réel récupéré.")


if __name__ == "__main__":
    main()
