"""Measure the effective EPG->EPG recurrent kernel from real disynaptic loops
(EPG->PEG->EPG, EPG->Delta7->EPG, EPG->PEN_a/PEN_b->EPG) and fit a von Mises
profile to get a half-width in degrees, per docs/CHORUS_fine_control.md
section 2 / docs/PAPER.md section 2 ("~24 deg half-width with a weak
inhibitory surround"). No existing implementation of this measurement was
found anywhere in code/ (cx_ring.py just hardcodes kappa=5.6 as the already-
calibrated kernel; it does not derive it from data), so this is a fresh
implementation, written to be run against any of the CX npz/csv pairs
(FlyWire or any male variant) for direct comparison.

EPG angular phase is not stored in the node csvs, so it is recovered here by
spectral embedding of the EPG-EPG effective (disynaptic) connectivity graph:
the Fiedler-like first two nontrivial eigenvectors of the symmetrized
effective-kernel graph Laplacian give a 2D embedding, and each EPG neuron's
angle in that embedding is its phase around the ring. This is an anatomical
estimate, independent per connectome, so FlyWire and male CX get their own
phases rather than sharing an assumed layout.

Usage: python code/measure_kernel.py --npz <path> --csv <path> --tag <name>
"""
import argparse, re
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit

FAMILIES = ['EPGt', 'EPG', 'PEN_a', 'PEN_b', 'PEG', 'Delta7']


def strip_paren(s):
    return re.sub(r'\(.*?\)', '', str(s))


def family_of(cell_type):
    t = strip_paren(cell_type)
    for f in FAMILIES:
        if t.startswith(f):
            return f
    return 'other'


def load(npz, csv):
    d = np.load(npz)
    W = d['W'].astype(np.float64)
    root_ids = d['root_ids']
    nodes = pd.read_csv(csv).set_index('root_id').loc[root_ids].reset_index()
    fam = nodes['cell_type'].map(family_of).to_numpy()
    return W, root_ids, fam


def effective_epg_kernel(W, fam):
    """K[i,j] = sum over intermediate populations m in {PEG, Delta7, PEN_a, PEN_b}
    of W[epg_i, m] @ W[m, epg_j], the disynaptic EPG->m->EPG effective interaction."""
    epg = np.where(fam == 'EPG')[0]
    n = len(epg)
    K = np.zeros((n, n))
    for m_fam in ['PEG', 'Delta7', 'PEN_a', 'PEN_b']:
        m_idx = np.where(fam == m_fam)[0]
        if len(m_idx) == 0:
            continue
        W_em = W[np.ix_(epg, m_idx)]
        W_me = W[np.ix_(m_idx, epg)]
        K += W_em @ W_me
    return K, epg


def spectral_phase(K):
    """Fiedler-style 2D spectral embedding of the symmetrized effective-kernel
    graph; angle in that embedding = anatomical phase around the ring."""
    A = np.abs(K)
    np.fill_diagonal(A, 0)
    A = (A + A.T) / 2
    deg = A.sum(1)
    deg[deg == 0] = 1e-9
    Dinv = np.diag(1.0 / np.sqrt(deg))
    L = np.eye(len(A)) - Dinv @ A @ Dinv
    w, v = np.linalg.eigh(L)
    # skip the trivial near-zero eigenvector, take next two
    order = np.argsort(w)
    v1, v2 = v[:, order[1]], v[:, order[2]]
    phase = np.arctan2(v2, v1)
    return phase


def von_mises(d, A, kappa, base):
    return base + A * np.exp(kappa * (np.cos(d) - 1.0))


def fit_kernel_halfwidth(K, phase, n_bins=24):
    n = K.shape[0]
    iu = np.triu_indices(n, k=1)
    d = np.abs((phase[iu[0]] - phase[iu[1]] + np.pi) % (2 * np.pi) - np.pi)
    vals = K[iu]
    bin_edges = np.linspace(0, np.pi, n_bins + 1)
    bin_idx = np.digitize(d, bin_edges) - 1
    bin_idx = np.clip(bin_idx, 0, n_bins - 1)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    bin_means = np.array([vals[bin_idx == b].mean() if np.any(bin_idx == b) else np.nan for b in range(n_bins)])
    ok = ~np.isnan(bin_means)
    bc, bm = bin_centers[ok], bin_means[ok]
    A0 = max(bm[0] - bm[-1], 1e-6)
    base0 = bm[-1]
    try:
        popt, _ = curve_fit(von_mises, bc, bm, p0=[A0, 5.0, base0], maxfev=20000)
        A, kappa, base = popt
        if kappa <= 0:
            raise RuntimeError('non-positive kappa fit')
        hwhm_rad = np.arccos(1.0 + np.log(0.5) / kappa)
        hwhm_deg = np.degrees(hwhm_rad)
        surround = 'inhibitory' if base < 0 else 'excitatory' if base > 0 else 'none'
        return dict(A=A, kappa=kappa, base=base, hwhm_deg=hwhm_deg, surround=surround,
                    fit_ok=True, bin_centers=bc, bin_means=bm)
    except Exception as ex:
        return dict(fit_ok=False, error=str(ex), bin_centers=bc, bin_means=bm)


def measure(npz, csv, tag):
    print(f'[{tag}] loading {npz} / {csv}', flush=True)
    W, root_ids, fam = load(npz, csv)
    n_epg = int((fam == 'EPG').sum())
    print(f'  N={W.shape[0]} n_EPG={n_epg}', flush=True)
    print('  computing disynaptic effective EPG-EPG kernel...', flush=True)
    K, epg_idx = effective_epg_kernel(W, fam)
    print('  spectral phase embedding...', flush=True)
    phase = spectral_phase(K)
    print('  fitting von Mises kernel...', flush=True)
    fit = fit_kernel_halfwidth(K, phase)
    fit['tag'] = tag
    fit['n_epg'] = n_epg
    if fit['fit_ok']:
        print(f'  [{tag}] kappa={fit["kappa"]:.3f} hwhm={fit["hwhm_deg"]:.1f} deg surround={fit["surround"]} (base={fit["base"]:.4g})', flush=True)
    else:
        print(f'  [{tag}] fit failed: {fit["error"]}', flush=True)
    return fit


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--npz', required=True)
    ap.add_argument('--csv', required=True)
    ap.add_argument('--tag', required=True)
    args = ap.parse_args()
    measure(args.npz, args.csv, args.tag)


if __name__ == '__main__':
    main()
