# CHORUS
### Connectome-Held Organism Reconstruction & Unified Steering
**A research study on instantiating and driving a population of embodied in-silico fly brains with AI**

---

## 0. One-paragraph summary

Two recent efforts define the frontier this study builds on. The **Eon** team took the
FlyWire adult *Drosophila* connectome (~125k neurons, ~50M synapses), used machine
learning to infer the biophysical properties the wiring diagram omits (notably
neurotransmitter identity and sign), and coupled the resulting network to a
physics-simulated fly body (NeuroMechFly v2) so that sensation flows in, activity
propagates through the real connectome, and motor commands drive a body in a physics
engine — closing the perception–action loop. **Nectome** represents the maximalist
end-goal: that a preserved connectome could someday be the substrate for a whole-brain
emulation driving a virtual or robotic body — while its sharpest critique is that
*structure is not dynamics*: a wiring diagram alone may not preserve the parameters
(synaptic weights, signs, plasticity state, the "synaptome") that make a specific brain
behave as itself. **CHORUS** turns that gap into a research program. We build two AI
systems — an **Instantiator** that infers the missing dynamics from structure and
returns a *distribution* over plausible brains, and a **Conductor** that reads neural
state and writes stimulation to *drive* those brains toward specified behaviors — and we
stress-test both against falsifiable controls, at the scale of a whole *population* of
embodied flies. The organism is deliberately an insect: rich enough to be scientifically
serious, far below any threshold that raises the ethical and biosecurity stakes of
vertebrate or human emulation.

---

## 1. Motivation & the precise gap

**What the connectome gives you.** A static, near-complete map of *who connects to whom*.
For adult *Drosophila* this now exists at synaptic resolution (FlyWire / hemibrain), plus
the ventral nerve cord (MANC) and the larval connectome.

**What it does not give you.** The connectome is a circuit *diagram* with the component
values erased. To simulate dynamics you must supply, per synapse and per neuron:
- **sign** (excitatory / inhibitory) and **neurotransmitter/receptor** identity,
- **synaptic weight / gain** (a count of synaptic contacts is only a proxy),
- **membrane time constants, thresholds, adaptation**,
- **neuromodulatory context** and any **plasticity / learned state**.

Eon's contribution was to show that ML can fill in a large part of this (e.g. predicting
neurotransmitter identity) well enough to produce *behaviorally meaningful* embodied
dynamics. The open scientific questions — and the reason a "digital sphinx" critique
exists — are: **(a)** how much of true behavior is recoverable from structure alone,
**(b)** whether the inferred parameters are *identifiable* or merely *one* of many
fitting sets, and **(c)** whether a model that reproduces some behaviors is actually
capturing mechanism or exploiting degrees of freedom. CHORUS is designed to answer these
head-on rather than assume them away.

**Why "create AND drive."** The user's target — *an AI that creates and drives a group of
fly brains* — decomposes into exactly the two hard problems above:
1. **Create** = solve the structure→dynamics inverse problem (the Instantiator).
2. **Drive** = solve the closed-loop control problem on a system you can both *read*
   (full neural state) and *write* (arbitrary stimulation) — a regime no wet-lab
   neuroscience can achieve (the Conductor).

---

## 2. Central hypotheses (falsifiable)

- **H1 (Sufficiency of structure).** The connectome plus AI-inferred dynamics is
  sufficient to reproduce a defined battery of fly behaviors above a pre-registered
  fidelity threshold — and *shuffled/foreign connectomes are not*.
- **H2 (Identifiability).** The Instantiator's posterior over dynamical parameters is
  narrow for behavior-critical parameters and wide for behavior-irrelevant ones; where
  it is wide, behavior is correspondingly invariant. (This directly tests the Nectome
  "synaptome" worry: which missing parameters actually matter.)
- **H3 (Controllability).** A Conductor with read+write access can steer an in-silico fly
  to specified behavioral goals it does not spontaneously produce, and can do so across a
  population with shared policy weights.
- **H4 (Degradation tolerance).** Behavioral fidelity degrades gracefully (not
  catastrophically) as we ablate/perturb the connectome to mimic imperfect preservation —
  and the degradation curve identifies *which* structural information is load-bearing.

---

## 3. System architecture (five stages + two AI subsystems)

See the accompanying schematic (`chorus_architecture.png`).

### Stage A — ACQUIRE (connectome substrate)
Use existing public connectomes as the substrate; no wet-lab work in v1.
- **Primary:** FlyWire adult full-brain connectome; hemibrain for cross-check.
- **Motor periphery:** MANC (ventral nerve cord) for descending→motor mapping.
- **Optional:** larval connectome as a smaller, fully-mapped sandbox for method
  development (faster iteration, whole-CNS completeness).
- Represent as a typed graph: nodes = neurons (with cell-type, neurotransmitter priors,
  morphology features), edges = synapses (with contact counts, predicted sign,
  compartment).

### Stage B — INSTANTIATE (the Instantiator = "create")
The AI that turns structure into dynamics and returns a **distribution**, not a point.
- **Backbone:** a **connectome foundation model** — a graph transformer / GNN pretrained
  on the connectome with self-supervised objectives (masked-edge, masked-neurotransmitter,
  cell-type prediction) so it internalizes the statistics of fly wiring.
- **Parameter inference:** **simulation-based inference (SBI)** / amortized posterior
  estimation. The network is a leaky-integrate-and-fire or adaptive-exponential spiking
  model (GPU-batched, e.g. Brian2/Norse/JAX). The Instantiator proposes parameter sets
  (weights, signs, time-constants, neuromodulator gains); we simulate; we compare against
  known constraints (see §4); SBI returns a posterior over parameters.
- **Priors from biology:** neurotransmitter predictions (Eon-style), Dale's law, known
  cell-type electrophysiology, synaptic-count→weight scaling laws.
- **Output:** an ensemble of *N* fully-parameterized brains sampled from the posterior —
  this ensemble *is* the "group of brains" and is the raw material for the population
  study.

### Stage C — EMBODY (Eon / NeuroMechFly loop)
- Couple each instantiated brain to **NeuroMechFly v2** in a MuJoCo physics simulation:
  a morphologically realistic fly body with legs, wings, proprioception, vision, and
  chemosensation.
- **Sensory encoders** map simulated visual/olfactory/mechanosensory input onto the
  correct afferent neurons; **motor decoders** map descending/motor-neuron activity onto
  actuator commands. Closed loop at biological-ish timestep.
- This is the substrate on which *both* "does it behave like a fly?" and "can we drive
  it?" are tested.

### Stage D — CONTROL (the Conductor = "drive")
The AI that *drives* the brains. Because this is in silico, the Conductor has powers no
experimentalist has: **full observability** (every spike) and **full actuation**
(inject current / "optogenetic" activation into any neuron set).
- **Interface:** at each step the Conductor observes (neural state summary + body state +
  task goal) and outputs a **stimulation vector** (which neurons to excite/inhibit and by
  how much) — an in-silico optogenetics actuator.
- **Learning:** deep RL (goal-conditioned; PPO/SAC-class) with a learned **spike-sequence
  world model** for sample efficiency; optionally **language-/goal-conditioned** so a
  natural-language or symbolic target ("walk left", "seek odor", "freeze") maps to a
  control policy — this is the NLP hook.
- **Two control regimes to compare:**
  1. *Naturalistic drive* — provide only sensory stimuli (like a real experiment); test
     whether goals are reachable through the front door.
  2. *Direct drive* — inject activity into internal circuits; measure the *minimal*
     intervention that reliably produces a target behavior (a controllability /
     "neural-lever" map).

### Stage E — POPULATION (the "group of brains")
- Instantiate *N* brains (posterior samples ± individual-variation noise), embody each,
  and run them **in parallel, GPU-batched**.
- **Shared-policy control:** one Conductor drives many bodies (fleet/robotics framing).
- **Multi-agent behavior:** put multiple embodied flies in a shared arena → collective
  behavior, chemotaxis-to-shared-source, simple interaction — a genuinely new object of
  study (a *simulated population* of connectome-derived agents).
- **Individual variability:** because each brain is a different posterior draw, the
  population lets us ask how much behavioral individuality the connectome permits.

---

## 4. Validation — the "digital sphinx" gauntlet (Stage ④)

A model that reproduces a behavior has not earned trust until it survives controls that a
*wrong* model would fail. Pre-register all thresholds.

**Negative controls (must FAIL to reproduce fly behavior):**
- **Edge-shuffled connectome** (degree-preserving rewiring).
- **Foreign connectome** (*C. elegans* / random scale-free graph of matched size).
- **Sign-scrambled** dynamics. If these reproduce the target behaviors, the behavior is
  coming from the body/task, not the brain → the result is an artifact.

**Positive / fidelity benchmarks (should SUCCEED):**
- **Neural predictivity:** correlate model neuron/population activity against published
  functional recordings for identified cell types (e.g. visual-motion, central-complex
  heading, olfactory) — held out from training.
- **Behavioral fidelity:** compare simulated behavior statistics (walking gait,
  optomotor turning, odor tracking, phototaxis) to published fly ethograms.
- **Perturbation congruence:** in-silico "silencing" of a cell type should reproduce the
  behavioral deficit reported for the analogous genetic silencing in vivo.

**Identifiability & degradation (tests H2, H4 — the Nectome questions):**
- **Posterior-width analysis:** which parameters are pinned by behavior, which are free?
- **Connectome-degradation stress test:** progressively remove edges / add noise / drop
  weak synapses to emulate imperfect preservation; plot fidelity vs. degradation. The
  knee of that curve is a quantitative answer to *"how good does a scan have to be?"* —
  a direct, publishable contribution to the preservation-vs-emulation debate.

---

## 5. Metrics

| Question | Metric |
|---|---|
| Does structure→dynamics work? | Behavioral-fidelity score vs. shuffled-connectome baseline (effect size, pre-registered threshold) |
| Are the dynamics real? | Neural-predictivity R² on held-out cell types |
| Are parameters identifiable? | Posterior entropy per parameter; behavior variance across posterior draws |
| Can we drive it? | Task success rate (naturalistic vs. direct); minimal-intervention size for target behavior |
| Does it scale to a population? | Throughput (flies·sec on GPU); shared-policy transfer success; collective-behavior emergence |
| How fragile to preservation quality? | Fidelity-vs-degradation curve; identified load-bearing structures |

---

## 6. Phased plan & compute

- **Phase 0 (larva sandbox, ~months):** full pipeline on the smaller larval connectome;
  de-risk SBI + embodiment + control on a completely-mapped CNS.
- **Phase 1 (adult single brain):** reproduce and extend an Eon-style embodied loop;
  run the full validation gauntlet on one instantiated brain.
- **Phase 2 (the Conductor):** train read+write closed-loop control; build the
  controllability map; add the NLP/goal-conditioning layer.
- **Phase 3 (population):** N-brain posterior ensemble, batched embodiment, shared-policy
  and multi-agent studies.
- **Compute:** GPU-heavy (spiking simulation + RL + SBI). Batched JAX/Norse spiking
  networks on multi-GPU; RL rollouts parallelized across the fly population. Estimate and
  reserve remote GPU compute before Phase 2.

---

## 7. Deliverables

1. **Instantiator** — open model + posterior samples of parameterized fly brains.
2. **Conductor** — trained closed-loop controller + the controllability/"neural-lever" map.
3. **CHORUS-Bench** — the validation gauntlet (controls, neural-predictivity,
   behavioral-fidelity, degradation) as a reusable benchmark others can run.
4. **The degradation curve** — a quantitative statement of how much connectome fidelity a
   faithful emulation requires (the concrete contribution to the Nectome debate).
5. **Population dataset** — trajectories/neural data from N embodied flies for
   downstream analysis.

---

## 8. Safety, ethics, biosecurity, and the metacognition angle (Stage ⑤)

This is not boilerplate; it is a design constraint.

- **Scope discipline / no uplift.** The organism is fixed at *insect*. CHORUS explicitly
  does **not** pursue vertebrate or human whole-brain emulation, and does not develop
  methods whose primary value is scaling emulation toward humans. This keeps the work
  scientifically rich while staying far from the moral-status and dual-use thresholds
  that make human "mind uploading" fraught. Any move up the phylogenetic ladder is a
  separate proposal with separate review.
- **Moral status monitoring.** As models gain closed-loop sensorimotor complexity, track
  proposed correlates of valence/sentience (nociceptive-analog circuits, learned
  avoidance, integration measures) and set pre-committed pause criteria. For a fly-scale
  system the risk is low, but the *monitoring methodology itself* is a contribution for
  when others scale up.
- **Biosecurity / dual-use.** This is purely in-silico and organism-scoped to a
  non-pathogen model insect; no wet-lab agent work, no sequence design, no capability
  that transfers to engineering organisms. A dual-use review gates any change to that.
- **AI-safety framing.** A Conductor that both *reads* full internal state and *writes*
  arbitrary interventions in a closed loop is a clean, contained testbed for
  interpretability-plus-control questions that matter for AI safety broadly: can you
  steer a system by reading its internals? what is the minimal intervention? do learned
  controllers find "adversarial" levers that produce behavior without producing the
  underlying state?
- **Metacognition & consciousness (the user's core interests).** The embodied in-silico
  fly is a substrate to operationalize questions the user cares about: does the network
  build *internal models* / predictive representations (world-model probing)? are there
  confidence-like or uncertainty signals in the neural state that predict behavioral
  hedging? These are testable read-outs in a system with full observability — a rare
  chance to study metacognitive *correlates* in a whole, embodied, connectome-grounded
  brain rather than a black-box agent.

---

## 9. Why this is the right study to run now

Every ingredient exists and is public: the connectome (FlyWire/hemibrain/MANC/larva), the
structure→dynamics ML recipe (Eon), the embodiment engine (NeuroMechFly v2), and mature
GNN/SBI/deep-RL tooling. What has *not* been done is (1) treating instantiation as a
*posterior* and testing identifiability, (2) building an AI that closes the loop by
reading and writing neural state to *drive* behavior, and (3) doing both at the scale of a
*population*. CHORUS is the smallest program that delivers all three while producing a
concrete, falsifiable answer to the preservation-vs-emulation question that the Nectome
program hinges on.
