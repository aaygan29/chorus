# CHORUS

**Connectome-Held Organism Reconstruction & Unified Steering**

Putting a real insect connectome inside a closed control loop, and measuring what
the connectome actually contributes to the behaviour that comes out.

CHORUS drives a simulated *Drosophila* by writing a single one-dimensional goal
heading into the central complex, the fly's navigation hub, and letting the fly's
own steering circuit close the loop. It runs on two real connectomes: the FlyWire
v783 female brain and the MaleCNS v1.0 male brain and ventral nerve cord.

## Why this exists

In September 2026 a collaboration between HHMI Janelia, the University of
Cambridge, the MRC Laboratory of Molecular Biology and Google Research released
the complete connectome of a male *Drosophila* central nervous system: over
166,000 neurons and roughly 125 million synaptic connections spanning brain and
nerve cord in a single animal. Within days, developers had wired that connectome
into video games, mapping frames onto sensory neurons and neural activity onto
game controls.

Those demos ask an interesting question in an uninstrumented way. Connecting a
connectome to a game and watching what happens tells you very little, because
there is no measurement that separates "the connectome is computing something"
from "the harness around it is computing something." A network that produces
plausible-looking behaviour may be contributing nothing at all, and without an
ablation you cannot tell.

CHORUS asks the same question with the measurement attached. The fly is placed in
closed-loop tasks (pursuit, trajectory tracking, obstacle avoidance) driven only
through a biologically precedented control channel, the outputs are control
fidelity rather than a score, and the connectome is ablated against matched nulls
to test whether it is load-bearing.

The current answer is not a clean yes, and this repository documents that
honestly. See **Current status** below.

## The control approach

A fly performing menotaxis holds an arbitrary goal heading with no gradient
present, because the goal is represented internally. So a brain-computer interface
does not need to fake a stimulus. It writes the goal, and the fly's own ring
attractor does the steering.

Six actuation levers were mapped from the *Drosophila* navigation literature, five
with direct in-vivo optogenetic precedent. The anchor is **L1**, a goal-heading
write into the FC2 layer, which has a direct demonstration in a behaving animal
(Mussells Pires, Abbott & Maimon 2024, *Nature*). Full taxonomy in
`data/control_levers.csv` and section 3 of the monograph.

## The central finding: structure does not determine dynamics

This is the most robust result here and the one worth carrying forward.

When the extracted signed weight matrix is used directly as the recurrent matrix
of a rate network, the heading bump does **not** behave as a continuous attractor.
It collapses onto a single globally pinned location regardless of input. The
wiring supplies the ring attractor's motif, but not a working ring attractor.

A steerable continuous attractor appears only after the excitatory/inhibitory
balance is calibrated. The connectome tells you the circuit; the synaptic gains
decide whether that circuit computes.

This now replicates on a second connectome. The MaleCNS CX pins at 90.0 degrees
with a standard deviation of 0.0004 across every seed and every commanded goal
(`ABLATION_SPECIFICITY.md`).

## Current status, and three open problems

The published control results (0.41 degree pointing, 0.17 unit figure-8 tracking,
100% point-to-point arrival) were produced by the calibrated ring pipeline, not by
simulating the raw connectome. That distinction was under-stated in earlier
versions of this README, which described the results as "all on the real
connectome." The accurate statement is that they run on a ring attractor whose
kernel width and population structure are derived from the real connectome.

Three problems currently prevent a clean claim in either direction:

1. **The pipeline that uses the connectome does not work.** `cx_real_dynamics.py`
   simulates the real weight matrix and pins, exactly as section 2 describes.
2. **The pipeline that works does not use the connectome.** `chorus_env.py`
   reproduces the published numbers while building the ring from a canonical
   16-wedge tiling with fitted gains. It loads the weight matrix and never reads
   it.
3. **The bridge between them cannot be reproduced.** The only channel from
   connectome to calibrated model is the measured recurrent kernel. The code that
   produced the published ~24 degree figure is not in this repository, and
   independent reimplementation gives 30.7 to 36.7 degrees depending on
   convention. The published value is recovered exactly as `1/sqrt(5.6)`, the
   circular standard deviation of the *calibrated* kappa, which raises the
   possibility that the measurement and the calibration are the same number
   (`KERNEL_RECOVERY.md`).

Until one of these changes, the connectome cannot be shown to be load-bearing for
the fine-control results, in either direction. The unblocking step is problem 3.

## What the ablation found

20 seeds per condition on the pipeline that does read the weight matrix, with the
null re-randomized per seed (`ABLATION_SPECIFICITY.md`).

| Condition | Pointing (deg) | Figure-8 RMS | Arrival |
|---|---|---|---|
| intact | 71.1 +/- 7.8 | 9.86 +/- 1.00 | 0.0% |
| sign_scramble | 87.0 +/- 3.9 | 12.89 +/- 0.52 | 1.9% |
| edge_shuffle | 81.2 +/- 12.1 | 9.84 +/- 3.35 | 8.1% |
| degree_matched_random | 82.6 +/- 8.3 | 9.86 +/- 3.06 | 1.9% |

**Sign structure is load-bearing.** Scrambling neurotransmitter signs is reliably
worse than intact on all three outcomes (Cohen's d = 2.58, 3.80, 5.69, all
p < 0.003).

**Topology specificity is mixed.** Intact beats both topology nulls on pointing
error (d = 1.00 and 1.42) but is statistically indistinguishable from both on
figure-8 tracking and point-to-point error, with a minimum detectable effect of
d = 0.89 at n=20.

Read these as differences between degrees of failure. Every condition sits between
71 and 87 degrees against a chance level near 90, because this is the uncalibrated
pipeline. They bound how much the connectome perturbs a non-working model, not how
much it contributes to working control.

## Two connectomes

| | FlyWire v783 (female) | MaleCNS v1.0 (male) |
|---|---|---|
| CX neurons | 1,051 | 1,161 (1,069 family-matched) |
| Signed edges | 64,909 | 105,409 |
| Synapses | 381,592 | 1,000,211 |

The male extraction independently reproduces the textbook circuit signs on a
different animal, sex and reconstruction pipeline: EPG cholinergic 46/46, Delta7
glutamatergic 42/42, PFL3 cholinergic 24/24.

The male graph carries roughly 2.6x the synapses per neuron, almost certainly
reconstruction depth and the `minconf 0.5` synapse threshold rather than biology.
`match_density.py` emits density-matched variants so that a difference between
connectomes can be separated from a difference between reconstructions. See
`MALECNS_EXTRACTION.md` and `DENSITY_CONTROL.md`.

## The path below the neck

MaleCNS is the first connectome with brain and ventral nerve cord traced in the
same animal. `data/malecns_cx/dn_vnc_edges.csv` holds the descending-neuron to VNC
to motor-neuron edge list (40,320 rows) for DNa02, DNp09 and MDN, the actuation
targets of levers L2, L5 and L6.

This matters for the problems above. CHORUS currently stops at the descending
neuron and replaces everything below with a kinematic point mass carrying heading
and speed. Below the neck there is no attractor calibration standing between the
connectome and the behaviour, so the wiring is load-bearing by construction. If a
PFL3 left-right bias produces a turn through real VNC circuitry, the connectome
did that, and it cannot be attributed to hand-set gains.

## Closed-loop task environment

`chorus_env.py` provides a Gym-like API over the fly. Dependency-light
(numpy/scipy/pandas/matplotlib; a `GymChorusEnv` wrapper appears if `gymnasium` is
importable).

```python
from chorus_env import ChorusEnv, TrackingTask
env = ChorusEnv('data/cx_real.npz', 'data/cx_nodes.csv', n_electrodes=8)
env.set_task(TrackingTask(path=my_figure8_xy))
obs, info = env.reset(seed=0)
obs, reward, terminated, truncated, info = env.step((goal_heading, speed))
```

- **Action** is the BCI write only: `(goal_heading_rad, speed)`. The agent never
  writes arbitrary neural state. Restricting the channel to the one lever with
  in-vivo precedent is the point, not a limitation.
- **Observation** is what an implant could plausibly decode: population-vector EPG
  heading and amplitude, plus target bearing and range.
- **Electrode model** quantizes the goal to `n_electrodes` sites tiling the EPG
  ring, with optional goal noise and site dropout.
- **Compass calibration** (`calibrate=True/False`) runs a landmark-alignment epoch
  before control starts. Turning it off reproduces the divergence failure on
  demand, going from about 9 degrees to about 92 degrees of compass-body offset.

Tasks: `PursuitTask` (cross-track RMS, capture time), `TrackingTask` (cross-track
RMS to a parametric path), `ObstacleTask` (arrival rate, path efficiency).

```
python code/run_env.py --connectome flywire --task tracking --electrodes 8 \
    --steps 400 --seed 0 --out figures/run_tracking
```

`code/test_env_regression.py` gates the env against the published numbers. A
failing check is left failing rather than tuned to pass. Note problem 2 above when
interpreting a pass.

## Repository

- `CHORUS_fine_control.md` is the control monograph. Start here.
- `COUNCIL_REVIEW.md` is an adversarial internal review of that monograph, verdict
  MAJOR REVISION, with numbers recomputed from `data/results.json`.
- `ABLATION_SPECIFICITY.md`, `KERNEL_RECOVERY.md`, `MALECNS_EXTRACTION.md`,
  `DENSITY_CONTROL.md` are the follow-up studies.
- `THREAT_MODEL.md` and `RESPONSIBLE_DISCLOSURE.md` cover dual-use.
- `code/` holds the simulation stack, the extraction and analysis scripts, and the
  environment. `data/` holds both connectomes and all results. `figures/` holds the
  publication figures.

## Data provenance

- **FlyWire v783**, public.
- **MaleCNS v1.0**, CC-BY 4.0, from the FlyEM flat-connectome release. Source
  tables (1.1 GB) are not committed; `code/extract_malecns_cx.py` documents the
  URLs and SHA256s, and the derived CX subgraphs are committed under
  `data/malecns_cx/`.

No restricted data is used anywhere in this project.

## Dual use

This is computational work on public connectome data, but the capability it
characterizes is directed control of an animal's navigation through a minimal
brain implant, and that carries real weight. Any wet-lab realization steers a
sentient animal against its own volition and falls under institutional animal-care
oversight. In the abstract, a minimal implant that directs a flying insect to
arbitrary targets with no external cue is a biological-drone capability.

The MaleCNS release adds a traced brain-to-motor pathway in a single animal, which
shifts that profile further. `RESPONSIBLE_DISCLOSURE.md` should be revised before
any work extends below the neck.

## Reproducibility

Python 3 with numpy, scipy, pandas and matplotlib. Results trace through
`data/results.json` and `data/ablation_results.json`. Seed handling is documented
per script; note that the original monograph reports single-run point estimates
without seed variance, which `COUNCIL_REVIEW.md` records as an open finding.

## License

MIT (code). MaleCNS v1.0 derived data is CC-BY 4.0, attribution to the FlyEM
project team at HHMI Janelia, the University of Cambridge, the MRC Laboratory of
Molecular Biology and Google Research.
