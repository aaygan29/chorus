"""Control evaluation and specificity ablation for the anchored model, run
ONLY at the frozen W_syn selected by anchor_sweep.py (never re-tuned here).
Reuses the null-generation and statistics functions from
ablation_specificity.py rather than reimplementing them, per the task spec.

Two things happen here, both post-freeze:
1. Control evaluation: angular pointing error across goals (20 seeds),
   figure-8 cross-track RMS, compared against the published RingCX numbers
   and the uncalibrated RealCX baseline in data/ablation_results.json.
2. Specificity ablation AT the anchored operating point: intact vs
   sign_scramble vs edge_shuffle vs degree_matched_random, 20 seeds, null
   re-randomized per seed, Cohen's d with CI, permutation p, MDE at n=20.

Usage:
  python3 anchored_eval.py --calib ../data/anchor_calibration.json \
      --npz ../data/cx_real.npz --csv ../data/cx_nodes.csv \
      --tag flywire --seeds 20 --out ../data/anchored_results.json
"""
import argparse, json, time, sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from cx_anchored import load_signed, AnchoredCX, bump_fwhm_deg
from ablation_specificity import (REWIRERS, stats_block, mde_at_n)

GOALS_DEG = np.arange(0, 360, 30)
N_SETTLE = 150
N_HOLD = 100
GOAL_GAIN = 6.0


def circ_err_deg(a, b):
    d = (a - b + np.pi) % (2 * np.pi) - np.pi
    return np.degrees(np.abs(d))


def make_cx(Wsigned, nodes, wsyn, sim_seed):
    cx = AnchoredCX(Wsigned, nodes, wsyn, seed=sim_seed)
    return cx


def pointing_trial(Wsigned, nodes, wsyn, sim_seed):
    errs = []
    for g_deg in GOALS_DEG:
        g = np.radians(g_deg)
        cx = make_cx(Wsigned, nodes, wsyn, sim_seed)
        cx.seed_bump(0.0, steps=N_SETTLE, gain=GOAL_GAIN)
        m = cx.fam == 'EPG'
        headings = np.empty(N_HOLD)
        for t in range(N_HOLD):
            ext = np.zeros(cx.N)
            ext[m] = GOAL_GAIN * np.cos(cx.ph[m] - g)
            cx.step(ext=ext)
            headings[t] = cx.bump_heading('EPG')[0]
        tail = headings[-N_HOLD // 3:]
        errs.append(np.mean(circ_err_deg(tail, g)))
    return float(np.mean(errs))


def figure8_ref(n_pts, a=3.0):
    t = np.linspace(0, 2 * np.pi, n_pts)
    x = a * np.sin(t)
    y = a * np.sin(t) * np.cos(t)
    return np.stack([x, y], axis=1)


def cross_track_rms(path, ref):
    from scipy.spatial import cKDTree
    tree = cKDTree(ref)
    d, _ = tree.query(path)
    return float(np.sqrt(np.mean(d ** 2)))


def figure8_trial(Wsigned, nodes, wsyn, sim_seed, n_steps=220, speed=0.12):
    ref = figure8_ref(400)
    tgt_heading = np.arctan2(np.gradient(ref[:, 1]), np.gradient(ref[:, 0]))
    idx = np.linspace(0, len(ref) - 1, n_steps).astype(int)
    cx = make_cx(Wsigned, nodes, wsyn, sim_seed)
    cx.seed_bump(tgt_heading[0], steps=N_SETTLE, gain=GOAL_GAIN)
    pos = np.array([ref[0, 0], ref[0, 1]])
    path = [pos.copy()]
    m = cx.fam == 'EPG'
    for k in idx:
        g = tgt_heading[k]
        ext = np.zeros(cx.N)
        ext[m] = GOAL_GAIN * np.cos(cx.ph[m] - g)
        cx.step(ext=ext)
        hd = cx.bump_heading('EPG')[0]
        pos = pos + speed * np.array([np.cos(hd), np.sin(hd)])
        path.append(pos.copy())
    path = np.array(path)
    return cross_track_rms(path, ref)


def bump_amp_check(Wsigned, nodes, wsyn):
    cx = AnchoredCX(Wsigned, nodes, wsyn, seed=0)
    cx.seed_bump(0.0, steps=N_SETTLE, gain=GOAL_GAIN)
    cx.free_run(200)
    r, ph = cx.epg_profile()
    return bump_fwhm_deg(r, ph), float(r.max()), float(r.min())


def w_sensitivity_check(Wsigned, nodes, wsyn, tag):
    print(f'[{tag}] W-sensitivity sanity check at frozen W_syn (does the anchored '
          f'operating point even depend on the connectome before we run the nulls?)', flush=True)
    base = pointing_trial(Wsigned, nodes, wsyn, sim_seed=0)
    scaled = pointing_trial(Wsigned * 0.1, nodes, wsyn, sim_seed=0)
    zeroed = pointing_trial(Wsigned * 0.0, nodes, wsyn, sim_seed=0)
    print(f'  intact W pointing error:      {base:.2f} deg', flush=True)
    print(f'  W scaled x0.1 pointing error: {scaled:.2f} deg', flush=True)
    print(f'  W zeroed pointing error:      {zeroed:.2f} deg', flush=True)
    w_sensitive = abs(scaled - base) > 1.0 or abs(zeroed - base) > 1.0
    print(f'  harness is W-sensitive at this operating point: {w_sensitive}', flush=True)
    return dict(intact=base, scaled_0p1=scaled, zeroed=zeroed, w_sensitive=bool(w_sensitive))


def run_control(Wsigned, nodes, wsyn, seeds, tag):
    print(f'[{tag}] control evaluation at frozen W_syn={wsyn:.4g}', flush=True)
    fwhm, rmax, rmin = bump_amp_check(Wsigned, nodes, wsyn)
    print(f'  operating-point bump check: fwhm={fwhm:.1f}deg rmax={rmax:.3f} rmin={rmin:.3f}', flush=True)
    pointing, fig8 = [], []
    for s in range(seeds):
        t0 = time.time()
        pt = pointing_trial(Wsigned, nodes, wsyn, sim_seed=s)
        f8 = figure8_trial(Wsigned, nodes, wsyn, sim_seed=s)
        pointing.append(pt); fig8.append(f8)
        print(f'  [{tag}] seed {s+1}/{seeds} pointing={pt:.2f}deg fig8_rms={f8:.3f} ({time.time()-t0:.1f}s)', flush=True)
    return dict(pointing_deg=pointing, fig8_rms=fig8,
                pointing_mean=float(np.mean(pointing)), pointing_sd=float(np.std(pointing, ddof=1)),
                fig8_mean=float(np.mean(fig8)), fig8_sd=float(np.std(fig8, ddof=1)),
                operating_point_check=dict(fwhm_deg=fwhm, rmax=rmax, rmin=rmin))


def run_ablation(Wsigned, nodes, wsyn, seeds, tag):
    print(f'[{tag}] specificity ablation at anchored operating point', flush=True)
    conditions = ['intact', 'sign_scramble', 'edge_shuffle', 'degree_matched_random']
    out = {}
    for cond in conditions:
        out[cond] = {'pointing_deg': [], 'fig8_rms': []}
        for s in range(seeds):
            t0 = time.time()
            if cond == 'intact':
                Wc = Wsigned
            else:
                rng = np.random.default_rng(2000 * s + hash(cond) % 1000)
                Wc = REWIRERS[cond](Wsigned, rng)
            pt = pointing_trial(Wc, nodes, wsyn, sim_seed=s)
            f8 = figure8_trial(Wc, nodes, wsyn, sim_seed=s)
            out[cond]['pointing_deg'].append(pt)
            out[cond]['fig8_rms'].append(f8)
            print(f'  [{tag}] [{cond}] seed {s+1}/{seeds} pointing={pt:.2f}deg fig8_rms={f8:.3f} ({time.time()-t0:.1f}s)', flush=True)
    intact = out['intact']
    stats_out = {}
    for cond in ['sign_scramble', 'edge_shuffle', 'degree_matched_random']:
        stats_out[cond] = {}
        for metric in ['pointing_deg', 'fig8_rms']:
            stats_out[cond][metric] = stats_block(intact[metric], out[cond][metric])
    out['stats_vs_intact'] = stats_out
    out['min_detectable_effect_d_n20'] = mde_at_n(seeds)
    return out


def run(calib_path, npz, csv, tag, seeds, out_path):
    with open(calib_path) as f:
        calib = json.load(f)
    wsyn = calib['selected_W_syn']
    print(f'[{tag}] loading connectome for post-freeze evaluation, frozen W_syn={wsyn:.4g}', flush=True)
    Wsigned, rid, nodes, info = load_signed(npz, csv)
    sanity = w_sensitivity_check(Wsigned, nodes, wsyn, tag)
    control = run_control(Wsigned, nodes, wsyn, seeds, tag)
    ablation = run_ablation(Wsigned, nodes, wsyn, seeds, tag)
    result = dict(tag=tag, frozen_W_syn=wsyn, calibration_source=calib_path,
                  sign_info=info, w_sensitivity_sanity_check=sanity,
                  control=control, ablation=ablation,
                  config=dict(seeds=seeds, n_goals=len(GOALS_DEG), n_hold=N_HOLD,
                              n_settle=N_SETTLE, goal_gain=GOAL_GAIN))
    with open(out_path, 'w') as f:
        json.dump(result, f, indent=2)
    print(f'wrote {out_path}', flush=True)
    return result


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--calib', required=True)
    ap.add_argument('--npz', required=True)
    ap.add_argument('--csv', required=True)
    ap.add_argument('--tag', required=True)
    ap.add_argument('--seeds', type=int, default=20)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    run(args.calib, args.npz, args.csv, args.tag, args.seeds, args.out)
