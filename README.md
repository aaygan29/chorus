# CHORUS — Connectome-Held Organism Reconstruction & Unified Steering

Fine control of a connectome-grounded *Drosophila* swarm via a minimal implantable BCI.
All dynamics run on the **real FlyWire v783** central-complex connectome
(1,051 neurons, 64,909 signed edges, 381,592 synapses) — not a hand-drawn motif.

## What's here

- **PAPER.md** — the full control monograph (read this first). Figures render
  inline from `figures/` when opened in any Markdown viewer.
- **figures/** — the 8 publication figures (PNG).
- **code/** — the simulation stack:
  - `cx_ring.py`         rate ring-attractor compass (EPG/PEN/Δ7)
  - `cx_spiking.py`      leaky integrate-and-fire spiking validation of the same ring
  - `cx_actuation.py`    the BCI actuation stack + BCIFly body model + swarm driver
  - `cx_real_dynamics.py` builds the attractor on the real FlyWire connectome
  - `chorus_env.py`      closed-loop Gym-like task environment (see below)
  - `run_env.py`         headless CLI runner for the task environment
  - `test_env_regression.py` regression gate checking the env against the published numbers
- **data/**
  - `cx_real.npz`        real CX subgraph (signed weight matrix, phases)
  - `cx_nodes.csv`       CX neuron table (ids, types, neurotransmitters)
  - `control_levers.csv` the 6 literature-grounded actuation levers + citations
  - `results.json`       all quantitative results (steps 3–9)
  - `spiking_*.npz`      spiking-validation raster / pointing / walk data

## Headline results (all on the real connectome)

| Capability | Result |
|---|---|
| Angular pointing error | 0.41° mean, uniform around the circle |
| Settling to <10° lock | ~13 steps |
| Point-to-point reach (no odor) | 100% arrival, 0.9 u error |
| Trajectory tracking (figure-8) | 0.17 u cross-track RMS |
| Swarm formation / split / shape-spell | 100% in-slot, no inter-fly comms |
| Minimal implant | ~8 electrodes → ~10° heading error |
| Spiking validation | rate-model precision reproduced in LIF, given a heading reference |

## The one load-bearing caveat (structure ≠ dynamics)

The raw connectome weights collapse to a single pinned state — the wiring alone
gives the ring *motif* but not a working attractor. A steerable continuous
attractor emerges only after E/I gains are calibrated to the measured ~24°
recurrent kernel. The spiking model sharpens this into a **design specification**:
the goal must live in a separate FC2 layer (never injected into the compass), and
a heading reference (ER ring neurons / landmark / sun) is required — exactly what
real fly navigation uses. See PAPER.md §2 and §13, and RESPONSIBLE_DISCLOSURE.md.

## Closed-loop task environment (`chorus_env.py`)

The connectome-analogue of the "connectome plays a game" demos, built as a
control instrument rather than a stunt: the measured output is control
fidelity (pointing error, cross-track RMS, arrival rate), not a score.

`ChorusEnv` is connectome-agnostic: it takes any `(npz, csv)` pair matching the
FlyWire schema (`W` signed float32, `root_ids` int64; nodes `root_id,cell_type,
side,nt`) and runs unchanged. Only the count of EPG-family neurons is read from
the connectome; the calibrated ring kernel (`kappa=5.6, w_exc=1.9, w_inh=0.28`)
is applied regardless of which connectome is loaded, since raw connectome
weights do not by themselves give a working attractor (§2 of the monograph).
Applying the FlyWire-measured kernel to a second species without re-measuring
its own recurrent kernel is a modeling assumption, not a validated fact, and is
flagged as such in the module docstring.

Gym-like API, dependency-light (numpy/scipy/pandas/matplotlib only; a thin
`GymChorusEnv` wrapper is exposed if `gymnasium` happens to be importable):

```python
from chorus_env import ChorusEnv, TrackingTask
env = ChorusEnv('data/flywire/cx_real.npz', 'data/flywire/cx_nodes.csv',
                 n_electrodes=8, max_steps=400)
env.set_task(TrackingTask(path=my_figure8_xy))
obs, info = env.reset(seed=0)          # obs = [decoded_heading, decoded_amp, target_bearing, target_range]
obs, reward, terminated, truncated, info = env.step((goal_heading, speed))
```

- **Action** is the BCI write only: `(goal_heading_rad, speed)` (lever L1+L4
  from the monograph). The agent never writes arbitrary neural state.
- **Observation** is what a real implant could plausibly decode: the
  population-vector EPG heading + amplitude, plus task-level target bearing
  and range. `info` carries decoded heading, true body heading, compass-body
  offset, and per-step angular error.
- **Electrode model** (`Electrode` class) quantizes the goal to `n_electrodes`
  sites tiling the EPG ring (heading error ≈ 90°/n), with optional per-step
  goal noise and site dropout (§8).
- **Compass calibration** (`calibrate=True/False`): reset() runs a
  visual-landmark alignment epoch that sets the internal compass to the body's
  allocentric heading before control starts (§7 design rule, discovered as an
  init bug). Turning it off reproduces the failure on demand: mean
  `|true_heading - goal|` over a fixed-goal probe goes from ~9° (calibrated)
  to ~92° (uncalibrated) on the FlyWire connectome: a systematic compass-body
  offset, not noise.
- **Goal-write mechanism**: by default the goal is injected on the compass
  ring's own `ext` channel and read out via `RingCX.pfl3_turn`. This is
  exactly `cx_actuation.BCIFly`'s mechanism and is what the monograph's rate-
  model numbers were measured with. `RingCX` also has a separate mechanistic
  FC2 goal-bump layer (`init_goal_layer`/`step_goal`/`pfl3_turn_from_layer`)
  that never touches the compass at all, more defensible against the spiking
  model's "goal current teleports the compass bump" failure mode (§13), and
  it is available via `ChorusEnv(..., goal_layer=True)`. It gives a visibly
  worse ~5° steady pointing error in this codebase and is not what the
  regression gate below checks; it is offered for anyone who wants the more
  conservative, spiking-consistent architecture instead of the validated
  rate-model one.

**Tasks** (`PursuitTask`, `TrackingTask`, `ObstacleTask`) share the same env
and differ only in target dynamics, observation of target bearing/range, and
the metrics they accumulate (`task.metrics()` after an episode):

| Task | Metric |
|---|---|
| `PursuitTask` | cross-track RMS to the moving target's path, capture time |
| `TrackingTask` | cross-track RMS to a parametric path (figure-8, circle, ...) |
| `ObstacleTask` | arrival rate, path efficiency (straight-line dist / path length), via an artificial-potential-field bearing that sums target attraction and obstacle repulsion |

### CLI runner

```
python code/run_env.py --connectome flywire --task tracking --electrodes 8 \
    --steps 400 --seed 0 --out figures/run_tracking
```

Runs one episode with a bearing-pursuit + distance/heading-taper controller,
prints step progress, and writes `<out>.json` (metrics) and `<out>.png`
(trajectory plot). `--connectome malecns` looks for
`data/malecns_cx/cx_real_male.npz` + `cx_nodes_male.csv` and needs no code
change once that extraction lands.

### Regression gate

`code/test_env_regression.py` asserts `ChorusEnv` reproduces the published
FlyWire numbers within the tolerances specified in the task brief:

| Check | Published | Tolerance | Measured |
|---|---|---|---|
| Pointing error (continuous goal-write) | 0.41° | <2° | 0.39° |
| Figure-8 cross-track RMS | 0.17 u | <0.5 u | 0.07 u |
| 8-electrode pointing error | ~10° | 7–14° | 10.2° |

Run with `python code/test_env_regression.py` or `pytest code/test_env_regression.py`.
A failing check is left failing rather than tuned to pass. The point of the
gate is to catch drift, not to always report green.

## Reproducibility

Python 3 + numpy/scipy/matplotlib/pandas. Each figure script reads from `data/`
and is traceable through `results.json`. See PAPER.md for per-figure methods.
