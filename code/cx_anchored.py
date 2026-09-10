"""CHORUS anchored model: Shiu et al. 2023/2024 (Cell) parameter discipline
applied to the CX connectome. Connection weight = connectome synapse count
* neurotransmitter sign * ONE global scalar W_syn. W_syn is the only free
parameter; everything else is fixed from the connectome or from cited
literature values (see ANCHORED_MODEL.md for the anchor and its citation).

Sign assignment (Dale's law, one sign per neuron, applied to that neuron's
entire outgoing row):
  acetylcholine            -> excitatory (+1)
  gaba, glutamate          -> inhibitory (-1)
  dopamine, serotonin,
  octopamine, unresolved   -> excitatory (+1), i.e. kept as the ORIGINAL
                               FlyWire extraction's default-to-excitatory
                               convention for cell-types with unclear or
                               non-fast-ionotropic transmitter identity
                               (see MALECNS_EXTRACTION.md). This is a
                               deliberate choice to stay comparable with the
                               existing extraction rather than inventing a
                               new convention; the affected neuron counts
                               are printed by load_signed() below.

Synapse-count magnitude is taken as |W| from the existing signed cx_real.npz
matrix (row i = presynaptic neuron i's outgoing synapse counts, confirmed
sign-consistent per row: 0 of 1051 FlyWire rows mix sign). Re-deriving the
sign from the nt column and discarding the existing per-edge sign is what
makes this a Shiu-style single-transmitter-per-neuron model rather than the
original per-edge-NT extraction.

Dynamics: a rate model (cheaper than LIF, explicitly allowed by the task).
tau, dt, and noise are NOT fit to this connectome; tau matches cx_spiking.py's
tau_m=20 ms LIF membrane time constant (reused, not invented), dt=0.5 ms
matches cx_spiking.py's dt_ms, and noise=0.02 matches cx_ring.py's calibrated
ring noise magnitude. Bias is fixed at 0 (no free threshold parameter). Only
W_syn is swept and frozen by anchor_sweep.py.
"""
import numpy as np
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from cx_real_dynamics import load as load_raw
from measure_kernel import effective_epg_kernel, spectral_phase

TAU_MS = 20.0
DT_MS = 0.5
NOISE = 0.02
BIAS = 0.0

NT_SIGN = {'acetylcholine': 1.0, 'gaba': -1.0, 'glutamate': -1.0}
DEFAULT_EXCITATORY_NT = ['dopamine', 'serotonin', 'octopamine']


def load_signed(npz, csv, verbose=True):
    W, rid, nodes = load_raw(npz, csv)
    nt = nodes['nt'].astype(str).str.lower().values
    sign = np.ones(len(nt), np.float64)
    for k, v in NT_SIGN.items():
        sign[nt == k] = v
    n_default = 0
    for k in DEFAULT_EXCITATORY_NT:
        n_default += int((nt == k).sum())
    n_unresolved = int((~np.isin(nt, list(NT_SIGN.keys()) + DEFAULT_EXCITATORY_NT)).sum())
    n_default += n_unresolved
    if verbose:
        print(f'sign assignment: N={len(nt)} neurons', flush=True)
        for k in list(NT_SIGN.keys()) + DEFAULT_EXCITATORY_NT:
            print(f'  {k}: {int((nt == k).sum())}', flush=True)
        print(f'  defaulted-to-excitatory (dopamine/serotonin/octopamine/unresolved): '
              f'{n_default} of {len(nt)} ({100.0 * n_default / len(nt):.1f}%)', flush=True)
    Wmag = np.abs(W)
    Wsigned = (sign[:, None] * Wmag).astype(np.float64)
    fam = nodes['fam'].values
    K, epg_idx = effective_epg_kernel(W, fam)
    phase_epg = spectral_phase(K)
    phase = np.full(W.shape[0], np.nan)
    phase[epg_idx] = phase_epg
    nodes = nodes.copy()
    nodes['phase'] = phase
    return Wsigned, rid, nodes, dict(n_neurons=len(nt), n_default_excitatory=n_default,
                                      n_gaba=int((nt == 'gaba').sum()),
                                      n_glutamate=int((nt == 'glutamate').sum()),
                                      n_ach=int((nt == 'acetylcholine').sum()))


class AnchoredCX:
    """Rate model. r in [0, inf), single free parameter W_syn."""

    def __init__(self, Wsigned, nodes, W_syn, tau_ms=TAU_MS, dt_ms=DT_MS, noise=NOISE, bias=BIAS, seed=0):
        self.Wsigned = Wsigned.astype(np.float64)
        self.N = Wsigned.shape[0]
        self.W_syn = W_syn
        self.tau, self.dt, self.noise, self.bias = tau_ms, dt_ms, noise, bias
        self.fam = nodes['fam'].values
        self.ph = nodes['phase'].values.astype(np.float64)
        self.FI = {f: np.where(self.fam == f)[0] for f in pd.unique(self.fam)}
        self.rng = np.random.default_rng(seed)
        self.reset()

    def reset(self):
        self.r = np.zeros(self.N, np.float64)

    @staticmethod
    def phi(x):
        return 1.0 / (1.0 + np.exp(-x))

    def step(self, ext=None):
        inp = self.W_syn * (self.Wsigned.T @ self.r) + self.bias
        if ext is not None:
            inp = inp + ext
        self.r = self.r + self.dt / self.tau * (-self.r + self.phi(inp)) + \
            self.noise * self.rng.standard_normal(self.N)
        self.r = np.clip(self.r, 0, None)
        return self.r

    def seed_bump(self, phase, steps=400, gain=6.0):
        m = self.fam == 'EPG'
        for _ in range(steps):
            ext = np.zeros(self.N)
            ext[m] = gain * np.cos(self.ph[m] - phase)
            self.step(ext=ext)

    def free_run(self, steps):
        for _ in range(steps):
            self.step()

    def epg_profile(self):
        idx = self.FI.get('EPG', np.array([], int))
        return self.r[idx], self.ph[idx]

    def bump_heading(self, pop='EPG'):
        idx = self.FI.get(pop, np.array([], int))
        r, ph = self.r[idx], self.ph[idx]
        z = np.sum(r * np.exp(1j * ph))
        return np.angle(z), np.abs(z) / (r.sum() + 1e-9)


def bump_fwhm_deg(r, ph):
    """Direct FWHM of the activity profile around the ring, same definition
    as Kim et al. 2017 Science (angular distance between the two points
    where amplitude crosses half of peak). Returns nan if no clear single
    peak (bump collapsed, saturated, or multi-modal)."""
    ok = np.isfinite(ph) & np.isfinite(r)
    r, ph = r[ok], ph[ok]
    if len(r) < 5 or r.max() < 1e-6:
        return np.nan
    order = np.argsort(ph)
    ps = np.unwrap(ph[order])
    rs = r[order]
    n = len(rs)
    ps3 = np.concatenate([ps - 2 * np.pi, ps, ps + 2 * np.pi])
    rs3 = np.tile(rs, 3)
    trough = float(rs.min())
    peak_i = n + int(np.argmax(rs))
    peak_val = rs3[peak_i]
    amp = peak_val - trough
    if amp <= 1e-9:
        return np.nan
    half = trough + amp / 2.0
    lo = peak_i
    while lo > 0 and rs3[lo] > half:
        lo -= 1
    hi = peak_i
    while hi < len(rs3) - 1 and rs3[hi] > half:
        hi += 1
    if lo == peak_i or hi == peak_i:
        return np.nan

    def cross(i0, i1):
        x0, x1 = ps3[i0], ps3[i1]
        y0, y1 = rs3[i0], rs3[i1]
        if y1 == y0:
            return x0
        t = (half - y0) / (y1 - y0)
        return x0 + t * (x1 - x0)

    left = cross(lo, lo + 1)
    right = cross(hi - 1, hi)
    width_rad = right - left
    if width_rad <= 0 or width_rad > 2 * np.pi:
        return np.nan
    return np.degrees(width_rad)
