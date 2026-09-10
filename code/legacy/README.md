# Legacy prototype

These three modules are the pre-connectome prototype that preceded the
real-connectome work. They are kept because they produced results that are still
cited, not because they are part of the current stack.

- `cx_connectome.py` builds a central complex from published wiring *motifs*
  (Kim et al. 2017, Turner-Evans et al. 2020, Hulse et al. 2021) rather than from
  a downloaded adjacency matrix. Superseded by `../cx_real_dynamics.py`, which
  uses the real FlyWire weight matrix.
- `chorus_sim.py` and `chorus_controllers.py` are the reservoir-brain swarm
  testbed with a real odor gradient and five drone-swarm control paradigms.
  Superseded by `../cx_actuation.py` and `../chorus_env.py`.

**Why this matters for reading the results.** The `sphinx` and `paradigm_agg`
blocks in `../../data/results.json` come from this prototype, not from the
real-connectome pipeline. That includes the specificity ablation in which sign
scrambling matched or beat the intact network. The equivalent ablation on the real
connectome gives the opposite answer for signs (see `../../ABLATION_SPECIFICITY.md`),
so the two must not be conflated.

Nothing in the current pipeline imports from this directory.
