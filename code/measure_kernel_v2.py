"""Acceptance test for the CHORUS monograph's ~24 deg recurrent-kernel figure
(CHORUS_fine_control.md section 2 / CHORUS_fine_control.md section 2), written
per KERNEL_RECOVERY.md forensics.

This script does NOT introduce a new free parameter to force ~24 deg. It
enumerates every candidate explanation that survives in the repo (half-width
definition, which disynaptic loops are summed, phase-recovery method, fit
range) and reports the kappa / half-width each one gives on the SAME FlyWire
data code/measure_kernel.py already loads (data/cx_real.npz +
cx_nodes.csv). It also reports, separately and clearly labeled as NOT an
independent measurement, what half-width the monograph's own hardcoded
calibrated kappa (cx_ring.py, kappa=5.6) implies under each definition, since
that is the only surviving trace of the original number.

Verdict printed at the end: REPRODUCED only if some combination without an
ad hoc rescaling lands in [22, 26] deg with an inhibitory surround (the
stated acceptance band). See KERNEL_RECOVERY.md for the full writeup.
"""
import numpy as np
from scipy.optimize import curve_fit
import measure_kernel as mk

ACCEPT_LO, ACCEPT_HI = 22.0, 26.0
CALIBRATED_KAPPA = 5.6  # cx_ring.py hardcoded value, the only surviving trace


def von_mises(d, A, kappa, base):
    return base + A * np.exp(kappa * (np.cos(d) - 1.0))


def hwhm_exact_deg(kappa):
    if kappa <= 0:
        return np.nan
    arg = 1.0 + np.log(0.5) / kappa
    if arg < -1 or arg > 1:
        return np.nan
    return np.degrees(np.arccos(arg))


def sigma_deg(kappa):
    if kappa <= 0:
        return np.nan
    return np.degrees(1.0 / np.sqrt(kappa))


def fit_subset(K, phase, n_bins=24, max_deg=180.0, weight_by_count=False):
    n = K.shape[0]
    iu = np.triu_indices(n, k=1)
    d = np.abs((phase[iu[0]] - phase[iu[1]] + np.pi) % (2 * np.pi) - np.pi)
    vals = K[iu]
    m = d <= np.radians(max_deg)
    d, vals = d[m], vals[m]
    edges = np.linspace(0, np.radians(max_deg), n_bins + 1)
    idx = np.clip(np.digitize(d, edges) - 1, 0, n_bins - 1)
    bc = (edges[:-1] + edges[1:]) / 2
    bm = np.array([vals[idx == b].mean() if np.any(idx == b) else np.nan for b in range(n_bins)])
    cnt = np.array([np.sum(idx == b) for b in range(n_bins)])
    ok = ~np.isnan(bm)
    bc, bm, cnt = bc[ok], bm[ok], cnt[ok]
    sigma = 1.0 / np.sqrt(np.maximum(cnt, 1)) if weight_by_count else None
    A0 = max(bm[0] - bm[-1], 1e-6)
    try:
        popt, _ = curve_fit(von_mises, bc, bm, p0=[A0, 5.0, bm[-1]], sigma=sigma, maxfev=20000)
        A, kappa, base = popt
        return dict(ok=True, kappa=kappa, base=base)
    except Exception as ex:
        return dict(ok=False, error=str(ex))


def kernel_from_loops(W, fam, epg, loops):
    K = np.zeros((len(epg), len(epg)))
    for m_fam in loops:
        idx = np.where(fam == m_fam)[0]
        if len(idx) == 0:
            continue
        K += W[np.ix_(epg, idx)] @ W[np.ix_(idx, epg)]
    return K


def main():
    print('=== Acceptance test: reproduce ~24 deg FlyWire kernel half-width ===', flush=True)
    W, root_ids, fam = mk.load('../data/cx_real.npz', '../data/cx_nodes.csv')
    epg = np.where(fam == 'EPG')[0]
    print(f'N={W.shape[0]} n_EPG={len(epg)}', flush=True)

    full_loops = ['PEG', 'Delta7', 'PEN_a', 'PEN_b']
    K_full = kernel_from_loops(W, fam, epg, full_loops)
    phase = mk.spectral_phase(K_full)

    print('\n-- Candidate (b): half-width definition, full loop set, spectral phase --', flush=True)
    fit = fit_subset(K_full, phase)
    results = []
    if fit['ok']:
        k = fit['kappa']
        hw_exact, hw_sigma = hwhm_exact_deg(k), sigma_deg(k)
        surround = 'inhibitory' if fit['base'] < 0 else 'excitatory'
        print(f'  kappa={k:.3f} surround={surround}')
        print(f'  HWHM (exact, arccos formula, measure_kernel.py convention): {hw_exact:.1f} deg')
        print(f'  circular-SD approx (1/sqrt(kappa), radians->deg):           {hw_sigma:.1f} deg')
        results += [('full loops, exact HWHM', hw_exact, surround),
                    ('full loops, sigma approx', hw_sigma, surround)]

    print('\n-- Candidate (c): which disynaptic loops are summed, spectral phase --', flush=True)
    subsets = {
        'PEG+Delta7+PEN_a+PEN_b (all 4, as measure_kernel.py)': full_loops,
        'PEG+Delta7 only': ['PEG', 'Delta7'],
        'Delta7+PEN_a+PEN_b (drop PEG)': ['Delta7', 'PEN_a', 'PEN_b'],
        'PEG+PEN_a+PEN_b (drop Delta7)': ['PEG', 'PEN_a', 'PEN_b'],
        'PEG only': ['PEG'],
        'Delta7 only': ['Delta7'],
        'PEN_a+PEN_b only': ['PEN_a', 'PEN_b'],
    }
    for name, loops in subsets.items():
        K = kernel_from_loops(W, fam, epg, loops)
        f = fit_subset(K, phase)
        if not f['ok']:
            print(f'  {name:45s} FIT FAILED ({f["error"]})')
            continue
        k = f['kappa']
        surround = 'inhibitory' if f['base'] < 0 else 'excitatory'
        hw_exact, hw_sigma = hwhm_exact_deg(k), sigma_deg(k)
        print(f'  {name:45s} kappa={k:6.3f} exact={hw_exact:6.1f} sigma={hw_sigma:6.1f} surround={surround}')
        if surround == 'inhibitory' and k > 0.5:
            results += [(f'{name}, exact', hw_exact, surround), (f'{name}, sigma', hw_sigma, surround)]
        elif surround == 'inhibitory':
            print(f'    (excluded from range: kappa={k:.3f} is a near-flat degenerate fit, not a real bump)')

    print('\n-- Candidate (d): fit range / weighting, full loops, spectral phase --', flush=True)
    for label, kw in [('n_bins=12', dict(n_bins=12)), ('n_bins=48', dict(n_bins=48)),
                       ('count-weighted fit', dict(weight_by_count=True)),
                       ('near-field only, max_deg=90', dict(max_deg=90.0)),
                       ('near-field only, max_deg=60', dict(max_deg=60.0))]:
        f = fit_subset(K_full, phase, **kw)
        if not f['ok']:
            print(f'  {label:30s} FIT FAILED')
            continue
        k = f['kappa']
        surround = 'inhibitory' if f['base'] < 0 else 'excitatory'
        hw_exact, hw_sigma = hwhm_exact_deg(k), sigma_deg(k)
        flag = '' if surround == 'inhibitory' else '  <- surround sign flips, not defensible per spec'
        print(f'  {label:30s} kappa={k:6.3f} exact={hw_exact:6.1f} sigma={hw_sigma:6.1f} surround={surround}{flag}')
        if surround == 'inhibitory' and k > 0.5:
            results += [(f'{label}, exact', hw_exact, surround), (f'{label}, sigma', hw_sigma, surround)]

    print('\n-- Trace of the calibrated kappa hardcoded in cx_ring.py (not an independent measurement) --')
    print(f'  cx_ring.py kappa={CALIBRATED_KAPPA}')
    print(f'  exact HWHM formula:  {hwhm_exact_deg(CALIBRATED_KAPPA):.1f} deg')
    print(f'  sigma approx formula: {sigma_deg(CALIBRATED_KAPPA):.1f} deg  <- matches the published ~24 deg')
    print('  This is consistent with "half-width" in the monograph meaning the circular-SD')
    print('  approximation 1/sqrt(kappa), not the exact arccos HWHM measure_kernel.py reports.')
    print('  But that convention alone does not rescue the FlyWire measurement: applying the same')
    print('  sigma-approx formula to every independently measured kappa above still misses 24 deg,')
    print('  because the measured kappa itself (~3.4-3.7) differs from the calibrated 5.6-5.7 needed.')
    print('  The anatomical EPG phase (position around the protocerebral bridge, CHORUS_fine_control.md')
    print('  section 1) that the original study used is not present in cx_nodes.csv (only root_id,')
    print('  cell_type, side, nt survive), so that phase-recovery method cannot be tested here; inventing')
    print('  an ordering to fill that gap would be exactly the kind of fudge factor this test forbids.')

    in_band = [(n, hw) for n, hw, s in results if ACCEPT_LO <= hw <= ACCEPT_HI]
    print(f'\n-- Full range of defensible half-widths tested on real FlyWire kernel data --')
    all_hw = sorted(hw for _, hw, s in results if not np.isnan(hw))
    print(f'  {[round(h,1) for h in all_hw]}')
    print(f'  range: {min(all_hw):.1f} - {max(all_hw):.1f} deg')

    print('\n=== VERDICT ===')
    if in_band:
        print('REPRODUCED:', in_band)
    else:
        print('NOT REPRODUCED. No definition/loop-subset/fit-range combination tested on the real')
        print('FlyWire disynaptic kernel, using only what survives in this repo, lands in the')
        print('22-26 deg acceptance band with an inhibitory surround. The published 24 deg figure')
        print('cannot currently be reproduced from surviving code and data. See KERNEL_RECOVERY.md.')


if __name__ == '__main__':
    main()
