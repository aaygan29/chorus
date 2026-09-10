"""CHORUS closed-loop task environment. The connectome-grounded fly (real CX
ring attractor, calibrated per CHORUS_fine_control.md) is the agent's
body; the only write channel is the BCI goal-heading + speed lever (L1+L4).
Connectome-agnostic: pass any (npz, csv) pair matching the FlyWire schema
(W signed float32, root_ids int64, nodes root_id/cell_type/side/nt) and it
runs unchanged. The calibrated ring kernel (kappa/w_exc/w_inh) is NOT read
from W -- per the monograph's central finding, raw connectome weights pin
the bump and only the measured/calibrated kernel gives a working attractor.
Applying the FlyWire-calibrated gains to a second species' connectome without
re-measuring its own kernel is an explicit, flagged modeling assumption.
"""
import numpy as np
import pandas as pd
from cx_ring import RingCX

N_WEDGE = 16   # canonical uniform EB-wedge tiling used throughout the monograph


def load_connectome(npz_path, csv_path):
    """Schema-only loader: returns node table + EPG family index. W/root_ids
    are returned for provenance but are NOT used to build the ring (see module
    docstring) -- only the EPG population size varies the model across species."""
    d = np.load(npz_path)
    W = d['W'].astype(np.float32)
    root_ids = d['root_ids']
    nodes = pd.read_csv(csv_path)
    t = nodes['cell_type'].astype(str).str.replace(r'\(.*?\)', '', regex=True)
    is_epg = t.str.startswith('EPG') & ~t.str.startswith('EPGt')
    n_epg = int(is_epg.sum())
    if n_epg == 0:
        raise ValueError(f"no EPG neurons found in {csv_path}; check cell_type schema")
    return dict(W=W, root_ids=root_ids, nodes=nodes, n_epg=n_epg)


def wedge_phases(n=N_WEDGE):
    return np.linspace(-np.pi, np.pi, n, endpoint=False)


def wrap(a):
    return (a + np.pi) % (2 * np.pi) - np.pi


class Electrode:
    """Quantized EPG-ring electrode array: n_electrodes tiling the ring, goal
    heading snapped to nearest site (heading error ~= 90deg/n, monograph S5).
    Optional per-step goal noise and site dropout (monograph S8)."""

    def __init__(self, n, noise_std=0.0, dropout_p=0.0, rng=None):
        self.n = n
        self.sites = np.linspace(-np.pi, np.pi, n, endpoint=False) if n else None
        self.noise_std = noise_std
        self.dropout_p = dropout_p
        self.rng = rng or np.random.default_rng(0)
        self._live = np.ones(n, bool) if n else None

    def write(self, goal):
        g = goal
        if self.noise_std > 0:
            g = wrap(g + self.rng.normal(0, self.noise_std))
        if self.sites is None:
            return g, True
        if self.dropout_p > 0:
            self._live = self.rng.random(self.n) >= self.dropout_p
            if not self._live.any():
                return g, False
            sites = self.sites[self._live]
        else:
            sites = self.sites
        i = np.argmin(np.abs(wrap(sites - g)))
        return sites[i], True


class ChorusEnv:
    """Gym-like closed-loop env. action = (goal_heading_rad, speed[0,1]).
    obs = (decoded_heading, decoded_amp, target_bearing, target_range).
    Goal-write follows the monograph's validated L1 mechanism (cx_actuation.BCIFly,
    cx_ring.RingCX.goal_ext/pfl3_turn): a goal-phase current is injected on the
    compass ring's ext channel and PFL3 reads sin(goal-heading) off the same
    bump. This is what the published rate-model numbers (0.41deg pointing,
    0.17-unit figure-8) were measured with, so it is what the regression gate
    checks against. RingCX also exposes a separate mechanistic FC2 goal-bump
    layer (init_goal_layer/step_goal/pfl3_turn_from_layer) that never writes
    into the compass at all -- more defensible against the spiking model's
    "goal current teleports the compass bump" failure (S13), but it was not
    what the headline numbers were measured with and gives a visibly worse
    ~5deg steady pointing error in this codebase; kept available via
    goal_layer=True for anyone who wants the more conservative model."""

    def __init__(self, npz_path, csv_path, n_electrodes=8, goal_noise_std=0.0,
                 electrode_dropout=0.0, calibrate=True, anchor_gain=0.0,
                 goal_amp=0.6, goal_layer=False, turn_gain=0.25, base_speed=1.0,
                 max_steps=500, ring_kw=None, seed=None):
        cx = load_connectome(npz_path, csv_path)
        self.n_epg = cx['n_epg']
        self.phases = wedge_phases(N_WEDGE)
        rk = dict(kappa=5.6, w_exc=1.9, w_inh=0.28, w_shift=1.0, noise=0.02)
        if ring_kw:
            rk.update(ring_kw)
        self.ring_kw = rk
        self.n_electrodes = n_electrodes
        self.goal_noise_std = goal_noise_std
        self.electrode_dropout = electrode_dropout
        self.calibrate = calibrate
        self.anchor_gain = anchor_gain
        self.goal_amp = goal_amp
        self.goal_layer = goal_layer
        self.turn_gain = turn_gain
        self.base_speed = base_speed
        self.max_steps = max_steps
        self.task = None
        self.seed(seed)

    def seed(self, seed=None):
        self._seed = seed if seed is not None else 0
        self.rng = np.random.default_rng(self._seed)

    def set_task(self, task):
        self.task = task
        task.env = self
        return self

    def reset(self, seed=None):
        if seed is not None:
            self.seed(seed)
        self.cx = RingCX(self.phases, **self.ring_kw)
        self.cx.rng = np.random.default_rng(self._seed)
        if self.goal_layer:
            self.cx.init_goal_layer()
        self.elec = Electrode(self.n_electrodes, self.goal_noise_std,
                               self.electrode_dropout, self.rng)
        self.t = 0
        self.true_head = self.rng.uniform(-np.pi, np.pi)
        self.x, self.y = 0.0, 0.0
        if self.calibrate:
            # compass calibration epoch: a visual-landmark alignment sets the
            # internal compass to allocentric heading before control begins
            # (monograph S7 design rule, discovered as an init bug).
            self.cx.reset(self.true_head)
            for _ in range(50):
                self.cx.step(ext=self.anchor_ext())
        else:
            # deliberately uncalibrated: compass initialized to an arbitrary
            # offset from body heading -> reproduces the divergence failure.
            self.cx.reset(self.rng.uniform(-np.pi, np.pi))
        traj = self.task.reset_task(self.rng) if self.task else {}
        self.traj = {'x': [self.x], 'y': [self.y], 'head': [self.true_head]}
        return self._obs(), {**self._info(), **traj}

    def anchor_ext(self):
        """ER-ring visual-anchor drive: weak continuous current at true
        heading, keeping the compass locked to allocentric reference so
        open-loop dead-reckoning does not drift (S7/S13)."""
        if self.anchor_gain <= 0:
            return None
        return self.anchor_gain * 0.05 * np.exp(3.0 * (np.cos(self.cx.ph - self.true_head) - 1.0))

    def decoded_heading(self):
        h, amp = self.cx.heading()
        return h, amp

    def _obs(self):
        h, amp = self.decoded_heading()
        bearing, rng_ = (0.0, 0.0)
        if self.task is not None:
            bearing, rng_ = self.task.target_bearing_range()
        return np.array([h, amp, bearing, rng_], dtype=np.float32)

    def _info(self):
        h, amp = self.decoded_heading()
        return dict(decoded_heading=h, true_heading=self.true_head,
                    compass_offset=wrap(h - self.true_head),
                    angular_error=abs(wrap(h - self.true_head)))

    def step(self, action):
        goal, speed = float(action[0]), float(np.clip(action[1], 0.0, 1.0))
        site, live = self.elec.write(goal)
        if self.goal_layer:
            self.cx.step_goal(drive_phase=site if live else None,
                               drive_amp=1.0 if live else 0.0)
            cmd, err, gamp = self.cx.pfl3_turn_from_layer()
            ext = self.anchor_ext()
        else:
            turn, err = self.cx.pfl3_turn(site)
            cmd = turn
            ext = self.cx.goal_ext(site, amp=self.goal_amp) if live else None
            a = self.anchor_ext()
            if a is not None:
                ext = a if ext is None else ext + a
        cmd = self.turn_gain * cmd
        self.cx.step(ang_vel=cmd, ext=ext)
        self.true_head = wrap(self.true_head + cmd)
        spd = self.base_speed * speed
        self.x += spd * np.cos(self.true_head)
        self.y += spd * np.sin(self.true_head)
        self.t += 1
        self.traj['x'].append(self.x); self.traj['y'].append(self.y); self.traj['head'].append(self.true_head)
        reward, terminated, task_info = (0.0, False, {})
        if self.task is not None:
            reward, terminated, task_info = self.task.step_task()
        truncated = self.t >= self.max_steps
        info = {**self._info(), **task_info, 'goal_error': err, 'electrode_live': live}
        return self._obs(), reward, terminated, truncated, info


# ---------------- tasks ----------------

class BaseTask:
    env = None

    def reset_task(self, rng):
        return {}

    def target_bearing_range(self):
        return 0.0, 0.0

    def step_task(self):
        return 0.0, False, {}


class PursuitTask(BaseTask):
    """Chase a moving target. Metric: cross-track RMS to the target's path,
    capture time (steps to first arrival within capture_r)."""

    def __init__(self, target_fn, capture_r=1.0, max_steps=500):
        self.target_fn = target_fn
        self.capture_r = capture_r
        self.max_steps = max_steps

    def reset_task(self, rng):
        self.errs = []
        self.captured_at = None
        return {}

    def _target(self):
        return self.target_fn(self.env.t)

    def target_bearing_range(self):
        tx, ty = self._target()
        dx, dy = tx - self.env.x, ty - self.env.y
        return np.arctan2(dy, dx), np.hypot(dx, dy)

    def step_task(self):
        tx, ty = self._target()
        d = np.hypot(tx - self.env.x, ty - self.env.y)
        self.errs.append(d)
        if self.captured_at is None and d < self.capture_r:
            self.captured_at = self.env.t
        return -d, False, dict(target=(tx, ty), dist=d)

    def metrics(self):
        rms = float(np.sqrt(np.mean(np.square(self.errs)))) if self.errs else np.nan
        return dict(cross_track_rms=rms, capture_time=self.captured_at)


class TrackingTask(BaseTask):
    """Trace a parametric reference path (Nx2 array or callable(t)->xy).
    Metric: cross-track RMS distance to the nearest path point."""

    def __init__(self, path, lookahead=3):
        self.path = np.asarray(path) if not callable(path) else path
        self.lookahead = lookahead

    def reset_task(self, rng):
        self.ref = self.path if isinstance(self.path, np.ndarray) else \
            np.array([self.path(t) for t in range(self.env.max_steps)])
        self.errs = []
        return {}

    def _lookahead_point(self):
        d = np.hypot(self.ref[:, 0] - self.env.x, self.ref[:, 1] - self.env.y)
        i = min(int(np.argmin(d)) + self.lookahead, len(self.ref) - 1)
        return self.ref[i], d.min()

    def target_bearing_range(self):
        pt, _ = self._lookahead_point()
        dx, dy = pt[0] - self.env.x, pt[1] - self.env.y
        return np.arctan2(dy, dx), np.hypot(dx, dy)

    def step_task(self):
        _, cte = self._lookahead_point()
        self.errs.append(cte)
        return -cte, False, dict(cross_track=cte)

    def metrics(self):
        return dict(cross_track_rms=float(np.sqrt(np.mean(np.square(self.errs)))))


class ObstacleTask(BaseTask):
    """Reach a target while avoiding circular obstacles requiring re-planning.
    Metric: arrival rate (1/0 this episode), path efficiency = straight-line
    dist / actual path length."""

    def __init__(self, target_xy, obstacles, arrive_r=1.5, margin=1.0):
        self.target_xy = np.asarray(target_xy, float)
        self.obstacles = obstacles  # list of (cx, cy, r)
        self.arrive_r = arrive_r
        self.margin = margin

    def reset_task(self, rng):
        self.arrived = False
        self.path_len = 0.0
        self.prev = (self.env.x, self.env.y)
        self.start_dist = np.hypot(*(self.target_xy - np.array([self.env.x, self.env.y])))
        return {}

    def _avoid_bearing(self):
        """Artificial potential field: unit attraction to target + repulsion
        from obstacles within margin, summed as vectors then turned back into
        a bearing. Smoother than a bearing-rotation rule -- avoids the
        overshoot oscillation a discontinuous rotate-away rule causes when
        combined with the finite-bandwidth CX steering loop."""
        tx, ty = self.target_xy
        dx, dy = tx - self.env.x, ty - self.env.y
        d = np.hypot(dx, dy) + 1e-9
        vx, vy = dx / d, dy / d
        for (ox, oy, r) in self.obstacles:
            odx, ody = self.env.x - ox, self.env.y - oy
            od = np.hypot(odx, ody)
            if od < r + self.margin and od > 1e-6:
                push = (r + self.margin - od) / self.margin
                vx += push * odx / od
                vy += push * ody / od
        return np.arctan2(vy, vx)

    def target_bearing_range(self):
        goal = self._avoid_bearing()
        dx, dy = self.target_xy - np.array([self.env.x, self.env.y])
        return goal, np.hypot(dx, dy)

    def step_task(self):
        d = np.hypot(*(self.target_xy - np.array([self.env.x, self.env.y])))
        self.path_len += np.hypot(self.env.x - self.prev[0], self.env.y - self.prev[1])
        self.prev = (self.env.x, self.env.y)
        if not self.arrived and d < self.arrive_r:
            self.arrived = True
        return -d, self.arrived, dict(dist=d, arrived=self.arrived)

    def metrics(self):
        eff = self.start_dist / self.path_len if self.path_len > 0 else 0.0
        return dict(arrival_rate=float(self.arrived), path_efficiency=float(min(eff, 1.0)))


# ---------------- optional gymnasium wrapper ----------------
try:
    import gymnasium as gym

    class GymChorusEnv(gym.Env):
        def __init__(self, *a, **kw):
            self.core = ChorusEnv(*a, **kw)
            self.observation_space = gym.spaces.Box(-np.inf, np.inf, (4,), np.float32)
            self.action_space = gym.spaces.Box(np.array([-np.pi, 0.0]), np.array([np.pi, 1.0]))

        def set_task(self, task):
            self.core.set_task(task); return self

        def reset(self, seed=None, options=None):
            return self.core.reset(seed=seed)

        def step(self, action):
            return self.core.step(action)
except ImportError:
    pass
