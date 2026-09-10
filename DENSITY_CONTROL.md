# Density control for the MaleCNS vs FlyWire CX comparison

The male CX extraction (docs/MALECNS_EXTRACTION.md) is substantially denser
than the FlyWire v783 reference, on a family-matched neuron set. Before any
claim about the male connectome's dynamics is attributed to sex/individual
differences, this needs to be separated from reconstruction depth
(segmentation, proofreading, the minconf 0.5 synapse-confidence threshold).
This doc builds and reports that control. Code: code/match_density.py
(pruning), code/measure_kernel.py (kernel measurement, new, see section 3).

## 1. The starting gap

|                     | FlyWire | MaleCNS noFC2 (matched families) |
|---|---|---|
| neurons             | 1051    | 1069 |
| edges               | 64,909  | 100,116 |
| total synapses      | 381,592 | 977,282 |
| mean out-degree     | 61.76   | 93.65 |
| synapses/neuron     | 363.08  | 914.20 |
| median edge weight  | 2.0     | 3.0 |

## 2. Two density-matching criteria, and where they land

`code/match_density.py` searches integer minimum-weight thresholds t (keep
an edge if abs(weight) >= t) on the male noFC2 graph and picks the t whose
resulting metric is closest to FlyWire's:

- **(a) edge-count matching** to FlyWire's mean out-degree 61.76: **t = 2**,
  giving 71,495 edges (66.88 edges/neuron, off by 5.1).
- **(b) synapse-count matching** to FlyWire's 363.08 synapses/neuron:
  **t = 36**, giving 390,244 total synapses (365.06/neuron, off by 2.0), but
  only 6,372 edges (5.96 edges/neuron).

**The two criteria do not agree** (t=2 vs t=36, an 18x difference in
threshold). This itself is informative: the male graph's excess density is
not a uniform rescaling of FlyWire's weight distribution. A modest number of
very heavy edges (up to weight 600, vs FlyWire max ~unrecorded but median
2.0) carry a large share of the synapse mass, so synapse-matching requires a
far more aggressive cut than edge-matching. Practically, edge-matching
(t=2) prunes weak/noisy edges and leaves a graph that still resembles the
original topology (71,495 of 100,116 edges survive, 71%); synapse-matching
(t=36) is a near-total sparsification, keeping only 6.4% of edges, and
disproportionately guts specific families (see below) rather than removing a
random 94% of the connectome.

Outputs (schema identical to the existing extraction: W float32 signed NxN,
root_ids int64, node CSV with root_id/cell_type/side/nt):
- `data/malecns_cx/cx_real_male_matched_edges.npz` + `cx_nodes_male_matched_edges.csv` (t=2)
- `data/malecns_cx/cx_real_male_matched_syn.npz` + `cx_nodes_male_matched_syn.csv` (t=36)

## 3. Is the pruning selective?

Per-family edge retention (fraction of that family's presynaptic edges kept)
and the excitatory/inhibitory split, from the actual `match_density.py` run:

**Edge-matched (t=2):** retention ranges from 30% (PFGs) to 95% (LNO1).
Delta7 keeps 86.7% of its edges (6,372/7,352); EPG keeps 76.3% (8,752/11,472).
E/I edge count: full graph 55,709 exc / 44,407 inh (ratio 1.255) ->
edge-matched 35,329 exc / 36,166 inh (ratio 0.977).

**Synapse-matched (t=36):** retention collapses across the board: several
families (ER1, PFNp, PFNm, PFL1/2/3) lose essentially 100% of their edges;
Delta7 keeps 6.7% (493/7,352), EPG keeps 4.7% (536/11,472). E/I count: 1,955
exc / 4,417 inh (ratio 0.443).

**Delta7 vs EPG, the specific question asked.** In both variants Delta7 is
retained at a *higher* rate than EPG (edge-matched: 86.7% vs 76.3%,
gap +10.4 points; synapse-matched: 6.7% vs 4.7%, gap +2.0 points). So
thresholding does **not** preferentially strip Delta7 inhibition relative to
EPG excitation here; if anything the reverse, Delta7's synapses run slightly
heavier on average and survive a rising threshold better. Combined with the
E/I ratio shift (1.255 -> 0.977 -> 0.443, i.e. the surviving graph gets
*more* inhibition-weighted, not less, as the threshold rises), the direction
of bias runs opposite to the naive worry: an aggressive threshold shifts the
male graph toward *more* inhibition-dominated, not toward stripping the
Delta7 surround that the ring attractor depends on. This is a real, testable
finding from this run, not an assumption, and it should be weighed against
the fact that the synapse-matched cut is so aggressive (see section 2) that
its per-family numbers are on very small edge counts and noisier.

## 4. The decisive measurement: the recurrent kernel

**No existing implementation measures this kernel from data anywhere in the
codebase.** `code/cx_ring.py` uses an *already-calibrated* von Mises kernel
(kappa=5.6, hardcoded) as the substrate for the working ring-attractor model;
it does not derive kappa from connectivity. `code/cx_real_dynamics.py`
accepts an `ann_phase` argument but never computes it. So `code/
measure_kernel.py` is a new script, written specifically for this task,
implementing the measurement docs/CHORUS_fine_control.md section 2
describes: the effective EPG->EPG interaction through real disynaptic loops
EPG->PEG->EPG, EPG->Delta7->EPG, EPG->PEN_a->EPG, EPG->PEN_b->EPG (computed
as the matrix product W[EPG,m] @ W[m,EPG] summed over intermediate
populations m), binned by angular offset and fit to a von Mises profile
(A*exp(kappa*(cos(d)-1)) + base) to recover kappa, a half-width-at-half-
maximum in degrees, and the sign of the flat baseline (surround). EPG phase
is not stored in any node CSV, so it is recovered per-connectome by spectral
embedding (first two nontrivial Laplacian eigenvectors) of the symmetrized
disynaptic EPG-EPG graph, independently for each connectome rather than
assumed shared.

This is an honest, independent reimplementation, not a reuse of whatever
produced the paper's own "~24 deg" figure (that exact pipeline is not in the
repo), so the FlyWire number below is not expected to reproduce 24 deg
exactly; it is the same method applied consistently across all five graphs,
which is what the comparison actually needs.

| connectome | N | n_EPG | kappa | half-width (deg) | surround |
|---|---|---|---|---|---|
| FlyWire (reference) | 1051 | 47 | 3.49 | 36.7 | inhibitory |
| Male, full (with FC2) | 1161 | 46 | 2.31 | 45.6 | inhibitory |
| Male, noFC2 | 1069 | 46 | 2.31 | 45.6 | inhibitory |
| Male, edge-matched (t=2) | 1069 | 46 | 2.32 | 45.5 | inhibitory |
| Male, synapse-matched (t=36) | 1069 | 46 | 29.90 | 12.4 | excitatory |

## 5. Reading the table

The male kernel (45.6 deg) is wider than FlyWire's (36.7 deg) both before
and after edge-count density matching, essentially unchanged by that control
(45.6 -> 45.5 deg). This is the clean result of the diagnostic: **if the
male/FlyWire kernel gap were purely a reconstruction-depth artifact,
edge-count density matching should have closed most of it, and it did not.**
The male CX's disynaptic EPG recurrence is measurably broader than
FlyWire's under matched edge density, which argues for treating the width
difference as a real structural feature of the male reconstruction rather
than only a proofreading-depth confound, at least on this measurement.

The synapse-matched variant (12.4 deg, flipped-sign surround) does not
support this reading and should not be used as the density control: at
t=36 it retains only 493 Delta7 edges and 536 EPG edges networkwide (a
6.4% overall edge survival rate), the disynaptic kernel matrix built from
that is extremely sparse, and the spectral phase embedding and von Mises
fit on that few points are unreliable, not a meaningful measurement of
recurrent structure. Its number is reported for completeness (section 4)
because the honesty requirement here is to report what falls out, not to
suppress an inconvenient or noisy result, but it should not be read as
evidence against the edge-matched finding above.

## 6. Which comparison is primary, and why

**Primary: FlyWire vs male noFC2 vs male edge-matched (t=2).** Edge-count
matching prunes only the weakest ~30% of edges, keeps every family
represented with a majority of its original edges, and its kernel measurement
sits on a graph dense enough for the spectral/von-Mises pipeline to be
trustworthy. It also happens to leave the kernel width essentially unchanged
from the raw noFC2 measurement (45.6 vs 45.5 deg), which is itself evidence
that the width difference from FlyWire is not primarily a density artifact.

**Secondary, flagged as unreliable: synapse-matched (t=36).** Retained for
transparency (the disagreement between the two matching criteria is exactly
the kind of thing a reviewer should be able to see), but its extreme
sparsification undermines the kernel measurement's validity and it should
not be used to argue either side of the sex/individual question.

**Bottom line for the downstream calibration experiment**: proceed with the
recurrent-kernel calibration on the male noFC2 (or edge-matched) connectome
and expect a genuinely wider recurrent kernel than FlyWire's, not an
artifact of the male reconstruction being more densely traced. The E/I count
imbalance (55,709 exc / 44,407 inh raw, ratio 1.255, FlyWire 1.144) is
present but does not explain the kernel-width gap either, since thresholding
toward FlyWire's absolute density does not close it. Report both the raw and
edge-matched kernel numbers when the calibration experiment is written up,
and do not report the synapse-matched number as a serious data point beyond
this appendix.
