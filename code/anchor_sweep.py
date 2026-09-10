"""Sweep W_syn, measure the anchor quantity (EPG bump FWHM), and freeze the
value that best matches the pre-declared anchor. See ANCHORED_MODEL.md for
the anchor declaration and citation. This script must be run BEFORE any
control evaluation; the frozen W_syn is never revisited after control
results are seen.

Usage:
  python3 anchor_sweep.py --npz ../data/cx_real.npz \
      --csv ../data/cx_nodes.csv --tag flywire \
      --out ../data/anchor_calibration.json
"""
import argparse, json, time
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from cx_anchored import load_signed, AnchoredCX, bump_fwhm_deg

ANCHOR_TARGET_DEG = 90.0  # Kim et al. 2017 Science, EPG bump FWHM, Fig. 1J / p.5
SEED_STEPS = 300
FREE_RUN_STEPS = 200
SEED_GAIN = 6.0
N_SEEDS = 6
PHASES = [0.0, 2.0944, 4.1888]  # 0, 120, 240 deg


def measure_point(W, nodes, wsyn, n_seeds=N_SEEDS, phases=PHASES):
    fws = []
    for s in range(n_seeds):
        for k, ph0 in enumerate(phases):
            cx = AnchoredCX(W, nodes, wsyn, seed=1000 * s + k)
            cx.seed_bump(ph0, steps=SEED_STEPS, gain=SEED_GAIN)
            cx.free_run(FREE_RUN_STEPS)
            r, ph = cx.epg_profile()
            fws.append(bump_fwhm_deg(r, ph))
    fws = np.array(fws, float)
    valid = fws[np.isfinite(fws)]
    return dict(mean=float(np.mean(valid)) if len(valid) else float('nan'),
                median=float(np.median(valid)) if len(valid) else float('nan'),
                sd=float(np.std(valid)) if len(valid) else float('nan'),
                n_valid=int(len(valid)), n_total=len(fws), raw=fws.tolist())


def run(npz, csv, tag, out_path, fig_path=None, grid=None):
    print(f'[{tag}] loading connectome and building signed weights...', flush=True)
    W, rid, nodes, info = load_signed(npz, csv)
    if grid is None:
        grid = np.geomspace(1e-6, 0.05, 18)
    sweep = []
    t0 = time.time()
    for i, wsyn in enumerate(grid):
        m = measure_point(W, nodes, float(wsyn))
        sweep.append(dict(W_syn=float(wsyn), **{k: v for k, v in m.items() if k != 'raw'},
                           dist_to_anchor=abs(m['mean'] - ANCHOR_TARGET_DEG) if np.isfinite(m['mean']) else float('inf')))
        print(f'  [{tag}] {i+1}/{len(grid)}  W_syn={wsyn:.3g}  mean_fwhm={m["mean"]:.1f}deg  '
              f'median={m["median"]:.1f}  sd={m["sd"]:.1f}  n_valid={m["n_valid"]}/{m["n_total"]}  '
              f'({time.time()-t0:.1f}s elapsed)', flush=True)

    finite = [p for p in sweep if np.isfinite(p['dist_to_anchor'])]
    best = min(finite, key=lambda p: p['dist_to_anchor']) if finite else None
    result = dict(tag=tag, npz=npz, csv=csv, anchor_target_deg=ANCHOR_TARGET_DEG,
                  anchor_citation='Kim, Rouault, Druckmann, Jayaraman 2017 Science '
                                   '10.1126/science.aal4835, EPG bump FWHM in vivo, Fig. 1J '
                                   '(constrained to 90 deg for model comparisons, p.5 of main text)',
                  sign_info=info, sweep=sweep,
                  selected_W_syn=best['W_syn'] if best else None,
                  selected_match_deg=best['mean'] if best else None,
                  match_quality_deg=best['dist_to_anchor'] if best else None,
                  config=dict(n_seeds=N_SEEDS, phases=PHASES, seed_steps=SEED_STEPS,
                              free_run_steps=FREE_RUN_STEPS, seed_gain=SEED_GAIN))
    with open(out_path, 'w') as f:
        json.dump(result, f, indent=2)
    print(f'[{tag}] selected W_syn={result["selected_W_syn"]:.3g} '
          f'-> mean FWHM {result["selected_match_deg"]:.1f} deg '
          f'(target {ANCHOR_TARGET_DEG} deg, |diff|={result["match_quality_deg"]:.1f} deg)', flush=True)
    print(f'wrote {out_path}', flush=True)

    if fig_path:
        w_arr = [p['W_syn'] for p in sweep]
        m_arr = [p['mean'] for p in sweep]
        sd_arr = [p['sd'] for p in sweep]
        fig, ax = plt.subplots(figsize=(6, 4.2))
        ax.errorbar(w_arr, m_arr, yerr=sd_arr, marker='o', ms=4, lw=1, capsize=2, color='#2b6cb0')
        ax.axhline(ANCHOR_TARGET_DEG, color='#c0392b', ls='--', lw=1.2, label=f'anchor target {ANCHOR_TARGET_DEG:.0f} deg')
        if best:
            ax.scatter([best['W_syn']], [best['mean']], color='#c0392b', zorder=5, s=60,
                       label=f"selected W_syn={best['W_syn']:.2g}")
        ax.set_xscale('log')
        ax.set_xlabel('W_syn (global synaptic scalar)')
        ax.set_ylabel('EPG bump FWHM (deg), mean +/- sd')
        ax.set_title(f'Anchor sweep: {tag}')
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(fig_path, dpi=150)
        print(f'wrote {fig_path}', flush=True)
    return result


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--npz', required=True)
    ap.add_argument('--csv', required=True)
    ap.add_argument('--tag', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--fig', default=None)
    args = ap.parse_args()
    run(args.npz, args.csv, args.tag, args.out, args.fig)
