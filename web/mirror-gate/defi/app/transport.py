"""Real HTTP transport confined to two pinned lab destinations.

This is a network boundary, independent of the intentionally flawed SOURCE-GUARD
authorization policy. Never weaken this boundary to implement the gameplay.
"""

import http.client
import ipaddress
import re
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as ResolutionTimeout
from contextlib import suppress
from urllib.parse import urlsplit, urlunsplit

MAX_URL = 2048
MAX_BODY = 64 * 1024
DNS_TIMEOUT = 1.5
CONNECT_TIMEOUT = 2.0
READ_TIMEOUT = 3.0
TRANSFER_TIMEOUT = 5.0
PORTS = {"mirror-catalog": 9080, "ng-r-relay": 9090}
CLASSIFICATIONS = {"PUBLIC", "INTERNAL", "RESTRICTED", "INTERNAL / RESTRICTED"}


class PreviewError(Exception):
    def __init__(self, code, message, status):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def parse_url(value):
    """Validate syntax and protocol before the SOURCE-GUARD authorization check."""
    if not isinstance(value, str) or not value or len(value) > MAX_URL:
        raise PreviewError(
            "INVALID_URL", "Indiquez une URL HTTP absolue (2048 caractères maximum).", 400
        )
    # Reject parser ambiguities before canonicalization, including stripped controls.
    if re.search(r"[\s\x00-\x1f\x7f\\]", value) or not value.isascii():
        raise PreviewError(
            "INVALID_URL", "Les caractères spéciaux doivent être encodés dans l'URL.", 400
        )
    try:
        parts = urlsplit(value)
        port = parts.port
    except ValueError as error:
        raise PreviewError("INVALID_URL", "L'URL ne peut pas être analysée.", 400) from error
    if parts.scheme.lower() != "http":
        raise PreviewError("UNSUPPORTED_SCHEME", "La consultation utilise uniquement HTTP.", 400)
    if not parts.netloc or not parts.hostname or port is None or "#" in value:
        raise PreviewError(
            "INVALID_URL", "Indiquez une URL absolue avec port et sans fragment.", 400
        )
    if parts.netloc.count("@") > 1 or ("@" in parts.netloc and not parts.username):
        raise PreviewError("INVALID_URL", "L'autorité déclarée dans l'URL n'est pas valide.", 400)
    path = parts.path or "/"
    if not path.startswith("/") or re.search(
        r"%(?![0-9a-fA-F]{2})", parts.netloc + path + parts.query
    ):
        raise PreviewError(
            "INVALID_URL", "L'encodage ou le chemin de la ressource est invalide.", 400
        )
    return parts


def confine_destination(parts):
    """Authorize only the effective hostname/port, never the userinfo prefix."""
    host = parts.hostname
    port = parts.port
    if host not in PORTS or port != PORTS.get(host):
        raise PreviewError(
            "DESTINATION_OUT_OF_SCOPE", "Cette destination est hors du périmètre documentaire.", 403
        )
    authority = parts.netloc.rsplit("@", 1)[-1]
    if authority.lower() != f"{host}:{port}":
        raise PreviewError(
            "INVALID_URL", "Le nom de service et son port doivent être explicites.", 400
        )
    path = parts.path or "/"
    # Preserve userinfo in the displayed address for subsequent form navigation.
    # It is never used as HTTP credentials or sent in the Host header.
    userinfo = parts.netloc.rsplit("@", 1)[0] + "@" if "@" in parts.netloc else ""
    normalized = urlunsplit(("http", f"{userinfo}{host}:{port}", path, parts.query, ""))
    target = path + (f"?{parts.query}" if parts.query else "")
    return host, port, target, normalized


class PinnedConnection(http.client.HTTPConnection):
    """Connect to the validated numeric address without a second DNS lookup."""

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        try:
            # The public ingress interface is never used by the preview client.
            self.sock.bind(self.source_address)
            self.sock.connect((self.host, self.port))
        except BaseException:
            self.sock.close()
            self.sock = None
            raise


class LabTransport:
    def __init__(self, prefix):
        network = ipaddress.IPv4Network(f"{prefix}.0/24", strict=True)
        private_networks = ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
        if not any(network.subnet_of(ipaddress.IPv4Network(net)) for net in private_networks):
            raise RuntimeError("MIRROR_LAB_PREFIX must designate a private IPv4 /24")
        self.addresses = {"mirror-catalog": f"{prefix}.20", "ng-r-relay": f"{prefix}.30"}
        self.source_address = (f"{prefix}.10", 0)
        # Fixed worker count and admission bound: a stalled resolver cannot spawn
        # unlimited threads or queue unbounded requests. Created lazily after fork.
        self.resolver = ThreadPoolExecutor(max_workers=2, thread_name_prefix="lab-dns")
        self.resolver_slots = threading.BoundedSemaphore(2)

    def resolve(self, host, port):
        if not self.resolver_slots.acquire(blocking=False):
            raise PreviewError(
                "RESOLVER_BUSY", "Le connecteur est occupé. Réessayez dans un instant.", 503
            )
        try:
            future = self.resolver.submit(
                socket.getaddrinfo, host, port, socket.AF_INET, socket.SOCK_STREAM
            )
        except RuntimeError:
            self.resolver_slots.release()
            raise
        future.add_done_callback(lambda _: self.resolver_slots.release())
        try:
            results = future.result(timeout=DNS_TIMEOUT)
        except ResolutionTimeout as error:
            raise PreviewError(
                "DNS_TIMEOUT", "La résolution du service a dépassé le délai imparti.", 504
            ) from error
        except socket.gaierror as error:
            raise PreviewError(
                "DNS_FAILURE", "Le nom du service interne ne peut pas être résolu.", 502
            ) from error
        addresses = {entry[4][0] for entry in results}
        expected = self.addresses[host]
        if not addresses or addresses != {expected}:
            raise PreviewError(
                "DNS_FAILURE",
                "La résolution du connecteur ne correspond pas à sa configuration.",
                502,
            )
        return expected

    def fetch(self, parts):
        host, port, target, normalized = confine_destination(parts)
        started = time.monotonic()
        address = self.resolve(host, port)
        connection = PinnedConnection(
            address, port, timeout=CONNECT_TIMEOUT, source_address=self.source_address
        )
        timer = None
        upstream = None
        expired = threading.Event()

        def abort_transfer(sock):
            expired.set()
            with suppress(OSError):
                sock.shutdown(socket.SHUT_RDWR)

        try:
            connection.connect()
            connection.sock.settimeout(READ_TIMEOUT)
            # Absolute transfer bound includes headers and slow/trickling bodies.
            timer = threading.Timer(TRANSFER_TIMEOUT, abort_transfer, args=(connection.sock,))
            timer.daemon = True
            timer.start()
            connection.request(
                "GET",
                target,
                headers={
                    "Host": f"{host}:{port}",
                    "User-Agent": "MirrorGate/3.0",
                    "Accept": "application/json, text/plain;q=0.9, */*;q=0.1",
                    "Accept-Encoding": "identity",
                    "Connection": "close",
                },
            )
            upstream = connection.getresponse()
            body = bytearray()
            while len(body) <= MAX_BODY:
                chunk = upstream.read1(min(4096, MAX_BODY + 1 - len(body)))
                if not chunk:
                    break
                body.extend(chunk)
            if expired.is_set():
                raise TimeoutError
            if len(body) <= MAX_BODY and upstream.length not in (None, 0):
                raise http.client.IncompleteRead(bytes(body))
            # Never decompress untrusted responses (a compressed bomb is still bounded).
            if upstream.getheader("Content-Encoding", "identity").lower() != "identity":
                raise PreviewError(
                    "UNSUPPORTED_ENCODING",
                    "Le service a renvoyé un contenu compressé non pris en charge.",
                    502,
                )
            classification = upstream.getheader("X-Vanta-Classification", "")
            result = {
                "ok": True,
                "requested_url": normalized,
                "upstream_status": upstream.status,
                "content_type": upstream.getheader("Content-Type", "application/octet-stream")[
                    :256
                ],
                "body": bytes(body[:MAX_BODY]).decode("utf-8", errors="replace"),
                "truncated": len(body) > MAX_BODY,
                "duration_ms": round((time.monotonic() - started) * 1000),
                "classification": classification if classification in CLASSIFICATIONS else None,
            }
            return result
        except TimeoutError as error:
            raise PreviewError(
                "UPSTREAM_TIMEOUT", "Le service distant a dépassé le délai de consultation.", 504
            ) from error
        except (OSError, http.client.HTTPException) as error:
            if expired.is_set():
                raise PreviewError(
                    "UPSTREAM_TIMEOUT",
                    "Le service distant a dépassé le délai de consultation.",
                    504,
                ) from error
            raise PreviewError(
                "DESTINATION_UNREACHABLE",
                "Le service distant n'a pas pu être joint ou sa réponse est incomplète.",
                502,
            ) from error
        finally:
            if timer:
                timer.cancel()
            if upstream:
                upstream.close()
            connection.close()
