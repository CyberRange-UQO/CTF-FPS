"""Public operational snapshots; no classified allocation data."""

SOURCES = [
    {
        "id": "DOC-017",
        "title": "Bulletin de maintenance",
        "kind": "text/plain",
        "path": "/public/bulletin",
        "synced": "16/10/2147 · 09:16",
        "description": "Fenêtre de maintenance, état du service et consignes de reprise.",
    },
    {
        "id": "DOC-024",
        "title": "Registre des connecteurs",
        "kind": "application/json",
        "path": "/public/connectors",
        "synced": "16/10/2147 · 09:08",
        "description": "Versions et métadonnées des sources documentaires standard.",
    },
    {
        "id": "DOC-031",
        "title": "Politique de conservation",
        "kind": "text/plain",
        "path": "/public/retention",
        "synced": "16/10/2147 · 08:52",
        "description": "Durées de disponibilité et traitement des documents remplacés.",
    },
]

JOBS = [
    {
        "id": "SYNC-DOC-017",
        "time": "09:16",
        "scope": "DOCUMENTATION",
        "relay": "mirror-catalog",
        "classification": "INTERNAL",
        "state": "INDEXED",
        "note": "Bulletin de maintenance révisé. Version 17 intégrée à l'index documentaire.",
    },
    {
        "id": "SYNC-NGR-2147",
        "time": "09:12",
        "scope": "NG-R",
        "relay": "ng-r-relay",
        "correlation_id": "TRC-2147-0912",
        "classification": "RESTRICTED",
        "state": "METADATA ONLY",
        "note": (
            "MIRROR GATE conserve uniquement les métadonnées de cette synchronisation "
            "classifiée. Les détails de provenance demeurent sur le relais source ; "
            "ses ressources ne sont pas indexées dans le catalogue standard."
        ),
    },
    {
        "id": "SYNC-DOC-024",
        "time": "09:08",
        "scope": "CONNECTORS",
        "relay": "mirror-catalog",
        "classification": "INTERNAL",
        "state": "INDEXED",
        "note": "Registre des connecteurs ordinaires actualisé. Aucun changement de protocole.",
    },
    {
        "id": "SYNC-DOC-031",
        "time": "08:52",
        "scope": "RETENTION",
        "relay": "mirror-catalog",
        "classification": "INTERNAL",
        "state": "INDEXED",
        "note": "Politique de conservation documentaire reçue. Révision 4 en vigueur.",
    },
    {
        "id": "SYNC-EID-2147",
        "time": "08:40",
        "scope": "EIDOLON",
        "relay": "identity-index",
        "classification": "INTERNAL",
        "state": "ACKNOWLEDGED",
        "note": (
            "Lot de révocations administratives appliqué au registre d'identité. "
            "Accusé de traitement reçu."
        ),
    },
]
