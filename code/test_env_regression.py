"""Regression gate: chorus_env.ChorusEnv must reproduce the published CHORUS
numbers (docs/CHORUS_fine_control.md) on the real FlyWire v783 connectome.
Tolerances are loose (per task spec) but real: if a number moves outside its
band, this FAILS and prints the actual value. Do not widen a tolerance to
silence a failure -- report the discrepancy instead.
"""
import os
import numpy as np
from chorus_env import ChorusEnv, TrackingTask, wrap

HERE = os.path.dirname(os.path.abspath(__file__))
NPZ = os.path.join(HERE, '..', 'data', 'flywire', 'cx_real.npz')
CSV = os.path.join(HERE, '..', 'data', 'flywire', 'cx_nodes.csv')


def pointing_error_deg(n_electrodes, settle=100, trials=12):
    env = ChorusEnv(NPZ, CSV, n_electrodes=n_electrodes, max_steps=settle)
    errs = []
    for k in range(trials):
        goal = -np.pi + 2 * np.pi * k / trials
        obs, info = env.reset(seed=k)
        for i in range(settle):
            obs, r, term, trunc, info = env.step((goal, 0.0))
        errs.append(abs(np.degrees(wrap(info['decoded_heading'] - goal))))
    return float(np.mean(errs))


def figure8_cross_track_rms(n_steps=400, scale=6.0):
    def fig8(t):
        th = 2 * np.pi * t / n_steps
        return scale * np.sin(th), scale * np.sin(th) * np.cos(th)
    ref = np.array([fig8(t) for t in range(n_steps)])
    env = ChorusEnv(NPZ, CSV, n_electrodes=None, max_steps=n_steps)
    task = TrackingTask(ref, lookahead=3)
    env.set_task(task)
    obs, info = env.reset(seed=0)
    env.x, env.y = ref[0]
    for t in range(n_steps):
        goal, d = obs[2], obs[3]
        speed = np.clip(d / 4.0, 0.15, 1.0)
        obs, r, term, trunc, info = env.step((goal, speed))
    return task.metrics()['cross_track_rms']


def test_pointing_continuous():
    err = pointing_error_deg(n_electrodes=None)
    print(f"pointing (continuous) mean error: {err:.3f} deg  (published 0.41 deg, tol <2 deg)")
    assert err < 2.0, f"pointing error {err:.3f} deg exceeds 2 deg tolerance"


def test_figure8_tracking():
    rms = figure8_cross_track_rms()
    print(f"figure-8 cross-track RMS: {rms:.3f} units  (published 0.17 units, tol <0.5)")
    assert rms < 0.5, f"figure-8 RMS {rms:.3f} exceeds 0.5-unit tolerance"


def test_8_electrode_pointing():
    err = pointing_error_deg(n_electrodes=8)
    print(f"8-electrode pointing mean error: {err:.3f} deg  (published ~10 deg, tol 7-14 deg)")
    assert 7.0 <= err <= 14.0, f"8-electrode error {err:.3f} deg outside 7-14 deg band"


if __name__ == '__main__':
    tests = [test_pointing_continuous, test_figure8_tracking, test_8_electrode_pointing]
    failures = []
    for i, t in enumerate(tests):
        print(f"[{i+1}/{len(tests)}] running {t.__name__} ...")
        try:
            t()
            print("  PASS")
        except AssertionError as e:
            print(f"  FAIL: {e}")
            failures.append(t.__name__)
    print("---")
    if failures:
        print(f"{len(failures)}/{len(tests)} regression checks FAILED: {failures}")
        raise SystemExit(1)
    print(f"all {len(tests)} regression checks passed")
