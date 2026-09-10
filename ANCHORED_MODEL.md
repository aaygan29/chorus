# Anchored model: one global synaptic scalar, no free control parameters

## 0. Pre-declaration (written before any control result was measured)

**Anchor.** EPG compass bump full width at half maximum (FWHM) in vivo,
**90 degrees**, from Kim, Rouault, Druckmann & Jayaraman 2017, *Science*
356:849-853 ("Ring attractor dynamics in the Drosophila central brain"),
DOI 10.1126/science.aal4835. The paper reports the in-vivo FWHM directly
(Fig. 1J, "Bump width measured by full width at half maximum") and uses a
fixed bump width of 90 deg as the physiological constraint for its own
attractor models ("Under constraints of a fixed bump width of 90 deg to
match physiological observations (Fig. 1J)..."). This is the strongest
available direct structural anchor: it is a single-neuron-population
measurement, obtained independently of any control task, and independently
of this codebase's own kernel-recovery problems (KERNEL_RECOVERY.md).
Seelig & Jayaraman 2015 was checked as an alternative source and does not
give a single citable FWHM number in a form usable here; Kim et al. 2017 is
used instead per the task's fallback instructions.

**Acceptance criterion.** Sweep W_syn over a log-spaced grid. For each
value, seed an EPG bump and measure its steady-state FWHM (same operational
definition as Kim et al.: angular distance between the two half-maximum
crossings of the profile, background-subtracted). Select the W_syn whose
mean FWHM (averaged over 6 seeds x 3 seed phases = 18 trials) is closest to
90 deg. Freeze that value. Then, and only then, run control evaluation and
the specificity ablation. **This document was drafted with this section
written first and the rest appended in the order the pipeline actually
ran; the anchor and criterion above were not touched after seeing section 2
or later.**

## 1. Sign assignment

Per-neuron transmitter sign (Dale's law: one sign for a neuron's entire
output), not per-edge sign as the original FlyWire extraction used:

| nt | sign | FlyWire n | MaleCNS (noFC2) n |
|---|---|---|---|
| acetylcholine | excitatory (+1) | 633 | 677 |
| gaba | inhibitory (-1) | 285 | 286 |
| glutamate | inhibitory (-1) | 58 | 54 |
| dopamine | excitatory (+1), defaulted | 33 | 4 |
| serotonin | excitatory (+1), defaulted | 42 | 48 |
| octopamine | excitatory (+1), defaulted | 0 | 0 |

Dopamine/serotonin/octopamine and any unresolved nt are kept
default-to-excitatory, the same convention the original FlyWire signed
extraction used for cell-types without a clear fast-ionotropic transmitter
(MALECNS_EXTRACTION.md section on default-to-excitatory edges). This
affects **75 of 1051 FlyWire neurons (7.1%)** and **52 of 1069 MaleCNS
neurons (4.9%)**. Synapse-count magnitude is taken as `|W|` from the
existing cx_real.npz matrix (confirmed sign-consistent per row: 0 of 1051
FlyWire rows and 0 of 1069 MaleCNS rows mix sign, so `W`'s existing rows
already encode a per-neuron sign; here the sign is re-derived independently
from the `nt` column rather than reused, which is what actually makes this
a Shiu-style single-transmitter-per-neuron model). Anatomical EPG phase is
recovered by the same connectome-derived spectral embedding used elsewhere
in this repo (code/measure_kernel.py's `effective_epg_kernel` +
`spectral_phase`, reused via ablation_specificity.py's approach), not a new
free parameter.

## 2. Model

code/cx_anchored.py, `AnchoredCX`: rate model, `r_{t+1} = r_t + dt/tau *
(-r_t + sigmoid(W_syn * (W_signed^T @ r_t) + ext)) + noise`. **W_syn is the
only free parameter.** tau=20 ms and dt=0.5 ms are reused verbatim from
code/cx_spiking.py's LIF membrane/integration constants (not fit here);
noise=0.02 is reused from code/cx_ring.py's calibrated ring; bias=0 (no
free threshold). None of these three were tuned against this connectome or
against control performance.

## 3. Sweep and freeze (code/anchor_sweep.py)

Grid: 18 log-spaced values, W_syn in [1e-6, 0.05]. 6 seeds x 3 seed phases
(0, 120, 240 deg) = 18 trials per point; bump seeded 300 steps with a
directional cosine drive, then run free for 200 steps, FWHM measured on the
resulting EPG profile.

**FlyWire result:** across the entire six-order-of-magnitude sweep, mean
FWHM never rises above ~28.6 deg and falls to ~12 deg at high W_syn (see
figures/anchor_calibration.png). The closest point to the 90 deg anchor is
**W_syn = 1.627e-4, mean FWHM = 28.6 deg, |diff| = 61.4 deg.** This is not a
close match by any reasonable tolerance; it is simply the best of a set of
uniformly bad matches. **Frozen: W_syn = 1.627e-4.**

**MaleCNS (noFC2) result, independent sweep:** best point **W_syn =
3.074e-4, mean FWHM = 40.7 deg, |diff| = 49.3 deg.** Also not a match.
**Frozen: W_syn = 3.074e-4.**

The two independently-selected W_syn values are within a factor of 1.9 of
each other (3.074e-4 / 1.627e-4 = 1.89), so the two connectomes at least
agree on the right order of magnitude for a single global scalar, even
though neither reaches the target. Full sweep data in
data/anchor_calibration.json and data/anchor_calibration_malecns.json;
sweep curves in figures/anchor_calibration.png and
figures/anchor_calibration_malecns.png.

**Honest statement at this stage:** the calibration itself already fails.
A signed connectome with one global synaptic scale, using this rate-model
formulation and the literature-fixed time constants, cannot produce a bump
as wide as the physiologically measured 90 deg FWHM anywhere in its
dynamic range; the model's connectome-driven bumps are structurally
narrower (roughly 10-40 deg) than the anchor at every scale tested. Per
the pre-declared protocol this does not block proceeding to control
evaluation; it is reported as part of the result, not resolved by picking
a different anchor or a different W_syn after the fact.

## 4. Control evaluation at the frozen W_syn (code/anchored_eval.py)

Before trusting the control numbers, a **W-sensitivity sanity check** was
run at the frozen operating point (same check style as
ablation_specificity.py's `sanity_check`, applied to the anchored model):

| condition | FlyWire pointing error | MaleCNS pointing error |
|---|---|---|
| intact W | 7.22 deg | 7.74 deg |
| W scaled x0.1 | 7.20 deg | 7.75 deg |
| W zeroed | 7.19 deg | 7.75 deg |

**Harness is W-sensitive: FALSE, on both connectomes.** Pointing error is
essentially unchanged whether the connectome is present at full strength,
scaled to 10%, or completely zeroed out. This is the central fact needed to
interpret everything below: at the frozen (anchor-selected) W_syn, the
external goal drive alone accounts for the entire control result. The
recurrent connectome is not doing the work.

Control numbers (20 seeds, goals every 30 deg around the full circle,
figure-8 cross-track RMS):

| pipeline | pointing error (deg) | figure-8 RMS (units) |
|---|---|---|
| published RingCX (uncalibrated, kappa/w_exc/w_inh/w_shift hand-fit) | 0.41 | 0.17 |
| RealCX baseline, uncalibrated (data/ablation_results.json) | 71.1 +/- 7.8 | 9.86 +/- 1.00 |
| **Anchored, FlyWire, frozen W_syn=1.627e-4** | **5.90 +/- 0.87** | **2.30 +/- 0.15** |
| **Anchored, MaleCNS, frozen W_syn=3.074e-4** | **7.92 +/- 1.43** | **2.45 +/- 0.08** |

Taken at face value, the anchored numbers look like a big improvement over
the RealCX baseline (5.9-7.9 deg vs 71 deg) and only modestly worse than the
published RingCX (0.41 deg). **That framing is wrong given the sanity check
above.** The anchored numbers are close to what a bare cosine-tuned external
drive with no connectome at all would produce (W-zeroed pointing error is
7.19-7.75 deg, statistically the same as intact). The apparent "improvement"
over RealCX's uncalibrated 71 deg is a property of the goal-drive gain and
the sigmoid/leak time constants at this particular W_syn, not of the
connectome. See figures/anchored_control.png, panels 1-2.

## 5. Specificity ablation at the anchored operating point

20 seeds, null re-randomized per seed, reusing `REWIRERS` and `stats_block`
from code/ablation_specificity.py without modification.

**FlyWire**, pointing error, intact mean 5.90 deg:

| null | mean (deg) | Cohen's d vs intact | 95% CI | permutation p |
|---|---|---|---|---|
| sign_scramble | 5.87 | -0.038 | [-0.66, 0.58] | 0.909 |
| edge_shuffle | 5.88 | -0.027 | [-0.65, 0.59] | 0.936 |
| degree_matched_random | 5.87 | -0.038 | [-0.66, 0.58] | 0.908 |

**MaleCNS**, pointing error, intact mean 7.92 deg:

| null | mean (deg) | Cohen's d vs intact | 95% CI | permutation p |
|---|---|---|---|---|
| sign_scramble | 7.97 | 0.032 | [-0.59, 0.65] | 0.919 |
| edge_shuffle | 7.87 | -0.033 | [-0.65, 0.59] | 0.917 |
| degree_matched_random | 7.84 | -0.055 | [-0.67, 0.57] | 0.860 |

Figure-8 cross-track RMS gives the same picture on both connectomes: all
|d| < 0.13, all p > 0.67. Minimum detectable effect at n=20 (alpha=0.05,
power=0.8): **d = 0.886.** Every observed |d| above is 5-25x smaller than
this MDE, so these are not "no significant effect, underpowered" results;
they are effects that, if they existed at the size the intact-vs-baseline
comparison would need to matter, would have been comfortably detected.
Sign-scrambling the connectome, shuffling its weight values across the same
edges, and replacing it with a degree-matched configuration-model random
graph are all statistically indistinguishable from the real signed
FlyWire/MaleCNS connectivity, at the one operating point (the anchored
W_syn) where the model's control numbers looked plausible. Full stats in
data/anchored_results.json and data/anchored_results_malecns.json
(`ablation.stats_vs_intact`); figure in figures/anchored_control.png
panel 3.

## 6. Two-connectome comparison

| quantity | FlyWire | MaleCNS (noFC2) |
|---|---|---|
| selected W_syn | 1.627e-4 | 3.074e-4 |
| best-match FWHM | 28.6 deg | 40.7 deg |
| pointing error (frozen W_syn) | 5.90 +/- 0.87 deg | 7.92 +/- 1.43 deg |
| figure-8 RMS | 2.30 +/- 0.15 | 2.45 +/- 0.08 |
| W-sensitive at operating point | No | No |
| max \|d\| across ablations | 0.038 | 0.055 |

The two independently-run anchor sweeps select W_syn values within a factor
of 1.9 of each other, so the anchoring procedure is at least somewhat
reproducible across individuals despite never reaching the target. Control
performance is quantitatively similar (5.9 vs 7.9 deg) and, more important,
**the specificity failure is identical**: on both connectomes, at both
independently-selected operating points, control is completely insensitive
to the connectome's wiring. The cross-individual question this comparison
was built to answer ("does the same anchor select a similar W_syn, and does
control transfer") has a clean answer: yes to both, but "transfer" here
means transfer of a result that does not depend on either connectome in the
first place.

## 7. Conclusion

The connectome plus neurotransmitter-derived signs plus one anchored global
scalar is **not sufficient for steerable heading control** in this
architecture, and the calibration needed to even ask the question already
fails: no W_syn in a six-order-of-magnitude sweep reproduces the ~90 deg
in-vivo EPG bump width on either connectome (best FWHM 28.6/40.7 deg vs
target 90 deg). At the frozen, best-available W_syn, control numbers that
look superficially reasonable (5.9-7.9 deg pointing error, a large
improvement over the uncalibrated RealCX baseline's 71 deg) turn out to be
generated almost entirely by the external goal drive: zeroing the
connectome changes pointing error by less than 0.6 deg on either
connectome, and every specificity-ablation null (sign scramble, edge
shuffle, degree-matched random rewiring) is statistically indistinguishable
from the intact connectome (|d| < 0.06, all p > 0.86, against a minimum
detectable effect of d=0.886 at n=20).

This sharpens, rather than resolves, the finding already on record in
KERNEL_RECOVERY.md and ABLATION_SPECIFICITY.md: the earlier work
showed the *uncalibrated* RealCX pipeline's headline control numbers (0.41
deg, 0.17 units) do not come from the real connectome, because that
pipeline never reads it. This work shows that replacing the four
hand-fitted RingCX parameters with connectome-derived structure plus a
single anchored scalar does not rescue the connectome as the source of
control ability either: the resulting model can be driven to plausible
looking heading control by external input alone, with the connectome
present, scrambled, shuffled, or removed, making no detectable difference.
Under the Shiu et al. parameter discipline applied here, CHORUS's
central-complex connectome, its neurotransmitter signs, and one anchored
global synaptic weight do not, on the evidence in this document, explain
steerable heading control. This directly extends Beiran & Litwin-Kumar
2025's cautionary point about connectome-constrained models: a model can
look right on a headline metric while the connectome does no work at all,
and the way to catch that is the specificity ablation run at the operating
point actually used for the headline metric, not at an arbitrary or
unconnected one.

## Files

- code/cx_anchored.py, code/anchor_sweep.py, code/anchored_eval.py,
  code/plot_anchored_control.py (new; nothing existing modified)
- data/anchor_calibration.json, data/anchor_calibration_malecns.json
- data/anchored_results.json, data/anchored_results_malecns.json
- figures/anchor_calibration.png, figures/anchor_calibration_malecns.png,
  figures/anchored_control.png
