# Kernel recovery — can the published ~24 deg half-width be reproduced?

## 0. Outcome, stated up front

**NOT REPRODUCED.** The ~24 deg von Mises recurrent-kernel half-width
reported in CHORUS_fine_control.md section 2 (and CHORUS_fine_control.md section
2) cannot be reproduced from the code and data that survive in this repo.
Every principled combination of half-width definition, disynaptic loop
composition, and fit configuration tested here, run on the real FlyWire v783
kernel that code/measure_kernel.py already measures, lands in **30.0-37.4
deg with an inhibitory surround** (see section 4). One partial, genuinely
useful finding survives the forensics (section 3): the "half-width"
convention almost certainly used in the original study is the circular
standard-deviation approximation sigma = 1/sqrt(kappa) in degrees, not the
exact arccos-based HWHM that measure_kernel.py reports. That convention
explains part of the gap but not all of it. The remainder is attributable to
a phase-recovery method (anatomical position around the protocerebral
bridge) whose code and underlying data column no longer exist in this repo.
The male-vs-female connectome comparison is blocked: the method-vs-method
discrepancy (30.0-37.4 deg by any defensible definition, vs. published 24
deg) is not smaller than the reported sex difference (36.7 vs 45.6 deg,
24%), so no comparison built on the current kernel estimator is trustworthy
against the published number.

## 1. Forensics — what survives, what does not

Read in full: CHORUS_fine_control.md sections 1-2, CHORUS_fine_control.md
(identical section 1-2 text), CHORUS_research_study.md,
CHORUS_swarm_findings.md, DENSITY_CONTROL.md, and
code/cx_real_dynamics.py, code/cx_ring.py, code/legacy/cx_connectome.py,
code/cx_actuation.py, code/legacy/chorus_sim.py, code/legacy/chorus_controllers.py,
code/chorus_env.py, data/results.json. The working tree used for this forensics pass had no `.git`
history to mine (`git log` fails: not a git repository), so there is no
commit trail to a deleted kernel-fitting script either.

**What survives:**

- The prose claim itself (section 2): "a von Mises recurrent kernel of ~24
  deg half-width with a weak inhibitory surround," measured "through the
  real disynaptic loops (EPG->PEG->EPG, EPG->Delta7->EPG, EPG->PEN->EPG)."
- A parenthetical methods note (end of section 2): "spectral EPG phase
  estimates were clumped over only ~318 deg of the circle, leaving coverage
  gaps that themselves pin the bump; the canonical uniform 16-wedge EPG
  tiling with the measured kernel width is the biologically correct
  representation and is used throughout." This says explicitly that spectral
  phase embedding was tried, rejected, and replaced by a uniform tiling for
  everything downstream of the kernel measurement.
- Section 1's phase-profile analysis description: "sorting each family by
  its position around the protocerebral bridge and measuring connection
  strength as a function of angular offset." This implies an anatomical
  position value existed per neuron at the time that analysis was run.
- `code/cx_ring.py`: the calibrated ring attractor, with **kappa=5.6,
  w_exc=1.9, w_inh=0.28 hardcoded** as constructor defaults. Its own
  docstring claims it "uses the 47 real EPG neurons and their
  spectral-embedding phases," which is contradicted by the actual caller.
- `code/chorus_env.py`: the environment that actually builds the ring passes
  `self.phases = wedge_phases(N_WEDGE)` — a uniform 16-point tiling
  (`np.linspace(-pi, pi, 16, endpoint=False)`), **not** 47 real EPG neurons
  and **not** spectral phases. This one line is the strongest surviving
  evidence for the "canonical uniform 16-wedge tiling ... used throughout"
  note above: whatever phase representation the kernel and the downstream
  ring both use, it is this synthetic 16-point tiling, and cx_ring.py's own
  docstring is stale/inaccurate about it.
- `data/results.json`: 14 top-level keys, all from steps 3 onward
  (paradigm_agg, sphinx, gain_sweep, degrade_edge, degrade_noise,
  bci_electrode_sweep, bci_noise, bci_swarm_reach, step3_control_authority
  through step9_spiking_validation). Searched exhaustively for "kappa",
  "kernel", "318", "hwhm", "von_mises", "half_width", "24." — **zero
  matches.** No step1/step2 record survives in this file at all.
- `data/cx_nodes.csv`: columns are exactly `root_id, cell_type,
  side, nt`. **No position, no bridge-column, no glomerulus index, no phase
  column.** The anatomical "position around the protocerebral bridge" that
  section 1's phase-profile analysis used is not recoverable from this file.

**What is genuinely absent:** any script that (a) computes an anatomical
EPG phase from bridge position, (b) fits a von Mises kernel and reports
kappa/half-width, or (c) records the step1/step2 intermediate numbers.
`code/measure_kernel.py`'s own docstring states this plainly and correctly:
"No existing implementation of this measurement was found anywhere in
code/." That statement was verified independently here and holds.

## 2. Candidates tested

### (a) Phase recovery: spectral vs. uniform tiling

The monograph explicitly rejects spectral phase for the working model in
favor of the uniform 16-wedge tiling, and chorus_env.py bears this out in
code. This was tested as far as it can be: measure_kernel.py's spectral
embedding was run (baseline, kappa=3.493) and compared against what a
uniform-tiling-based measurement would require. The blocker: a uniform
16-wedge tiling is a *modeling abstraction* for the ring's state variables,
not an assignment of phases to the 47 individual real EPG neurons the
disynaptic kernel is measured between. To fit a von Mises kernel to
neuron-neuron interaction strengths you need a phase per neuron, and turning
"16 uniform wedges" into "47 real-neuron phases" requires an anatomical
ordering (e.g. bridge position, glomerulus index) that is not present in
cx_nodes.csv. Assigning neurons to wedges by an arbitrary key (root_id order,
alphabetical, etc.) would not be anatomical — it would be exactly the kind
of unjustified free parameter this task forbids, and it was not done.
**Ruled out as untestable, not as false:** the mechanism is plausible and
partially corroborated (chorus_env.py's real behavior contradicts cx_ring.py's
docstring), but the concrete phase values cannot be recovered.

### (b) Half-width definition

Enumerated and computed on the same measured kappa in every case:

| Definition | Formula | kappa=3.493 (measured) | kappa=5.6 (cx_ring.py hardcoded) |
|---|---|---|---|
| Exact HWHM (arccos, measure_kernel.py's own convention) | `arccos(1 + ln(0.5)/kappa)` | 36.7 deg | 28.8 deg |
| Circular-SD approximation | `1/sqrt(kappa)` (rad -> deg) | 30.7 deg | **24.2 deg** |
| Gaussian-equivalent HWHM (small-angle) | `sqrt(2 ln2 / kappa)` (rad -> deg) | 36.1 deg | 28.5 deg |
| Full width at half max / 2 | `2 * HWHM_exact / 2` = HWHM_exact | 36.7 deg | 28.8 deg |

**Finding:** the circular-SD approximation applied to cx_ring.py's hardcoded
kappa=5.6 gives 24.2 deg — matching the published figure almost exactly.
This is a strong, principled candidate for what "half-width" means in the
monograph: not the exact von Mises HWHM, but the standard circular-statistics
concentration-to-spread approximation. It is a real definitional difference,
not a coincidence to three significant figures. **But it does not, by
itself, close the FlyWire discrepancy:** applying the identical sigma-approx
formula to the independently measured kappa (3.493) gives 30.7 deg, not 24
deg. The definition explains why 5.6 reads as "~24 deg" but does not explain
why the measured kappa is 3.493 rather than ~5.6-5.7 (the kappa the sigma
convention needs to land at 22-26 deg is 5.7-9.5, computed directly).
**Partially confirmed, insufficient alone.**

### (c) Which loops, weighting, normalization

All defensible loop subsets (all four EPG->PEG/Delta7/PEN_a/PEN_b->EPG
loops; dropping PEG; dropping Delta7; single-population loops) were fit on
the same spectral phase. Full results in section 4. Only subsets that
include Delta7 give the required inhibitory surround; subsets without Delta7
flip to an excitatory surround and are disqualified regardless of their
kappa. Among the inhibitory-surround subsets, kappa ranges 3.38-3.49 (37.4 to
36.7 deg exact, 31.2 to 30.7 deg sigma) — **no loop-composition choice moves
the number meaningfully, let alone into the 22-26 deg band.** Bin count
(12/24/48) and count-weighting were also varied and change the fit by <2 deg.
**Ruled out:** loop composition and fit mechanics are not the source of the
discrepancy.

Restricting the angular fit range to the near field (≤90 deg or ≤60 deg,
excluding the far surround from the fit) does pull kappa up to 5.1-7.2,
which under the sigma convention gives 25.3 and 21.4 deg — inside or near the
acceptance band. **This was tested and rejected as a candidate**, not
adopted: restricting the range this way flips the fitted surround to
excitatory, because the far-field points that establish the inhibitory
baseline are exactly what gets excluded. That contradicts the monograph's
own explicit "weak inhibitory surround" description and would be curve
fitting to the answer, not a defensible methodological choice. This is
exactly the "well-documented failure" the task asks to report rather than
paper over.

### (d) Sign and normalization convention

The disynaptic kernel `K = sum_m W[EPG,m] @ W[m,EPG]` already carries correct
signs because `W` itself is signed by neurotransmitter (EPG cholinergic =
excitatory, Delta7 glutamatergic = inhibitory), so an EPG->Delta7->EPG path
naturally comes out negative without any extra sign convention. No
normalization (row, degree, or otherwise) is applied to K before fitting in
measure_kernel.py; testing degree-normalized variants was not pursued beyond
this point because sections (b)-(c) already account for the full observed
range and a fit-level rescaling of K would change the fitted amplitude A,
not kappa, and half-width depends on kappa alone in this parameterization —
so it could not explain the gap by construction.

## 3. Why this counts as forensically resolved, not just inconclusive

The single most important surviving fact is the mismatch between
cx_ring.py's docstring ("uses the 47 real EPG neurons and their
spectral-embedding phases") and chorus_env.py's actual behavior (uniform
16-point `wedge_phases`, no spectral embedding, no real per-neuron phases at
all in the working model). Combined with the monograph's own admission that
spectral phase was tried and abandoned for "clumping over only ~318 deg,"
the most likely history is: an early kernel measurement used spectral
phases; it showed a ~24 deg-ish figure at the time by whatever kappa->degree
convention was in use, or a related but different phase-assignment scheme
was used to compute the kernel that was then round-tripped into the
uniform-wedge ring model as a hardcoded kappa=5.6. Either way, the exact
per-neuron phase values behind the ~24 deg number are gone, and cx_nodes.csv
no longer carries the anatomical column (bridge position) that section 1
says was used for a related analysis. Absent that column, the phase
assignment cannot be reconstructed, only bounded.

## 4. Full range of defensible half-widths on real FlyWire data (code/measure_kernel_v2.py)

Every row below is a kappa fit to the real FlyWire disynaptic kernel with an
inhibitory surround (excitatory-surround fits are excluded as
non-defensible per the monograph's own description) and kappa > 0.5
(near-zero-kappa degenerate flat fits, e.g. Delta7-only, PEG+Delta7-only,
are excluded as not real bumps):

| configuration | kappa | HWHM exact (deg) | sigma approx (deg) |
|---|---|---|---|
| all 4 loops, 24 bins (measure_kernel.py baseline) | 3.493 | 36.7 | 30.7 |
| all 4 loops, 12 bins | 3.379 | 37.4 | 31.2 |
| all 4 loops, 48 bins | 3.645 | 35.9 | 30.0 |
| all 4 loops, count-weighted | 3.576 | 36.3 | 30.3 |
| Delta7+PEN_a+PEN_b (drop PEG) | 3.380 | 37.4 | 31.2 |

**Range across every defensible configuration: 30.0 - 37.4 deg.** The
published 24 deg figure sits well outside this range under every
combination of definition and loop composition testable from surviving
code and data. Full run output:

```
=== Acceptance test: reproduce ~24 deg FlyWire kernel half-width ===
N=1051 n_EPG=47

-- Candidate (b): half-width definition, full loop set, spectral phase --
  kappa=3.493 surround=inhibitory
  HWHM (exact, arccos formula, measure_kernel.py convention): 36.7 deg
  circular-SD approx (1/sqrt(kappa), radians->deg):           30.7 deg

-- Candidate (c): which disynaptic loops are summed, spectral phase --
  PEG+Delta7+PEN_a+PEN_b (all 4, as measure_kernel.py) kappa= 3.493 exact=  36.7 sigma=  30.7 surround=inhibitory
  PEG+Delta7 only                               kappa= 0.256 exact=   nan sigma= 113.2 surround=inhibitory
    (excluded from range: kappa=0.256 is a near-flat degenerate fit, not a real bump)
  Delta7+PEN_a+PEN_b (drop PEG)                 kappa= 3.380 exact=  37.4 sigma=  31.2 surround=inhibitory
  PEG+PEN_a+PEN_b (drop Delta7)                 kappa= 3.782 exact=  35.2 sigma=  29.5 surround=excitatory
  PEG only                                      kappa=16.052 exact=  16.9 sigma=  14.3 surround=excitatory
  Delta7 only                                   kappa= 0.000 exact=   nan sigma=5462.6 surround=inhibitory
    (excluded from range: kappa=0.000 is a near-flat degenerate fit, not a real bump)
  PEN_a+PEN_b only                              kappa= 3.659 exact=  35.9 sigma=  30.0 surround=excitatory

-- Candidate (d): fit range / weighting, full loops, spectral phase --
  n_bins=12                      kappa= 3.379 exact=  37.4 sigma=  31.2 surround=inhibitory
  n_bins=48                      kappa= 3.645 exact=  35.9 sigma=  30.0 surround=inhibitory
  count-weighted fit             kappa= 3.576 exact=  36.3 sigma=  30.3 surround=inhibitory
  near-field only, max_deg=90    kappa= 5.128 exact=  30.1 sigma=  25.3 surround=excitatory  <- surround sign flips, not defensible per spec
  near-field only, max_deg=60    kappa= 7.153 exact=  25.4 sigma=  21.4 surround=excitatory  <- surround sign flips, not defensible per spec

-- Trace of the calibrated kappa hardcoded in cx_ring.py (not an independent measurement) --
  cx_ring.py kappa=5.6
  exact HWHM formula:  28.8 deg
  sigma approx formula: 24.2 deg  <- matches the published ~24 deg
  This is consistent with "half-width" in the monograph meaning the circular-SD
  approximation 1/sqrt(kappa), not the exact arccos HWHM measure_kernel.py reports.
  But that convention alone does not rescue the FlyWire measurement: applying the same
  sigma-approx formula to every independently measured kappa above still misses 24 deg,
  because the measured kappa itself (~3.4-3.7) differs from the calibrated 5.6-5.7 needed.
  The anatomical EPG phase (position around the protocerebral bridge, CHORUS_fine_control.md
  section 1) that the original study used is not present in cx_nodes.csv (only root_id,
  cell_type, side, nt survive), so that phase-recovery method cannot be tested here; inventing
  an ordering to fill that gap would be exactly the kind of fudge factor this test forbids.

-- Full range of defensible half-widths tested on real FlyWire kernel data --
  [30.0, 30.3, 30.7, 30.7, 31.2, 31.2, 35.9, 36.3, 36.7, 36.7, 37.4, 37.4]
  range: 30.0 - 37.4 deg

=== VERDICT ===
NOT REPRODUCED. No definition/loop-subset/fit-range combination tested on the real
FlyWire disynaptic kernel, using only what survives in this repo, lands in the
22-26 deg acceptance band with an inhibitory surround. The published 24 deg figure
cannot currently be reproduced from surviving code and data. See KERNEL_RECOVERY.md.
```

## 5. What this means for the female-vs-male comparison

The task that motivated this forensics is blocked, and should stay blocked
until one of two things happens:

1. The original anatomical phase data (bridge position per EPG neuron, or
   whatever produced the 24 deg figure) is recovered from outside this repo
   and cx_nodes.csv is regenerated with it, allowing a like-for-like rerun
   of the original method, or
2. The comparison is explicitly reframed around code/measure_kernel.py's own
   internally-consistent method (spectral phase, all-4-loop disynaptic
   kernel, exact HWHM) as the new reference standard, dropping any claim
   that it reproduces the monograph's 24 deg figure, and stating plainly
   that the calibrated ring model (cx_ring.py kappa=5.6 etc.) and the
   measurement method (measure_kernel.py) are not currently reconciled.

Reporting the male (36.7 to 45.6 deg female-comparison language notwithstanding, note the correct FlyWire number under measure_kernel.py's own method is 36.7 deg, matching DENSITY_CONTROL.md exactly) vs. female difference as a 24% structural finding while a same-method, same-data reproducibility check on the reference number is off by 53% is not currently defensible. This document does not resolve that gap; it documents, with numbers, exactly where the gap comes from and where it doesn't.

## 6. Files

- `code/measure_kernel_v2.py` — the acceptance-test script (new, does not
  modify measure_kernel.py). Run: `python3 measure_kernel_v2.py` from
  `code/` (uses relative paths to `../data/...`, matching
  measure_kernel.py's own convention).
- This document.

No other files were modified. `code/measure_kernel.py`,
`DENSITY_CONTROL.md`, `MALECNS_EXTRACTION.md`,
`code/chorus_env.py`, `code/run_env.py`, `code/test_env_regression.py`, and
`README.md` were read but not changed, per instructions.
