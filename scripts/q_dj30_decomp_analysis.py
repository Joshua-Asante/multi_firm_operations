"""Q-DJ30-decomp analysis — 5-config static-equity rebase + additivity check.

Inputs (5 TV-export CSVs):
  baseline   98bf2 — BT-ON,  risk 1.00%, pyr 350, dDD 1.00%
  variant_A  953f2 — BT-ON,  risk 0.70%, pyr 350, dDD 1.00%
  variant_B  ac9a9 — BT-ON,  risk 1.00%, pyr 750, dDD 1.00%
  variant_C  c0b35 — BT-OFF, risk 1.00%, pyr 350, dDD 1.00%
  joint      1e83b — BT-OFF, risk 0.70%, pyr 750, dDD 1.00%

Methodology:
- Compounded basis: read Net P&L USD directly from Exit rows.
- Static-equity rebase: per-trade equity-% = Net P&L USD / equity_at_entry,
  where equity_at_entry = $200K + cumulative Net P&L USD before this trade.
  static_pnl = equity-% * $200K.
  This converts TV's compounded sizing back to FXIFY-comparable static $200K.
- For BT-OFF configs (variant_C, joint), static rebase should be near-identity
  since position size is already static-$200K-based.
"""
import pandas as pd
from pathlib import Path

INIT = 200_000.0

CSVS = {
    'baseline':  (r'C:/Users/joshu/Downloads/Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-17_98bf2.csv',
                  'BT-ON,  risk 1.00%, pyr 350'),
    'variant_A': (r'C:/Users/joshu/Downloads/Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-17_953f2.csv',
                  'BT-ON,  risk 0.70%, pyr 350'),
    'variant_B': (r'C:/Users/joshu/Downloads/Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-17_ac9a9.csv',
                  'BT-ON,  risk 1.00%, pyr 750'),
    'variant_C': (r'C:/Users/joshu/multi_firm_operations/.claude/worktrees/admiring-saha-147572/data/tv_exports/pepperstone/Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-17_c0b35.csv',
                  'BT-OFF, risk 1.00%, pyr 350'),
    'joint':     (r'C:/Users/joshu/Downloads/updated_Striker_DJ30_v4.5_PEPPERSTONE_US30_2026-05-17_1e83b.csv',
                  'BT-OFF, risk 0.70%, pyr 750'),
}


def analyze_one(label: str, path: str, config: str) -> dict:
    df = pd.read_csv(path, encoding='utf-8-sig')
    ex = df[df['Type'].str.startswith('Exit')].copy().reset_index(drop=True)
    pnl_c = ex['Net P&L USD'].astype(float).values
    n = len(pnl_c)

    eq_entry = [INIT]
    for i in range(n - 1):
        eq_entry.append(eq_entry[-1] + pnl_c[i])
    eq_entry = pd.Series(eq_entry)
    pct = pnl_c / eq_entry.values
    pnl_s = pct * INIT

    def metrics(pnl):
        net = pnl.sum()
        wins = (pnl > 0).sum()
        wr = wins / n * 100
        gw = pnl[pnl > 0].sum()
        gl = pnl[pnl <= 0].sum()
        pf = gw / abs(gl) if gl else float('inf')
        eq = INIT + pd.Series(pnl).cumsum()
        dd = ((eq - eq.cummax()) / eq.cummax() * 100).min()
        return {'net': net, 'wr': wr, 'pf': pf, 'dd': dd}

    mc = metrics(pnl_c)
    ms = metrics(pnl_s)

    pyr_mask = ex['Signal'].str.contains('Add', case=False, na=False).values
    dd_mask = ex['Signal'].str.startswith('DD ').values
    mh_mask = (ex['Signal'] == 'Max Hold').values

    return {
        'label': label,
        'config': config,
        'n': n,
        'compounded': {**mc,
                       'pyr_share': pnl_c[pyr_mask].sum() / mc['net'] * 100,
                       'dd_limit_n': int(dd_mask.sum()),
                       'dd_limit_net': pnl_c[dd_mask].sum(),
                       'max_hold_n': int(mh_mask.sum()),
                       'max_hold_net': pnl_c[mh_mask].sum()},
        'static': {**ms,
                   'pyr_share': pnl_s[pyr_mask].sum() / ms['net'] * 100,
                   'dd_limit_net': pnl_s[dd_mask].sum(),
                   'max_hold_net': pnl_s[mh_mask].sum()},
        'pyr_n': int(pyr_mask.sum()),
    }


def main():
    results = {label: analyze_one(label, path, cfg) for label, (path, cfg) in CSVS.items()}

    print('=' * 100)
    print('Q-DJ30-decomp — per-config metrics (compounded vs static-equity rebase)')
    print('=' * 100)
    for label, r in results.items():
        c, s = r['compounded'], r['static']
        print(f"\n{label:12s}  {r['config']}")
        print(f"  N={r['n']:3d}  pyr_exits={r['pyr_n']:2d}  DD_Limit_n={c['dd_limit_n']:2d}  Max_Hold_n={c['max_hold_n']:2d}")
        print(f"  -- compounded --   WR {c['wr']:6.2f}%  PF {c['pf']:.3f}  Net ${c['net']:>11,.0f}  DD {c['dd']:6.2f}%")
        print(f"                     pyr_share {c['pyr_share']:5.1f}%  DD_Lim ${c['dd_limit_net']:>10,.0f}  Max_Hold ${c['max_hold_net']:>9,.0f}")
        print(f"  -- static-$200K -- WR {s['wr']:6.2f}%  PF {s['pf']:.3f}  Net ${s['net']:>11,.0f}  DD {s['dd']:6.2f}%")
        print(f"                     pyr_share {s['pyr_share']:5.1f}%  DD_Lim ${s['dd_limit_net']:>10,.0f}  Max_Hold ${s['max_hold_net']:>9,.0f}")
        print(f"  -- cascade share of headline Net: {(c['net'] - s['net']) / c['net'] * 100:5.1f}%")

    print('\n' + '=' * 100)
    print('Marginal-effect deltas vs baseline (static-equity basis, FXIFY-comparable)')
    print('=' * 100)
    base_s = results['baseline']['static']
    for label in ['variant_A', 'variant_B', 'variant_C', 'joint']:
        s = results[label]['static']
        dnet = s['net'] - base_s['net']
        dpf = s['pf'] - base_s['pf']
        ddd = s['dd'] - base_s['dd']
        dwr = s['wr'] - base_s['wr']
        print(f"  {label:12s}  dNet ${dnet:>+10,.0f} ({dnet/base_s['net']*100:+5.1f}%)   dPF {dpf:+6.3f}   dDD {ddd:+5.2f}pp   dWR {dwr:+5.2f}pp")

    print('\n' + '=' * 100)
    print('Additivity check (static-equity Net)')
    print('=' * 100)
    base = base_s['net']
    dA = results['variant_A']['static']['net'] - base
    dB = results['variant_B']['static']['net'] - base
    dC = results['variant_C']['static']['net'] - base
    dJ = results['joint']['static']['net'] - base
    msum = dA + dB + dC
    interaction = dJ - msum
    print(f"  Sum marginals (A+B+C):  ${msum:>+11,.0f}")
    print(f"  Joint actual:          ${dJ:>+11,.0f}")
    print(f"  Cross-axis interaction: ${interaction:>+11,.0f}  ({interaction/abs(dJ)*100 if dJ else 0:+5.1f}% of joint magnitude)")

    print('\nAdditivity check (static-equity DD)')
    print('=' * 100)
    base_dd = base_s['dd']
    dA_dd = results['variant_A']['static']['dd'] - base_dd
    dB_dd = results['variant_B']['static']['dd'] - base_dd
    dC_dd = results['variant_C']['static']['dd'] - base_dd
    dJ_dd = results['joint']['static']['dd'] - base_dd
    msum_dd = dA_dd + dB_dd + dC_dd
    print(f"  Sum marginals (A+B+C):  {msum_dd:+5.2f}pp")
    print(f"  Joint actual:          {dJ_dd:+5.2f}pp")
    print(f"  Cross-axis interaction: {dJ_dd - msum_dd:+5.2f}pp")

    print('\nAdditivity check (compounded Net, for comparison)')
    print('=' * 100)
    base_c = results['baseline']['compounded']['net']
    dAc = results['variant_A']['compounded']['net'] - base_c
    dBc = results['variant_B']['compounded']['net'] - base_c
    dCc = results['variant_C']['compounded']['net'] - base_c
    dJc = results['joint']['compounded']['net'] - base_c
    msumc = dAc + dBc + dCc
    print(f"  Sum marginals (A+B+C):  ${msumc:>+11,.0f}")
    print(f"  Joint actual:          ${dJc:>+11,.0f}")
    print(f"  Cross-axis interaction: ${dJc - msumc:>+11,.0f}")


if __name__ == '__main__':
    main()
