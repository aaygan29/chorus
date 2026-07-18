"""
Biologically-structured central-complex (CX) ring-attractor model.
=================================================================
Rather than a random reservoir, this instantiates the *documented* CX wiring
motifs (Kim et al. 2017; Turner-Evans et al. 2020; Hulse et al. 2021 hemibrain
CX paper). It is a circuit-level 'realistic connectome': populations and
connection rules match the biology, weights are set to the canonical
ring-attractor regime.

Populations (per hemibrain nomenclature):
  EPG   : 'compass' neurons, one per of 16 wedges -> hold the HEADING bump
  PEN   : shift neurons, rotate the bump by angular velocity (2 copies L/R)
  Delta7: global inhibitory ring (normalisation / single-bump enforcement)
  PFL3  : output/steering neurons, compare heading bump vs GOAL bump -> turn

The GOAL bump is what a BCI writes. With no odor in the world, injecting a goal
at heading phi makes PFL3 drive turning until heading == phi (menotaxis).
"""
import numpy as np

N_WEDGE = 16  # 16 columns around the ring (EB wedges / PB glomeruli)

def _ring_gaussian(centers, phi, kappa=2.5):
    """von-Mises-like bump over the ring at angle phi."""
    ang = centers - phi
    return np.exp(kappa*(np.cos(ang)-1))

class CentralComplex:
    """One fly's CX. Vectorised over a population by stacking states externally."""
    def __init__(self, seed=0, w_rec=2.5, w_inh=0.8, w_shift=1.1,
                 w_pfl=1.4, tau=0.2, noise=0.005):
        self.rng = np.random.default_rng(seed)
        self.centers = np.linspace(0, 2*np.pi, N_WEDGE, endpoint=False)
        self.tau = tau; self.noise = noise
        # ---- EPG recurrent ring: local excitation via nearest wedges ----
        d = self.centers[:,None]-self.centers[None,:]
        self.W_epg = w_rec*np.exp(3.0*(np.cos(d)-1)).astype(np.float32)  # local excit.
        np.fill_diagonal(self.W_epg, self.W_epg.diagonal()+0.3)
        # ---- Delta7 global inhibition (uniform) enforces a single bump ----
        self.w_inh = w_inh
        # ---- PEN shift matrices: rotate bump +/- one wedge per side ----
        self.W_shiftL = w_shift*np.roll(np.eye(N_WEDGE, dtype=np.float32), 1, axis=0)
        self.W_shiftR = w_shift*np.roll(np.eye(N_WEDGE, dtype=np.float32),-1, axis=0)
        # ---- PFL3 steering readout: left/right turn from heading-vs-goal ----
        self.w_pfl = w_pfl
        self.reset()

    def reset(self, phi0=None):
        phi0 = self.rng.uniform(0,2*np.pi) if phi0 is None else phi0
        self.epg = _ring_gaussian(self.centers, phi0, 2.5).astype(np.float32)
        self.epg /= self.epg.sum()+1e-9

    def heading(self):
        """Decode bump phase = the fly's internal heading estimate."""
        v = np.sum(self.epg*np.exp(1j*self.centers))
        return np.angle(v)

    def step(self, ang_vel, goal_bump=None, epg_stim=None):
        """
        ang_vel : proprioceptive angular velocity (rad/step) -> drives PEN shift
        goal_bump : (16,) desired-heading bump the BCI writes (or None)
        epg_stim  : (16,) direct stimulation into EPG wedges (BCI 'compass hack')
        Returns steering command turn in [-1,1].
        """
        e = self.epg
        rec = self.W_epg @ e
        inh = self.w_inh * e.sum()
        # PEN angular-velocity shift: left/right gain set by sign of ang_vel
        gL = max( ang_vel, 0.0)*12.0; gR = max(-ang_vel, 0.0)*12.0
        shift = gL*(self.W_shiftL@e) + gR*(self.W_shiftR@e)
        drive = rec - inh + 1.5*shift
        if epg_stim is not None:
            drive = drive + epg_stim
        e_new = e + self.tau*(-e + np.maximum(drive,0))
        e_new += self.noise*self.rng.standard_normal(N_WEDGE)
        e_new = np.maximum(e_new, 0)
        s = e_new.sum()
        if s>1e-9: e_new/=s
        self.epg = e_new.astype(np.float32)
        # ---- PFL3 steering: turn to align heading bump with goal bump ----
        if goal_bump is not None:
            gh = np.angle(np.sum(goal_bump*np.exp(1j*self.centers)))
            err = np.angle(np.exp(1j*(gh - self.heading())))   # signed heading error
            turn = self.w_pfl*np.clip(err/np.pi, -1, 1)
            return float(turn)
        return 0.0

def goal_bump_at(phi, kappa=2.5):
    c = np.linspace(0,2*np.pi,N_WEDGE,endpoint=False)
    b = _ring_gaussian(c, phi, kappa); return (b/b.sum()).astype(np.float32)
