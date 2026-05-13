"""Parse / format Q-CORR-1.2 LOCK §16 ``Silver_*`` TV export filenames."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

# LOCK §16 short tokens for session dimension
SESSION_TO_TOKEN = {
    "NY_Extended": "NYExt",
    "London_NY_Overlap": "LdnNY",
}
TOKEN_TO_SESSION = {v: k for k, v in SESSION_TO_TOKEN.items()}

_SILVER_RE = re.compile(
    r"^Silver_e(?P<ema>\d+)_sl(?P<sl>\d+)_tp(?P<tp>\d+)_(?P<sess>NYExt|LdnNY)_(?P<phase>train|oos)\.csv$",
    re.IGNORECASE,
)


def format_silver_basename(
    *,
    ema_slow_len: int,
    stop_atr: float,
    tp_atr: int,
    session: str,
    phase: str,
) -> str:
    """Build canonical basename (``train`` / ``oos``). ``stop_atr`` encoded as hundredths."""
    if session not in SESSION_TO_TOKEN:
        raise ValueError(f"unknown session {session!r}; expected one of {list(SESSION_TO_TOKEN)}")
    if phase not in ("train", "oos"):
        raise ValueError("phase must be 'train' or 'oos'")
    sl = int(round(float(stop_atr) * 100))
    tok = SESSION_TO_TOKEN[session]
    return f"Silver_e{int(ema_slow_len)}_sl{sl}_tp{int(tp_atr)}_{tok}_{phase}.csv"


def parse_silver_export_basename(name: str) -> dict[str, Any]:
    m = _SILVER_RE.match(name)
    if not m:
        raise ValueError(
            f"filename {name!r} does not match LOCK §16 pattern "
            "Silver_e{ema}_sl{stop×100}_tp{tp}_{NYExt|LdnNY}_{train|oos}.csv"
        )
    ema = int(m.group("ema"))
    sl_raw = int(m.group("sl"))
    tp = int(m.group("tp"))
    sess_tok = m.group("sess")
    phase = m.group("phase").lower()
    stop_atr = sl_raw / 100.0
    session = TOKEN_TO_SESSION[sess_tok]
    return {
        "ema_slow_len": ema,
        "stop_atr": stop_atr,
        "tp_atr": tp,
        "session": session,
        "phase": phase,
        "basename": name,
    }


def validate_parsed_in_grid(parsed: dict[str, Any], grid: dict[str, Any]) -> None:
    """Raise ValueError if parsed params are not in the LOCK Cartesian grid."""
    td = grid.get("tunable_dimensions") or {}
    ema_ok = parsed["ema_slow_len"] in td.get("ema_slow_len", [])
    stop_ok = parsed["stop_atr"] in td.get("stop_atr", [])
    tp_ok = parsed["tp_atr"] in td.get("tp_atr", [])
    sess_ok = parsed["session"] in td.get("session", [])
    if not (ema_ok and stop_ok and tp_ok and sess_ok):
        raise ValueError(
            f"params ({parsed['ema_slow_len']}, {parsed['stop_atr']}, "
            f"{parsed['tp_atr']}, {parsed['session']!r}) not in locked grid"
        )


def load_grid(run_dir: Path) -> dict[str, Any]:
    p = run_dir / "grid.json"
    if not p.is_file():
        raise FileNotFoundError(f"missing {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def expected_oos_basename(train_basename: str) -> str:
    if not train_basename.endswith("_train.csv"):
        raise ValueError("train basename must end with _train.csv")
    return train_basename.replace("_train.csv", "_oos.csv")
