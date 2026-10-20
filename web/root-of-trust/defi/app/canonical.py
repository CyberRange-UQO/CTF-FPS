"""The challenge's Python JSON convention; deliberately not RFC 8785."""

import hashlib
import json


def canonical_bytes(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("utf-8")


def sha256(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON member")
        result[key] = value
    return result


def _reject_number(value):
    raise ValueError("Only integer JSON numbers are supported")


def strict_loads(raw):
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="strict")
    return json.loads(
        raw, object_pairs_hook=_unique_object,
        parse_float=_reject_number, parse_constant=_reject_number,
    )
