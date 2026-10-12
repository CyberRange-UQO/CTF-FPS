"""Ordinary V2 auth/catalog checks. Never bypass approval or retrieve an NG-R resource."""

import argparse
import json
import urllib.error
import urllib.request
from html.parser import HTMLParser
from http.cookiejar import CookieJar
from urllib.parse import urlencode


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class TokenParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.token = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "input" and attributes.get("name") == "csrf_token":
            self.token = attributes.get("value")
        if tag == "meta" and attributes.get("name") == "csrf-token":
            self.token = attributes.get("content")


def token_from(body):
    parser = TokenParser()
    parser.feed(body)
    assert parser.token, "Jeton CSRF absent du formulaire ou de la page"
    return parser.token


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8082")
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")
    cookies = CookieJar()
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}), urllib.request.HTTPCookieProcessor(cookies), NoRedirect()
    )

    def request(path, payload=None, form=None, csrf=None):
        data, headers = None, {}
        if payload is not None:
            data = json.dumps(payload).encode()
            headers["Content-Type"] = "application/json"
        if form is not None:
            data = urlencode(form).encode()
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        if csrf is not None:
            headers["X-CSRF-Token"] = csrf
        req = urllib.request.Request(base_url + path, data=data, headers=headers)
        try:
            response = opener.open(req, timeout=12)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            body = response.read().decode()
            return response.status, response.headers, body

    status, _, _ = request("/healthz")
    assert status == 200
    for path in ("/", "/catalog", "/preview", "/journal", "/support"):
        status, headers, _ = request(path)
        assert status == 302 and headers["Location"] == "/login", (path, status)
    status, _, body = request("/api/preview", {"url": "http://mirror-catalog:9080/"})
    assert status == 401 and json.loads(body)["error"] == "SESSION_REQUIRED"
    print("OK pages et API protégées ; healthcheck public")

    status, headers, body = request("/login")
    assert status == 200
    cookie_header = headers.get("Set-Cookie", "")
    assert "HttpOnly" in cookie_header and "SameSite=Lax" in cookie_header
    if base_url.startswith("https:"):
        assert "Secure" in cookie_header
    login_token = token_from(body)
    credentials = {"username": "operator.mg-041", "password": "MG-041-2147"}
    status, _, _ = request("/login", form=credentials)
    assert status == 403
    status, _, body = request(
        "/login", form={**credentials, "password": "incorrect", "csrf_token": login_token}
    )
    assert status == 401 and "Identifiant ou mot de passe incorrect" in body
    status, headers, _ = request("/login", form={**credentials, "csrf_token": login_token})
    assert status == 303 and headers["Location"] == "/"
    print("OK connexion réelle, refus des mauvais identifiants et CSRF de connexion")

    csrf = None
    for path in ("/", "/catalog", "/preview", "/journal", "/support"):
        status, headers, body = request(path)
        assert status == 200, (path, status)
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert headers["Cache-Control"] == "no-store"
        assert "operator.mg-041" in body and "OPS-1" in body
        if path == "/journal":
            assert all(value in body for value in ("SYNC-NGR-2147", "ng-r-relay", "09:12"))
        if path == "/support":
            assert "9090" in body and "HTTP" in body and "KB-MIRROR-023" in body
        if path == "/preview":
            csrf = token_from(body)
        print(f"OK GET authentifié {path}")
    assert csrf != login_token, "Le jeton CSRF doit être renouvelé à la connexion"

    status, _, body = request("/api/preview", {"url": "http://mirror-catalog:9080/"})
    assert status == 403 and json.loads(body)["error"] == "CSRF_INVALID"
    for path in ("/", "/public/bulletin", "/public/connectors", "/public/retention"):
        url = "http://mirror-catalog:9080" + path
        status, _, body = request("/api/preview", {"url": url}, csrf=csrf)
        result = json.loads(body)
        assert status == 200 and result["ok"], result
        assert result["upstream_status"] == 200 and result["body"], result
        assert result["requested_url"] == url and result["truncated"] is False
        assert result["classification"] == "INTERNAL"
        print(f"OK catalogue {path}: HTTP 200, {result['content_type']}")

    status, _, body = request(
        "/api/preview", {"url": "http://mirror-catalog:9080/public/missing"}, csrf=csrf
    )
    result = json.loads(body)
    assert status == 200 and result["ok"] and result["upstream_status"] == 404
    print("OK statut amont 404 distingué du statut du portail")

    errors = (
        ({}, 400, "INVALID_INPUT"),
        ({"url": 42}, 400, "INVALID_INPUT"),
        ({"url": ""}, 400, "INVALID_URL"),
        ({"url": "http://mirror-catalog:incorrect/"}, 400, "INVALID_URL"),
        ({"url": "https://mirror-catalog:9080/"}, 400, "UNSUPPORTED_SCHEME"),
        ({"url": "http://ng-r-relay:9090/"}, 403, "DESTINATION_NOT_APPROVED"),
        ({"url": "http://mirror-catalog:9081/"}, 403, "DESTINATION_OUT_OF_SCOPE"),
    )
    for payload, expected_status, expected_error in errors:
        status, _, body = request("/api/preview", payload, csrf=csrf)
        result = json.loads(body)
        assert status == expected_status and result["error"] == expected_error, result
    print("OK erreurs distinctes ; NG-R direct refusé avant toute requête HTTP")

    status, _, _ = request("/logout", form={})
    assert status == 403
    status, headers, _ = request("/logout", form={"csrf_token": csrf})
    assert status == 303 and headers["Location"] == "/login"
    status, _, body = request("/api/preview", {"url": "http://mirror-catalog:9080/"}, csrf=csrf)
    assert status == 401 and json.loads(body)["error"] == "SESSION_REQUIRED"
    print("OK déconnexion et suppression de la session navigateur")
    print("Vérifications V2 ordinaires terminées ; exploitation SSRF non auditée.")


if __name__ == "__main__":
    main()
