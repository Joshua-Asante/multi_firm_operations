# Validator self-test — KNOWN-GOOD fixture mock of dd_protection.py.
# Values intentionally match params.toml in this directory.

DD_TRIGGER = 0.015
DD_SCALE = 0.40

BASE_RISK = {
    "Guardian":       0.0034,
    "Striker":        0.0100,
    "Aegis":          0.0150,
    "Striker NAS100": 0.0040,
}
