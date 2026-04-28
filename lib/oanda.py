"""OANDA REST API wrapper.

Built on oandapyV20. Auth via lib/oanda_creds.load() (~/.keys/oanda.txt).
Endpoint chosen from account-ID prefix (101 = practice, 001 = live) per
reference_oanda_credentials.md.

Two-tier canonical rule (memory: feedback_two_tier_canonical_pepperstone_oanda):
this module is for OANDA-specific operations only. Pepperstone-anchored
artifacts (e.g. portfolio_mc Pepperstone panels) are never overwritten by
data fetched here.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterator

from .oanda_creds import load as load_creds


PRACTICE_HOST = "api-fxpractice.oanda.com"
LIVE_HOST = "api-fxtrade.oanda.com"

PRACTICE_PREFIX = "101"
LIVE_PREFIX = "001"


def _host_for_account(account_id: str) -> str:
    """Return the OANDA API host that matches the account-ID prefix."""
    prefix = account_id.split("-", 1)[0]
    if prefix == PRACTICE_PREFIX:
        return PRACTICE_HOST
    if prefix == LIVE_PREFIX:
        return LIVE_HOST
    raise ValueError(
        f"Unrecognized OANDA account ID prefix '{prefix}' "
        f"(expected '{PRACTICE_PREFIX}' practice or '{LIVE_PREFIX}' live)"
    )


def _environment_for_host(host: str) -> str:
    return "practice" if host == PRACTICE_HOST else "live"


def client(token: str | None = None, account_id: str | None = None):
    """Return a configured (oandapyV20.API, account_id) tuple.

    Falls back to lib.oanda_creds.load() if either arg is None. Endpoint is
    selected from the account-ID prefix.
    """
    try:
        import oandapyV20
    except ImportError as e:
        raise ImportError(
            "oandapyV20 not installed. Run: pip install -e .[broker]"
        ) from e
    if token is None or account_id is None:
        token, account_id = load_creds()
    host = _host_for_account(account_id)
    api = oandapyV20.API(
        access_token=token,
        environment=_environment_for_host(host),
    )
    return api, account_id


def _iso_to_epoch(s: str) -> float:
    """Parse OANDA RFC3339 (with nanosecond precision and Z suffix) to epoch.

    OANDA returns timestamps like '2022-01-02T22:00:00.000000000Z'. fromisoformat
    handles up to microsecond precision, so we truncate the fractional part.
    """
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    if "." in s:
        head, frac_tz = s.split(".", 1)
        if "+" in frac_tz:
            frac, tz = frac_tz.split("+", 1)
            tz = "+" + tz
        elif "-" in frac_tz:
            frac, tz = frac_tz.split("-", 1)
            tz = "-" + tz
        else:
            frac, tz = frac_tz, ""
        frac = frac[:6]
        s = f"{head}.{frac}{tz}"
    return datetime.fromisoformat(s).timestamp()


def _advance_cursor(last_seen_iso: str) -> str:
    """+1 second after the last candle timestamp, formatted as RFC3339Z."""
    epoch = _iso_to_epoch(last_seen_iso)
    return datetime.fromtimestamp(epoch + 1, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_candles(instrument: str, start: str, end: str,
                  granularity: str = "M15", price: str = "M",
                  token: str | None = None,
                  account_id: str | None = None) -> Iterator[dict]:
    """Yield completed candles for `instrument` between RFC3339 start/end.

    Replaces the stdlib urllib pagination loop in scripts/fetch_oanda_bars.py
    with the oandapyV20 SDK. Same on-the-wire behavior: paginates with
    `from` + `count=5000`; advances cursor to last_candle_time + 1s after each
    page; skips incomplete candles.

    Yields rows of shape {time, open, high, low, close, volume} matching the
    legacy CSV schema in data/bar_data/.
    """
    from oandapyV20.endpoints.instruments import InstrumentsCandles
    api, _ = client(token, account_id)

    end_epoch = _iso_to_epoch(end)
    cursor = start
    last_seen: str | None = None
    while True:
        params = {
            "granularity": granularity,
            "price": price,
            "count": 5000,
            "from": cursor,
            "includeFirst": "true" if last_seen is None else "false",
        }
        r = InstrumentsCandles(instrument=instrument, params=params)
        api.request(r)
        candles = r.response.get("candles", [])
        if not candles:
            return
        kept = 0
        for c in candles:
            t = c["time"]
            # Epoch compare — t may have ns-precision suffix that breaks lexical compare
            # against an end like '2024-01-03T00:00:00Z'.
            if _iso_to_epoch(t) >= end_epoch:
                return
            if not c.get("complete", False):
                continue
            mid = c["mid"]
            yield {
                "time": t,
                "open": mid["o"],
                "high": mid["h"],
                "low": mid["l"],
                "close": mid["c"],
                "volume": c.get("volume", 0),
            }
            kept += 1
            last_seen = t
        if kept == 0 or last_seen is None:
            return
        cursor = _advance_cursor(last_seen)


def account_summary(account_id: str | None = None) -> dict:
    """Return the account-summary dict (balance, NAV, margin, positions...).

    Honors the two-tier canonical rule: this fetches OANDA state only.
    Callers writing to local persistence (e.g. cli.py update --from-oanda)
    must enforce the OANDA-only-firm gate themselves; this function does
    not know about local account records.
    """
    from oandapyV20.endpoints.accounts import AccountSummary
    api, acct = client(account_id=account_id)
    r = AccountSummary(accountID=acct)
    api.request(r)
    return r.response.get("account", {})
