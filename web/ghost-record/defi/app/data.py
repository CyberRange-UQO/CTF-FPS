"""Jeu de données fictif, en lecture seule : aucune persistance nécessaire."""

from datetime import date
from types import MappingProxyType

USERS = MappingProxyType(
    {
        1: MappingProxyType(
            {
                "id": 1,
                "username": "runner.1042",
                "password_hash": (
                    "scrypt:32768:8:1$af0bcb21239818b3$"
                    "310c81f6afb2593896e3c506d6d6806e7dc909aeed5539c2e4a9553fe655b9663"
                    "dd557d6181c02194515ce1aeaa300b55af404afe9c5246aa1aab895a72efa77"
                ),
                "role": "CITIZEN",
                "record_id": 1042,
            }
        )
    }
)

# Le propriétaire 7 représente MIRA, dont le compte n'est plus actif.
# Aucun identifiant de connexion n'existe pour ce propriétaire.
RECORDS = MappingProxyType(
    {
        1042: MappingProxyType(
            {
                "id": 1042,
                "owner_user_id": 1,
                "alias": "runner.1042",
                "birth_date": date(2120, 8, 12),
                "status": "ACTIVE",
                "sector": "Noctis-9 / Secteur 03",
                "operation": None,
                "has_report": False,
                "summary": "Identité validée. Droits citoyens en vigueur. Aucune démarche en attente.",
            }
        ),
        1057: MappingProxyType(
            {
                "id": 1057,
                "owner_user_id": 7,
                "alias": "MIRA-07",
                "birth_date": date(2122, 4, 19),
                "status": "ERASED",
                "sector": "Noctis-9 / Secteur 07",
                "operation": "SILENCE",
                "has_report": True,
                "summary": (
                    "Enregistrement retiré du registre public. "
                    "Une pièce administrative subsiste dans les archives Legacy."
                ),
            }
        ),
    }
)

NOTIFICATIONS = (
    MappingProxyType(
        {
            "id": 1,
            "recipient_user_id": 1,
            "title": "Maintenance du registre d'identités / Secteur 07",
            "code": "MAINT-07",
            "body": (
                "La mise à jour SILENCE-4 du registre d'identités du secteur 07 est en cours. "
                "Des délais de synchronisation peuvent affecter certains services citoyens. "
                "Aucune démarche n'est requise. VANTA Systems vous remercie de votre compréhension."
            ),
            "status": "MAINTENANCE",
            "created_at": "16/10/2147 · 08:41",
        }
    ),
    MappingProxyType(
        {
            "id": 2,
            "recipient_user_id": 1,
            "title": "Identité synchronisée",
            "code": "EID-CITIZEN",
            "body": "Votre identité citoyenne est à jour. Vos services restent disponibles.",
            "status": "DELIVERED",
            "created_at": "16/10/2147 · 08:30",
        }
    ),
)
