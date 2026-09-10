"""Headless runner for chorus_env: drives one episode of a task with a simple
built-in bearing+taper controller, writes a metrics JSON and a trajectory PNG.
No GUI required (matplotlib Agg backend).

Example:
  python run_env.py --connectome flywire --task tracking --electrodes 8 \
      --steps 400 --seed 0 --out ../figures/run_tracking
"""
import argparse
import json
import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from chorus_env import ChorusEnv, PursuitTask, TrackingTask, ObstacleTask, wrap

CONNECTOMES = {
    'flywire': ('../data/cx_real.npz', '../data/cx_nodes.csv'),
    'malecns': ('../data/malecns_cx/cx_real_male.npz', '../data/malecns_cx/cx_nodes_male.csv'),
}


def fig8(t, n_steps, scale=6.0):
    th = 2 * np.pi * t / n_steps
    return scale * np.sin(th), scale * np.sin(th) * np.cos(th)


def circle(t, n_steps, scale=5.0):
    th = 2 * np.pi * t / n_steps
    return scale * np.cos(th), scale * np.sin(th)


def build_task(name, steps):
    if name == 'pursuit':
        target_fn = lambda t: (5 * np.cos(t * 0.02), 5 * np.sin(t * 0.02))
        return PursuitTask(target_fn, capture_r=1.0), None
    if name == 'tracking':
        ref = np.array([fig8(t, steps) for t in range(steps)])
        return TrackingTask(ref, lookahead=3), ref
    if name == 'obstacle':
        return ObstacleTask((10, 0), [(5, 0, 2)], arrive_r=1.0, margin=2.0), None
    raise ValueError(f"unknown task {name}")


def controller(obs, info):
    """Bearing-pursuit with distance + heading-alignment speed taper. Not part
    of the env API -- a stand-in for whatever policy drives the BCI goal-write."""
    goal, d = float(obs[2]), float(obs[3])
    err = abs(wrap(goal - info['true_heading']))
    align = np.clip(1.0 - err / 1.2, 0.1, 1.0)
    speed = float(np.clip(d / 4.0, 0.15, 1.0) * align)
    return goal, speed


def run(args):
    npz_default, csv_default = CONNECTOMES.get(args.connectome, (args.connectome, args.csv))
    npz = args.npz or os.path.join(os.path.dirname(__file__), npz_default)
    csv = args.csv or os.path.join(os.path.dirname(__file__), csv_default)
    if not os.path.exists(npz):
        raise FileNotFoundError(f"connectome npz not found: {npz}")

    n_elec = None if args.electrodes <= 0 else args.electrodes
    env = ChorusEnv(npz, csv, n_electrodes=n_elec, max_steps=args.steps)
    task, ref = build_task(args.task, args.steps)
    env.set_task(task)
    obs, info = env.reset(seed=args.seed)
    if args.task == 'tracking':
        env.x, env.y = ref[0]
    if args.task == 'obstacle':
        env.x, env.y = 0.0, 0.0

    xs, ys, errs = [env.x], [env.y], []
    print(f"running {args.task} on {args.connectome}: {args.steps} steps, {args.electrodes} electrodes")
    for t in range(args.steps):
        action = controller(obs, info)
        obs, reward, terminated, truncated, info = env.step(action)
        xs.append(env.x); ys.append(env.y); errs.append(info['angular_error'])
        if (t + 1) % max(1, args.steps // 10) == 0 or t == args.steps - 1:
            pct = 100 * (t + 1) / args.steps
            print(f"  step {t+1}/{args.steps} ({pct:.0f}%) heading_err={np.degrees(info['angular_error']):.2f} deg")
        if terminated:
            print(f"  terminated at step {t+1}")
            break

    metrics = dict(task=args.task, connectome=args.connectome, electrodes=args.electrodes,
                    steps=t + 1, seed=args.seed,
                    mean_angular_error_deg=float(np.degrees(np.mean(errs))),
                    **task.metrics())
    os.makedirs(os.path.dirname(args.out) or '.', exist_ok=True)
    with open(args.out + '.json', 'w') as f:
        json.dump(metrics, f, indent=2)

    fig, ax = plt.subplots(figsize=(5, 5))
    ax.plot(xs, ys, '-', lw=1, color='tab:blue', label='fly path')
    if ref is not None:
        ax.plot(ref[:, 0], ref[:, 1], '--', lw=1, color='tab:orange', label='reference')
    if args.task == 'obstacle':
        for (ox, oy, r) in task.obstacles:
            ax.add_patch(plt.Circle((ox, oy), r, color='gray', alpha=0.4))
        ax.scatter(*task.target_xy, marker='*', s=120, color='green', label='target')
    ax.set_aspect('equal'); ax.legend(); ax.set_title(f"{args.task} ({args.connectome}, {args.electrodes} elec)")
    fig.savefig(args.out + '.png', dpi=130)
    print(f"wrote {args.out}.json and {args.out}.png")
    print(json.dumps(metrics, indent=2))
    return metrics


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--connectome', default='flywire', choices=list(CONNECTOMES.keys()))
    p.add_argument('--npz', default=None, help='override connectome npz path')
    p.add_argument('--csv', default=None, help='override node csv path')
    p.add_argument('--task', default='tracking', choices=['pursuit', 'tracking', 'obstacle'])
    p.add_argument('--electrodes', type=int, default=8)
    p.add_argument('--steps', type=int, default=400)
    p.add_argument('--seed', type=int, default=0)
    p.add_argument('--out', default='../figures/run_env_out')
    args = p.parse_args()
    run(args)


if __name__ == '__main__':
    main()
