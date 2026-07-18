"""
CHORUS in-silico testbed
========================
A population of embodied agents, each driven by an internal *connectome-derived*
recurrent rate network. "Driving" = writing stimulation into internal neurons
(in-silico optogenetics); sensory dynamics stay in the loop. Multiple swarm
control paradigms (drone/collective-behaviour literature) are implemented as
different stimulation policies acting on the SAME brains.

Everything is vectorised over the population with numpy (n_agents x n_neurons).
"""
import numpy as np

# ---------------------------------------------------------------------------
# 1. Connectome-derived brain
# ---------------------------------------------------------------------------
def make_connectome(n_internal=120, p_conn=0.12, spectral_radius=1.25,
                    frac_inh=0.2, seed=0):
    """Sparse, signed recurrent weight matrix obeying Dale's law.
    Stands in for a connectome-instantiated dynamical network: fixed 'species'
    wiring, scaled to the edge-of-chaos regime that gives rich reservoir dynamics.
    Returns W (n_internal x n_internal) and the inhibitory mask.
    """
    rng = np.random.default_rng(seed)
    mask = rng.random((n_internal, n_internal)) < p_conn
    np.fill_diagonal(mask, False)
    W = np.abs(rng.normal(0, 1, (n_internal, n_internal))) * mask
    # Dale's law: a neuron is either all-excitatory or all-inhibitory (by column)
    is_inh = rng.random(n_internal) < frac_inh
    W[:, is_inh] *= -1.0
    # scale to target spectral radius (reservoir / echo-state regime)
    eig = np.max(np.abs(np.linalg.eigvals(W)))
    if eig > 0:
        W *= spectral_radius / eig
    return W.astype(np.float32), is_inh


class BrainPopulation:
    """A population of agents sharing one connectome (with small per-agent
    'posterior-draw' weight jitter). Rate model:
        x <- (1-a) x + a * tanh( x @ W.T  +  Win @ sensory  +  stim )
    Motor output = linear readout of internal state -> (forward_drive, turn_drive).
    """
    def __init__(self, n_agents=24, n_internal=120, n_sensory=4, n_motor=2,
                 alpha=0.35, jitter=0.03, n_steer=20, seed=0):
        self.rng = np.random.default_rng(seed)
        self.n_agents, self.n_internal = n_agents, n_internal
        self.n_sensory, self.n_motor = n_sensory, n_motor
        self.alpha = alpha
        W, self.is_inh = make_connectome(n_internal, seed=seed)
        # per-agent posterior-draw jitter on the shared connectome
        self.W = np.stack([W * (1 + jitter * self.rng.standard_normal(W.shape))
                           for _ in range(n_agents)]).astype(np.float32)  # (A,N,N)
        self.Win = self.rng.standard_normal((n_internal, n_sensory)).astype(np.float32) * 0.8
        # ---- steering pools live in the brain (shared by controllers) ----
        perm = self.rng.permutation(n_internal)
        self.left_pool  = perm[:n_steer]
        self.right_pool = perm[n_steer:2*n_steer]
        self.fwd_pool   = perm[2*n_steer:3*n_steer]
        # ---- calibrated/learned motor decoder aligned to the pools ----
        # forward = mean(fwd_pool) + explore_bias ; turn = mean(left_pool) - mean(right_pool)
        Wout = np.zeros((n_motor, n_internal), np.float32)
        Wout[0, self.fwd_pool]   =  1.0 / n_steer
        Wout[1, self.left_pool]  =  1.0 / n_steer
        Wout[1, self.right_pool] = -1.0 / n_steer
        self.Wout = Wout
        self.explore_bias = 0.45   # baseline forward drive so the swarm explores
        self.X = np.zeros((n_agents, n_internal), np.float32)

    def reset(self):
        self.X = 0.05 * self.rng.standard_normal(self.X.shape).astype(np.float32)

    def step(self, sensory, stim=None):
        """sensory: (A, n_sensory); stim: (A, n_internal) or None. Returns motor (A, n_motor)."""
        rec = np.einsum('anm,am->an', self.W, self.X)          # recurrent drive
        inp = sensory @ self.Win.T                              # sensory drive
        drive = rec + inp
        if stim is not None:
            drive = drive + stim
        self.X = (1 - self.alpha) * self.X + self.alpha * np.tanh(drive)
        motor = self.X @ self.Wout.T                            # (A, n_motor)
        motor[:, 0] = motor[:, 0] + self.explore_bias
        return motor


# ---------------------------------------------------------------------------
# 2. Embodiment: 2D arena with an odour source (collective chemotaxis task)
# ---------------------------------------------------------------------------
class Arena:
    def __init__(self, n_agents=24, size=20.0, source=None, sigma=6.0, seed=0):
        self.rng = np.random.default_rng(seed + 999)
        self.size = size
        self.n_agents = n_agents
        self.source = np.array(source if source is not None else [size*0.8, size*0.8])
        self.sigma = sigma
        self.reset()

    def reset(self):
        # start clustered in the opposite corner from the source
        self.pos = self.rng.uniform(1.0, 5.0, (self.n_agents, 2)).astype(np.float32)
        self.theta = self.rng.uniform(0, 2*np.pi, self.n_agents).astype(np.float32)
        self.pheromone = np.zeros((40, 40), np.float32)  # stigmergy grid

    def odor(self, pos):
        d2 = np.sum((pos - self.source)**2, axis=1)
        return np.exp(-d2 / (2 * self.sigma**2))

    def bilateral_odor(self, pos, theta, d=0.6):
        """Left/right antenna concentrations -> gives a gradient cue."""
        left  = pos + d * np.stack([-np.sin(theta),  np.cos(theta)], axis=1)
        right = pos + d * np.stack([ np.sin(theta), -np.cos(theta)], axis=1)
        return self.odor(left), self.odor(right)

    def neighbor_density(self, radius=3.0):
        """Local crowding each agent senses (for swarm rules)."""
        D = np.linalg.norm(self.pos[:, None] - self.pos[None], axis=2)
        return (np.sum(D < radius, axis=1) - 1).astype(np.float32)

    def move(self, forward, turn, dt=0.15, vmax=1.6, wmax=1.2):
        f = np.clip(forward, -0.3, 1.0) * vmax
        w = np.clip(turn, -1, 1) * wmax
        self.theta = (self.theta + w * dt) % (2*np.pi)
        step = f[:, None] * np.stack([np.cos(self.theta), np.sin(self.theta)], axis=1) * dt
        self.pos = np.clip(self.pos + step, 0, self.size)

    def deposit_pheromone(self, amount=1.0, decay=0.96):
        self.pheromone *= decay
        gx = np.clip((self.pos[:,0]/self.size*39).astype(int), 0, 39)
        gy = np.clip((self.pos[:,1]/self.size*39).astype(int), 0, 39)
        np.add.at(self.pheromone, (gx, gy), amount)

    def sense_pheromone_gradient(self, theta, d=0.8):
        def val(p):
            gx = np.clip((p[:,0]/self.size*39).astype(int), 0, 39)
            gy = np.clip((p[:,1]/self.size*39).astype(int), 0, 39)
            return self.pheromone[gx, gy]
        left  = self.pos + d*np.stack([-np.sin(theta),  np.cos(theta)],axis=1)
        right = self.pos + d*np.stack([ np.sin(theta), -np.cos(theta)],axis=1)
        return val(np.clip(left,0,self.size)), val(np.clip(right,0,self.size))


# ---------------------------------------------------------------------------
# 3. Metrics
# ---------------------------------------------------------------------------
def rollout_metrics(pos_hist, arena, reach_radius=2.5):
    pos_hist = np.asarray(pos_hist)              # (T, A, 2)
    final = pos_hist[-1]
    dist_final = np.linalg.norm(final - arena.source, axis=1)
    dist_hist = np.linalg.norm(pos_hist - arena.source, axis=2)  # (T,A)
    reached = np.min(dist_hist, axis=0) < reach_radius
    # time to first reach (or T if never)
    T = pos_hist.shape[0]
    ttf = np.full(arena.n_agents, T, float)
    for a in range(arena.n_agents):
        hit = np.where(dist_hist[:, a] < reach_radius)[0]
        if len(hit): ttf[a] = hit[0]
    # aggregation: mean pairwise distance at the end (lower = tighter swarm)
    D = np.linalg.norm(final[:,None]-final[None], axis=2)
    aggregation = D[np.triu_indices(arena.n_agents,1)].mean()
    return dict(frac_reached=float(reached.mean()),
                mean_final_dist=float(dist_final.mean()),
                median_time_to_source=float(np.median(ttf)),
                aggregation=float(aggregation))
