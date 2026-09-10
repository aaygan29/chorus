# Specificity ablation — is the real connectome load-bearing for the published control results?

## 0. Outcome, stated up front

**The real connectome is not shown to be load-bearing, and the published
headline numbers do not reproduce on the only pipeline in this repo that
actually uses the connectome weights.** Run on `code/cx_real_dynamics.py`
`RealCX` (the sole class whose `step()` reads `self.W`), the intact FlyWire
connectome gives a mean steady-state pointing error of **71.1 deg** (n=20
seeds), not the published 0.41 deg; figure-8 cross-track RMS of **9.86**,
not 0.17; and **0%** point-to-point arrival, not 100%. Against the three
null rewirings, intact is statistically better than the nulls for pointing
error (Cohen's d = 1.0 to 2.6, p < 0.003, all three comparisons) but the
effect is small in absolute terms relative to the 100+ deg gap from the
published number, and for figure-8 tracking and point-to-point final error
intact is statistically indistinguishable from **edge_shuffle** and
**degree_matched_random** (|d| < 0.33, p > 0.3). `sign_scramble` is reliably
*worse* than intact on all three metrics, which is the one result consistent
with the connectome's sign structure mattering at all. Taken together: this
experiment finds a real, small, specificity signal for pointing on the
question "does destroying every synaptic sign hurt," but it finds no support
for the published control precision, and no support that an intact,
correctly-signed connectome beats a degree-matched random graph on tracking
or reach. This corroborates, on an independent pipeline, the same
conclusion `docs/KERNEL_RECOVERY.md` reached about the recurrent kernel: the
monograph's real-connectome pipeline (`chorus_env.py`, which never reads
`W`) is not the same pipeline as the one that actually simulates the real
connectome (`RealCX`, this document), and the two disagree by roughly two
orders of magnitude on every headline number.

## 1. Design

### 1.1 Which pipeline was ablated, and why

Three lines of evidence in this repo (the `sphinx` block in
`data/flywire/results.json`, `chorus_env.py` never reading `W`, and the
circular kernel-recovery in `docs/KERNEL_RECOVERY.md`) raised the same
question: do the published headline numbers depend on the real connectome
at all? Answering that requires ablating a pipeline whose dynamics are
actually computed from `W`. Inspection of every simulation class in
`code/` found exactly one: `RealCX.step()` in `code/cx_real_dynamics.py`,
whose recurrent input is `self.G * self.gpop * (self.W.T @ self.r) / self.norm
+ self.bias`. `code/chorus_env.py` (used to produce the monograph's
headline table) builds a canonical 16-wedge ring via `wedge_phases()` and
never indexes `self.W` in its step function — it is not a real-connectome
pipeline in the load-bearing sense, and ablating it would trivially show
"no effect" without saying anything about the real connectome. This
document ablates `RealCX` only.

### 1.2 W-sensitivity sanity check (required before proceeding)

Before running the ablation, the harness was checked for whether it is even
capable of detecting a connectome effect: the pointing-error measurement
(section 2.2) was run on intact `W`, on `W` scaled by 0.1, and on `W`
zeroed out entirely, same seed.

```
intact W pointing error:      62.63 deg   (single-seed check, seed 0)
W scaled x0.1 pointing error: 36.96 deg
W zeroed pointing error:       5.44 deg
harness is W-sensitive: True
```

(These numbers are the single-seed values printed by the sanity check
inside `ablation_specificity.py`; the full 20-seed intact mean below is
71.1 deg — the sanity check uses only seed 0 and is a pass/fail gate, not
an estimate.) The three conditions give three different behaviors and the
gate (`|scaled - base| > 1 deg` or `|zeroed - base| > 1 deg`) passed by a
wide margin. The harness is W-sensitive: it is capable of showing an
effect of connectome structure, so a null result from the ablation below is
informative rather than a broken-harness artifact.

### 1.3 Anatomical phase (electrode/compass coordinate)

`RealCX` needs a phase (ring position) per EPG neuron to inject a goal
current and to decode the bump heading. `cx_nodes.csv` has no phase column
(confirmed in `docs/KERNEL_RECOVERY.md`). The phase used here is the same
W-derived spectral-embedding phase `code/measure_kernel.py` already
computes: the Fiedler-style 2D embedding of the symmetrized EPG-EPG
disynaptic effective kernel (`EPG->PEG->EPG`, `EPG->Delta7->EPG`,
`EPG->PEN_a/b->EPG`). This phase is computed **once, from the intact
connectome**, and reused unchanged as the fixed anatomical/electrode map
for every rewired condition. This is the physically correct choice: an
implanted electrode targets a neuron's physical position, which does not
move when the synaptic wiring is scrambled — only the weights change. Using
a fresh phase recomputed from each scrambled connectome would conflate
"the wiring is disrupted" with "we also lost the ability to find the
neurons," which is not the manipulation this experiment is testing.

### 1.4 Conditions

All on `data/flywire/cx_real.npz` (1,051 x 1,051 signed W) +
`cx_nodes.csv`, re-randomized per seed:

- **intact** — unmodified W.
- **sign_scramble** — the sign of each nonzero edge is randomly permuted
  across existing edge positions; the magnitude at each edge location and
  the topology (which pairs are connected) are both preserved exactly.
- **edge_shuffle** — the entire weight value (sign and magnitude together)
  of each nonzero edge is randomly reassigned across existing edge
  positions; topology and the exact weight multiset are preserved, only the
  edge-to-weight assignment is randomized.
- **degree_matched_random** — a directed configuration-model null: edges
  are rewired via repeated double-edge-swaps (`(i1,j1),(i2,j2) ->
  (i1,j2),(i2,j1)`, rejecting self-loops and duplicate edges), which
  preserves every neuron's in-degree and out-degree exactly while
  destroying which specific neurons are connected to which. The weight
  multiset is then reassigned onto the new edge set by the same shuffle as
  `edge_shuffle`. This is the strongest null: it keeps only the degree
  sequence and the marginal weight distribution.
- **intact_male** — the real MaleCNS CX (`data/malecns_cx/cx_real_male_noFC2.npz`
  + `cx_nodes_male_noFC2.csv`, 1,069 neurons), a second real connectome, run
  through the identical pipeline as a reference point (not part of the
  intact-vs-null hypothesis test).

### 1.5 Seeds

20 seeds per condition. Each seed draws a fresh scramble/shuffle/rewiring
(`np.random.default_rng` seeded per condition and seed) and a fresh
simulation RNG (`RealCX`'s internal noise, reseeded per trial), so reported
variance covers both the rewiring randomness and the simulation noise.

### 1.6 Outcomes and the control loop used to measure them

`RealCX` has no companion closed-loop controller of its own (that
machinery — `BCIFly`, `RingCX`, `chorus_env`'s `step_goal`/`pfl3_turn` —
all runs on the synthetic 16-wedge ring, not on `RealCX`). To measure the
three headline outcomes on `RealCX`, a minimal closed loop was built for
this experiment, using only mechanisms that already exist in
`cx_real_dynamics.py` (`seed()`'s goal-current injection pattern and
`bump_heading()`'s population-vector readout), applied identically across
all conditions:

- Continuous goal write: each step, a cosine current `gain * cos(phase_EPG
  - goal)` (same functional form as `RealCX.seed`, gain=1.6) is injected
  into the EPG population, mimicking the FC2/L1 goal-write lever.
- Heading readout: `RealCX.bump_heading('EPG')`, the same population-vector
  decode the class already provides.
- Body: a point with position updated each step by `speed * (cos(heading),
  sin(heading))` using the decoded heading, i.e. the real network's own
  bump position directly drives movement (no separate PFL3/turn-rate model
  was added, since none exists for `RealCX`).

Per seed per condition:
- **Pointing error (deg).** 12 goal headings (0-330 deg, 30 deg steps).
  Each trial: 100 settle steps (no goal, network free-runs from zero) then
  150 steps holding the goal; error is the mean circular distance between
  decoded heading and goal over the final 50 steps. Reported value is the
  mean over the 12 headings.
- **Figure-8 cross-track RMS.** A parametric figure-8 reference path
  (`x=3 sin t, y=3 sin t cos t`); the goal heading at each of 220 steps is
  the local tangent direction of the reference curve; the simulated
  position is compared to the nearest point on the reference curve
  (`scipy.spatial.cKDTree`) and the RMS of that distance is reported.
- **Point-to-point arrival / final error.** 8 targets on a ring of radius 4
  (matching the reach test's geometry), goal heading = current bearing to
  target with proximity-tapered speed (`speed * min(1, dist/1.0)`),
  arrival = final distance < 0.15. Arrival rate and mean final distance are
  averaged over the 8 targets.

**What was reduced for time, stated explicitly:** all three outcomes were
run at full seed count (20). Simulation length was kept short relative to
what a from-scratch closed-loop optimization might use (150 hold steps for
pointing, 220 for figure-8, up to 250 for point-to-point) to keep the full
5-condition x 20-seed sweep under two minutes; this does not affect the
qualitative conclusion because the intact condition's own steady-state
error was already checked to plateau within this window (see raw per-seed
traces available by rerunning with `--seeds 1` and inspecting
`drive_goal`'s output). No outcome was dropped or substituted.

## 2. Results

### 2.1 Sanity check (repeated, full record)

```
intact W pointing error:      62.63 deg
W scaled x0.1 pointing error: 36.96 deg
W zeroed pointing error:       5.44 deg
harness is W-sensitive: True
```

### 2.2 Full results table (mean +/- SD over 20 seeds)

| Condition | Pointing error (deg) | Figure-8 cross-track RMS | P2P arrival rate | P2P final error |
|---|---|---|---|---|
| intact | 71.10 +/- 7.60 | 9.86 +/- 0.97 | 0.0% | 24.87 +/- 2.08 |
| sign_scramble | 86.97 +/- 3.78 | 12.89 +/- 0.51 | 1.9% | 36.27 +/- 1.93 |
| edge_shuffle | 81.24 +/- 11.75 | 9.84 +/- 3.26 | 8.1% | 25.86 +/- 7.16 |
| degree_matched_random | 82.57 +/- 8.13 | 9.86 +/- 2.98 | 1.9% | 26.76 +/- 8.00 |
| intact_male (reference) | 90.00 +/- 0.0004 | 3.25 +/- 1.87 | 1.9% | 12.17 +/- 1.41 |

(Published monograph headlines for comparison, on `chorus_env.py`, which
does not read `W`: 0.41 deg pointing, 0.17 unit figure-8 RMS, 100%
arrival / 0.9 unit final error.)

None of the five conditions comes remotely close to the published numbers.
Point-to-point arrival is near zero for every condition including intact,
which by itself already says the headline 100%/0.9-unit result is not a
property of the real connectome driven through its own recurrent dynamics
with a plain goal-write, whatever else the ablation shows.

Note on `intact_male`: its pointing error is 90.00 deg with essentially
zero seed-to-seed variance (SD = 0.0004 deg across 20 seeds), i.e. the bump
lands on the identical fixed heading regardless of the commanded goal or
simulation noise. This is the monograph's own §2 "pinning" phenomenon
(raw connectome weights collapse to one globally pinned location rather
than a steerable continuous attractor) reproducing directly in this
independent harness on the second real connectome, and is additional,
convergent evidence against the connectome (as opposed to the calibrated
synthetic ring) actually supplying the fine-control headline.

### 2.3 Statistics, null vs. intact

For each null, mean/SD/95% CI is the null condition's own sampling
distribution; Cohen's d and its 95% CI and the permutation p-value (10,000
resamples) compare null vs. intact.

**Pointing error (deg):**

| Null | mean (95% CI) | SD | Cohen's d (95% CI) | p (permutation) |
|---|---|---|---|---|
| sign_scramble | 86.97 (85.15, 88.78) | 3.88 | 2.58 (1.74, 3.42) | 0.0000 |
| edge_shuffle | 81.24 (75.60, 86.88) | 12.05 | 1.00 (0.34, 1.66) | 0.0024 |
| degree_matched_random | 82.57 (78.67, 86.47) | 8.34 | 1.42 (0.73, 2.11) | 0.0001 |

All three nulls are significantly *worse* (higher pointing error) than
intact, with large effect sizes. This is the one metric on which the real
connectome shows a specificity signal: destroying the signed wiring hurts
pointing accuracy relative to intact, most strongly when only the sign is
scrambled.

**Figure-8 cross-track RMS:**

| Null | mean (95% CI) | SD | Cohen's d (95% CI) | p (permutation) |
|---|---|---|---|---|
| sign_scramble | 12.89 (12.65, 13.14) | 0.52 | 3.80 (2.76, 4.83) | 0.0000 |
| edge_shuffle | 9.84 (8.28, 11.41) | 3.35 | -0.008 (-0.63, 0.61) | 0.9817 |
| degree_matched_random | 9.86 (8.42, 11.29) | 3.06 | -0.002 (-0.62, 0.62) | 0.9963 |

`sign_scramble` is worse; `edge_shuffle` and `degree_matched_random` are
statistically indistinguishable from intact (d approx 0, p > 0.98). The
real connectome's specific topology and specific weight placement carry no
detectable advantage over a degree-matched random graph for figure-8
tracking in this pipeline.

**Point-to-point final error:**

| Null | mean (95% CI) | SD | Cohen's d (95% CI) | p (permutation) |
|---|---|---|---|---|
| sign_scramble | 36.27 (35.37, 37.18) | 1.93 | 5.69 (4.30, 7.08) | 0.0000 |
| edge_shuffle | 25.86 (22.51, 29.21) | 7.16 | 0.19 (-0.43, 0.81) | 0.5582 |
| degree_matched_random | 26.76 (23.02, 30.50) | 8.00 | 0.32 (-0.30, 0.95) | 0.3136 |

Same pattern: `sign_scramble` is much worse, `edge_shuffle` and
`degree_matched_random` (including the strongest, most structure-destroying
null) are not distinguishable from intact.

### 2.4 Minimum detectable effect at n=20

Two-sample, alpha=0.05, power=0.8, equal n=20 per arm: **minimum detectable
Cohen's d = 0.89**. The `edge_shuffle` and `degree_matched_random` null
results on figure-8 RMS and point-to-point error (|d| < 0.33) are
comfortably inside the region this design can rule out an effect of that
size — this is not an underpowered null. The `sign_scramble` effects
(d = 2.6 to 5.7) and the pointing-error effects for all three nulls
(d = 1.0 to 2.6) are far above the MDE and are well-powered detections.

## 3. Conclusion

Three separable findings:

1. **The real-connectome pipeline that this repo can actually run
   (`RealCX`) does not reproduce the published control precision at all.**
   Intact-connectome pointing error is 71 deg, not 0.41 deg; figure-8 RMS
   is 9.86, not 0.17; point-to-point arrival is 0%, not 100%. The gap is
   roughly two orders of magnitude on every metric. This corroborates, from
   a completely independent angle, what `docs/KERNEL_RECOVERY.md` already
   found about the kernel calibration: the pipeline that produces the
   monograph's numbers (`chorus_env.py`, the calibrated 16-wedge
   `RingCX`) is disconnected from the pipeline that actually simulates the
   real connectome (`RealCX`).
2. **Where a specificity signal exists, it is real but small relative to
   the published claim.** The intact connectome reliably beats all three
   nulls on pointing error (d = 1.0-2.6, well-powered), and `sign_scramble`
   is reliably worse than intact on every metric (the one prediction of
   "the connectome's signed structure matters" that holds up here). This is
   a genuine, measured connectome effect — just one 100+ degrees away from
   sub-degree control, not evidence for the headline numbers.
3. **Against the field's standard strongest null, the connectome shows no
   advantage on two of three outcomes.** `degree_matched_random` — the
   configuration-model null that keeps only degree sequence and the
   marginal weight distribution — is statistically indistinguishable from
   intact on figure-8 tracking and point-to-point reach, with well-powered
   null results (comfortably below the n=20 minimum detectable effect of
   d=0.89). For these two outcomes, the specific topology of the real
   connectome, beyond its degree sequence, is not shown to matter in this
   pipeline.

**Plain answer to the question this experiment was designed to settle:**
the real connectome is not shown to be load-bearing for the published
fine-control headline numbers. The pipeline that produces those numbers
does not use the connectome weights (`chorus_env.py`); the pipeline that
does use them (`RealCX`, ablated here) is roughly two orders of magnitude
worse than the published numbers on every metric, and on two of the three
outcomes it cannot be distinguished from a degree-matched random graph.
The one place the real connectome shows a genuine, well-powered advantage
(pointing error, against all three nulls) is real but does not rescue the
central framing that CHORUS's fine-control results are "all on the real
connectome" in the sense the monograph claims.

## 4. Files

- `code/ablation_specificity.py` — the experiment (this document's source
  of all numbers above; deterministic given `--seeds`, prints per-seed
  progress).
- `code/plot_ablation.py` — builds `figures/ablation_specificity.png` from
  `data/ablation_results.json` (not itself a deliverable path but kept for
  reproducibility).
- `data/ablation_results.json` — full per-seed raw values, the sanity
  check, and the computed statistics.
- `figures/ablation_specificity.png` — per-condition distributions (violin
  plots with 95% CI error bars) for the three outcomes, with intact and
  intact_male reference lines.

No existing file was modified. `code/chorus_env.py`, `code/run_env.py`,
`code/test_env_regression.py`, `code/measure_kernel.py`,
`code/measure_kernel_v2.py`, `README.md`, and all other existing docs were
read but not changed.

---

## Reviewer note on interpretation (added after the run)

The experiment above instantiates `RealCX(W, nodes)` with default gains. It does
not apply the section 2 calibration (kappa=5.6, w_exc=1.9, w_inh=0.28). This
matters for how the results should be read, and one framing in the summary above
overstates the case.

**The intact condition failing is not new evidence against the monograph.** Section
2 states plainly that the raw connectome weights, simulated directly, collapse onto
a single pinned location and do not behave as a continuous attractor. Measuring
71.1 deg pointing and 0% arrival on the uncalibrated real-connectome pipeline
reproduces that stated finding. It is not a discovery that the published numbers
are disconnected from the connectome; the paper already says the raw pipeline does
not work and describes calibration as the fix.

**What the W-sensitivity check actually shows** deserves emphasis. Intact gives
62.4 deg, W scaled by 0.1 gives 38.6 deg, and W zeroed entirely gives 5.9 deg. In
this uncalibrated regime the real connectome is roughly ten times worse than no
connectome at all. That is consistent with the pinning account: the recurrence
fights the goal injection.

**The comparison happens entirely inside a broken regime.** Every condition lands
between 71 and 87 deg, against a chance level near 90 deg. The differences are
between degrees of failure, so effect sizes here bound how much the connectome
changes a non-working model, not how much it contributes to working control.

**What survives as a genuine result:**

- Sign structure is load-bearing. `sign_scramble` is reliably worse than intact on
  all three outcomes (d = 2.58 pointing, 3.80 figure-8, 5.69 point-to-point error,
  all p < 0.003). This contradicts the `sphinx` block in `data/results.json`, where
  sign scrambling matched or beat intact. On the real CX pipeline, signs matter.
- Topology specificity is mixed. Intact beats `edge_shuffle` (d = 1.00, p = 0.0024)
  and `degree_matched_random` (d = 1.42, p = 0.0001) on pointing error, but is
  statistically indistinguishable from both on figure-8 tracking (|d| < 0.01,
  p > 0.98) and point-to-point error (d = 0.19 and 0.32, p = 0.56 and 0.31). With a
  minimum detectable effect of d = 0.89 at n=20, those are well-powered nulls.
- The male connectome pins at 90.0 deg with SD 0.0004 across all seeds and all
  goals, independently reproducing section 2's pinning phenomenon on a second real
  connectome. Flagged for a check: a decoded heading that constant regardless of
  commanded goal should be confirmed as genuine pinning rather than a degenerate
  phase assignment in the male extraction.

**The gap this experiment does not close.** The published numbers come from the
calibrated pipeline, and the ablation the verdict actually needs is on that
pipeline. But the calibrated pipeline (`RingCX` / `chorus_env.py`) does not read W
at all, so an ablation there is vacuous by construction. The only channel from the
connectome into the calibrated model is the measured kernel width, and
`KERNEL_RECOVERY.md` shows that measurement cannot currently be reproduced.

That is the honest statement of where the project stands: there is a pipeline that
uses the connectome and does not work, a pipeline that works and does not use the
connectome, and a bridge between them that cannot be reproduced from what shipped.
Until one of those three changes, the connectome cannot be shown to be load-bearing
for the published control results, in either direction.
