#!/usr/bin/env python3
"""
Generate strong random secrets for ComputeSwarm production deployment.

Usage:
    python scripts/generate-secrets.py
    python scripts/generate-secrets.py --env-file .env.prod
"""

from __future__ import annotations

import argparse
import secrets
import string
import sys


def generate_secret(length: int = 64) -> str:
    """Generate a cryptographically secure random secret string."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*_-"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def generate_password(length: int = 32) -> str:
    """Generate a URL-safe random password."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate secrets for ComputeSwarm")
    parser.add_argument(
        "--env-file",
        default=".env.prod",
        help="Path to the .env file to create or update (default: .env.prod)",
    )
    parser.add_argument(
        "--print-only",
        action="store_true",
        help="Print secrets to stdout without writing to a file",
    )
    args = parser.parse_args()

    secret_key = generate_secret(64)
    db_password = generate_password(32)
    minio_root_password = generate_password(32)

    lines = [
        "# === Auto-generated secrets — DO NOT COMMIT ===",
        f"SECRET_KEY={secret_key}",
        f"DB_PASSWORD={db_password}",
        f"MINIO_ROOT_PASSWORD={minio_root_password}",
        f"MINIO_ROOT_USER={generate_password(16)}",
        "# ==============================================",
    ]

    output = "\n".join(lines) + "\n"

    if args.print_only:
        print(output)
        return

    print("=== Generated Secrets ===")
    print(f"SECRET_KEY        = {secret_key}")
    print(f"DB_PASSWORD       = {db_password}")
    print(f"MINIO_ROOT_PASSWORD = {minio_root_password}")
    print(f"MINIO_ROOT_USER    = {generate_password(16)}")
    print("")
    print(f"Appending to {args.env_file} ...")

    try:
        with open(args.env_file, "a", encoding="utf-8") as f:
            f.write("\n")
            f.write(output)
    except FileNotFoundError:
        print(f"ERROR: {args.env_file} not found. Create it from .env.prod.example first.")
        sys.exit(1)

    print("Done. Now fill in the remaining values (domains, Stripe keys, etc.)")


if __name__ == "__main__":
    main()
