"""Only ordinary archive metadata; no classified bodies or runtime secrets."""

from .archive import ARCHIVE_REF

ARCHIVE_META = {
    "ref": ARCHIVE_REF,
    "title": "Conservation d'un dossier d'intégrité",
    "identity": "EID-1057",
    "classification": "BLACK",
    "status": "RETAINED",
    "indexed": "16.10.2147 / 09:24",
    "public_count": 3,
    "sealed_count": 4,
    "sector": "Noctis-9",
}

PUBLIC_DOCUMENTS = [
    {
        "file": "summary.txt",
        "label": "Synthèse administrative",
        "code": "BV / 01",
        "kind": "Synthèse administrative",
    },
    {
        "file": "inventory.txt",
        "label": "Inventaire des compartiments",
        "code": "BV / 02",
        "kind": "Inventaire documentaire",
    },
    {
        "file": "migration-note.txt",
        "label": "Contrats de référence documentaire",
        "code": "KB-VAULT-021",
        "kind": "Note de procédure",
    },
]
