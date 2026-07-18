"""CHORUS actuation stack — the documented levers a BCI uses to direct a fly,
each implemented on the calibrated real-connectome ring attractor (cx_ring.RingCX)
and mapped to a real central-complex node. A minimal 2-D body integrates heading
+ speed so we can score point-to-point, trajectory, and swarm control.

Levers (see control_levers.csv for citations / in-vivo precedents):
  L1 goal-write (FC2)      : set desired heading, PFL3 nulls error   [proven in vivo]
  L2 direct steer (PFL3)   : impose turn rate directly              [proven in vivo]
  L3 compass offset (EPG)  : bias internal heading vs true          [partial]
  L4 forward speed (PFN)   : set translational speed                [partial]
  L5 stop (DNp09)          : gate locomotion off                    [proven in vivo]
  L6 reverse (MDN)         : negative forward speed                 [proven in vivo]
"""
import numpy as np
from cx_ring import RingCX


class BCIFly:
    """A single fly: real-connectome compass + 2-D body, driven by BCI levers."""

    def __init__(self, phases, x=0.0, y=0.0, heading=0.0, seed=0,
                 base_speed=1.0, turn_gain=0.25, ring_kw=None):
        rk = dict(kappa=5.6, w_exc=1.9, w_inh=0.28, w_shift=1.0, noise=0.02)
        if ring_kw:
            rk.update(ring_kw)
        self.cx = RingCX(phases, **rk)
        self.cx.rng = np.random.default_rng(seed)
        self.cx.reset(heading)
        self.x, self.y, self.true_head = x, y, heading
        self.base_speed, self.turn_gain = base_speed, turn_gain
        # lever state
        self.goal = None          # L1 desired heading (rad) or None
        self.direct_turn = 0.0     # L2 imposed turn rate
        self.compass_offset = 0.0  # L3 internal-vs-true offset
        self.speed_gain = 1.0      # L4 speed multiplier
        self.stopped = False       # L5
        self.reverse = False       # L6

    def set_goal(self, heading):      self.goal = heading          # L1
    def set_direct_turn(self, w):     self.direct_turn = w         # L2
    def set_compass_offset(self, o):  self.compass_offset = o      # L3
    def set_speed(self, g):           self.speed_gain = g          # L4
    def stop(self, on=True):          self.stopped = on            # L5
    def set_reverse(self, on=True):   self.reverse = on            # L6

    def step(self, dt=1.0, disturb=0.0):
        # --- decide angular velocity command from active levers ---
        cmd = 0.0
        ext = None
        if self.goal is not None:
            # L1: goal written into FC2 layer; PFL3 reads compass-vs-goal error
            turn, err = self.cx.pfl3_turn(self.goal)
            cmd += self.turn_gain * turn
            ext = self.cx.goal_ext(self.goal, amp=0.6)   # goal-layer drive on compass loop
        cmd += self.direct_turn                           # L2 direct steer
        # --- advance compass with self-motion (PEN integrates commanded turn) ---
        self.cx.step(ang_vel=cmd, ext=ext)
        # --- body update ---
        self.true_head += cmd + disturb
        spd = 0.0 if self.stopped else self.base_speed * self.speed_gain
        if self.reverse:
            spd = -abs(spd)
        self.x += spd * np.cos(self.true_head) * dt
        self.y += spd * np.sin(self.true_head) * dt
        return self.x, self.y, self.true_head

    def internal_heading(self):
        h, _ = self.cx.heading()
        return h + self.compass_offset


def point_to_point(fly, target_xy, steps=400, arrive_r=1.5):
    """Stream goal-heading commands to walk a fly to a target (NO stimulus gradient)."""
    xs, ys = [], []
    for t in range(steps):
        dx, dy = target_xy[0] - fly.x, target_xy[1] - fly.y
        if np.hypot(dx, dy) < arrive_r:
            fly.stop(True)
        fly.set_goal(np.arctan2(dy, dx))
        fly.step()
        xs.append(fly.x); ys.append(fly.y)
    return np.array(xs), np.array(ys)


def reach_tapered(fly, target_xy, steps=400, arrive_r=1.0, taper=6.0):
    """Point-to-point with proximity speed taper (closed-loop L4). Flies slow as
    they approach the goal -- biologically realistic, eliminates orbiting overshoot."""
    import numpy as np
    xs, ys = [], []
    tx, ty = target_xy
    for t in range(steps):
        dx, dy = tx - fly.x, ty - fly.y
        d = np.hypot(dx, dy)
        fly.set_goal(np.arctan2(dy, dx))
        fly.set_speed(np.clip(d / taper, 0.0, 1.0))
        if d < arrive_r:
            fly.stop(True)
        fly.step(); xs.append(fly.x); ys.append(fly.y)
    return np.array(xs), np.array(ys)


def track_path(fly_cls_phases, ref, lookahead=3, taper=4.0, elec=None, bw=None, noise=0.02):
    """Fine trajectory tracking: stream goal-heading (pursuit of nearest ref point +
    lookahead) and proximity-tapered speed to trace a reference path ref (Nx2).
    elec: quantize goal to that many EPG electrode sites. bw: first-order command
    low-pass (finite command bandwidth, 0-1). Returns (xs, ys)."""
    import numpy as np
    f = BCIFly(fly_cls_phases, ring_kw=dict(noise=noise)); f.x, f.y = ref[0]
    xs, ys = [], []
    esites = np.linspace(-np.pi, np.pi, elec, endpoint=False) if elec else None
    N = len(ref); prev = 0.0
    for t in range(N):
        d = np.hypot(ref[:,0]-f.x, ref[:,1]-f.y)
        i = min(np.argmin(d)+lookahead, N-1)
        gx, gy = ref[i]; goal = np.arctan2(gy-f.y, gx-f.x)
        if esites is not None:
            goal = esites[np.argmin(np.abs(((esites-goal+np.pi)%(2*np.pi))-np.pi))]
        if bw is not None:
            goal = prev + bw*(((goal-prev+np.pi)%(2*np.pi))-np.pi); prev = goal
        f.set_goal(goal); dist = np.hypot(gx-f.x, gy-f.y)
        f.set_speed(np.clip(dist/taper, 0.15, 1.0))
        f.step(); xs.append(f.x); ys.append(f.y)
    return np.array(xs), np.array(ys)


def make_swarm(phases, n, spread=15, seed=0, noise=0.02):
    """n independent real-connectome CX flies at random positions/headings.
    CRITICAL: pass heading into BCIFly so the internal compass is initialized
    consistent with body heading (allocentric calibration) -- otherwise a fixed
    compass-vs-body offset corrupts the goal->turn mapping and flies diverge."""
    import numpy as np
    rng = np.random.default_rng(seed); flies = []
    for i in range(n):
        x, y = rng.uniform(-spread, spread, 2); hd = rng.uniform(-np.pi, np.pi)
        flies.append(BCIFly(phases, x=x, y=y, heading=hd, seed=i, ring_kw=dict(noise=noise)))
    return flies

def swarm_drive(flies, target_fn, steps=320, arrive_r=1.0, taper=6.0):
    """Drive a swarm: each fly independently BCI-addressed toward target_fn(i,t)->(x,y).
    Returns history array (steps, n, 2). No inter-fly communication."""
    import numpy as np
    hist = []
    for t in range(steps):
        pos = []
        for i, f in enumerate(flies):
            tx, ty = target_fn(i, t); dx, dy = tx-f.x, ty-f.y; d = np.hypot(dx, dy)
            f.set_goal(np.arctan2(dy, dx)); f.set_speed(np.clip(d/taper, 0.0, 1.0))
            f.stop(d < arrive_r); f.step(); pos.append((f.x, f.y))
        hist.append(np.array(pos))
    return np.array(hist)
