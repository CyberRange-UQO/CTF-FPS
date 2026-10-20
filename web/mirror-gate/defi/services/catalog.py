"""Ordinary document catalog, served independently on port 9080."""

from flask import Flask, Response, jsonify
from werkzeug.exceptions import HTTPException


def create_app():
    app = Flask(__name__)
    app.json.ensure_ascii = False

    @app.after_request
    def classification(response):
        response.headers["X-Vanta-Classification"] = "INTERNAL"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/healthz")
    def health():
        return jsonify(status="ok", service="DOCUMENT CATALOG")

    @app.get("/")
    def index():
        return jsonify(
            service="DOCUMENT CATALOG",
            version="2.6",
            classification="INTERNAL",
            resources=["/public/bulletin", "/public/connectors", "/public/retention"],
        )

    @app.get("/public/bulletin")
    def bulletin():
        return Response(
            "VANTA//SYSTEMS — BULLETIN DE MAINTENANCE\n"
            "Document : DOC-017 / Révision : 17\n"
            "Publié le 16/10/2147 à 09:16 — Noctis-9\n"
            "Classification : INTERNAL\n\n"
            "La maintenance documentaire de 08:30 à 08:50 est terminée.\n"
            "Les sources ordinaires sont disponibles en consultation HTTP.\n"
            "Les opérateurs peuvent prévisualiser les documents depuis MIRROR GATE.\n"
            "La récupération s'effectue côté serveur ; aucun accès direct au réseau\n"
            "de la source n'est nécessaire sur le poste de l'opérateur.\n\n"
            "En cas de réponse 404, vérifiez le chemin publié par la source.\n"
            "En cas de délai dépassé, consultez le journal avant de relancer.\n",
            content_type="text/plain; charset=utf-8",
        )

    @app.get("/public/connectors")
    def connectors():
        return jsonify(
            document="DOC-024",
            revision=6,
            classification="INTERNAL",
            updated_at="2147-10-16T09:08:00",
            source="mirror-catalog",
            connectors=[
                {
                    "id": "MAINTENANCE",
                    "version": "2.6",
                    "path": "/public/bulletin",
                    "status": "INDEXED",
                },
                {
                    "id": "RETENTION",
                    "version": "1.4",
                    "path": "/public/retention",
                    "status": "INDEXED",
                },
            ],
            note="Ce registre couvre uniquement les sources documentaires standard.",
        )

    @app.get("/public/retention")
    def retention():
        return Response(
            "VANTA//SYSTEMS — CONSERVATION DOCUMENTAIRE\n"
            "Document : DOC-031 / Révision : 4\n"
            "En vigueur le 16/10/2147 à 08:52\n\n"
            "Bulletins de maintenance : 30 jours après remplacement.\n"
            "Registres de connecteurs : dernière révision approuvée.\n"
            "Journaux de synchronisation : 90 jours.\n\n"
            "L'index conserve les métadonnées des sources non documentaires.\n"
            "Leur cycle de vie reste géré par le service d'origine. Une suppression\n"
            "dans un registre ne constitue pas une instruction d'arrêt de service.\n",
            content_type="text/plain; charset=utf-8",
        )

    @app.errorhandler(HTTPException)
    def error_response(error):
        return jsonify(
            error=f"HTTP_{error.code}", message="Ressource documentaire indisponible."
        ), error.code

    return app
