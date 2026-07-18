# CHORUS — Driving Real Fly Swarms with a Central-Complex BCI
### From in-silico brains to implantable steering of live flies toward a fictive target

*Companion to `CHORUS_research_study.md` and `CHORUS_swarm_findings.md`. This memo
answers the specific question: can an AI convince a swarm of real flies to go in a
chosen direction using tiny implantable BCI circuitry — even when the thing they'd
normally chase (an odor) is not there?*

---

## 1. The reframing, and why it changes the substrate

The earlier prototype used a random reservoir brain and a real odor gradient. Two
things had to change to make this about **real flies with implants**:

1. **A realistic connectome, not a random network.** Instead of an arbitrary
   reservoir I built the **central complex (CX)** — the fly's navigation hub — using
   its *documented wiring motifs* (Kim et al. 2017; Turner-Evans et al. 2020; Hulse
   et al. 2021 hemibrain CX reconstruction). The CX is a **ring attractor**: EPG
   "compass" neurons hold a single bump of activity encoding the fly's current
   heading; PEN neurons rotate that bump by the fly's angular velocity
   (dead-reckoning); Δ7 neurons provide global inhibition so only one bump survives;
   and PFL3 output neurons compare the heading bump against a **goal bump** and drive
   turning to null the difference. *(I attempted to pull the exact hemibrain
   connectivity from neuprint/FlyWire; those portals are auth-gated and were not
   reachable here, so the circuit is instantiated from the published motifs rather
   than a downloaded adjacency matrix. Swapping in the real weight matrix is a
   drop-in upgrade and is the first Phase-1 task.)*

2. **A fabricated goal, not a real stimulus.** This is the mechanistic key. A fly
   doing **menotaxis** holds an *arbitrary* goal heading with no gradient present —
   the goal bump is internal. So a BCI does not need to fake an odor; it needs to
   **write the goal bump directly**. Set the goal, and the fly's own attractor
   circuit does the steering. That is why this is feasible in a real animal: you are
   borrowing the navigation controller the fly already has.

## 2. What was built and tested (all reproducible from `cx_connectome.py`)

- A calibrated CX ring attractor: verified it **holds a stable heading** (bump std
  0.01 rad at rest) and **tracks imposed rotation** (dead-reckoning), with a
  proprioceptive gain constant (K≈1.37) fit so the internal compass matches true
  heading 1:1.
- **Fictive-goal steering (no odor):** writing a clean goal bump steers a fly to the
  commanded heading with ~16–18° error for most directions (larger only near ±180°,
  an expected ring-attractor property where the bump must cross the whole ring).
- **Realistic implant model:** a tiny implant cannot write a clean 16-wedge bump. I
  modeled **coarse electrodes** — N discrete stimulation sites, broad footprint,
  positional jitter, plus proprioceptive noise — and quantized the goal to the
  nearest electrode.
- **Embodied swarm to a target point (no odor anywhere):** each fly's BCI computes
  the bearing to a target and writes it as a coarse goal; the fly walks.

## 3. Results (see `chorus_bci_results.png`)

**Steering a swarm to a fabricated target with no stimulus in the world works.**

| Implant | Swarm reaching target | Heading error |
|---|---|---|
| Clean goal (ideal ceiling) | 76% | ~16° |
| **8 electrodes** | **92%** | **21°** |
| 4 electrodes | 80% | 30° |
| 16 electrodes | 84% | 14° |
| 2 electrodes | 4% | 63° |

- **Minimal viable implant ≈ 4–8 stimulation sites.** Two electrodes cannot resolve
  direction (fails); four already delivers 80% of the swarm to target; eight is the
  practical sweet spot. This is a concrete hardware spec, not a vague aspiration.
- **The fly's own dynamics clean up a noisy BCI.** Steering held up under large goal
  jitter — even 0.8 rad (~46°) of per-step goal noise still landed 72% of the swarm.
  The ring attractor integrates and denoises the coarse implant signal. This is the
  most encouraging sim-to-real result: the implant can be crude because the biology
  is doing the precision work.
- **Heading locks on and holds** (panel c): commanded a heading, the fly's actual
  heading converges within ~30 steps and stays there — open-loop-stable menotaxis
  driven entirely by the written goal.

## 4. Why this is the right mechanism for a real animal

- **You are not fighting the brain, you are commanding it.** Injecting a goal into
  PFL3/FB goal circuitry uses the fly's existing steering controller. Contrast with
  the earlier "strong centralized drive" finding, where brute stimulation overrode
  the connectome and made it irrelevant — here the connectome (the CX) is *doing the
  work*, which is both more efficient and more robust.
- **The goal representation is low-dimensional.** Heading is a single angle. You do
  not need to control 100k neurons — you need to bias one bump in one ~16-column
  circuit. That is what makes a *tiny* implant plausible.
- **It degrades gracefully**, so imperfect surgery, electrode drift, and signal noise
  do not break it.

## 5. Concrete path to wet-lab (Phases)

- **P0 — real connectivity.** Replace the motif-based CX with the hemibrain CX
  adjacency matrix (EPG/PEN/Δ7/PFL3, ~a few hundred neurons) from neuprint/FlyWire
  once auth is available. Re-run everything; the code is drop-in.
- **P1 — spiking + optogenetics model.** Move from rate to spiking; model the BCI as
  **optogenetic activation** (e.g. CsChrimson in EPG or FB goal neurons) rather than
  abstract stimulation — this matches the real actuation modality and lets us predict
  light-power/temporal requirements.
- **P2 — closed-loop in tethered flies.** The standard rig: tethered fly on a ball or
  in VR, two-photon or LED optogenetic targeting of CX, measure whether written goals
  produce commanded fictive turning. This is directly testable with today's tools and
  is where the model's predictions get falsified or confirmed.
- **P3 — free-flight/free-walking micro-implant.** The hard engineering: a
  weight-and-power-budgeted implant delivering 4–8 stimulation sites to the CX in a
  freely behaving fly, driven by an external AI computing goal headings for the
  swarm. The 4–8-electrode spec and noise-tolerance numbers here are the design
  targets.

## 6. Safety, ethics, biosecurity (this is a live animal now)

The moment this leaves simulation it stops being purely computational, and the bar
rises accordingly:

- **Animal-welfare governance.** Implantation and neural manipulation of live animals
  require institutional animal-care approval (IACUC-equivalent), even for insects in
  many frameworks. Anesthesia, surgical load, and refinement/reduction principles
  apply. The in-silico work here exists partly to **minimize live-animal use** by
  pre-computing the minimal viable implant and predicting failure modes before any
  surgery.
- **Dual-use review — mandatory and non-trivial.** "AI steers a swarm of live insects
  toward a target" is a capability with obvious dual-use dimensions (surveillance,
  directed insect delivery). This work should be gated by an explicit dual-use
  assessment, kept to non-pathogen model species, published with the controls and
  limitations foregrounded, and scoped away from any payload/vector application. The
  biology here — a navigation-steering interface — is deliberately *not* a
  pathogen-, toxin-, or vector-engineering capability, and must not be extended in
  that direction.
- **Moral-status caution scales with capability.** Fly welfare is the immediate
  concern; the methodology (welfare monitoring, minimal intervention) is what would
  need to travel if anyone ever moved up the phylogenetic ladder — which this program
  explicitly does not.
- **Scope discipline carries over from the main study:** insect-only, in-silico-first,
  no uplift toward vertebrate or human interfaces.

## 7. Honest limitations

- The CX here is built from **published motifs, not the downloaded hemibrain matrix**
  (portals were auth-gated in this environment). The qualitative results — fictive-
  goal steering, the 4–8-electrode spec, noise tolerance — follow from the ring-
  attractor architecture and should be robust to the exact weights, but the numbers
  will shift with real connectivity and must be re-derived in P0.
- Rate model, 2D walking arena, abstract stimulation. Real flies add sensory conflict
  (they will also see/smell the actual world), flight aerodynamics, adaptation, and
  individual variation. The claim is **mechanistic feasibility and a hardware spec**,
  not a finished device.
- No claim that the fly "wants" the target — only that its heading controller can be
  set. Whether higher drives (hunger, threat) override a written goal is an open,
  testable question (P2).
