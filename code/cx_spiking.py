"""CHORUS spiking ring attractor — the SAME EPG compass, now built from
leaky integrate-and-fire neurons instead of a rate model. This is the
sim-to-real stress test: the control study's numbers were measured on a
CALIBRATED RATE model; here we ask whether they survive when the ring is
made of spiking cells with an explicit Delta7 inhibitory pool and finite
synaptic time constants.

Architecture (all spiking):
  EPG : N excitatory LIF neurons on the ring at phases `phases`.
        Recurrent E->E weights = von-Mises local excitation (same kappa as
        the rate kernel). This is the continuous-attractor backbone.
  D7  : a small inhibitory LIF pool (Delta7). Receives uniform excitation
        from all EPG, projects uniform inhibition back -> global normalization
        that sharpens the bump and enforces a single active hill.
  PEN : dead-reckoning shift. Angular-velocity input injects a drive
        proportional to the *circular spatial derivative* of the EPG
        synaptic activation, advecting the bump around the ring (the
        continuous analogue of the PEN one-wedge shift). The derivative is
        taken on the spike-derived synaptic trace, so the state stays spiking.
  Goal/PFL3 : goal-write injects an extra excitatory current bump at the
        commanded heading; PFL3 steering reads sin(goal - heading) from the
        population-vector heading of recent spikes.

The class mirrors cx_ring.RingCX's public API (reset, step, heading,
goal_ext, pfl3_turn, .rng) so it drops straight into cx_actuation.BCIFly.
Units: mV / ms. One control `step()` = `ms_per_step` ms of biology,
integrated at `dt_ms` resolution; heading is read from spike counts in a
trailing window.
"""
import numpy as np


class SpikingRing:
    def __init__(self, phases, kappa=5.6,
                 J_EE=0.42, J_IE=0.9, J_EI=0.62, J_pen=5.0,
                 tau_m=20.0, tau_syn=5.0, tau_i=10.0,
                 V_rest=-70.0, V_th=-50.0, V_reset=-58.0, t_ref=2.0,
                 I_bias=16.5, I_bias_i=6.0, ms_per_step=25.0, dt_ms=0.5,
                 noise=1.6, pfl_gain=0.9, w_shift=1.0, seed=0):
        self.ph = np.asarray(phases, float)
        self.N = len(self.ph)
        self.NI = max(8, self.N // 6)          # Delta7 inhibitory pool
        # recurrent excitation: von-Mises local kernel, zero self, row-normalized
        d = (self.ph[None, :] - self.ph[:, None] + np.pi) % (2*np.pi) - np.pi
        K = np.exp(kappa * (np.cos(d) - 1.0))
        np.fill_diagonal(K, 0.0)
        K /= K.sum(1, keepdims=True) + 1e-12
        self.W_EE = (J_EE * K * self.N)        # E->E (scaled so row-sum ~ J_EE*N)
        self.J_IE, self.J_EI, self.J_pen = J_IE, J_EI, J_pen
        # LIF params
        self.tau_m, self.tau_syn, self.tau_i = tau_m, tau_syn, tau_i
        self.V_rest, self.V_th, self.V_reset, self.t_ref = V_rest, V_th, V_reset, t_ref
        self.I_bias, self.I_bias_i = I_bias, I_bias_i
        self.ms_per_step, self.dt_ms = ms_per_step, dt_ms
        self.noise, self.pfl_gain, self.w_shift = noise, pfl_gain, w_shift
        self.order = np.argsort(self.ph)
        self.rng = np.random.default_rng(seed)
        self.reset()

    def reset(self, phase=0.0):
        self.V = self.V_rest + (self.V_th - self.V_rest) * self.rng.random(self.N)
        self.VI = self.V_rest + (self.V_th - self.V_rest) * self.rng.random(self.NI)
        self.ref = np.zeros(self.N)            # refractory clocks (ms)
        self.refI = np.zeros(self.NI)
        # synaptic activations (spike-filtered)
        self.sE = 0.9 * np.exp(3.0 * (np.cos(self.ph - phase) - 1.0))  # seed bump
        self.sI = np.zeros(self.NI)
        self.rate = self.sE.copy()             # trailing firing-rate estimate (Hz-ish)

    # --- rate-model-compatible API ---------------------------------------
    @staticmethod
    def phi(x):
        return x

    def _circ_deriv(self, v):
        """circular spatial derivative of profile v along the phase-sorted ring."""
        o = self.order
        vs = v[o]
        dv = (np.roll(vs, -1) - np.roll(vs, 1)) * 0.5
        out = np.empty_like(v)
        out[o] = dv
        return out

    def step(self, ang_vel=0.0, ext=None):
        """Advance ms_per_step ms of spiking dynamics. ang_vel advects the bump
        (PEN dead reckoning); ext is an extra excitatory current bump (goal write).
        Returns the trailing firing-rate estimate (same role as RingCX.r)."""
        nsub = int(self.ms_per_step / self.dt_ms)
        dt = self.dt_ms
        spk_count = np.zeros(self.N)
        aE = dt / self.tau_syn
        aI = dt / self.tau_i
        # PEN shift current: drive along the circular derivative of the bump
        pen = np.zeros(self.N)
        if ang_vel != 0.0:
            pen = -self.J_pen * self.w_shift * ang_vel * self._circ_deriv(self.sE)
        extra = np.zeros(self.N)
        if ext is not None:
            extra = extra + np.asarray(ext, float)
        for _ in range(nsub):
            # synaptic input currents
            I_E = (self.W_EE @ self.sE) - self.J_EI * self.sI.sum() \
                  + self.I_bias + pen + extra \
                  + self.noise * self.rng.standard_normal(self.N)
            I_I = self.J_IE * self.sE.sum() + self.I_bias_i \
                  + 0.5 * self.noise * self.rng.standard_normal(self.NI)
            # membrane update (LIF), respecting refractory
            act = self.ref <= 0
            self.V[act] += dt / self.tau_m * (-(self.V[act] - self.V_rest) + I_E[act])
            self.ref[~act] -= dt
            actI = self.refI <= 0
            self.VI[actI] += dt / self.tau_m * (-(self.VI[actI] - self.V_rest) + I_I[actI])
            self.refI[~actI] -= dt
            # spikes
            fired = np.where(self.V >= self.V_th)[0]
            firedI = np.where(self.VI >= self.V_th)[0]
            if fired.size:
                self.V[fired] = self.V_reset
                self.ref[fired] = self.t_ref
                spk_count[fired] += 1
            if firedI.size:
                self.VI[firedI] = self.V_reset
                self.refI[firedI] = self.t_ref
            # synaptic activation decay + spike increments
            self.sE += -aE * self.sE
            self.sE[fired] += 1.0
            self.sI += -aI * self.sI
            self.sI[firedI] += 1.0
        # trailing firing-rate estimate (spikes/window -> smooth), used as .r/readout
        inst = spk_count / (self.ms_per_step / 1000.0)   # Hz
        self.rate = 0.6 * self.rate + 0.4 * inst
        self.r = self.rate
        return self.rate

    def heading(self):
        w = self.rate
        z = np.sum(w * np.exp(1j * self.ph))
        return np.angle(z), np.abs(z) / (w.sum() + 1e-9)

    def goal_ext(self, goal_phase, amp=0.6):
        """Goal write: extra excitatory current bump at goal heading. Scaled to
        the spiking model's current units (mV/ms)."""
        return 26.0 * amp * np.exp(3.0 * (np.cos(self.ph - goal_phase) - 1.0))

    def pfl3_turn(self, goal_phase):
        h, amp = self.heading()
        err = (goal_phase - h + np.pi) % (2*np.pi) - np.pi
        return self.pfl_gain * np.sin(err) * min(amp * 4, 1.0), err
