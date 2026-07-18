"""CHORUS: ring-attractor dynamics on the REAL FlyWire v783 central complex.
Loads signed weighted connectivity (cx_real.npz) + node table (cx_nodes.csv),
recovers EB ring phase from real anatomy, simulates a rate model whose bump
is sustained by the real EPG-PEG local recurrence and sculpted by real
Delta7 offset inhibition. Actuation via population-targeted stimulation."""
import numpy as np, pandas as pd


def load(npz="cx_real.npz", csv="cx_nodes.csv", ann_phase=None):
    d = np.load(npz); W = d['W'].astype(np.float32); rid = d['root_ids']
    nodes = pd.read_csv(csv)
    nodes['t'] = nodes['cell_type'].astype(str).str.replace(r'\(.*?\)', '', regex=True)

    def fam(t):
        for f in ['EPGt', 'EPG', 'PEN_a', 'PEN_b', 'PEG', 'Delta7', 'PFL1', 'PFL2', 'PFL3',
                  'PFNa', 'PFNd', 'PFNm', 'PFNp', 'PFNv', 'PFR', 'PFGs', 'IbSpsP',
                  'ER1', 'ER2', 'ER3', 'ER4', 'ER5', 'ER6', 'ExR']:
            if str(t).startswith(f):
                return f
        return 'other'
    nodes['fam'] = nodes['t'].map(fam)
    nodes['phase'] = ann_phase
    return W, rid, nodes


class RealCX:
    """Rate model on real connectivity. State r in [0,1]^N."""

    def __init__(self, W, nodes, dt=0.02, tau=0.2, noise=0.003):
        self.W = W.astype(np.float32); self.N = W.shape[0]; self.nodes = nodes
        self.dt = dt; self.tau = tau; self.noise = noise
        self.ph = nodes['phase'].values.astype(np.float32)
        self.fam = nodes['fam'].values
        self.FI = {f: np.where(nodes['fam'].values == f)[0] for f in pd.unique(nodes['fam'])}
        self.side = nodes['side'].values
        self.gpop = np.ones(self.N, np.float32)
        for f, gv in {'EPG': 1.0, 'PEG': 1.3, 'PEN_a': 1.1, 'PEN_b': 1.1, 'Delta7': 1.15,
                      'PFL3': 1.0, 'PFL2': 1.0, 'PFL1': 1.0}.items():
            self.gpop[self.FI.get(f, [])] = gv
        self.norm = np.sqrt(np.abs(W).sum(0) + 1.0).astype(np.float32)
        self.G = 13.0; self.bias = -0.55
        self.reset()

    def reset(self):
        self.r = np.zeros(self.N, np.float32); self.rng = np.random.default_rng(0)

    @staticmethod
    def phi(x):
        return 1.0 / (1.0 + np.exp(-x))

    def step(self, ext=None, pen_drive=0.0):
        inp = self.G * self.gpop * (self.W.T @ self.r) / self.norm + self.bias
        if pen_drive != 0.0:
            for f in ['PEN_a', 'PEN_b']:
                idx = self.FI.get(f, [])
                s = np.where(self.side[idx] == 'right', 1.0, -1.0)
                inp[idx] += pen_drive * s
        if ext is not None:
            inp = inp + ext
        self.r = self.r + self.dt / self.tau * (-self.r + self.phi(inp)) + \
            self.noise * self.rng.standard_normal(self.N).astype(np.float32)
        self.r = np.clip(self.r, 0, 1)
        return self.r

    def seed(self, phase, steps=300, gain=1.6):
        m = self.fam == 'EPG'
        for _ in range(steps):
            ext = np.zeros(self.N, np.float32)
            ext[m] = gain * np.cos(self.ph[m] - phase)
            self.step(ext=ext)

    def bump_heading(self, pop='EPG'):
        idx = self.FI[pop]; r = self.r[idx]; ph = self.ph[idx]
        z = np.sum(r * np.exp(1j * ph))
        return np.angle(z), np.abs(z) / (r.sum() + 1e-9)
