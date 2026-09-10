"""Density-matched controls for the MaleCNS CX extraction vs FlyWire.

The male CX (noFC2, family-matched to FlyWire) has ~1.5x the edges/neuron and
~2.6x the synapses/neuron of FlyWire. That gap is a plausible reconstruction
artifact (different segmentation, proofreading depth, minconf threshold), not
necessarily biology. This script prunes weak edges from the male noFC2 graph
under two independent matching criteria and reports where each lands, plus
whether the pruning is selective (family-biased, E/I-biased).

Usage: python code/match_density.py --in-dir data/malecns_cx --out-dir data/malecns_cx
"""
import argparse, re
from pathlib import Path
import numpy as np
import pandas as pd

FLYWIRE_MEAN_OUTDEGREE = 64909 / 1051   # 61.76
FLYWIRE_SYN_PER_NEURON = 381592 / 1051  # 363.08


def strip_paren(s):
    return re.sub(r'\(.*?\)', '', str(s))


def family_of(cell_type):
    fams = ['EPGt', 'EPG', 'PEN_a', 'PEN_b', 'PEG', 'Delta7', 'PFL1', 'PFL2', 'PFL3',
            'PFNa', 'PFNd', 'PFNm', 'PFNp', 'PFNv', 'PFR', 'PFGs', 'IbSpsP',
            'ER1', 'ER2', 'ER3', 'ER4', 'ER5', 'ER6', 'ExR', 'LNO1', 'LNO2', 'LNOa', 'LPsP']
    t = strip_paren(cell_type)
    for f in fams:
        if t.startswith(f):
            return f
    return 'other'


def find_threshold(W, target_metric, target_value, N):
    """Search integer weight thresholds t (keep |w|>=t) for the one whose
    metric (edges/neuron or synapses/neuron) is closest to target_value."""
    absw = np.abs(W)
    max_w = int(absw.max())
    print(f'  searching thresholds 1..{max_w} for target {target_metric}={target_value:.2f}', flush=True)
    best_t, best_err, best_stats = None, np.inf, None
    for t in range(1, max_w + 1):
        keep = absw >= t
        n_edges = int(keep.sum())
        n_syn = float(absw[keep].sum())
        if target_metric == 'edges':
            val = n_edges / N
        else:
            val = n_syn / N
        err = abs(val - target_value)
        if err < best_err:
            best_err, best_t, best_stats = err, t, (n_edges, n_syn)
        if n_edges == 0:
            break
        if t % 20 == 0 or t == max_w:
            print(f'    t={t} edges/neuron={n_edges/N:.2f} syn/neuron={n_syn/N:.2f}', flush=True)
    return best_t, best_err, best_stats


def prune(W, t):
    keep = np.abs(W) >= t
    Wp = np.where(keep, W, 0.0).astype(np.float32)
    return Wp


def family_pruning_report(W_full, W_pruned, nodes, root_ids):
    fam = nodes.set_index('root_id').loc[root_ids, 'cell_type'].map(family_of).to_numpy()
    rows = []
    pre_fam = np.repeat(fam[:, None], W_full.shape[1], axis=1)
    for f in sorted(set(fam)):
        mask_pre = fam == f
        edges_full = int((W_full[mask_pre] != 0).sum())
        edges_pruned = int((W_pruned[mask_pre] != 0).sum())
        if edges_full == 0:
            continue
        frac_kept = edges_pruned / edges_full
        rows.append((f, edges_full, edges_pruned, frac_kept))
    df = pd.DataFrame(rows, columns=['family', 'edges_full', 'edges_pruned', 'frac_kept'])
    return df.sort_values('frac_kept')


def ei_report(W):
    exc = int((W > 0).sum())
    inh = int((W < 0).sum())
    return exc, inh


def delta7_epg_check(W_full, W_pruned, nodes, root_ids):
    fam = nodes.set_index('root_id').loc[root_ids, 'cell_type'].map(family_of).to_numpy()
    d7 = fam == 'Delta7'
    epg = fam == 'EPG'
    d7_full = int((W_full[d7] != 0).sum())
    d7_pruned = int((W_pruned[d7] != 0).sum())
    epg_full = int((W_full[epg] != 0).sum())
    epg_pruned = int((W_pruned[epg] != 0).sum())
    d7_frac = d7_pruned / d7_full if d7_full else float('nan')
    epg_frac = epg_pruned / epg_full if epg_full else float('nan')
    return dict(d7_edges_full=d7_full, d7_edges_kept=d7_pruned, d7_frac_kept=d7_frac,
                epg_edges_full=epg_full, epg_edges_kept=epg_pruned, epg_frac_kept=epg_frac)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--in-dir', default='data/malecns_cx')
    ap.add_argument('--out-dir', default='data/malecns_cx')
    args = ap.parse_args()
    in_dir = Path(args.in_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print('loading male noFC2 extraction...', flush=True)
    d = np.load(in_dir / 'cx_real_male_noFC2.npz')
    W = d['W'].astype(np.float32)
    root_ids = d['root_ids']
    nodes = pd.read_csv(in_dir / 'cx_nodes_male_noFC2.csv')
    N = W.shape[0]
    print(f'  N={N} edges={int((W!=0).sum())} synapses={float(np.abs(W).sum()):.0f}', flush=True)

    print('criterion (a): edge-count matching to FlyWire mean out-degree', FLYWIRE_MEAN_OUTDEGREE)
    t_edges, err_edges, stats_edges = find_threshold(W, 'edges', FLYWIRE_MEAN_OUTDEGREE, N)
    print(f'  chosen threshold t={t_edges}, edges={stats_edges[0]}, edges/neuron={stats_edges[0]/N:.2f}, err={err_edges:.3f}')

    print('criterion (b): synapse-count matching to FlyWire synapses/neuron', FLYWIRE_SYN_PER_NEURON)
    t_syn, err_syn, stats_syn = find_threshold(W, 'synapses', FLYWIRE_SYN_PER_NEURON, N)
    print(f'  chosen threshold t={t_syn}, synapses={stats_syn[1]:.0f}, synapses/neuron={stats_syn[1]/N:.2f}, err={err_syn:.3f}')

    print(f'thresholds agree: {t_edges == t_syn} (t_edges={t_edges}, t_syn={t_syn})')

    W_edges = prune(W, t_edges)
    W_syn = prune(W, t_syn)

    np.savez(out_dir / 'cx_real_male_matched_edges.npz', W=W_edges, root_ids=root_ids.astype(np.int64))
    nodes.to_csv(out_dir / 'cx_nodes_male_matched_edges.csv', index=False)
    np.savez(out_dir / 'cx_real_male_matched_syn.npz', W=W_syn, root_ids=root_ids.astype(np.int64))
    nodes.to_csv(out_dir / 'cx_nodes_male_matched_syn.csv', index=False)
    print('wrote cx_real_male_matched_edges.npz, cx_real_male_matched_syn.npz + node csvs', flush=True)

    print('\n--- selectivity of pruning ---')
    for tag, Wp, t in [('edge-matched', W_edges, t_edges), ('synapse-matched', W_syn, t_syn)]:
        print(f'\n[{tag}] threshold t={t}')
        fr = family_pruning_report(W, Wp, nodes, root_ids)
        print(fr.to_string(index=False))
        exc_full, inh_full = ei_report(W)
        exc_p, inh_p = ei_report(Wp)
        print(f'  E/I full: {exc_full}/{inh_full} = {exc_full/inh_full:.3f}')
        print(f'  E/I {tag}: {exc_p}/{inh_p} = {exc_p/max(inh_p,1):.3f}')
        d7 = delta7_epg_check(W, Wp, nodes, root_ids)
        print(f'  Delta7 edges kept: {d7["d7_edges_kept"]}/{d7["d7_edges_full"]} ({d7["d7_frac_kept"]:.3f})')
        print(f'  EPG edges kept:    {d7["epg_edges_kept"]}/{d7["epg_edges_full"]} ({d7["epg_frac_kept"]:.3f})')
        bias = d7['d7_frac_kept'] - d7['epg_frac_kept']
        print(f'  Delta7-vs-EPG retention gap: {bias:+.3f} ({"Delta7 pruned MORE" if bias < 0 else "Delta7 pruned LESS or equal"})')

    print('\ndone.')


if __name__ == '__main__':
    main()
