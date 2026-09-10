"""
Five control paradigms borrowed from drone-swarm / collective-behaviour research,
each realised as an in-silico STIMULATION policy that writes into the internal
neurons of connectome-derived brains. All share the same brains & bodies.

Design: sensory input always flows into the brain. A controller additionally
computes a stimulation vector `stim` (A x n_internal) injected into a fixed set
of 'steering' neurons, biasing the motor readout. This models optogenetic drive.
"""
import numpy as np

class BaseController:
    name = "base"
    def __init__(self, brain, arena, gain=2.5, seed=0):
        self.brain, self.arena, self.gain = brain, arena, gain
        # steering pools are defined inside the brain (shared, calibrated decoder)
        self.left_pool  = brain.left_pool
        self.right_pool = brain.right_pool
        self.fwd_pool   = brain.fwd_pool
    def sensory(self):
        """Common afferent signal: bilateral odour + local density + bias."""
        oL, oR = self.arena.bilateral_odor(self.arena.pos, self.arena.theta)
        dens = self.arena.neighbor_density() / 10.0
        return np.stack([oL, oR, dens, np.ones_like(oL)*0.1], axis=1).astype(np.float32)
    def stim(self):
        return None   # autonomous: no drive
    def _steer(self, turn_cmd, fwd_cmd):
        """Turn commands (A,) in [-1,1] -> stimulation vector via steering pools."""
        A, N = self.brain.n_agents, self.brain.n_internal
        s = np.zeros((A, N), np.float32)
        left  = np.clip( turn_cmd, 0, 1)
        right = np.clip(-turn_cmd, 0, 1)
        s[:, self.left_pool]  += self.gain * left[:, None]
        s[:, self.right_pool] += self.gain * right[:, None]
        s[:, self.fwd_pool]   += self.gain * np.clip(fwd_cmd,0,1)[:, None]
        return s
    def post_move(self):
        pass


class Autonomous(BaseController):
    """No AI drive. Baseline: connectome dynamics + sensory loop only."""
    name = "Autonomous (no drive)"


class Centralized(BaseController):
    """Drone-fleet ground-station model: one policy reads every agent's true
    gradient and injects corrective stimulation. Full observability."""
    name = "Centralized Conductor"
    def stim(self):
        oL, oR = self.arena.bilateral_odor(self.arena.pos, self.arena.theta)
        turn = np.clip((oL - oR) * 8.0, -1, 1)          # climb odour gradient
        fwd  = np.clip(0.5 + (oL+oR), 0, 1)
        return self._steer(turn, fwd)


class ReynoldsBoids(BaseController):
    """Decentralised local rules (Reynolds 1987): separation + alignment +
    cohesion + gradient-following, expressed as stimulation. No global info."""
    name = "Decentralized (boids+gradient)"
    def stim(self):
        pos, th = self.arena.pos, self.arena.theta
        A = self.brain.n_agents
        D = np.linalg.norm(pos[:,None]-pos[None], axis=2)
        head = np.stack([np.cos(th), np.sin(th)], axis=1)
        desired = np.zeros((A,2), np.float32)
        for a in range(A):
            nb = np.where((D[a] < 4.0) & (D[a] > 1e-6))[0]
            if len(nb):
                sep = np.sum((pos[a]-pos[nb]) / (D[a,nb,None]**2 + 1e-6), axis=0)  # separation
                ali = np.mean(head[nb], axis=0)                                     # alignment
                coh = np.mean(pos[nb], axis=0) - pos[a]                             # cohesion
                desired[a] = 1.4*sep + 1.0*ali + 0.5*coh
        oL, oR = self.arena.bilateral_odor(pos, th)
        grad_turn = (oL - oR) * 6.0
        # convert desired direction to a turn relative to current heading
        des_ang = np.arctan2(desired[:,1], desired[:,0])
        dth = np.arctan2(np.sin(des_ang-th), np.cos(des_ang-th))
        turn = np.clip(0.7*dth + grad_turn, -1, 1)
        fwd  = np.clip(0.5 + (oL+oR), 0, 1)
        return self._steer(turn, fwd)


class LeaderFollower(BaseController):
    """Partially-informed swarm (Couzin 2005): a few 'informed' agents know the
    source direction; the rest align to neighbours (consensus flocking)."""
    name = "Leader-follower (informed few)"
    def __init__(self, *a, n_informed=4, **k):
        super().__init__(*a, **k)
        self.informed = np.arange(n_informed)
    def stim(self):
        pos, th = self.arena.pos, self.arena.theta
        A = self.brain.n_agents
        D = np.linalg.norm(pos[:,None]-pos[None], axis=2)
        head = np.stack([np.cos(th), np.sin(th)], axis=1)
        turn = np.zeros(A, np.float32)
        # informed: head straight to source
        to_src = self.arena.source - pos
        src_ang = np.arctan2(to_src[:,1], to_src[:,0])
        dsrc = np.arctan2(np.sin(src_ang-th), np.cos(src_ang-th))
        # naive: align to neighbours
        for a in range(A):
            nb = np.where((D[a] < 5.0) & (D[a] > 1e-6))[0]
            ali = np.mean(head[nb], axis=0) if len(nb) else head[a]
            ali_ang = np.arctan2(ali[1], ali[0])
            turn[a] = np.arctan2(np.sin(ali_ang-th[a]), np.cos(ali_ang-th[a]))
        turn[self.informed] = dsrc[self.informed]
        turn = np.clip(turn, -1, 1)
        oL, oR = self.arena.bilateral_odor(pos, th)
        fwd = np.clip(0.55 + (oL+oR), 0, 1)
        return self._steer(turn, fwd)


class Stigmergy(BaseController):
    """Indirect coordination via environmental trails (ant-colony / stigmergy).
    Agents deposit pheromone, follow the gradient of the shared field + odour."""
    name = "Stigmergy (pheromone trails)"
    def stim(self):
        pos, th = self.arena.pos, self.arena.theta
        oL, oR = self.arena.bilateral_odor(pos, th)
        pL, pR = self.arena.sense_pheromone_gradient(th)
        turn = np.clip((oL-oR)*6.0 + (pL-pR)*1.5, -1, 1)
        fwd  = np.clip(0.5 + (oL+oR), 0, 1)
        return self._steer(turn, fwd)
    def post_move(self):
        self.arena.deposit_pheromone()


CONTROLLERS = [Autonomous, Centralized, ReynoldsBoids, LeaderFollower, Stigmergy]
