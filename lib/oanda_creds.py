"""Load OANDA REST credentials from ~/.keys/oanda.txt.

File shape (verified 2026-04-26):
  line 1: 65-char personal access token (contains '-')
  line 2: empty
  line 3: account ID, ~19 chars, digits and dashes only (NNN-NNN-NNNNNNNN-NNN)

Path is hardcoded; values are never printed.
"""
from __future__ import annotations

import pathlib

KEYS_PATH = pathlib.Path.home() / ".keys" / "oanda.txt"


def load() -> tuple[str, str]:
    if not KEYS_PATH.exists():
        raise SystemExit(f"OANDA creds not found at {KEYS_PATH}")
    nonempty = [l.strip() for l in KEYS_PATH.read_text().splitlines() if l.strip()]
    if len(nonempty) != 2:
        raise SystemExit(
            f"unexpected key file shape: {len(nonempty)} non-empty lines (expected 2)"
        )
    token, account = nonempty[0], nonempty[1]
    if not (60 <= len(token) <= 80 and "-" in token):
        raise SystemExit("first non-empty line does not match OANDA token shape")
    if not (15 <= len(account) <= 25 and account.replace("-", "").isdigit()):
        raise SystemExit("second non-empty line does not match OANDA account ID shape")
    return token, account
