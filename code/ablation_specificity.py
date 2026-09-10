"""Specificity ablation for the real-connectome CX control pipeline (RealCX).

Tests whether the published control headlines (0.41 deg pointing, 0.17 unit
figure-8 cross-track RMS, 100% / 0.9 unit point-to-point) actually depend on
the real FlyWire/MaleCNS signed connectome, by comparing intact W against
three null rewirings that destroy specific structure while holding other
statistics fixed. Runs entirely on code/cx_real_dynamics.py RealCX, which is
the only pipeline in this repo whose step() reads self.W (self.W.T @ self.r).
chorus_env.py / cx_ring.py never read W and are not used here.

Conditions: intact, sign_scramble, edge_shuffle, degree_matched_random (all
on FlyWire cx_real.npz), plus intact_male (MaleCNS noFC2, reference only).

Usage: python3 ablation_specificity.py --seeds 20 --out ../data/ablation_results.json
"""
import argparse, json, time, sys
import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, '.')
from cx_real_dynamics import load, RealCX
from measure_kernel import effective_epg_kernel, spectral_phase, family_of

FLY_NPZ, FLY_CSV = '../data/flywire/cx_real.npz', '../data/flywire/cx_nodes.csv'
MALE_NPZ, MALE_CSV = '../data/malecns_cx/cx_real_male_noFC2.npz', '../data/malecns_cx/cx_nodes_male_noFC2.csv'

GOALS_DEG = np.arange(0, 360, 30)
N_SETTLE = 100
N_HOLD = 150
GOAL_GAIN = 1.6


def epg_spectral_phase(W, fam):
    """W-derived anatomical phase for EPG neurons (measure_kernel.py method).
    Computed once from the INTACT connectome and reused as the fixed
    electrode/anatomical map across all rewired conditions: electrodes sit
    on physical neurons, they do not move when we ablate the wiring."""
    K, epg_idx = effective_epg_kernel(W, fam)
    ph = spectral_phase(K)
    full = np.full(W.shape[0], np.nan)
    full[epg_idx] = ph
    return full


def build_nodes_with_phase(csv, root_ids, phase_by_fam_pos, fam):
    nodes = pd.read_csv(csv).set_index('root_id').loc[root_ids].reset_index()
    nodes['t'] = nodes['cell_type'].astype(str)
    nodes['fam'] = fam
    nodes['phase'] = phase_by_fam_pos
    return nodes


def rewire_sign_scramble(W, rng):
    """Shuffle the SIGN across existing edges: same topology, same |W| at
    each edge location, but which edges are + vs - is permuted."""
    Wo = W.copy()
    iu = np.nonzero(W)
    signs = np.sign(W[iu])
    perm = rng.permutation(len(signs))
    Wo[iu] = np.abs(W[iu]) * signs[perm]
    return Wo


def rewire_edge_shuffle(W, rng):
    """Shuffle entire weight VALUES (sign+magnitude) across existing edge
    locations: same topology, exact same weight multiset, edges get a
    randomly reassigned value from that multiset."""
    Wo = np.zeros_like(W)
    iu = np.nonzero(W)
    vals = W[iu].copy()
    rng.shuffle(vals)
    Wo[iu] = vals
    return Wo


def rewire_degree_matched(W, rng, n_swap_mult=3):
    """Configuration-model null: double-edge-swap rewiring of the directed
    topology (preserves each neuron's in-degree and out-degree exactly),
    then the signed weight multiset is reassigned onto the new edge set by
    edge_shuffle. Strongest null: kills topology AND weight placement while
    matching degree sequence and the marginal weight distribution."""
    rows, cols = np.nonzero(W)
    vals = W[rows, cols].copy()
    edges = list(zip(rows.tolist(), cols.tolist()))
    edge_set = set(edges)
    n_edges = len(edges)
    n_swaps = n_swap_mult * n_edges
    edges = np.array(edges)
    for _ in range(n_swaps):
        a, b = rng.integers(0, n_edges, size=2)
        if a == b:
            continue
        i1, j1 = edges[a]; i2, j2 = edges[b]
        if i1 == i2 or j1 == j2 or i1 == j2 or i2 == j1:
            continue
        new1, new2 = (i1, j2), (i2, j1)
        if new1 in edge_set or new2 in edge_set:
            continue
        edge_set.discard((i1, j1)); edge_set.discard((i2, j2))
        edge_set.add(new1); edge_set.add(new2)
        edges[a] = new1; edges[b] = new2
    rng.shuffle(vals)
    Wo = np.zeros_like(W)
    ei = edges[:, 0]; ej = edges[:, 1]
    Wo[ei, ej] = vals
    return Wo


REWIRERS = {
    'sign_scramble': rewire_sign_scramble,
    'edge_shuffle': rewire_edge_shuffle,
    'degree_matched_random': rewire_degree_matched,
}


def make_cx(W, nodes, sim_seed):
    cx = RealCX(W, nodes)
    cx.rng = np.random.default_rng(sim_seed)
    cx.r = np.zeros(cx.N, np.float32)
    return cx


def drive_goal(cx, goal_phase, n_steps, gain=GOAL_GAIN):
    m = cx.fam == 'EPG'
    headings = np.empty(n_steps)
    for t in range(n_steps):
        ext = np.zeros(cx.N, np.float32)
        ext[m] = gain * np.cos(cx.ph[m] - goal_phase)
        cx.step(ext=ext)
        headings[t] = cx.bump_heading('EPG')[0]
    return headings


def circ_err_deg(a, b):
    d = (a - b + np.pi) % (2 * np.pi) - np.pi
    return np.degrees(np.abs(d))


def pointing_trial(W, nodes, sim_seed):
    errs = []
    for g_deg in GOALS_DEG:
        g = np.radians(g_deg)
        cx = make_cx(W, nodes, sim_seed)
        cx.seed(0.0, steps=N_SETTLE)
        headings = drive_goal(cx, g, N_HOLD)
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


def figure8_trial(W, nodes, sim_seed, n_steps=220, speed=0.12):
    ref = figure8_ref(400)
    tgt_heading = np.arctan2(np.gradient(ref[:, 1]), np.gradient(ref[:, 0]))
    idx = np.linspace(0, len(ref) - 1, n_steps).astype(int)
    cx = make_cx(W, nodes, sim_seed)
    cx.seed(tgt_heading[0], steps=N_SETTLE)
    pos = np.array([ref[0, 0], ref[0, 1]])
    path = [pos.copy()]
    for k in idx:
        g = tgt_heading[k]
        ext = np.zeros(cx.N, np.float32)
        m = cx.fam == 'EPG'
        ext[m] = GOAL_GAIN * np.cos(cx.ph[m] - g)
        cx.step(ext=ext)
        hd = cx.bump_heading('EPG')[0]
        pos = pos + speed * np.array([np.cos(hd), np.sin(hd)])
        path.append(pos.copy())
    path = np.array(path)
    return cross_track_rms(path, ref)


def p2p_trial(W, nodes, sim_seed, target, n_steps=250, speed=0.15, taper_r=1.0, arrive_r=1.0):
    cx = make_cx(W, nodes, sim_seed)
    pos = np.zeros(2)
    bearing0 = np.arctan2(target[1] - pos[1], target[0] - pos[0])
    cx.seed(bearing0, steps=N_SETTLE)
    arrived = False
    for _ in range(n_steps):
        d = target - pos
        dist = np.linalg.norm(d)
        g = np.arctan2(d[1], d[0])
        ext = np.zeros(cx.N, np.float32)
        m = cx.fam == 'EPG'
        ext[m] = GOAL_GAIN * np.cos(cx.ph[m] - g)
        cx.step(ext=ext)
        hd = cx.bump_heading('EPG')[0]
        v = speed * min(1.0, dist / taper_r)
        pos = pos + v * np.array([np.cos(hd), np.sin(hd)])
        if np.linalg.norm(target - pos) < arrive_r * 0.15:
            arrived = True
            break
    final_err = float(np.linalg.norm(target - pos))
    return arrived, final_err


def p2p_batch(W, nodes, sim_seed, n_targets=8, radius=4.0):
    rng = np.random.default_rng(sim_seed + 9000)
    angles = np.linspace(0, 2 * np.pi, n_targets, endpoint=False) + rng.uniform(0, 0.1)
    arrivals, errs = [], []
    for i, a in enumerate(angles):
        tgt = radius * np.array([np.cos(a), np.sin(a)])
        arr, err = p2p_trial(W, nodes, sim_seed * 100 + i, tgt)
        arrivals.append(arr); errs.append(err)
    return float(np.mean(arrivals)), float(np.mean(errs))


def sanity_check(W, nodes):
    print('=== W-sensitivity sanity check ===', flush=True)
    base = pointing_trial(W, nodes, sim_seed=0)
    scaled = pointing_trial(W * 0.1, nodes, sim_seed=0)
    zeroed = pointing_trial(W * 0.0, nodes, sim_seed=0)
    print(f'  intact W pointing error:      {base:.2f} deg', flush=True)
    print(f'  W scaled x0.1 pointing error: {scaled:.2f} deg', flush=True)
    print(f'  W zeroed pointing error:      {zeroed:.2f} deg', flush=True)
    ok = abs(scaled - base) > 1.0 or abs(zeroed - base) > 1.0
    print(f'  harness is W-sensitive: {ok}', flush=True)
    if not ok:
        raise SystemExit('SANITY CHECK FAILED: harness output does not depend on W. Aborting.')
    return dict(intact=base, scaled_0p1=scaled, zeroed=zeroed, w_sensitive=bool(ok))


def cohend_ci(x, y):
    nx, ny = len(x), len(y)
    pooled_sd = np.sqrt(((nx - 1) * np.var(x, ddof=1) + (ny - 1) * np.var(y, ddof=1)) / (nx + ny - 2))
    d = (np.mean(x) - np.mean(y)) / pooled_sd if pooled_sd > 0 else 0.0
    se = np.sqrt((nx + ny) / (nx * ny) + d ** 2 / (2 * (nx + ny)))
    return float(d), float(d - 1.96 * se), float(d + 1.96 * se)


def perm_test(x, y, n_perm=10000, seed=0):
    rng = np.random.default_rng(seed)
    obs = np.mean(x) - np.mean(y)
    pooled = np.concatenate([x, y])
    n = len(x)
    diffs = np.empty(n_perm)
    for i in range(n_perm):
        rng.shuffle(pooled)
        diffs[i] = np.mean(pooled[:n]) - np.mean(pooled[n:])
    p = float(np.mean(np.abs(diffs) >= np.abs(obs)))
    return p


def mde_at_n(n, alpha=0.05, power=0.8):
    from scipy.stats import norm
    z_a, z_b = norm.ppf(1 - alpha / 2), norm.ppf(power)
    return float((z_a + z_b) * np.sqrt(2.0 / n))


def stats_block(intact_vals, null_vals):
    intact_vals, null_vals = np.array(intact_vals), np.array(null_vals)
    mean, sd = float(np.mean(null_vals)), float(np.std(null_vals, ddof=1))
    ci = stats.t.interval(0.95, len(null_vals) - 1, loc=mean, scale=sd / np.sqrt(len(null_vals)))
    d, dlo, dhi = cohend_ci(null_vals, intact_vals)
    p = perm_test(null_vals, intact_vals)
    return dict(mean=mean, sd=sd, ci95=[float(ci[0]), float(ci[1])],
                cohens_d=d, cohens_d_ci95=[dlo, dhi], p_perm=p)


def run(seeds, out_path, quick=False):
    print('loading FlyWire CX connectome...', flush=True)
    W0, rid, nodes0 = load(FLY_NPZ, FLY_CSV)
    fam = nodes0['fam'].values
    phase = epg_spectral_phase(W0, fam)
    nodes = nodes0.copy(); nodes['phase'] = phase

    print('loading MaleCNS reference connectome...', flush=True)
    Wm, ridm, nodesm0 = load(MALE_NPZ, MALE_CSV)
    famm = nodesm0['fam'].values
    phasem = epg_spectral_phase(Wm, famm)
    nodesm = nodesm0.copy(); nodesm['phase'] = phasem

    global GOALS_DEG, N_HOLD
    if quick:
        GOALS_DEG = np.arange(0, 360, 90)
        N_HOLD = 60

    sanity = sanity_check(W0, nodes)

    conditions = ['intact', 'sign_scramble', 'edge_shuffle', 'degree_matched_random']
    results = {'sanity_check': sanity, 'conditions': {}, 'intact_male': {}}

    for cond in conditions:
        print(f'=== condition: {cond} ===', flush=True)
        results['conditions'][cond] = {'pointing_deg': [], 'fig8_rms': [], 'p2p_arrival': [], 'p2p_err': []}
        for s in range(seeds):
            t0 = time.time()
            if cond == 'intact':
                Wc = W0
            else:
                rng = np.random.default_rng(1000 * s + hash(cond) % 1000)
                Wc = REWIRERS[cond](W0, rng)
            pt = pointing_trial(Wc, nodes, sim_seed=s)
            f8 = figure8_trial(Wc, nodes, sim_seed=s)
            arr, perr = p2p_batch(Wc, nodes, sim_seed=s)
            results['conditions'][cond]['pointing_deg'].append(pt)
            results['conditions'][cond]['fig8_rms'].append(f8)
            results['conditions'][cond]['p2p_arrival'].append(arr)
            results['conditions'][cond]['p2p_err'].append(perr)
            print(f'  [{cond}] seed {s + 1}/{seeds}  pointing={pt:.2f}deg fig8_rms={f8:.3f} '
                  f'p2p_arrival={arr:.2f} p2p_err={perr:.3f}  ({time.time() - t0:.1f}s)', flush=True)

    print('=== condition: intact_male (reference) ===', flush=True)
    results['intact_male'] = {'pointing_deg': [], 'fig8_rms': [], 'p2p_arrival': [], 'p2p_err': []}
    for s in range(seeds):
        t0 = time.time()
        pt = pointing_trial(Wm, nodesm, sim_seed=s)
        f8 = figure8_trial(Wm, nodesm, sim_seed=s)
        arr, perr = p2p_batch(Wm, nodesm, sim_seed=s)
        results['intact_male']['pointing_deg'].append(pt)
        results['intact_male']['fig8_rms'].append(f8)
        results['intact_male']['p2p_arrival'].append(arr)
        results['intact_male']['p2p_err'].append(perr)
        print(f'  [intact_male] seed {s + 1}/{seeds}  pointing={pt:.2f}deg fig8_rms={f8:.3f} '
              f'p2p_arrival={arr:.2f} p2p_err={perr:.3f}  ({time.time() - t0:.1f}s)', flush=True)

    intact = results['conditions']['intact']
    stats_out = {}
    for cond in ['sign_scramble', 'edge_shuffle', 'degree_matched_random']:
        stats_out[cond] = {}
        for metric in ['pointing_deg', 'fig8_rms', 'p2p_err']:
            stats_out[cond][metric] = stats_block(intact[metric], results['conditions'][cond][metric])
        stats_out[cond]['p2p_arrival_intact_mean'] = float(np.mean(intact['p2p_arrival']))
        stats_out[cond]['p2p_arrival_null_mean'] = float(np.mean(results['conditions'][cond]['p2p_arrival']))
    results['stats_vs_intact'] = stats_out
    results['min_detectable_effect_d_n20'] = mde_at_n(seeds)
    results['config'] = dict(seeds=seeds, n_goals=len(GOALS_DEG), n_hold=int(N_HOLD),
                              n_settle=N_SETTLE, goal_gain=GOAL_GAIN, quick=quick)

    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f'wrote {out_path}', flush=True)
    return results


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--seeds', type=int, default=20)
    ap.add_argument('--out', default='../data/ablation_results.json')
    ap.add_argument('--quick', action='store_true', help='reduced sim length for a fast smoke test')
    args = ap.parse_args()
    run(args.seeds, args.out, quick=args.quick)
