"""USOIL 15min behavioral characterization (Notice/Identify-phase).

Plan: ~/.claude/plans/usoil-15min-behavioral-composed-tower.md
Brief: docs/methodology/findings/2026-05-02_usoil_15min_characterization.md (output)
Loop: INQHIORI Notice/Identify
D-S-A domain: data + system

This package executes the multi-stage characterization for USOIL 15min on
OANDA, with Pepperstone TV-export reconciliation at Stage 0 and visual
overlay validation at Stage D (handled outside Python via Pine indicator).

NOT a strategy. NO trade simulation. Descriptive statistics only.
"""
