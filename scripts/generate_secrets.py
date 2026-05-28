#!/usr/bin/env python3
from __future__ import annotations

import secrets


def token() -> str:
    return secrets.token_urlsafe(32)


def main() -> None:
    print("# Copy these into your deployment environment, not into chat.")
    print(f"ADMIN_API_TOKEN={token()}")
    print(f"WEBHOOK_TOKEN={token()}")
    print(f"ALLOW_UNAUTHENTICATED_LOOPBACK=0")


if __name__ == "__main__":
    main()
