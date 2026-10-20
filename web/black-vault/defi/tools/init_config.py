"""Create a private development .env once, without printing any key."""

import argparse
import base64
import os
import secrets
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / ".env")
args = parser.parse_args()
key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii").rstrip("=")
try:
    fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
except FileExistsError:
    parser.exit(1, "Configuration existante : conservée. Ne pas régénérer la clé partagée.\n")
with os.fdopen(fd, "w", encoding="utf-8") as stream:
    stream.write(
        f"ROOT_AUDIT_KEY_B64U={key}\n"
        "SESSION_COOKIE_SECURE=false\n"
        "BLACK_VAULT_BIND=127.0.0.1\n"
        "BLACK_VAULT_PORT=8083\n"
    )
print(f"Configuration privée créée : {args.output}. Réutiliser la clé pour ROOT OF TRUST.")
