# The Neural Model-Extraction Attack Surface: An In-Silico Neurosecurity Framework

Aayush Gandhi. Threat-model and framework document. No em dashes.

This document reframes the Neuro-AI program as a cognitive-security problem. It defines a formal
threat model for **neural model extraction** (stealing enough of a brain's weight-function to
reconstruct, forecast, or steer its behavior), states the defensive duals (a distribution-free
neuroprivacy floor, a crown-jewel ranking, and a calibrated extraction detector), and shows why the
flyvis connectome-constrained ensemble plus a second connectome-constrained RNN population make the
attack surface measurable purely in silico, on real and near-real connectomes, at power the human
datasets cannot reach.

---

## 0. The security gap this fills

Neurosecurity was named in 2009 for the security and privacy of implanted neural devices
[Denning2009], and the ethics literature has since defined neurorights: mental privacy, personal
identity, and agency as the assets at risk [Yuste2017, Ienca2017]. That work is largely normative.
The device-attack literature (brainjacking; consumer brain-data leaks) is largely qualitative
[Pycroft2016, Ienca2018]. What is missing, and what a recent push for a mathematical framework for the
security of cognition calls for, is a **quantitative attack-surface model**: given a measured amount of
neural access, how much of an individual's behavior can an adversary actually reconstruct, and what is
the provable access threshold below which they cannot?

Machine-learning security already has this shape. Model-extraction attacks steal a model's function
through query access [Tramer2016]; membership-inference attacks quantify what training data leaks from a
released model [Shokri2017]. A brain, captured or eavesdropped, is a model. This program has already
built the three instruments the neuro version needs: wiring-not-weights (what part of a network carries
its individual function), cultist (a neural signature that predicts behavior/belief and thus bounds
manipulability), and neurobridge (calibrated forecasting of behavior from neural signal with honest
abstention). This document assembles them into the missing quantitative neurosecurity framework and
tests it on a real connectome.

## 1. The asset: what an attacker is trying to steal

A population of individuals shares one wiring diagram (connectome) `C` but differs in weights.
Individual `i` has weight-function `W_i`. A behavioral readout `g` maps a member's stimulus-evoked
activity to a behavioral output (flyvis: optic-flow/motion estimate; RNN: task decision). This is
exactly a connectome-constrained ensemble: same `C`, many valid weight solutions `{W_i}`
(flyvis pretrained ensemble; Beiran teacher-student ensemble).

The program's prior results fix what the asset is. The wiring `C` alone is cheap and non-identifying of
function [Beiran2025]; on real connectomes it even fingerprints individuals (ABIDE, identification acc
0.97), so an attacker gets the wiring essentially for free and it does not let them clone behavior. The
exact weights are degenerate [Prinz2004] and need not be stolen precisely. The asset an attacker must
actually acquire, and a defender must actually protect, is **the functional-equivalence class of the
weight-function with respect to behavior**. wiring-not-weights established this dissociation
synthetically (Cohen d = 33); this framework asks whether it holds as a *security* property on a real
connectome with a *behavioral* endpoint.

## 2. The adversary and the access channel

The adversary observes the brain through a lossy access channel `K_f` at fidelity `f in [0,1]`, where
`f` indexes a real leakage budget. The wiring `C` is known for free. The weight-function is observed at
fidelity `f` through a principled, budget-linked degradation family:

- **bit-depth quantization** of synaptic weights, tied directly to bits/synapse (Bartol 4.7 bits/synapse
  is the empirical anchor for `f = full`) so `f` maps to leaked bits;
- **neuron/synapse subsampling** (the adversary eavesdrops on only a fraction of the network and infers
  the rest from the connectome prior);
- **additive observation noise** at a controlled SNR (imperfect measurement of each parameter, the
  regime real recordings live in).

`f = 0` is wiring-only (the free structural leak); `f = 1` is a lossless capture.

## 3. Three adversary capabilities (the attack surface)

### 3.1 Extraction / cloning

The adversary reconstructs a clone `W_i^f = K_f(W_i)` and runs it. Behavioral agreement with the source
on held-out stimuli defines the **attack-surface curve**:

```
A(f) = mean_i  agreement( g(response(W_i^f, S_test)),  g(response(W_i, S_test)) )
```

The **extraction threshold** `f* = min { f : A(f) >= tau }` is the minimal access at which cloning
succeeds within tolerance `tau`. Converting `f*` through the bits/synapse anchor gives a **leakage
bit-budget to clone behavior**: the amount of neural access that constitutes a successful theft of the
person's behavioral function, as opposed to the (smaller) access needed to merely fingerprint them.

**Prediction (H1).** `A(0)` is at chance (wiring alone cannot clone behavior), `A(1) = 1`, and `f*` is
strictly interior and substantial (behavior is distributed, high-dimensional; stealing a few top weights
does not suffice), replicating the wiring-not-weights sufficiency curve (alpha* ~ 0.8) as a security
property, on a real connectome, with a behavioral endpoint.

### 3.2 Forecasting from an eavesdropped subset

The weaker, more realistic adversary records only a subset of neurons and forecasts held-out behavior
(the neurobridge idiom, applied to an individual). Beiran and Litwin-Kumar (Nat Neurosci 2025) show a
connectome is often insufficient to fix dynamics but recording a subset of neurons collapses the
degeneracy, and the theory prioritizes which recordings are most efficient. Cast as security: forecast
accuracy as a function of the number and identity of recorded neurons is the eavesdropping attack
surface, and the efficiency ranking is the attacker's target list. The brain-beats-behavior contrast
(neural-subset forecast vs a behavior-only baseline) measures the marginal leakage that neural access
adds over merely watching behavior.

### 3.3 Bounded steering (proof-of-risk only)

The cultist idiom: how much access is needed to shift behavior by a target margin. Reported strictly as
a **risk envelope** (a bound on manipulability), never as a working optimizer, mirroring the cultist
bright line. This bounds the agency-violation risk that the neurorights framework names [Yuste2017].

## 4. The defensive duals

Each attack axis has a defensive counterpart, which is the deliverable that matters for policy.

- **Neuroprivacy floor `f_min`.** The leakage budget below which reconstruction/forecast is provably at
  chance, certified distribution-free with split-conformal coverage on held-out members. A capture or
  recording that leaks below `f_min` is safe by construction in this system. This is the quantitative
  form of the mental-privacy right.
- **Crown-jewel map.** The behavioral-leakage ranking of neurons/populations: what a defender hardens
  first and what an attacker targets first. It turns "protect the brain" into a prioritized list.
- **Calibrated extraction detector.** A conformal detector (lift the neurobridge layer) that flags
  extraction attempts and abstains under distribution shift rather than emitting a false-precise verdict.

## 5. Substrates and why now

- **flyvis** (Lappalainen et al., Nature 2024; doi 10.1038/s41586-024-07939-3): a connectome-constrained
  deep mechanistic network of the Drosophila visual system, shipped as a pretrained ensemble of models
  that share the identical measured connectome but hold different trained weights, each reproducing
  neural responses and each producing a behavioral (optic-flow) readout. A real biological connectome
  with a real behavioral endpoint and a ready-made weight-degenerate population.
- **Connectome-constrained teacher-student RNN ensemble** (Beiran and Litwin-Kumar, Nat Neurosci 2025;
  doi 10.1038/s41593-025-02080-4): a second, independent substrate (different connectivity type, different
  behavior) built here so no conclusion rests on one system.
- **NSD N=8** (Allen et al. 2022; doi 10.1038/s41593-021-00962-x): the real-but-underpowered human anchor,
  already local, used in an SNR sweep to ask whether current fMRI leakage sits above or below the
  neuroprivacy floor, and whether the digital-brain N=8 null (0/25 ROIs) is power-limited or principled.

## 6. Bright line and dual-use posture

This is an in-silico measurement instrument. It uses connectome-constrained model ensembles and public
human data. It models population-level and per-member leakage on simulated brains. It does **not** target,
profile, or optimize against any real named individual, builds **no** deployable extraction or
manipulation system, and the steering axis is reported only as a risk bound. The output is a quantified
attack surface and a defensive floor, handed to neuroprivacy and neurorights research [Yuste2017,
Ienca2017, Ienca2018]. The constitution question (whether a behavioral clone is the same subject in the
first-person sense) is explicitly bracketed; this framework resolves the reconstruction/leakage question,
which is the one that can be operationalized and measured.

## 7. What each outcome means

- A substantial interior `f*` on both substrates: the weight-function is the crown jewel, cloning behavior
  requires stealing far more than the wiring, at a quantified bit-budget, and a real neuroprivacy floor
  exists and can be certified. Wiring-level protection is provably insufficient.
- `A(0)` already high (wiring suffices to clone behavior): the strong attacker wins from structure alone,
  the neuroprivacy floor is near zero, and the wiring-not-weights dissociation does not transfer. This
  would be the most consequential negative result in the program and would sharply raise the stakes of
  connectome release.
- The N=8 SNR sweep places current human fMRI relative to `f_min` and tells us whether "encoding is not
  identity" is a principle or a power problem.

## 8. References

See `paper/refs.bib` (DOIs verified). Neurosecurity/neurorights: Denning 2009, Yuste 2017, Ienca 2017,
Pycroft 2016, Ienca 2018. ML-security analogs: Tramer 2016 (model extraction), Shokri 2017 (membership
inference). Substrates and identity theory: Lappalainen 2024, Beiran and Litwin-Kumar 2025, Prinz 2004,
Finn 2015, Bartol 2015, Sandberg 2008. Behavioral-forecasting instruments: Stallen 2021, Genevsky 2017,
Knutson and Genevsky 2018, Falk 2010, Kaplan 2016. Uncertainty: Angelopoulos and Bates 2023.
