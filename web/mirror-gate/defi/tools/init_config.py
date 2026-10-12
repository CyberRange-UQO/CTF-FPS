"""Initialize an ignored local .env without printing or replacing an existing secret."""

import argparse
import secrets
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, help="Override only the portal's local host port")
    args = parser.parse_args()
    if args.port is not None and not 1 <= args.port <= 65535:
        parser.error("--port doit être compris entre 1 et 65535")
    base = Path(__file__).resolve().parents[1]
    target = base / ".env"
    content = target.read_text() if target.exists() else (base / ".env.example").read_text()
    lines = content.splitlines()

    def values(key):
        return [
            line.split("=", 1)[1].strip().strip("\"'")
            for line in lines
            if "=" in line and line.split("=", 1)[0].strip() == key
        ]

    def replace(key, value):
        lines[:] = [
            line for line in lines if "=" not in line or line.split("=", 1)[0].strip() != key
        ]
        lines.append(f"{key}={value}")

    if not any(values("SESSION_SECRET")):
        replace("SESSION_SECRET", secrets.token_hex(32))
    if args.port is not None:
        replace("MIRROR_PORT", args.port)
    target.touch(mode=0o600, exist_ok=True)
    target.chmod(0o600)
    target.write_text("\n".join(lines) + "\n")
    print("Configuration locale prête dans defi/.env ; secret conservé ou généré sans affichage.")


if __name__ == "__main__":
    main()
