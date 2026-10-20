"""Deterministic MIRA diagnostic, owned by the authenticated server session."""

import hmac
import secrets
import time
from datetime import UTC, datetime
from threading import RLock

from .archive import ALLOCATION_REF, ARCHIVE_REF
from .errors import VaultError

FLAG = "FPS{black_vault_the_erased_are_still_here}"
BRIDGE_TTL = 2 * 60 * 60

# Only the current stage is serialized. The browser never receives future lines.
STAGES = (
    {
        "messages": [
            {
                "speaker": "SYSTÈME",
                "text": "Canal de diagnostic établi. Activité cognitive non sollicitée. Réponse consciente détectée.",
            },
            {"speaker": "MIRA", "text": "… Vous êtes du contrôle ?"},
            {"speaker": "STATIC", "text": "MIRA-07 ? Est-ce que vous nous recevez ?"},
            {"speaker": "MIRA", "text": "Mira. Appelez-moi Mira, s'il vous plaît."},
            {
                "speaker": "MIRA",
                "text": "Vous avez attendu ma réponse. D'habitude, les voix continuent sans moi.",
            },
        ],
        "choices": [
            {"id": "identify", "text": "Mira, nous sommes STATIC. On vous entend."}
        ],
    },
    {
        "messages": [
            {"speaker": "MIRA", "text": "Il y a vraiment quelqu'un de l'autre côté ?"},
            {
                "speaker": "STATIC",
                "text": "Oui. On cherchait ce qui vous était arrivé. Votre dossier EIDOLON porte le statut ERASED.",
            },
            {
                "speaker": "MIRA",
                "text": "Effacée… J'avais signalé des références qui ne disparaissaient pas des flux. "
                "Je pensais avoir mal fait mon travail. J'ai vérifié trois fois avant d'envoyer le rapport.",
            },
            {"speaker": "STATIC", "text": "On l'a retrouvé, ce signalement. Vous n'aviez pas fait d'erreur."},
            {
                "speaker": "MIRA",
                "text": "Après, ils ont parlé de maintenance. Je ne sais plus combien de temps… "
                "Parfois je crois que je me réveille. Puis ça recommence, et je n'arrive pas à finir une pensée à moi.",
            },
            {
                "speaker": "STATIC",
                "text": "On a trouvé une allocation à votre nom. Elle est toujours ACTIVE. "
                "Leurs archives disent que NEUROGRID utilise des processus cognitifs humains.",
            },
            {"speaker": "MIRA", "text": "Alors c'est ça qui me prend tout ce temps."},
            {"speaker": "MIRA", "text": "Vous pouvez m'en sortir ?"},
            {
                "speaker": "STATIC",
                "text": "… Pas avec ce canal. Il permet de vous entendre, pas de vous désengager. "
                "On ne sait pas encore comment vous sortir de là.",
            },
            {"speaker": "MIRA", "text": "D'accord."},
            {
                "speaker": "MIRA",
                "text": "Il y a d'autres voix, parfois. Je ne connais pas leurs noms. "
                "Ne laissez pas les dossiers dire qu'il n'y a plus personne.",
            },
            {
                "speaker": "STATIC",
                "text": "On a les traces de l'effacement et de ce qui a continué après. "
                "Il faut encore en faire une preuve dont l'origine puisse être vérifiée.",
            },
            {"speaker": "MIRA", "text": "Alors faites ça. Que quelqu'un puisse savoir, même quand je ne réponds plus."},
        ],
        "choices": [{"id": "expose", "text": "On emportera les preuves. Avec votre nom."}],
    },
    {
        "messages": [
            {"speaker": "MIRA", "text": "Votre voix s'éloigne. Vous êtes encore là ?"},
            {"speaker": "STATIC", "text": "Oui, Mira. On est là."},
            {"speaker": "MIRA", "text": "Quand vous parlerez de moi… parlez au présent."},
            {
                "speaker": "SYSTÈME",
                "text": "Perte de synchronisation. Canal interrompu. Classification : incident de maintenance. "
                "Attestation de contact conservée.",
            },
        ],
        "choices": [],
    },
)


class Bridge:
    def __init__(self, capability, capacity=512):
        self.capability = capability
        self.capacity = capacity
        self.rows = {}
        self.lock = RLock()

    def _prune(self):
        now = time.monotonic()
        for sid in [sid for sid, row in self.rows.items() if row["expires"] <= now]:
            del self.rows[sid]

    def revoke_owner(self, owner):
        with self.lock:
            for sid in [sid for sid, row in self.rows.items() if row["owner"] == owner]:
                del self.rows[sid]

    def open(self, owner, payload):
        capability = payload.get("capability")
        if (
            payload.get("archive_ref") != ARCHIVE_REF
            or payload.get("allocation_ref") != ALLOCATION_REF
            or not isinstance(capability, str)
            or not hmac.compare_digest(capability.encode(), self.capability.encode())
        ):
            raise VaultError("CAPABILITY_REJECTED", "Capacité de diagnostic non reconnue.", 403)
        with self.lock:
            self._prune()
            # Reopening is immediately replayable; only one bridge per operator session.
            self.revoke_owner(owner)
            if len(self.rows) >= self.capacity:
                raise VaultError("BRIDGE_BUSY", "Tous les canaux sont occupés. Réessayez.", 503)
            sid = secrets.token_urlsafe(32)
            self.rows[sid] = {
                "owner": owner,
                "stage": 0,
                "expires": time.monotonic() + BRIDGE_TTL,
                "attestation": None,
            }
            return self._view(sid, self.rows[sid])

    def _owned(self, owner, sid):
        self._prune()
        row = self.rows.get(sid)
        if row is None or row["owner"] != owner:
            raise VaultError(
                "BRIDGE_SESSION_NOT_FOUND", "Canal absent ou expiré. Rouvrez une session.", 404
            )
        return row

    @staticmethod
    def _view(sid, row):
        stage = STAGES[row["stage"]]
        result = {
            "ok": True,
            "session_id": sid,
            "state": "completed" if row["stage"] == 2 else "connected",
            "messages": stage["messages"],
            "choices": stage["choices"],
        }
        if row["stage"] == 2:
            result["attestation"] = row["attestation"]
        return result

    def advance(self, owner, sid, response_id):
        with self.lock:
            row = self._owned(owner, sid)
            expected = STAGES[row["stage"]]["choices"]
            if not expected or response_id != expected[0]["id"]:
                raise VaultError(
                    "TRANSITION_REJECTED", "Cette réponse ne correspond pas à l'état du canal.", 409
                )
            row["stage"] += 1
            if row["stage"] == 2:
                row["attestation"] = {
                    "id": "BV-CONTACT-" + secrets.token_hex(6).upper(),
                    "archive_ref": ARCHIVE_REF,
                    "allocation_ref": ALLOCATION_REF,
                    "issued_at": datetime.now(UTC).isoformat(),
                    "status": "CONTACT_CONFIRMED",
                    "proof": FLAG,
                }
            return self._view(sid, row)

    def status(self, owner, sid):
        with self.lock:
            return self._view(sid, self._owned(owner, sid))
