# Council Review, 2026-09-10

Adversarial internal review of the CHORUS monograph (`CHORUS_fine_control.md`,
byte-identical to `PAPER.md`) together with its artifacts, and of the MaleCNS v1.0
replication work added in the `malecns-replication` branch. Mode: manuscript plus
artifact, with numbers recomputed from `data/results.json` rather than read from
the prose.

## Verdict: MAJOR REVISION

Not a rejection. The data provenance is clean, the engineering is real, the MaleCNS
extraction holds up, and the central negative finding of section 2 (structure does
not determine dynamics) is honest and correct. But the central positive framing,
that these are control results about the real connectome, is not currently
supported by the artifacts, and the project's own unreported ablation points the
other way.

## What should be preserved

- Section 2 is the paper. The finding that raw connectome weights pin the bump, and
  that the wiring supplies the motif but not the computation, is stated against the
  author's own interest and is the most valuable thing here.
- Section 13's spiking validation is exemplary. Dead reckoning failed at 98.5 deg
  pointing, and rather than tuning it away the study identified the biological
  anchor real flies use and reported that the rescue was required.
- Sections 10 and 11 are unusually candid for a control paper. The dual-use section
  names the biological-drone capability plainly.
- The MaleCNS extraction reproduces the textbook circuit signs independently on a
  different animal, sex and reconstruction pipeline (EPG 46/46 cholinergic, Delta7
  42/42 glutamatergic, PFL3 24/24 cholinergic). Section 1's claim was n=1 and is
  now replicated.

## The load-bearing finding: the connectome is not shown to be load-bearing

Three independent lines converge.

**1. An unreported specificity ablation, already public in this repository.**
`data/results.json` contains a `sphinx` block that appears nowhere in the
manuscript. Searching both `CHORUS_fine_control.md` and `PAPER.md` for sphinx,
scramble, shuffle, random_graph or ablat returns zero hits.

| Condition | frac_reached | Cohen's d vs intact |
|---|---|---|
| intact connectome | 0.8875 +/- 0.0644 | reference |
| shuffle | 0.8375 +/- 0.0735 | +0.72 |
| sign_scramble | 0.9083 +/- 0.0400 | -0.39 |
| random_graph | 0.8208 +/- 0.0576 | +1.09 |

Scrambling every synaptic sign performed better than the intact connectome. All
four standard deviations overlap.

The fair defense is that this block almost certainly comes from the earlier
reservoir-based prototype rather than the real-connectome CX study:
`paradigm_agg/Centralized Conductor/frac_reached` is 0.8875, identical to
`sphinx/intact`, and `CHORUS_bci_realfly.md` describes that earlier work as using a
random reservoir brain and a real odor gradient. The defense does not fully hold,
because this is the only specificity test anywhere in the project and the
real-connectome study ran none.

**2. A working reimplementation needs no connectome.** `code/chorus_env.py`
reproduces the published numbers (0.386 deg pointing against a published 0.41,
10.16 deg at eight electrodes against a published ~10) while constructing the ring
from a canonical 16-wedge tiling with fitted gains. It loads the weight matrix and
never uses it.

**3. The calibration may be circular.** See `KERNEL_RECOVERY.md`. The published
"measured ~24 deg kernel" is recovered exactly as 1/sqrt(5.6), the circular-SD of
the hardcoded calibrated kappa. Independent measurement of the same connectome
gives kappa 3.49, i.e. 30.7 deg under the same convention. If the measurement and
the calibration are the same number, the connectome did not independently constrain
the model. Stated as a hypothesis consistent with the arithmetic, not as
established fact.

Each line has an individual defense. Together they describe one situation: the
calibrated ring does the work, and the connectome supplies a kernel width and
population counts.

## Gate ladder

| Gate | Result | Evidence |
|---|---|---|
| 0 Provenance | PASS | Public FlyWire v783 and CC-BY MaleCNS v1.0, no restricted data |
| 1 Variance | FAIL | No seed sweep anywhere in the real-connectome study; every headline in sections 4-8 is a single run with no CI |
| 2 Spec robustness | FAIL | Electrode sweep non-monotone: n=24 gives 0.2 deg, n=32 gives 2.5 deg |
| M Multiverse | FAIL | Kernel width spans 24 / 30.7 / 36.7 / 45.6 deg across estimator choices |
| 3 Specificity | FAIL | See load-bearing finding |
| 4 Confound control | PASS | Density control run properly and refuted its own hypothesis |
| 5 Mechanism | FAIL | No necessity test on the real-connectome results |
| 6 Claim calibration | FAIL | Section 0's "all on the real connectome" against section 2's own finding |
| 7 External validity | FAIL | n=1 connectome for all published claims; MaleCNS is the fix, in progress |
| 8 Measurement validity | FAIL | Kernel estimator does not reproduce its own reference, 53% discrepancy |
| 9 Reproducibility | FAIL | No seeds or configs; the code producing the load-bearing 24 deg is absent |
| 10 Ethics and safety | PASS | Section 11 is genuinely good, with a standing condition below |
| 11 Analytic integrity | FAIL | No preregistration; the compass-calibration rule is exploratory presented as principle |
| F Figures | evidence-blocked | Twelve figures present, not inspected in this pass |
| T Theory | N/A | No formal claims |

## Error analysis

- **0.41 deg pointing.** Dominant risk Type I. Single run, no CI. The number
  reproduces from a connectome-free ring, so it bounds nothing about
  connectome-grounded control.
- **Error approximately 90/n.** Dominant risk: a law fitted to a non-monotone
  single-seed sweep. Residuals against 90/n are exactly 0.00 at n=2, 3 and 4, which
  means those points are quantization arithmetic rather than measurements. Then
  n=24 has residual -3.55 and n=32 is worse than n=24. The earlier
  `bci_electrode_sweep` is worse: n=4 gives 29.6 deg, n=6 gives 42.2 deg, n=8 gives
  21.2 deg, n=12 gives 26.8 deg.
- **Male kernel wider than female.** Method variance (24 to 36.7 deg, 53%) exceeds
  the effect (36.7 to 45.6 deg, 24%). Uninterpretable until the estimator
  reproduces its reference.
- **The sphinx ablation itself.** Underpowered at roughly n=8: minimum detectable
  effect is about d = 1.4. But an underpowered null does not rescue a wrong-signed
  point estimate.

## Severity-ranked findings

1. **Blocker.** The connectome is not demonstrated to be load-bearing. Fix: run the
   ablation ladder (intact, sign-scrambled, edge-shuffled, degree-matched random) on
   the real-connectome pipeline, 20 seeds, report d and CI, publish whichever way it
   falls.
2. **Blocker.** Section 0 overclaims relative to section 2. Fix: restate as "on a
   ring attractor whose kernel width and population structure are derived from the
   real connectome". Costs nothing and is defensible.
3. **Blocker.** No seed variance on any headline. Fix: 20-seed sweep across sections
   4-8.
4. **Major.** The 24 deg kernel is not reproducible and its code is absent. See
   `KERNEL_RECOVERY.md`.
5. **Major.** `chorus_env.py` cannot serve its stated purpose until it takes a
   per-connectome measured kernel. Blocked on finding 4.
6. **Major.** The 90/n law is fitted to a non-monotone single-seed sweep with three
   points exact by construction.
7. **Minor.** The original FlyWire extraction defaulted unresolved presynaptic
   neurotransmitters to excitatory rather than dropping them. Undocumented in the
   methods; belongs there.
8. **Standing, ethics.** MaleCNS adds a traced brain-to-motor pathway in one animal,
   which shifts the dual-use profile. `RESPONSIBLE_DISCLOSURE.md` should be revised
   before the VNC extension, not after.

## What would change the verdict

Run the specificity ablation on the real-connectome pipeline: intact versus
sign-scrambled versus degree-matched random, 20 seeds, pointing error and figure-8
cross-track RMS as outcomes.

If intact beats the nulls with d greater than 0.5 and non-overlapping CIs, findings
1 and 2 dissolve and the verdict moves to ACCEPT once the seed sweeps land.

If the nulls match intact, which the sphinx block and the connectome-free
environment both predict, then the honest paper is a different and arguably better
one: what the fly connectome does and does not determine for control, with the
negative ablation as the headline and the control results as the demonstration that
motif-level structure plus calibrated gains suffices. That paper survives review.
The current framing does not.

## On program direction, given MaleCNS

The release does not rescue the specificity problem, it makes it answerable. Two
connectomes allow the question of whether calibrated gains transfer across
individuals, which n=1 could not pose. But run in the current architecture it would
return perfect transfer as a code artifact.

The strongest move the release enables is the descending-neuron to VNC to motor
extension. That edge list is already extracted in `data/malecns_cx/dn_vnc_edges.csv`.
Below the neck there is no ring-attractor calibration standing between the
connectome and the behaviour, so the wiring is load-bearing by construction. If a
PFL3 left-right bias produces a turn through real VNC circuitry, the connectome did
that, and it cannot be attributed to hand-set gains. That is the version of this
project where connectome-grounded is a claim rather than a framing.
