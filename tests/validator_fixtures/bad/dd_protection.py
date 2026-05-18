# Validator self-test — KNOWN-BAD fixture mock of dd_protection.py.
# SEEDED VIOLATION: DD_TRIGGER drifted to 0.010 (manifest expects 0.015).
# Validator MUST surface this as a HARD violation.

DD_TRIGGER = 0.010   # SEEDED — drift from manifest's 1.5% / 0.015
DD_SCALE = 0.40

BASE_RISK = {
    "Guardian":       0.0034,
    "Striker":        0.0100,
    "Aegis":          0.0150,
    "Striker NAS100": 0.0040,
}
