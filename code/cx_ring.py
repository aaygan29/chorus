"""CHORUS calibrated ring attractor — EPG compass on the REAL FlyWire EB ring.
Uses the 47 real EPG neurons and their spectral-embedding phases; the recurrent
coupling kernel is the effective EPG->EPG kernel MEASURED from real disynaptic
loops through PEG/Delta7/PEN (von-Mises local excitation, ~24 deg half-width,
weak inhibitory surround). PEN shift term rotates the bump by angular velocity;
PFL3 L/R output compares heading vs goal to command turns. Actuation operators
write to the goal bump (menotaxis) or inject direct steering — the levers a BCI
would use. This is the connectome-CALIBRATED model the control study runs on."""
import numpy as np


class RingCX:
    def __init__(self, phases, kappa=5.6, w_exc=1.9, w_inh=0.28, w_shift=1.5,
                 tau=0.2, dt=0.02, noise=0.02, pfl_gain=0.9):
        self.ph = np.asarray(phases, float)      # real EPG spectral phases
        self.N = len(self.ph)
        d = (self.ph[None, :] - self.ph[:, None] + np.pi) % (2 * np.pi) - np.pi
        # recurrent kernel: local excitation (real measured von Mises) - global inhibition
        Kexc = np.exp(kappa * (np.cos(d) - 1.0))
        self.Wrec = (w_exc * Kexc - w_inh).astype(np.float64)
        np.fill_diagonal(self.Wrec, self.Wrec.diagonal())
        self.w_shift = w_shift
        self.tau, self.dt, self.noise, self.pfl_gain = tau, dt, noise, pfl_gain
        # precompute phase-sorted order for the shift term's spatial derivative
        self.order = np.argsort(self.ph)
        ps = self.ph[self.order]
        self.ph_sorted_unwrap = np.unwrap(ps)
        self.reset()

    def reset(self, phase=0.0):
        self.r = 0.3 * np.exp(2.0 * (np.cos(self.ph - phase) - 1.0))
        self.rng = np.random.default_rng(0)

    @staticmethod
    def phi(x):
        return np.tanh(np.maximum(x, 0))

    def step(self, ang_vel=0.0, ext=None):
        # Recurrent attractor update
        rec = self.Wrec @ self.r
        inp = rec
        if ext is not None:
            inp = inp + ext
        self.r = self.r + self.dt / self.tau * (-self.r + self.phi(inp)) \
            + self.noise * self.rng.standard_normal(self.N)
        self.r = np.clip(self.r, 0, 5)
        # PEN dead-reckoning: advect the bump along the ring by ang_vel. Real PEN
        # neurons shift the EPG bump one wedge per unit rotation; here we translate
        # the rate profile in phase-sorted coordinates by (w_shift*ang_vel) radians
        # via linear interpolation, then map back. This is a phase-space advection,
        # the continuous analogue of the PEN one-wedge shift.
        if ang_vel != 0.0:
            o = self.order
            ps = self.ph_sorted_unwrap
            rs = self.r[o]
            shifted_pos = ps - self.w_shift * ang_vel
            new_rs = np.interp(shifted_pos, ps, rs, period=2 * np.pi)
            self.r[o] = new_rs
        return self.r

    def heading(self):
        z = np.sum(self.r * np.exp(1j * self.ph))
        return np.angle(z), np.abs(z) / (self.r.sum() + 1e-9)

    def goal_ext(self, goal_phase, amp=0.6):
        """Menotaxis goal write: extra drive at goal heading (what a BCI injects)."""
        return amp * np.exp(3.0 * (np.cos(self.ph - goal_phase) - 1.0))

    def pfl3_turn(self, goal_phase):
        """PFL3 steering readout: L/R activity difference -> turn command.
        Real PFL3 sums a ~90 deg-shifted copy of the bump on each side; the L-R
        difference is ~sin(goal - heading), the classic proportional steering law."""
        h, amp = self.heading()
        err = (goal_phase - h + np.pi) % (2 * np.pi) - np.pi
        return self.pfl_gain * np.sin(err) * min(amp * 4, 1.0), err

    # --- mechanistic FC2 goal-bump layer (a second ring the BCI writes into) ---
    def init_goal_layer(self):
        self.g = np.zeros(self.N)              # goal-bump rates
        self.Wg = self.Wrec.copy()             # same ring dynamics as the compass

    def step_goal(self, drive_phase=None, drive_amp=0.0):
        """Advance the goal-bump ring. A BCI writes drive_amp at drive_phase;
        the goal bump persists via ring recurrence and decays if drive is weak."""
        inp = self.Wg @ self.g
        if drive_phase is not None and drive_amp > 0:
            inp = inp + drive_amp * np.exp(3.0 * (np.cos(self.ph - drive_phase) - 1.0))
        self.g = self.g + self.dt / self.tau * (-self.g + self.phi(inp)) \
            + self.noise * self.rng.standard_normal(self.N)
        self.g = np.clip(self.g, 0, 5)
        return self.g

    def goal_heading(self):
        z = np.sum(self.g * np.exp(1j * self.ph))
        return np.angle(z), np.abs(z) / (self.g.sum() + 1e-9)

    def pfl3_turn_from_layer(self):
        """PFL3 compares compass heading to the GOAL-BUMP heading (not an oracle)."""
        h, ah = self.heading()
        gh, ag = self.goal_heading()
        err = (gh - h + np.pi) % (2 * np.pi) - np.pi
        # steering strength scales with BOTH bump amplitudes (weak goal bump -> weak steer)
        return self.pfl_gain * np.sin(err) * min(ah * 4, 1.0) * min(ag * 4, 1.0), err, ag
