"""Fictional corporate identity and private incident content; never static assets."""

from werkzeug.security import generate_password_hash

USER = {
    "username": "contractor.073",
    "password_hash": generate_password_hash("PHANTOM-073-2147"),
    "sub": "contractor-073",
    "display_id": "C-073",
    "division": "FIELD_SUPPORT",
    "clearance": "TECH-0",
}


def confidential_report(proof_id):
    return {
        "id": "SEC-2147-089",
        "title": "Incident SEC-2147-089 — Identity Integrity Monitoring",
        "classification": "CIPHER / RESTRICTED / TECH-2",
        "declarant": "MIRA-07 / EID-1057",
        "assignment": "EIDOLON Data Integrity — sous-traitance",
        "status": "CLOSED / RESTRICTED",
        "events": [
            {
                "date": "14/10/2147",
                "label": "Signalement d'intégrité",
                "detail": (
                    "MIRA-07, sous-traitante affectée au suivi de la qualité et de l'intégrité "
                    "des données EIDOLON, signale des dossiers citoyens révoqués dont les "
                    "références subsistent dans des flux internes de consommation de ressources. "
                    "Hypothèse initiale de la déclarante : anomalie de synchronisation ou de "
                    "comptabilisation. La nature de ces flux ne lui est pas connue."
                ),
            },
            {
                "date": "15/10/2147",
                "label": "Transfert de périmètre",
                "detail": (
                    "Signalement corrélé au périmètre classifié NG-R. Retrait du circuit "
                    "standard et transfert à CIPHER. Communication avec la déclarante suspendue."
                ),
            },
            {
                "date": "16/10/2147",
                "label": "Clôture sous directive",
                "detail": (
                    "Incident clôturé sous la directive SIL-4/2147-07. "
                    "Justification détaillée classifiée. Aucune diffusion au circuit ordinaire."
                ),
            },
        ],
        "proof_id": proof_id,
    }
