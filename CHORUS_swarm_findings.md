# CHORUS — Swarm-Control Experiments & Findings
### Trying multiple ways to make an AI create and drive a population of in-silico fly brains

*Companion to `CHORUS_research_study.md`. This memo reports a working in-silico
prototype that implements the proposal's Stage D (drive) and Stage E (population),
borrows five coordination paradigms from the drone-swarm / collective-behaviour
literature, and runs the Stage ④ validation gauntlet. Everything here is
reproducible from `chorus_sim.py` + `chorus_controllers.py`.*

---

## 1. What was built

A vectorised population of **30 embodied agents**, each driven by an internal
**connectome-derived recurrent rate network** (120 neurons, sparse signed weights
obeying Dale's law, scaled to the edge-of-chaos/reservoir regime). The brains are
*shared species wiring* with small per-agent "posterior-draw" weight jitter — the
population is a set of samples from an instantiated brain, exactly as in the
proposal's Instantiator.

Each brain sits in a **2D physics-lite arena** with a Gaussian **odour source**.
Bilateral (left/right antenna) odour and local neighbour density flow in as
sensory input; a **calibrated motor decoder** reads three internal "steering"
neuron pools (left / right / forward) to produce turn and forward commands. The
task — a canonical swarm benchmark — is **collective chemotaxis**: get the
population from the far corner to the source.

**"Driving" = writing stimulation into internal neurons** (in-silico
optogenetics). Every controller works by injecting activity into the steering
pools while the sensory loop keeps running — no controller ever writes motor
commands directly. This is the key modelling choice that makes it a *brain*
control problem, not a point-particle swarm.

## 2. The five paradigms (mapped from swarm robotics)

| Paradigm | Swarm-robotics origin | How it drives the brains |
|---|---|---|
| **Autonomous** | open-loop baseline | no stimulation — connectome + sensory loop only |
| **Centralized Conductor** | drone-fleet ground station; full observability | one policy reads every agent's true gradient, injects corrective stimulation |
| **Decentralized (boids)** | Reynolds 1987 (separation/alignment/cohesion) + gradient | local-neighbour rules only, expressed as stimulation; no global info |
| **Leader-follower** | Couzin 2005 partially-informed groups; consensus flocking | a few "informed" agents steer to source, rest align to neighbours |
| **Stigmergy** | ant-colony optimization (Dorigo); pheromone trails | agents deposit/sense a shared environmental field + odour |

## 3. Headline results (n = 8 seeds each; see `chorus_results.png`)

**Task success (fraction of agents reaching the source):**

| Paradigm | Reached | Median time-to-source |
|---|---|---|
| Centralized Conductor | **0.89 ± 0.06** | 115 steps |
| Decentralized (boids+gradient) | 0.42 ± 0.14 | 235 |
| Stigmergy | 0.19 ± 0.08 | (>T) |
| Leader-follower | 0.15 ± 0.03 | (>T) |
| Autonomous (no drive) | 0.00 ± 0.01 | (>T) |

- **Driving works, and the method matters.** Full-observability centralized
  control nearly solves the task; decentralized local rules get roughly half the
  swarm there with far less information; indirect/partial schemes trail; the
  undriven baseline never arrives. This is the ordering the swarm literature
  predicts, reproduced on connectome-derived brains.
- **A population is controllable with a single shared policy** — one Conductor
  drives 30 different brains (different posterior draws) at once, which is the
  fleet-robotics result carried over to in-silico brains.

## 4. The validation gauntlet — and the finding that matters most

Running the proposal's "digital-sphinx" controls under the **strong** Centralized
Conductor gave a result that is initially uncomfortable but is the scientific
payload of the whole exercise:

**Under strong drive, the connectome is bypassed.** Task success with the intact
connectome (0.89) was *statistically indistinguishable* from success with a
**shuffled** (0.84), **sign-scrambled** (0.91), or **entirely random** (0.82)
connectome. A powerful controller with full read/write access overrides intrinsic
dynamics — it can drive *any* sufficiently expressive network to the goal. **Task
success alone therefore does not certify that you have captured the brain.** This
is the digital-sphinx critique, reproduced and quantified: a model can "work"
while telling you nothing about whether the wiring is right.

**The controllability–identifiability tradeoff (panel c).** Sweeping stimulation
gain resolves the paradox. Connectome-*sensitivity* (how much the intact wiring
beats a shuffled one) is near zero at low gain (brain too weakly driven to act),
**peaks at intermediate gain ≈1.5** (intact beats shuffled by ~10 points), then
**collapses back toward zero at high gain** (drive swamps the dynamics). *There is
a specific drive regime in which the connectome is both expressed and
identifiable* — and it is not the regime that maximises task success. Any honest
programme to "instantiate a brain from structure" must operate and be evaluated
in that intermediate band, not at maximum control authority.

**The preservation stress test (panel d) — direct relevance to Nectome.** In the
intermediate regime we degraded the connectome two ways:
- **Edge ablation (topology loss):** removing **up to 80 % of synapses** barely
  changed behaviour (0.87 → 0.88). The wiring diagram is massively redundant for
  behaviour.
- **Weight noise (synaptic-strength corruption):** behaviour degraded **smoothly
  and severely** — σ=0.1 dropped success to 0.70, σ=0.3 to 0.38, σ=0.5 to 0.23.

This is a clean **dissociation**: *which connections exist* is robust; *how strong
they are* is fragile. It is a quantitative statement of the Nectome worry — a
preservation method that captures topology but not synaptic weights (the
"synaptome") would pass a connectivity check yet fail to reproduce behaviour. The
load-bearing quantity is the weights, not the graph.

## 5. What each attempt taught us (the "try multiple ways" ask)

1. **Centralized full-observability control** is the most effective *and* the most
   misleading — it works so well it hides whether the brain is right. Use it as a
   capability ceiling, never as evidence of fidelity.
2. **Decentralized boids-style stimulation** is the most biologically honest
   driver: local information only, emergent aggregation, moderate success. This is
   the paradigm to develop for *naturalistic* control.
3. **Leader-follower** shows information can propagate through a partially-informed
   population — promising for "seed a few neurons, let dynamics spread", but our
   consensus coupling was too weak; needs stronger inter-agent alignment.
4. **Stigmergy** underperformed here (short horizon, fast pheromone decay) but is
   the only paradigm that scales without per-agent communication — worth revisiting
   for large populations.
5. **The gauntlet is non-negotiable.** Every paradigm "succeeded" enough to look
   good; only the shuffled/random controls and the gain sweep revealed when success
   was real versus imposed.

## 6. Direct implications for the full CHORUS study

- **Redefine the fidelity metric.** Behavioural success must be reported *together
  with* connectome-sensitivity (intact-minus-shuffled) at a controlled,
  intermediate drive level. Success at max drive is not a fidelity claim.
- **The Instantiator should target weights, not just topology.** Since weights are
  load-bearing and topology is redundant, simulation-based inference effort belongs
  on synaptic strengths, signs, and time-constants — precisely the parameters the
  connectome omits and Nectome's critics flag.
- **Operate the Conductor in the identifiable band.** Add a regulariser that
  penalises stimulation magnitude, so the controller is forced to exploit intrinsic
  dynamics rather than override them — this is where "driving a brain" and
  "understanding a brain" coincide.
- **Population studies are viable now.** Shared-policy control over 30 jittered
  brains already works; scaling to hundreds and to spiking networks on GPU is an
  engineering step, not a conceptual one.

## 7. Honest limitations

This is a **rate-network abstraction in a physics-lite arena**, not the FlyWire
connectome in NeuroMechFly. The 120-neuron reservoir stands in for the
instantiated brain; the arena stands in for the embodied loop. The *relationships*
demonstrated — driving works, method ordering, the controllability–identifiability
tradeoff, the topology-vs-weights dissociation — are the transferable findings and
are stated as hypotheses to re-test at scale (Phase 1–3 of the main proposal) on
the real connectome and body. Numbers are specific to this model; the qualitative
structure is the contribution.
